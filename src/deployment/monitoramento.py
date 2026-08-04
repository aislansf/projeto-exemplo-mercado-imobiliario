"""Monitoramento do modelo em operação.

Um agrupamento não tem erro de previsão para acompanhar: não existe gabarito.
O que se acompanha é a **entrada** mudar de distribuição (*data drift*) e os
**grupos** perderem coesão (*cluster drift*).

Este módulo compara qualquer recorte da carteira contra a linha de base gravada
na implantação, sem exigir acesso à base de treino.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from src import config
from src.data import dicionario as dic
from src.eda.estatistica import psi
from src.utils.io import ler_json

LIMIAR_ATENCAO = 0.10
LIMIAR_ACAO = 0.25


@lru_cache(maxsize=1)
def carregar_linha_de_base() -> dict:
    """Lê as distribuições de referência gravadas na implantação."""
    return ler_json(config.MODELS / "linha_de_base.json")


def situacao(valor: float) -> str:
    """Traduz o PSI para a faixa de leitura usada no plano de monitoramento."""
    if valor >= LIMIAR_ACAO:
        return "ação"
    if valor >= LIMIAR_ATENCAO:
        return "atenção"
    return "estável"


def avaliar_drift(atual: pd.DataFrame, referencia: pd.DataFrame | None = None) -> pd.DataFrame:
    """Calcula o PSI de cada atributo contra a referência.

    Args:
        atual: recorte a avaliar.
        referencia: quando informada, é usada diretamente; quando ausente, a
            comparação usa os decis gravados em ``models/linha_de_base.json``,
            que é o caminho de produção — a base de treino não fica disponível.
    """
    base = carregar_linha_de_base()
    linhas = []
    for coluna in dic.NUMERICAS + dic.ORDINAIS:
        if coluna not in atual.columns:
            continue
        if referencia is not None:
            valor = psi(referencia[coluna], atual[coluna])
            mediana_referencia = float(referencia[coluna].median())
        else:
            decis = np.array(base[coluna]["decis"], dtype=float)
            sintetica = pd.Series(np.interp(np.linspace(0, 1, 1000), np.linspace(0, 1, 11), decis))
            valor = psi(sintetica, atual[coluna])
            mediana_referencia = float(base[coluna]["mediana"])
        linhas.append(
            {
                "atributo": dic.rotulo(coluna),
                "coluna": coluna,
                "psi": round(valor, 4),
                "mediana_referencia": round(mediana_referencia, 2),
                "mediana_atual": round(float(atual[coluna].median()), 2),
                "situacao": situacao(valor),
            }
        )
    return pd.DataFrame(linhas).sort_values("psi", ascending=False).reset_index(drop=True)


def avaliar_composicao(atual: pd.Series, referencia: pd.Series) -> pd.DataFrame:
    """Compara a proporção de cada segmento entre dois recortes."""
    tabela = pd.DataFrame(
        {
            "referência (%)": 100 * referencia.value_counts(normalize=True),
            "atual (%)": 100 * atual.value_counts(normalize=True),
        }
    ).fillna(0)
    tabela["variação (p.p.)"] = (tabela["atual (%)"] - tabela["referência (%)"]).round(2)
    tabela["alerta"] = np.where(tabela["variação (p.p.)"].abs() >= 10, "revisar orçamento", "—")
    return tabela.round(2).sort_index()


def resumo_de_saude(drift: pd.DataFrame, coesao_atual: float) -> dict:
    """Consolida os indicadores em um veredicto único para o painel."""
    em_acao = int((drift["situacao"] == "ação").sum())
    em_atencao = int((drift["situacao"] == "atenção").sum())

    if em_acao > 0:
        veredicto, cor = "Reciclagem necessária", config.CORAL
    elif em_atencao >= 3 or coesao_atual < config.SILHUETA_MINIMA:
        veredicto, cor = "Atenção", config.AMARELO
    else:
        veredicto, cor = "Estável", config.VERDE

    return {
        "veredicto": veredicto,
        "cor": cor,
        "atributos_em_acao": em_acao,
        "atributos_em_atencao": em_atencao,
        "coesao_atual": round(coesao_atual, 4),
        "gatilho": (
            f"PSI ≥ {LIMIAR_ACAO} em qualquer atributo, três atributos acima de "
            f"{LIMIAR_ATENCAO}, ou silhueta abaixo de {config.SILHUETA_MINIMA}"
        ),
    }
