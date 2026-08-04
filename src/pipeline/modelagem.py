"""CRISP-DM 4 — Modelagem: clusterização.

Executa o desenho do experimento completo e grava toda a evidência:

* três leituras do espaço de atributos (euclidiano enxuto, euclidiano com
  *one-hot* e misto por Gower);
* escolha de *k* por cotovelo, silhueta, Davies-Bouldin, Calinski-Harabasz,
  estabilidade por reamostragem e teto operacional de cinco grupos;
* seis famílias de algoritmo — K-Means, K-Medoids, hierárquica, DBSCAN,
  Mean Shift e GMM — comparadas na mesma tabela;
* redução de dimensionalidade por PCA e Kernel PCA;
* perfilagem dos segmentos e serialização do modelo final.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from joblib import dump
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples
from sklearn.pipeline import Pipeline

from src import config
from src.data import dicionario as dic
from src.data import preparacao
from src.data.preparacao import carregar_curada, construir_matriz_modelagem
from src.model import densidade as den
from src.model import distancias as dist
from src.model import estabilidade as est
from src.model import hierarquica as hier
from src.model import mistura as mis
from src.model import particional as part
from src.model import perfilagem as perf
from src.model import personas as pers
from src.model import reducao as red
from src.utils.io import configurar_estilo, salvar_figura, salvar_json, salvar_tabela

SECAO = "modelagem"

#: `minPts` do DBSCAN pela heurística usual: duas vezes a dimensionalidade.
MULTIPLICADOR_MINPTS = 2


# --------------------------------------------------------------------------- #
# 4.1 — Seleção das técnicas: qual distância, e por quê
# --------------------------------------------------------------------------- #


def comparar_espacos(matriz: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Compara as três leituras do espaço de atributos.

    A pergunta que a tabela responde é a da rubrica: *a distância escolhida é
    adequada à natureza dos atributos?*
    """
    euclidiano, nomes = preparacao.preparar_espaco(matriz, "padrao", com_nominais=False)
    com_onehot, nomes_onehot = preparacao.preparar_espaco(matriz, "padrao", com_nominais=True)
    gower = dist.gower(matriz, dic.NUMERICAS + dic.ORDINAIS, dic.NOMINAIS)

    comparativo = dist.comparar_metricas(euclidiano, ("euclidean", "cityblock", "cosine"))
    salvar_tabela(comparativo, SECAO, "m1-metricas-de-distancia")

    resumo = pd.DataFrame(
        [
            {
                "espaço": "Euclidiano enxuto",
                "variáveis": len(nomes),
                "composição": "11 numéricas + 6 ordinais + 4 binárias",
                "distância": "euclidiana sobre variáveis padronizadas",
                "observação": "as nominais ficam de fora; nenhuma delas domina a geometria",
            },
            {
                "espaço": "Euclidiano com one-hot",
                "variáveis": len(nomes_onehot),
                "composição": (
                    f"{len(nomes)} do enxuto + {len(nomes_onehot) - len(nomes)} binárias de one-hot"
                ),
                "distância": "euclidiana sobre variáveis padronizadas",
                "observação": "28 colunas binárias não padronizadas competem com 21 contínuas",
            },
            {
                "espaço": "Misto (Gower)",
                "variáveis": len(dic.ESPACO_MISTO),
                "composição": "17 numéricas/ordinais + 5 nominais em estado bruto",
                "distância": "dissimilaridade de Gower, peso igual por variável",
                "observação": "cada nominal pesa tanto quanto cada numérica — inclusive `estilo`",
            },
        ]
    ).set_index("espaço")
    salvar_tabela(resumo, SECAO, "m1-espacos-de-atributos")

    return (
        {"euclidiano": euclidiano, "onehot": com_onehot, "gower": gower, "nomes": nomes},
        resumo,
    )


# --------------------------------------------------------------------------- #
# 4.2 — Desenho do experimento: a escolha de k
# --------------------------------------------------------------------------- #


