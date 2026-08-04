"""Classificação de um imóvel novo pelo modelo publicado.

O ponto central deste módulo é que a aplicação **não reimplementa a preparação**.
O artefato serializado em ``models/pipeline_segmentacao.joblib`` carrega o
pré-processador e o K-Means juntos, com as mesmas médias e desvios do treino.
Reimplementar a padronização na camada de aplicação é a forma mais comum de um
modelo funcionar no notebook e falhar em produção.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from joblib import load

from src import config
from src.data import dicionario as dic
from src.model import personas as pers
from src.utils.io import ler_json

#: Colunas que o pipeline espera receber, na ordem em que foi treinado.
COLUNAS_ENTRADA = dic.NUMERICAS + dic.ORDINAIS + dic.BINARIAS

#: Cortes da razão de fronteira, **calibrados na distribuição da carteira**, e
#: não escolhidos por intuição. Sobre os 2.925 imóveis de treino, a razão entre
#: a distância ao centroide mais próximo e ao segundo mais próximo tem
#: quartil inferior 0,60, mediana 0,715 e nono decil 0,93.
#:
#: A leitura operacional: cerca de um quarto da carteira é núcleo, dois terços
#: são típicos e um décimo fica na fronteira — proporção que a Gerência de
#: Ativos consegue revisar manualmente.
CORTE_NUCLEO = 0.60
CORTE_FRONTEIRA = 0.90

#: Valores neutros para preencher o que o usuário não informar — a mediana da
#: carteira. Declarados aqui para que a suposição fique visível na tela.
PADROES = {
    "area_habitavel": 1441.0,
    "area_porao": 989.0,
    "area_terreno": 9428.0,
    "area_garagem": 480.0,
    "area_varandas": 164.0,
    "banheiros_total": 2.0,
    "comodos": 6.0,
    "dormitorios": 3.0,
    "lareiras": 1.0,
    "idade_imovel": 34.0,
    "anos_desde_reforma": 15.0,
    "qualidade_geral": 6.0,
    "conservacao_geral": 5.0,
    "qualidade_externa": 3.0,
    "qualidade_cozinha": 3.0,
    "qualidade_porao": 3.0,
    "acabamento_garagem": 2.0,
}


@lru_cache(maxsize=1)
def carregar_modelo():
    """Carrega o pipeline serializado e seus metadados (uma vez por processo)."""
    pipeline = load(config.MODELS / "pipeline_segmentacao.joblib")
    metadados = ler_json(config.MODELS / "metadados_segmentacao.json")
    traducao = {
        int(bruto): int(canonico)
        for bruto, canonico in metadados["traducao_rotulo_bruto_para_canonico"].items()
    }
    return pipeline, metadados, traducao


def montar_registro(atributos: dict) -> pd.DataFrame:
    """Monta a linha de entrada, completando o que faltar com a mediana da carteira.

    As flags binárias são **derivadas**, não pedidas: um imóvel com área de
    porão igual a zero não tem porão, e deixar isso a cargo de quem preenche o
    formulário abriria espaço para entrada inconsistente.
    """
    registro = {**PADROES, **{k: v for k, v in atributos.items() if k in PADROES}}
    registro["tem_porao"] = int(registro["area_porao"] > 0)
    registro["tem_garagem"] = int(registro["area_garagem"] > 0)
    registro["tem_lareira"] = int(registro["lareiras"] > 0)
    registro["tem_segundo_pavimento"] = int(atributos.get("tem_segundo_pavimento", 0))
    if registro["area_porao"] == 0:
        registro["qualidade_porao"] = 0
    if registro["area_garagem"] == 0:
        registro["acabamento_garagem"] = 0
    return pd.DataFrame([registro])[COLUNAS_ENTRADA]


def classificar(atributos: dict) -> dict:
    """Classifica um imóvel e devolve segmento, persona e grau de confiança.

    A confiança é a razão entre a distância ao centroide mais próximo e a
    distância ao segundo mais próximo. Perto de 1, o imóvel está na fronteira
    entre dois segmentos — e a ação automática não deveria ser disparada sem
    revisão humana.
    """
    pipeline, metadados, traducao = carregar_modelo()
    registro = montar_registro(atributos)

    transformado = pipeline.named_steps["preparacao"].transform(registro)
    centroides = pipeline.named_steps["kmeans"].cluster_centers_
    distancias = np.linalg.norm(centroides - transformado, axis=1)

    ordem = np.argsort(distancias)
    segmento = traducao[int(ordem[0])]
    razao = float(distancias[ordem[0]] / distancias[ordem[1]])

    if razao < CORTE_NUCLEO:
        confianca = "núcleo"
    elif razao < CORTE_FRONTEIRA:
        confianca = "típico"
    else:
        confianca = "fronteira"

    por_segmento = {
        traducao[int(indice)]: float(distancias[indice]) for indice in range(len(distancias))
    }
    persona = pers.PERSONAS[segmento]
    return {
        "segmento": segmento,
        "codigo": persona["codigo"],
        "persona": persona["nome"],
        "resumo": persona["resumo"],
        "acao": persona["acao"],
        "metrica": persona["metrica"],
        "canal": persona["canal"],
        "cor": persona["cor"],
        "confianca": confianca,
        "razao_fronteira": round(razao, 3),
        "distancias": {pers.codigo(s): round(d, 3) for s, d in sorted(por_segmento.items())},
        "segundo_mais_proximo": pers.codigo(traducao[int(ordem[1])]),
        "registro": registro.iloc[0].to_dict(),
        "versao_modelo": metadados["versao_modelo"],
    }


def classificar_lote(dados: pd.DataFrame) -> pd.DataFrame:
    """Classifica um conjunto inteiro — o caminho usado a cada carga."""
    pipeline, _, traducao = carregar_modelo()
    faltando = [coluna for coluna in COLUNAS_ENTRADA if coluna not in dados.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes na entrada: {faltando}")
    brutos = pipeline.predict(dados[COLUNAS_ENTRADA])
    segmentos = np.array([traducao[int(rotulo)] for rotulo in brutos])
    return dados.assign(
        segmento=segmentos,
        codigo_segmento=[pers.codigo(s) for s in segmentos],
        persona=[pers.PERSONAS[int(s)]["nome"] for s in segmentos],
    )
