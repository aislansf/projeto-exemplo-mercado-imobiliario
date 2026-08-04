"""Clusterização particional: K-Means e K-Medoids, e a escolha de *k*.

O `scikit-learn` não distribui K-Medoids. A implementação aqui é a variante de
**iteração de Voronoi** (Park & Jun, 2009), com inicialização no estilo
k-means++ adaptada a matriz de distâncias e múltiplas reinicializações. Ela
opera sobre qualquer matriz de dissimilaridade — inclusive a de Gower —, que é
justamente o que o K-Means não sabe fazer.

Diferença que importa para o negócio: o centroide do K-Means é um imóvel médio
que **não existe**; o medoide é um imóvel **real da carteira**, com endereço.
Em uma reunião de diretoria, a segunda coisa é muito mais fácil de defender.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)

from src import config

# --------------------------------------------------------------------------- #
# K-Medoids
# --------------------------------------------------------------------------- #


@dataclass
class ResultadoKMedoids:
    """Saída do K-Medoids."""

    rotulos: np.ndarray
    medoides: np.ndarray
    custo: float
    iteracoes: int
    historico_custo: list[float] = field(default_factory=list)


def _inicializar_medoides(
    distancias: np.ndarray, k: int, gerador: np.random.Generator
) -> np.ndarray:
    """Inicialização k-means++ adaptada: cada medoide novo é sorteado longe dos atuais."""
    n = len(distancias)
    medoides = [int(gerador.integers(n))]
    for _ in range(1, k):
        # Distância de cada ponto ao medoide mais próximo já escolhido.
        proximidade = distancias[:, medoides].min(axis=1)
        probabilidade = proximidade**2
        soma = probabilidade.sum()
        if soma <= 0:
            candidatos = [i for i in range(n) if i not in medoides]
            medoides.append(int(gerador.choice(candidatos)))
            continue
        medoides.append(int(gerador.choice(n, p=probabilidade / soma)))
    return np.array(medoides)


def kmedoids(
    distancias: np.ndarray,
    k: int,
    reinicios: int = 10,
    max_iteracoes: int = 300,
    semente: int = config.SEMENTE,
) -> ResultadoKMedoids:
    """Agrupa por K-Medoids sobre uma matriz de dissimilaridade pré-calculada.

    Args:
        distancias: matriz ``n × n`` simétrica.
        k: número de grupos.
        reinicios: quantas inicializações independentes; fica a de menor custo.
        max_iteracoes: teto de iterações por reinício.
        semente: semente do gerador, para reprodutibilidade.

    Returns:
        :class:`ResultadoKMedoids` com rótulos, índices dos medoides e custo
        (soma das distâncias de cada ponto ao seu medoide).
    """
    gerador = np.random.default_rng(semente)
    melhor: ResultadoKMedoids | None = None

    for _ in range(reinicios):
        medoides = _inicializar_medoides(distancias, k, gerador)
        historico: list[float] = []
        rotulos = np.zeros(len(distancias), dtype=int)

        for iteracao in range(max_iteracoes):
            rotulos = np.argmin(distancias[:, medoides], axis=1)
            custo = float(distancias[np.arange(len(distancias)), medoides[rotulos]].sum())
            historico.append(custo)

            novos = medoides.copy()
            for grupo in range(k):
                indices = np.flatnonzero(rotulos == grupo)
                if len(indices) == 0:
                    continue
                # O medoide é o ponto do grupo com menor soma de distâncias
                # aos demais pontos do mesmo grupo.
                interno = distancias[np.ix_(indices, indices)].sum(axis=1)
                novos[grupo] = indices[int(np.argmin(interno))]

            if np.array_equal(np.sort(novos), np.sort(medoides)):
                medoides = novos
                break
            medoides = novos

        rotulos = np.argmin(distancias[:, medoides], axis=1)
        custo = float(distancias[np.arange(len(distancias)), medoides[rotulos]].sum())
        resultado = ResultadoKMedoids(rotulos, medoides, custo, iteracao + 1, historico)
        if melhor is None or resultado.custo < melhor.custo:
            melhor = resultado

    assert melhor is not None
    return melhor


# --------------------------------------------------------------------------- #
# Métricas de validação interna
# --------------------------------------------------------------------------- #


def metricas_internas(
    dados: np.ndarray | None, rotulos: np.ndarray, distancias: np.ndarray | None = None
) -> dict[str, float]:
    """Calcula silhueta, Davies-Bouldin e Calinski-Harabasz.

    Args:
        dados: matriz de atributos. Pode ser ``None`` quando só há matriz de
            dissimilaridade — é o caso do Gower, em que não existe espaço
            vetorial subjacente.
        rotulos: atribuição de grupo por registro.
        distancias: matriz de dissimilaridade; quando informada, a silhueta é
            calculada com ``metric='precomputed'``.

    Returns:
        Dicionário com as três métricas. Silhueta e Calinski-Harabasz: maior é
        melhor. Davies-Bouldin: menor é melhor.

    Note:
        Davies-Bouldin e Calinski-Harabasz são definidos a partir de centroides
        e, por isso, **não existem** sobre uma dissimilaridade sem coordenadas.
        Nesses casos voltam como ``NaN``, em vez de um número inventado.
    """
    vazio = {"silhueta": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan}
    if len(np.unique(rotulos[rotulos >= 0])) < 2:
        return vazio

    if distancias is not None:
        silhueta = float(
            silhouette_score(np.asarray(distancias, dtype=float), rotulos, metric="precomputed")
        )
    else:
        silhueta = float(silhouette_score(dados, rotulos))

    if dados is None:
        return {**vazio, "silhueta": silhueta}

    return {
        "silhueta": silhueta,
        "davies_bouldin": float(davies_bouldin_score(dados, rotulos)),
        "calinski_harabasz": float(calinski_harabasz_score(dados, rotulos)),
    }


def varrer_k(
    dados: np.ndarray,
    k_minimo: int = 2,
    k_maximo: int = 10,
    semente: int = config.SEMENTE,
) -> pd.DataFrame:
    """Roda o K-Means para cada *k* e devolve as quatro métricas de escolha.

    A inércia sustenta o método do cotovelo; as demais são índices de validação
    interna. Nenhuma delas conhece a restrição de negócio — o confronto entre a
    métrica e o teto de cinco grupos é feito depois, e é a parte que importa.
    """
    linhas = []
    for k in range(k_minimo, k_maximo + 1):
        modelo = KMeans(n_clusters=k, init="k-means++", n_init=20, random_state=semente)
        rotulos = modelo.fit_predict(dados)
        metricas = metricas_internas(dados, rotulos)
        linhas.append(
            {
                "k": k,
                "inercia": float(modelo.inertia_),
                **metricas,
                "menor_grupo": int(np.bincount(rotulos).min()),
                "maior_grupo": int(np.bincount(rotulos).max()),
            }
        )
    return pd.DataFrame(linhas).set_index("k")


def cotovelo(inercias: pd.Series) -> int:
    """Encontra o joelho da curva pelo método da maior distância à corda.

    Liga o primeiro ao último ponto da curva por uma reta e devolve o *k* cujo
    ponto está mais distante dessa reta. É o mesmo critério que se usa a olho,
    escrito de forma reprodutível — e, por isso, defensável em banca.
    """
    x = inercias.index.to_numpy(dtype=float)
    y = inercias.to_numpy(dtype=float)
    x_norm = (x - x.min()) / (x.max() - x.min())
    y_norm = (y - y.min()) / (y.max() - y.min())
    # Distância de cada ponto à reta que liga (0,1) a (1,0) da curva normalizada.
    inicio = np.array([x_norm[0], y_norm[0]])
    fim = np.array([x_norm[-1], y_norm[-1]])
    vetor = fim - inicio
    vetor = vetor / np.linalg.norm(vetor)
    pontos = np.column_stack([x_norm, y_norm]) - inicio
    projecao = np.outer(pontos @ vetor, vetor)
    distancias = np.linalg.norm(pontos - projecao, axis=1)
    return int(x[int(np.argmax(distancias))])


def silhueta_por_grupo(
    dados: np.ndarray, rotulos: np.ndarray, distancias: np.ndarray | None = None
) -> pd.DataFrame:
    """Silhueta média e proporção de registros mal classificados, por grupo.

    A silhueta média global esconde o caso mais comum: um grupo coeso e outro
    esgarçado se compensam e devolvem um número intermediário aceitável.
    """
    if distancias is not None:
        amostras = silhouette_samples(distancias, rotulos, metric="precomputed")
    else:
        amostras = silhouette_samples(dados, rotulos)
    tabela = pd.DataFrame({"grupo": rotulos, "silhueta": amostras})
    resumo = tabela.groupby("grupo")["silhueta"].agg(
        registros="size", media="mean", mediana="median", minimo="min"
    )
    resumo["pct_negativa"] = tabela.groupby("grupo")["silhueta"].apply(lambda s: (s < 0).mean())
    return resumo.round(4)
