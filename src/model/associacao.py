"""Regras de associação: Apriori, Eclat e FP-Growth.

O `mlxtend` traz Apriori e FP-Growth, mas não o **Eclat**. A implementação
abaixo é própria e usa a representação que dá nome ao algoritmo: em vez da
lista de itens de cada transação (representação *horizontal*), guarda-se para
cada item a lista de transações em que ele aparece (o *tidset*, representação
**vertical**). O suporte de um conjunto passa a ser o tamanho da interseção dos
tidsets — uma operação de conjunto, sem varrer a base de novo.

Os três algoritmos produzem **exatamente os mesmos** conjuntos frequentes para
os mesmos limiares. O que muda é como chegam lá, e quanto custa. Verificar essa
igualdade na prática é o exercício.

Zaki, M. J. (2000). *Scalable Algorithms for Association Mining.*
IEEE TKDE, 12(3), 372–390.
"""

from __future__ import annotations

import time
from itertools import combinations

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth

from src.data import dicionario as dic

# --------------------------------------------------------------------------- #
# Preparação transacional
# --------------------------------------------------------------------------- #

#: Faixas semânticas das ordinais. A escala 1–10 de qualidade é oficial da base;
#: o corte em 4 / 7 separa "abaixo do padrão", "padrão" e "acima do padrão" como
#: o próprio mercado imobiliário descreve.
FAIXAS_ORDINAIS = {
    "qualidade_geral": ([0, 4, 7, 10], ["qualidade:baixa", "qualidade:média", "qualidade:alta"]),
    "conservacao_geral": (
        [0, 4, 6, 10],
        ["conservação:ruim", "conservação:média", "conservação:boa"],
    ),
    "qualidade_cozinha": (
        [-1, 2, 3, 5],
        ["cozinha:simples", "cozinha:padrão", "cozinha:superior"],
    ),
}

#: Numéricas discretizadas por **quartil da própria carteira**. A escolha é
#: deliberada: quartil é relativo ao estoque, e não a um valor absoluto que
#: envelheceria a cada ano. O efeito sobre as regras está registrado em
#: `docs/modelagem.md`.
NUMERICAS_QUARTIL = {
    "area_habitavel": "área",
    "area_terreno": "terreno",
    "idade_imovel": "idade",
    "banheiros_total": "banheiros",
}

QUARTIS = ["Q1", "Q2", "Q3", "Q4"]


def montar_transacoes(curada: pd.DataFrame, segmentos: np.ndarray | None = None) -> pd.DataFrame:
    """Converte cada imóvel em uma transação de itens.

    A entidade da transação é o **imóvel**, não o bairro nem o ano: a pergunta
    de negócio é sobre a composição do produto. Agrupar por bairro juntaria
    imóveis distintos em uma cesta só e inflaria o suporte artificialmente.

    Args:
        curada: base curada.
        segmentos: rótulos de segmento; quando informados, cada transação
            recebe também o item ``segmento:Sn``, o que permite minerar as
            regras que ligam configuração de produto a segmento.

    Returns:
        Matriz booleana ``imóveis × itens``, no formato que o `mlxtend` espera.
    """
    itens = pd.DataFrame(index=curada.index)

    # Nominais: cada categoria é um item nativo, sem discretização nenhuma.
    for coluna in dic.NOMINAIS:
        prefixo = dic.rotulo(coluna).lower().replace(" ", "_")
        marcadores = pd.get_dummies(curada[coluna], prefix=prefixo, prefix_sep=":")
        itens = pd.concat([itens, marcadores], axis=1)

    # Ordinais: faixas com significado de mercado.
    for coluna, (cortes, rotulos) in FAIXAS_ORDINAIS.items():
        faixa = pd.cut(curada[coluna], bins=cortes, labels=rotulos, include_lowest=True)
        itens = pd.concat([itens, pd.get_dummies(faixa)], axis=1)

    # Numéricas: quartis da própria carteira.
    for coluna, prefixo in NUMERICAS_QUARTIL.items():
        faixa = pd.qcut(
            curada[coluna].rank(method="first"), q=4, labels=[f"{prefixo}:{q}" for q in QUARTIS]
        )
        itens = pd.concat([itens, pd.get_dummies(faixa)], axis=1)

    # Binárias derivadas: presença de item construtivo.
    for coluna in dic.BINARIAS:
        nome = dic.rotulo(coluna).lower().replace(" ", "_")
        itens[f"{nome}:sim"] = curada[coluna] == 1

    if segmentos is not None:
        marcadores = pd.get_dummies(
            pd.Series(segmentos, index=curada.index), prefix="segmento", prefix_sep=":"
        )
        itens = pd.concat([itens, marcadores], axis=1)

    return itens.astype(bool)


