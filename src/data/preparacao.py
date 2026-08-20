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
# Limiares da limpeza
# --------------------------------------------------------------------------- #

#: Proporção de ausência a partir da qual a coluna — ou o registro — é
#: descartada em vez de imputada. Acima disso a imputação deixa de completar o
#: dado e passa a inventá-lo: 16,7% de testada de lote imputada pela mediana do
#: bairro é um sexto da coluna produzido pelo próprio método.
LIMIAR_AUSENCIA = 0.05

#: Múltiplo do IQR que define o valor extremo. O 1,5 de Tukey marca um quinto da
#: carteira, incluindo o alto padrão que a segmentação precisa isolar; o 3
#: alcança só a anomalia.
FATOR_EXTREMO = 3.0

#: Concentração num único valor a partir da qual a coluna não informa nada.
LIMIAR_CONCENTRACAO = 99.0

#: Colunas que a regra de concentração não remove: são o esqueleto da base
#: curada e da matriz de modelagem.
COLUNAS_PROTEGIDAS = set(
    dic.IDENTIFICADORES
    + dic.ESPACO_MISTO
    + dic.BINARIAS
    + dic.ATRIBUTOS_TRANSACAO
    + [dic.ROTULO_RESERVADO, dic.RESERVADA_VALIDACAO]
)

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
        "regra": "Alinhar `ano_reforma` ao `ano_construcao` quando a ordem está invertida",
        "motivo": (
            "Um imóvel construído em 2002 aparece com reforma em 2001. Reforma "
            "anterior à construção não existe; sem o alinhamento, o imóvel fica com "
            "mais anos desde a reforma do que anos de vida."
        ),
    },
    {
        "regra": "Converter `tipo_garagem` em `SemGaragem` no registro sem medida de garagem",
        "motivo": (
            "Um registro declara garagem separada (`Detchd`) e deixa área, vagas, ano "
            "e as duas notas em branco. Sem medida não há garagem para descrever, e "
            "manter o tipo produziria um imóvel com garagem de área zero."
        ),
    },
    {
        "regra": "Descartar coluna e registro com mais de 5% de ausência real",
        "motivo": (
            "Acima de 5% a imputação deixa de completar o dado e passa a produzi-lo. "
            "Saem `testada_lote` (16,7%) e `ano_garagem` (5,4%) — nenhuma das duas "
            "no espaço de atributos — e um registro com seis campos de porão vazios. "
            "O corte roda depois da ausência estrutural: antes dela, um imóvel sem "
            "piscina, sem viela e sem cerca cairia por não ter o que nunca existiu."
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
        "regra": "Remover os valores extremos, além de 3×IQR em qualquer atributo",
        "motivo": (
            "A cerca clássica de Tukey (1,5×IQR) marca 21,7% da carteira e levaria "
            "junto o segmento de alto padrão que a segmentação existe para isolar. O "
            "fator 3 alcança só a anomalia: 76 registros."
        ),
    },
    {
        "regra": "Remover as vendas não normais",
        "motivo": (
            "Leilão, venda entre familiares e imóvel entregue antes da conclusão do "
            "cadastro têm preço que não descreve o produto. Sem elas, preço e "
            "condição de venda deixam de medir coisas diferentes."
        ),
    },
    {
        "regra": "Remover os cadastros sem dormitório acima do solo e sem banheiro completo",
        "motivo": (
            "São imóveis reais — o dormitório fica no porão em split foyer, split "
            "level e duplex —, mas descrevem um produto que não é comparável ao "
            "resto da carteira em nenhum dos atributos de tamanho."
        ),
    },
    {
        "regra": "Descartar as colunas concentradas acima de 99% num único valor",
        "motivo": (
            "Coluna em que 99% dos imóveis dizem a mesma coisa não separa ninguém e "
            "tem variância quase nula na padronização. As colunas do esqueleto da "
            "base ficam mesmo assim: `condicao_venda` vira constante porque a "
            "depuração deixou só as vendas normais, e a matriz de modelagem a exige."
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

    # Um registro traz reforma em 2001 e construção em 2002: a ordem dos dois
    # anos está invertida. Sem correção, `anos_desde_reforma` sai maior que a
    # idade do imóvel — reforma feita antes de existir casa para reformar.
    reforma_invertida = dados["Year Remod/Add"] < dados["Year Built"]
    dados.loc[reforma_invertida, "Year Remod/Add"] = dados.loc[reforma_invertida, "Year Built"]

    # Um registro declara garagem separada (`Detchd`) sem nenhuma medida: área,
    # vagas, ano e as duas notas vêm todos vazios. As demais colunas do bloco já
    # foram rotuladas como `SemGaragem` pela ausência estrutural; deixar só o
    # tipo preenchido criaria imóvel com garagem de área zero.
    garagem_sem_medida = (
        dados["Garage Type"].ne(dic.AUSENCIA_ESTRUTURAL["Garage Type"])
        & dados["Garage Area"].isna()
        & dados["Garage Cars"].isna()
        & dados["Garage Yr Blt"].isna()
    )
    dados.loc[garagem_sem_medida, "Garage Type"] = dic.AUSENCIA_ESTRUTURAL["Garage Type"]
    return dados


def _imputar(dados: pd.DataFrame) -> pd.DataFrame:
    """Imputa o que sobrou depois do corte de ausência, sempre abaixo de 1%.

    Só chega aqui coluna que passou por :func:`_remover_por_ausencia`, isto é,
    coluna com menos de 5% de vazio. Nesse volume a imputação não desloca a
    distribuição, e a estratégia é declarada por coluna.
    """
    dados = dados.copy()

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
        if coluna in dados.columns:
            dados[coluna] = dados[coluna].fillna(0)

    # Sistema elétrico: um único registro ausente, imputado pela moda.
    dados["Electrical"] = dados["Electrical"].fillna(dados["Electrical"].mode().iloc[0])
    return dados


def _remover_por_ausencia(dados: pd.DataFrame) -> pd.DataFrame:
    """Descarta coluna e registro cuja ausência passa de :data:`LIMIAR_AUSENCIA`.

    A ordem importa: a coluna sai primeiro, e o corte por registro roda sobre o
    que restou. Registro que só era ruim por causa de uma coluna descartada
    deixa de ser ruim quando ela sai.

    A regra roda **depois** de :func:`_aplicar_ausencia_estrutural`. Antes dela,
    um imóvel sem piscina, sem viela e sem cerca teria 17% de vazio e cairia por
    não ter o que nunca existiu.
    """
    dados = dados.copy()

    proporcao_coluna = dados.isna().mean()
    colunas_fora = list(proporcao_coluna[proporcao_coluna > LIMIAR_AUSENCIA].index)
    dados = dados.drop(columns=colunas_fora)

    proporcao_registro = dados.isna().mean(axis=1)
    dados = dados[proporcao_registro <= LIMIAR_AUSENCIA]

    dados.attrs["colunas_removidas_por_ausencia"] = colunas_fora
    dados.attrs["registros_removidos_por_ausencia"] = int(
        (proporcao_registro > LIMIAR_AUSENCIA).sum()
    )
    return dados


def _depurar_carteira(curada: pd.DataFrame) -> pd.DataFrame:
    """Remove da carteira o que não descreve um imóvel residencial comparável.

    Três cortes, nesta ordem — cada um medido sobre a base como ela está quando
    o corte roda:

    1. **extremos** além de :data:`FATOR_EXTREMO`×IQR em qualquer variável do
       espaço de atributos. O fator 3, e não o 1,5 de Tukey, é deliberado: a
       cerca clássica levaria junto um quinto da carteira, incluindo o segmento
       de alto padrão que a segmentação existe para isolar;
    2. **vendas não normais** — leilão, venda entre familiares, imóvel entregue
       antes da conclusão do cadastro. O preço dessas transações não descreve o
       produto;
    3. **cadastros implausíveis** — sem dormitório acima do solo e sem banheiro
       completo.
    """
    atributos = [c for c in dic.NUMERICAS + dic.ORDINAIS if c in curada.columns]

    fora_da_cerca = pd.Series(False, index=curada.index)
    for coluna in atributos:
        q1, q3 = curada[coluna].quantile([0.25, 0.75])
        iqr = q3 - q1
        limites = (q1 - FATOR_EXTREMO * iqr, q3 + FATOR_EXTREMO * iqr)
        fora_da_cerca |= (curada[coluna] < limites[0]) | (curada[coluna] > limites[1])
    curada = curada[~fora_da_cerca]

    curada = curada[curada["condicao_venda"] == "Normal"]

    implausivel = (curada["dormitorios"] == 0) | (
        curada["banheiros_completos"] + curada["banheiros_completos_porao"] == 0
    )
    return curada[~implausivel]


def _remover_colunas_sem_informacao(curada: pd.DataFrame) -> pd.DataFrame:
    """Descarta coluna concentrada acima de :data:`LIMIAR_CONCENTRACAO` num valor.

    Coluna em que 99% dos imóveis dizem a mesma coisa não separa ninguém e tem
    variância quase nula na padronização.

    As colunas declaradas em :data:`COLUNAS_PROTEGIDAS` ficam mesmo quando
    passam do limiar: `condicao_venda` vira constante justamente **porque** a
    depuração deixou só as vendas normais, e o esquema da matriz de modelagem
    depende dela.
    """
    concentracao = {}
    for coluna in curada.columns:
        preenchida = curada[coluna].dropna()
        if not len(preenchida):
            continue
        concentracao[coluna] = 100 * preenchida.value_counts(normalize=True).iloc[0]

    descartar = [
        coluna
        for coluna, pct in concentracao.items()
        if pct >= LIMIAR_CONCENTRACAO and coluna not in COLUNAS_PROTEGIDAS
    ]
    return curada.drop(columns=descartar)


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

    A ordem dos passos é a do notebook `02-ajustes-dados`, que narra cada
    decisão. Os dois precisam produzir a mesma tabela, e o notebook confere isso
    célula a célula na última seção.

    Args:
        salvar: quando ``True``, grava o parquet em ``data/processed/``.
    """
    bruto = carregar_bruto()
    bruto = _aplicar_ausencia_estrutural(bruto)
    bruto = _corrigir_inconsistencias(bruto)
    bruto = _remover_por_ausencia(bruto)
    bruto = _imputar(bruto)
    bruto = _mapear_ordinais(bruto)

    curada = bruto.rename(columns=dic.RENOMEAR)
    curada = _derivar(curada)

    # Recomendação explícita do autor da base.
    antes = len(curada)
    curada = curada[curada["area_habitavel"] <= 4000].copy()
    curada.attrs["removidos_por_area"] = antes - len(curada)

    # Depuração da carteira: extremos, vendas não normais e cadastros
    # implausíveis saem; depois disso a coluna que virou constante sai também.
    antes = len(curada)
    curada = _depurar_carteira(curada)
    curada.attrs["removidos_na_depuracao"] = antes - len(curada)

    colunas = list(curada.columns)
    curada = _remover_colunas_sem_informacao(curada)
    curada.attrs["colunas_sem_informacao"] = [c for c in colunas if c not in curada.columns]

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
