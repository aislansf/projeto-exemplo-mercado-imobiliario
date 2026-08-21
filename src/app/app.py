"""Aplicação Streamlit que consome o modelo publicado em ``.pkl``.

A tela lê **um único artefato**: ``models/aplicacao-segmentacao.pkl``. Tudo o que
aparece aqui — a partição, as personas, as faixas de confiança, a carteira
classificada e o plano de monitoramento — sai de dentro desse pacote. Não há
consulta a ``data/``, a ``reports/`` nem aos demais arquivos de ``models/``: se o
pacote for copiado para outra máquina junto com este diretório, a aplicação sobe.

Execute com::

    uv run invoke app
    # ou
    uv run streamlit run src/app/app.py

As sete abas seguem o caminho de quem usa: primeiro o resultado do modelo, depois
a classificação de um imóvel, o catálogo de ações, a carteira, o lote mensal, o
monitoramento e, por último, a procedência do próprio pacote.
"""

from __future__ import annotations

import sys
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

from src.app import pacote as pac  # noqa: E402

st.set_page_config(
    page_title="Meridiano · Segmentação da carteira",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Cores de apoio da tela. As cores dos segmentos vêm do próprio pacote
# (``catalogo['cores']``); estas espelham a identidade de ``src/config.py`` e
# ficam aqui para que a aplicação não dependa de nenhum outro módulo do projeto.
AZUL_PROFUNDO = "#1B4965"
AZUL_COBALTO = "#2A6F97"
CORAL = "#EE6C4D"
CINZA = "#8A9BA8"

#: Como o formulário agrupa os 17 campos do contrato. Campo do contrato que não
#: estiver aqui ainda assim aparece na tela, no bloco final.
GRUPOS = {
    "Áreas (pé²)": [
        "area_habitavel",
        "area_porao",
        "area_terreno",
        "area_garagem",
        "area_varandas",
    ],
    "Distribuição interna": ["comodos", "dormitorios", "banheiros_total", "lareiras"],
    "Idade": ["idade_imovel", "anos_desde_reforma"],
    "Qualidade e conservação": [
        "qualidade_geral",
        "conservacao_geral",
        "qualidade_externa",
        "qualidade_cozinha",
        "qualidade_porao",
        "acabamento_garagem",
    ],
}

CSS = f"""
<style>
    .cartao-segmento {{
        border-left: 8px solid var(--cor); border-radius: 8px;
        padding: 1rem 1.2rem; margin: .2rem 0 1rem 0;
        background: rgba(27, 73, 101, 0.06);
    }}
    .cartao-segmento h2 {{ margin: 0; color: {AZUL_PROFUNDO}; font-size: 1.6rem; }}
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
# Carga do pacote
# --------------------------------------------------------------------------- #


@st.cache_resource(show_spinner="Abrindo o pacote publicado…")
def abrir_pacote(caminho: str) -> dict:
    """Lê o ``.pkl`` uma única vez por processo."""
    return pac.carregar(caminho)


try:
    PACOTE = abrir_pacote(str(pac.CAMINHO_PACOTE))
except FileNotFoundError:
    st.error(
        f"O pacote `{pac.CAMINHO_PACOTE.name}` não existe em `models/`. "
        "Ele é gravado na fase de implantação:\n\n```bash\nuv run invoke notebooks\n```"
    )
    st.stop()
except pac.PacoteInvalido as erro:
    st.error(f"O pacote existe, mas não pôde ser lido: {erro}")
    st.stop()

MODELO = PACOTE["modelo"]
ESPACO = pac.espaco(PACOTE)
ROTULOS = pac.rotulos(PACOTE)
CAMPOS = pac.campos(PACOTE)
LINHAS = pac.linhas_de_produto(PACOTE)
CORES = pac.cores(PACOTE)
CORES_POR_CODIGO = {LINHAS.loc[seg, "codigo"]: cor for seg, cor in CORES.items()}
CARTEIRA = pac.carteira(PACOTE)
ORDEM_FAIXAS = list(PACOTE["atribuicao"]["faixas"])


def milhar(valor: float, casas: int = 0) -> str:
    """Formata número no padrão brasileiro: 2.350 e 1.234,56."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def csv_para_download(dados: pd.DataFrame, indice: bool = False) -> bytes:
    """Serializa no padrão do projeto: separador ``;`` e decimal ``,``."""
    return dados.to_csv(sep=";", decimal=",", index=indice).encode("utf-8-sig")


def evidencia(*origens: str) -> None:
    """Rodapé que aponta a chave do pacote de onde os números daquele bloco vieram."""
    st.markdown(
        '<div class="rodape-evidencia">Do pacote: '
        + " · ".join(f"<code>{origem}</code>" for origem in origens)
        + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Barra lateral — identidade do modelo em operação
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.title("🏘️ Meridiano")
    st.caption("Segmentação da carteira residencial · modelo servido a partir do `.pkl`")
    st.divider()
    st.metric("Linhas de produto", MODELO["k"])
    st.metric("Imóveis classificados", milhar(len(CARTEIRA)))
    st.metric("Coesão (silhueta)", f"{MODELO['silhueta']:.4f}")
    st.metric(
        "Ação automática liberada", f"{100 * CARTEIRA['acao_automatica_liberada'].mean():.1f}%"
    )
    st.divider()
    st.caption(
        f"Pacote `{PACOTE['formato']}` · modelo **{PACOTE['versao_modelo']}**\n\n"
        f"{MODELO['algoritmo']} com k={MODELO['k']}, semente {MODELO['semente']}\n\n"
        f"Treino: {milhar(MODELO['imoveis_de_treino'])} imóveis · {MODELO['periodo_de_treino']}"
    )
    st.caption(f"Arquivo: `models/{pac.CAMINHO_PACOTE.name}`")
    st.caption(
        "O preço de venda **não** entrou na modelagem: é rótulo reservado, aberto só "
        "na leitura de resultado."
    )

abas = st.tabs(
    [
        "Resultado do modelo",
        "Classificar um imóvel",
        "Linhas de produto",
        "Carteira classificada",
        "Classificação em lote",
        "Monitoramento",
        "O pacote",
    ]
)


# --------------------------------------------------------------------------- #
# 1 · Resultado do modelo
# --------------------------------------------------------------------------- #

with abas[0]:
    st.header("O que o modelo entrega")

    colunas = st.columns(4)
    lider = LINHAS["pct_receita"].idxmax()
    colunas[0].metric("Linhas de produto", MODELO["k"], "de 2 a 5 pelo orçamento", border=True)
    colunas[1].metric(
        "Linha líder em receita",
        LINHAS.loc[lider, "codigo"],
        f"{LINHAS.loc[lider, 'pct_receita']:.1f}% da receita",
        border=True,
    )
    colunas[2].metric(
        "Coesão (silhueta)",
        f"{MODELO['silhueta']:.4f}",
        f"piso de {PACOTE['monitoramento']['limiares']['piso_de_silhueta']:.2f}",
        border=True,
    )
    colunas[3].metric(
        "Imóveis em fronteira",
        f"{100 * (CARTEIRA['confianca'] == 'fronteira').mean():.1f}%",
        f"teto operacional de {100 * PACOTE['atribuicao']['teto_operacional']:.0f}%",
        delta_color="inverse",
        border=True,
    )

    esquerda, direita = st.columns([3, 2])

    with esquerda:
        st.subheader("Unidades e receita por linha")
        composicao = LINHAS.melt(
            id_vars="codigo",
            value_vars=["pct_carteira", "pct_receita"],
            var_name="medida",
            value_name="percentual",
        ).replace({"pct_carteira": "% das unidades", "pct_receita": "% da receita"})
        figura = px.bar(
            composicao,
            x="codigo",
            y="percentual",
            color="medida",
            barmode="group",
            text_auto=".1f",
            color_discrete_sequence=[AZUL_COBALTO, CORAL],
            labels={"codigo": "", "percentual": "% da carteira", "medida": ""},
        )
        figura.update_layout(height=340, legend_title_text="", margin=dict(t=10, b=10))
        st.plotly_chart(figura)
        st.caption(
            "A leitura que interessa à diretoria: a linha com menos unidades pode ser a "
            "que sustenta a receita — orçamento por unidade e orçamento por receita não "
            "são a mesma conta."
        )

    with direita:
        st.subheader("Coesão de cada linha")
        figura = px.bar(
            LINHAS.reset_index(),
            x="silhueta_media",
            y="codigo",
            orientation="h",
            text_auto=".4f",
            color="codigo",
            color_discrete_map=CORES_POR_CODIGO,
            labels={"silhueta_media": "silhueta média", "codigo": ""},
        )
        figura.add_vline(
            x=PACOTE["monitoramento"]["limiares"]["piso_de_silhueta"],
            line_dash="dash",
            line_color=CINZA,
            annotation_text="piso",
        )
        figura.update_layout(height=340, showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(figura)
        st.caption(
            "A silhueta média da carteira esconde diferença entre linhas: a mais coesa "
            "sustenta ação automática, a menos coesa exige revisão caso a caso."
        )

    st.subheader("Confronto com os critérios de aceite")
    resultados = PACOTE["evidencias"]["resultados"].copy()
    resultados["atende"] = resultados["atende"].map({True: "✅ atende", False: "❌ não atende"})
    st.dataframe(
        resultados.rename(
            columns={
                "resultado": "Resultado",
                "valor": "Valor",
                "regua": "Régua",
                "criterio": "Critério",
                "atende": "Situação",
            }
        ),
        hide_index=True,
    )
    evidencia("evidencias['resultados']", "catalogo['linhas']", "modelo")


# --------------------------------------------------------------------------- #
# 2 · Classificar um imóvel
# --------------------------------------------------------------------------- #

with abas[1]:
    st.header("Classificar um imóvel")
    st.markdown(
        "O formulário é o **contrato de entrada** do modelo, lido do pacote. Três campos "
        "são obrigatórios; os demais, quando não informados, entram com a mediana da "
        "carteira de treino — e a tela diz quais foram completados."
    )

    obrigatorios = set(PACOTE["contrato"]["obrigatorios"])
    contrato = CAMPOS.set_index("campo")
    agrupados = {
        titulo: [c for c in lista if c in contrato.index] for titulo, lista in GRUPOS.items()
    }
    restantes = [
        c for c in ESPACO if c not in {campo for lista in agrupados.values() for campo in lista}
    ]
    if restantes:
        agrupados["Outros campos do contrato"] = restantes

    with st.form("classificar"):
        informados: dict[str, float] = {}
        for titulo, lista in agrupados.items():
            st.markdown(f"**{titulo}**")
            colunas = st.columns(min(len(lista), 5))
            for posicao, campo in enumerate(lista):
                linha = contrato.loc[campo]
                rotulo = linha["rotulo"] + (" *" if campo in obrigatorios else "")
                ajuda = (
                    f"Observado no treino: {linha['observado_minimo']:g} a "
                    f"{linha['observado_maximo']:g}. Padrão do contrato: {linha['padrao']:g}."
                )
                with colunas[posicao % len(colunas)]:
                    if linha["tipo"] == "ordinal":
                        informados[campo] = float(
                            st.slider(
                                rotulo,
                                min_value=int(linha["aceito_minimo"]),
                                max_value=int(linha["aceito_maximo"]),
                                value=int(linha["padrao"]),
                                help=ajuda,
                            )
                        )
                    else:
                        largura = float(linha["observado_maximo"] - linha["observado_minimo"])
                        informados[campo] = float(
                            st.number_input(
                                rotulo,
                                min_value=float(linha["aceito_minimo"]),
                                max_value=float(linha["aceito_maximo"]),
                                value=float(linha["padrao"]),
                                step=1.0 if largura <= 20 else 10.0,
                                help=ajuda,
                            )
                        )
            st.divider()
        enviado = st.form_submit_button("Classificar", type="primary")

    if enviado or "resultado" in st.session_state:
        if enviado:
            st.session_state["resultado"] = pac.classificar(informados, PACOTE)
        resultado = st.session_state["resultado"]

        st.markdown(
            f'<div class="cartao-segmento" style="--cor:{resultado["cor"]}">'
            f"<h2>{resultado['codigo']} · {resultado['persona']}</h2>"
            f"<p>{resultado['ficha']['retrato']}</p></div>",
            unsafe_allow_html=True,
        )

        colunas = st.columns(4)
        colunas[0].metric("Faixa de confiança", resultado["confianca"], border=True)
        colunas[1].metric(
            "Razão de fronteira",
            f"{resultado['razao_de_fronteira']:.4f}",
            f"fronteira a partir de {PACOTE['atribuicao']['corte_de_fronteira']}",
            delta_color="off",
            border=True,
        )
        colunas[2].metric("Segundo mais próximo", resultado["segundo_mais_proximo"], border=True)
        colunas[3].metric(
            "Ação automática",
            "liberada" if resultado["acao_automatica_liberada"] else "bloqueada",
            border=True,
        )

        if not resultado["acao_automatica_liberada"]:
            st.warning(
                f"**Imóvel de fronteira.** A distância até o {resultado['codigo']} e até o "
                f"{resultado['segundo_mais_proximo']} são próximas demais para automatizar a "
                "decisão. Pela regra calibrada no pacote, este imóvel vai para avaliação "
                "humana antes de receber a ação da linha."
            )
        elif resultado["confianca"] == "núcleo":
            st.success(
                "**Imóvel de núcleo.** Está no coração da linha — é o caso em que a ação "
                "padrão pode ser disparada sem revisão."
            )

        if resultado["avisos"]:
            for aviso in resultado["avisos"]:
                st.error(aviso, icon="⚠️")

        esquerda, direita = st.columns([2, 3])

        with esquerda:
            st.subheader("Distância até cada centroide")
            distancias = pd.DataFrame(
                {
                    "codigo": [LINHAS.loc[seg, "codigo"] for seg in resultado["distancias"]],
                    "distancia": list(resultado["distancias"].values()),
                }
            ).sort_values("distancia")
            figura = px.bar(
                distancias,
                x="distancia",
                y="codigo",
                orientation="h",
                text_auto=".3f",
                color="codigo",
                color_discrete_map=CORES_POR_CODIGO,
                labels={"distancia": "distância euclidiana no espaço padronizado", "codigo": ""},
            )
            figura.update_layout(height=280, showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(figura)

        with direita:
            st.subheader(f"O imóvel contra a mediana do {resultado['codigo']}")
            perfil = PACOTE["catalogo"]["perfil_por_linha"].loc[resultado["segmento"]]
            comparacao = pd.DataFrame(
                {
                    "Atributo": [ROTULOS[campo] for campo in ESPACO],
                    "Este imóvel": [resultado["registro"][campo] for campo in ESPACO],
                    f"Mediana do {resultado['codigo']}": [float(perfil[campo]) for campo in ESPACO],
                }
            )
            comparacao["Diferença"] = (
                comparacao["Este imóvel"] - comparacao[f"Mediana do {resultado['codigo']}"]
            )
            st.dataframe(comparacao, hide_index=True, height=280)

        st.subheader("O que fazer com ele")
        ficha = resultado["ficha"]
        colunas = st.columns(2)
        colunas[0].markdown(
            f"**Política de preço**  \n{ficha['politica_de_preco']}\n\n"
            f"**Teto de reforma**  \n{ficha['teto_de_reforma']}\n\n"
            f"**Canal de venda**  \n{ficha['canal']}"
        )
        colunas[1].markdown(
            f"**Ação**  \n{ficha['acao']}\n\n"
            f"**Métrica de acompanhamento**  \n{ficha['metrica']}\n\n"
            f"**Meta**  \n{ficha['meta']}"
        )

        completados = resultado["campos_completados"]
        with st.expander(
            f"Registro efetivamente classificado · {len(completados)} campo(s) completado(s) "
            "pelo contrato"
        ):
            if completados:
                st.caption(
                    "Preenchidos com a mediana do treino: "
                    + ", ".join(ROTULOS[campo] for campo in completados)
                )
            registro = pd.DataFrame(
                {
                    "Atributo": [ROTULOS[campo] for campo in ESPACO],
                    "Valor usado": [resultado["registro"][campo] for campo in ESPACO],
                }
            )
            st.dataframe(registro, hide_index=True)

        saida = pd.DataFrame(
            [
                {
                    **resultado["registro"],
                    **{
                        "segmento": resultado["segmento"],
                        "codigo_segmento": resultado["codigo"],
                        "persona": resultado["persona"],
                        "confianca": resultado["confianca"],
                        "razao_de_fronteira": resultado["razao_de_fronteira"],
                        "acao_automatica_liberada": resultado["acao_automatica_liberada"],
                        "versao_modelo": resultado["versao_modelo"],
                    },
                }
            ]
        )
        st.download_button(
            "Baixar esta classificação (CSV)",
            data=csv_para_download(saida),
            file_name="classificacao-do-imovel.csv",
            mime="text/csv",
        )
    evidencia("contrato", "modelo['pipeline']", "atribuicao", "catalogo['personas']")


# --------------------------------------------------------------------------- #
# 3 · Linhas de produto
# --------------------------------------------------------------------------- #

with abas[2]:
    st.header("As linhas de produto e a ação de cada uma")
    st.markdown(
        "Cada linha nasceu do agrupamento e recebeu leitura de negócio na fase de "
        "avaliação. É esse catálogo que a tela de classificação consulta."
    )

    for segmento, linha in LINHAS.iterrows():
        with st.container(border=True):
            st.markdown(
                f'<div class="cartao-segmento" style="--cor:{linha["cor"]}">'
                f"<h2>{linha['codigo']} · {linha['nome']}</h2>"
                f"<p>{linha['retrato']}</p></div>",
                unsafe_allow_html=True,
            )
            colunas = st.columns(5)
            colunas[0].metric("Imóveis", milhar(linha["imoveis"]))
            colunas[1].metric("Da carteira", f"{linha['pct_carteira']:.1f}%")
            colunas[2].metric("Da receita", f"{linha['pct_receita']:.1f}%")
            colunas[3].metric("Preço mediano", f"US$ {milhar(linha['preco_mediano'])}")
            colunas[4].metric("Na fronteira", f"{linha['pct_na_fronteira']:.1f}%")

            esquerda, direita = st.columns(2)
            esquerda.markdown(
                f"**Política de preço**  \n{linha['politica_de_preco']}\n\n"
                f"**Teto de reforma**  \n{linha['teto_de_reforma']}\n\n"
                f"**Canal**  \n{linha['canal']}"
            )
            direita.markdown(
                f"**Ação**  \n{linha['acao']}\n\n"
                f"**Métrica**  \n{linha['metrica']}\n\n"
                f"**Meta**  \n{linha['meta']}"
            )

    st.subheader("Assinatura dos segmentos")
    st.caption(
        "Quantos desvios-padrão cada linha fica acima ou abaixo da mediana da carteira. "
        "É a leitura de por que os grupos são diferentes — e não apenas caros e baratos."
    )
    assinatura = PACOTE["catalogo"]["assinatura"]
    mapa = go.Figure(
        go.Heatmap(
            z=assinatura[ESPACO].to_numpy(),
            x=[ROTULOS[campo] for campo in ESPACO],
            y=[LINHAS.loc[seg, "codigo"] for seg in assinatura.index],
            colorscale=[[0, CORAL], [0.5, "#FFFFFF"], [1, AZUL_COBALTO]],
            zmid=0,
            text=assinatura[ESPACO].to_numpy(),
            texttemplate="%{text:.2f}",
            colorbar=dict(title="desvios"),
        )
    )
    mapa.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(mapa)

    st.subheader("Perfil mediano de cada linha")
    perfil = PACOTE["catalogo"]["perfil_por_linha"].copy()
    perfil.index = [LINHAS.loc[seg, "codigo"] for seg in perfil.index]
    st.dataframe(perfil.rename(columns=ROTULOS))
    evidencia("catalogo['linhas']", "catalogo['assinatura']", "catalogo['perfil_por_linha']")


# --------------------------------------------------------------------------- #
# 4 · Carteira classificada
# --------------------------------------------------------------------------- #

with abas[3]:
    st.header("A carteira que o pacote publica")
    st.markdown(
        "Os imóveis de treino já classificados, com a faixa de confiança de cada um. "
        "É a lista que a operação usa para separar o que segue automático do que vai "
        "para avaliação humana."
    )

    filtros = st.columns([2, 2, 3])
    escolhidos = filtros[0].multiselect(
        "Linha de produto",
        options=sorted(CARTEIRA["codigo_segmento"].unique()),
        default=sorted(CARTEIRA["codigo_segmento"].unique()),
    )
    faixas = filtros[1].multiselect(
        "Faixa de confiança", options=ORDEM_FAIXAS, default=ORDEM_FAIXAS
    )
    bairros = filtros[2].multiselect(
        "Bairro", options=sorted(CARTEIRA["bairro"].unique()), default=[]
    )

    recorte = CARTEIRA[
        CARTEIRA["codigo_segmento"].isin(escolhidos) & CARTEIRA["confianca"].isin(faixas)
    ]
    if bairros:
        recorte = recorte[recorte["bairro"].isin(bairros)]

    if recorte.empty:
        st.info("Nenhum imóvel atende aos filtros selecionados.")
    else:
        colunas = st.columns(4)
        colunas[0].metric("Imóveis no recorte", milhar(len(recorte)), border=True)
        colunas[1].metric(
            "Ação automática liberada",
            f"{100 * recorte['acao_automatica_liberada'].mean():.1f}%",
            border=True,
        )
        colunas[2].metric(
            "Receita do recorte",
            f"US$ {milhar(recorte['preco_venda'].sum() / 1e6, 1)} mi",
            border=True,
        )
        colunas[3].metric(
            "Preço mediano", f"US$ {milhar(recorte['preco_venda'].median())}", border=True
        )

        esquerda, direita = st.columns([3, 2])
        with esquerda:
            st.subheader("Área habitável × preço realizado")
            figura = px.scatter(
                recorte,
                x="area_habitavel",
                y="preco_venda",
                color="codigo_segmento",
                color_discrete_map=CORES_POR_CODIGO,
                opacity=0.65,
                hover_data=["pid", "bairro", "confianca", "razao_de_fronteira"],
                labels={
                    "area_habitavel": "área habitável (pé²)",
                    "preco_venda": "preço de venda (US$)",
                    "codigo_segmento": "",
                },
            )
            figura.update_layout(height=420, margin=dict(t=10, b=10))
            st.plotly_chart(figura)
            st.caption(
                "O preço aparece no eixo porque é **resultado**, não entrada: nenhum "
                "algoritmo do projeto o enxergou. A separação vertical entre as cores é a "
                "validação externa da segmentação."
            )

        with direita:
            st.subheader("Confiança por linha")
            cruzamento = (
                recorte.groupby(["codigo_segmento", "confianca"]).size().reset_index(name="imoveis")
            )
            figura = px.bar(
                cruzamento,
                x="codigo_segmento",
                y="imoveis",
                color="confianca",
                category_orders={"confianca": ORDEM_FAIXAS},
                color_discrete_sequence=[AZUL_PROFUNDO, AZUL_COBALTO, CORAL],
                text_auto=True,
                labels={"codigo_segmento": "", "imoveis": "imóveis", "confianca": ""},
            )
            figura.update_layout(height=420, margin=dict(t=10, b=10), legend_title_text="")
            st.plotly_chart(figura)

        st.dataframe(recorte, hide_index=True, height=320)
        st.download_button(
            "Baixar o recorte (CSV)",
            data=csv_para_download(recorte),
            file_name="carteira-classificada.csv",
            mime="text/csv",
        )
    evidencia("carteira", "atribuicao['faixas']")


# --------------------------------------------------------------------------- #
# 5 · Classificação em lote
# --------------------------------------------------------------------------- #

with abas[4]:
    st.header("Classificar um lote de imóveis")
    st.markdown(
        "O caminho da carga mensal: um CSV com os atributos do contrato entra, a lista "
        "classificada sai. Coluna ausente é completada com o padrão do contrato; coluna "
        "extra (como matrícula ou bairro) é preservada no resultado."
    )

    modelo_csv = pd.DataFrame([pac.padroes(PACOTE)])[ESPACO]
    esquerda, direita = st.columns([2, 3])
    esquerda.download_button(
        "Baixar modelo de CSV",
        data=csv_para_download(modelo_csv),
        file_name="modelo-de-carga.csv",
        mime="text/csv",
        help="Uma linha com os 17 campos do contrato, preenchida com os valores padrão.",
    )
    separador = direita.radio(
        "Separador do arquivo", options=[";", ","], horizontal=True, help="Padrão do projeto: ;"
    )

    arquivo = st.file_uploader("Arquivo CSV", type=["csv"])
    if arquivo is not None:
        try:
            entrada = pd.read_csv(
                BytesIO(arquivo.getvalue()), sep=separador, decimal="," if separador == ";" else "."
            )
        except Exception as erro:  # noqa: BLE001 - a mensagem vai para a tela
            st.error(f"Não foi possível ler o arquivo: {erro}")
        else:
            ausentes = [campo for campo in ESPACO if campo not in entrada.columns]
            if ausentes:
                st.warning(
                    f"{len(ausentes)} campo(s) do contrato não vieram no arquivo e entraram "
                    "com a mediana do treino: " + ", ".join(ROTULOS[campo] for campo in ausentes)
                )
            faltando = [campo for campo in PACOTE["contrato"]["obrigatorios"] if campo in ausentes]
            if faltando:
                st.error(
                    "Campos **obrigatórios** ausentes: "
                    + ", ".join(ROTULOS[campo] for campo in faltando)
                    + ". O resultado abaixo é apenas indicativo — a carga real seria recusada."
                )

            classificado = pac.classificar_lote(entrada, PACOTE)
            colunas = st.columns(3)
            colunas[0].metric("Imóveis classificados", milhar(len(classificado)), border=True)
            colunas[1].metric(
                "Ação automática liberada",
                f"{100 * classificado['acao_automatica_liberada'].mean():.1f}%",
                border=True,
            )
            colunas[2].metric(
                "Em fronteira",
                milhar((classificado["confianca"] == "fronteira").sum()),
                border=True,
            )

            distribuicao = (
                classificado.groupby("codigo_segmento").size().reset_index(name="imoveis")
            )
            figura = px.bar(
                distribuicao,
                x="codigo_segmento",
                y="imoveis",
                color="codigo_segmento",
                color_discrete_map=CORES_POR_CODIGO,
                text_auto=True,
                labels={"codigo_segmento": "", "imoveis": "imóveis"},
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
    evidencia("contrato['padroes']", "modelo['pipeline']", "atribuicao")


# --------------------------------------------------------------------------- #
# 6 · Monitoramento
# --------------------------------------------------------------------------- #

with abas[5]:
    st.header("O modelo em operação")
    monitor = PACOTE["monitoramento"]
    painel = monitor["painel"]

    st.subheader("Painel de indicadores")
    colunas = st.columns(3)
    for posicao, (_, linha) in enumerate(painel.iterrows()):
        icone = {"folga": "🟢", "margem estreita": "🟡"}.get(linha["situacao"], "🔴")
        colunas[posicao % 3].metric(
            f"{icone} {linha['indicador']}",
            f"{linha['valor']:.4g}",
            f"{linha['sentido']} de {linha['limiar']:.4g}",
            delta_color="off",
            border=True,
        )

    limiares = monitor["limiares"]
    st.caption(
        f"Limiares vigentes — PSI de atenção {limiares['psi_atencao']}, PSI de ação "
        f"{limiares['psi_acao']}, piso de silhueta {limiares['piso_de_silhueta']}, "
        f"piso de ARI {limiares['piso_de_ari']}."
    )

    st.subheader("Plano de monitoramento")
    st.dataframe(monitor["plano"], hide_index=True)

    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Gatilhos de reciclagem")
        st.dataframe(monitor["gatilhos_de_reciclagem"], hide_index=True)
    with direita:
        st.subheader("Critério de aceite da reciclagem")
        st.dataframe(monitor["criterio_de_aceite"], hide_index=True)

    st.subheader("Calibração do corte de fronteira")
    st.caption(
        "A regra que decide quando a ação automática dispara não foi escolhida por "
        "intuição: os cortes saíram desta varredura, maximizando o F1 na identificação "
        "da silhueta negativa sob o teto operacional."
    )
    calibracao = PACOTE["atribuicao"]["calibracao"]
    figura = px.line(
        calibracao,
        x="corte",
        y=["precisao", "revocacao", "f1"],
        color_discrete_sequence=[AZUL_COBALTO, CORAL, AZUL_PROFUNDO],
        labels={"corte": "corte da razão de fronteira", "value": "", "variable": ""},
    )
    figura.add_vline(
        x=PACOTE["atribuicao"]["corte_de_fronteira"],
        line_dash="dash",
        line_color=CINZA,
        annotation_text="corte publicado",
    )
    figura.update_layout(height=340, margin=dict(t=10, b=10))
    st.plotly_chart(figura)

    st.subheader("Faixas de confiança por linha (%)")
    st.dataframe(
        PACOTE["atribuicao"]["faixas_por_segmento"].rename(
            index={seg: LINHAS.loc[seg, "codigo"] for seg in LINHAS.index}
        )
    )
    evidencia("monitoramento", "atribuicao['calibracao']", "atribuicao['faixas_por_segmento']")


# --------------------------------------------------------------------------- #
# 7 · O pacote
# --------------------------------------------------------------------------- #

with abas[6]:
    st.header("De onde vem o que esta tela mostra")
    st.markdown(
        f"Toda a aplicação é servida por **um arquivo**: `models/{pac.CAMINHO_PACOTE.name}` "
        f"({milhar(pac.CAMINHO_PACOTE.stat().st_size / 1024)} KB, formato "
        f"`{PACOTE['formato']}`). Ele não importa nada de `src/`: o pipeline, o contrato, "
        "o catálogo e a carteira viajam juntos."
    )

    st.subheader("Instruções de uso gravadas no pacote")
    st.info(PACOTE["leia_me"])

    esquerda, direita = st.columns(2)
    with esquerda:
        st.subheader("Espaço de atributos publicado")
        st.dataframe(
            CAMPOS.rename(
                columns={
                    "campo": "Campo",
                    "rotulo": "Rótulo",
                    "tipo": "Tipo",
                    "obrigatorio": "Obrigatório",
                    "observado_minimo": "Mín. observado",
                    "observado_maximo": "Máx. observado",
                    "aceito_minimo": "Mín. aceito",
                    "aceito_maximo": "Máx. aceito",
                    "padrao": "Padrão",
                }
            ),
            hide_index=True,
            height=380,
        )
    with direita:
        st.subheader("Carimbo de origem")
        st.caption(
            "SHA-256 de cada artefato que originou o pacote. É o que permite provar, meses "
            "depois, que a tela está servindo o modelo aprovado na fase de avaliação."
        )
        carimbos = pd.DataFrame(
            {
                "Artefato": list(PACOTE["carimbo_de_origem"]),
                "SHA-256": [f"{valor[:16]}…" for valor in PACOTE["carimbo_de_origem"].values()],
            }
        )
        st.dataframe(carimbos, hide_index=True)
        st.markdown(
            f"**Versão do modelo:** {PACOTE['versao_modelo']}  \n"
            f"**Algoritmo:** {MODELO['algoritmo']} · k={MODELO['k']} · "
            f"semente {MODELO['semente']}  \n"
            f"**Treino:** {milhar(MODELO['imoveis_de_treino'])} imóveis · "
            f"{MODELO['periodo_de_treino']}  \n"
            f"**Pré-processador:** `{type(MODELO['pipeline'].named_steps['preparo']).__name__}` "
            "serializado junto — a tela não recalcula padronização."
        )

    st.subheader("Evidências que viajaram com o pacote")
    nomes = {
        "resultados": "Resultados contra os critérios",
        "insights": "Insights registrados",
        "entregas": "Entregas e consumidores",
        "janelas": "Janelas de implantação",
        "deliberacoes": "Deliberações pendentes",
        "backlog_da_fase_5": "Backlog da fase 5",
        "auditoria_do_publicado": "Auditoria do publicado",
    }
    escolhida = st.selectbox(
        "Evidência", options=list(nomes), format_func=lambda chave: nomes[chave]
    )
    st.dataframe(PACOTE["evidencias"][escolhida], hide_index=True)
    evidencia("leia_me", "carimbo_de_origem", "contrato['campos']", "evidencias")
