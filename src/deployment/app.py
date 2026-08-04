"""Aplicação Streamlit — a entrega da fase de implantação do CRISP-DM.

É o ponto em que o ciclo se fecha: o resultado da modelagem deixa de ser um
notebook e vira algo que o corretor abre no navegador para decidir o que fazer
com um imóvel.

Execute com ``uv run invoke app`` ou
``uv run streamlit run src/deployment/app.py``.

As sete abas correspondem às perguntas que a diretoria fez, e cada uma aponta a
evidência que a sustenta — o mesmo CSV que o relatório cita.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.data import dicionario as dic
from src.data.preparacao import construir_matriz_modelagem, preparar_espaco
from src.deployment import monitoramento as mon
from src.deployment.scoring import PADROES, classificar
from src.model import personas as pers
from src.model.particional import metricas_internas
from src.utils.io import ler_json

st.set_page_config(
    page_title="Meridiano · Segmentação da carteira",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = f"""
<style>
    .bloco-persona {{
        border-left: 6px solid var(--cor); border-radius: 6px;
        padding: 0.9rem 1.1rem; margin-bottom: 0.8rem;
        background: rgba(27, 73, 101, 0.06);
    }}
    .bloco-persona h4 {{ margin: 0 0 .35rem 0; color: {config.AZUL_PROFUNDO}; }}
    .rodape-evidencia {{
        font-size: 0.78rem; color: #6B7C88; border-top: 1px solid #E6EBEF;
        padding-top: .5rem; margin-top: 1.2rem;
    }}
    div[data-testid="stMetricValue"] {{ font-size: 1.55rem; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #


@st.cache_data(show_spinner="Carregando a carteira…")
def carregar_carteira() -> pd.DataFrame:
    """Lê a base já segmentada, produzida pela fase de modelagem."""
    return pd.read_parquet(config.SEGMENTOS)


@st.cache_data(show_spinner=False)
def carregar_tabela(secao: str, nome: str) -> pd.DataFrame:
    """Lê uma tabela de evidência de ``reports/tables``."""
    return pd.read_csv(config.TABLES / secao / f"{nome}.csv", sep=";", decimal=",")


@st.cache_data(show_spinner=False)
def carregar_metadados() -> dict:
    """Lê os metadados do modelo publicado."""
    return ler_json(config.MODELS / "metadados_segmentacao.json")


@st.cache_data(show_spinner=False)
def espaco_de_atributos(carteira: pd.DataFrame):
    """Reconstrói o espaço padronizado, para as métricas calculadas ao vivo."""
    matriz = construir_matriz_modelagem(carteira, salvar=False)
    dados, _ = preparar_espaco(matriz, "padrao")
    return dados


def evidencia(*caminhos: str) -> None:
    """Rodapé que aponta o arquivo de onde cada número veio."""
    st.markdown(
        '<div class="rodape-evidencia">Evidência: '
        + " · ".join(f"<code>{caminho}</code>" for caminho in caminhos)
        + "</div>",
        unsafe_allow_html=True,
    )


if not (config.SEGMENTOS.exists() and (config.MODELS / "pipeline_segmentacao.joblib").exists()):
    st.error(
        "Os artefatos do modelo ainda não existem. Execute o pipeline antes de abrir a "
        "aplicação:\n\n```bash\nuv run invoke pipeline\n```"
    )
    st.stop()

carteira = carregar_carteira()
metadados = carregar_metadados()
CORES = {pers.codigo(s): pers.PERSONAS[s]["cor"] for s in sorted(pers.PERSONAS)}


# --------------------------------------------------------------------------- #
# Barra lateral
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.title("🏘️ Meridiano")
    st.caption("Segmentação não supervisionada da carteira residencial")
    st.divider()
    st.metric("Imóveis na carteira", f"{len(carteira):,}".replace(",", "."))
    st.metric("Segmentos", metadados["k"])
    st.metric("Silhueta", f"{metadados['silhueta']:.4f}")
    st.metric("Estabilidade (ARI)", f"{metadados['estabilidade_ari']:.3f}")
    st.divider()
    st.caption(
        f"Modelo `{metadados['versao_modelo']}` · {metadados['algoritmo']}\n\n"
        f"Treino: {metadados['registros_treino']} imóveis · {metadados['periodo_treino']}"
    )
    st.caption(
        "O preço de venda **não** entrou na modelagem: é rótulo reservado, usado apenas "
        "na avaliação a posteriori."
    )

abas = st.tabs(
    [
        "Visão executiva",
        "Personas e ações",
        "Explorar a carteira",
        "Classificar um imóvel",
        "Padrões de coocorrência",
        "Monitoramento",
        "Como chegamos aqui",
    ]
)


# --------------------------------------------------------------------------- #
# 1 · Visão executiva
# --------------------------------------------------------------------------- #

with abas[0]:
    st.header("As quatro perguntas da diretoria")

    valor = carregar_tabela("avaliacao", "a2-valor-por-segmento")
    criterios = carregar_tabela("avaliacao", "a1-confronto-criterios")

    colunas = st.columns(4)
    colunas[0].metric("Quantos grupos existem", metadados["k"], "de 2 a 5 pelo orçamento")
    colunas[1].metric(
        "Maior segmento em receita",
        valor.loc[valor["pct_receita"].idxmax(), "código"],
        f"{valor['pct_receita'].max():.1f}% da receita",
    )
    colunas[2].metric(
        "Imóveis fora de padrão",
        int(carteira["fora_de_padrao_dbscan"].sum()),
        f"{100 * carteira['fora_de_padrao_dbscan'].mean():.1f}% da carteira",
    )
    colunas[3].metric(
        "Critérios de aceite atendidos",
        f"{int((criterios['situacao'] == 'atendido').sum())} de {len(criterios)}",
    )

    st.markdown(
        """
> **1. Quantos grupos existem, e por que esse número?**
>
> Quatro. As métricas de coesão sozinhas apontariam dois — mas dois grupos são
> "caro" e "barato", que a diretoria já sabe. Cinco, que o orçamento comportaria,
> não sobrevive ao teste de estabilidade: sob reamostragem de 80% da carteira, o
> índice de Rand ajustado cai de **0,94 para 0,44**. Quatro é o maior número de
> linhas de produto que é simultaneamente estável, coeso acima do mínimo e
> operável dentro do orçamento.
"""
    )

    esquerda, direita = st.columns([3, 2])
    with esquerda:
        composicao = (
            carteira.groupby("codigo_segmento")
            .agg(imoveis=("pid", "size"), receita=("preco_venda", "sum"))
            .reset_index()
        )
        composicao["% das unidades"] = 100 * composicao["imoveis"] / composicao["imoveis"].sum()
        composicao["% da receita"] = 100 * composicao["receita"] / composicao["receita"].sum()
        longo = composicao.melt(
            id_vars="codigo_segmento",
            value_vars=["% das unidades", "% da receita"],
            var_name="medida",
            value_name="percentual",
        )
        figura = px.bar(
            longo, x="codigo_segmento", y="percentual", color="medida", barmode="group",
            text_auto=".1f", color_discrete_sequence=[config.AZUL_COBALTO, config.CORAL],
            labels={"codigo_segmento": "", "percentual": "%"},
            title="Unidades × receita — onde está o dinheiro",
        )
        figura.update_layout(height=380, legend_title_text="")
        st.plotly_chart(figura, use_container_width=True)
    with direita:
        figura = px.pie(
            composicao, names="codigo_segmento", values="imoveis", hole=0.55,
            color="codigo_segmento", color_discrete_map=CORES,
            title="Composição da carteira",
        )
        figura.update_traces(textinfo="percent+label")
        figura.update_layout(height=380, showlegend=False)
        st.plotly_chart(figura, use_container_width=True)

    st.subheader("Confronto com os critérios de aceite")
    st.dataframe(
        criterios[["objetivo", "criterio", "meta", "obtido", "situacao"]],
        use_container_width=True, hide_index=True,
    )
    evidencia(
        "reports/tables/avaliacao/a1-confronto-criterios.csv",
        "reports/tables/avaliacao/a2-valor-por-segmento.csv",
    )


# --------------------------------------------------------------------------- #
# 2 · Personas e ações
# --------------------------------------------------------------------------- #

with abas[1]:
    st.header("O que caracteriza cada grupo, e o que fazer com ele")
    st.caption(
        "A resposta à segunda e à quarta pergunta da diretoria. Cada segmento tem nome, "
        "ação diferenciada e métrica de acompanhamento — sem os três, o agrupamento não "
        "vira decisão."
    )

    valor = carregar_tabela("avaliacao", "a2-valor-por-segmento").set_index("código")
    medoides = carregar_tabela("modelagem", "m13-medoides-reais")

    for indice in sorted(pers.PERSONAS):
        persona = pers.PERSONAS[indice]
        codigo = persona["codigo"]
        recorte = carteira[carteira["segmento"] == indice]
        with st.container(border=True):
            titulo, metricas = st.columns([3, 2])
            with titulo:
                st.markdown(
                    f'<div class="bloco-persona" style="--cor:{persona["cor"]}">'
                    f"<h4>{codigo} — {persona['nome']}</h4>{persona['resumo']}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Ação diferenciada.** {persona['acao']}")
                st.markdown(f"**Como saberemos se funcionou.** {persona['metrica']}")
                st.markdown(f"**Canal.** {persona['canal']}")
            with metricas:
                st.metric(
                    "Imóveis", f"{len(recorte):,}".replace(",", "."),
                    f"{100 * len(recorte) / len(carteira):.1f}% da carteira",
                )
                st.metric(
                    "Preço mediano",
                    f"US$ {recorte['preco_venda'].median():,.0f}".replace(",", "."),
                )
                st.metric("Preço por pé²", f"US$ {recorte['preco_por_pe2'].median():.0f}")
                st.metric("% da receita", f"{valor.loc[codigo, 'pct_receita']:.1f}%")
                medoide = medoides[medoides["segmento"] == indice].iloc[0]
                st.caption(
                    f"**Imóvel representante (medoide):** PID `{medoide['pid']}` · "
                    f"{medoide['bairro']} · {medoide['area_habitavel']} pés² · "
                    f"qualidade {medoide['qualidade_geral']} · {medoide['idade_imovel']} anos"
                )

    st.subheader("Assinatura dos segmentos")
    st.caption(
        "Quanto cada segmento se afasta da mediana da carteira, em escala robusta. "
        "Vermelho: acima. Azul: abaixo."
    )
    assinatura = carregar_tabela("modelagem", "m13-assinatura").set_index("segmento")
    assinatura.index = [pers.codigo(int(indice)) for indice in assinatura.index]
    assinatura.columns = [dic.rotulo(coluna) for coluna in assinatura.columns]
    figura = px.imshow(
        assinatura.T, color_continuous_scale="RdBu_r", color_continuous_midpoint=0,
        aspect="auto", text_auto=".1f", labels={"color": "desvios da mediana"},
    )
    figura.update_layout(height=560, xaxis_title="", yaxis_title="")
    st.plotly_chart(figura, use_container_width=True)
    evidencia(
        "reports/tables/modelagem/m14-personas.csv",
        "reports/tables/modelagem/m13-assinatura.csv",
        "reports/tables/modelagem/m13-medoides-reais.csv",
    )


# --------------------------------------------------------------------------- #
# 3 · Explorar a carteira
# --------------------------------------------------------------------------- #

with abas[2]:
    st.header("Explorar a carteira")

    filtros = st.columns(4)
    escolhidos = filtros[0].multiselect(
        "Segmentos", sorted(carteira["codigo_segmento"].unique()),
        default=sorted(carteira["codigo_segmento"].unique()),
    )
    bairros = filtros[1].multiselect("Bairros", sorted(carteira["bairro"].unique()))
    faixa_anos = filtros[2].slider(
        "Ano da venda", int(carteira["ano_venda"].min()), int(carteira["ano_venda"].max()),
        (int(carteira["ano_venda"].min()), int(carteira["ano_venda"].max())),
    )
    apenas_atipicos = filtros[3].toggle("Só imóveis fora de padrão", value=False)

    recorte = carteira[
        carteira["codigo_segmento"].isin(escolhidos)
        & carteira["ano_venda"].between(*faixa_anos)
    ]
    if bairros:
        recorte = recorte[recorte["bairro"].isin(bairros)]
    if apenas_atipicos:
        recorte = recorte[recorte["fora_de_padrao_dbscan"]]

    if recorte.empty:
        st.warning("Nenhum imóvel atende aos filtros escolhidos.")
    else:
        indicadores = st.columns(4)
        indicadores[0].metric("Imóveis", f"{len(recorte):,}".replace(",", "."))
        indicadores[1].metric(
            "Área mediana", f"{recorte['area_habitavel'].median():,.0f} pés²".replace(",", ".")
        )
        indicadores[2].metric("Idade mediana", f"{recorte['idade_imovel'].median():.0f} anos")
        indicadores[3].metric(
            "Preço mediano", f"US$ {recorte['preco_venda'].median():,.0f}".replace(",", ".")
        )

        eixos = st.columns(2)
        eixo_x = eixos[0].selectbox(
            "Eixo horizontal", dic.NUMERICAS + dic.ORDINAIS, index=0, format_func=dic.rotulo
        )
        eixo_y = eixos[1].selectbox(
            "Eixo vertical", dic.NUMERICAS + dic.ORDINAIS, index=11, format_func=dic.rotulo
        )
        figura = px.scatter(
            recorte, x=eixo_x, y=eixo_y, color="codigo_segmento", color_discrete_map=CORES,
            opacity=0.6, hover_data=["pid", "bairro", "persona", "preco_venda"],
            labels={eixo_x: dic.rotulo(eixo_x), eixo_y: dic.rotulo(eixo_y),
                    "codigo_segmento": "segmento"},
            marginal_x="box", marginal_y="box",
        )
        figura.update_layout(height=620)
        st.plotly_chart(figura, use_container_width=True)

        with st.expander("Ver a tabela de imóveis"):
            st.dataframe(
                recorte[
                    ["pid", "codigo_segmento", "persona", "bairro", "area_habitavel",
                     "qualidade_geral", "idade_imovel", "dormitorios", "banheiros_total",
                     "ano_venda", "preco_venda", "confianca_gmm", "fora_de_padrao_dbscan"]
                ],
                use_container_width=True, hide_index=True,
            )
            st.download_button(
                "Baixar recorte em CSV",
                recorte.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name="carteira_filtrada.csv", mime="text/csv",
            )
    evidencia("data/processed/imoveis_segmentados.parquet")


# --------------------------------------------------------------------------- #
# 4 · Classificar um imóvel
# --------------------------------------------------------------------------- #

with abas[3]:
    st.header("Classificar um imóvel novo")
    st.caption(
        "O caso de uso do Comitê de Aquisição: antes de comprar, saber em que linha de "
        "produto o imóvel cai e qual política se aplica a ele."
    )

    with st.form("classificacao"):
        linha1 = st.columns(4)
        area_habitavel = linha1[0].number_input(
            "Área habitável (pés²)", 300, 4000, int(PADROES["area_habitavel"]), 10
        )
        area_porao = linha1[1].number_input(
            "Área do porão (pés²)", 0, 3500, int(PADROES["area_porao"]), 10
        )
        area_terreno = linha1[2].number_input(
            "Área do terreno (pés²)", 1000, 60000, int(PADROES["area_terreno"]), 100
        )
        area_garagem = linha1[3].number_input(
            "Área da garagem (pés²)", 0, 1500, int(PADROES["area_garagem"]), 10
        )

        linha2 = st.columns(4)
        comodos = linha2[0].number_input("Cômodos acima do solo", 2, 15, int(PADROES["comodos"]))
        dormitorios = linha2[1].number_input("Dormitórios", 0, 8, int(PADROES["dormitorios"]))
        banheiros = linha2[2].number_input(
            "Banheiros equivalentes", 0.5, 7.0, float(PADROES["banheiros_total"]), 0.5
        )
        lareiras = linha2[3].number_input("Lareiras", 0, 4, int(PADROES["lareiras"]))

        linha3 = st.columns(4)
        idade = linha3[0].slider("Idade do imóvel (anos)", 0, 140, int(PADROES["idade_imovel"]))
        reforma = linha3[1].slider(
            "Anos desde a reforma", 0, 60, int(PADROES["anos_desde_reforma"])
        )
        varandas = linha3[2].number_input(
            "Área de varandas (pés²)", 0, 1500, int(PADROES["area_varandas"]), 10
        )
        segundo_pavimento = linha3[3].toggle("Tem segundo pavimento", value=False)

        linha4 = st.columns(5)
        qualidade = linha4[0].slider(
            "Qualidade geral (1–10)", 1, 10, int(PADROES["qualidade_geral"])
        )
        conservacao = linha4[1].slider(
            "Conservação (1–10)", 1, 10, int(PADROES["conservacao_geral"])
        )
        qualidade_externa = linha4[2].slider(
            "Qualidade externa (0–5)", 0, 5, int(PADROES["qualidade_externa"])
        )
        qualidade_cozinha = linha4[3].slider(
            "Qualidade da cozinha (0–5)", 0, 5, int(PADROES["qualidade_cozinha"])
        )
        acabamento_garagem = linha4[4].slider(
            "Acabamento da garagem (0–3)", 0, 3, int(PADROES["acabamento_garagem"])
        )

        qualidade_porao = st.slider(
            "Qualidade do porão (0 = sem porão, 5 = excelente)", 0, 5,
            int(PADROES["qualidade_porao"]),
        )
        enviado = st.form_submit_button("Classificar", type="primary", use_container_width=True)

    if enviado:
        resultado = classificar(
            {
                "area_habitavel": area_habitavel, "area_porao": area_porao,
                "area_terreno": area_terreno, "area_garagem": area_garagem,
                "area_varandas": varandas, "banheiros_total": banheiros, "comodos": comodos,
                "dormitorios": dormitorios, "lareiras": lareiras, "idade_imovel": idade,
                "anos_desde_reforma": reforma, "qualidade_geral": qualidade,
                "conservacao_geral": conservacao, "qualidade_externa": qualidade_externa,
                "qualidade_cozinha": qualidade_cozinha, "qualidade_porao": qualidade_porao,
                "acabamento_garagem": acabamento_garagem,
                "tem_segundo_pavimento": int(segundo_pavimento),
            }
        )

        esquerda, direita = st.columns([3, 2])
        with esquerda:
            st.markdown(
                f'<div class="bloco-persona" style="--cor:{resultado["cor"]}">'
                f"<h4>{resultado['codigo']} — {resultado['persona']}</h4>"
                f"{resultado['resumo']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Política que se aplica.** {resultado['acao']}")
            st.markdown(f"**Métrica de acompanhamento.** {resultado['metrica']}")

            if resultado["confianca"] == "fronteira":
                st.warning(
                    f"**Imóvel de fronteira.** A distância ao segundo segmento mais próximo "
                    f"({resultado['segundo_mais_proximo']}) é quase igual à distância ao "
                    "escolhido. A ação automática **não** deve ser disparada sem avaliação "
                    "humana."
                )
            elif resultado["confianca"] == "típico":
                st.info(
                    "Classificação típica, com alguma proximidade de "
                    f"{resultado['segundo_mais_proximo']}."
                )
            else:
                st.success(
                    "Imóvel no núcleo do segmento: a política padrão se aplica sem ressalva."
                )

        with direita:
            distancias = pd.DataFrame(
                {
                    "segmento": list(resultado["distancias"]),
                    "distância": list(resultado["distancias"].values()),
                }
            )
            figura = px.bar(
                distancias.sort_values("distância"), x="distância", y="segmento",
                orientation="h", color="segmento", color_discrete_map=CORES,
                title="Distância ao centroide de cada segmento", text_auto=".2f",
            )
            figura.update_layout(height=330, showlegend=False, yaxis_title="")
            st.plotly_chart(figura, use_container_width=True)
            st.caption(
                f"Confiança: **{resultado['confianca']}** · razão de fronteira "
                f"{resultado['razao_fronteira']} · modelo `{resultado['versao_modelo']}`"
            )

        with st.expander("Ver o registro efetivamente enviado ao modelo"):
            st.caption(
                "Os campos não preenchidos assumem a mediana da carteira, e as flags "
                "binárias são derivadas — não pedidas — para evitar entrada inconsistente."
            )
            st.dataframe(
                pd.DataFrame(
                    {
                        "atributo": [dic.rotulo(c) for c in resultado["registro"]],
                        "valor": list(resultado["registro"].values()),
                    }
                ),
                use_container_width=True, hide_index=True,
            )
    evidencia("models/pipeline_segmentacao.joblib", "src/deployment/scoring.py")


# --------------------------------------------------------------------------- #
# 5 · Padrões de coocorrência
# --------------------------------------------------------------------------- #

with abas[4]:
    st.header("Que padrões existem dentro dos dados")
    st.caption(
        "A terceira pergunta da diretoria. Regras mineradas com Apriori, Eclat e FP-Growth "
        "— os três devolvem exatamente os mesmos conjuntos frequentes."
    )

    comparativo = carregar_tabela("associacao", "r1-comparativo-algoritmos")
    funil = carregar_tabela("associacao", "r2-funil-de-poda")
    principais = carregar_tabela("associacao", "r2-principais-regras")
    diferenciais = carregar_tabela("associacao", "r3-regras-diferenciais")
    tautologias = carregar_tabela("associacao", "r2-tautologias-descartadas")

    colunas = st.columns(3)
    colunas[0].metric("Conjuntos frequentes", int(comparativo["conjuntos_frequentes"].iloc[0]))
    colunas[1].metric("Regras após toda a poda", int(funil["quantidade"].iloc[-1]))
    colunas[2].metric(
        "Algoritmos com resultado idêntico",
        f"{int(comparativo['identico_ao_apriori'].sum())} de 3",
    )

    st.subheader("Funil de poda")
    st.dataframe(funil, use_container_width=True, hide_index=True)

    st.subheader("Regras que sobreviveram")
    st.dataframe(principais, use_container_width=True, hide_index=True)

    st.subheader("Padrões que só valem dentro de um segmento")
    st.caption(
        "É o cruzamento que valida a segmentação: se as regras de cada grupo fossem as "
        "mesmas da base inteira, o agrupamento não teria achado nada."
    )
    escolha = st.selectbox("Segmento", sorted(diferenciais["persona"].unique()))
    st.dataframe(
        diferenciais[diferenciais["persona"] == escolha][
            ["regra", "suporte_no_segmento", "confianca", "lift_no_segmento", "lift_na_base",
             "diferenca"]
        ],
        use_container_width=True, hide_index=True,
    )

    with st.expander("Regras descartadas por tautologia — e por que nenhuma métrica as pega"):
        st.markdown(
            "Uma casa de estilo `2Story` tem segundo pavimento porque é isso que `2Story` "
            "significa. Suporte, confiança e lift são altos **justamente** porque a relação "
            "é perfeita. Só o conhecimento do domínio separa a tautologia da descoberta."
        )
        st.dataframe(tautologias, use_container_width=True, hide_index=True)
    evidencia(
        "reports/tables/associacao/r1-comparativo-algoritmos.csv",
        "reports/tables/associacao/r2-principais-regras.csv",
        "reports/tables/associacao/r3-regras-diferenciais.csv",
    )


# --------------------------------------------------------------------------- #
# 6 · Monitoramento
# --------------------------------------------------------------------------- #

with abas[5]:
    st.header("Monitoramento do modelo em operação")
    st.markdown(
        "Um agrupamento **não tem gabarito**: não existe erro de previsão para acompanhar. "
        "O que se monitora é a entrada mudar de distribuição (*data drift*) e os grupos "
        "perderem coesão (*cluster drift*)."
    )

    corte = st.slider(
        "Ano de corte entre referência e acompanhamento",
        int(carteira["ano_venda"].min()) + 1, int(carteira["ano_venda"].max()), 2009,
        help="Arraste para simular outro recorte temporal e ver como os indicadores reagem.",
    )
    referencia = carteira[carteira["ano_venda"] < corte]
    atual = carteira[carteira["ano_venda"] >= corte]

    if len(atual) < 50 or len(referencia) < 50:
        st.warning("Recorte pequeno demais para uma leitura confiável.")
    else:
        drift = mon.avaliar_drift(atual, referencia)
        espaco = espaco_de_atributos(carteira)
        marcador = (carteira["ano_venda"] >= corte).to_numpy()
        coesao = metricas_internas(espaco[marcador], carteira["segmento"].to_numpy()[marcador])
        saude = mon.resumo_de_saude(drift, coesao["silhueta"])

        indicadores = st.columns(4)
        indicadores[0].metric("Veredicto", saude["veredicto"])
        indicadores[1].metric("Atributos em ação", saude["atributos_em_acao"])
        indicadores[2].metric("Atributos em atenção", saude["atributos_em_atencao"])
        indicadores[3].metric("Silhueta no período", f"{saude['coesao_atual']:.4f}")
        st.caption(f"Gatilho de reciclagem: {saude['gatilho']}")

        esquerda, direita = st.columns([3, 2])
        with esquerda:
            figura = px.bar(
                drift.sort_values("psi"), x="psi", y="atributo", orientation="h",
                color="situacao",
                color_discrete_map={"estável": config.VERDE, "atenção": config.AMARELO,
                                    "ação": config.CORAL},
                title=f"Data drift — PSI de cada atributo (antes × a partir de {corte})",
            )
            figura.add_vline(x=mon.LIMIAR_ATENCAO, line_dash="dash", line_color=config.AMARELO)
            figura.add_vline(x=mon.LIMIAR_ACAO, line_dash="dash", line_color=config.CORAL)
            figura.update_layout(height=520, yaxis_title="")
            st.plotly_chart(figura, use_container_width=True)
        with direita:
            st.subheader("Cluster drift — composição")
            st.dataframe(
                mon.avaliar_composicao(atual["codigo_segmento"], referencia["codigo_segmento"]),
                use_container_width=True,
            )

            participacao = (
                carteira.groupby(["ano_venda", "codigo_segmento"]).size().unstack(fill_value=0)
            )
            participacao = 100 * participacao.div(participacao.sum(axis=1), axis=0)
            figura = go.Figure()
            for coluna in sorted(participacao.columns):
                figura.add_trace(
                    go.Scatter(
                        x=participacao.index, y=participacao[coluna], name=coluna,
                        mode="lines+markers", line={"color": CORES[coluna], "width": 3},
                    )
                )
            figura.add_vline(x=corte - 0.5, line_dash="dash", line_color=config.CINZA)
            figura.update_layout(
                height=320, yaxis_title="% das vendas do ano", title="Participação por ano",
                margin={"t": 40},
            )
            st.plotly_chart(figura, use_container_width=True)

        with st.expander("Plano de monitoramento — o que dispara o quê, e quem responde"):
            st.dataframe(
                carregar_tabela("implantacao", "i3-plano-de-monitoramento"),
                use_container_width=True, hide_index=True,
            )
        with st.expander("Plano de reciclagem"):
            st.dataframe(
                carregar_tabela("implantacao", "i4-plano-de-reciclagem"),
                use_container_width=True, hide_index=True,
            )
            st.dataframe(
                carregar_tabela("implantacao", "i4-criterio-de-aceite-da-reciclagem"),
                use_container_width=True, hide_index=True,
            )
    evidencia(
        "models/linha_de_base.json",
        "reports/tables/implantacao/i1-drift-por-atributo.csv",
        "reports/tables/implantacao/i3-plano-de-monitoramento.csv",
    )


# --------------------------------------------------------------------------- #
# 7 · Como chegamos aqui
# --------------------------------------------------------------------------- #

with abas[6]:
    st.header("Como chegamos aqui")
    st.caption(
        "A rastreabilidade do CRISP-DM: cada decisão, o critério que a sustenta e o "
        "arquivo que a comprova."
    )

    fases = {
        "1 · Entendimento de negócio": [
            ("Problema", "segmentar a carteira residencial em no máximo cinco linhas de "
                         "produto com ação diferenciada", "docs/entendimento-negocio.md"),
            ("Critério técnico", f"silhueta ≥ {config.SILHUETA_MINIMA}, k entre "
                                 f"{config.K_MINIMO_NEGOCIO} e {config.K_MAXIMO_NEGOCIO}, "
                                 f"ruído ≤ {config.RUIDO_MAXIMO:.0%}",
             "docs/criterios-sucesso.md"),
        ],
        "2 · Entendimento dos dados": [
            ("Origem", "Ames Housing (De Cock, 2011) — 2.930 imóveis × 82 colunas, "
                       "download direto do artigo original", "docs/fonte-dados.md"),
            ("Achado de qualidade", "a categoria `None` de `Mas Vnr Type` virava nulo na "
                                    "leitura padrão: 60,6% de ausência aparente contra 0,8% "
                                    "real", "reports/tables/eda/f5-inventario-sentinelas.csv"),
            ("EDA", "oito fases percorridas, com insights registrados",
             "reports/tables/eda/colecao-de-insights.csv"),
        ],
        "3 · Preparação dos dados": [
            ("Rótulo reservado", "`preco_venda` fora da modelagem; `bairro` reservado para "
                                 "validação externa", "src/data/dicionario.py"),
            ("Regras de limpeza", "10 regras, cada uma com o motivo registrado",
             "docs/preparacao.md"),
            ("Escala", "`log1p` em 3 variáveis assimétricas e `StandardScaler`",
             "reports/tables/modelagem/m4-sensibilidade-escala.csv"),
        ],
        "4 · Modelagem": [
            ("Espaço de atributos", "21 variáveis: 11 numéricas, 6 ordinais e 4 binárias "
                                    "derivadas",
             "reports/tables/modelagem/m1-espacos-de-atributos.csv"),
            ("Escolha de k", "quatro métricas, estabilidade e teto operacional → k = 4",
             "reports/tables/modelagem/m2-decisao-de-k.csv"),
            ("Algoritmos comparados", "K-Means, K-Medoids/Gower, hierárquica, DBSCAN, "
                                      "Mean Shift e GMM",
             "reports/tables/modelagem/m12-matriz-comparativa.csv"),
            ("Regras de associação", "Apriori, Eclat e FP-Growth com resultado idêntico",
             "reports/tables/associacao/r1-comparativo-algoritmos.csv"),
        ],
        "5 · Avaliação": [
            ("Critérios de aceite", "13 de 13 atendidos",
             "reports/tables/avaliacao/a1-confronto-criterios.csv"),
            ("Não é tabela de preço", "ARI de 0,31 contra os quartis de preço",
             "reports/tables/avaliacao/a2-concordancia-com-preco.csv"),
            ("Hipóteses derrubadas", "três registradas, com a evidência que as derrubou",
             "reports/tables/avaliacao/a7-limitacoes-e-hipoteses.csv"),
        ],
        "6 · Implantação": [
            ("Artefato", "pipeline serializado que reproduz 100% da classificação de treino",
             "models/pipeline_segmentacao.joblib"),
            ("Monitoramento", "PSI por atributo, coesão por período e composição, com "
                              "gatilhos",
             "reports/tables/implantacao/i3-plano-de-monitoramento.csv"),
            ("Entrega", "esta aplicação", "src/deployment/app.py"),
        ],
    }

    for fase, itens in fases.items():
        with st.expander(fase, expanded=fase.startswith("4")):
            st.dataframe(
                pd.DataFrame(itens, columns=["decisão", "o que foi feito", "evidência"]),
                use_container_width=True, hide_index=True,
            )

    st.subheader("Limitações declaradas e hipóteses derrubadas")
    st.dataframe(
        carregar_tabela("avaliacao", "a7-limitacoes-e-hipoteses"),
        use_container_width=True, hide_index=True,
    )

    st.subheader("Espaço de atributos publicado")
    st.dataframe(
        pd.DataFrame(
            {
                "atributo": [dic.rotulo(c) for c in metadados["espaco_de_atributos"]],
                "coluna": metadados["espaco_de_atributos"],
                "descrição": [
                    dic.DESCRICOES.get(c, "—") for c in metadados["espaco_de_atributos"]
                ],
                "log1p": [
                    "sim" if c in metadados["variaveis_log1p"] else "—"
                    for c in metadados["espaco_de_atributos"]
                ],
            }
        ),
        use_container_width=True, hide_index=True,
    )
    evidencia("models/metadados_segmentacao.json", "docs/metodologia.md")
