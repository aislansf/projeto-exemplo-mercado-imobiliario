"""Clusterização hierárquica aglomerativa.

Com 2.925 imóveis o dendrograma completo é ilegível, mas o dendrograma
**truncado** nos últimos níveis é exatamente o que interessa: são as fusões
finais que definem os grupos candidatos, e a altura delas é o argumento para o
corte.

Quatro critérios de ligação são comparados. Não é preciosismo: `single` produz
o efeito de encadeamento (um grupo gigante que engole tudo), `complete` favorece
grupos compactos de tamanho parecido, `average` fica no meio e `ward` minimiza a
variância interna — e, por isso, é o único que se comporta como o K-Means.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, dendrogram, fcluster, linkage
from scipy.spatial.distance import squareform

LIGACOES = ("ward", "complete", "average", "single")


def matriz_ligacao(
    dados: np.ndarray | None = None,
    ligacao: str = "ward",
    distancias: np.ndarray | None = None,
) -> np.ndarray:
    """Constrói a matriz de ligação a partir dos dados ou de uma dissimilaridade.

    Args:
        dados: matriz de atributos; usada quando ``distancias`` é ``None``.
        ligacao: um dos critérios em :data:`LIGACOES`.
        distancias: matriz ``n × n`` (por exemplo, de Gower).

    Raises:
        ValueError: quando se pede ``ward`` sobre uma matriz de dissimilaridade
            que não é euclidiana — o critério de Ward pressupõe variância em
            espaço euclidiano, e aplicá-lo a Gower produz altura sem significado.
    """
    if distancias is not None:
        if ligacao == "ward":
            raise ValueError(
                "O critério de Ward pressupõe espaço euclidiano. Sobre uma matriz "
                "de Gower, use 'average' ou 'complete'."
            )
        condensada = squareform(distancias, checks=False)
        return linkage(condensada, method=ligacao)
    if dados is None:
        raise ValueError("Informe `dados` ou `distancias`.")
    return linkage(dados, method=ligacao)


def coeficiente_cofenetico(ligacao_matriz: np.ndarray, distancias_condensadas: np.ndarray) -> float:
    """Correlação cofenética: quanto o dendrograma preserva as distâncias originais.

    Acima de 0,75 costuma indicar que a hierarquia representa bem os dados.
    É a métrica que permite comparar critérios de ligação sem apelar ao gosto.
    """
    return float(cophenet(ligacao_matriz, distancias_condensadas)[0])


def comparar_ligacoes(
    dados: np.ndarray, distancias_condensadas: np.ndarray, k: int
) -> pd.DataFrame:
    """Compara os quatro critérios de ligação pelo cofenético e pelo equilíbrio dos grupos."""
    linhas = []
    for ligacao in LIGACOES:
        matriz = linkage(dados, method=ligacao)
        rotulos = fcluster(matriz, t=k, criterion="maxclust")
        tamanhos = np.bincount(rotulos)[1:]
        linhas.append(
            {
                "ligacao": ligacao,
                "cofenetico": round(coeficiente_cofenetico(matriz, distancias_condensadas), 4),
                "grupos_obtidos": int(len(tamanhos)),
                "menor_grupo": int(tamanhos.min()),
                "maior_grupo": int(tamanhos.max()),
                "razao_maior_menor": round(float(tamanhos.max() / max(tamanhos.min(), 1)), 1),
                "altura_ultima_fusao": round(float(matriz[-1, 2]), 3),
                "salto_relativo_ultima": round(
                    float(matriz[-1, 2] / matriz[-2, 2]) if matriz[-2, 2] > 0 else np.nan, 3
                ),
            }
        )
    return pd.DataFrame(linhas).set_index("ligacao")


def alturas_de_fusao(ligacao_matriz: np.ndarray, ultimas: int = 15) -> pd.DataFrame:
    """Altura das últimas fusões e o salto entre elas.

    O corte se justifica onde há **salto grande**: fundir dois grupos que estavam
    muito distantes é o sinal de que já se passou do ponto.
    """
    alturas = ligacao_matriz[-ultimas:, 2]
    grupos = np.arange(ultimas, 0, -1)
    saltos = np.append(np.diff(alturas), np.nan)
    return pd.DataFrame(
        {
            "grupos_apos_fusao": grupos,
            "altura": alturas.round(3),
            "salto_para_proxima": saltos.round(3),
        }
    ).set_index("grupos_apos_fusao")


def cortar(ligacao_matriz: np.ndarray, k: int) -> np.ndarray:
    """Corta o dendrograma em *k* grupos e devolve rótulos começando em zero."""
    return fcluster(ligacao_matriz, t=k, criterion="maxclust") - 1


def desenhar_dendrograma(eixo, ligacao_matriz: np.ndarray, k: int, titulo: str, cor_corte: str):
    """Desenha o dendrograma truncado com a linha de corte no *k* escolhido."""
    # Altura do corte: entre a fusão que produz k grupos e a que produz k−1.
    altura_corte = (ligacao_matriz[-k, 2] + ligacao_matriz[-(k - 1), 2]) / 2
    dendrogram(
        ligacao_matriz,
        truncate_mode="lastp",
        p=25,
        ax=eixo,
        color_threshold=altura_corte,
        above_threshold_color="#8A9BA8",
        leaf_rotation=90,
        leaf_font_size=7,
    )
    eixo.axhline(altura_corte, ls="--", lw=1.4, color=cor_corte)
    eixo.text(
        0.99, altura_corte, f" corte em k={k}", transform=eixo.get_yaxis_transform(),
        ha="right", va="bottom", color=cor_corte, fontsize=9, fontweight="bold",
    )
    eixo.set_title(titulo, fontsize=11)
    eixo.set_xlabel("grupos (dendrograma truncado nas 25 últimas fusões)")
    eixo.set_ylabel("altura da fusão")
    return altura_corte
