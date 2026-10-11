"""As oito fases do fluxo de análise exploratória.

    Base de dados
       ├─ 1ª  Distribuição dos atributos
       ├─ 2ª  Análise univariada
       ├─ 3ª  Análise bivariada
       ├─ 4ª  Análise multivariada
       ├─ 5ª  Valores ausentes
       ├─ 6ª  Valores discrepantes
       ├─ 7ª  Detecção de correlação
       └─ 8ª  Seleção de características
       ▼
    Coleção de insights

Cada função executa uma fase, grava figura e tabela-fonte em disco e devolve os
achados. :func:`executar` roda as oito na ordem e consolida a coleção de
insights em ``reports/tables/eda/colecao-de-insights.csv``.

Nenhuma fase toca no rótulo reservado (``preco_venda``).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src import config
from src.data import dicionario as dic
from src.data import qualidade as q
from src.data.ingestao import carregar_bruto, inventario_sentinelas
from src.data.preparacao import carregar_curada
from src.eda import estatistica as est
from src.utils.io import configurar_estilo, salvar_figura, salvar_tabela

SECAO = "eda"

#: Coleção de insights acumulada pelas oito fases.
INSIGHTS: list[dict[str, str]] = []


def _registrar(fase: str, insight: str, consequencia: str, evidencia: str) -> None:
    """Acrescenta um achado à coleção de insights.

    Um insight sem consequência é curiosidade. O campo ``consequencia`` é o que
    liga a fase exploratória às decisões de preparação e modelagem.
    """
    INSIGHTS.append(
        {
            "fase": fase,
            "insight": insight,
            "consequencia": consequencia,
            "evidencia": evidencia,
        }
    )


# --------------------------------------------------------------------------- #
# 1ª fase — Distribuição dos atributos
# --------------------------------------------------------------------------- #


def fase_1_distribuicao_atributos(bruto: pd.DataFrame, curada: pd.DataFrame) -> pd.DataFrame:
    """Panorama do conjunto: quantas colunas de cada natureza, e com que cardinalidade."""
    perfil = q.perfil_colunas(bruto)
    salvar_tabela(perfil, SECAO, "f1-perfil-colunas-origem")

    numericas = bruto.select_dtypes(include=[np.number]).columns
    contagem = pd.Series(
        {
            "Numéricas na origem": len(numericas),
            "Textuais na origem": bruto.shape[1] - len(numericas),
            "Ordinais mapeadas": len(dic.ESCALAS_ORDINAIS),
            "Nominais na modelagem": len(dic.NOMINAIS),
            "Numéricas na modelagem": len(dic.NUMERICAS),
            "Derivadas criadas": len(dic.BINARIAS) + 5,
        }
    )

    cardinalidade = (
        bruto.select_dtypes(exclude=[np.number]).nunique().sort_values(ascending=False).head(15)
    )

    fig, eixos = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    contagem.sort_values().plot.barh(ax=eixos[0], color=config.AZUL_PROFUNDO)
    eixos[0].set_title("Composição do conjunto de atributos")
    eixos[0].set_xlabel("nº de colunas")
    eixos[0].bar_label(eixos[0].containers[0], padding=3, fontsize=9)

    cardinalidade.sort_values().plot.barh(ax=eixos[1], color=config.AZUL_COBALTO)
    eixos[1].set_title("Cardinalidade das 15 colunas textuais mais diversas")
    eixos[1].set_xlabel("valores distintos")
    eixos[1].bar_label(eixos[1].containers[0], padding=3, fontsize=9)
    fig.suptitle(
        "1ª fase — Distribuição dos atributos",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f1-panorama-atributos", contagem.to_frame("colunas"))

    constantes = q.colunas_constantes(bruto)
    salvar_tabela(constantes, SECAO, "f1-colunas-constantes")

    _registrar(
        "1ª — Distribuição dos atributos",
        f"A origem traz {bruto.shape[1]} colunas para {bruto.shape[0]} imóveis, sendo "
        f"{bruto.shape[1] - len(numericas)} textuais; {len(dic.ESCALAS_ORDINAIS)} delas "
        "são ordinais disfarçadas de texto.",
        "Tratar as 20 ordinais como nominais multiplicaria a dimensionalidade e "
        "destruiria a ordem. Elas são mapeadas para inteiro na preparação.",
        "f1-panorama-atributos.png / f1-perfil-colunas-origem.csv",
    )
    _registrar(
        "1ª — Distribuição dos atributos",
        f"{len(constantes)} colunas são praticamente constantes: "
        + ", ".join(
            f"`{c}` ({constantes.loc[c, 'pct_valor_mais_frequente']:.1f}%)"
            for c in constantes.index
        ),
        "Variância quase nula não separa grupo nenhum e ainda gera divisão por zero "
        "na padronização. Nenhuma delas entra no espaço de atributos.",
        "f1-colunas-constantes.csv",
    )
    _registrar(
        "1ª — Distribuição dos atributos",
        f"`bairro` tem {curada['bairro'].nunique()} categorias — a maior cardinalidade "
        "nominal da base.",
        "Em one-hot viraria 28 colunas binárias que dominariam a distância euclidiana. "
        "Como localização é o principal determinante de preço, fica reservada para "
        "validação externa dos segmentos.",
        "f1-panorama-atributos.png",
    )
    return perfil


# --------------------------------------------------------------------------- #
# 2ª fase — Análise univariada
# --------------------------------------------------------------------------- #


def fase_2_univariada(curada: pd.DataFrame) -> pd.DataFrame:
    """Distribuição, dispersão, assimetria e curtose de cada variável do espaço."""
    resumo = q.resumo_numericas(curada, dic.NUMERICAS + dic.ORDINAIS)
    salvar_tabela(resumo, SECAO, "f2-resumo-numericas")

    # Histogramas das numéricas contínuas e discretas.
    fig, eixos = plt.subplots(4, 3, figsize=(14, 12), constrained_layout=True)
    for eixo, coluna in zip(eixos.ravel(), dic.NUMERICAS, strict=False):
        serie = curada[coluna]
        eixo.hist(serie, bins=40, color=config.AZUL_COBALTO, edgecolor="white", linewidth=0.4)
        eixo.axvline(
            serie.median(), color=config.CORAL, lw=2, label=f"mediana {serie.median():,.0f}"
        )
        eixo.axvline(
            serie.mean(), color=config.AMARELO, lw=2, ls="--", label=f"média {serie.mean():,.0f}"
        )
        eixo.set_title(f"{dic.rotulo(coluna)}  (assimetria {serie.skew():.2f})", fontsize=10)
        eixo.legend(fontsize=7)
    for eixo in eixos.ravel()[len(dic.NUMERICAS) :]:
        eixo.axis("off")
    fig.suptitle(
        "2ª fase — Distribuição das variáveis numéricas",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f2-histogramas-numericas", resumo)

    # Boxplots padronizados: mostram, no mesmo eixo, quem tem cauda.
    padronizado = pd.DataFrame(
        StandardScaler().fit_transform(curada[dic.NUMERICAS]), columns=dic.NUMERICAS
    )
    ordem = padronizado.skew().sort_values(ascending=False).index
    fig, eixo = plt.subplots(figsize=(12, 5.5), constrained_layout=True)
    sns.boxplot(
        data=padronizado[ordem],
        orient="v",
        ax=eixo,
        color=config.AZUL_CLARO,
        fliersize=2,
        linewidth=1,
    )
    eixo.set_xticks(range(len(ordem)))
    eixo.set_xticklabels([dic.rotulo(c) for c in ordem], rotation=35, ha="right")
    eixo.set_ylabel("escore padronizado")
    eixo.set_title(
        "2ª fase — Dispersão comparada (variáveis padronizadas, ordenadas por assimetria)"
    )
    salvar_figura(fig, SECAO, "f2-boxplots-numericas", padronizado[ordem].describe().T)

    # Ordinais e nominais.
    fig, eixos = plt.subplots(2, 3, figsize=(14, 7), constrained_layout=True)
    for eixo, coluna in zip(eixos.ravel(), dic.ORDINAIS, strict=False):
        contagem = curada[coluna].value_counts().sort_index()
        eixo.bar(
            contagem.index.astype(str), contagem.to_numpy(), color=config.VERDE, edgecolor="white"
        )
        eixo.set_title(dic.rotulo(coluna), fontsize=10)
        eixo.set_xlabel("nível")
    fig.suptitle(
        "2ª fase — Distribuição das variáveis ordinais",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f2-ordinais", curada[dic.ORDINAIS].describe().T)

    fig, eixos = plt.subplots(2, 3, figsize=(14, 7.5), constrained_layout=True)
    nominais_grafico = dic.NOMINAIS + ["bairro"]
    for eixo, coluna in zip(eixos.ravel(), nominais_grafico, strict=False):
        contagem = curada[coluna].value_counts().head(10)
        eixo.barh(
            contagem.index[::-1].astype(str),
            contagem.to_numpy()[::-1],
            color=config.ROXO,
            edgecolor="white",
        )
        eixo.set_title(dic.rotulo(coluna), fontsize=10)
        eixo.tick_params(axis="y", labelsize=8)
    fig.suptitle(
        "2ª fase — Distribuição das variáveis nominais (10 categorias mais frequentes)",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    contagens_nominais = pd.concat(
        {c: curada[c].value_counts(normalize=True).head(10).round(4) for c in nominais_grafico}
    )
    salvar_figura(fig, SECAO, "f2-nominais", contagens_nominais.to_frame("proporcao"))

    assimetria = resumo.loc[dic.NUMERICAS, "assimetria"].abs().sort_values(ascending=False)
    acima = assimetria[assimetria > dic.LIMIAR_ASSIMETRIA]
    _registrar(
        "2ª — Univariada",
        f"{len(acima)} variáveis superam o limiar de assimetria "
        f"{dic.LIMIAR_ASSIMETRIA:.2f}: "
        + ", ".join(f"`{c}` ({assimetria[c]:.2f})" for c in acima.index)
        + f". A campeã é a área do terreno, com {assimetria.iloc[0]:.1f}.",
        "Só essas recebem `log1p` antes da padronização. Sem a transformação, a cauda "
        "longa do terreno domina a distância euclidiana e o K-Means devolve um cluster "
        "gigante com satélites de um elemento. Transformar as demais seria hábito, não "
        "decisão — a área do porão fica de fora, com assimetria "
        f"{assimetria['area_porao']:.2f}.",
        "f2-histogramas-numericas.png / f2-resumo-numericas.csv",
    )
    pct_sem_porao = 100 * (curada["area_porao"] == 0).mean()
    pct_sem_garagem = 100 * (curada["area_garagem"] == 0).mean()
    pct_sem_varanda = 100 * (curada["area_varandas"] == 0).mean()
    _registrar(
        "2ª — Univariada",
        f"Três variáveis têm massa concentrada em zero: porão ({pct_sem_porao:.1f}% "
        f"sem), garagem ({pct_sem_garagem:.1f}% sem) e varandas ({pct_sem_varanda:.1f}% sem).",
        "O zero aqui é categoria ('não tem'), não medida. As flags binárias derivadas "
        "preservam essa informação, que a área sozinha esconde.",
        "f2-histogramas-numericas.png",
    )
    _registrar(
        "2ª — Univariada",
        f"`qualidade_geral` concentra {100 * curada['qualidade_geral'].between(5, 7).mean():.1f}% "
        "dos imóveis nos níveis 5 a 7, e `conservacao_geral` tem "
        f"{100 * (curada['conservacao_geral'] == 5).mean():.1f}% no nível 5.",
        "Conservação tem poder de separação baixo: quase todo imóvel é 'médio'. "
        "Vale acompanhar se ela sobrevive à seleção de características.",
        "f2-ordinais.png",
    )
    return resumo


# --------------------------------------------------------------------------- #
# 3ª fase — Análise bivariada
# --------------------------------------------------------------------------- #


def fase_3_bivariada(curada: pd.DataFrame) -> pd.DataFrame:
    """Relações entre pares de variáveis, respeitando a natureza de cada uma."""
    pares = [
        ("area_habitavel", "qualidade_geral"),
        ("area_habitavel", "comodos"),
        ("area_habitavel", "banheiros_total"),
        ("idade_imovel", "qualidade_geral"),
        ("area_terreno", "area_habitavel"),
        ("idade_imovel", "anos_desde_reforma"),
    ]
    fig, eixos = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    linhas_pares = []
    for eixo, (x, y) in zip(eixos.ravel(), pares, strict=False):
        eixo.scatter(
            curada[x], curada[y], s=8, alpha=0.25, color=config.AZUL_COBALTO, edgecolors="none"
        )
        rho = curada[x].corr(curada[y], method="spearman")
        eixo.set_xlabel(dic.rotulo(x))
        eixo.set_ylabel(dic.rotulo(y))
        eixo.set_title(f"ρ de Spearman = {rho:.2f}", fontsize=10)
        if x in dic.ASSIMETRICAS:
            eixo.set_xscale("log")
        linhas_pares.append({"variavel_x": x, "variavel_y": y, "spearman": round(rho, 3)})
    fig.suptitle(
        "3ª fase — Relações entre pares de variáveis numéricas",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    tabela_pares = pd.DataFrame(linhas_pares)
    salvar_figura(fig, SECAO, "f3-dispersao-pares", tabela_pares)

    # Associação entre nominais: V de Cramér, porque Pearson não se aplica.
    nominais = dic.NOMINAIS + ["bairro", "fundacao", "estilo_telhado"]
    cramer = est.matriz_cramer(curada, nominais)
    fig, eixo = plt.subplots(figsize=(8.5, 7), constrained_layout=True)
    sns.heatmap(
        cramer.astype(float),
        annot=True,
        fmt=".2f",
        cmap="Blues",
        vmin=0,
        vmax=1,
        ax=eixo,
        cbar_kws={"label": "V de Cramér"},
        linewidths=0.5,
        linecolor="white",
    )
    eixo.set_xticklabels([dic.rotulo(c) for c in nominais], rotation=35, ha="right")
    eixo.set_yticklabels([dic.rotulo(c) for c in nominais], rotation=0)
    eixo.set_title("3ª fase — Associação entre variáveis nominais (V de Cramér)")
    salvar_figura(fig, SECAO, "f3-cramer-nominais", cramer.round(3))

    # Razão de correlação: quanto uma nominal explica de uma numérica.
    eta = pd.DataFrame(
        {
            numerica: {
                nominal: round(est.razao_correlacao(curada[nominal], curada[numerica]), 3)
                for nominal in dic.NOMINAIS + ["bairro"]
            }
            for numerica in ["area_habitavel", "idade_imovel", "qualidade_geral", "area_terreno"]
        }
    )
    fig, eixo = plt.subplots(figsize=(8, 4), constrained_layout=True)
    sns.heatmap(
        eta,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        ax=eixo,
        vmin=0,
        vmax=1,
        cbar_kws={"label": "η² (variância explicada)"},
        linewidths=0.5,
        linecolor="white",
    )
    eixo.set_xticklabels([dic.rotulo(c) for c in eta.columns], rotation=25, ha="right")
    eixo.set_yticklabels([dic.rotulo(c) for c in eta.index], rotation=0)
    eixo.set_title("3ª fase — Quanto cada nominal explica de cada numérica (η²)")
    salvar_figura(fig, SECAO, "f3-eta-nominal-numerica", eta)

    rho_area_comodos = curada["area_habitavel"].corr(curada["comodos"], method="spearman")
    _registrar(
        "3ª — Bivariada",
        f"`area_habitavel` e `comodos` têm ρ = {rho_area_comodos:.2f}: "
        "medem quase a mesma coisa por caminhos diferentes.",
        "Uma das duas é redundante. A decisão vai para a 8ª fase, junto com as demais "
        "redundâncias detectadas.",
        "f3-dispersao-pares.png",
    )
    _registrar(
        "3ª — Bivariada",
        f"`bairro` explica {eta.loc['bairro', 'qualidade_geral']:.0%} da variância da "
        f"qualidade geral e {eta.loc['bairro', 'area_terreno']:.0%} da área do terreno.",
        "Confirma que o bairro carrega informação de produto — e, por tabela, de preço. "
        "Reforça a decisão de mantê-lo fora da modelagem e usá-lo como régua externa.",
        "f3-eta-nominal-numerica.png",
    )
    fora_diagonal = cramer.where(~np.eye(len(cramer), dtype=bool)).stack()
    par_mais_forte = fora_diagonal.idxmax()
    entre_nominais = cramer.loc[dic.NOMINAIS, dic.NOMINAIS]
    maximo_entre_nominais = entre_nominais.where(~np.eye(len(dic.NOMINAIS), dtype=bool)).max().max()
    _registrar(
        "3ª — Bivariada",
        f"A associação nominal mais forte é `{par_mais_forte[0]}` × `{par_mais_forte[1]}` "
        f"(V de Cramér = {fora_diagonal.max():.2f}); entre as nominais que entram na "
        f"modelagem, o máximo é "
        f"{maximo_entre_nominais:.2f}.",
        "Nenhum par de nominais do espaço de atributos passa de associação moderada. "
        "Não há redundância a remover entre elas — o que importa é o peso que cada uma "
        "recebe na distância, discutido na escolha entre espaço euclidiano e Gower.",
        "f3-cramer-nominais.png",
    )
    return cramer


# --------------------------------------------------------------------------- #
# 4ª fase — Análise multivariada
# --------------------------------------------------------------------------- #


def fase_4_multivariada(curada: pd.DataFrame) -> pd.DataFrame:
    """Estrutura conjunta: o que aparece quando se olham todas as variáveis de uma vez."""
    espaco = dic.NUMERICAS + dic.ORDINAIS
    matriz = curada[espaco].copy()
    for coluna in dic.ASSIMETRICAS:
        matriz[coluna] = np.log1p(matriz[coluna])
    padronizada = StandardScaler().fit_transform(matriz)

    pca = PCA(random_state=config.SEMENTE).fit(padronizada)
    projecao = pca.transform(padronizada)

    variancia = pd.DataFrame(
        {
            "componente": [f"CP{i + 1}" for i in range(len(pca.explained_variance_ratio_))],
            "variancia_explicada": pca.explained_variance_ratio_.round(4),
            "acumulada": np.cumsum(pca.explained_variance_ratio_).round(4),
        }
    ).set_index("componente")

    fig, eixos = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    eixos[0].bar(variancia.index, variancia["variancia_explicada"], color=config.AZUL_COBALTO)
    eixo_secundario = eixos[0].twinx()
    eixo_secundario.plot(variancia.index, variancia["acumulada"], color=config.CORAL, marker="o")
    eixo_secundario.axhline(0.8, ls="--", color=config.CINZA, lw=1)
    eixo_secundario.set_ylabel("acumulada", color=config.CORAL)
    eixo_secundario.set_ylim(0, 1.02)
    eixo_secundario.grid(False)
    eixos[0].set_ylabel("variância explicada")
    eixos[0].tick_params(axis="x", rotation=60, labelsize=7)
    eixos[0].set_title("Scree plot exploratório")

    dispersao = eixos[1].scatter(
        projecao[:, 0],
        projecao[:, 1],
        c=curada["qualidade_geral"],
        cmap="viridis",
        s=10,
        alpha=0.6,
        edgecolors="none",
    )
    fig.colorbar(dispersao, ax=eixos[1], label="qualidade geral")
    eixos[1].set_xlabel(f"CP1 ({pca.explained_variance_ratio_[0]:.1%})")
    eixos[1].set_ylabel(f"CP2 ({pca.explained_variance_ratio_[1]:.1%})")
    eixos[1].set_title("Projeção em 2 componentes, colorida pela qualidade")
    fig.suptitle(
        "4ª fase — Estrutura multivariada",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f4-pca-exploratorio", variancia)

    # Cargas: o que cada componente significa em linguagem de negócio.
    cargas = pd.DataFrame(
        pca.components_[:3].T,
        index=[dic.rotulo(c) for c in espaco],
        columns=["CP1", "CP2", "CP3"],
    ).round(3)
    fig, eixo = plt.subplots(figsize=(7.5, 6.5), constrained_layout=True)
    sns.heatmap(
        cargas,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        ax=eixo,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "carga"},
    )
    eixo.set_title("4ª fase — Cargas dos três primeiros componentes")
    salvar_figura(fig, SECAO, "f4-cargas-componentes", cargas)

    # Perfil médio por estilo construtivo: leitura multivariada legível.
    perfil_estilo = (
        curada.groupby("estilo")[espaco].mean().pipe(lambda d: (d - d.mean()) / d.std()).round(2)
    )
    fig, eixo = plt.subplots(figsize=(13, 5), constrained_layout=True)
    sns.heatmap(
        perfil_estilo,
        cmap="RdBu_r",
        center=0,
        annot=False,
        ax=eixo,
        linewidths=0.4,
        linecolor="white",
        cbar_kws={"label": "desvios da média"},
    )
    eixo.set_xticklabels([dic.rotulo(c) for c in espaco], rotation=40, ha="right", fontsize=8)
    eixo.set_title("4ª fase — Perfil padronizado por estilo construtivo")
    eixo.set_ylabel("")
    salvar_figura(fig, SECAO, "f4-perfil-por-estilo", perfil_estilo)

    n80 = int(np.searchsorted(variancia["acumulada"].to_numpy(), 0.80) + 1)
    _registrar(
        "4ª — Multivariada",
        f"São necessários {n80} componentes principais para reter 80% da variância de "
        f"{len(espaco)} variáveis; o CP1 sozinho retém "
        f"{pca.explained_variance_ratio_[0]:.1%}.",
        "Há redundância real, mas não a ponto de o problema ser unidimensional. "
        "PCA serve para visualização e para remover ruído, não para substituir o "
        "espaço original na modelagem.",
        "f4-pca-exploratorio.png / f4-cargas-componentes.csv",
    )
    _registrar(
        "4ª — Multivariada",
        "O CP1 carrega positivamente tamanho e qualidade ao mesmo tempo; o CP2 opõe "
        "idade e reforma às áreas de porão e terreno.",
        "Dá nome de negócio aos eixos: CP1 é 'porte e padrão' e CP2 é 'maturidade do "
        "imóvel'. É essa leitura que torna a projeção 2D defensável em uma banca.",
        "f4-cargas-componentes.png",
    )
    return variancia


# --------------------------------------------------------------------------- #
# 5ª fase — Valores ausentes
# --------------------------------------------------------------------------- #


def fase_5_ausentes(bruto: pd.DataFrame) -> pd.DataFrame:
    """Mapeia a ausência e distingue o que é estrutural do que é faltante de fato."""
    perfil = q.perfil_colunas(bruto)
    com_nulo = perfil[perfil["nulos"] > 0].copy()
    com_nulo["natureza"] = [
        "estrutural (o item não existe)"
        if coluna in dic.AUSENCIA_ESTRUTURAL
        else "faltante de fato"
        for coluna in com_nulo.index
    ]
    salvar_tabela(com_nulo, SECAO, "f5-ausentes-por-coluna")

    cores = [
        config.AZUL_COBALTO if natureza.startswith("estrutural") else config.CORAL
        for natureza in com_nulo["natureza"]
    ]
    fig, eixo = plt.subplots(figsize=(10, 7), constrained_layout=True)
    eixo.barh(com_nulo.index[::-1], com_nulo["pct_nulos"][::-1], color=cores[::-1])
    eixo.set_xlabel("% de ausência")
    eixo.set_title("5ª fase — Ausência por coluna, separada por natureza")
    marcadores = [
        plt.Rectangle((0, 0), 1, 1, color=config.AZUL_COBALTO),
        plt.Rectangle((0, 0), 1, 1, color=config.CORAL),
    ]
    eixo.legend(
        marcadores, ["estrutural — o item não existe", "faltante de fato"], loc="lower right"
    )
    salvar_figura(fig, SECAO, "f5-mapa-ausencia", com_nulo[["nulos", "pct_nulos", "natureza"]])

    # Coocorrência: colunas que faltam sempre juntas denunciam ausência estrutural.
    grupo_garagem = [
        "tipo_garagem",
        "acabamento_garagem",
        "qualidade_garagem",
        "conservacao_garagem",
        "ano_garagem",
    ]
    grupo_porao = [
        "qualidade_porao",
        "conservacao_porao",
        "exposicao_porao",
        "acabamento_porao_1",
        "acabamento_porao_2",
    ]
    coocorrencia = q.matriz_ausencia(bruto, grupo_garagem + grupo_porao + ["testada_lote"])
    fig, eixo = plt.subplots(figsize=(9, 7), constrained_layout=True)
    sns.heatmap(
        coocorrencia,
        annot=True,
        fmt="d",
        cmap="Reds",
        ax=eixo,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "registros ausentes em ambas"},
    )
    eixo.set_title("5ª fase — Coocorrência de ausência")
    salvar_figura(fig, SECAO, "f5-coocorrencia-ausencia", coocorrencia)

    sentinelas = inventario_sentinelas()
    salvar_tabela(sentinelas, SECAO, "f5-inventario-sentinelas")

    _registrar(
        "5ª — Valores ausentes",
        "As cinco colunas de garagem faltam nos mesmos 157 a 159 imóveis, e as cinco de "
        "porão nos mesmos 79 a 83. A ausência é blocada, não aleatória.",
        "Ausência estrutural: são imóveis sem garagem e sem porão. Imputar pela moda "
        "criaria garagens inexistentes. O tratamento correto é rótulo próprio e área zero.",
        "f5-coocorrencia-ausencia.png",
    )
    _registrar(
        "5ª — Valores ausentes",
        "A palavra `None` em `Mas Vnr Type` é categoria legítima ('sem revestimento em "
        "alvenaria aparente'), mas a leitura padrão do pandas a converte em nulo.",
        "Sem declarar `na_values=['NA','']` na leitura, a coluna aparenta 60,6% de "
        "ausência quando a ausência real é de 0,8% — 23 registros.",
        "f5-inventario-sentinelas.csv",
    )
    _registrar(
        "5ª — Valores ausentes",
        "`Lot Frontage` tem 16,7% de ausência e é a única ausência numérica relevante "
        "que não é estrutural.",
        "Ausência do tipo MAR, ligada à geometria do lote (esquina e fundo não têm "
        "testada registrada). Imputação pela mediana do bairro preserva a variação local.",
        "f5-mapa-ausencia.png",
    )
    return com_nulo


# --------------------------------------------------------------------------- #
# 6ª fase — Valores discrepantes
# --------------------------------------------------------------------------- #


def fase_6_discrepantes(curada: pd.DataFrame) -> pd.DataFrame:
    """Detecta discrepantes por três métodos e confronta os resultados."""
    espaco = dic.NUMERICAS
    contagens = []
    for coluna in espaco:
        serie = curada[coluna]
        contagens.append(
            {
                "variavel": dic.rotulo(coluna),
                "IQR (Tukey 1,5)": int(est.outliers_iqr(serie).sum()),
                "z robusto (MAD > 3)": int(est.outliers_zscore(serie).sum()),
            }
        )
    tabela = pd.DataFrame(contagens).set_index("variavel")

    matriz = curada[espaco].copy()
    for coluna in dic.ASSIMETRICAS:
        matriz[coluna] = np.log1p(matriz[coluna])
    multivariado = est.outliers_isolation(
        pd.DataFrame(StandardScaler().fit_transform(matriz), columns=espaco), contaminacao=0.05
    )
    # O Isolation Forest devolve **um** veredicto por registro, olhando todas as
    # variáveis de uma vez. Não existe "contagem por variável" para ele, e
    # repetir o total em cada linha da tabela seria enganoso.
    salvar_tabela(
        pd.DataFrame(
            [
                {
                    "metodo": "Isolation Forest (multivariado)",
                    "registros_sinalizados": int(multivariado.sum()),
                    "pct": round(100 * float(multivariado.mean()), 2),
                    "observacao": "olha a combinação de atributos, não uma variável por vez",
                }
            ]
        ),
        SECAO,
        "f6-discrepantes-multivariados",
        indice=False,
    )

    fig, eixos = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    tabela[["IQR (Tukey 1,5)", "z robusto (MAD > 3)"]].plot.barh(
        ax=eixos[0], color=[config.AZUL_COBALTO, config.CORAL], width=0.8
    )
    eixos[0].set_xlabel("registros sinalizados")
    eixos[0].set_title("Discrepantes univariados por variável")
    eixos[0].legend(loc="lower right")

    eixos[1].scatter(
        curada.loc[~multivariado.to_numpy(), "area_habitavel"],
        curada.loc[~multivariado.to_numpy(), "qualidade_geral"],
        s=10,
        alpha=0.3,
        color=config.AZUL_CLARO,
        label="típico",
        edgecolors="none",
    )
    eixos[1].scatter(
        curada.loc[multivariado.to_numpy(), "area_habitavel"],
        curada.loc[multivariado.to_numpy(), "qualidade_geral"],
        s=22,
        alpha=0.85,
        color=config.CORAL,
        label="atípico (Isolation Forest)",
        edgecolors="white",
        linewidths=0.3,
    )
    eixos[1].set_xlabel(dic.rotulo("area_habitavel"))
    eixos[1].set_ylabel(dic.rotulo("qualidade_geral"))
    eixos[1].set_title(f"Atípicos multivariados: {int(multivariado.sum())} imóveis (5%)")
    eixos[1].legend()
    fig.suptitle(
        "6ª fase — Valores discrepantes por três métodos",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f6-discrepantes", tabela)

    # Perfil de quem foi marcado como atípico — é isso que decide o tratamento.
    perfil_atipicos = pd.DataFrame(
        {
            "típicos": curada.loc[~multivariado.to_numpy(), espaco].median(),
            "atípicos": curada.loc[multivariado.to_numpy(), espaco].median(),
        }
    )
    perfil_atipicos["razão"] = (
        perfil_atipicos["atípicos"] / perfil_atipicos["típicos"].replace(0, np.nan)
    ).round(2)
    salvar_tabela(perfil_atipicos.round(2), SECAO, "f6-perfil-atipicos")

    _registrar(
        "6ª — Valores discrepantes",
        f"`area_terreno` tem {tabela.loc[dic.rotulo('area_terreno'), 'IQR (Tukey 1,5)']} "
        "discrepantes por Tukey, mas são lotes grandes legítimos, não erro de digitação.",
        "Discrepante legítimo não se remove: se remove o lote grande, some justamente o "
        "segmento de alto padrão que a diretoria quer enxergar. A resposta é `log1p`, "
        "não exclusão.",
        "f6-discrepantes.png / f6-perfil-atipicos.csv",
    )
    _registrar(
        "6ª — Valores discrepantes",
        "Os 5 imóveis acima de 4.000 pés² já haviam sido removidos por recomendação "
        "explícita do autor da base (De Cock, 2011, §4): são vendas parciais atípicas.",
        "Remoção citável, e não arbitrária — a diferença entre uma decisão defensável "
        "em banca e um corte de conveniência.",
        "docs/preparacao.md",
    )
    _registrar(
        "6ª — Valores discrepantes",
        "O Isolation Forest marca 5% dos imóveis como atípicos pela combinação de "
        "atributos, e o perfil deles é sistematicamente diferente do típico.",
        "Esses imóveis são candidatos naturais a virar ruído no DBSCAN. Se virarem, "
        "o ruído é produto — uma lista de imóveis fora de padrão para avaliação "
        "individual — e não resíduo a descartar.",
        "f6-discrepantes.png",
    )
    return tabela


# --------------------------------------------------------------------------- #
# 7ª fase — Detecção de correlação
# --------------------------------------------------------------------------- #


def fase_7_correlacao(curada: pd.DataFrame) -> pd.DataFrame:
    """Correlação linear e monotônica entre as variáveis do espaço de atributos."""
    espaco = dic.NUMERICAS + dic.ORDINAIS
    pearson = curada[espaco].corr(method="pearson")
    spearman = curada[espaco].corr(method="spearman")

    fig, eixos = plt.subplots(1, 2, figsize=(17, 7), constrained_layout=True)
    for eixo, matriz, titulo in zip(
        eixos, [pearson, spearman], ["Pearson (linear)", "Spearman (monotônica)"], strict=True
    ):
        mascara = np.triu(np.ones_like(matriz, dtype=bool), k=1)
        sns.heatmap(
            matriz,
            mask=mascara,
            cmap="RdBu_r",
            center=0,
            vmin=-1,
            vmax=1,
            annot=True,
            fmt=".2f",
            annot_kws={"size": 6},
            ax=eixo,
            linewidths=0.4,
            linecolor="white",
            cbar_kws={"shrink": 0.7},
        )
        eixo.set_xticklabels([dic.rotulo(c) for c in espaco], rotation=45, ha="right", fontsize=8)
        eixo.set_yticklabels([dic.rotulo(c) for c in espaco], rotation=0, fontsize=8)
        eixo.set_title(titulo)
    fig.suptitle(
        "7ª fase — Detecção de correlação",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f7-correlacao", pearson.round(3))
    salvar_tabela(spearman.round(3), SECAO, "f7-correlacao-spearman")

    redundantes = est.pares_redundantes(spearman, limiar=0.7)
    redundantes["variavel_a"] = redundantes["variavel_a"].map(dic.rotulo)
    redundantes["variavel_b"] = redundantes["variavel_b"].map(dic.rotulo)
    salvar_tabela(redundantes, SECAO, "f7-pares-redundantes", indice=False)

    if len(redundantes):
        fig, eixo = plt.subplots(
            figsize=(9, max(2.5, 0.45 * len(redundantes))), constrained_layout=True
        )
        rotulos = redundantes["variavel_a"] + "  ×  " + redundantes["variavel_b"]
        eixo.barh(rotulos[::-1], redundantes["correlacao"].abs()[::-1], color=config.CORAL)
        eixo.axvline(0.7, ls="--", color=config.CINZA)
        eixo.set_xlim(0, 1)
        eixo.set_xlabel("|ρ de Spearman|")
        eixo.set_title("7ª fase — Pares com correlação absoluta ≥ 0,70")
        salvar_figura(fig, SECAO, "f7-pares-redundantes", redundantes)

    _registrar(
        "7ª — Correlação",
        f"{len(redundantes)} pares ultrapassam |ρ| = 0,70. O mais forte é "
        f"{redundantes.iloc[0]['variavel_a']} × {redundantes.iloc[0]['variavel_b']} "
        f"(ρ = {redundantes.iloc[0]['correlacao']:.2f}).",
        "Variável redundante entra duas vezes na distância e pesa dobrado sem que "
        "ninguém tenha decidido isso. A 8ª fase resolve par a par.",
        "f7-correlacao.png / f7-pares-redundantes.csv",
    )
    _registrar(
        "7ª — Correlação",
        "Pearson e Spearman divergem nas variáveis de área — sinal de relação "
        "monotônica, porém não linear, causada pela cauda longa.",
        "Confirma a necessidade do `log1p`: depois da transformação, as duas medidas "
        "convergem e a distância euclidiana passa a fazer sentido geométrico.",
        "f7-correlacao.png",
    )
    return redundantes


# --------------------------------------------------------------------------- #
# 8ª fase — Seleção de características
# --------------------------------------------------------------------------- #


def fase_8_selecao(curada: pd.DataFrame, redundantes: pd.DataFrame) -> pd.DataFrame:
    """Decide, com registro, o que entra e o que sai do espaço de atributos."""
    decisoes = [
        {
            "variavel": "preco_venda",
            "decisao": "reservada",
            "motivo": "Rótulo. Uso exclusivo na avaliação a posteriori (critério eliminatório).",
        },
        {
            "variavel": "bairro",
            "decisao": "reservada",
            "motivo": "Proxy de preço e 28 categorias. Vira régua de validação externa.",
        },
        {
            "variavel": "infraestrutura, tipo_via, area_piscina",
            "decisao": "descartada",
            "motivo": "Concentração acima de 99,5% em um único valor: variância desprezível.",
        },
        {
            "variavel": "comodos",
            "decisao": "mantida",
            "motivo": (
                "Correlacionada com área habitável, mas mede configuração, não tamanho: "
                "dois imóveis de mesma área com 5 e 9 cômodos são produtos diferentes."
            ),
        },
        {
            "variavel": "area_terreo, area_pavimento_superior",
            "decisao": "descartada",
            "motivo": "A soma das duas é a própria área habitável — redundância exata.",
        },
        {
            "variavel": "5 colunas de varanda",
            "decisao": "consolidada",
            "motivo": (
                "Separadas, cada uma é quase toda zero. Somadas em `area_varandas`, "
                "viram um atributo com variância útil."
            ),
        },
        {
            "variavel": "banheiros (4 colunas)",
            "decisao": "consolidada",
            "motivo": "Consolidadas em `banheiros_total`, com lavabo valendo meio banheiro.",
        },
        {
            "variavel": "conservacao_geral",
            "decisao": "mantida sob observação",
            "motivo": (
                "Baixo poder de separação (concentrada no nível 5), mas é a única "
                "variável de estado de conservação — informação de negócio insubstituível."
            ),
        },
        {
            "variavel": "qualidade_aquecimento, conservacao_externa, funcionalidade",
            "decisao": "descartada",
            "motivo": "Correlacionadas com qualidade geral e sem leitura de negócio própria.",
        },
        {
            "variavel": "mes_venda, ano_venda, tipo_venda, condicao_venda",
            "decisao": "reservada",
            "motivo": (
                "Descrevem a transação, não o produto. Usadas na análise temporal e no drift."
            ),
        },
    ]
    tabela = pd.DataFrame(decisoes)
    salvar_tabela(tabela, SECAO, "f8-decisoes-selecao", indice=False)

    espaco_final = dic.ESPACO_MISTO
    composicao = pd.Series(
        {
            "Numéricas": len(dic.NUMERICAS),
            "Ordinais": len(dic.ORDINAIS),
            "Nominais": len(dic.NOMINAIS),
            "Binárias derivadas": len(dic.BINARIAS),
        }
    )

    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.5), constrained_layout=True)
    eixos[0].bar(
        composicao.index,
        composicao.to_numpy(),
        color=[config.AZUL_PROFUNDO, config.VERDE, config.ROXO, config.AMARELO],
    )
    eixos[0].bar_label(eixos[0].containers[0], padding=3)
    eixos[0].set_ylabel("nº de variáveis")
    eixos[0].set_title(f"Espaço de atributos final: {len(espaco_final)} variáveis (+4 binárias)")
    eixos[0].tick_params(axis="x", rotation=15)

    contagem_decisoes = tabela["decisao"].value_counts()
    eixos[1].barh(
        contagem_decisoes.index[::-1], contagem_decisoes.to_numpy()[::-1], color=config.AZUL_COBALTO
    )
    eixos[1].bar_label(eixos[1].containers[0], padding=3)
    eixos[1].set_xlabel("nº de decisões registradas")
    eixos[1].set_title("Decisões de seleção documentadas")
    fig.suptitle(
        "8ª fase — Seleção de características",
        fontsize=14,
        fontweight="bold",
        color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "f8-selecao-caracteristicas", composicao.to_frame("variaveis"))

    _registrar(
        "8ª — Seleção de características",
        f"Das 82 colunas da origem, {len(espaco_final)} entram no espaço de atributos "
        f"(+{len(dic.BINARIAS)} binárias derivadas); 2 ficam reservadas e o restante sai.",
        "Espaço enxuto o bastante para o dendrograma ser legível e rico o bastante para "
        "sustentar uma persona. Cada exclusão tem motivo registrado.",
        "f8-decisoes-selecao.csv",
    )
    _registrar(
        "8ª — Seleção de características",
        "A redundância entre área habitável e cômodos foi mantida deliberadamente.",
        "Remover tudo o que se correlaciona empobrece a leitura de negócio: dois imóveis "
        "de mesma área com número diferente de cômodos são produtos diferentes. "
        "Redundância estatística não é sinônimo de redundância de negócio.",
        "f7-pares-redundantes.csv",
    )
    return tabela


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #


def executar() -> pd.DataFrame:
    """Executa as oito fases na ordem e grava a coleção de insights."""
    configurar_estilo()
    INSIGHTS.clear()

    bruto = carregar_bruto()
    curada = carregar_curada()

    fase_1_distribuicao_atributos(bruto, curada)
    fase_2_univariada(curada)
    fase_3_bivariada(curada)
    fase_4_multivariada(curada)
    fase_5_ausentes(bruto)
    fase_6_discrepantes(curada)
    redundantes = fase_7_correlacao(curada)
    fase_8_selecao(curada, redundantes)

    colecao = pd.DataFrame(INSIGHTS)
    colecao.index = [f"I{i + 1:02d}" for i in range(len(colecao))]
    colecao.index.name = "id"
    salvar_tabela(colecao, SECAO, "colecao-de-insights")
    return colecao


if __name__ == "__main__":
    insights = executar()
    print(f"8 fases executadas. {len(insights)} insights registrados.")
    print(f"Figuras em {config.FIGURES / SECAO}")