# --------------------------------------------------------------------------- #
# Eclat — implementação vertical
# --------------------------------------------------------------------------- #


def eclat(transacoes: pd.DataFrame, suporte_minimo: float, max_tamanho: int = 4) -> pd.DataFrame:
    """Minera conjuntos frequentes pela representação vertical (tidsets).

    Args:
        transacoes: matriz booleana ``transações × itens``.
        suporte_minimo: suporte relativo mínimo, entre 0 e 1.
        max_tamanho: tamanho máximo do conjunto a explorar.

    Returns:
        Tabela com ``support`` e ``itemsets``, no mesmo formato do `mlxtend`,
        para que a comparação entre algoritmos seja direta.
    """
    n = len(transacoes)
    minimo_absoluto = int(np.ceil(suporte_minimo * n))

    # Representação vertical: item → conjunto de identificadores de transação.
    tidsets: dict[str, set[int]] = {}
    for item in transacoes.columns:
        posicoes = set(np.flatnonzero(transacoes[item].to_numpy()).tolist())
        if len(posicoes) >= minimo_absoluto:
            tidsets[item] = posicoes

    frequentes: list[tuple[frozenset, int]] = [
        (frozenset([item]), len(tids)) for item, tids in tidsets.items()
    ]

    def explorar(prefixo: list[str], candidatos: list[tuple[str, set[int]]]) -> None:
        """Busca em profundidade: estende o prefixo com um item de cada vez."""
        for posicao, (item, tids) in enumerate(candidatos):
            novo_prefixo = [*prefixo, item]
            frequentes.append((frozenset(novo_prefixo), len(tids)))
            if len(novo_prefixo) >= max_tamanho:
                continue
            # A interseção substitui a varredura da base — é o ganho do Eclat.
            proximos = [
                (outro, tids & outros_tids)
                for outro, outros_tids in candidatos[posicao + 1 :]
                if len(tids & outros_tids) >= minimo_absoluto
            ]
            if proximos:
                explorar(novo_prefixo, proximos)

    ordenados = sorted(tidsets.items(), key=lambda par: (-len(par[1]), par[0]))
    for posicao, (item, tids) in enumerate(ordenados):
        proximos = [
            (outro, tids & outros_tids)
            for outro, outros_tids in ordenados[posicao + 1 :]
            if len(tids & outros_tids) >= minimo_absoluto
        ]
        if proximos:
            explorar([item], proximos)

    resultado = pd.DataFrame(frequentes, columns=["itemsets", "contagem"]).drop_duplicates(
        subset="itemsets"
    )
    resultado["support"] = resultado["contagem"] / n
    return (
        resultado[["support", "itemsets"]]
        .sort_values("support", ascending=False)
        .reset_index(drop=True)
    )


