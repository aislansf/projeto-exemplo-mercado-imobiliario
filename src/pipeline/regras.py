"""CRISP-DM 4 — Modelagem: regras de associação.

Responde à terceira das quatro perguntas da diretoria: *que padrões de
coocorrência existem nos dados que sustentem ou contradigam a segmentação?*

O percurso é o da disciplina: preparar a base transacional, rodar os três
algoritmos com os mesmos limiares, conferir que produzem os mesmos conjuntos,
gerar as regras, podar o que é trivial e redundante, e então cruzar com os
segmentos para achar o que só vale dentro de cada um.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src import config
from src.model import associacao as assoc
from src.model import personas as pers
from src.utils.io import configurar_estilo, salvar_figura, salvar_tabela

SECAO = "associacao"

#: Suporte mínimo. Com 2.925 imóveis, 10% são 293 imóveis — massa suficiente
#: para sustentar uma política comercial. O efeito de afrouxar esse limiar está
#: medido em `r1-sensibilidade-limiares`: a 5%, o número de regras quadruplica
#: sem que apareça nenhum padrão novo de negócio.
SUPORTE_MINIMO = 0.10
#: Suporte mínimo dentro de um segmento, onde a base é menor.
SUPORTE_MINIMO_SEGMENTO = 0.20
#: Confiança mínima: em 7 de cada 10 imóveis com o antecedente, o consequente
#: aparece.
CONFIANCA_MINIMA = 0.70
#: Lift mínimo. Abaixo de 1,0 a regra é pior que o acaso; entre 1,0 e 1,3 o
#: ganho não justifica uma decisão comercial.
LIFT_MINIMO = 1.30
#: Tamanho máximo do conjunto. Regras com quatro itens no antecedente não são
#: operacionalizáveis por um corretor, e a 4 itens o número de conjuntos salta
#: de 3 mil para 10 mil — quase todos redundantes entre si.
MAX_ITENS = 3


def sensibilidade_limiares(transacoes: pd.DataFrame) -> pd.DataFrame:
    """Mede o efeito do suporte e do tamanho máximo sobre o volume de resultado.

    Calibrar o limiar **é** o exercício: suporte alto devolve só o óbvio,
    suporte baixo explode combinatoriamente. A tabela torna visível onde fica o
    ponto de operação — e é a justificativa da escolha, no lugar do gosto.
    """
    from mlxtend.frequent_patterns import fpgrowth

    linhas = []
    for suporte in (0.03, 0.05, 0.10, 0.15, 0.20, 0.30):
        for tamanho in (2, 3, 4):
            frequentes = fpgrowth(
                transacoes, min_support=suporte, use_colnames=True, max_len=tamanho
            )
            regras = (
                assoc.gerar_regras(frequentes, CONFIANCA_MINIMA, LIFT_MINIMO)
                if len(frequentes) > 1
                else pd.DataFrame()
            )
            linhas.append(
                {
                    "suporte_minimo": suporte,
                    "imoveis_no_suporte": int(round(suporte * len(transacoes))),
                    "max_itens": tamanho,
                    "conjuntos_frequentes": len(frequentes),
                    "regras": len(regras),
                }
            )
    return pd.DataFrame(linhas)


def _figura_comparativo(comparativo: pd.DataFrame) -> None:
    """Tempo e número de conjuntos por algoritmo."""
    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.6), constrained_layout=True)
    eixos[0].barh(comparativo.index, comparativo["tempo_s"], color=config.AZUL_COBALTO)
    eixos[0].bar_label(eixos[0].containers[0], fmt="%.3f s", padding=3, fontsize=9)
    eixos[0].set_xlabel("tempo de execução (s)")
    eixos[0].set_title("Custo de cada algoritmo")

    eixos[1].barh(comparativo.index, comparativo["conjuntos_frequentes"], color=config.VERDE)
    eixos[1].bar_label(eixos[1].containers[0], padding=3, fontsize=9)
    eixos[1].set_xlabel("conjuntos frequentes encontrados")
    eixos[1].set_title("Resultado — idêntico nos três, como deve ser")
    fig.suptitle(
        f"Apriori, Eclat e FP-Growth com os mesmos limiares "
        f"(suporte ≥ {SUPORTE_MINIMO:.0%}, até {MAX_ITENS} itens)",
        fontsize=13, fontweight="bold", color=config.AZUL_PROFUNDO,
    )
    salvar_figura(fig, SECAO, "r1-comparativo-algoritmos", comparativo)


def _figura_dispersao_regras(regras: pd.DataFrame, titulo: str, nome: str) -> None:
    """Suporte × confiança, com o lift na cor — o mapa clássico das regras."""
    fig, eixo = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    dispersao = eixo.scatter(
        regras["support"], regras["confidence"], c=regras["lift"], cmap="viridis",
        s=28 + 60 * (regras["lift"] - regras["lift"].min()), alpha=0.75, edgecolors="white",
        linewidths=0.4,
    )
    fig.colorbar(dispersao, ax=eixo, label="lift")
    eixo.set_xlabel("suporte")
    eixo.set_ylabel("confiança")
    eixo.set_title(titulo)
    salvar_figura(fig, SECAO, nome, regras[["antecedentes", "consequentes", "support",
                                            "confidence", "lift"]].head(200))


def executar() -> dict:
    """Executa a mineração de regras e grava todas as evidências."""
    configurar_estilo()
    config.garantir_diretorios()

    segmentada = pd.read_parquet(config.SEGMENTOS)
    segmentos = segmentada["segmento"].to_numpy()

    # --- Preparação transacional ------------------------------------------- #
    transacoes = assoc.montar_transacoes(segmentada, segmentos)
    transacoes.to_parquet(config.TRANSACOES, index=False)

    inventario = pd.DataFrame(
        {
            "item": transacoes.columns,
            "suporte": transacoes.mean().to_numpy().round(4),
            "imoveis": transacoes.sum().to_numpy(),
        }
    ).sort_values("suporte", ascending=False)
    salvar_tabela(inventario, SECAO, "r0-inventario-de-itens", indice=False)

    origem = pd.DataFrame(
        [
            {"origem": "Nominais (categoria nativa)", "itens": 27,
             "discretizacao": "nenhuma — a categoria já é o item"},
            {"origem": "Ordinais em faixas de mercado", "itens": 9,
             "discretizacao": "cortes em 4 e 7 na escala 1–10 (abaixo, no e acima do padrão)"},
            {"origem": "Numéricas em quartis", "itens": 16,
             "discretizacao": "quartis da própria carteira, relativos ao estoque"},
            {"origem": "Binárias construtivas", "itens": 4,
             "discretizacao": "nenhuma — presença do item"},
            {"origem": "Segmento", "itens": 4,
             "discretizacao": "resultado da clusterização, para o cruzamento"},
        ]
    ).set_index("origem")
    salvar_tabela(origem, SECAO, "r0-origem-dos-itens")

    # --- Calibração dos limiares -------------------------------------------- #
    sem_segmento = transacoes[[c for c in transacoes.columns if not c.startswith("segmento:")]]
    sensibilidade = sensibilidade_limiares(sem_segmento)
    salvar_tabela(sensibilidade, SECAO, "r1-sensibilidade-limiares", indice=False)

    fig, eixo = plt.subplots(figsize=(9.5, 5), constrained_layout=True)
    tamanhos = sorted(sensibilidade["max_itens"].unique())
    for cor, tamanho in zip(config.PALETA, tamanhos, strict=False):
        recorte = sensibilidade[sensibilidade["max_itens"] == tamanho]
        eixo.plot(recorte["suporte_minimo"], recorte["regras"], marker="o", color=cor,
                  label=f"até {tamanho} itens")
    eixo.axvline(SUPORTE_MINIMO, ls="--", color=config.CINZA)
    eixo.annotate("ponto de operação escolhido", xy=(SUPORTE_MINIMO, eixo.get_ylim()[1]),
                  xytext=(6, -14), textcoords="offset points", fontsize=9, color=config.CINZA)
    eixo.set_yscale("symlog")
    eixo.set_xlabel("suporte mínimo")
    eixo.set_ylabel("regras geradas (escala logarítmica)")
    eixo.set_title("Calibração do limiar — suporte alto devolve o óbvio, suporte baixo explode")
    eixo.legend()
    salvar_figura(fig, SECAO, "r1-sensibilidade-limiares", sensibilidade)

    # --- Os três algoritmos ------------------------------------------------ #
    comparativo, frequentes = assoc.comparar_algoritmos(
        sem_segmento, SUPORTE_MINIMO, max_tamanho=MAX_ITENS
    )
    salvar_tabela(comparativo, SECAO, "r1-comparativo-algoritmos")
    _figura_comparativo(comparativo)

    tamanhos = assoc.itens_por_tamanho(frequentes)
    salvar_tabela(tamanhos, SECAO, "r1-conjuntos-por-tamanho")
    for tamanho in (2, 3):
        salvar_tabela(
            assoc.combinacoes_frequentes(frequentes, tamanho, 12),
            SECAO, f"r1-combinacoes-{tamanho}-itens", indice=False,
        )

    # --- Regras e poda ------------------------------------------------------ #
    brutas = assoc.gerar_regras(frequentes, CONFIANCA_MINIMA, LIFT_MINIMO)
    sem_triviais = assoc.remover_regras_triviais(brutas)
    sem_redundantes = assoc.podar_redundantes(sem_triviais)
    podadas, tautologicas = assoc.remover_tautologias(sem_redundantes)

    salvar_tabela(
        assoc.formatar_regras(tautologicas, 12), SECAO, "r2-tautologias-descartadas", indice=False
    )

    funil = pd.DataFrame(
        [
            {"etapa": f"Conjuntos frequentes (suporte ≥ {SUPORTE_MINIMO:.0%})",
             "quantidade": len(frequentes),
             "criterio": "antimonotonicidade: todo subconjunto de um frequente é frequente"},
            {"etapa": f"Regras com confiança ≥ {CONFIANCA_MINIMA:.0%} e lift ≥ {LIFT_MINIMO}",
             "quantidade": len(brutas),
             "criterio": "lift ≤ 1 significa que a regra é pior que o acaso"},
            {"etapa": "Após remover regras entre faixas da mesma variável",
             "quantidade": len(sem_triviais),
             "criterio": "faixas de uma mesma variável não coocorrem: nenhuma sobreviveu"},
            {"etapa": "Após podar redundância por especialização",
             "quantidade": len(sem_redundantes),
             "criterio": "{A,B}→C some quando {A}→C já tem confiança igual ou maior"},
            {"etapa": "Após remover tautologias semânticas", "quantidade": len(podadas),
             "criterio": "relação definicional, não de mercado — nenhuma métrica detecta"},
        ]
    ).set_index("etapa")
    salvar_tabela(funil, SECAO, "r2-funil-de-poda")

    fig, eixo = plt.subplots(figsize=(11, 4.4), constrained_layout=True)
    eixo.barh(funil.index[::-1], funil["quantidade"][::-1], color=config.AZUL_PROFUNDO)
    eixo.set_xscale("log")
    eixo.bar_label(eixo.containers[0], padding=3, fontsize=9)
    eixo.set_xlabel("regras")
    eixo.set_title("Funil de poda — o que sobra depois de descartar o trivial e o redundante")
    eixo.tick_params(axis="y", labelsize=8)
    salvar_figura(fig, SECAO, "r2-funil-de-poda", funil)

    salvar_tabela(assoc.formatar_regras(podadas, 25), SECAO, "r2-principais-regras", indice=False)
    _figura_dispersao_regras(
        podadas,
        f"Regras podadas: suporte × confiança, lift na cor ({len(podadas)} regras)",
        "r2-mapa-das-regras",
    )

    # Evidência de que o filtro de lift importa: o que seria "descoberto" sem ele.
    sem_filtro_lift = assoc.gerar_regras(frequentes, CONFIANCA_MINIMA, lift_minimo=0.0)
    triviais = sem_filtro_lift[sem_filtro_lift["lift"] <= 1.0].nlargest(10, "confidence")
    salvar_tabela(
        assoc.formatar_regras(triviais, 10), SECAO, "r2-regras-triviais-descartadas", indice=False
    )

    # --- Cruzamento com a segmentação --------------------------------------- #
    por_segmento = assoc.regras_por_segmento(
        transacoes, segmentos, SUPORTE_MINIMO_SEGMENTO, CONFIANCA_MINIMA, LIFT_MINIMO, 3
    )
    diferencial = assoc.lift_diferencial(por_segmento, podadas, minimo_diferenca=0.20)
    if not diferencial.empty:
        diferencial["persona"] = diferencial["segmento"].map(
            lambda s: pers.PERSONAS[int(s)]["codigo"]
        )
    # As dez mais fortes **de cada** segmento. Cortar as 40 primeiras da tabela
    # ordenada por segmento devolveria só o primeiro grupo.
    salvar_tabela(
        diferencial.groupby("segmento", group_keys=False).head(10)
        if not diferencial.empty
        else diferencial,
        SECAO, "r3-regras-diferenciais", indice=False,
    )
    salvar_tabela(diferencial, SECAO, "r3-regras-diferenciais-completo", indice=False)

    contagem = (
        por_segmento.groupby("segmento").size().rename("regras").to_frame()
        if not por_segmento.empty
        else pd.DataFrame()
    )
    if not contagem.empty:
        contagem["persona"] = [pers.PERSONAS[int(s)]["codigo"] for s in contagem.index]
        contagem["diferenciais"] = (
            diferencial.groupby("segmento").size() if not diferencial.empty else 0
        )
        contagem = contagem.fillna(0)
        salvar_tabela(contagem, SECAO, "r3-regras-por-segmento")

        fig, eixo = plt.subplots(figsize=(9, 4.4), constrained_layout=True)
        posicoes = np.arange(len(contagem))
        eixo.bar(posicoes - 0.2, contagem["regras"], width=0.4, color=config.AZUL_COBALTO,
                 label="regras válidas no segmento")
        eixo.bar(posicoes + 0.2, contagem["diferenciais"], width=0.4, color=config.CORAL,
                 label="regras que só valem nele")
        eixo.set_xticks(posicoes)
        eixo.set_xticklabels(
            [f"{pers.PERSONAS[int(s)]['codigo']}\n{pers.PERSONAS[int(s)]['nome']}"
             for s in contagem.index], fontsize=8,
        )
        eixo.legend(fontsize=8)
        eixo.set_ylabel("nº de regras")
        eixo.set_title("Regras por segmento — e quantas delas são exclusivas dele")
        salvar_figura(fig, SECAO, "r3-regras-por-segmento", contagem)

    # Regras que apontam para o próprio segmento: a tradução da segmentação em
    # regra legível, que é o que o corretor consegue usar sem abrir um modelo.
    with_seg = assoc.gerar_regras(
        __import__("mlxtend.frequent_patterns", fromlist=["fpgrowth"]).fpgrowth(
            transacoes, min_support=0.03, use_colnames=True, max_len=3
        ),
        confianca_minima=0.55,
        lift_minimo=1.30,
    )
    apontam_segmento = with_seg[
        with_seg["consequents"].apply(lambda s: all(str(i).startswith("segmento:") for i in s))
    ]
    apontam_segmento = assoc.podar_redundantes(apontam_segmento)

    if not apontam_segmento.empty:
        recorte = apontam_segmento.head(15).iloc[::-1]
        fig, eixo = plt.subplots(figsize=(11, max(4, 0.42 * len(recorte))), constrained_layout=True)
        rotulos = [
            f"{a}  →  {c}" for a, c in zip(recorte["antecedentes"], recorte["consequentes"],
                                           strict=True)
        ]
        eixo.barh(rotulos, recorte["lift"], color=config.VERDE)
        eixo.bar_label(eixo.containers[0], fmt="%.2f", padding=3, fontsize=8)
        eixo.axvline(1.0, ls="--", color=config.CINZA)
        eixo.set_xlabel("lift")
        eixo.set_title("Configurações de imóvel que preveem o segmento (regra legível, sem modelo)")
        eixo.tick_params(axis="y", labelsize=7)
        salvar_figura(
            fig, SECAO, "r4-regras-que-explicam-o-segmento",
            assoc.formatar_regras(apontam_segmento, 25),
        )
    else:
        salvar_tabela(
            assoc.formatar_regras(apontam_segmento, 25), SECAO,
            "r4-regras-que-explicam-o-segmento", indice=False,
        )

    # Mapa de calor item × segmento: a leitura mais direta para o pitch.
    itens_relevantes = inventario[
        (inventario["suporte"] > 0.05) & (~inventario["item"].str.startswith("segmento:"))
    ]["item"].head(28)
    presenca = pd.DataFrame(
        {
            pers.PERSONAS[int(s)]["codigo"]: transacoes.loc[segmentos == s, itens_relevantes].mean()
            for s in sorted(np.unique(segmentos))
        }
    )
    diferenca = presenca.sub(transacoes[itens_relevantes].mean(), axis=0)
    fig, eixo = plt.subplots(figsize=(8, 10), constrained_layout=True)
    sns.heatmap(100 * diferenca, cmap="RdBu_r", center=0, annot=True, fmt=".0f", ax=eixo,
                linewidths=0.4, linecolor="white",
                cbar_kws={"label": "pontos percentuais acima/abaixo da carteira"})
    eixo.set_title("Presença de cada item por segmento,\nem diferença para a carteira inteira",
                   fontsize=11)
    eixo.set_ylabel("")
    salvar_figura(fig, SECAO, "r3-itens-por-segmento", (100 * diferenca).round(1))

    return {
        "itens": int(transacoes.shape[1]),
        "conjuntos_frequentes": int(len(frequentes)),
        "regras_podadas": int(len(podadas)),
        "regras_diferenciais": int(len(diferencial)),
    }


if __name__ == "__main__":
    resumo = executar()
    print(
        f"{resumo['itens']} itens · {resumo['conjuntos_frequentes']} conjuntos frequentes · "
        f"{resumo['regras_podadas']} regras após poda · "
        f"{resumo['regras_diferenciais']} diferenciais por segmento"
    )
