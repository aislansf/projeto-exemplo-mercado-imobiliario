"""Redução de dimensionalidade: PCA, Kernel PCA e LDA.

A distinção que a disciplina trata como eliminatória:

* **PCA** e **Kernel PCA** são **não supervisionados**. Procuram as direções de
  maior variância, sem olhar rótulo nenhum. Podem ser usados livremente.
* **LDA** é **supervisionado**. Procura as direções que melhor separam classes
  *conhecidas*. Usá-lo antes de clusterizar seria contrabandear o rótulo para
  dentro do modelo.

Neste projeto o LDA aparece uma única vez, na **avaliação a posteriori**, sobre
a faixa de preço derivada do rótulo reservado — e a comparação com o PCA é
justamente o argumento de que a segmentação não é uma tabela de preço disfarçada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA, KernelPCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

from src import config


def ajustar_pca(dados: np.ndarray, componentes: int | None = None) -> tuple[PCA, np.ndarray]:
    """Ajusta o PCA sobre dados **já padronizados** e devolve modelo e projeção.

    Warning:
        PCA sobre dados não padronizados encontra a variável com maior unidade
        de medida, não a direção de maior informação. A padronização é
        pré-requisito, não refinamento.
    """
    modelo = PCA(n_components=componentes, random_state=config.SEMENTE).fit(dados)
    return modelo, modelo.transform(dados)


def variancia_explicada(modelo: PCA) -> pd.DataFrame:
    """Tabela de variância explicada, acumulada e autovalor por componente."""
    return pd.DataFrame(
        {
            "componente": [f"CP{i + 1}" for i in range(len(modelo.explained_variance_ratio_))],
            "autovalor": modelo.explained_variance_.round(4),
            "variancia_explicada": modelo.explained_variance_ratio_.round(4),
            "acumulada": np.cumsum(modelo.explained_variance_ratio_).round(4),
        }
    ).set_index("componente")


def componentes_para(modelo: PCA, alvo: float = 0.80) -> int:
    """Quantos componentes são necessários para reter a proporção de variância pedida."""
    acumulada = np.cumsum(modelo.explained_variance_ratio_)
    return int(np.searchsorted(acumulada, alvo) + 1)


def cargas(modelo: PCA, nomes: list[str], quantos: int = 3) -> pd.DataFrame:
    """Cargas dos primeiros componentes — é o que dá nome de negócio aos eixos."""
    return pd.DataFrame(
        modelo.components_[:quantos].T,
        index=nomes,
        columns=[f"CP{i + 1}" for i in range(quantos)],
    ).round(3)


def ajustar_kernel_pca(
    dados: np.ndarray, kernel: str = "rbf", componentes: int = 2, gamma: float | None = None
) -> tuple[KernelPCA, np.ndarray]:
    """Ajusta o Kernel PCA, que captura estrutura não linear.

    O preço é a interpretabilidade: não existem cargas, porque a projeção
    acontece em um espaço de dimensão implícita. Serve para visualizar, não
    para explicar.
    """
    modelo = KernelPCA(
        n_components=componentes,
        kernel=kernel,
        gamma=gamma,
        random_state=config.SEMENTE,
        n_jobs=-1,
    ).fit(dados)
    return modelo, modelo.transform(dados)


def comparar_kernels(
    dados: np.ndarray, rotulos: np.ndarray, kernels: tuple[str, ...] = ("linear", "rbf", "cosine")
) -> pd.DataFrame:
    """Compara kernels pela separação que a projeção 2D produz entre os grupos.

    A medida é a silhueta calculada **na projeção**: mede legibilidade do
    gráfico, não qualidade do agrupamento. Confundir as duas coisas é o erro
    que essa tabela existe para evitar.
    """
    from sklearn.metrics import silhouette_score

    linhas = []
    for kernel in kernels:
        _, projecao = ajustar_kernel_pca(dados, kernel=kernel, componentes=2)
        linhas.append(
            {
                "kernel": kernel,
                "silhueta_na_projecao_2d": round(float(silhouette_score(projecao, rotulos)), 4),
            }
        )
    return pd.DataFrame(linhas).set_index("kernel")


def lda_a_posteriori(
    dados: np.ndarray, classes: np.ndarray, componentes: int = 2
) -> tuple[LinearDiscriminantAnalysis, np.ndarray, float]:
    """Projeção supervisionada, usada **apenas** na avaliação.

    Args:
        dados: espaço de atributos usado na modelagem.
        classes: rótulo reservado, discretizado — aqui, a faixa de preço.
        componentes: número de discriminantes.

    Returns:
        Modelo, projeção e a acurácia de reclassificação. A acurácia responde a
        uma pergunta específica: *o espaço de atributos que usei carrega
        informação de preço?* Ela não valida o agrupamento.
    """
    modelo = LinearDiscriminantAnalysis(n_components=componentes).fit(dados, classes)
    return modelo, modelo.transform(dados), float(modelo.score(dados, classes))