def escolher_k(dados: np.ndarray) -> tuple[int, pd.DataFrame, pd.DataFrame]:
    """Varre *k*, mede estabilidade e confronta com o teto operacional."""
    varredura = part.varrer_k(dados, 2, 10)
    varredura["cotovelo"] = ""
    k_cotovelo = part.cotovelo(varredura["inercia"])
    varredura.loc[k_cotovelo, "cotovelo"] = "◄ joelho da curva"

    estabilidades = est.estabilidade_por_k(dados, range(2, 9), repeticoes=40)
    consolidado = varredura.join(estabilidades)
    salvar_tabela(consolidado, SECAO, "m2-escolha-de-k")

    fig, eixos = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    ks = varredura.index

    painel = [
        ("inercia", "Inércia (cotovelo)", "menor é melhor", config.AZUL_PROFUNDO),
        ("silhueta", "Coeficiente de silhueta", "maior é melhor", config.CORAL),
        ("davies_bouldin", "Davies-Bouldin", "menor é melhor", config.VERDE),
        ("calinski_harabasz", "Calinski-Harabasz", "maior é melhor", config.ROXO),
    ]
    for eixo, (coluna, titulo, leitura, cor) in zip(eixos.ravel(), painel, strict=False):
        eixo.plot(ks, varredura[coluna], marker="o", color=cor, lw=2)
        eixo.axvspan(config.K_MAXIMO_NEGOCIO + 0.5, ks.max() + 0.3, color="#F4D35E", alpha=0.18)
        eixo.set_title(f"{titulo}\n({leitura})", fontsize=10)
        eixo.set_xlabel("k")
        eixo.set_xticks(ks)
    eixos[0, 0].axvline(k_cotovelo, ls="--", color=config.CINZA)
    eixos[0, 0].annotate(
        f"joelho em k={k_cotovelo}", xy=(k_cotovelo, varredura.loc[k_cotovelo, "inercia"]),
        xytext=(8, 18), textcoords="offset points", fontsize=9, color=config.CINZA,
    )
    eixos[0, 1].axhline(config.SILHUETA_MINIMA, ls=":", color=config.CINZA)
    eixos[0, 1].annotate(
        f"mínimo do Canvas ({config.SILHUETA_MINIMA})", xy=(ks.max(), config.SILHUETA_MINIMA),
        xytext=(-4, 6), textcoords="offset points", ha="right", fontsize=8, color=config.CINZA,
    )

    eixo = eixos[1, 1]
    eixo.errorbar(
        estabilidades.index, estabilidades["ari_medio"], yerr=estabilidades["ari_desvio"],
        marker="o", color=config.AZUL_COBALTO, capsize=4, lw=2,
    )
    eixo.axhline(0.75, ls=":", color=config.CINZA)
    eixo.annotate("piso de estabilidade aceitável (0,75)", xy=(estabilidades.index.max(), 0.75),
                  xytext=(-4, 6), textcoords="offset points", ha="right", fontsize=8,
                  color=config.CINZA)
    eixo.set_title(
        "Estabilidade por reamostragem\n(ARI médio em 40 reamostras de 80%)", fontsize=10
    )
    eixo.set_xlabel("k")
    eixo.set_ylim(0, 1.05)

    eixo = eixos[1, 2]
    tamanhos = varredura[["menor_grupo", "maior_grupo"]]
    eixo.plot(
        ks, tamanhos["maior_grupo"], marker="o", label="maior grupo",
        color=config.AZUL_PROFUNDO,
    )
    eixo.plot(ks, tamanhos["menor_grupo"], marker="o", label="menor grupo", color=config.CORAL)
    eixo.set_yscale("log")
    eixo.set_title("Equilíbrio dos grupos\n(escala logarítmica)", fontsize=10)
    eixo.set_xlabel("k")
    eixo.legend(fontsize=8)

    fig.suptitle(
        "Escolha de k — quatro métricas internas, estabilidade e o teto de cinco grupos "
        "(faixa amarela: inviável para o negócio)",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "m2-escolha-de-k", consolidado)

    # A decisão: dentro do teto de negócio, o maior k que se mantém estável.
    viaveis = consolidado.loc[config.K_MINIMO_NEGOCIO : config.K_MAXIMO_NEGOCIO]
    candidatos = viaveis[
        (viaveis["ari_medio"] >= 0.75) & (viaveis["silhueta"] >= config.SILHUETA_MINIMA)
    ]
    k_escolhido = (
        int(candidatos.index.max()) if len(candidatos) else int(viaveis["silhueta"].idxmax())
    )

    decisao = pd.DataFrame(
        [
            {"critério": "Cotovelo da inércia", "aponta para": k_cotovelo,
             "leitura": "sugere mais grupos do que o negócio consegue operar"},
            {"critério": "Maior silhueta (global)",
             "aponta para": int(varredura["silhueta"].idxmax()),
             "leitura": f"{varredura['silhueta'].max():.4f} — mas com apenas 2 linhas de produto"},
            {"critério": "Maior silhueta dentro do teto de 5",
             "aponta para": int(viaveis["silhueta"].idxmax()),
             "leitura": f"{viaveis['silhueta'].max():.4f}"},
            {"critério": "Menor Davies-Bouldin dentro do teto",
             "aponta para": int(viaveis["davies_bouldin"].idxmin()),
             "leitura": f"{viaveis['davies_bouldin'].min():.4f}"},
            {"critério": "Estabilidade por reamostragem (ARI ≥ 0,75)",
             "aponta para": ", ".join(str(k) for k in viaveis[viaveis["ari_medio"] >= 0.75].index),
             "leitura": "os demais não se reproduzem em reamostragem"},
            {"critério": "Restrição operacional do Canvas", "aponta para": "2 a 5",
             "leitura": "orçamento para no máximo cinco ações diferenciadas"},
            {"critério": "DECISÃO", "aponta para": k_escolhido,
             "leitura": "maior k que é simultaneamente estável, acima da silhueta mínima e viável"},
        ]
    ).set_index("critério")
    salvar_tabela(decisao, SECAO, "m2-decisao-de-k")

    return k_escolhido, consolidado, decisao


def grafico_silhueta(dados: np.ndarray, rotulos: np.ndarray, k: int) -> pd.DataFrame:
    """Gráfico de silhueta por cluster — o que a média global esconde."""
    amostras = silhouette_samples(dados, rotulos)
    media = float(amostras.mean())

    fig, eixo = plt.subplots(figsize=(9, 6), constrained_layout=True)
    base = 10
    marcas, rotulos_eixo = [], []
    for grupo in range(k):
        valores = np.sort(amostras[rotulos == grupo])
        topo = base + len(valores)
        eixo.fill_betweenx(np.arange(base, topo), 0, valores, color=pers.cores()[grupo], alpha=0.85)
        marcas.append(base + len(valores) / 2)
        rotulos_eixo.append(f"{pers.PERSONAS[grupo]['codigo']}  (n={len(valores)})")
        base = topo + 20
    eixo.axvline(media, color=config.CORAL, ls="--", lw=1.6)
    eixo.annotate(f"silhueta média = {media:.3f}", xy=(media, base), xytext=(6, -12),
                  textcoords="offset points", color=config.CORAL, fontsize=9, fontweight="bold")
    eixo.axvline(0, color=config.CINZA, lw=1)
    eixo.set_yticks(marcas)
    eixo.set_yticklabels(rotulos_eixo, fontsize=9)
    eixo.set_xlabel("coeficiente de silhueta")
    eixo.set_title(f"Silhueta registro a registro, por segmento (k = {k})")
    tabela = part.silhueta_por_grupo(dados, rotulos)
    salvar_figura(fig, SECAO, "m3-silhueta-por-segmento", tabela)
    return tabela


