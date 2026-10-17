"""Aplicação Streamlit que consome os artefatos gravados pelos notebooks.

A tela lê o que os notebooks 00 a 05 deixam em disco — o modelo vencedor do 04-0
(``models/selecionado.json`` e o ``.joblib`` que ele aponta), os segmentos da
carteira, a base curada, o dicionário e as escalas ordinais. Os resultados do
04-2 (PCA e UMAP), do 04-3 (regras de associação) e do 05 (avaliação) entram
quando existem. A lista completa e o notebook que grava cada arquivo estão em
:data:`src.app.artefatos.ARQUIVOS`.

Execute com::

    uv run invoke app
    # ou
    uv run streamlit run src/app/app.py

As sete abas seguem o caminho de quem usa: primeiro o resultado do modelo, depois
a classificação de um imóvel, o perfil dos segmentos, a carteira, o lote, as
regras de associação e, por último, a procedência dos arquivos.
"""

from __future__ import annotations

import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# A aplicação roda tanto com o projeto instalado (``uv run``) quanto a partir de
# um clone cru, em que ``streamlit run`` só coloca ``src/app`` no path.
if __package__ in (None, ""):  # pragma: no cover - caminho de execução direta
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import config  # noqa: E402
from src.app import artefatos as art  # noqa: E402

