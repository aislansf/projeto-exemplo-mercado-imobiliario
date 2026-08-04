"""CRISP-DM 6 — Implantação, monitoramento e manutenção.

Uma segmentação que só existe porque alguém rodou o notebook uma vez **não está
implantada**. Esta fase produz o que falta para que ela exista amanhã:

* os artefatos que a aplicação Streamlit consome;
* a linha de base de monitoramento (distribuições de referência por atributo);
* a evidência de *drift* medida em dado real, dividindo a carteira em período
  de referência (2006–2008) e período de acompanhamento (2009–2010);
* o plano de monitoramento com gatilho quantitativo e responsável.

O problema específico de monitorar um modelo **sem gabarito**: não existe erro
de previsão para acompanhar. O que se acompanha, então, é (a) a entrada mudar
de distribuição — *data drift* —, (b) os grupos perderem coesão — *cluster
drift* — e (c) a proporção entre segmentos se deslocar.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from joblib import load

from src import config
from src.data import dicionario as dic
from src.data import preparacao
from src.data.preparacao import construir_matriz_modelagem
from src.eda.estatistica import psi
from src.model import personas as pers
from src.model.particional import metricas_internas
from src.utils.io import configurar_estilo, ler_json, salvar_figura, salvar_json, salvar_tabela

SECAO = "implantacao"

#: Corte temporal entre referência e acompanhamento.
ANO_CORTE = 2009

#: Faixas de leitura do PSI, convenção usual em modelos de crédito.
LIMIAR_PSI_ATENCAO = 0.10
LIMIAR_PSI_ACAO = 0.25


def linha_de_base(matriz: pd.DataFrame) -> dict:
    """Distribuições de referência que a aplicação usa para medir desvio.

    Sem isso gravado, o monitoramento depende de alguém ter guardado a base de
    treino — o que, na prática, significa não haver monitoramento.
    """
    colunas = dic.NUMERICAS + dic.ORDINAIS
    referencia = {
        coluna: {
            "media": float(matriz[coluna].mean()),
            "mediana": float(matriz[coluna].median()),
            "desvio": float(matriz[coluna].std()),
            "minimo": float(matriz[coluna].min()),
            "maximo": float(matriz[coluna].max()),
            "decis": [float(v) for v in matriz[coluna].quantile(np.linspace(0, 1, 11))],
        }
        for coluna in colunas
    }
    for coluna in dic.NOMINAIS:
        referencia[coluna] = {
            "proporcoes": matriz[coluna].value_counts(normalize=True).round(5).to_dict()
        }
    salvar_json(referencia, config.MODELS / "linha_de_base.json")
    return referencia


def medir_drift(segmentada: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mede *data drift* e *cluster drift* entre os dois períodos.

    O corte é o próprio calendário da base: 2006–2008 é a referência com que o
    modelo foi construído, 2009–2010 é o período de acompanhamento. É um teste
    honesto, feito com dado real, e não uma perturbação simulada.
    """
    referencia = segmentada[segmentada["ano_venda"] < ANO_CORTE]
    atual = segmentada[segmentada["ano_venda"] >= ANO_CORTE]

    linhas = []
    for coluna in dic.NUMERICAS + dic.ORDINAIS:
        valor = psi(referencia[coluna], atual[coluna])
        linhas.append(
            {
                "atributo": dic.rotulo(coluna),
                "psi": round(valor, 4),
                "mediana_referencia": round(float(referencia[coluna].median()), 2),
                "mediana_atual": round(float(atual[coluna].median()), 2),
                "variacao_pct": round(
                    100
                    * (atual[coluna].median() - referencia[coluna].median())
                    / max(abs(referencia[coluna].median()), 1e-9),
                    1,
                ),
                "situacao": (
                    "ação" if valor >= LIMIAR_PSI_ACAO
                    else "atenção" if valor >= LIMIAR_PSI_ATENCAO
                    else "estável"
                ),
            }
        )
    drift_atributos = pd.DataFrame(linhas).sort_values("psi", ascending=False).set_index("atributo")
    salvar_tabela(drift_atributos, SECAO, "i1-drift-por-atributo")

    composicao = pd.DataFrame(
        {
            "referência 2006–2008": referencia["codigo_segmento"].value_counts(normalize=True),
            "acompanhamento 2009–2010": atual["codigo_segmento"].value_counts(normalize=True),
        }
    ).sort_index()
    composicao["variação (p.p.)"] = (
        100 * (composicao["acompanhamento 2009–2010"] - composicao["referência 2006–2008"])
    ).round(2)
    composicao[["referência 2006–2008", "acompanhamento 2009–2010"]] = (
        100 * composicao[["referência 2006–2008", "acompanhamento 2009–2010"]]
    ).round(2)
    salvar_tabela(composicao, SECAO, "i1-drift-de-composicao")

    fig, eixos = plt.subplots(1, 3, figsize=(17, 5), constrained_layout=True)

    cores = [
        config.CORAL if s == "ação" else config.AMARELO if s == "atenção" else config.VERDE
        for s in drift_atributos["situacao"]
    ]
    eixos[0].barh(drift_atributos.index[::-1], drift_atributos["psi"][::-1], color=cores[::-1])
    eixos[0].axvline(LIMIAR_PSI_ATENCAO, ls="--", color=config.AMARELO)
    eixos[0].axvline(LIMIAR_PSI_ACAO, ls="--", color=config.CORAL)
    eixos[0].set_xlabel("PSI (referência 2006–2008 × acompanhamento 2009–2010)")
    eixos[0].set_title("Data drift por atributo", fontsize=10)
    eixos[0].tick_params(axis="y", labelsize=8)

    posicoes = np.arange(len(composicao))
    eixos[1].bar(posicoes - 0.2, composicao["referência 2006–2008"], width=0.4,
                 color=config.AZUL_PROFUNDO, label="2006–2008")
    eixos[1].bar(posicoes + 0.2, composicao["acompanhamento 2009–2010"], width=0.4,
                 color=config.AZUL_CLARO, label="2009–2010")
    eixos[1].set_xticks(posicoes)
    eixos[1].set_xticklabels(composicao.index)
    eixos[1].set_ylabel("% da carteira")
    eixos[1].set_title("Cluster drift — composição da carteira por segmento", fontsize=10)
    eixos[1].legend(fontsize=8)
    for posicao, valor in zip(posicoes, composicao["variação (p.p.)"], strict=True):
        eixos[1].annotate(f"{valor:+.1f} p.p.", xy=(posicao, 2), ha="center", fontsize=8,
                          color="white", fontweight="bold")

    volume = segmentada.groupby(["ano_venda", "codigo_segmento"]).size().unstack(fill_value=0)
    volume_relativo = 100 * volume.div(volume.sum(axis=1), axis=0)
    for coluna, cor in zip(sorted(volume_relativo.columns), pers.cores(), strict=True):
        eixos[2].plot(volume_relativo.index, volume_relativo[coluna], marker="o", color=cor,
                      label=coluna, lw=2)
    eixos[2].axvline(ANO_CORTE - 0.5, ls="--", color=config.CINZA)
    eixos[2].annotate("corte de monitoramento", xy=(ANO_CORTE - 0.5, eixos[2].get_ylim()[1]),
                      xytext=(4, -14), textcoords="offset points", fontsize=8, color=config.CINZA)
    eixos[2].set_xticks(sorted(volume_relativo.index))
    eixos[2].set_ylabel("% das vendas do ano")
    eixos[2].set_title("Participação de cada segmento, ano a ano", fontsize=10)
    eixos[2].legend(fontsize=8, ncol=2)

    fig.suptitle(
        "Monitoramento sem gabarito: o que se acompanha é a entrada e a composição, "
        "não o erro de previsão",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "i1-drift-temporal", drift_atributos)
    salvar_tabela(volume_relativo.round(2), SECAO, "i1-participacao-por-ano")
    return drift_atributos, composicao


