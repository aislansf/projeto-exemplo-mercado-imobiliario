"""Modelos de mistura gaussiana (GMM).

O que o GMM traz e o K-Means não tem: **grau de pertencimento**. Um imóvel com
0,52 de probabilidade no segmento A e 0,46 no B não é um imóvel do segmento A —
é um imóvel de fronteira, e tratá-lo como se fosse do A é a origem de boa parte
das ações de marketing que não funcionam.

A seleção de *k* usa BIC e AIC, e não a silhueta: como o GMM é um modelo
probabilístico, existe verossimilhança, e critérios de informação penalizam a
complexidade de forma explícita.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from src import config
from src.model.particional import metricas_internas

COVARIANCIAS = ("full", "tied", "diag", "spherical")


def varrer_gmm(
    dados: np.ndarray,
    k_minimo: int = 2,
    k_maximo: int = 10,
    covariancias: tuple[str, ...] = COVARIANCIAS,
    semente: int = config.SEMENTE,
) -> pd.DataFrame:
    """Ajusta o GMM para cada combinação de *k* e tipo de covariância."""
    linhas = []
    for tipo in covariancias:
        for k in range(k_minimo, k_maximo + 1):
            modelo = GaussianMixture(
                n_components=k,
                covariance_type=tipo,
                random_state=semente,
                n_init=5,
                max_iter=500,
            ).fit(dados)
            rotulos = modelo.predict(dados)
            probabilidades = modelo.predict_proba(dados)
            metricas = metricas_internas(dados, rotulos)
            linhas.append(
                {
                    "covariancia": tipo,
                    "k": k,
                    "bic": round(float(modelo.bic(dados)), 1),
                    "aic": round(float(modelo.aic(dados)), 1),
                    "log_verossimilhanca": round(float(modelo.score(dados) * len(dados)), 1),
                    "convergiu": bool(modelo.converged_),
                    "silhueta": round(metricas["silhueta"], 4),
                    "pct_fronteira": round(float((probabilidades.max(axis=1) < 0.60).mean()), 4),
                }
            )
    return pd.DataFrame(linhas)


def ajustar_gmm(
    dados: np.ndarray, k: int, covariancia: str = "full", semente: int = config.SEMENTE
) -> tuple[GaussianMixture, np.ndarray, np.ndarray]:
    """Ajusta o GMM final e devolve o modelo, os rótulos e as probabilidades."""
    modelo = GaussianMixture(
        n_components=k, covariance_type=covariancia, random_state=semente, n_init=10, max_iter=500
    ).fit(dados)
    return modelo, modelo.predict(dados), modelo.predict_proba(dados)


def classificar_confianca(
    probabilidades: np.ndarray, limiar_alto: float = 0.80, limiar_baixo: float = 0.60
) -> pd.Series:
    """Traduz o grau de pertencimento em três faixas de leitura para o negócio.

    * **núcleo** — pertence claramente a um segmento; a ação padrão se aplica;
    * **típico** — pertence, com alguma sobreposição;
    * **fronteira** — o algoritmo não decidiu, e a ação automática não deveria
      ser disparada sem revisão humana.
    """
    maxima = probabilidades.max(axis=1)
    faixas = np.where(
        maxima >= limiar_alto, "núcleo", np.where(maxima >= limiar_baixo, "típico", "fronteira")
    )
    return pd.Series(faixas, name="confianca")
