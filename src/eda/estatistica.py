"""Medidas de associação e detecção de discrepantes usadas na análise exploratória."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest

from src import config


def v_de_cramer(a: pd.Series, b: pd.Series) -> float:
    """Associação entre duas variáveis nominais, corrigida por viés.

    Correlação de Pearson não se aplica a variáveis sem ordem. O V de Cramér
    devolve um valor entre 0 e 1 a partir do qui-quadrado da tabela de
    contingência, com a correção de Bergsma para tabelas pequenas.
    """
    tabela = pd.crosstab(a, b)
    if tabela.size == 0 or tabela.shape[0] < 2 or tabela.shape[1] < 2:
        return np.nan
    qui2 = stats.chi2_contingency(tabela, correction=False)[0]
    n = tabela.to_numpy().sum()
    phi2 = qui2 / n
    linhas, colunas = tabela.shape
    phi2_corrigido = max(0.0, phi2 - (colunas - 1) * (linhas - 1) / (n - 1))
    linhas_c = linhas - (linhas - 1) ** 2 / (n - 1)
    colunas_c = colunas - (colunas - 1) ** 2 / (n - 1)
    denominador = min(linhas_c - 1, colunas_c - 1)
    return float(np.sqrt(phi2_corrigido / denominador)) if denominador > 0 else np.nan


def matriz_cramer(dados: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Matriz simétrica de V de Cramér entre as colunas nominais informadas."""
    matriz = pd.DataFrame(index=colunas, columns=colunas, dtype=float)
    for i, primeira in enumerate(colunas):
        for segunda in colunas[i:]:
            valor = 1.0 if primeira == segunda else v_de_cramer(dados[primeira], dados[segunda])
            matriz.loc[primeira, segunda] = valor
            matriz.loc[segunda, primeira] = valor
    return matriz


def razao_correlacao(categorica: pd.Series, numerica: pd.Series) -> float:
    """Razão de correlação (eta²): quanto da variância da numérica a categoria explica."""
    grupos = numerica.groupby(categorica)
    media_geral = numerica.mean()
    entre = ((grupos.mean() - media_geral) ** 2 * grupos.size()).sum()
    total = ((numerica - media_geral) ** 2).sum()
    return float(entre / total) if total > 0 else np.nan


def outliers_iqr(serie: pd.Series, fator: float = 1.5) -> pd.Series:
    """Máscara booleana de discrepantes pelo critério de Tukey."""
    q1, q3 = serie.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (serie < q1 - fator * iqr) | (serie > q3 + fator * iqr)


def outliers_zscore(serie: pd.Series, limite: float = 3.0) -> pd.Series:
    """Máscara booleana de discrepantes pelo escore z robusto (mediana e MAD).

    O z clássico usa média e desvio padrão, ambos contaminados justamente pelos
    valores que se quer detectar. O MAD não tem esse problema.
    """
    mediana = serie.median()
    mad = (serie - mediana).abs().median()
    if mad == 0:
        return pd.Series(False, index=serie.index)
    z = 0.6745 * (serie - mediana) / mad
    return z.abs() > limite


def outliers_isolation(dados: pd.DataFrame, contaminacao: float = 0.05) -> pd.Series:
    """Máscara booleana de discrepantes multivariados por Isolation Forest.

    IQR e z olham uma variável por vez. Um imóvel pode ter área normal e idade
    normal e, ainda assim, ser atípico pela combinação das duas.
    """
    modelo = IsolationForest(
        contamination=contaminacao, random_state=config.SEMENTE, n_estimators=300
    )
    predito = modelo.fit_predict(dados)
    return pd.Series(predito == -1, index=dados.index)


def pares_redundantes(correlacao: pd.DataFrame, limiar: float = 0.7) -> pd.DataFrame:
    """Pares de variáveis com correlação absoluta acima do limiar."""
    superior = correlacao.where(np.triu(np.ones(correlacao.shape), k=1).astype(bool))
    empilhado = superior.stack()
    fortes = empilhado[empilhado.abs() >= limiar].sort_values(key=abs, ascending=False)
    return (
        fortes.reset_index()
        .rename(columns={"level_0": "variavel_a", "level_1": "variavel_b", 0: "correlacao"})
        .round(3)
    )


def psi(referencia: pd.Series, atual: pd.Series, faixas: int = 10) -> float:
    """Population Stability Index entre duas distribuições.

    Convenção de leitura: < 0,10 estável; 0,10 a 0,25 atenção; > 0,25 desvio
    relevante. É a métrica de *data drift* usada no monitoramento.
    """
    quantis = np.unique(np.nanquantile(referencia, np.linspace(0, 1, faixas + 1)))
    if len(quantis) < 3:
        return 0.0
    quantis[0], quantis[-1] = -np.inf, np.inf
    prop_ref = np.histogram(referencia, bins=quantis)[0] / len(referencia)
    prop_atual = np.histogram(atual, bins=quantis)[0] / len(atual)
    # Piso para não dividir por zero em faixa vazia.
    prop_ref = np.clip(prop_ref, 1e-6, None)
    prop_atual = np.clip(prop_atual, 1e-6, None)
    return float(np.sum((prop_atual - prop_ref) * np.log(prop_atual / prop_ref)))