def coesao_no_periodo(segmentada: pd.DataFrame) -> pd.DataFrame:
    """Silhueta dos segmentos calculada dentro de cada período.

    É o indicador de *cluster drift*: se a coesão cair no período novo, os
    grupos deixaram de descrever a carteira, mesmo sem nenhum atributo ter
    mudado de distribuição.
    """
    matriz = construir_matriz_modelagem(segmentada, salvar=False)
    dados, _ = preparacao.preparar_espaco(matriz, "padrao")
    rotulos = segmentada["segmento"].to_numpy()

    linhas = []
    for nome, marcador in (
        ("Carteira inteira (2006–2010)", np.ones(len(segmentada), dtype=bool)),
        ("Referência (2006–2008)", (segmentada["ano_venda"] < ANO_CORTE).to_numpy()),
        ("Acompanhamento (2009–2010)", (segmentada["ano_venda"] >= ANO_CORTE).to_numpy()),
    ):
        metricas = metricas_internas(dados[marcador], rotulos[marcador])
        linhas.append(
            {
                "período": nome,
                "imóveis": int(marcador.sum()),
                "silhueta": round(metricas["silhueta"], 4),
                "davies_bouldin": round(metricas["davies_bouldin"], 3),
            }
        )
    tabela = pd.DataFrame(linhas).set_index("período")
    salvar_tabela(tabela, SECAO, "i2-coesao-por-periodo")
    return tabela


