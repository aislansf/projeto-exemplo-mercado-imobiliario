"""Leitura dos artefatos gravados pelos notebooks e classificação de imóveis.

A aplicação consome o que os notebooks 00 a 05 deixam em disco:

* ``models/selecionado.json`` e o ``.joblib`` que ele aponta (notebook 04-0);
* ``data/processed/segmentos.csv`` — o segmento de cada imóvel da carteira (04-0);
* ``data/processed/ames_housing_tratado.csv`` — a base curada (02);
* ``data/processed/dicionario.csv`` e ``escala.csv`` — tipos e níveis ordinais (00);
* ``data/processed/ames_housing_preprocessed.csv`` — a saída do 03, usada só para
  conferir que o pré-processamento reconstruído aqui é o mesmo do treino.

Opcionais — quando existem, a tela mostra; quando não, segue sem eles:

* ``ames_housing_pca.csv`` e ``ames_housing_umap.csv`` (04-2) — o mapa da carteira;
* ``regras_associacao.csv`` (04-3) — as regras fortes;
* ``reports/05-avaliacao.json`` (05) — critérios de sucesso e cenários financeiros.

O roteiro de classificação é o do notebook 06: o pré-processador é reajustado na
base curada com as mesmas regras do 03, o imóvel novo é completado pelo imóvel
mais parecido da carteira e o segmento sai do ``predict`` do modelo — ou, quando
o modelo não classifica imóveis novos, do centroide mais próximo.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder

from src import config

#: Colunas que não entram no modelo: identificadores, o rótulo reservado e um código.
FORA = ["ordem", "pid", "preco_venda", "subclasse"]

#: Atributos criados no notebook 02 que o 03 trata como numéricos.
DERIVADAS = [
    "area_varandas",
    "banheiros_total",
    "idade_imovel",
    "anos_desde_reforma",
    "tem_porao",
    "tem_garagem",
    "tem_lareira",
    "tem_segundo_pavimento",
    "foi_reformada",
]

#: Arquivo, notebook que o grava e se a tela depende dele para subir.
ARQUIVOS = {
    "selecionado": (config.MODELS / "selecionado.json", "04-0", True),
    "segmentos": (config.DATA_PROCESSED / "segmentos.csv", "04-0", True),
    "base": (config.DATA_PROCESSED / "ames_housing_tratado.csv", "02", True),
    "dicionario": (config.DATA_PROCESSED / "dicionario.csv", "00", True),
    "escala": (config.DATA_PROCESSED / "escala.csv", "00", True),
    "preprocessada": (config.DATA_PROCESSED / "ames_housing_preprocessed.csv", "03", True),
    "pca": (config.DATA_PROCESSED / "ames_housing_pca.csv", "04-2", False),
    "umap": (config.DATA_PROCESSED / "ames_housing_umap.csv", "04-2", False),
    "regras": (config.DATA_PROCESSED / "regras_associacao.csv", "04-3", False),
    "avaliacao": (config.REPORTS / "05-avaliacao.json", "05", False),
}


class ArtefatosAusentes(FileNotFoundError):
    """Algum arquivo obrigatório ainda não foi gravado pelos notebooks."""


@dataclass
class Artefatos:
    """Tudo o que a tela precisa, já lido, alinhado e pronto para classificar."""

    selecionado: dict[str, Any]
    modelo: Any
    base: pd.DataFrame
    dicionario: pd.DataFrame
    continuas: list[str]
    ordinais: list[str]
    nominais: list[str]
    niveis: dict[str, list]
    preprocessador: ColumnTransformer
    X: pd.DataFrame
    rotulos: np.ndarray
    nomes: dict[int, str]
    centros: pd.DataFrame
    confere_com_03: bool
    concordancia: float | None
    opcionais: dict[str, Any] = field(default_factory=dict)

    @property
    def colunas_de_entrada(self) -> list[str]:
        """Colunas que um imóvel pode informar: as da base, menos identificadores."""
        return [c for c in self.base.columns if c not in ("ordem", "pid")]

    @property
    def classifica_novos(self) -> bool:
        """``True`` quando o próprio modelo atribui o segmento (``predict``)."""
        return hasattr(self.modelo, "predict")

    @cached_property
    def categorias(self) -> dict[str, set]:
        """Valores válidos de cada coluna de texto da base curada."""
        return {
            c: set(self.base[c].dropna())
            for c in self.colunas_de_entrada
            if not pd.api.types.is_numeric_dtype(self.base[c])
        }

    @property
    def segmentos(self) -> list[str]:
        """Nomes dos segmentos, do preço mediano mais alto ao mais baixo."""
        return [self.nomes[r] for r in sorted(self.nomes) if r >= 0]


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #


def arquivos_ausentes() -> list[tuple[str, str]]:
    """Arquivos obrigatórios que ainda não existem, com o notebook que os grava."""
    return [
        (str(caminho.relative_to(config.RAIZ)), notebook)
        for caminho, notebook, obrigatorio in ARQUIVOS.values()
        if obrigatorio and not caminho.exists()
    ]


def _ler_csv(nome: str, **opcoes: Any) -> pd.DataFrame:
    return pd.read_csv(ARQUIVOS[nome][0], sep=";", encoding="utf-8", **opcoes)


def _ler_opcionais() -> dict[str, Any]:
    opcionais: dict[str, Any] = {}
    for nome in ("pca", "umap", "regras"):
        if ARQUIVOS[nome][0].exists():
            opcionais[nome] = _ler_csv(nome)
    caminho = ARQUIVOS["avaliacao"][0]
    if caminho.exists() and caminho.stat().st_size > 0:
        try:
            opcionais["avaliacao"] = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass  # gravação interrompida: a tela segue sem a avaliação
    return opcionais


def carregar() -> Artefatos:
    """Lê os artefatos dos notebooks e reconstrói o espaço do modelo.

    Raises:
        ArtefatosAusentes: algum arquivo obrigatório não existe — rode os notebooks.
    """
    ausentes = arquivos_ausentes()
    if ausentes:
        lista = ", ".join(f"{caminho} (notebook {nb})" for caminho, nb in ausentes)
        raise ArtefatosAusentes(f"Arquivos ainda não gravados: {lista}")

    selecionado = json.loads(ARQUIVOS["selecionado"][0].read_text(encoding="utf-8"))
    try:
        modelo = joblib.load(config.MODELS / selecionado["arquivo"])
    except Exception:  # noqa: BLE001 - k-medianas/k-medoides só carregam no notebook
        modelo = None

    base = _ler_csv("base")
    dicionario = _ler_csv("dicionario")
    escala = _ler_csv("escala", dtype={"nivel": str}).sort_values(["coluna", "ordem"])
    escalas = escala.groupby("coluna")["nivel"].apply(list).to_dict()

    def colunas_do_tipo(*tipos: str) -> list[str]:
        colunas = dicionario.loc[dicionario["Tipo"].isin(tipos), "variavel"]
        return [c for c in colunas if c in base.columns and c not in FORA]

    continuas = list(
        dict.fromkeys(colunas_do_tipo("Contínua", "Discreta") + [c for c in DERIVADAS if c in base])
    )
    ordinais = colunas_do_tipo("Ordinal")
    nominais = colunas_do_tipo("Nominal")

    niveis: dict[str, list] = {}
    for col in ordinais:  # mesma regra de codificação do 03
        escala_col = escalas[col]
        if pd.api.types.is_numeric_dtype(base[col]):
            escala_col = pd.to_numeric(pd.Series(escala_col)).tolist()
        ausencia = [
            v
            for v in base[col].unique()
            if isinstance(v, str) and v.startswith("Sem ") and v not in escala_col
        ]
        niveis[col] = ausencia + escala_col  # "Sem porão", "Sem garagem"… é o menor nível

    entrada = base.drop(columns=["ordem", "pid"], errors="ignore")
    preprocessador = ColumnTransformer(
        [
            ("continuous", MinMaxScaler(), continuas),
            ("ordinal", MinMaxScaler(), ordinais),
            (
                "nominal",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                nominais,
            ),
        ],
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")
    X = preprocessador.fit_transform(_codificar(entrada, ordinais, niveis))

    saida_03 = _ler_csv("preprocessada").drop(columns=FORA, errors="ignore")
    confere = list(X.columns) == list(saida_03.columns) and np.allclose(X, saida_03)

    rotulos = _ler_csv("segmentos")["segmento"].to_numpy()
    if len(rotulos) != len(base):
        raise ValueError(
            f"segmentos.csv tem {len(rotulos)} linhas e a base curada {len(base)}: "
            "rode de novo o notebook 04-0."
        )
    validos = rotulos >= 0

    # Nomes do 05 e do 06: Segmento A é o de preço mediano mais alto.
    ordem = (
        pd.Series(base["preco_venda"].to_numpy()[validos], index=rotulos[validos])
        .groupby(level=0)
        .median()
        .sort_values(ascending=False)
        .index
    )
    nomes = {int(s): f"Segmento {chr(65 + i)}" for i, s in enumerate(ordem)} | {-1: "Sem segmento"}

    centros = getattr(modelo, "cluster_centers_", None)
    if centros is not None and np.shape(centros)[1] == X.shape[1]:
        centros = pd.DataFrame(centros, columns=X.columns)
    else:  # sem centros no modelo: a média de cada segmento faz o papel
        centros = X[validos].groupby(rotulos[validos]).mean()

    concordancia = None
    if hasattr(modelo, "predict"):
        concordancia = float((modelo.predict(X.to_numpy()) == rotulos).mean())

    return Artefatos(
        selecionado=selecionado,
        modelo=modelo,
        base=base,
        dicionario=dicionario,
        continuas=continuas,
        ordinais=ordinais,
        nominais=nominais,
        niveis=niveis,
        preprocessador=preprocessador,
        X=X,
        rotulos=rotulos,
        nomes=nomes,
        centros=centros,
        confere_com_03=bool(confere),
        concordancia=concordancia,
        opcionais=_ler_opcionais(),
    )


# --------------------------------------------------------------------------- #
# Espaço do modelo
# --------------------------------------------------------------------------- #


def _codificar(dados: pd.DataFrame, ordinais: list[str], niveis: dict[str, list]) -> pd.DataFrame:
    """Troca cada nível ordinal pela sua posição na escala (0, 1, 2…)."""
    dados = dados.copy()
    for col in ordinais:
        codigos = pd.Categorical(dados[col], categories=niveis[col], ordered=True).codes
        if (codigos < 0).any():
            raise ValueError(f"{col}: valor fora da escala. Use um destes: {niveis[col]}")
        dados[col] = codigos
    return dados


def transformar(art: Artefatos, entrada: pd.DataFrame) -> np.ndarray:
    """Leva registros da base curada para o espaço em que o modelo foi treinado."""
    codificada = _codificar(entrada[art.colunas_de_entrada], art.ordinais, art.niveis)
    return art.preprocessador.transform(codificada).to_numpy()


def distancias(art: Artefatos, matriz: np.ndarray) -> pd.DataFrame:
    """Distância euclidiana de cada registro até o centro de cada segmento."""
    centros = art.centros.to_numpy()
    valores = np.linalg.norm(matriz[:, None, :] - centros[None, :, :], axis=2)
    return pd.DataFrame(valores, columns=[art.nomes[int(r)] for r in art.centros.index])


def atribuir(art: Artefatos, matriz: np.ndarray) -> np.ndarray:
    """Rótulo cru de cada registro: ``predict`` do modelo ou centro mais próximo."""
    if art.classifica_novos:
        return np.asarray(art.modelo.predict(matriz))
    return art.centros.index.to_numpy()[distancias(art, matriz).to_numpy().argmin(axis=1)]


def razao_de_fronteira(tabela: pd.DataFrame) -> np.ndarray:
    """Menor distância ÷ segunda menor. Perto de 1, o imóvel está entre dois segmentos."""
    ordenadas = np.sort(tabela.to_numpy(), axis=1)
    if ordenadas.shape[1] < 2:
        return np.zeros(len(ordenadas))
    return np.divide(
        ordenadas[:, 0],
        ordenadas[:, 1],
        out=np.zeros(len(ordenadas)),
        where=ordenadas[:, 1] > 0,
    )


# --------------------------------------------------------------------------- #
# Carteira
# --------------------------------------------------------------------------- #


def carteira(art: Artefatos) -> pd.DataFrame:
    """A base curada com o segmento publicado e a razão de fronteira de cada imóvel."""
    tabela = distancias(art, art.X.to_numpy())
    return art.base.assign(
        segmento=[art.nomes[int(r)] for r in art.rotulos],
        razao_de_fronteira=np.round(razao_de_fronteira(tabela), 4),
    )


def perfil(art: Artefatos) -> pd.DataFrame:
    """Tamanho, valor de venda e medianas de negócio de cada segmento."""
    dados = carteira(art)
    total_vgv = dados["preco_venda"].sum()
    resumo = dados.groupby("segmento").agg(
        imoveis=("preco_venda", "size"),
        vgv=("preco_venda", "sum"),
        preco_mediano=("preco_venda", "median"),
        area_habitavel=("area_habitavel", "median"),
        qualidade_geral=("qualidade_geral", "median"),
        idade_imovel=("idade_imovel", "median"),
        razao_mediana=("razao_de_fronteira", "median"),
    )
    resumo["pct_carteira"] = 100 * resumo["imoveis"] / len(dados)
    resumo["pct_vgv"] = 100 * resumo["vgv"] / total_vgv
    return resumo.sort_values("preco_mediano", ascending=False)


def assinatura(art: Artefatos, colunas: list[str]) -> pd.DataFrame:
    """Desvios-padrão entre a mediana de cada segmento e a mediana da carteira."""
    dados = carteira(art)
    numericas = [c for c in colunas if pd.api.types.is_numeric_dtype(dados[c])]
    desvio = dados[numericas].std().replace(0, 1)
    medianas = dados.groupby("segmento")[numericas].median()
    return ((medianas - dados[numericas].median()) / desvio).loc[
        [s for s in art.segmentos if s in medianas.index]
    ]


# --------------------------------------------------------------------------- #
# Imóveis novos
# --------------------------------------------------------------------------- #


def _vazio(valor: Any) -> bool:
    return valor is None or valor == "" or (isinstance(valor, float) and np.isnan(valor))


def validar(art: Artefatos, imovel: Mapping[str, Any]) -> None:
    """Recusa coluna desconhecida e categoria que o modelo nunca viu."""
    desconhecidas = set(imovel) - set(art.colunas_de_entrada)
    if desconhecidas:
        raise ValueError(f"Colunas que não existem na base curada: {sorted(desconhecidas)}")
    for col, valor in imovel.items():
        if col in art.ordinais:
            if valor not in art.niveis[col]:
                raise ValueError(f'{col}: "{valor}" fora da escala. Válidos: {art.niveis[col]}')
        elif col in art.categorias and valor not in art.categorias[col]:
            validos = sorted(map(str, art.categorias[col]))
            raise ValueError(f'{col}: "{valor}" não existe na base. Válidos: {validos}')


def mais_parecido(art: Artefatos, imovel: Mapping[str, Any]) -> pd.Series:
    """Imóvel da carteira com as categorias informadas e os números mais próximos.

    As categorias filtram a carteira uma a uma, na ordem em que foram
    informadas; uma combinação que nenhum imóvel tem deixa de filtrar, em vez de
    travar a classificação. O valor informado vale de qualquer forma — o vizinho
    só empresta os campos que ficaram em branco.
    """
    candidatos = art.base
    for col, valor in imovel.items():
        if col in art.categorias:
            filtrados = candidatos[candidatos[col] == valor]
            if not filtrados.empty:
                candidatos = filtrados
    informadas = [c for c in imovel if c not in art.categorias]
    if not informadas:
        return candidatos.iloc[0]
    amplitude = (art.base[informadas].max() - art.base[informadas].min()).replace(0, 1)
    alvo = pd.Series(imovel)[informadas].astype(float)
    distancia = ((candidatos[informadas] - alvo).abs() / amplitude).sum(axis=1)
    return candidatos.loc[distancia.idxmin()]


def _completar(art: Artefatos, imovel: Mapping[str, Any]) -> tuple[dict[str, Any], Any]:
    """Valida o imóvel e completa o que faltar pelo vizinho mais parecido."""
    validar(art, imovel)
    if set(art.colunas_de_entrada) <= set(imovel):  # nada a completar
        return dict(imovel), None
    vizinho = mais_parecido(art, imovel)
    return {**vizinho.to_dict(), **imovel}, vizinho.get("pid")


def _segmentar(
    art: Artefatos, registros: list[dict[str, Any]]
) -> tuple[pd.DataFrame, list, pd.DataFrame]:
    """Transforma os registros completos de uma vez e atribui o segmento."""
    entrada = pd.DataFrame(registros, columns=art.base.columns)
    entrada = entrada.astype({c: art.base[c].dtype for c in art.colunas_de_entrada})
    matriz = transformar(art, entrada)
    rotulos = [art.nomes[int(r)] for r in atribuir(art, matriz)]
    return entrada, rotulos, distancias(art, matriz)


def informados(imovel: Mapping[str, Any]) -> dict[str, Any]:
    """Só os campos preenchidos — vazio, ``None`` e ``NaN`` ficam para o vizinho."""
    return {c: v for c, v in imovel.items() if not _vazio(v)}


def classificar(art: Artefatos, imovel: Mapping[str, Any]) -> dict[str, Any]:
    """Classifica um imóvel e devolve o segmento com a leitura de cada distância."""
    imovel = informados(imovel)
    registro, vizinho = _completar(art, imovel)
    entrada, rotulos, tabela = _segmentar(art, [registro])
    ordem = tabela.iloc[0].sort_values()
    return {
        "segmento": rotulos[0],
        "segundo_mais_proximo": next(s for s in ordem.index if s != rotulos[0]),
        "razao_de_fronteira": round(float(razao_de_fronteira(tabela)[0]), 4),
        "distancias": ordem.to_dict(),
        "registro": entrada.iloc[0].to_dict(),
        "informados": list(imovel),
        "completados": [c for c in art.colunas_de_entrada if c not in imovel],
        "vizinho": vizinho,
    }


def classificar_lote(art: Artefatos, dados: pd.DataFrame) -> pd.DataFrame:
    """Classifica um lote; colunas extras seguem no resultado.

    Linha com categoria desconhecida ou valor fora da escala não derruba o lote:
    sai sem segmento e com o motivo na coluna ``erro``.
    """
    conhecidas = [c for c in dados.columns if c in art.colunas_de_entrada]
    registros, vizinhos, erros, aceitas = [], [], [], []
    for posicao, linha in enumerate(dados[conhecidas].to_dict(orient="records")):
        try:
            registro, vizinho = _completar(art, informados(linha))
        except ValueError as erro:
            vizinhos.append(None)
            erros.append(str(erro))
            continue
        registros.append(registro)
        vizinhos.append(vizinho)
        erros.append("")
        aceitas.append(posicao)

    segmentos = np.full(len(dados), None, dtype=object)
    razoes = np.full(len(dados), np.nan)
    if registros:
        _, rotulos, tabela = _segmentar(art, registros)
        segmentos[aceitas] = rotulos
        razoes[aceitas] = np.round(razao_de_fronteira(tabela), 4)
    return dados.assign(
        segmento=segmentos,
        razao_de_fronteira=razoes,
        pid_de_referencia=pd.array(vizinhos, dtype="Int64"),
        erro=erros,
    )