# --------------------------------------------------------------------------- #
# 4.3 — Construção dos modelos
# --------------------------------------------------------------------------- #


def _atributo_dominante(curada: pd.DataFrame, rotulos: np.ndarray) -> tuple[str, float]:
    """Qual atributo mais separa os grupos — a razão entre variância entre e dentro.

    É o que revela o que o algoritmo *de fato* usou para particionar, por trás
    da métrica agregada.
    """
    colunas = dic.NUMERICAS + dic.ORDINAIS
    dados = curada.assign(_grupo=rotulos)
    razoes = {}
    for coluna in colunas:
        media_geral = dados[coluna].mean()
        grupos = dados.groupby("_grupo")[coluna]
        entre = ((grupos.mean() - media_geral) ** 2 * grupos.size()).sum()
        dentro = ((dados[coluna] - grupos.transform("mean")) ** 2).sum()
        razoes[coluna] = entre / dentro if dentro > 0 else np.nan
    vencedor = max(razoes, key=lambda c: razoes[c])
    return dic.rotulo(vencedor), float(razoes[vencedor])


def experimento_escala(matriz: pd.DataFrame, curada: pd.DataFrame, k: int) -> pd.DataFrame:
    """Sensibilidade à escala: quatro escalonadores comparados por ARI."""
    resumo, ari = est.sensibilidade_escala(matriz, k)

    # A silhueta sozinha engana aqui. Esta coluna mostra por qual atributo cada
    # pré-processamento acabou particionando a carteira.
    dominantes = []
    for escalador in resumo.index:
        dados, _ = preparacao.preparar_espaco(matriz, escalador=escalador)
        rotulos = KMeans(n_clusters=k, n_init=20, random_state=config.SEMENTE).fit_predict(dados)
        atributo, razao = _atributo_dominante(curada, rotulos)
        dominantes.append({"atributo_dominante": atributo, "razao_entre_dentro": round(razao, 2)})
    resumo = pd.concat([resumo, pd.DataFrame(dominantes, index=resumo.index)], axis=1)

    salvar_tabela(resumo, SECAO, "m4-sensibilidade-escala")
    salvar_tabela(ari, SECAO, "m4-ari-entre-escalonadores")

    fig, eixos = plt.subplots(1, 2, figsize=(14, 5.2), constrained_layout=True)
    cores = [
        config.CORAL if nome != "padrao" else config.AZUL_PROFUNDO for nome in resumo.index
    ]
    resumo["silhueta"].plot.bar(ax=eixos[0], color=cores, rot=0)
    eixos[0].bar_label(eixos[0].containers[0], fmt="%.3f", padding=3, fontsize=9)
    eixos[0].axhline(config.SILHUETA_MINIMA, ls=":", color=config.CINZA)
    eixos[0].set_ylabel("silhueta")
    eixos[0].set_title(
        "Silhueta por escalonador — e o atributo que de fato particionou\n"
        "(azul: o escolhido; a maior silhueta é a pior segmentação)", fontsize=10
    )
    eixos[0].set_xlabel("")
    for posicao, nome in enumerate(resumo.index):
        eixos[0].annotate(
            resumo.loc[nome, "atributo_dominante"], xy=(posicao, 0.01), ha="center", va="bottom",
            rotation=90, fontsize=8, color="white", fontweight="bold",
        )

    sns.heatmap(ari.astype(float), annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1,
                ax=eixos[1], linewidths=0.5, linecolor="white",
                cbar_kws={"label": "índice de Rand ajustado"})
    eixos[1].set_title("Concordância entre as partições resultantes")
    fig.suptitle(
        f"Sensibilidade à escala — o mesmo K-Means (k={k}) sobre quatro pré-processamentos",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "m4-sensibilidade-escala", resumo)
    return resumo


def experimento_hierarquica(dados: np.ndarray, k: int) -> pd.DataFrame:
    """Dendrogramas com quatro critérios de ligação e a justificativa do corte."""
    condensadas = pdist(dados)
    comparativo = hier.comparar_ligacoes(dados, condensadas, k)
    salvar_tabela(comparativo, SECAO, "m6-comparacao-ligacoes")

    fig, eixos = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    for eixo, ligacao in zip(eixos.ravel(), hier.LIGACOES, strict=True):
        matriz = hier.matriz_ligacao(dados, ligacao)
        hier.desenhar_dendrograma(
            eixo, matriz, k,
            f"{ligacao}  ·  cofenético {comparativo.loc[ligacao, 'cofenetico']:.3f}  ·  "
            f"maior/menor grupo {comparativo.loc[ligacao, 'razao_maior_menor']:.0f}×",
            config.CORAL,
        )
    fig.suptitle(
        "Clusterização hierárquica — quatro critérios de ligação sobre o mesmo espaço",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "m6-dendrogramas", comparativo)

    ligacao_escolhida = "ward"
    matriz = hier.matriz_ligacao(dados, ligacao_escolhida)
    alturas = hier.alturas_de_fusao(matriz, ultimas=12)
    salvar_tabela(alturas, SECAO, "m6-alturas-de-fusao")

    fig, eixo = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    eixo.bar(alturas.index.astype(str), alturas["altura"], color=config.AZUL_COBALTO)
    destaque = alturas.index.get_loc(k)
    eixo.patches[destaque].set_color(config.CORAL)
    eixo.set_xlabel("nº de grupos após a fusão")
    eixo.set_ylabel("altura da fusão (Ward)")
    eixo.set_title("Altura das últimas fusões — o corte se justifica onde o salto é grande")
    eixo.invert_xaxis()
    salvar_figura(fig, SECAO, "m6-alturas-de-fusao", alturas)
    return comparativo