def plano_de_monitoramento() -> pd.DataFrame:
    """O plano com gatilho quantitativo, periodicidade e responsável."""
    plano = [
        {
            "o_que_monitorar": "Data drift dos atributos de entrada",
            "como": "PSI de cada um dos 17 atributos numéricos e ordinais contra a "
                    "linha de base gravada em `models/linha_de_base.json`",
            "periodicidade": "mensal",
            "gatilho": f"qualquer atributo com PSI ≥ {LIMIAR_PSI_ACAO}, ou três atributos "
                       f"simultaneamente acima de {LIMIAR_PSI_ATENCAO}",
            "acao_se_desviar": "reciclar o agrupamento e comparar por ARI com a partição vigente",
            "responsavel": "Área de Dados",
        },
        {
            "o_que_monitorar": "Cluster drift — coesão dos segmentos",
            "como": "silhueta calculada sobre as vendas dos últimos 12 meses, com os "
                    "centroides congelados",
            "periodicidade": "trimestral",
            "gatilho": f"silhueta abaixo de {config.SILHUETA_MINIMA} por dois trimestres "
                       "consecutivos",
            "acao_se_desviar": "reciclagem obrigatória, com nova varredura de k",
            "responsavel": "Área de Dados",
        },
        {
            "o_que_monitorar": "Composição da carteira por segmento",
            "como": "participação percentual de cada segmento nas entradas do período",
            "periodicidade": "mensal",
            "gatilho": "variação acima de 10 pontos percentuais em qualquer segmento "
                       "contra a linha de base",
            "acao_se_desviar": "revisar o orçamento de cada ação diferenciada — o mix "
                               "mudou e a alocação deixou de fazer sentido",
            "responsavel": "Diretoria Comercial",
        },
        {
            "o_que_monitorar": "Imóveis de fronteira",
            "como": "percentual de entradas classificadas como `fronteira` pelo grau de "
                    "pertencimento do GMM",
            "periodicidade": "mensal",
            "gatilho": "acima de 15% das entradas do mês",
            "acao_se_desviar": "suspender a ação automática para esses imóveis e escalar "
                               "para avaliação humana",
            "responsavel": "Gerência de Ativos",
        },
        {
            "o_que_monitorar": "Volume e integridade da carga",
            "como": "contagem de registros e percentual de nulos por coluna contra o "
                    "manifesto da carga",
            "periodicidade": "a cada carga",
            "gatilho": "queda de volume acima de 30% ou surgimento de nulo em coluna "
                       "que não tinha",
            "acao_se_desviar": "bloquear a publicação e acionar a origem — sem dado "
                               "novo válido, a classificação anterior permanece vigente",
            "responsavel": "Engenharia de Dados",
        },
        {
            "o_que_monitorar": "Efeito das ações diferenciadas",
            "como": "as métricas de acompanhamento declaradas em cada persona "
                    "(giro, desconto médio, retorno da reforma)",
            "periodicidade": "trimestral",
            "gatilho": "meta não atingida em dois trimestres consecutivos",
            "acao_se_desviar": "revisar a ação, não o modelo: o agrupamento pode estar "
                               "certo e a ação, errada",
            "responsavel": "Diretoria Comercial",
        },
    ]
    tabela = pd.DataFrame(plano)
    salvar_tabela(tabela, SECAO, "i3-plano-de-monitoramento", indice=False)
    return tabela


