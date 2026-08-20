"""Estabilidade do agrupamento e sensibilidade à escala.

Duas perguntas que a silhueta não responde:

1. **A segmentação sobrevive a uma reamostragem?** Se retirar 20% dos imóveis
   muda a atribuição do restante, os grupos são artefato do conjunto, não
   estrutura do mercado.
2. **A segmentação sobrevive a uma troca de escalonador?** Se o resultado muda
   ao trocar `StandardScaler` por `MinMaxScaler`, quem definiu os segmentos foi
   a escolha do pré-processamento, não os dados.

As duas usam o **índice de Rand ajustado** (ARI): 1,0 é concordância perfeita,
0,0 é o que se espera de duas atribuições aleatórias independentes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score

from src import config
from src.data import preparacao


def estabilidade_bootstrap(
    dados: np.ndarray,
    k: int,
    repeticoes: int = 30,
    fracao: float = 0.80,
    semente: int = config.SEMENTE,
) -> pd.DataFrame:
    """Reamostra sem reposição, reagrupa e compara com a partição de referência.

    Cada repetição sorteia ``fracao`` dos registros, roda o K-Means do zero e
    calcula o ARI contra os rótulos de referência **restritos aos mesmos
    registros**. A média dos ARI é o índice de estabilidade.
    """
    gerador = np.random.default_rng(semente)
    referencia = KMeans(n_clusters=k, n_init=20, random_state=semente).fit_predict(dados)
    tamanho = int(fracao * len(dados))

    resultados = []
    for repeticao in range(repeticoes):
        indices = gerador.choice(len(dados), size=tamanho, replace=False)
        rotulos = KMeans(
            n_clusters=k, n_init=10, random_state=int(gerador.integers(1e6))
        ).fit_predict(dados[indices])
        resultados.append(
            {
                "repeticao": repeticao + 1,
                "ari": round(float(adjusted_rand_score(referencia[indices], rotulos)), 4),
                "ami": round(float(adjusted_mutual_info_score(referencia[indices], rotulos)), 4),
            }
        )
    return pd.DataFrame(resultados).set_index("repeticao")


def estabilidade_por_k(
    dados: np.ndarray, ks: range, repeticoes: int = 20, semente: int = config.SEMENTE
) -> pd.DataFrame:
    """Índice de estabilidade para cada *k* candidato.

    Um *k* com silhueta alta e estabilidade baixa é uma armadilha: parece bom na
    métrica e não se reproduz.
    """
    linhas = []
    for k in ks:
        amostras = estabilidade_bootstrap(dados, k, repeticoes=repeticoes, semente=semente)
        linhas.append(
            {
                "k": k,
                "ari_medio": round(float(amostras["ari"].mean()), 4),
                "ari_desvio": round(float(amostras["ari"].std()), 4),
                "ari_minimo": round(float(amostras["ari"].min()), 4),
            }
        )
    return pd.DataFrame(linhas).set_index("k")


def sensibilidade_escala(
    matriz: pd.DataFrame, k: int, semente: int = config.SEMENTE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara as quatro versões de escala pelo ARI entre as partições resultantes.

    Returns:
        Par ``(resumo, matriz_ari)``. O resumo traz silhueta e tamanho dos
        grupos por escalonador; a matriz traz o ARI entre cada par de
        escalonadores.
    """
    from src.model.particional import metricas_internas

    particoes: dict[str, np.ndarray] = {}
    linhas = []
    for nome in preparacao.ESCALADORES:
        dados, _ = preparacao.preparar_espaco(matriz, escalador=nome)
        rotulos = KMeans(n_clusters=k, n_init=20, random_state=semente).fit_predict(dados)
        particoes[nome] = rotulos
        tamanhos = np.bincount(rotulos)
        metricas = metricas_internas(dados, rotulos)
        linhas.append(
            {
                "escalador": nome,
                "silhueta": round(metricas["silhueta"], 4),
                "davies_bouldin": round(metricas["davies_bouldin"], 4),
                "menor_grupo": int(tamanhos.min()),
                "maior_grupo": int(tamanhos.max()),
                "razao_maior_menor": round(float(tamanhos.max() / tamanhos.min()), 1),
            }
        )

    nomes = list(particoes)
    ari = pd.DataFrame(index=nomes, columns=nomes, dtype=float)
    for primeiro in nomes:
        for segundo in nomes:
            ari.loc[primeiro, segundo] = round(
                float(adjusted_rand_score(particoes[primeiro], particoes[segundo])), 3
            )
    return pd.DataFrame(linhas).set_index("escalador"), ari


def comparar_particoes(particoes: dict[str, np.ndarray]) -> pd.DataFrame:
    """Matriz de ARI entre partições produzidas por algoritmos diferentes."""
    nomes = list(particoes)
    matriz = pd.DataFrame(index=nomes, columns=nomes, dtype=float)
    for primeiro in nomes:
        for segundo in nomes:
            a, b = particoes[primeiro], particoes[segundo]
            validos = (a >= 0) & (b >= 0)
            matriz.loc[primeiro, segundo] = round(
                float(adjusted_rand_score(a[validos], b[validos])), 3
            )
    return matriz


def contingencia(a: np.ndarray, b: np.ndarray, nome_a: str, nome_b: str) -> pd.DataFrame:
    """Tabela de contingência entre duas partições — onde exatamente elas discordam."""
    return pd.crosstab(
        pd.Series(a, name=nome_a), pd.Series(b, name=nome_b), margins=True, margins_name="total"
    )