def experimento_densidade(
    dados: np.ndarray, curada: pd.DataFrame
) -> tuple[np.ndarray, pd.DataFrame]:
    """DBSCAN calibrado pelo gráfico k-distância e Mean Shift por varredura de banda."""
    min_amostras = MULTIPLICADOR_MINPTS * dados.shape[1]
    curva = den.curva_k_distancia(dados, min_amostras)
    indice, eps_joelho = den.joelho_k_distancia(curva)

    grade = np.round(np.arange(eps_joelho - 1.5, eps_joelho + 1.6, 0.25), 3)
    grade = grade[grade > 0]
    varredura = den.varrer_dbscan(dados, grade, min_amostras)
    salvar_tabela(varredura, SECAO, "m7-dbscan-varredura")

    # Dentro do teto de ruído do Canvas, o eps que produz mais grupos.
    aceitaveis = varredura[varredura["pct_ruido"] <= config.RUIDO_MAXIMO]
    eps_final = float(aceitaveis["grupos"].idxmax()) if len(aceitaveis) else float(eps_joelho)
    rotulos = den.aplicar_dbscan(dados, eps_final, min_amostras)

    fig, eixos = plt.subplots(1, 3, figsize=(17, 5), constrained_layout=True)
    eixos[0].plot(curva, color=config.AZUL_PROFUNDO, lw=2)
    eixos[0].axvline(indice, ls="--", color=config.CORAL)
    eixos[0].axhline(eps_joelho, ls="--", color=config.CORAL)
    eixos[0].annotate(f"joelho: eps ≈ {eps_joelho:.2f}", xy=(indice, eps_joelho), xytext=(-140, 20),
                      textcoords="offset points", color=config.CORAL, fontweight="bold")
    eixos[0].set_xlabel("registros ordenados")
    eixos[0].set_ylabel(f"distância ao {min_amostras}º vizinho")
    eixos[0].set_title(f"Gráfico k-distância (minPts = 2 × d = {min_amostras})")

    eixos[1].plot(varredura.index, varredura["grupos"], marker="o", color=config.AZUL_COBALTO,
                  label="grupos encontrados")
    eixo_ruido = eixos[1].twinx()
    eixo_ruido.plot(varredura.index, 100 * varredura["pct_ruido"], marker="s", color=config.CORAL,
                    label="% de ruído")
    eixo_ruido.axhline(100 * config.RUIDO_MAXIMO, ls=":", color=config.CINZA)
    eixo_ruido.set_ylabel("% de ruído", color=config.CORAL)
    eixo_ruido.grid(False)
    eixos[1].set_xlabel("eps")
    eixos[1].set_ylabel("nº de grupos", color=config.AZUL_COBALTO)
    eixos[1].set_title("Varredura de eps: grupos × ruído")

    ruido = rotulos == -1
    eixos[2].scatter(curada.loc[~ruido, "area_habitavel"], curada.loc[~ruido, "qualidade_geral"],
                     s=8, alpha=0.25, color=config.AZUL_CLARO, edgecolors="none", label="agrupado")
    eixos[2].scatter(curada.loc[ruido, "area_habitavel"], curada.loc[ruido, "qualidade_geral"],
                     s=26, alpha=0.9, color=config.CORAL, edgecolors="white", linewidths=0.3,
                     label=f"ruído ({ruido.sum()} imóveis)")
    eixos[2].set_xlabel(dic.rotulo("area_habitavel"))
    eixos[2].set_ylabel(dic.rotulo("qualidade_geral"))
    eixos[2].set_title(f"Resultado com eps = {eps_final:.2f}")
    eixos[2].legend(fontsize=8)
    fig.suptitle("DBSCAN — calibração e diagnóstico", fontsize=13, fontweight="bold",
                 color=config.AZUL_PROFUNDO)
    salvar_figura(fig, SECAO, "m7-dbscan", varredura)

    perfil_ruido = den.perfil_do_ruido(curada, rotulos, dic.NUMERICAS + dic.ORDINAIS)
    salvar_tabela(perfil_ruido, SECAO, "m7-perfil-do-ruido")

    lista_ruido = curada.loc[ruido, ["pid", "bairro", "area_habitavel", "qualidade_geral",
                                     "idade_imovel", "tipo_construcao", "preco_venda"]]
    salvar_tabela(lista_ruido.head(50), SECAO, "m7-imoveis-fora-de-padrao", indice=False)

    mean_shift = den.varrer_mean_shift(dados)
    salvar_tabela(mean_shift, SECAO, "m8-mean-shift")

    fig, eixo = plt.subplots(figsize=(9, 4.6), constrained_layout=True)
    eixo.plot(mean_shift["bandwidth"], mean_shift["grupos"], marker="o", color=config.AZUL_PROFUNDO,
              lw=2)
    for _, linha in mean_shift.iterrows():
        eixo.annotate(f"{100 * linha['maior_grupo_pct']:.0f}% em um grupo",
                      xy=(linha["bandwidth"], linha["grupos"]), xytext=(6, 8),
                      textcoords="offset points", fontsize=8, color=config.CINZA)
    eixo.set_xlabel("largura de banda estimada")
    eixo.set_ylabel("nº de grupos emergentes")
    eixo.set_title("Mean Shift — o número de grupos emerge da largura de banda")
    salvar_figura(fig, SECAO, "m8-mean-shift", mean_shift)

    return rotulos, varredura