def plano_de_reciclagem() -> pd.DataFrame:
    """Quando e como o agrupamento é refeito."""
    reciclagem = [
        {"gatilho": "Calendário", "condicao": "a cada 12 meses",
         "procedimento": "reexecutar `uv run invoke pipeline` sobre a base acumulada e "
                         "comparar a nova partição com a vigente por ARI"},
        {"gatilho": "Data drift", "condicao": f"PSI ≥ {LIMIAR_PSI_ACAO} em qualquer atributo",
         "procedimento": "reciclagem imediata, com registro do atributo que disparou"},
        {"gatilho": "Cluster drift", "condicao": f"silhueta < {config.SILHUETA_MINIMA} por dois "
                                                 "trimestres",
         "procedimento": "reciclagem com nova varredura de k, incluindo teste de estabilidade"},
        {"gatilho": "Mudança de escopo", "condicao": "entrada de um novo tipo de ativo na "
                                                     "carteira (comercial, terreno)",
         "procedimento": "revisão do espaço de atributos antes de qualquer reciclagem — "
                         "o dicionário de dados muda primeiro"},
    ]
    tabela = pd.DataFrame(reciclagem)
    salvar_tabela(tabela, SECAO, "i4-plano-de-reciclagem", indice=False)

    criterio_aceite = pd.DataFrame(
        [
            {"resultado_da_reciclagem": "ARI ≥ 0,80 com a partição vigente",
             "interpretacao": "mesma estrutura",
             "decisao": "atualizar centroides, manter personas"},
            {"resultado_da_reciclagem": "ARI entre 0,50 e 0,80",
             "interpretacao": "estrutura deslocada",
             "decisao": "revisar as personas afetadas com a Diretoria Comercial"},
            {"resultado_da_reciclagem": "ARI < 0,50",
             "interpretacao": "estrutura diferente",
             "decisao": "novo ciclo de CRISP-DM a partir do entendimento de negócio"},
        ]
    )
    salvar_tabela(criterio_aceite, SECAO, "i4-criterio-de-aceite-da-reciclagem", indice=False)
    return tabela


def entregas() -> pd.DataFrame:
    """Quem consome o quê, por qual meio e com que frequência."""
    tabela = pd.DataFrame(
        [
            {"entrega": "Classificação de cada imóvel da carteira",
             "consumidor": "Corretores e Gerência de Ativos",
             "meio": "aplicação Streamlit (`src/deployment/app.py`)",
             "frequencia": "sob demanda, atualizada a cada carga"},
            {"entrega": "Classificação de um imóvel novo, antes da aquisição",
             "consumidor": "Comitê de Aquisição",
             "meio": "formulário da aplicação, com grau de confiança",
             "frequencia": "sob demanda"},
            {"entrega": "Lista de imóveis fora de padrão",
             "consumidor": "Gerência de Ativos",
             "meio": "`reports/tables/modelagem/m7-imoveis-fora-de-padrao.csv` e a aplicação",
             "frequencia": "mensal"},
            {"entrega": "Painel de monitoramento de drift",
             "consumidor": "Área de Dados",
             "meio": "aba de monitoramento da aplicação",
             "frequencia": "mensal"},
            {"entrega": "Relatório executivo com personas e ações",
             "consumidor": "Diretoria",
             "meio": "site MkDocs (`uv run invoke docs`)",
             "frequencia": "a cada reciclagem"},
        ]
    )
    salvar_tabela(tabela, SECAO, "i0-entregas", indice=False)
    return tabela


