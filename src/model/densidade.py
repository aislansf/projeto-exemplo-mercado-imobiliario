"""Clusterização por densidade: DBSCAN e Mean Shift.

Nos dois casos o número de grupos **emerge** do parâmetro, em vez de ser
imposto. É a diferença conceitual que justifica tê-los no comparativo mesmo
quando o resultado final não os escolhe.

No DBSCAN, o ponto de ruído não é resíduo: é o imóvel que não pertence a
nenhuma linha de produto e precisa de avaliação individual. Para a Meridiano,
essa lista **é** uma entrega.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, MeanShift, estimate_bandwidth
from sklearn.neighbors import NearestNeighbors

from src import config
from src.model.particional import metricas_internas


def curva_k_distancia(dados: np.ndarray, k: int) -> np.ndarray:
    """Distâncias ao *k*-ésimo vizinho, ordenadas — a curva que calibra o `eps`.

    O joelho da curva separa o regime em que os pontos têm vizinhos próximos
    (dentro de um grupo denso) do regime em que não têm. É ali que o `eps` deve
    ficar. Escolher `eps` por tentativa e erro é o erro mais comum do DBSCAN.
    """
    vizinhos = NearestNeighbors(n_neighbors=k).fit(dados)
    distancias, _ = vizinhos.kneighbors(dados)
    return np.sort(distancias[:, -1])


def joelho_k_distancia(curva: np.ndarray) -> tuple[int, float]:
    """Localiza o joelho da curva k-distância pela maior distância à corda."""
    x = np.arange(len(curva), dtype=float)
    x_norm = (x - x.min()) / (x.max() - x.min())
    y_norm = (curva - curva.min()) / (curva.max() - curva.min())
    inicio = np.array([x_norm[0], y_norm[0]])
    fim = np.array([x_norm[-1], y_norm[-1]])
    vetor = (fim - inicio) / np.linalg.norm(fim - inicio)
    pontos = np.column_stack([x_norm, y_norm]) - inicio
    projecao = np.outer(pontos @ vetor, vetor)
    indice = int(np.argmax(np.linalg.norm(pontos - projecao, axis=1)))
    return indice, float(curva[indice])


def varrer_dbscan(dados: np.ndarray, valores_eps: np.ndarray, min_amostras: int) -> pd.DataFrame:
    """Aplica DBSCAN para uma grade de `eps` e resume o resultado de cada um."""
    linhas = []
    for eps in valores_eps:
        rotulos = DBSCAN(eps=float(eps), min_samples=min_amostras).fit_predict(dados)
        validos = rotulos >= 0
        n_grupos = len(set(rotulos[validos]))
        pct_ruido = float((~validos).mean())
        silhueta = np.nan
        if n_grupos >= 2 and validos.sum() > n_grupos:
            silhueta = metricas_internas(dados[validos], rotulos[validos])["silhueta"]
        linhas.append(
            {
                "eps": round(float(eps), 3),
                "min_amostras": min_amostras,
                "grupos": n_grupos,
                "pct_ruido": round(pct_ruido, 4),
                "silhueta_sem_ruido": round(silhueta, 4) if silhueta == silhueta else np.nan,
                "maior_grupo_pct": round(
                    float(np.bincount(rotulos[validos]).max() / len(rotulos)) if n_grupos else 0.0,
                    4,
                ),
            }
        )
    return pd.DataFrame(linhas).set_index("eps")


def aplicar_dbscan(dados: np.ndarray, eps: float, min_amostras: int) -> np.ndarray:
    """Executa o DBSCAN com os parâmetros calibrados."""
    return DBSCAN(eps=eps, min_samples=min_amostras).fit_predict(dados)


def varrer_mean_shift(
    dados: np.ndarray, quantis: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4)
) -> pd.DataFrame:
    """Compara larguras de banda estimadas por diferentes quantis.

    O `bandwidth` é o raio da janela que busca os modos da densidade. Quanto
    maior, menos grupos — e a relação não é linear, o que torna a varredura
    obrigatória para poder afirmar qualquer coisa sobre o número de grupos.
    """
    linhas = []
    for quantil in quantis:
        largura = estimate_bandwidth(
            dados, quantile=quantil, n_samples=1000, random_state=config.SEMENTE
        )
        if largura <= 0:
            continue
        modelo = MeanShift(bandwidth=largura, bin_seeding=True).fit(dados)
        rotulos = modelo.labels_
        n_grupos = len(np.unique(rotulos))
        metricas = (
            metricas_internas(dados, rotulos)
            if n_grupos >= 2
            else {"silhueta": np.nan, "davies_bouldin": np.nan, "calinski_harabasz": np.nan}
        )
        tamanhos = np.bincount(rotulos)
        linhas.append(
            {
                "quantil": quantil,
                "bandwidth": round(float(largura), 3),
                "grupos": int(n_grupos),
                "silhueta": round(metricas["silhueta"], 4)
                if metricas["silhueta"] == metricas["silhueta"]
                else np.nan,
                "maior_grupo_pct": round(float(tamanhos.max() / len(rotulos)), 4),
                "grupos_com_menos_de_30": int((tamanhos < 30).sum()),
            }
        )
    return pd.DataFrame(linhas).set_index("quantil")


def perfil_do_ruido(curada: pd.DataFrame, rotulos: np.ndarray, colunas: list[str]) -> pd.DataFrame:
    """Compara a mediana dos pontos de ruído com a dos pontos agrupados.

    Sem esta tabela, o ruído é apenas um número. Com ela, vira a descrição de um
    tipo de imóvel — e o que a diretoria recebe é uma lista acionável.
    """
    ruido = rotulos == -1
    perfil = pd.DataFrame(
        {
            "agrupados": curada.loc[~ruido, colunas].median(),
            "ruido": curada.loc[ruido, colunas].median(),
        }
    )
    perfil["razao"] = (perfil["ruido"] / perfil["agrupados"].replace(0, np.nan)).round(2)
    return perfil.round(2)