def experimento_gmm(dados: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """GMM: BIC e AIC por tipo de covariância, e a atribuição probabilística."""
    varredura = mis.varrer_gmm(dados, 2, 10)
    salvar_tabela(varredura, SECAO, "m9-gmm-varredura", indice=False)

    fig, eixos = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    for eixo, criterio in zip(eixos, ("bic", "aic"), strict=True):
        for cor, tipo in zip(config.PALETA, mis.COVARIANCIAS, strict=False):
            recorte = varredura[varredura["covariancia"] == tipo]
            eixo.plot(recorte["k"], recorte[criterio], marker="o", label=tipo, color=cor)
        eixo.axvspan(config.K_MAXIMO_NEGOCIO + 0.5, 10.3, color="#F4D35E", alpha=0.18)
        eixo.set_xlabel("k")
        eixo.set_ylabel(criterio.upper())
        eixo.set_title(f"{criterio.upper()} por tipo de covariância (menor é melhor)")
        eixo.legend(title="covariância", fontsize=8)
    fig.suptitle(
        "GMM — seleção por critérios de informação. Nenhuma curva apresenta mínimo no "
        "intervalo: a base é um contínuo, não uma mistura de gaussianas separadas.",
        fontsize=12, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "m9-gmm-bic-aic", varredura)

    melhor = (
        varredura[varredura["k"] == k].sort_values("bic").iloc[0]["covariancia"]
    )
    _, rotulos, probabilidades = mis.ajustar_gmm(dados, k, melhor)
    confianca = mis.classificar_confianca(probabilidades)
    salvar_tabela(confianca.value_counts().to_frame("imóveis"), SECAO, "m9-gmm-confianca")

    fig, eixo = plt.subplots(figsize=(9, 4.6), constrained_layout=True)
    eixo.hist(probabilidades.max(axis=1), bins=40, color=config.ROXO, edgecolor="white")
    eixo.axvline(0.60, ls="--", color=config.CORAL)
    eixo.axvline(0.80, ls="--", color=config.VERDE)
    eixo.set_xlabel("probabilidade do segmento mais provável")
    eixo.set_ylabel("imóveis")
    eixo.set_title(
        f"GMM (k={k}, covariância '{melhor}') — grau de pertencimento.\n"
        "À esquerda da linha vermelha, o modelo não decidiu: ação automática exige revisão."
    )
    salvar_figura(fig, SECAO, "m9-gmm-pertencimento",
                  pd.DataFrame({"probabilidade_maxima": probabilidades.max(axis=1)}).describe())
    return rotulos, probabilidades, varredura


def experimento_reducao(
    dados: np.ndarray, nomes: list[str], rotulos: np.ndarray, k: int
) -> pd.DataFrame:
    """PCA e Kernel PCA: variância explicada, cargas e legibilidade da projeção."""
    modelo, projecao = red.ajustar_pca(dados)
    variancia = red.variancia_explicada(modelo)
    salvar_tabela(variancia, SECAO, "m10-pca-variancia")

    tabela_cargas = red.cargas(modelo, [dic.rotulo(n) for n in nomes], quantos=3)
    salvar_tabela(tabela_cargas, SECAO, "m10-pca-cargas")

    fig, eixos = plt.subplots(1, 3, figsize=(17, 5.2), constrained_layout=True)
    eixos[0].bar(range(1, len(variancia) + 1), variancia["variancia_explicada"],
                 color=config.AZUL_COBALTO)
    eixo_acumulado = eixos[0].twinx()
    eixo_acumulado.plot(range(1, len(variancia) + 1), variancia["acumulada"], color=config.CORAL,
                        marker="o", ms=4)
    eixo_acumulado.axhline(0.80, ls="--", color=config.CINZA)
    eixo_acumulado.set_ylim(0, 1.02)
    eixo_acumulado.grid(False)
    eixo_acumulado.set_ylabel("acumulada", color=config.CORAL)
    eixos[0].set_xlabel("componente")
    eixos[0].set_ylabel("variância explicada")
    eixos[0].set_title(
        f"Scree plot — {red.componentes_para(modelo, 0.80)} componentes para 80% da variância"
    )

    for grupo in range(k):
        marcador = rotulos == grupo
        eixos[1].scatter(projecao[marcador, 0], projecao[marcador, 1], s=9, alpha=0.55,
                         color=pers.cores()[grupo], label=pers.PERSONAS[grupo]["codigo"],
                         edgecolors="none")
    eixos[1].set_xlabel(f"CP1 — porte e padrão ({variancia['variancia_explicada'].iloc[0]:.1%})")
    eixos[1].set_ylabel(f"CP2 — maturidade ({variancia['variancia_explicada'].iloc[1]:.1%})")
    eixos[1].set_title("Segmentos projetados nos dois primeiros componentes")
    eixos[1].legend(fontsize=8, markerscale=2)

    sns.heatmap(tabela_cargas, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=eixos[2],
                linewidths=0.5, linecolor="white", cbar_kws={"label": "carga"})
    eixos[2].set_title("Cargas — o que cada componente significa")
    fig.suptitle("Redução de dimensionalidade por PCA", fontsize=13, fontweight="bold",
                 color=config.AZUL_PROFUNDO)
    salvar_figura(fig, SECAO, "m10-pca", variancia)

    kernels = red.comparar_kernels(dados, rotulos)
    salvar_tabela(kernels, SECAO, "m11-kernel-pca")

    fig, eixos = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    for eixo, kernel in zip(eixos, ("linear", "rbf", "cosine"), strict=True):
        _, projetado = red.ajustar_kernel_pca(dados, kernel=kernel, componentes=2)
        for grupo in range(k):
            marcador = rotulos == grupo
            eixo.scatter(projetado[marcador, 0], projetado[marcador, 1], s=8, alpha=0.5,
                         color=pers.cores()[grupo], edgecolors="none")
        eixo.set_title(
            f"kernel '{kernel}' — silhueta na projeção "
            f"{kernels.loc[kernel, 'silhueta_na_projecao_2d']:.3f}"
        )
        eixo.set_xlabel("componente 1")
        eixo.set_ylabel("componente 2")
    fig.suptitle(
        "Kernel PCA — a projeção fica mais legível, mas perde as cargas: serve para "
        "visualizar, não para explicar",
        fontsize=12, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "m11-kernel-pca", kernels)
    return variancia


# --------------------------------------------------------------------------- #
# 4.4 — Avaliação técnica: a matriz comparativa
# --------------------------------------------------------------------------- #


def matriz_comparativa(
    dados: np.ndarray, particoes: dict[str, np.ndarray], gower: np.ndarray, k: int
) -> pd.DataFrame:
    """Consolida métricas quantitativas e critérios qualitativos por algoritmo.

    Note:
        Todas as métricas são calculadas **no mesmo espaço de referência** (o
        euclidiano padronizado), independentemente do espaço em que cada
        algoritmo foi ajustado. É a única forma de comparar. A exceção é a
        silhueta do K-Medoids/Gower, medida na própria dissimilaridade de Gower
        e marcada como não comparável: silhueta calculada em espaços métricos
        diferentes não é uma escala comum, e tratá-la como se fosse é o erro
        que essa nota existe para evitar.
    """
    qualitativo = {
        "K-Means (euclidiano)": (
            "esférica", "centroide médio (não existe)", "sim — k fixado",
            "escolhido: estável, interpretável e dentro do teto",
        ),
        "K-Means (euclid. + one-hot)": (
            "esférica", "centroide médio", "sim — k fixado",
            "28 binárias diluem a distância; silhueta cai sem mudar a partição",
        ),
        "K-Medoids (Gower)": (
            "arbitrária", "medoide (imóvel real)", "sim — k fixado",
            "particiona por estilo construtivo: as nominais dominam o peso",
        ),
        "Hierárquica (Ward)": (
            "esférica", "sem representante", "não — corte no dendrograma",
            "concorda em 64% com o K-Means; útil como validação, não como produto",
        ),
        "DBSCAN": (
            "arbitrária", "sem representante", "não — emerge do eps",
            "degenerado: um grupo com 92% dos imóveis. Entrega o ruído, não a segmentação",
        ),
        "Mean Shift": (
            "arbitrária", "modo da densidade", "não — emerge da banda",
            "degenerado pelo mesmo motivo: não há vale de densidade neste espaço",
        ),
        "GMM": (
            "elipsoidal", "média da componente", "sim — BIC não minimiza",
            "grupos menos coesos; contribui com o grau de pertencimento",
        ),
    }

    linhas = []
    for nome, rotulos in particoes.items():
        validos = rotulos >= 0
        n_grupos = len(np.unique(rotulos[validos]))
        metricas = (
            part.metricas_internas(dados[validos], rotulos[validos])
            if n_grupos >= 2
            else {"silhueta": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan}
        )
        # Para o Gower, a silhueta precisa ser medida no próprio espaço métrico.
        espaco_metrica = "euclidiano padronizado (referência comum)"
        if nome == "K-Medoids (Gower)":
            metricas["silhueta"] = part.metricas_internas(
                None, rotulos, distancias=gower
            )["silhueta"]
            espaco_metrica = "dissimilaridade de Gower — NÃO comparável às demais"
        tamanhos = np.bincount(rotulos[validos]) if n_grupos else np.array([0])
        forma, representante, k_fixo, leitura = qualitativo.get(nome, ("—",) * 4)
        linhas.append(
            {
                "algoritmo": nome,
                "grupos": n_grupos,
                "silhueta": round(metricas["silhueta"], 4)
                if metricas["silhueta"] == metricas["silhueta"]
                else np.nan,
                "davies_bouldin": round(metricas["davies_bouldin"], 3)
                if metricas["davies_bouldin"] == metricas["davies_bouldin"]
                else np.nan,
                "calinski_harabasz": round(metricas["calinski_harabasz"], 1)
                if metricas["calinski_harabasz"] == metricas["calinski_harabasz"]
                else np.nan,
                "pct_ruido": round(100 * float((~validos).mean()), 2),
                "maior_grupo_pct": round(100 * float(tamanhos.max() / len(rotulos)), 1),
                "espaco_da_metrica": espaco_metrica,
                "forma_suposta": forma,
                "representante": representante,
                "k_definido_pelo_analista": k_fixo,
                "leitura_de_negocio": leitura,
            }
        )
    tabela = pd.DataFrame(linhas).set_index("algoritmo")
    salvar_tabela(tabela, SECAO, "m12-matriz-comparativa")

    concordancia = est.comparar_particoes(particoes)
    salvar_tabela(concordancia, SECAO, "m12-ari-entre-algoritmos")

    fig, eixos = plt.subplots(1, 2, figsize=(16, 5.5), constrained_layout=True)
    quantitativo = tabela[["silhueta"]].dropna().sort_values("silhueta")
    eixos[0].barh(quantitativo.index, quantitativo["silhueta"], color=config.AZUL_COBALTO)
    eixos[0].bar_label(eixos[0].containers[0], fmt="%.3f", padding=3, fontsize=9)
    eixos[0].axvline(config.SILHUETA_MINIMA, ls=":", color=config.CORAL)
    eixos[0].set_xlabel("silhueta")
    eixos[0].set_title("Coesão por algoritmo\n(a do Gower não é comparável: outro espaço métrico)",
                       fontsize=10)

    sns.heatmap(concordancia.astype(float), annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1,
                ax=eixos[1], linewidths=0.5, linecolor="white",
                cbar_kws={"label": "índice de Rand ajustado"})
    eixos[1].set_title("Concordância entre as partições", fontsize=10)
    eixos[1].tick_params(axis="x", rotation=35)
    fig.suptitle("Matriz comparativa de algoritmos", fontsize=13, fontweight="bold",
                 color=config.AZUL_PROFUNDO)
    salvar_figura(fig, SECAO, "m12-matriz-comparativa", tabela)

    contingencia = est.contingencia(
        particoes["K-Means (euclidiano)"], particoes["Hierárquica (Ward)"], "K-Means", "Ward"
    )
    salvar_tabela(contingencia, SECAO, "m12-contingencia-kmeans-ward")
    return tabela


# --------------------------------------------------------------------------- #
# Perfilagem
# --------------------------------------------------------------------------- #


def perfilar(curada: pd.DataFrame, rotulos: np.ndarray, gower: np.ndarray, k: int) -> pd.DataFrame:
    """Traduz os segmentos em perfil, assinatura, representante real e persona."""
    perfil = perf.perfil_por_segmento(curada, rotulos)
    salvar_tabela(perfil, SECAO, "m13-perfil-por-segmento")

    assinatura = perf.assinatura(curada, rotulos)
    salvar_tabela(assinatura, SECAO, "m13-assinatura")

    medoides = perf.medoides_reais(curada, rotulos, gower)
    salvar_tabela(medoides, SECAO, "m13-medoides-reais")

    salvar_tabela(pers.tabela_personas(), SECAO, "m14-personas")

    fig, eixo = plt.subplots(figsize=(12, 6), constrained_layout=True)
    dados_mapa = assinatura.T
    dados_mapa.index = [dic.rotulo(c) for c in dados_mapa.index]
    dados_mapa.columns = pers.nomes()
    sns.heatmap(dados_mapa, cmap="RdBu_r", center=0, annot=True, fmt=".1f", ax=eixo,
                linewidths=0.5, linecolor="white",
                cbar_kws={"label": "desvios da mediana da carteira (escala robusta)"})
    eixo.set_title("Assinatura de cada segmento — o que ele tem de diferente da carteira inteira")
    eixo.tick_params(axis="x", rotation=12)
    salvar_figura(fig, SECAO, "m13-assinatura", assinatura)

    fig, eixos = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    atributos = ["area_habitavel", "qualidade_geral", "idade_imovel", "banheiros_total",
                 "area_porao", "area_terreno"]
    dados_grafico = curada.assign(segmento=rotulos)
    for eixo, coluna in zip(eixos.ravel(), atributos, strict=True):
        caixas = [dados_grafico.loc[dados_grafico["segmento"] == g, coluna] for g in range(k)]
        desenho = eixo.boxplot(caixas, patch_artist=True, showfliers=False,
                               tick_labels=[pers.PERSONAS[g]["codigo"] for g in range(k)])
        for caixa, cor in zip(desenho["boxes"], pers.cores(), strict=True):
            caixa.set_facecolor(cor)
            caixa.set_alpha(0.8)
        for mediana in desenho["medians"]:
            mediana.set_color("white")
            mediana.set_linewidth(1.8)
        eixo.set_title(dic.rotulo(coluna), fontsize=10)
        if coluna in dic.ASSIMETRICAS:
            eixo.set_yscale("log")
    fig.suptitle("Perfil dos segmentos em unidades originais", fontsize=13, fontweight="bold",
                 color=config.AZUL_PROFUNDO)
    salvar_figura(fig, SECAO, "m13-perfil-unidades-originais", perfil)

    composicoes = {}
    fig, eixos = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    for eixo, coluna in zip(eixos, ("tipo_construcao", "estilo", "tipo_garagem"), strict=True):
        tabela = perf.composicao_nominal(curada, rotulos, coluna)
        composicoes[coluna] = tabela
        tabela.plot.barh(stacked=True, ax=eixo, color=config.PALETA, width=0.75)
        eixo.set_yticklabels([pers.PERSONAS[g]["codigo"] for g in range(k)])
        eixo.set_xlabel("% do segmento")
        eixo.set_ylabel("")
        eixo.set_title(dic.rotulo(coluna), fontsize=10)
        eixo.legend(fontsize=7, ncol=2, loc="lower right")
    fig.suptitle("Composição nominal por segmento", fontsize=13, fontweight="bold",
                 color=config.AZUL_PROFUNDO)
    salvar_figura(fig, SECAO, "m13-composicao-nominal", pd.concat(composicoes))
    return perfil


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #


def executar() -> dict:
    """Roda a fase de modelagem inteira e devolve o resumo das decisões."""
    configurar_estilo()
    config.garantir_diretorios()

    curada = carregar_curada()
    matriz = construir_matriz_modelagem(curada)

    espacos, _ = comparar_espacos(matriz)
    euclidiano, com_onehot, gower, nomes = (
        espacos["euclidiano"], espacos["onehot"], espacos["gower"], espacos["nomes"]
    )

    k, varredura, decisao = escolher_k(euclidiano)

    kmeans = KMeans(n_clusters=k, init="k-means++", n_init=20, random_state=config.SEMENTE)
    rotulos_brutos = kmeans.fit_predict(euclidiano)
    rotulos = pers.ordenar_canonicamente(curada, rotulos_brutos)

    grafico_silhueta(euclidiano, rotulos, k)
    experimento_escala(matriz, curada, k)
    experimento_hierarquica(euclidiano, k)

    kmedoids = part.kmedoids(gower, k, reinicios=12)
    rotulos_gower = pers.ordenar_canonicamente(curada, kmedoids.rotulos)

    rotulos_onehot = pers.ordenar_canonicamente(
        curada, KMeans(n_clusters=k, n_init=20, random_state=config.SEMENTE).fit_predict(com_onehot)
    )
    rotulos_ward = pers.ordenar_canonicamente(
        curada, hier.cortar(hier.matriz_ligacao(euclidiano, "ward"), k)
    )
    rotulos_dbscan, _ = experimento_densidade(euclidiano, curada)
    rotulos_gmm, probabilidades, _ = experimento_gmm(euclidiano, k)

    from sklearn.cluster import MeanShift, estimate_bandwidth

    largura = estimate_bandwidth(euclidiano, quantile=0.2, n_samples=1000,
                                 random_state=config.SEMENTE)
    rotulos_meanshift = MeanShift(bandwidth=largura, bin_seeding=True).fit_predict(euclidiano)

    particoes = {
        "K-Means (euclidiano)": rotulos,
        "K-Means (euclid. + one-hot)": rotulos_onehot,
        "K-Medoids (Gower)": rotulos_gower,
        "Hierárquica (Ward)": rotulos_ward,
        "DBSCAN": rotulos_dbscan,
        "Mean Shift": rotulos_meanshift,
        "GMM": pers.ordenar_canonicamente(curada, rotulos_gmm),
    }
    comparativa = matriz_comparativa(euclidiano, particoes, gower, k)
    experimento_reducao(euclidiano, nomes, rotulos, k)
    perfilar(curada, rotulos, gower, k)

    # Base segmentada: é o insumo das regras de associação, da avaliação e da aplicação.
    segmentada = curada.copy()
    segmentada["segmento"] = rotulos
    segmentada["persona"] = [pers.PERSONAS[int(s)]["nome"] for s in rotulos]
    segmentada["codigo_segmento"] = [pers.codigo(s) for s in rotulos]
    segmentada["confianca_gmm"] = mis.classificar_confianca(probabilidades).to_numpy()
    segmentada["fora_de_padrao_dbscan"] = rotulos_dbscan == -1
    segmentada.to_parquet(config.SEGMENTOS, index=False)

    # Modelo final: pré-processador e K-Means em um único objeto, para que a
    # aplicação nunca reimplemente a preparação.
    pipeline_final = Pipeline(
        [
            ("preparacao", preparacao.construir_preprocessador("padrao", com_nominais=False)),
            ("kmeans", kmeans),
        ]
    )
    pipeline_final.fit(matriz)
    dump(pipeline_final, config.MODELS / "pipeline_segmentacao.joblib")

    ordem = pers.ordenar_canonicamente(curada, pipeline_final.named_steps["kmeans"].labels_)
    traducao = {
        int(bruto): int(canonico)
        for bruto, canonico in zip(pipeline_final.named_steps["kmeans"].labels_, ordem, strict=True)
    }

    metadados = {
        "versao_modelo": "1.0.0",
        "algoritmo": "KMeans (k-means++, n_init=20)",
        "k": int(k),
        "semente": config.SEMENTE,
        "espaco_de_atributos": nomes,
        "variaveis_log1p": dic.ASSIMETRICAS,
        "escalador": "StandardScaler",
        "rotulo_reservado": dic.ROTULO_RESERVADO,
        "reservada_validacao": dic.RESERVADA_VALIDACAO,
        "traducao_rotulo_bruto_para_canonico": traducao,
        "silhueta": float(comparativa.loc["K-Means (euclidiano)", "silhueta"]),
        "estabilidade_ari": float(varredura.loc[k, "ari_medio"]),
        "registros_treino": int(len(matriz)),
        "periodo_treino": f"{int(curada['ano_venda'].min())}–{int(curada['ano_venda'].max())}",
        "personas": {
            str(indice): {"codigo": dados["codigo"], "nome": dados["nome"]}
            for indice, dados in pers.PERSONAS.items()
        },
    }
    salvar_json(metadados, config.MODELS / "metadados_segmentacao.json")

    return {
        "k": k,
        "decisao_k": decisao,
        "comparativa": comparativa,
        "segmentos": segmentada["codigo_segmento"].value_counts().to_dict(),
    }


if __name__ == "__main__":
    resumo = executar()
    print(f"k escolhido: {resumo['k']}")
    print(f"Segmentos: {resumo['segmentos']}")
    print(f"Figuras em {config.FIGURES / SECAO}")
