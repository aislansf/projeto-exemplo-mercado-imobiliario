"""CRISP-DM 2.2 e 2.4 — Descrição dos dados e verificação de qualidade.

Produz o perfil que sustenta a página *Entendimento dos dados*: tipos, volume,
ausentes, cardinalidade, colunas constantes, duplicidades e sentinelas.

O perfil é gravado como tabela para que a página de documentação cite números
apurados, e não números lembrados.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def perfil_colunas(dados: pd.DataFrame) -> pd.DataFrame:
    """Monta o perfil coluna a coluna do conjunto de dados.

    Returns:
        Tabela com tipo, contagem de nulos, percentual de nulos, cardinalidade,
        percentual do valor mais frequente e amostra de valores.
    """
    total = len(dados)
    linhas = []
    for coluna in dados.columns:
        serie = dados[coluna]
        nulos = int(serie.isna().sum())
        preenchida = serie.dropna()
        moda = preenchida.mode()
        valor_frequente = moda.iloc[0] if len(moda) else np.nan
        freq_relativa = float((preenchida == valor_frequente).mean()) if len(preenchida) else np.nan
        linhas.append(
            {
                "coluna": coluna,
                "tipo": str(serie.dtype),
                "nulos": nulos,
                "pct_nulos": round(100 * nulos / total, 2),
                "distintos": int(serie.nunique(dropna=True)),
                "valor_mais_frequente": valor_frequente,
                "pct_valor_mais_frequente": round(100 * freq_relativa, 2)
                if freq_relativa == freq_relativa
                else np.nan,
            }
        )
    perfil = pd.DataFrame(linhas).set_index("coluna")
    return perfil.sort_values("pct_nulos", ascending=False)


def colunas_constantes(dados: pd.DataFrame, limiar: float = 99.5) -> pd.DataFrame:
    """Colunas com um único valor ou quase — variância nula quebra a padronização.

    Args:
        dados: conjunto a inspecionar.
        limiar: percentual de concentração acima do qual a coluna é sinalizada.
    """
    perfil = perfil_colunas(dados)
    alvo = perfil[(perfil["distintos"] <= 1) | (perfil["pct_valor_mais_frequente"] >= limiar)]
    return alvo[["distintos", "valor_mais_frequente", "pct_valor_mais_frequente"]]


def diagnostico_duplicidade(dados: pd.DataFrame, chave: str) -> dict:
    """Verifica se a chave declarada identifica de fato cada registro."""
    return {
        "linhas": int(len(dados)),
        "chaves_distintas": int(dados[chave].nunique()),
        "linhas_duplicadas_completas": int(dados.duplicated().sum()),
        "chave_unica": bool(dados[chave].is_unique),
    }


def resumo_numericas(dados: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Estatística descritiva estendida, com assimetria e curtose.

    Assimetria alta é o sinal de que a variável precisa de transformação antes
    de qualquer algoritmo baseado em distância.
    """
    resumo = dados[colunas].describe().T
    resumo["assimetria"] = dados[colunas].skew()
    resumo["curtose"] = dados[colunas].kurtosis()
    resumo["zeros"] = (dados[colunas] == 0).sum()
    resumo["pct_zeros"] = round(100 * (dados[colunas] == 0).mean(), 2)
    resumo["cv"] = resumo["std"] / resumo["mean"].replace(0, np.nan)
    return resumo.round(3)


#: Regras de plausibilidade do domínio imobiliário: nome, colunas exigidas e o
#: teste. A lista é declarada fora da função para que a checagem seja auditável
#: sem ler o corpo dela.
CHECAGENS: list[tuple[str, list[str], object]] = [
    (
        "idade negativa (construído após a venda)",
        ["ano_construcao", "ano_venda"],
        lambda d: d["ano_construcao"] > d["ano_venda"],
    ),
    (
        "reforma anterior à construção",
        ["ano_reforma", "ano_construcao"],
        lambda d: d["ano_reforma"] < d["ano_construcao"],
    ),
    (
        "garagem construída depois da venda",
        ["ano_garagem", "ano_venda"],
        lambda d: d["ano_garagem"].notna() & (d["ano_garagem"] > d["ano_venda"]),
    ),
    (
        "área habitável nula ou negativa",
        ["area_habitavel"],
        lambda d: d["area_habitavel"] <= 0,
    ),
    ("sem dormitório acima do solo", ["dormitorios"], lambda d: d["dormitorios"] == 0),
    (
        "sem banheiro completo",
        ["banheiros_completos", "banheiros_completos_porao"],
        lambda d: d["banheiros_completos"] + d["banheiros_completos_porao"] == 0,
    ),
    (
        "área do porão diverge da soma das partes",
        ["area_porao_acabada_1", "area_porao_acabada_2", "area_porao_bruta", "area_porao"],
        lambda d: (
            (
                d["area_porao_acabada_1"].fillna(0)
                + d["area_porao_acabada_2"].fillna(0)
                + d["area_porao_bruta"].fillna(0)
                - d["area_porao"].fillna(0)
            ).abs()
            > 1
        ),
    ),
    (
        "imóvel acima de 4.000 pés² (recomendação de De Cock)",
        ["area_habitavel"],
        lambda d: d["area_habitavel"] > 4000,
    ),
]


def valores_implausiveis(dados: pd.DataFrame) -> pd.DataFrame:
    """Regras de plausibilidade específicas do domínio imobiliário.

    Cada regra devolve quantos registros a violam. Regra sem violação também
    aparece — é evidência de que a checagem foi feita.

    A regra cuja coluna não existe no conjunto recebido aparece como *não
    aplicável*, e não desaparece do relatório: checagem omitida em silêncio é
    checagem que ninguém percebe que deixou de rodar.
    """
    linhas = []
    for nome, exigidas, teste in CHECAGENS:
        if not set(exigidas) <= set(dados.columns):
            ausentes = ", ".join(c for c in exigidas if c not in dados.columns)
            linhas.append(
                {
                    "regra": nome,
                    "registros": pd.NA,
                    "pct": pd.NA,
                    "situacao": f"não aplicável — sem {ausentes}",
                }
            )
            continue
        mascara = teste(dados)
        linhas.append(
            {
                "regra": nome,
                "registros": int(mascara.sum()),
                "pct": round(100 * mascara.mean(), 2),
                "situacao": "verificada",
            }
        )
    return pd.DataFrame(linhas).set_index("regra")


def matriz_ausencia(dados: pd.DataFrame, colunas: list[str] | None = None) -> pd.DataFrame:
    """Coocorrência de ausência entre colunas — revela ausência estrutural.

    Quando duas colunas faltam sempre juntas, a ausência não é aleatória: é a
    marca de um item que não existe no imóvel.
    """
    alvo = colunas or [c for c in dados.columns if dados[c].isna().any()]
    faltando = dados[alvo].isna().astype(int)
    return faltando.T @ faltando
