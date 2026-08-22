"""Aplicação Streamlit que identifica o grupo de um imóvel.

A tela consome o modelo treinado no notebook `08_modelagem_bonus.ipynb`:
`models/model_bonus_imoveis_k_means.joblib`. É um `Pipeline` do scikit-learn com
duas etapas — o pré-processamento (normalização e codificação) e o k-means com
3 grupos. O usuário preenche o formulário, clica em **Identificar grupo** e a
tela mostra o grupo devolvido pelo modelo.

Execute com::

    uv run streamlit run app/app_imobiliario.py
"""

from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_MODELO = RAIZ / "models" / "model_bonus_imoveis_k_means.joblib"
CAMINHO_DADOS = RAIZ / "data" / "processed" / "imoveis_curados.parquet"

#: Colunas que o notebook 08 deixou de fora da modelagem.
FORA_DA_MODELAGEM = ["ordem", "pid"]


def silhouette_scorer(estimator, X, y=None):
    """Espaço reservado para a métrica de silhueta usada no treino.

    O modelo foi salvo dentro de um `GridSearchCV`, que guarda a referência à
    função de avaliação. O `joblib` precisa reencontrá-la com este nome ao
    reabrir o arquivo. Ela não é chamada na predição.
    """
    raise NotImplementedError("A silhueta é calculada no notebook, não na tela.")


@st.cache_resource
def carregar_modelo():
    """Lê o pipeline treinado uma única vez por processo."""
    return joblib.load(CAMINHO_MODELO)


@st.cache_data
def carregar_dados():
    """A base curada, sem as colunas que ficaram fora da modelagem."""
    return pd.read_parquet(CAMINHO_DADOS).drop(columns=FORA_DA_MODELAGEM)


MODELO = carregar_modelo()
DADOS = carregar_dados()


def imovel_tipico():
    """Uma linha com todas as colunas que o modelo espera, no valor típico de cada uma.

    O modelo foi treinado com 81 colunas, mas o formulário pergunta apenas 10.
    As demais entram com a mediana (números) ou com o valor mais frequente (texto).
    """
    valores = {
        coluna: DADOS[coluna].median()
        if pd.api.types.is_numeric_dtype(DADOS[coluna])
        else DADOS[coluna].mode()[0]
        for coluna in DADOS.columns
    }
    return pd.DataFrame([valores])


TIPICO = imovel_tipico()


def seletor(rotulo, coluna):
    """Uma caixa de seleção com as categorias da base, já posicionada no valor típico."""
    categorias = sorted(DADOS[coluna].unique())
    return st.selectbox(rotulo, categorias, index=categorias.index(TIPICO.loc[0, coluna]))


def numero(rotulo, coluna, minimo, maximo, passo=1):
    """Um campo numérico já preenchido com o valor típico da coluna."""
    return st.number_input(rotulo, minimo, maximo, int(TIPICO.loc[0, coluna]), step=passo)


st.set_page_config(page_title="Grupos de imóveis", page_icon="🏘️")
st.title("🏘️ Identificação de grupos de imóveis")
st.write("Preencha os dados do imóvel e descubra a qual grupo ele pertence.")

with st.form("formulario"):
    esquerda, direita = st.columns(2)

    with esquerda:
        st.subheader("Terreno e idade")
        bairro = seletor("Bairro", "bairro")
        zoneamento = seletor("Zoneamento", "zoneamento")
        estilo = seletor("Estilo da construção", "estilo")
        ano_construcao = numero("Ano de construção", "ano_construcao", 1870, 2010)
        ano_reforma = numero("Ano da última reforma", "ano_reforma", 1870, 2010)

    with direita:
        st.subheader("Construção")
        fundacao = seletor("Fundação", "fundacao")
        revestimento = seletor("Revestimento externo", "revestimento_1")
        garagem = seletor("Tipo de garagem", "tipo_garagem")
        area_habitavel = numero("Área habitável (pé²)", "area_habitavel", 300, 6000, passo=50)
        qualidade = st.slider("Qualidade geral", 1, 10, int(TIPICO.loc[0, "qualidade_geral"]))

    enviado = st.form_submit_button("Identificar grupo", type="primary")

if enviado:
    respostas = {
        "bairro": bairro,
        "zoneamento": zoneamento,
        "estilo": estilo,
        "ano_construcao": ano_construcao,
        "ano_reforma": ano_reforma,
        "fundacao": fundacao,
        "revestimento_1": revestimento,
        "tipo_garagem": garagem,
        "area_habitavel": area_habitavel,
        "qualidade_geral": qualidade,
    }

    imovel = TIPICO.copy()
    for coluna, valor in respostas.items():
        imovel.loc[0, coluna] = valor

    # A curadoria derivou estas duas colunas dos anos; a tela refaz a mesma conta.
    imovel.loc[0, "idade_imovel"] = imovel.loc[0, "ano_venda"] - ano_construcao
    imovel.loc[0, "anos_desde_reforma"] = imovel.loc[0, "ano_venda"] - ano_reforma

    grupo = MODELO.predict(imovel)[0]
    st.success(f"Este imóvel pertence ao **Grupo {grupo}**.")
