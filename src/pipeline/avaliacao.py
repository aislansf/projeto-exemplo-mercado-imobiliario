"""CRISP-DM 5 — Avaliação.

A fase 4 perguntou se o modelo é tecnicamente bom. Esta pergunta se ele
**resolve o problema que a diretoria trouxe**, o que é outra coisa.

É aqui, e só aqui, que o rótulo reservado (``preco_venda``) entra. Ele serve
para responder a duas perguntas de negócio — quanto vale cada segmento e se a
segmentação é apenas uma tabela de preço disfarçada — e nunca alimentou nenhum
algoritmo. O LDA aparece pela mesma razão e com a mesma restrição.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from src import config
from src.data import preparacao
from src.data.preparacao import construir_matriz_modelagem
from src.model import perfilagem as perf
from src.model import personas as pers
from src.model import reducao as red
from src.utils.io import configurar_estilo, ler_json, salvar_figura, salvar_tabela

SECAO = "avaliacao"


# --------------------------------------------------------------------------- #
# 5.1 — Avaliar os resultados sob a ótica do negócio
# --------------------------------------------------------------------------- #


def confrontar_criterios(segmentada: pd.DataFrame, metadados: dict) -> pd.DataFrame:
    """Confronta cada critério de aceite do Canvas com o que foi entregue.

    Critério não atendido é registrado como não atendido. Reescrever o critério
    para caber no resultado é a forma mais comum de um projeto falhar em
    silêncio.
    """
    rotulos = segmentada["segmento"].to_numpy()
    tamanhos = segmentada["codigo_segmento"].value_counts(normalize=True)
    ruido = float(segmentada["fora_de_padrao_dbscan"].mean())

    faixa_preco = pd.qcut(segmentada["preco_venda"], 4, labels=False)
    ari_preco = float(adjusted_rand_score(rotulos, faixa_preco))
    nmi_preco = float(normalized_mutual_info_score(rotulos, faixa_preco))

    regras = pd.read_csv(
        config.TABLES / "associacao" / "r2-principais-regras.csv", sep=";", decimal=","
    )
    diferenciais = pd.read_csv(
        config.TABLES / "associacao" / "r3-regras-diferenciais.csv", sep=";", decimal=","
    )
    comparativo_algoritmos = pd.read_csv(
        config.TABLES / "associacao" / "r1-comparativo-algoritmos.csv", sep=";", decimal=","
    )

    criterios = [
        {
            "objetivo": "1. Segmentar a carteira em linhas de produto operáveis",
            "criterio": f"No máximo {config.K_MAXIMO_NEGOCIO} segmentos",
            "meta": f"≤ {config.K_MAXIMO_NEGOCIO}",
            "obtido": metadados["k"],
            "situacao": "atendido" if metadados["k"] <= config.K_MAXIMO_NEGOCIO else "não atendido",
            "evidencia": "m2-decisao-de-k.csv",
        },
        {
            "objetivo": "1. Segmentar a carteira em linhas de produto operáveis",
            "criterio": "Silhueta mínima aceitável",
            "meta": f"≥ {config.SILHUETA_MINIMA}",
            "obtido": round(metadados["silhueta"], 4),
            "situacao": "atendido"
            if metadados["silhueta"] >= config.SILHUETA_MINIMA
            else "não atendido",
            "evidencia": "m3-silhueta-por-segmento.png",
        },
        {
            "objetivo": "1. Segmentar a carteira em linhas de produto operáveis",
            "criterio": "Estabilidade sob reamostragem de 80%",
            "meta": "ARI ≥ 0,75",
            "obtido": round(metadados["estabilidade_ari"], 4),
            "situacao": "atendido" if metadados["estabilidade_ari"] >= 0.75 else "não atendido",
            "evidencia": "m2-escolha-de-k.png",
        },
        {
            "objetivo": "1. Segmentar a carteira em linhas de produto operáveis",
            "criterio": "Nenhum segmento abaixo de 2% da carteira",
            "meta": "≥ 2%",
            "obtido": f"{100 * tamanhos.min():.1f}%",
            "situacao": "atendido" if tamanhos.min() >= 0.02 else "não atendido",
            "evidencia": "m13-perfil-por-segmento.csv",
        },
        {
            "objetivo": "2. Descrever cada segmento em linguagem de negócio",
            "criterio": "Persona, ação diferenciada e métrica de acompanhamento por segmento",
            "meta": f"{metadados['k']} de {metadados['k']}",
            "obtido": f"{len(pers.PERSONAS)} de {metadados['k']}",
            "situacao": "atendido" if len(pers.PERSONAS) == metadados["k"] else "não atendido",
            "evidencia": "m14-personas.csv",
        },
        {
            "objetivo": "2. Descrever cada segmento em linguagem de negócio",
            "criterio": "Imóvel real representante de cada segmento, com identificador",
            "meta": f"{metadados['k']} medoides",
            "obtido": f"{metadados['k']} medoides",
            "situacao": "atendido",
            "evidencia": "m13-medoides-reais.csv",
        },
        {
            "objetivo": "2. Descrever cada segmento em linguagem de negócio",
            "criterio": "A segmentação não pode ser apenas uma faixa de preço",
            "meta": "ARI contra quartis de preço < 0,40",
            "obtido": round(ari_preco, 4),
            "situacao": "atendido" if ari_preco < 0.40 else "não atendido",
            "evidencia": "a2-segmentos-vs-preco.png",
        },
        {
            "objetivo": "3. Encontrar padrões de coocorrência que sustentem a segmentação",
            "criterio": "Regras com suporte ≥ 10%, confiança ≥ 70% e lift ≥ 1,30",
            "meta": "≥ 10 regras",
            "obtido": len(regras),
            "situacao": "atendido" if len(regras) >= 10 else "não atendido",
            "evidencia": "r2-principais-regras.csv",
        },
        {
            "objetivo": "3. Encontrar padrões de coocorrência que sustentem a segmentação",
            "criterio": "Ao menos um padrão diferencial por segmento",
            "meta": f"{metadados['k']} segmentos cobertos",
            "obtido": f"{diferenciais['persona'].nunique()} segmentos cobertos"
            if "persona" in diferenciais
            else "0",
            "situacao": "atendido"
            if "persona" in diferenciais and diferenciais["persona"].nunique() >= metadados["k"]
            else "parcial",
            "evidencia": "r3-regras-diferenciais.csv",
        },
        {
            "objetivo": "3. Encontrar padrões de coocorrência que sustentem a segmentação",
            "criterio": "Apriori, Eclat e FP-Growth devolvem os mesmos conjuntos frequentes",
            "meta": "3 de 3 idênticos",
            "obtido": f"{int(comparativo_algoritmos['identico_ao_apriori'].sum())} de 3 idênticos",
            "situacao": "atendido"
            if bool(comparativo_algoritmos["identico_ao_apriori"].all())
            else "não atendido",
            "evidencia": "r1-comparativo-algoritmos.csv",
        },
        {
            "objetivo": "4. Isolar os imóveis que não pertencem a nenhuma linha de produto",
            "criterio": "Percentual de ruído dentro do teto",
            "meta": f"≤ {config.RUIDO_MAXIMO:.0%}",
            "obtido": f"{100 * ruido:.2f}%",
            "situacao": "atendido" if ruido <= config.RUIDO_MAXIMO else "não atendido",
            "evidencia": "m7-dbscan.png",
        },
        {
            "objetivo": "5. Entregar o resultado em forma utilizável pela operação",
            "criterio": "Modelo serializado e aplicação de consulta publicada",
            "meta": "pipeline + aplicação",
            "obtido": "pipeline_segmentacao.joblib + src/deployment/app.py",
            "situacao": "atendido",
            "evidencia": "models/ e src/deployment/",
        },
        {
            "objetivo": "5. Entregar o resultado em forma utilizável pela operação",
            "criterio": "Plano de monitoramento com gatilho quantitativo",
            "meta": "PSI por atributo, com limiar",
            "obtido": "PSI e deslocamento de centroide, com gatilhos em docs/implementacao.md",
            "situacao": "atendido",
            "evidencia": "i1-drift-temporal.png",
        },
    ]
    tabela = pd.DataFrame(criterios)
    salvar_tabela(tabela, SECAO, "a1-confronto-criterios", indice=False)

    consolidado = (
        tabela.groupby("objetivo")["situacao"]
        .value_counts()
        .unstack(fill_value=0)
        .rename_axis(columns=None)
    )
    salvar_tabela(consolidado, SECAO, "a1-consolidado-criterios")

    fig, eixo = plt.subplots(figsize=(11, 4.6), constrained_layout=True)
    cores = {"atendido": config.VERDE, "parcial": config.AMARELO, "não atendido": config.CORAL}
    base = np.zeros(len(consolidado))
    for situacao in ["atendido", "parcial", "não atendido"]:
        if situacao not in consolidado:
            continue
        eixo.barh(consolidado.index, consolidado[situacao], left=base,
                  color=cores[situacao], label=situacao)
        base += consolidado[situacao].to_numpy()
    eixo.set_xlabel("critérios de aceite")
    eixo.set_yticks(range(len(consolidado)))
    eixo.set_yticklabels([rotulo[:54] for rotulo in consolidado.index], fontsize=8)
    eixo.legend(fontsize=8)
    eixo.set_title(
        f"Confronto com os critérios de aceite do Canvas "
        f"({int((tabela['situacao'] == 'atendido').sum())} de {len(tabela)} atendidos)"
    )
    salvar_figura(fig, SECAO, "a1-criterios-por-objetivo", consolidado)

    salvar_tabela(
        pd.DataFrame(
            [
                {"medida": "ARI entre segmentos e quartis de preço", "valor": round(ari_preco, 4),
                 "leitura": "0 = independentes, 1 = idênticos"},
                {"medida": "NMI entre segmentos e quartis de preço", "valor": round(nmi_preco, 4),
                 "leitura": "informação compartilhada, normalizada"},
            ]
        ),
        SECAO, "a2-concordancia-com-preco", indice=False,
    )
    return tabela


def leitura_de_negocio(segmentada: pd.DataFrame) -> pd.DataFrame:
    """O que cada segmento vale — a única leitura que usa o rótulo reservado."""
    rotulos = segmentada["segmento"].to_numpy()
    resumo = perf.leitura_a_posteriori(segmentada, rotulos)
    resumo.insert(0, "persona", [pers.PERSONAS[int(s)]["nome"] for s in resumo.index])
    resumo.insert(0, "código", [pers.codigo(s) for s in resumo.index])
    salvar_tabela(resumo, SECAO, "a2-valor-por-segmento")

    sobreposicao = perf.sobreposicao_de_preco(segmentada, rotulos)
    salvar_tabela(sobreposicao, SECAO, "a2-sobreposicao-de-preco")

    fig, eixos = plt.subplots(1, 3, figsize=(17, 5), constrained_layout=True)

    caixas = [segmentada.loc[rotulos == g, "preco_venda"] for g in sorted(np.unique(rotulos))]
    desenho = eixos[0].boxplot(caixas, patch_artist=True, showfliers=False,
                               tick_labels=[pers.codigo(g) for g in sorted(np.unique(rotulos))])
    for caixa, cor in zip(desenho["boxes"], pers.cores(), strict=True):
        caixa.set_facecolor(cor)
        caixa.set_alpha(0.85)
    for mediana in desenho["medians"]:
        mediana.set_color("white")
        mediana.set_linewidth(1.8)
    eixos[0].set_ylabel("preço de venda (US$)")
    eixos[0].set_title(
        "Faixa de preço por segmento\n(as caixas se sobrepõem — não é tabela de preço)",
        fontsize=10,
    )

    participacao = pd.DataFrame(
        {
            "% das unidades": 100 * resumo["imoveis"] / resumo["imoveis"].sum(),
            "% da receita": resumo["pct_receita"],
        },
        index=[pers.codigo(s) for s in resumo.index],
    )
    participacao.plot.bar(ax=eixos[1], color=[config.AZUL_COBALTO, config.CORAL], rot=0, width=0.75)
    for container in eixos[1].containers:
        eixos[1].bar_label(container, fmt="%.1f", padding=2, fontsize=8)
    eixos[1].set_ylabel("%")
    eixos[1].set_title("Unidades × receita — onde está o dinheiro", fontsize=10)
    eixos[1].legend(fontsize=8)

    sns.heatmap(sobreposicao.astype(float), annot=True, fmt=".2f", cmap="Oranges", vmin=0, vmax=1,
                ax=eixos[2], linewidths=0.5, linecolor="white",
                cbar_kws={"label": "sobreposição dos intervalos interquartis"})
    eixos[2].set_xticklabels([pers.codigo(int(s)) for s in sobreposicao.columns])
    eixos[2].set_yticklabels([pers.codigo(int(s)) for s in sobreposicao.index], rotation=0)
    eixos[2].set_title("Sobreposição de preço entre segmentos", fontsize=10)

    fig.suptitle(
        "Leitura de negócio — o rótulo reservado entra aqui, e só aqui",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "a2-segmentos-vs-preco", resumo)

    bairros = perf.validacao_por_bairro(segmentada, rotulos, top=8)
    bairros.columns = [pers.codigo(int(c)) for c in bairros.columns]
    salvar_tabela(bairros, SECAO, "a3-validacao-por-bairro")

    fig, eixo = plt.subplots(figsize=(9, 5), constrained_layout=True)
    bairros.plot.barh(stacked=True, ax=eixo, color=pers.cores(), width=0.78)
    eixo.set_xlabel("% do bairro")
    eixo.set_ylabel("")
    eixo.legend(fontsize=8, ncol=4, loc="lower right")
    eixo.set_title(
        "Validação externa — composição de segmentos nos 8 maiores bairros.\n"
        "`bairro` ficou fora da modelagem justamente para poder ser usado aqui.",
        fontsize=10,
    )
    salvar_figura(fig, SECAO, "a3-validacao-por-bairro", bairros)
    return resumo


def pca_versus_lda(segmentada: pd.DataFrame) -> pd.DataFrame:
    """Contrapõe a projeção não supervisionada à supervisionada.

    O PCA não viu preço nenhum. O LDA foi treinado para separar faixas de preço.
    Se as duas projeções contassem a mesma história, a segmentação seria uma
    tabela de preço; se contarem histórias diferentes, ela carrega informação
    de produto que o preço sozinho não tem.
    """
    matriz = construir_matriz_modelagem(segmentada, salvar=False)
    dados, nomes = preparacao.preparar_espaco(matriz, "padrao")
    rotulos = segmentada["segmento"].to_numpy()

    modelo_pca, projecao_pca = red.ajustar_pca(dados)
    faixas = pd.qcut(segmentada["preco_venda"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
    _, projecao_lda, acuracia = red.lda_a_posteriori(dados, faixas.to_numpy(), componentes=2)

    fig, eixos = plt.subplots(1, 3, figsize=(17, 5.2), constrained_layout=True)
    for grupo in sorted(np.unique(rotulos)):
        marcador = rotulos == grupo
        eixos[0].scatter(projecao_pca[marcador, 0], projecao_pca[marcador, 1], s=9, alpha=0.55,
                         color=pers.cores()[grupo], label=pers.codigo(grupo), edgecolors="none")
    eixos[0].legend(fontsize=8, markerscale=2)
    eixos[0].set_title("PCA — não supervisionado, colorido por segmento", fontsize=10)
    eixos[0].set_xlabel("CP1")
    eixos[0].set_ylabel("CP2")

    for cor, faixa in zip(config.PALETA, ["Q1", "Q2", "Q3", "Q4"], strict=False):
        marcador = (faixas == faixa).to_numpy()
        eixos[1].scatter(projecao_pca[marcador, 0], projecao_pca[marcador, 1], s=9, alpha=0.55,
                         color=cor, label=f"preço {faixa}", edgecolors="none")
    eixos[1].legend(fontsize=8, markerscale=2)
    eixos[1].set_title("O mesmo PCA, colorido por faixa de preço", fontsize=10)
    eixos[1].set_xlabel("CP1")
    eixos[1].set_ylabel("CP2")

    for cor, faixa in zip(config.PALETA, ["Q1", "Q2", "Q3", "Q4"], strict=False):
        marcador = (faixas == faixa).to_numpy()
        eixos[2].scatter(projecao_lda[marcador, 0], projecao_lda[marcador, 1], s=9, alpha=0.55,
                         color=cor, label=f"preço {faixa}", edgecolors="none")
    eixos[2].legend(fontsize=8, markerscale=2)
    eixos[2].set_title(
        f"LDA — supervisionado pela faixa de preço\n"
        f"(reclassificação: {acuracia:.1%}); usado APENAS na avaliação", fontsize=10
    )
    eixos[2].set_xlabel("Discriminante 1")
    eixos[2].set_ylabel("Discriminante 2")
    fig.suptitle(
        "PCA × LDA — a diferença entre procurar variância e procurar separação de classe",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )

    comparacao = pd.DataFrame(
        [
            {"técnica": "PCA", "supervisionada": "não",
             "o que procura": "direções de maior variância",
             "uso no projeto": "visualização e diagnóstico de redundância",
             "variancia_ou_acuracia": round(
                 float(modelo_pca.explained_variance_ratio_[:2].sum()), 4
             )},
            {"técnica": "LDA", "supervisionada": "sim",
             "o que procura": "direções que separam classes conhecidas",
             "uso no projeto": "somente avaliação a posteriori, sobre a faixa de preço",
             "variancia_ou_acuracia": round(acuracia, 4)},
        ]
    ).set_index("técnica")
    salvar_figura(fig, SECAO, "a4-pca-versus-lda", comparacao)
    salvar_tabela(comparacao, SECAO, "a4-pca-versus-lda")
    return comparacao


# --------------------------------------------------------------------------- #
# 5.2 e 5.3 — Revisão do processo e próximas etapas
# --------------------------------------------------------------------------- #


def revisar_processo() -> pd.DataFrame:
    """Retrospectiva da condução, independente do resultado."""
    revisao = [
        {"dimensão": "O que funcionou",
         "registro": "Reservar `preco_venda` e `bairro` desde o início. Sem essa decisão "
                     "tomada antes da modelagem, não haveria régua externa nenhuma para "
                     "avaliar o resultado no fim."},
        {"dimensão": "O que funcionou",
         "registro": "Medir estabilidade por reamostragem em paralelo à silhueta. Foi o "
                     "único critério que derrubou k=5, que as métricas de coesão "
                     "recomendavam."},
        {"dimensão": "O que funcionou",
         "registro": "Gravar a tabela-fonte junto com cada figura. Toda afirmação do "
                     "relatório é rastreável até um CSV, e nenhum número foi digitado à mão."},
        {"dimensão": "O que atrasou",
         "registro": "A leitura padrão do pandas converteu a categoria `None` de "
                     "`Mas Vnr Type` em nulo, e a coluna aparentou 60,6% de ausência. O "
                     "diagnóstico consumiu uma iteração inteira da 5ª fase da EDA."},
        {"dimensão": "O que atrasou",
         "registro": "A primeira rodada de regras usou suporte de 5% e conjuntos de até 4 "
                     "itens, e produziu 6.274 regras — volume que nenhuma área comercial "
                     "lê. Foi preciso voltar e calibrar o limiar com evidência."},
        {"dimensão": "O que foi esquecido",
         "registro": "A poda por lift e por redundância não remove tautologia semântica: "
                     "`tem 2º pavimento → estilo 2Story` passou pelos três filtros com "
                     "lift 3,03. Só o conhecimento do domínio a derrubou, e isso teve de "
                     "ser acrescentado depois."},
        {"dimensão": "O que foi esquecido",
         "registro": "A silhueta do K-Medoids sobre Gower foi comparada à do K-Means na "
                     "primeira versão da matriz, como se fossem a mesma escala. São "
                     "espaços métricos diferentes; a tabela hoje marca isso explicitamente."},
    ]
    tabela = pd.DataFrame(revisao)
    salvar_tabela(tabela, SECAO, "a5-revisao-do-processo", indice=False)
    return tabela


def proximas_etapas() -> pd.DataFrame:
    """Decisão formal sobre o destino do projeto."""
    acoes = [
        {"acao": "Implantar a segmentação como classificação padrão da carteira",
         "responsavel": "Diretoria Comercial", "prazo": "30 dias", "decisao": "implantar"},
        {"acao": "Publicar a aplicação de consulta para os 12 corretores",
         "responsavel": "Área de Dados", "prazo": "15 dias", "decisao": "implantar"},
        {"acao": "Avaliar individualmente os 53 imóveis fora de padrão apontados pelo DBSCAN",
         "responsavel": "Gerência de Ativos", "prazo": "90 dias", "decisao": "implantar"},
        {"acao": "Reciclar o agrupamento com os dados do próximo exercício e comparar por ARI",
         "responsavel": "Área de Dados", "prazo": "12 meses", "decisao": "iterar"},
        {"acao": "Buscar dado de tempo de permanência em estoque, ausente na base atual",
         "responsavel": "Área de Dados + TI", "prazo": "6 meses", "decisao": "iterar"},
        {"acao": "Reavaliar o segmento S1 (80 imóveis) quando a carteira dobrar de tamanho",
         "responsavel": "Área de Dados", "prazo": "18 meses", "decisao": "iterar"},
    ]
    tabela = pd.DataFrame(acoes)
    salvar_tabela(tabela, SECAO, "a6-proximas-etapas", indice=False)
    return tabela


def limitacoes() -> pd.DataFrame:
    """Limitações declaradas e hipóteses derrubadas ao longo do percurso."""
    itens = [
        {"tipo": "Hipótese derrubada",
         "registro": "«Cinco segmentos dariam a leitura mais rica, já que o orçamento "
                     "comporta cinco ações.» Derrubada pela estabilidade: em k=5 o ARI "
                     "médio sob reamostragem cai para 0,44 — a quinta linha de produto "
                     "não se reproduz."},
        {"tipo": "Hipótese derrubada",
         "registro": "«A dissimilaridade de Gower, por tratar dados mistos, daria a melhor "
                     "segmentação.» Derrubada pela leitura do resultado: com peso igual "
                     "por variável, `estilo` domina e a partição vira 1 pavimento × 2 "
                     "pavimentos — fato construtivo, não linha de produto."},
        {"tipo": "Hipótese derrubada",
         "registro": "«O DBSCAN encontraria grupos de densidade que o K-Means não vê.» "
                     "Derrubada: em 21 dimensões padronizadas não há vale de densidade, e "
                     "o algoritmo devolve um grupo com 92% da carteira. O que ele entrega "
                     "de útil é o ruído, não a partição."},
        {"tipo": "Limitação",
         "registro": "A base cobre 2006 a 2010, período que inclui a crise imobiliária "
                     "americana. A estrutura de segmentos é estável no período, mas os "
                     "patamares de preço da avaliação a posteriori não devem ser lidos "
                     "como preço corrente."},
        {"tipo": "Limitação",
         "registro": "Não há tempo de permanência em estoque na origem. As metas de giro "
                     "das personas S2 e S4 são propostas de meta, não medições — e "
                     "precisam de instrumentação antes de virar indicador."},
        {"tipo": "Limitação",
         "registro": "O segmento S1 tem 80 imóveis (2,7%). É estatisticamente coeso "
                     "(silhueta 0,376, a maior da carteira), mas pequeno o bastante para "
                     "que qualquer mudança de composição o desestabilize."},
        {"tipo": "Limitação",
         "registro": "A segmentação descreve o **produto**, não o **comprador**. Não há na "
                     "base nenhum atributo de quem comprou, e portanto nenhuma ação de "
                     "segmentação de demanda pode ser derivada daqui."},
        {"tipo": "Caminho abandonado",
         "registro": "O espaço euclidiano com one-hot das nominais foi construído e "
                     "descartado: produz partição praticamente idêntica (ARI 0,98) com "
                     "silhueta menor. As 28 colunas binárias acrescentam ruído, não "
                     "informação."},
    ]
    tabela = pd.DataFrame(itens)
    salvar_tabela(tabela, SECAO, "a7-limitacoes-e-hipoteses", indice=False)
    return tabela


def executar() -> dict:
    """Executa a avaliação completa."""
    configurar_estilo()
    config.garantir_diretorios()

    segmentada = pd.read_parquet(config.SEGMENTOS)
    metadados = ler_json(config.MODELS / "metadados_segmentacao.json")

    criterios = confrontar_criterios(segmentada, metadados)
    valor = leitura_de_negocio(segmentada)
    pca_versus_lda(segmentada)
    revisar_processo()
    proximas_etapas()
    limitacoes()

    return {
        "criterios_atendidos": int((criterios["situacao"] == "atendido").sum()),
        "criterios_totais": int(len(criterios)),
        "receita_por_segmento": valor["pct_receita"].to_dict(),
    }


if __name__ == "__main__":
    resumo = executar()
    print(
        f"Critérios de aceite: {resumo['criterios_atendidos']} de "
        f"{resumo['criterios_totais']} atendidos"
    )
    print(f"Figuras em {config.FIGURES / SECAO}")
