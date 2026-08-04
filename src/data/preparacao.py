"""CRISP-DM 3 — Preparação dos dados.

Transforma a camada bruta imutável em duas saídas:

* ``data/processed/imoveis_curados.parquet`` — base curada, em unidades
  originais, legível por gente de negócio;
* ``data/processed/matriz_modelagem.parquet`` — recorte com as 22 variáveis do
  espaço de atributos, sem rótulo reservado.

Toda regra de limpeza vem com o motivo registrado em :data:`REGRAS_LIMPEZA`,
que é publicado na documentação. Regra sem motivo é removida na primeira
refatoração e o problema volta.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    MinMaxScaler,
    OneHotEncoder,
    RobustScaler,
    StandardScaler,
)

from src import config
from src.data import dicionario as dic
from src.data.ingestao import carregar_bruto

# --------------------------------------------------------------------------- #
# Regras de limpeza — publicadas em docs/preparacao.md
# --------------------------------------------------------------------------- #

REGRAS_LIMPEZA: list[dict[str, str]] = [
    {
        "regra": "Renomear as 82 colunas para snake_case em português",
        "motivo": (
            "Os nomes originais têm espaço no meio (`Gr Liv Area`), o que obriga a "
            "usar colchetes em toda referência e impede o acesso por atributo. O "
            "resultado é lido por gente de negócio."
        ),
    },
    {
        "regra": "Ler o arquivo com `na_values=['NA', '']`, em vez do padrão do pandas",
        "motivo": (
            "A palavra `None` em `Mas Vnr Type` é categoria legítima — 'sem "
            "revestimento em alvenaria aparente'. A leitura padrão a converte em "
            "nulo e transforma 1.752 imóveis descritos em 1.752 imóveis "
            "desconhecidos, inflando a ausência da coluna de 0,8% para 60,6%."
        ),
    },
    {
        "regra": "Converter `NA` em rótulo de ausência estrutural em 14 colunas",
        "motivo": (
            "Nessas colunas `NA` significa 'o item não existe' (sem porão, sem "
            "garagem, sem lareira), não 'informação faltante'. Imputar pela mediana "
            "inventaria porões que nunca existiram."
        ),
    },
    {
        "regra": "Mapear 20 colunas ordinais para inteiros, com 0 para ausência",
        "motivo": (
            "`Ex > Gd > TA > Fa > Po` tem ordem semântica. One-hot destruiria essa "
            "ordem e multiplicaria a dimensionalidade sem ganho."
        ),
    },
    {
        "regra": "Corrigir `ano_garagem = 2207` para 2007",
        "motivo": (
            "Erro de digitação evidente: o imóvel foi vendido em 2007 e construído "
            "em 2006. Sem a correção, a idade da garagem fica negativa em 200 anos "
            "e domina qualquer padronização."
        ),
    },
    {
        "regra": "Imputar `testada_lote` pela mediana do bairro",
        "motivo": (
            "16,7% de ausência concentrada em lotes de esquina e de fundo, onde a "
            "medida não é registrada — ausência MAR, explicada pela geometria do "
            "lote. A mediana global achataria a variação entre bairros."
        ),
    },
    {
        "regra": "Preencher com 0 as áreas e contagens de itens inexistentes",
        "motivo": (
            "Área de garagem ausente em imóvel sem garagem é zero, não desconhecida. "
            "O único registro com porão nulo é um imóvel sem porão."
        ),
    },
    {
        "regra": "Remover os 5 imóveis com área habitável acima de 4.000 pés²",
        "motivo": (
            "Recomendação explícita do autor da base (De Cock, 2011, seção 4): são "
            "vendas parciais de imóveis atípicos que distorcem qualquer análise. "
            "Decisão citável, não arbitrária."
        ),
    },
    {
        "regra": "Derivar 8 atributos (áreas somadas, banheiros equivalentes, idades, flags)",
        "motivo": (
            "Cinco colunas de varanda medem a mesma coisa; separadas, cada uma é "
            "quase toda zero e nenhuma tem poder de separação. Somadas, viram um "
            "atributo com variância útil."
        ),
    },
    {
        "regra": "Manter as vendas não normais (17,7% dos registros)",
        "motivo": (
            "A condição da venda descreve a transação, não o produto. Para "
            "segmentar o imóvel, uma venda entre familiares continua sendo um "
            "imóvel válido. A coluna fica reservada para a análise de sensibilidade."
        ),
    },
]


# --------------------------------------------------------------------------- #
# Camada curada
# --------------------------------------------------------------------------- #


def _aplicar_ausencia_estrutural(dados: pd.DataFrame) -> pd.DataFrame:
    """Converte `NA` em rótulo explícito nas colunas de ausência estrutural."""
    dados = dados.copy()
    for coluna, rotulo in dic.AUSENCIA_ESTRUTURAL.items():
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].fillna(rotulo)
    for coluna, rotulo in dic.AUSENCIA_DESCONHECIDA.items():
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].fillna(rotulo)
    return dados


def _mapear_ordinais(dados: pd.DataFrame) -> pd.DataFrame:
    """Traduz as escalas ordinais para inteiro, com 0 para ausência do item."""
    dados = dados.copy()
    for coluna, escala in dic.ESCALAS_ORDINAIS.items():
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].map(escala).fillna(0).astype("int8")
    return dados


def _corrigir_inconsistencias(dados: pd.DataFrame) -> pd.DataFrame:
    """Corrige os erros de digitação identificados no diagnóstico de qualidade."""
    dados = dados.copy()
    # Um registro traz ano de construção da garagem em 2207 (venda em 2007).
    fora_de_faixa = dados["Garage Yr Blt"] > dados["Yr Sold"]
    dados.loc[fora_de_faixa, "Garage Yr Blt"] = dados.loc[fora_de_faixa, "Year Built"]
    return dados


def _imputar(dados: pd.DataFrame) -> pd.DataFrame:
    """Aplica a estratégia de imputação declarada por coluna."""
    dados = dados.copy()

    # Testada do lote: mediana do bairro (ausência explicada pela geometria).
    mediana_bairro = dados.groupby("Neighborhood")["Lot Frontage"].transform("median")
    dados["Lot Frontage"] = dados["Lot Frontage"].fillna(mediana_bairro)
    dados["Lot Frontage"] = dados["Lot Frontage"].fillna(dados["Lot Frontage"].median())

    # Áreas e contagens de itens que não existem no imóvel.
    zeros = [
        "Mas Vnr Area",
        "BsmtFin SF 1",
        "BsmtFin SF 2",
        "Bsmt Unf SF",
        "Total Bsmt SF",
        "Bsmt Full Bath",
        "Bsmt Half Bath",
        "Garage Cars",
        "Garage Area",
    ]
    for coluna in zeros:
        dados[coluna] = dados[coluna].fillna(0)

    # Sem garagem: o ano da garagem passa a ser o ano da construção da casa,
    # para que a coluna derivada não fique nula. A flag `tem_garagem` preserva
    # a informação de que não há garagem.
    dados["Garage Yr Blt"] = dados["Garage Yr Blt"].fillna(dados["Year Built"])

    # Sistema elétrico: um único registro ausente, imputado pela moda.
    dados["Electrical"] = dados["Electrical"].fillna(dados["Electrical"].mode().iloc[0])
    return dados


def _derivar(dados: pd.DataFrame) -> pd.DataFrame:
    """Constrói os atributos derivados (CRISP-DM 3.3)."""
    dados = dados.copy()
    dados["area_varandas"] = (
        dados["area_deck"]
        + dados["area_varanda_aberta"]
        + dados["area_varanda_fechada"]
        + dados["area_varanda_3estacoes"]
        + dados["area_varanda_tela"]
    )
    dados["banheiros_total"] = (
        dados["banheiros_completos"]
        + 0.5 * dados["lavabos"]
        + dados["banheiros_completos_porao"]
        + 0.5 * dados["lavabos_porao"]
    )
    dados["idade_imovel"] = dados["ano_venda"] - dados["ano_construcao"]
    dados["anos_desde_reforma"] = dados["ano_venda"] - dados["ano_reforma"]
    dados["tem_porao"] = (dados["area_porao"] > 0).astype("int8")
    dados["tem_garagem"] = (dados["area_garagem"] > 0).astype("int8")
    dados["tem_lareira"] = (dados["lareiras"] > 0).astype("int8")
    dados["tem_segundo_pavimento"] = (dados["area_pavimento_superior"] > 0).astype("int8")

    # Idade negativa aparece em imóveis vendidos na planta (venda parcial no
    # ano anterior à conclusão). O piso em zero mantém o registro sem inventar
    # uma idade impossível.
    dados["idade_imovel"] = dados["idade_imovel"].clip(lower=0)
    dados["anos_desde_reforma"] = dados["anos_desde_reforma"].clip(lower=0)

    # Preço por pé² entra apenas na avaliação a posteriori.
    dados["preco_por_pe2"] = dados["preco_venda"] / dados["area_habitavel"]
    return dados


def construir_base_curada(salvar: bool = True) -> pd.DataFrame:
    """Executa a preparação completa e devolve a base curada.

    Args:
        salvar: quando ``True``, grava o parquet em ``data/processed/``.
    """
    bruto = carregar_bruto()
    bruto = _aplicar_ausencia_estrutural(bruto)
    bruto = _corrigir_inconsistencias(bruto)
    bruto = _imputar(bruto)
    bruto = _mapear_ordinais(bruto)

    curada = bruto.rename(columns=dic.RENOMEAR)
    curada = _derivar(curada)

    # Recomendação explícita do autor da base.
    antes = len(curada)
    curada = curada[curada["area_habitavel"] <= 4000].copy()
    curada.attrs["removidos_por_area"] = antes - len(curada)

    curada = curada.reset_index(drop=True)
    if salvar:
        config.garantir_diretorios()
        curada.to_parquet(config.BASE_CURADA, index=False)
    return curada


def construir_matriz_modelagem(curada: pd.DataFrame, salvar: bool = True) -> pd.DataFrame:
    """Recorta a matriz de modelagem — sem rótulo reservado, sem bairro."""
    colunas = (
        dic.IDENTIFICADORES
        + dic.ESPACO_MISTO
        + dic.BINARIAS
        + [dic.RESERVADA_VALIDACAO, dic.ROTULO_RESERVADO]
        + dic.ATRIBUTOS_TRANSACAO
    )
    matriz = curada[colunas].copy()
    if salvar:
        matriz.to_parquet(config.MATRIZ_MODELAGEM, index=False)
    return matriz


def carregar_curada() -> pd.DataFrame:
    """Lê a base curada, construindo-a se ainda não existir."""
    if not config.BASE_CURADA.exists():
        return construir_base_curada()
    return pd.read_parquet(config.BASE_CURADA)


# --------------------------------------------------------------------------- #
# Espaços de atributos — CRISP-DM 3.5 (formatação e escala)
# --------------------------------------------------------------------------- #


def aplicar_log1p(matriz: np.ndarray, indices: list[int]) -> np.ndarray:
    """Aplica `log1p` às colunas indicadas pelos índices.

    Precisa ser uma função de módulo, e não uma função interna: o pipeline é
    serializado com `joblib` para a aplicação, e closure não é serializável.
    """
    saida = np.asarray(matriz, dtype=float).copy()
    if indices:
        saida[:, indices] = np.log1p(saida[:, indices])
    return saida


def _log1p_seletivo(colunas: list[str]) -> FunctionTransformer:
    """Aplica `log1p` apenas onde a assimetria medida na EDA justifica."""
    indices = [colunas.index(c) for c in dic.ASSIMETRICAS if c in colunas]
    return FunctionTransformer(
        aplicar_log1p, kw_args={"indices": indices}, feature_names_out="one-to-one"
    )


ESCALADORES = {
    "sem_escala": "passthrough",
    "minmax": MinMaxScaler(),
    "padrao": StandardScaler(),
    "robusto": RobustScaler(),
}


def construir_preprocessador(
    escalador: str = "padrao", com_nominais: bool = False
) -> Pipeline | ColumnTransformer:
    """Monta o pré-processador do espaço euclidiano.

    Args:
        escalador: uma das chaves de :data:`ESCALADORES`.
        com_nominais: quando ``True``, acrescenta as nominais em *one-hot* —
            usado para demonstrar a diluição do espaço euclidiano.
    """
    if escalador not in ESCALADORES:
        raise ValueError(f"Escalador desconhecido: {escalador}. Use {list(ESCALADORES)}.")

    numericas = dic.NUMERICAS + dic.ORDINAIS + dic.BINARIAS
    passos_numericos = [("log", _log1p_seletivo(numericas))]
    escala = ESCALADORES[escalador]
    if escala != "passthrough":
        # Cada chamada precisa de uma instância própria: o mesmo objeto
        # reaproveitado guardaria as estatísticas do ajuste anterior.
        passos_numericos.append(("escala", type(escala)()))
    ramo_numerico = Pipeline(passos_numericos)

    if not com_nominais:
        return ColumnTransformer(
            [("num", ramo_numerico, numericas)], verbose_feature_names_out=False
        )

    return ColumnTransformer(
        [
            ("num", ramo_numerico, numericas),
            (
                "nom",
                OneHotEncoder(drop="if_binary", handle_unknown="ignore", sparse_output=False),
                dic.NOMINAIS,
            ),
        ],
        verbose_feature_names_out=False,
    )


def preparar_espaco(
    matriz: pd.DataFrame, escalador: str = "padrao", com_nominais: bool = False
) -> tuple[np.ndarray, list[str]]:
    """Aplica o pré-processador e devolve a matriz numérica e os nomes."""
    preprocessador = construir_preprocessador(escalador, com_nominais)
    transformada = preprocessador.fit_transform(matriz)
    nomes = list(preprocessador.get_feature_names_out())
    return np.asarray(transformada, dtype=float), nomes


if __name__ == "__main__":
    base = construir_base_curada()
    modelo = construir_matriz_modelagem(base)
    print(f"Base curada:      {base.shape[0]} × {base.shape[1]}")
    print(f"Removidos (>4000 pés²): {base.attrs.get('removidos_por_area')}")
    print(f"Matriz de modelagem: {modelo.shape[0]} × {modelo.shape[1]}")
    print(f"Nulos remanescentes na matriz: {int(modelo.isna().sum().sum())}")