def comparar_algoritmos(
    transacoes: pd.DataFrame, suporte_minimo: float, max_tamanho: int = 4
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Roda os três algoritmos com os mesmos limiares e confere a equivalência.

    Returns:
        Par ``(comparativo, conjuntos_apriori)``. O comparativo traz tempo e
        número de conjuntos por algoritmo, além da confirmação de que os
        conjuntos são idênticos.
    """
    resultados: dict[str, tuple[pd.DataFrame, float]] = {}

    for nome, funcao in (("Apriori", apriori), ("FP-Growth", fpgrowth)):
        inicio = time.perf_counter()
        saida = funcao(
            transacoes, min_support=suporte_minimo, use_colnames=True, max_len=max_tamanho
        )
        resultados[nome] = (saida, time.perf_counter() - inicio)

    inicio = time.perf_counter()
    saida_eclat = eclat(transacoes, suporte_minimo, max_tamanho=max_tamanho)
    resultados["Eclat (implementação própria)"] = (saida_eclat, time.perf_counter() - inicio)

    referencia = {frozenset(c) for c in resultados["Apriori"][0]["itemsets"]}
    linhas = []
    for nome, (saida, duracao) in resultados.items():
        conjuntos = {frozenset(c) for c in saida["itemsets"]}
        linhas.append(
            {
                "algoritmo": nome,
                "conjuntos_frequentes": len(saida),
                "tempo_s": round(duracao, 3),
                "identico_ao_apriori": conjuntos == referencia,
                "conjuntos_a_mais": len(conjuntos - referencia),
                "conjuntos_a_menos": len(referencia - conjuntos),
            }
        )
    return pd.DataFrame(linhas).set_index("algoritmo"), resultados["Apriori"][0]


# --------------------------------------------------------------------------- #
# Regras: geração, poda e leitura
# --------------------------------------------------------------------------- #


def gerar_regras(
    frequentes: pd.DataFrame, confianca_minima: float = 0.60, lift_minimo: float = 1.20
) -> pd.DataFrame:
    """Gera regras e aplica o primeiro filtro: confiança e lift.

    O lift é o filtro que separa descoberta de trivialidade. Uma regra com
    confiança de 0,95 e lift de 1,00 diz apenas que o consequente é comum — ela
    valeria para qualquer antecedente.
    """
    regras = association_rules(frequentes, metric="confidence", min_threshold=confianca_minima)
    regras = regras[regras["lift"] >= lift_minimo].copy()
    regras["antecedentes"] = regras["antecedents"].apply(lambda s: ", ".join(sorted(s)))
    regras["consequentes"] = regras["consequents"].apply(lambda s: ", ".join(sorted(s)))
    regras["tamanho_antecedente"] = regras["antecedents"].apply(len)
    return regras.sort_values("lift", ascending=False).reset_index(drop=True)


def podar_redundantes(regras: pd.DataFrame) -> pd.DataFrame:
    """Remove regras redundantes por especialização do antecedente.

    Uma regra ``{A, B} → C`` é redundante quando já existe ``{A} → C`` com
    confiança igual ou maior: acrescentar B ao antecedente não informou nada, só
    reduziu o suporte. Manter as duas infla a contagem de "descobertas" sem
    acrescentar conhecimento.
    """
    manter = []
    por_consequente: dict[frozenset, list[tuple[frozenset, float]]] = {}
    for _, regra in regras.sort_values("tamanho_antecedente").iterrows():
        consequente = frozenset(regra["consequents"])
        antecedente = frozenset(regra["antecedents"])
        gerais = por_consequente.setdefault(consequente, [])
        redundante = any(
            outro < antecedente and confianca >= regra["confidence"] - 1e-9
            for outro, confianca in gerais
        )
        if not redundante:
            manter.append(regra.name)
            gerais.append((antecedente, float(regra["confidence"])))
    return regras.loc[manter].sort_values("lift", ascending=False).reset_index(drop=True)


def remover_regras_triviais(regras: pd.DataFrame) -> pd.DataFrame:
    """Descarta regras cujo antecedente e consequente vêm da mesma variável.

    ``área:Q4 → terreno:Q4`` é informativa. ``área:Q4 → área:Q3`` é impossível,
    e regras entre faixas da mesma variável só poluem o resultado.
    """

    def prefixos(conjunto) -> set[str]:
        return {item.split(":")[0] for item in conjunto}

    mesma_variavel = regras.apply(
        lambda r: bool(prefixos(r["antecedents"]) & prefixos(r["consequents"])), axis=1
    )
    return regras[~mesma_variavel].reset_index(drop=True)


#: Pares de variáveis ligadas **por definição**, e não por comportamento de
#: mercado. Uma casa de estilo `2Story` tem segundo pavimento porque é isso que
#: `2Story` significa; um imóvel com `tipo_de_garagem` diferente de `SemGaragem`
#: tem garagem pela mesma razão.
#:
#: Nenhuma métrica detecta isso: suporte, confiança e lift são altos justamente
#: porque a relação é perfeita. Só o conhecimento do domínio separa a tautologia
#: da descoberta — e essa é a razão de a lista ser explícita, e não inferida.
TAUTOLOGIAS: list[tuple[str, str]] = [
    ("tem_2º_pavimento", "estilo"),
    ("tem_garagem", "tipo_de_garagem"),
    ("tem_porão", "acabamento_da_garagem"),
]


def remover_tautologias(
    regras: pd.DataFrame, pares: list[tuple[str, str]] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Descarta regras que ligam variáveis definicionalmente equivalentes.

    Returns:
        Par ``(mantidas, descartadas)``. As descartadas são gravadas no
        relatório: mostrar o que foi removido, e por quê, é o que impede a
        suspeita de que o resultado foi escolhido a dedo.
    """
    pares = pares or TAUTOLOGIAS

    def prefixos(conjunto) -> set[str]:
        return {str(item).split(":")[0] for item in conjunto}

    def e_tautologia(regra) -> bool:
        antes, depois = prefixos(regra["antecedents"]), prefixos(regra["consequents"])
        return any((a in antes and b in depois) or (b in antes and a in depois) for a, b in pares)

    if regras.empty:
        return regras, regras
    marcador = regras.apply(e_tautologia, axis=1)
    return (
        regras[~marcador].reset_index(drop=True),
        regras[marcador].sort_values("lift", ascending=False).reset_index(drop=True),
    )


def regras_por_segmento(
    transacoes: pd.DataFrame,
    segmentos: np.ndarray,
    suporte_minimo: float = 0.15,
    confianca_minima: float = 0.60,
    lift_minimo: float = 1.20,
    max_tamanho: int = 3,
) -> pd.DataFrame:
    """Minera regras dentro de cada segmento e compara o lift com o da base inteira.

    É o cruzamento que valida ou contesta a segmentação: se as regras de cada
    grupo forem as mesmas da base toda, o agrupamento não achou nada que a
    frequência global já não dissesse.
    """
    colunas = [c for c in transacoes.columns if not c.startswith("segmento:")]
    resultados = []
    for segmento in sorted(np.unique(segmentos)):
        recorte = transacoes.loc[segmentos == segmento, colunas]
        if len(recorte) < 40:
            continue
        frequentes = fpgrowth(
            recorte, min_support=suporte_minimo, use_colnames=True, max_len=max_tamanho
        )
        if frequentes.empty:
            continue
        regras = gerar_regras(frequentes, confianca_minima, lift_minimo)
        regras = remover_tautologias(remover_regras_triviais(podar_redundantes(regras)))[0]
        if regras.empty:
            continue
        regras.insert(0, "segmento", segmento)
        resultados.append(regras)
    if not resultados:
        return pd.DataFrame()
    return pd.concat(resultados, ignore_index=True)


def lift_diferencial(
    regras_segmento: pd.DataFrame, regras_globais: pd.DataFrame, minimo_diferenca: float = 0.20
) -> pd.DataFrame:
    """Isola as regras que só valem dentro de um segmento.

    Para cada regra de segmento, procura a mesma regra na base inteira e mede a
    diferença de lift. Regra com lift alto no segmento e baixo (ou ausente) no
    global é o padrão diferencial que sustenta uma ação específica.
    """
    chave_global = {
        (frozenset(a), frozenset(c)): lift
        for a, c, lift in zip(
            regras_globais["antecedents"],
            regras_globais["consequents"],
            regras_globais["lift"],
            strict=True,
        )
    }
    linhas = []
    for _, regra in regras_segmento.iterrows():
        chave = (frozenset(regra["antecedents"]), frozenset(regra["consequents"]))
        lift_base = chave_global.get(chave, np.nan)
        diferenca = regra["lift"] - (lift_base if lift_base == lift_base else 1.0)
        if diferenca >= minimo_diferenca:
            linhas.append(
                {
                    "segmento": regra["segmento"],
                    "regra": f"{regra['antecedentes']}  →  {regra['consequentes']}",
                    "suporte_no_segmento": round(float(regra["support"]), 3),
                    "confianca": round(float(regra["confidence"]), 3),
                    "lift_no_segmento": round(float(regra["lift"]), 2),
                    "lift_na_base": round(float(lift_base), 2) if lift_base == lift_base else None,
                    "diferenca": round(float(diferenca), 2),
                }
            )
    return (
        pd.DataFrame(linhas)
        .sort_values(["segmento", "diferenca"], ascending=[True, False])
        .reset_index(drop=True)
    )


def formatar_regras(regras: pd.DataFrame, quantas: int = 20) -> pd.DataFrame:
    """Recorta as colunas legíveis para publicação em relatório."""
    colunas = {
        "antecedentes": "se o imóvel tem",
        "consequentes": "então também tem",
        "support": "suporte",
        "confidence": "confiança",
        "lift": "lift",
        "leverage": "leverage",
        "conviction": "convicção",
    }
    disponiveis = [c for c in colunas if c in regras.columns]
    return (
        regras.head(quantas)[disponiveis]
        .rename(columns=colunas)
        .round({"suporte": 3, "confiança": 3, "lift": 2, "leverage": 4, "convicção": 2})
        .reset_index(drop=True)
    )


def itens_por_tamanho(frequentes: pd.DataFrame) -> pd.DataFrame:
    """Distribuição dos conjuntos frequentes por número de itens."""
    tamanhos = frequentes["itemsets"].apply(len)
    return (
        tamanhos.value_counts().sort_index().rename_axis("itens_no_conjunto").to_frame("conjuntos")
    )


def combinacoes_frequentes(
    frequentes: pd.DataFrame, tamanho: int, quantas: int = 10
) -> pd.DataFrame:
    """Os conjuntos mais frequentes de um dado tamanho, já legíveis."""
    recorte = frequentes[frequentes["itemsets"].apply(len) == tamanho].nlargest(quantas, "support")
    return pd.DataFrame(
        {
            "combinação": recorte["itemsets"].apply(lambda s: "  +  ".join(sorted(s))),
            "suporte": recorte["support"].round(3),
        }
    ).reset_index(drop=True)


def _pares_de_itens(transacoes: pd.DataFrame, itens: list[str]) -> list[tuple[str, str]]:
    """Todos os pares possíveis entre os itens informados (utilitário de teste)."""
    return list(combinations(itens, 2))
