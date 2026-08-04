"""Medidas de distância e dissimilaridade.

O `scikit-learn` cobre euclidiana, Manhattan e cosseno, mas não traz a
dissimilaridade de **Gower**, que é a medida natural para dados mistos — e a
base deste projeto tem 17 variáveis numéricas ou ordinais convivendo com 5
nominais. A implementação abaixo é própria, e é parte do material didático: a
fórmula cabe em quinze linhas e entendê-la é mais útil do que instalar um
pacote.

Gower, J. C. (1971). *A General Coefficient of Similarity and Some of Its
Properties.* Biometrics, 27(4), 857–871.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform


def gower(
    dados: pd.DataFrame,
    numericas: list[str],
    nominais: list[str],
    pesos: dict[str, float] | None = None,
) -> np.ndarray:
    """Matriz de dissimilaridade de Gower para dados mistos.

    Para cada par de registros *i* e *j*, a dissimilaridade é a média ponderada
    das contribuições de cada variável:

    * **numérica ou ordinal** — ``|x_i − x_j| / amplitude_da_variável``, o que
      leva toda variável ao intervalo [0, 1] sem exigir padronização prévia;
    * **nominal** — 0 quando as categorias coincidem, 1 quando diferem.

    Args:
        dados: registros a comparar.
        numericas: colunas tratadas pela diferença normalizada (inclui ordinais).
        nominais: colunas tratadas por igualdade.
        pesos: peso por coluna; o padrão é 1 para todas.

    Returns:
        Matriz ``n × n`` simétrica, com zeros na diagonal, no intervalo [0, 1].

    Note:
        O custo é quadrático em memória: 2.925 registros ocupam cerca de 34 MB
        em ``float32``. Acima de ~10.000 registros, amostre.
    """
    pesos = pesos or {}
    n = len(dados)
    acumulado = np.zeros((n, n), dtype=np.float32)
    peso_total = 0.0

    for coluna in numericas:
        valores = dados[coluna].to_numpy(dtype=np.float32)
        amplitude = float(valores.max() - valores.min())
        if amplitude == 0:
            # Variável constante não separa nada e dividiria por zero.
            continue
        peso = float(pesos.get(coluna, 1.0))
        acumulado += peso * np.abs(valores[:, None] - valores[None, :]) / amplitude
        peso_total += peso

    for coluna in nominais:
        codigos = pd.factorize(dados[coluna])[0].astype(np.int32)
        peso = float(pesos.get(coluna, 1.0))
        acumulado += peso * (codigos[:, None] != codigos[None, :]).astype(np.float32)
        peso_total += peso

    if peso_total == 0:
        raise ValueError("Nenhuma variável com variância foi informada.")

    matriz = acumulado / peso_total
    np.fill_diagonal(matriz, 0.0)
    return matriz


def matriz_distancia(dados: np.ndarray, metrica: str = "euclidean") -> np.ndarray:
    """Matriz condensada expandida para as métricas suportadas pelo SciPy."""
    return squareform(pdist(dados, metric=metrica))


def comparar_metricas(dados: np.ndarray, metricas: tuple[str, ...]) -> pd.DataFrame:
    """Resume como cada métrica distribui as distâncias entre pares.

    Serve para tornar visível o que costuma ficar implícito: métricas diferentes
    não são reescalas uma da outra — elas mudam quem é vizinho de quem.
    """
    linhas = []
    for metrica in metricas:
        distancias = pdist(dados, metric=metrica)
        linhas.append(
            {
                "metrica": metrica,
                "media": float(np.mean(distancias)),
                "mediana": float(np.median(distancias)),
                "desvio": float(np.std(distancias)),
                "minimo": float(np.min(distancias)),
                "maximo": float(np.max(distancias)),
                "razao_max_min": float(np.max(distancias) / max(np.min(distancias), 1e-12)),
            }
        )
    return pd.DataFrame(linhas).set_index("metrica").round(4)