def executar() -> dict:
    """Gera os artefatos de implantação e a evidência de monitoramento."""
    configurar_estilo()
    config.garantir_diretorios()

    segmentada = pd.read_parquet(config.SEGMENTOS)
    matriz = construir_matriz_modelagem(segmentada, salvar=False)

    entregas()
    linha_de_base(matriz)
    drift, composicao = medir_drift(segmentada)
    coesao = coesao_no_periodo(segmentada)
    plano_de_monitoramento()
    plano_de_reciclagem()

    # Conferência de que o artefato serializado reproduz a classificação.
    pipeline = load(config.MODELS / "pipeline_segmentacao.joblib")
    metadados = ler_json(config.MODELS / "metadados_segmentacao.json")
    traducao = {int(k): int(v) for k, v in metadados["traducao_rotulo_bruto_para_canonico"].items()}
    reproduzido = np.array([traducao[int(r)] for r in pipeline.predict(matriz)])
    concordancia = float((reproduzido == segmentada["segmento"].to_numpy()).mean())

    verificacao = pd.DataFrame(
        [
            {"verificacao": "O pipeline serializado reproduz a classificação da base de treino",
             "resultado": f"{100 * concordancia:.2f}% de concordância",
             "situacao": "aprovado" if concordancia > 0.999 else "reprovado"},
            {"verificacao": "Linha de base gravada para o monitoramento",
             "resultado": "models/linha_de_base.json",
             "situacao": "aprovado"},
            {"verificacao": "Atributos com data drift em nível de ação",
             "resultado": f"{int((drift['situacao'] == 'ação').sum())} de {len(drift)}",
             "situacao": "aprovado" if (drift["situacao"] == "ação").sum() == 0 else "atenção"},
            {"verificacao": "Queda de coesão no período de acompanhamento",
             "resultado": f"silhueta {coesao.loc['Referência (2006–2008)', 'silhueta']:.4f} → "
                          f"{coesao.loc['Acompanhamento (2009–2010)', 'silhueta']:.4f}",
             "situacao": "aprovado"
             if coesao.loc["Acompanhamento (2009–2010)", "silhueta"] >= config.SILHUETA_MINIMA
             else "atenção"},
        ]
    )
    salvar_tabela(verificacao, SECAO, "i5-verificacao-de-implantacao", indice=False)

    fig, eixo = plt.subplots(figsize=(8, 3.6), constrained_layout=True)
    sns.heatmap(
        coesao[["silhueta", "davies_bouldin"]].T, annot=True, fmt=".3f", cmap="RdYlGn",
        center=0.18, ax=eixo, linewidths=0.6, linecolor="white", cbar=False,
    )
    eixo.set_title("Coesão dos segmentos por período — o indicador de cluster drift")
    eixo.set_xlabel("")
    eixo.tick_params(axis="x", labelsize=8)
    salvar_figura(fig, SECAO, "i2-coesao-por-periodo", coesao)

    return {
        "concordancia_pipeline": concordancia,
        "atributos_em_acao": int((drift["situacao"] == "ação").sum()),
        "atributos_em_atencao": int((drift["situacao"] == "atenção").sum()),
        "maior_variacao_composicao": float(composicao["variação (p.p.)"].abs().max()),
    }


if __name__ == "__main__":
    resumo = executar()
    print(f"Pipeline serializado reproduz {100 * resumo['concordancia_pipeline']:.2f}% da base")
    print(
        f"Drift: {resumo['atributos_em_acao']} atributos em ação, "
        f"{resumo['atributos_em_atencao']} em atenção"
    )
    print(f"Figuras em {config.FIGURES / SECAO}")
