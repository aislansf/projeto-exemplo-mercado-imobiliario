"""Do centroide à persona.

Um centroide é uma lista de coordenadas. Uma persona é uma frase que um diretor
comercial consegue repetir. A tradução tem quatro passos, e todos estão aqui:

1. **Perfil em unidades originais** — mediana de cada atributo por segmento, em
   pés quadrados e anos, não em desvios padrão;
2. **Assinatura** — o que cada segmento tem de diferente da carteira inteira,
   medido em desvios da mediana global;
3. **Representante real** — o medoide, um imóvel com identificador que existe
   de fato e pode ser visitado;
4. **Nome e ação** — em :mod:`src.model.personas`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data import dicionario as dic


def perfil_por_segmento(
    curada: pd.DataFrame, rotulos: np.ndarray, colunas: list[str] | None = None
) -> pd.DataFrame:
    """Mediana de cada atributo por segmento, em unidades originais."""
    colunas = colunas or dic.NUMERICAS + dic.ORDINAIS
    dados = curada.assign(segmento=rotulos)
    perfil = dados.groupby("segmento")[colunas].median()
    perfil.insert(0, "imóveis", dados.groupby("segmento").size())
    perfil.insert(1, "participação", (perfil["imóveis"] / len(dados)).round(3))
    return perfil.round(2)


def assinatura(
    curada: pd.DataFrame, rotulos: np.ndarray, colunas: list[str] | None = None
) -> pd.DataFrame:
    """Desvio padronizado de cada segmento em relação à carteira inteira.

    Usa mediana e desvio absoluto mediano (MAD) em vez de média e desvio padrão:
    a assinatura de um segmento não pode depender da cauda de outro.

    Em variáveis discretas muito concentradas (dormitórios, conservação) o MAD é
    zero e a divisão explodiria. Nesses casos a escala cai para o desvio padrão,
    o que preserva a leitura sem inventar um valor.
    """
    colunas = colunas or dic.NUMERICAS + dic.ORDINAIS
    dados = curada.assign(segmento=rotulos)
    mediana_global = dados[colunas].median()
    mad = (dados[colunas] - mediana_global).abs().median()
    escala = mad.where(mad > 0, dados[colunas].std()).replace(0, np.nan)
    medianas = dados.groupby("segmento")[colunas].median()
    return ((medianas - mediana_global) / escala).round(2)


def atributos_distintivos(
    assinatura_tabela: pd.DataFrame, quantos: int = 5
) -> dict[int, list[tuple[str, float]]]:
    """Os atributos que mais afastam cada segmento da carteira média."""
    distintivos: dict[int, list[tuple[str, float]]] = {}
    for segmento, linha in assinatura_tabela.iterrows():
        ordenado = linha.reindex(linha.abs().sort_values(ascending=False).index)
        distintivos[int(segmento)] = [
            (dic.rotulo(coluna), float(valor)) for coluna, valor in ordenado.head(quantos).items()
        ]
    return distintivos


def composicao_nominal(
    curada: pd.DataFrame, rotulos: np.ndarray, coluna: str, top: int = 4
) -> pd.DataFrame:
    """Composição de uma variável nominal dentro de cada segmento, em percentual."""
    dados = curada.assign(segmento=rotulos)
    tabela = pd.crosstab(dados["segmento"], dados[coluna], normalize="index")
    principais = tabela.sum().nlargest(top).index
    recorte = (100 * tabela[principais]).round(1)
    recorte["outras"] = (100 - recorte.sum(axis=1)).round(1)
    return recorte


def medoides_reais(
    curada: pd.DataFrame, rotulos: np.ndarray, distancias: np.ndarray
) -> pd.DataFrame:
    """Imóvel real mais central de cada segmento — o representante com identificador.

    É a resposta para "me mostre um imóvel deste grupo". O centroide do K-Means
    não serve: ele é uma média que pode ter 2,7 dormitórios.
    """
    linhas = []
    for segmento in sorted(np.unique(rotulos[rotulos >= 0])):
        indices = np.flatnonzero(rotulos == segmento)
        interno = distancias[np.ix_(indices, indices)].sum(axis=1)
        posicao = indices[int(np.argmin(interno))]
        registro = curada.iloc[posicao]
        linhas.append(
            {
                "segmento": int(segmento),
                "pid": int(registro["pid"]),
                "bairro": registro["bairro"],
                "area_habitavel": int(registro["area_habitavel"]),
                "qualidade_geral": int(registro["qualidade_geral"]),
                "idade_imovel": int(registro["idade_imovel"]),
                "dormitorios": int(registro["dormitorios"]),
                "banheiros_total": float(registro["banheiros_total"]),
                "tipo_construcao": registro["tipo_construcao"],
                "estilo": registro["estilo"],
                "preco_venda": int(registro["preco_venda"]),
            }
        )
    return pd.DataFrame(linhas).set_index("segmento")


def leitura_a_posteriori(curada: pd.DataFrame, rotulos: np.ndarray) -> pd.DataFrame:
    """Confronta os segmentos com o rótulo reservado — **depois** da modelagem.

    Esta é a única função do projeto que toca em ``preco_venda``, e ela roda
    depois que os segmentos já estão definidos. Serve para responder a duas
    perguntas de negócio: quanto cada segmento vale, e se a segmentação é apenas
    uma tabela de preço disfarçada.
    """
    dados = curada.assign(segmento=rotulos)
    resumo = dados.groupby("segmento").agg(
        imoveis=("preco_venda", "size"),
        preco_mediano=("preco_venda", "median"),
        preco_medio=("preco_venda", "mean"),
        preco_p10=("preco_venda", lambda s: s.quantile(0.10)),
        preco_p90=("preco_venda", lambda s: s.quantile(0.90)),
        preco_por_pe2=("preco_por_pe2", "median"),
    )
    resumo["amplitude_p90_p10"] = (resumo["preco_p90"] / resumo["preco_p10"]).round(2)
    resumo["receita_total"] = dados.groupby("segmento")["preco_venda"].sum()
    resumo["pct_receita"] = (100 * resumo["receita_total"] / dados["preco_venda"].sum()).round(1)
    return resumo.round(2)


def sobreposicao_de_preco(curada: pd.DataFrame, rotulos: np.ndarray) -> pd.DataFrame:
    """Mede quanto as faixas de preço dos segmentos se sobrepõem.

    Se os intervalos interquartis de preço não se sobrepõem, a segmentação é
    uma tabela de preço com outro nome — e a diretoria pediu outra coisa.
    """
    dados = curada.assign(segmento=rotulos)
    faixas = dados.groupby("segmento")["preco_venda"].quantile([0.25, 0.75]).unstack()
    faixas.columns = ["q1", "q3"]
    segmentos = faixas.index.tolist()
    matriz = pd.DataFrame(index=segmentos, columns=segmentos, dtype=float)
    for a in segmentos:
        for b in segmentos:
            inicio = max(faixas.loc[a, "q1"], faixas.loc[b, "q1"])
            fim = min(faixas.loc[a, "q3"], faixas.loc[b, "q3"])
            intersecao = max(0.0, fim - inicio)
            uniao = max(faixas.loc[a, "q3"], faixas.loc[b, "q3"]) - min(
                faixas.loc[a, "q1"], faixas.loc[b, "q1"]
            )
            matriz.loc[a, b] = round(intersecao / uniao, 3) if uniao > 0 else 1.0
    return matriz


def validacao_por_bairro(curada: pd.DataFrame, rotulos: np.ndarray, top: int = 6) -> pd.DataFrame:
    """Distribuição dos segmentos pelos bairros — a validação externa reservada.

    ``bairro`` ficou fora da modelagem justamente para poder ser usado aqui: se
    os segmentos se distribuírem por bairros de forma diferente, é sinal de que
    capturaram estrutura real de mercado.
    """
    dados = curada.assign(segmento=rotulos)
    principais = dados["bairro"].value_counts().nlargest(top).index
    recorte = dados[dados["bairro"].isin(principais)]
    return (100 * pd.crosstab(recorte["bairro"], recorte["segmento"], normalize="index")).round(1)