st.set_page_config(
    page_title="Meridiano · Segmentação da carteira",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

#: Campos do formulário, agrupados como o corretor pensa o imóvel. Campo que não
#: existir na base curada some do formulário sem quebrar a tela.
GRUPOS = {
    "Áreas (pé²)": {
        "area_habitavel": "Área habitável",
        "area_porao": "Área do porão",
        "area_terreno": "Área do terreno",
        "area_garagem": "Área da garagem",
        "area_varandas": "Área de varandas",
    },
    "Distribuição interna": {
        "comodos": "Cômodos",
        "dormitorios": "Dormitórios",
        "banheiros_total": "Banheiros (total)",
        "lareiras": "Lareiras",
        "vagas_garagem": "Vagas de garagem",
    },
    "Idade": {
        "idade_imovel": "Idade do imóvel (anos)",
        "anos_desde_reforma": "Anos desde a reforma",
    },
    "Qualidade e conservação": {
        "qualidade_geral": "Qualidade geral",
        "conservacao_geral": "Conservação geral",
        "qualidade_cozinha": "Qualidade da cozinha",
        "qualidade_porao": "Qualidade do porão",
        "acabamento_garagem": "Acabamento da garagem",
    },
    "Localização e tipo": {
        "bairro": "Bairro",
        "zoneamento": "Zoneamento",
        "tipo_construcao": "Tipo de construção",
        "estilo": "Estilo",
        "ar_central": "Ar-condicionado central",
    },
    "O imóvel tem": {
        "tem_porao": "Porão",
        "tem_garagem": "Garagem",
        "tem_lareira": "Lareira",
        "tem_segundo_pavimento": "Segundo pavimento",
        "foi_reformada": "Reforma",
    },
}
BINARIAS = set(GRUPOS["O imóvel tem"])
ROTULOS = {campo: rotulo for grupo in GRUPOS.values() for campo, rotulo in grupo.items()}

CSS = f"""
<style>
    .cartao-segmento {{
        border-left: 8px solid var(--cor); border-radius: 8px;
        padding: 1rem 1.2rem; margin: .2rem 0 1rem 0;
        background: rgba(27, 73, 101, 0.06);
    }}
    .cartao-segmento h2 {{ margin: 0; color: {config.AZUL_PROFUNDO}; font-size: 1.6rem; }}
    .cartao-segmento p {{ margin: .35rem 0 0 0; color: #33454F; }}
    .rodape-evidencia {{
        font-size: .78rem; color: #6B7C88; border-top: 1px solid #E6EBEF;
        padding-top: .5rem; margin-top: 1.2rem;
    }}
    div[data-testid="stMetricValue"] {{ font-size: 1.5rem; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Carga dos artefatos
# --------------------------------------------------------------------------- #


def versao_dos_arquivos() -> tuple:
    """Data de modificação de cada artefato — muda quando um notebook regrava."""
    return tuple(
        caminho.stat().st_mtime if caminho.exists() else None
        for caminho, _, _ in art.ARQUIVOS.values()
    )


@st.cache_resource(show_spinner="Lendo os artefatos dos notebooks…")
def abrir(_versao: tuple) -> tuple[art.Artefatos, pd.DataFrame, pd.DataFrame]:
    """Lê tudo uma vez e só relê quando algum notebook regravar um arquivo."""
    artefatos = art.carregar()
    return artefatos, art.carteira(artefatos), art.perfil(artefatos)


try:
    ART, CARTEIRA, PERFIL = abrir(versao_dos_arquivos())
except art.ArtefatosAusentes:
    linhas = "\n".join(
        f"- `{caminho}` — notebook **{nb}**" for caminho, nb in art.arquivos_ausentes()
    )
    st.error(
        "A aplicação depende de arquivos que os notebooks ainda não gravaram:\n\n"
        f"{linhas}\n\nExecute os notebooks na ordem:\n\n```bash\nuv run invoke notebooks\n```"
    )
    st.stop()
except ValueError as erro:
    st.error(f"Os artefatos existem, mas não conversam entre si: {erro}")
    st.stop()

SELECIONADO = ART.selecionado
SEGMENTOS = ART.segmentos
CORES = {
    nome: config.PALETA_SEGMENTOS[i % len(config.PALETA_SEGMENTOS)]
    for i, nome in enumerate(SEGMENTOS)
} | {"Sem segmento": config.CINZA}
DESCRICOES = ART.dicionario.set_index("variavel")["descricao"].to_dict()
AVALIACAO = ART.opcionais.get("avaliacao")


def milhar(valor: float, casas: int = 0) -> str:
    """Formata número no padrão brasileiro: 2.350 e 1.234,56."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def csv_para_download(dados: pd.DataFrame, indice: bool = False) -> bytes:
    """Serializa no padrão do projeto: separador ``;`` e decimal ``,``."""
    return dados.to_csv(sep=";", decimal=",", index=indice).encode("utf-8-sig")


def evidencia(*origens: str) -> None:
    """Rodapé que aponta os arquivos de onde os números daquele bloco vieram."""
    st.markdown(
        '<div class="rodape-evidencia">Fonte: '
        + " · ".join(f"<code>{origem}</code>" for origem in origens)
        + "</div>",
        unsafe_allow_html=True,
    )


def rotulo(campo: str) -> str:
    """Nome de tela do campo; na falta, o próprio nome da coluna."""
    return ROTULOS.get(campo, campo.replace("_", " ").capitalize())


def cartao(segmento: str, texto: str) -> None:
    st.markdown(
        f'<div class="cartao-segmento" style="--cor:{CORES[segmento]}">'
        f"<h2>{segmento}</h2><p>{texto}</p></div>",
        unsafe_allow_html=True,
    )


def retrato(segmento: str) -> str:
    """Uma frase com as medianas de negócio do segmento."""
    linha = PERFIL.loc[segmento]
    return (
        f"{milhar(linha['imoveis'])} imóveis ({linha['pct_carteira']:.1f}% da carteira) · "
        f"preço mediano US$ {milhar(linha['preco_mediano'])} · "
        f"{milhar(linha['area_habitavel'])} pé² · qualidade {linha['qualidade_geral']:.0f} · "
        f"{linha['idade_imovel']:.0f} anos"
    )


# --------------------------------------------------------------------------- #
# Barra lateral — o modelo em operação
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.title("🏘️ Meridiano")
    st.caption("Segmentação da carteira residencial · modelo do notebook 04-0")
    st.divider()
    st.metric("Segmentos", len(SEGMENTOS))
    st.metric("Imóveis na carteira", milhar(len(CARTEIRA)))
    st.metric("Silhueta", f"{SELECIONADO['silhueta']:.3f}")
    st.divider()
    st.caption(
        f"Modelo **{SELECIONADO['modelo']}**\n\n`{SELECIONADO['params']}`\n\n"
        f"Arquivo: `models/{SELECIONADO['arquivo']}`\n\n"
        f"Atribuição de imóveis novos: "
        f"**{'predict do modelo' if ART.classifica_novos else 'centroide mais próximo'}**"
    )
    st.caption(
        "O preço de venda **não** entrou na modelagem: é rótulo reservado, usado só "
        "para ler o resultado."
    )

abas = st.tabs(
    [
        "Resultado do modelo",
        "Classificar um imóvel",
        "Perfil dos segmentos",
        "Carteira classificada",
        "Classificação em lote",
        "Regras de associação",
        "Procedência",
    ]
)


# --------------------------------------------------------------------------- #
# 1 · Resultado do modelo
# --------------------------------------------------------------------------- #

with abas[0]:
    st.header("O que o modelo entrega")

    lider = PERFIL["pct_vgv"].idxmax()
    maior = PERFIL["pct_carteira"].idxmax()
    colunas = st.columns(4)
    colunas[0].metric(
        "Segmentos", len(SEGMENTOS), f"{SELECIONADO['modelo']}", delta_color="off", border=True
    )
    colunas[1].metric(
        "Líder em valor de venda",
        lider,
        f"{PERFIL.loc[lider, 'pct_vgv']:.1f}% do VGV",
        delta_color="off",
        border=True,
    )
    colunas[2].metric(
        "Maior segmento",
        maior,
        f"{PERFIL.loc[maior, 'pct_carteira']:.1f}% dos imóveis",
        delta_color="off",
        border=True,
    )
    colunas[3].metric(
        "Preço mediano: maior ÷ menor",
        f"{PERFIL['preco_mediano'].max() / PERFIL['preco_mediano'].min():.2f}×",
        border=True,
    )

    esquerda, direita = st.columns([3, 2])
    with esquerda:
        st.subheader("Imóveis e valor de venda por segmento")
        composicao = (
            PERFIL.reset_index()
            .melt(
                id_vars="segmento",
                value_vars=["pct_carteira", "pct_vgv"],
                var_name="medida",
                value_name="percentual",
            )
            .replace({"pct_carteira": "% dos imóveis", "pct_vgv": "% do VGV"})
        )
        figura = px.bar(
            composicao,
            x="segmento",
            y="percentual",
            color="medida",
            barmode="group",
            text_auto=".1f",
            color_discrete_sequence=[config.AZUL_COBALTO, config.CORAL],
            labels={"segmento": "", "percentual": "% da carteira", "medida": ""},
        )
        figura.update_layout(height=340, legend_title_text="", margin=dict(t=10, b=10))
        st.plotly_chart(figura)
        st.caption(
            "O segmento com menos imóveis pode ser o que concentra o valor de venda — "
            "orçamento por unidade e orçamento por receita não são a mesma conta."
        )

    with direita:
        st.subheader("Preço de venda por segmento")
        figura = px.box(
            CARTEIRA,
            x="segmento",
            y="preco_venda",
            color="segmento",
            category_orders={"segmento": SEGMENTOS},
            color_discrete_map=CORES,
            points=False,
            labels={"segmento": "", "preco_venda": "US$"},
        )
        figura.update_layout(height=340, showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(figura)
        st.caption(
            "O preço não entrou no agrupamento. Segmentos que se separam no preço são a "
            "validação externa da segmentação."
        )

    if AVALIACAO:
        st.subheader("Critérios de sucesso — notebook 05")
        criterios = pd.DataFrame(AVALIACAO["criterios"])
        criterios["atende"] = criterios["atende"].map({True: "✅ atende", False: "❌ não atende"})
        criterios["crítico"] = criterios["crítico"].map({True: "sim", False: "não"})
        st.dataframe(criterios, hide_index=True)

        esquerda, direita = st.columns([3, 2])
        with esquerda:
            st.markdown("**Cenários financeiros do primeiro ano**")
            cenarios = pd.DataFrame(AVALIACAO["cenarios_financeiros"])
            st.dataframe(
                cenarios,
                hide_index=True,
                column_config={
                    "ganho": st.column_config.NumberColumn("ganho", format="percent"),
                    "receita_extra": st.column_config.NumberColumn(format="$ %.0f"),
                    "resultado_ano1": st.column_config.NumberColumn(format="$ %.0f"),
                    "roi_ano1": st.column_config.NumberColumn(format="percent"),
                    "payback_meses": st.column_config.NumberColumn(format="%.1f"),
                },
            )
        with direita:
            aprovado = AVALIACAO.get("aprovado")
            (st.success if aprovado else st.warning)(
                f"**Próxima ação: {AVALIACAO.get('proxima_acao', '—')}**\n\n"
                f"{AVALIACAO.get('justificativa', '')}"
            )
        evidencia("reports/05-avaliacao.json", "data/processed/segmentos.csv")
    else:
        st.info(
            "A avaliação do notebook 05 (`reports/05-avaliacao.json`) ainda não foi gravada — "
            "os critérios de sucesso aparecem aqui depois que ele rodar."
        )
        evidencia("data/processed/segmentos.csv", "data/processed/ames_housing_tratado.csv")


# --------------------------------------------------------------------------- #
# 2 · Classificar um imóvel
# --------------------------------------------------------------------------- #


def campo_do_formulario(campo: str) -> object:
    """Desenha o controle certo para o tipo da coluna; vazio significa não informado."""
    serie = ART.base[campo]
    ajuda = DESCRICOES.get(campo, "")
    if campo in BINARIAS:
        return st.selectbox(
            rotulo(campo),
            options=[1, 0],
            index=None,
            format_func=lambda v: "Sim" if v else "Não",
            placeholder="não informado",
            help=ajuda,
        )
    if campo in ART.ordinais:
        return st.selectbox(
            rotulo(campo),
            options=ART.niveis[campo],
            index=None,
            placeholder="não informado",
            help=ajuda,
        )
    if campo in ART.categorias:
        return st.selectbox(
            rotulo(campo),
            options=sorted(ART.categorias[campo], key=str),
            index=None,
            placeholder="não informado",
            help=ajuda,
        )
    minimo, maximo = float(serie.min()), float(serie.max())
    return st.number_input(
        rotulo(campo),
        min_value=0.0,
        value=None,
        step=1.0 if maximo - minimo <= 50 else 10.0,
        placeholder=f"mediana {milhar(serie.median(), 1 if serie.median() % 1 else 0)}",
        help=f"{ajuda} Na carteira: {minimo:g} a {maximo:g}.",
    )


with abas[1]:
    st.header("Classificar um imóvel")
    st.markdown(
        "Preencha o que souber. O que ficar em branco é emprestado do **imóvel mais "
        "parecido da carteira** — o mesmo roteiro do notebook 06 — e a tela mostra qual "
        "foi o vizinho e quais campos ele completou."
    )

    grupos = {
        titulo: [c for c in campos if c in ART.colunas_de_entrada]
        for titulo, campos in GRUPOS.items()
    }
    with st.form("classificar"):
        preenchidos: dict[str, object] = {}
        for titulo, campos in grupos.items():
            if not campos:
                continue
            st.markdown(f"**{titulo}**")
            colunas = st.columns(5)
            for posicao, campo in enumerate(campos):
                with colunas[posicao % 5]:
                    preenchidos[campo] = campo_do_formulario(campo)
            st.divider()
        enviado = st.form_submit_button("Classificar", type="primary")

    if enviado:
        imovel = art.informados(preenchidos)
        if not imovel:
            st.session_state.pop("resultado", None)
            st.warning("Informe ao menos um campo para classificar.")
        else:
            try:
                st.session_state["resultado"] = art.classificar(ART, imovel)
            except ValueError as erro:
                st.session_state.pop("resultado", None)
                st.error(str(erro))

    if "resultado" in st.session_state:
        resultado = st.session_state["resultado"]
        segmento = resultado["segmento"]
        cartao(segmento, retrato(segmento))

        razao = resultado["razao_de_fronteira"]
        acima = (CARTEIRA["razao_de_fronteira"] < razao).mean()
        colunas = st.columns(4)
        colunas[0].metric("Segmento", segmento, border=True)
        colunas[1].metric("Segundo mais próximo", resultado["segundo_mais_proximo"], border=True)
        colunas[2].metric(
            "Razão de fronteira",
            f"{razao:.3f}",
            f"maior que {100 * acima:.0f}% da carteira",
            delta_color="off",
            border=True,
        )
        colunas[3].metric(
            "Campos informados",
            len(resultado["informados"]),
            f"{len(resultado['completados'])} completados pelo vizinho",
            delta_color="off",
            border=True,
        )
        st.caption(
            "Razão de fronteira = distância ao centro do segmento ÷ distância ao segundo "
            "mais próximo. Perto de 1, o imóvel está entre dois segmentos e a leitura "
            "pede revisão humana."
        )

        esquerda, direita = st.columns([2, 3])
        with esquerda:
            st.subheader("Distância até cada segmento")
            distancias = pd.DataFrame(
                {
                    "segmento": list(resultado["distancias"]),
                    "distancia": list(resultado["distancias"].values()),
                }
            )
            figura = px.bar(
                distancias,
                x="distancia",
                y="segmento",
                orientation="h",
                text_auto=".3f",
                color="segmento",
                color_discrete_map=CORES,
                labels={"distancia": "distância euclidiana no espaço do modelo", "segmento": ""},
            )
            figura.update_layout(height=280, showlegend=False, margin=dict(t=10, b=10))
            figura.update_yaxes(autorange="reversed")
            st.plotly_chart(figura)

        with direita:
            st.subheader(f"O imóvel contra o típico do {segmento}")
            do_segmento = CARTEIRA[CARTEIRA["segmento"] == segmento]
            linhas = []
            for campo in resultado["informados"]:
                valor = resultado["registro"][campo]
                if pd.api.types.is_numeric_dtype(ART.base[campo]):
                    tipico = do_segmento[campo].median()
                else:
                    tipico = do_segmento[campo].mode().iat[0]
                linhas.append(
                    {"Atributo": rotulo(campo), "Este imóvel": valor, "Típico do segmento": tipico}
                )
            st.dataframe(pd.DataFrame(linhas).astype(str), hide_index=True, height=280)

        with st.expander(
            f"Registro efetivamente classificado · vizinho de referência: pid "
            f"{resultado['vizinho']}"
        ):
            registro = pd.DataFrame(
                {
                    "Atributo": ART.colunas_de_entrada,
                    "Valor usado": [str(resultado["registro"][c]) for c in ART.colunas_de_entrada],
                    "Origem": [
                        "informado" if c in resultado["informados"] else "vizinho"
                        for c in ART.colunas_de_entrada
                    ],
                }
            )
            st.dataframe(registro, hide_index=True)

        saida = pd.DataFrame(
            [
                {
                    **resultado["registro"],
                    "segmento": segmento,
                    "razao_de_fronteira": razao,
                    "pid_de_referencia": resultado["vizinho"],
                }
            ]
        )
        st.download_button(
            "Baixar esta classificação (CSV)",
            data=csv_para_download(saida),
            file_name="classificacao-do-imovel.csv",
            mime="text/csv",
        )
    evidencia(
        f"models/{SELECIONADO['arquivo']}",
        "data/processed/ames_housing_tratado.csv",
        "data/processed/escala.csv",
    )


# --------------------------------------------------------------------------- #
# 3 · Perfil dos segmentos
# --------------------------------------------------------------------------- #

with abas[2]:
    st.header("O que diferencia cada segmento")

    for segmento in SEGMENTOS:
        cartao(segmento, retrato(segmento))

    st.subheader("Assinatura dos segmentos")
    st.caption(
        "Quantos desvios-padrão a mediana de cada segmento fica acima ou abaixo da "
        "mediana da carteira. É a leitura de por que os grupos são diferentes — e não "
        "apenas caros e baratos."
    )
    colunas_assinatura = [
        c
        for grupo in ("Áreas (pé²)", "Distribuição interna", "Idade", "Qualidade e conservação")
        for c in GRUPOS[grupo]
        if c in ART.base and pd.api.types.is_numeric_dtype(ART.base[c])
    ] + ["preco_venda"]
    assinatura = art.assinatura(ART, colunas_assinatura)
    mapa = go.Figure(
        go.Heatmap(
            z=assinatura.to_numpy(),
            x=[rotulo(c) if c != "preco_venda" else "Preço de venda" for c in assinatura],
            y=list(assinatura.index),
            colorscale=[[0, config.CORAL], [0.5, "#FFFFFF"], [1, config.AZUL_COBALTO]],
            zmid=0,
            text=assinatura.to_numpy(),
            texttemplate="%{text:.2f}",
            colorbar=dict(title="desvios"),
        )
    )
    mapa.update_layout(height=320, margin=dict(t=10, b=10))
    st.plotly_chart(mapa)

    reducoes = {
        nome: ART.opcionais[chave]
        for nome, chave in (("UMAP", "umap"), ("PCA", "pca"))
        if chave in ART.opcionais and len(ART.opcionais[chave]) == len(CARTEIRA)
    }
    if reducoes:
        st.subheader("A carteira em duas dimensões")
        tecnica = st.radio("Redução", options=list(reducoes), horizontal=True)
        eixos = reducoes[tecnica].iloc[:, :2]
        pontos = CARTEIRA[["pid", "bairro", "segmento", "preco_venda"]].assign(
            x=eixos.iloc[:, 0].to_numpy(), y=eixos.iloc[:, 1].to_numpy()
        )
        figura = px.scatter(
            pontos,
            x="x",
            y="y",
            color="segmento",
            category_orders={"segmento": SEGMENTOS},
            color_discrete_map=CORES,
            opacity=0.6,
            hover_data=["pid", "bairro", "preco_venda"],
            labels={"x": eixos.columns[0], "y": eixos.columns[1], "segmento": ""},
        )
        figura.update_layout(height=460, margin=dict(t=10, b=10))
        st.plotly_chart(figura)
        st.caption(
            f"Projeção gravada pelo notebook 04-2 ({tecnica}). Cores do modelo do 04-0: "
            "a redução só desenha a carteira, não decide o segmento."
        )

    st.subheader("Perfil mediano de cada segmento")
    st.dataframe(
        PERFIL.rename(
            columns={
                "imoveis": "Imóveis",
                "vgv": "VGV (US$)",
                "preco_mediano": "Preço mediano",
                "area_habitavel": "Área habitável",
                "qualidade_geral": "Qualidade geral",
                "idade_imovel": "Idade",
                "razao_mediana": "Razão de fronteira mediana",
                "pct_carteira": "% dos imóveis",
                "pct_vgv": "% do VGV",
            }
        ).round(2)
    )
    evidencia(
        "data/processed/segmentos.csv",
        "data/processed/ames_housing_tratado.csv",
        "data/processed/ames_housing_umap.csv",
        "data/processed/ames_housing_pca.csv",
    )


# --------------------------------------------------------------------------- #
# 4 · Carteira classificada
# --------------------------------------------------------------------------- #

with abas[3]:
    st.header("A carteira classificada")
    st.markdown(
        "Os imóveis da base curada com o segmento gravado pelo notebook 04-0 e a razão "
        "de fronteira de cada um."
    )

    filtros = st.columns([2, 3, 2])
    escolhidos = filtros[0].multiselect("Segmento", options=SEGMENTOS, default=SEGMENTOS)
    bairros = filtros[1].multiselect(
        "Bairro", options=sorted(CARTEIRA["bairro"].dropna().unique()), default=[]
    )
    teto = filtros[2].slider(
        "Razão de fronteira até", min_value=0.0, max_value=1.0, value=1.0, step=0.05
    )

    recorte = CARTEIRA[
        CARTEIRA["segmento"].isin(escolhidos) & (CARTEIRA["razao_de_fronteira"] <= teto)
    ]
    if bairros:
        recorte = recorte[recorte["bairro"].isin(bairros)]

    if recorte.empty:
        st.info("Nenhum imóvel atende aos filtros selecionados.")
    else:
        colunas = st.columns(4)
        colunas[0].metric("Imóveis no recorte", milhar(len(recorte)), border=True)
        colunas[1].metric(
            "VGV do recorte", f"US$ {milhar(recorte['preco_venda'].sum() / 1e6, 1)} mi", border=True
        )
        colunas[2].metric(
            "Preço mediano", f"US$ {milhar(recorte['preco_venda'].median())}", border=True
        )
        colunas[3].metric(
            "Razão de fronteira mediana",
            f"{recorte['razao_de_fronteira'].median():.3f}",
            border=True,
        )

        esquerda, direita = st.columns([3, 2])
        with esquerda:
            st.subheader("Área habitável × preço realizado")
            figura = px.scatter(
                recorte,
                x="area_habitavel",
                y="preco_venda",
                color="segmento",
                category_orders={"segmento": SEGMENTOS},
                color_discrete_map=CORES,
                opacity=0.65,
                hover_data=["pid", "bairro", "razao_de_fronteira"],
                labels={
                    "area_habitavel": "área habitável (pé²)",
                    "preco_venda": "preço de venda (US$)",
                    "segmento": "",
                },
            )
            figura.update_layout(height=420, margin=dict(t=10, b=10))
            st.plotly_chart(figura)

        with direita:
            st.subheader("Razão de fronteira")
            figura = px.histogram(
                recorte,
                x="razao_de_fronteira",
                color="segmento",
                category_orders={"segmento": SEGMENTOS},
                color_discrete_map=CORES,
                nbins=40,
                labels={"razao_de_fronteira": "razão de fronteira", "segmento": ""},
            )
            figura.update_layout(height=420, margin=dict(t=10, b=10), bargap=0.05)
            st.plotly_chart(figura)

        principais = [
            "pid",
            "segmento",
            "razao_de_fronteira",
            "bairro",
            "preco_venda",
            "area_habitavel",
            "qualidade_geral",
            "idade_imovel",
        ]
        st.dataframe(recorte[[c for c in principais if c in recorte]], hide_index=True, height=320)
        st.download_button(
            "Baixar o recorte com todas as colunas (CSV)",
            data=csv_para_download(recorte),
            file_name="carteira-classificada.csv",
            mime="text/csv",
        )
    evidencia("data/processed/segmentos.csv", "data/processed/ames_housing_tratado.csv")


# --------------------------------------------------------------------------- #
# 5 · Classificação em lote
# --------------------------------------------------------------------------- #

with abas[4]:
    st.header("Classificar um lote de imóveis")
    st.markdown(
        "Um CSV com colunas da base curada entra, a lista classificada sai. Cada linha é "
        "completada pelo imóvel mais parecido da carteira; colunas que o modelo não "
        "conhece (matrícula, observação…) seguem intactas no resultado. Linha com "
        "categoria desconhecida não derruba o lote: sai sem segmento e com o motivo."
    )

    campos_do_modelo = [c for c in ROTULOS if c in ART.colunas_de_entrada]
    exemplo = pd.DataFrame(
        [
            {
                c: (
                    ART.base[c].median()
                    if pd.api.types.is_numeric_dtype(ART.base[c])
                    else ART.base[c].mode().iat[0]
                )
                for c in campos_do_modelo
            }
        ]
    )
    esquerda, direita = st.columns([2, 3])
    esquerda.download_button(
        "Baixar modelo de CSV",
        data=csv_para_download(exemplo),
        file_name="modelo-de-carga.csv",
        mime="text/csv",
        help="Uma linha com os campos do formulário, no valor típico da carteira.",
    )
    separador = direita.radio(
        "Separador do arquivo", options=[";", ","], horizontal=True, help="Padrão do projeto: ;"
    )

    arquivo = st.file_uploader("Arquivo CSV", type=["csv"])
    if arquivo is not None:
        try:
            entrada = pd.read_csv(
                BytesIO(arquivo.getvalue()),
                sep=separador,
                decimal="," if separador == ";" else ".",
                encoding="utf-8-sig",
            )
        except Exception as erro:  # noqa: BLE001 - a mensagem vai para a tela
            st.error(f"Não foi possível ler o arquivo: {erro}")
        else:
            conhecidas = [c for c in entrada.columns if c in ART.colunas_de_entrada]
            if not conhecidas:
                st.error(
                    "Nenhuma coluna do arquivo existe na base curada — confira o modelo de CSV."
                )
            else:
                with st.spinner("Classificando…"):
                    classificado = art.classificar_lote(ART, entrada)
                com_erro = classificado["erro"] != ""
                colunas = st.columns(3)
                colunas[0].metric("Linhas no arquivo", milhar(len(classificado)), border=True)
                colunas[1].metric("Classificadas", milhar((~com_erro).sum()), border=True)
                colunas[2].metric("Com erro", milhar(com_erro.sum()), border=True)

                if com_erro.any():
                    st.warning(
                        f"{com_erro.sum()} linha(s) não foram classificadas — o motivo está na "
                        "coluna `erro`."
                    )

                distribuicao = (
                    classificado.loc[~com_erro]
                    .groupby("segmento")
                    .size()
                    .reset_index(name="imoveis")
                )
                figura = px.bar(
                    distribuicao,
                    x="segmento",
                    y="imoveis",
                    color="segmento",
                    category_orders={"segmento": SEGMENTOS},
                    color_discrete_map=CORES,
                    text_auto=True,
                    labels={"segmento": "", "imoveis": "imóveis"},
                )
                figura.update_layout(height=300, showlegend=False, margin=dict(t=10, b=10))
                st.plotly_chart(figura)

                st.dataframe(classificado, hide_index=True, height=320)
                st.download_button(
                    "Baixar o lote classificado (CSV)",
                    data=csv_para_download(classificado),
                    file_name="lote-classificado.csv",
                    mime="text/csv",
                )
    evidencia(f"models/{SELECIONADO['arquivo']}", "data/processed/ames_housing_tratado.csv")


# --------------------------------------------------------------------------- #
# 6 · Regras de associação
# --------------------------------------------------------------------------- #

with abas[5]:
    st.header("Regras de associação da carteira")
    regras = ART.opcionais.get("regras")
    if regras is None or regras.empty:
        st.info(
            "As regras do notebook 04-3 (`data/processed/regras_associacao.csv`) ainda não "
            "foram gravadas."
        )
    else:
        st.markdown(
            "Combinações de atributos que aparecem juntas na carteira, encontradas pelo "
            "notebook 04-3. Atributos numéricos entram em faixas (`=baixo`, `=medio`, "
            "`=alto`); **lift** acima de 1 indica que os itens aparecem juntos mais do que o "
            "acaso explicaria."
        )
        filtros = st.columns([2, 2, 3, 3])
        lift_minimo = filtros[0].slider(
            "Lift mínimo",
            min_value=float(regras["lift"].min()),
            max_value=float(regras["lift"].max()),
            value=float(regras["lift"].quantile(0.5)),
        )
        confianca_minima = filtros[1].slider(
            "Confiança mínima", min_value=0.0, max_value=1.0, value=0.7, step=0.05
        )
        antecedente = filtros[2].text_input(
            "Antecedente contém", placeholder="ex.: qualidade_geral"
        )
        consequente = filtros[3].text_input("Consequente contém", placeholder="ex.: estilo")

        filtradas = regras[
            (regras["lift"] >= lift_minimo) & (regras["confianca"] >= confianca_minima)
        ]
        if antecedente:
            filtradas = filtradas[
                filtradas["antecedente"].str.contains(antecedente, case=False, regex=False)
            ]
        if consequente:
            filtradas = filtradas[
                filtradas["consequente"].str.contains(consequente, case=False, regex=False)
            ]
        filtradas = filtradas.sort_values("lift", ascending=False)

        colunas = st.columns(3)
        colunas[0].metric("Regras no filtro", milhar(len(filtradas)), border=True)
        colunas[1].metric("Regras gravadas", milhar(len(regras)), border=True)
        colunas[2].metric(
            "Maior lift no filtro",
            f"{filtradas['lift'].max():.2f}" if len(filtradas) else "—",
            border=True,
        )
        st.dataframe(
            filtradas.head(500),
            hide_index=True,
            height=420,
            column_config={
                "suporte": st.column_config.NumberColumn(format="%.3f"),
                "confianca": st.column_config.NumberColumn(format="%.3f"),
                "lift": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        if len(filtradas) > 500:
            st.caption("Mostrando as 500 de maior lift; o download traz todas.")
        st.download_button(
            "Baixar as regras filtradas (CSV)",
            data=csv_para_download(filtradas),
            file_name="regras-de-associacao.csv",
            mime="text/csv",
        )
    evidencia("data/processed/regras_associacao.csv")


# --------------------------------------------------------------------------- #
# 7 · Procedência
# --------------------------------------------------------------------------- #

with abas[6]:
    st.header("De onde vem o que esta tela mostra")
    st.markdown(
        "A aplicação não treina nada: lê o que os notebooks gravaram. O pré-processador é "
        "reconstruído a partir da base curada, do dicionário e das escalas — exatamente "
        "como no notebook 06 — e conferido contra a saída do 03."
    )

    colunas = st.columns(3)
    colunas[0].metric(
        "Pré-processamento confere com o 03",
        "sim" if ART.confere_com_03 else "não",
        f"{ART.X.shape[1]} features",
        delta_color="off",
        border=True,
    )
    colunas[1].metric(
        "Modelo reproduz segmentos.csv",
        f"{100 * ART.concordancia:.1f}%" if ART.concordancia is not None else "sem predict",
        border=True,
    )
    colunas[2].metric("Atribuição", "predict" if ART.classifica_novos else "centroide", border=True)

    if not ART.confere_com_03:
        st.error(
            "O pré-processamento reconstruído não bate com `ames_housing_preprocessed.csv`. "
            "Algum notebook foi rodado fora de ordem — execute de novo do 02 ao 04-0."
        )
    if ART.concordancia is not None and ART.concordancia < 1:
        st.warning(
            "O modelo não reproduz todos os rótulos de `segmentos.csv`: o `.joblib` e os "
            "rótulos vieram de execuções diferentes do 04-0."
        )

    st.subheader("Arquivos consumidos")

    def linha_de_arquivo(caminho: Path, notebook: str, obrigatorio: bool, lido: bool) -> dict:
        existe = caminho.exists()
        return {
            "Arquivo": caminho.relative_to(config.RAIZ).as_posix(),
            "Notebook": notebook,
            "Obrigatório": "sim" if obrigatorio else "não",
            "Situação": ("✅ lido" if lido else "⚠️ não carregou") if existe else "— ausente",
            "Tamanho (KB)": round(caminho.stat().st_size / 1024, 1) if existe else None,
            "Gravado em": (
                datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                if existe
                else None
            ),
        }

    arquivos = [
        linha_de_arquivo(caminho, notebook, obrigatorio, lido=obrigatorio or nome in ART.opcionais)
        for nome, (caminho, notebook, obrigatorio) in art.ARQUIVOS.items()
    ]
    arquivos.insert(
        1,
        linha_de_arquivo(
            config.MODELS / SELECIONADO["arquivo"], "04-0", True, lido=ART.modelo is not None
        ),
    )
    st.dataframe(pd.DataFrame(arquivos), hide_index=True)

    st.subheader("Modelo selecionado")
    st.json(SELECIONADO)
    evidencia("models/selecionado.json")
