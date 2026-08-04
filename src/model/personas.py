"""As quatro personas: nome, descrição, ação diferenciada e métrica de acompanhamento.

Um agrupamento vira produto quando cada grupo tem **um nome**, **uma ação** e
**uma forma de saber se a ação funcionou**. Sem os três, o resultado é um
gráfico bonito que ninguém usa.

Os rótulos do K-Means não têm ordem: rodar de novo com outra semente troca o
número dos grupos. :func:`ordenar_canonicamente` resolve isso reordenando os
segmentos por qualidade geral e área, de modo que o segmento 0 seja sempre o de
padrão mais baixo. É o que permite amarrar persona a segmento sem depender da
sorte da inicialização.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import config

#: Ordem canônica: critério de desempate para tornar o rótulo reprodutível.
CRITERIO_ORDENACAO = ["qualidade_geral", "area_habitavel"]

PERSONAS: dict[int, dict[str, str]] = {
    0: {
        "codigo": "S1",
        "nome": "Requalificação sem porão",
        "resumo": (
            "Imóvel antigo, sem porão, de padrão construtivo mais baixo e com um terço "
            "do grupo em formato duplex. É o estoque que a carteira herdou e nunca tratou."
        ),
        "acao": (
            "Avaliação individual por unidade, com decisão binária: converter em ativo de "
            "renda (locação, aproveitando o formato duplex) ou desinvestir. Teto de "
            "requalificação limitado a 8% do valor de avaliação — acima disso, o retorno "
            "não se paga neste padrão."
        ),
        "metrica": (
            "Percentual do grupo com destino definido em 12 meses (meta: 100%) e retorno "
            "sobre o capital requalificado (meta: ≥ 12% a.a.)."
        ),
        "canal": "Carteira de investidores e gestores de locação",
        "cor": config.ROXO,
    },
    1: {
        "codigo": "S2",
        "nome": "Compacto de entrada",
        "resumo": (
            "Casa pequena, meio século de idade, sem reforma recente, com garagem "
            "apertada e um banheiro e meio. É o imóvel de primeira aquisição — e o maior "
            "grupo da carteira."
        ),
        "acao": (
            "Precificação por giro, não por margem: preço alinhado ao percentil 40 do "
            "bairro e pacote de reforma leve padronizado (pintura, piso e louças), com "
            "teto de 6% do valor. Financiamento facilitado como argumento de venda."
        ),
        "metrica": (
            "Tempo médio de giro do estoque (meta: reduzir de 90 para 60 dias) e taxa de "
            "conversão do canal digital (meta: ≥ 3%)."
        ),
        "canal": "Digital, com foco em primeira moradia e crédito facilitado",
        "cor": config.AZUL_CLARO,
    },
    2: {
        "codigo": "S3",
        "nome": "Familiar consolidado",
        "resumo": (
            "Imóvel amplo, de meia-idade, com sete cômodos, dois banheiros e lareira. "
            "Padrão médio bem conservado, em bairros estabelecidos. É onde a reforma "
            "tem o melhor retorno da carteira."
        ),
        "acao": (
            "Pacote de reforma de valorização concentrado em cozinha e banheiro — os dois "
            "atributos em que este grupo fica meio nível abaixo do segmento superior, com "
            "teto de 12% do valor de avaliação. Precificação por comparação de bairro."
        ),
        "metrica": (
            "Ganho de preço realizado sobre o custo da reforma (meta: ≥ 1,8× o investido) "
            "e percentual de unidades reformadas antes do anúncio (meta: ≥ 70%)."
        ),
        "canal": "Corretagem tradicional, com foco em família em segunda aquisição",
        "cor": config.VERDE,
    },
    3: {
        "codigo": "S4",
        "nome": "Novo de alto padrão",
        "resumo": (
            "Construção recente, grande, com três banheiros, porão amplo e acabamento "
            "superior. Um terço da carteira em unidades, metade da receita."
        ),
        "acao": (
            "Nenhuma reforma: o imóvel já está no padrão. Corretor dedicado, material de "
            "venda com fotografia profissional e precificação por comparação direta com "
            "os lançamentos do período. Descontos autorizados apenas acima de 90 dias."
        ),
        "metrica": (
            "Razão entre preço realizado e preço anunciado (meta: ≥ 0,97) e percentual de "
            "vendas fechadas sem desconto (meta: ≥ 60%)."
        ),
        "canal": "Corretagem dedicada e vitrine premium",
        "cor": config.CORAL,
    },
}


def ordenar_canonicamente(
    curada: pd.DataFrame, rotulos: np.ndarray, criterio: list[str] | None = None
) -> np.ndarray:
    """Renumera os grupos em ordem crescente de padrão construtivo.

    Sem isso, o segmento chamado "0" muda de identidade a cada reexecução e
    qualquer texto que se refira a ele fica errado na próxima rodada.

    Args:
        curada: base curada, em unidades originais.
        rotulos: rótulos como saíram do algoritmo.
        criterio: colunas de ordenação; o padrão é
            :data:`CRITERIO_ORDENACAO`.

    Returns:
        Vetor de rótulos renumerados, com 0 sempre no padrão mais baixo.
    """
    criterio = criterio or CRITERIO_ORDENACAO
    medianas = curada.assign(_grupo=rotulos).groupby("_grupo")[criterio].median()
    ordem = medianas.sort_values(criterio).index.tolist()
    traducao = {antigo: novo for novo, antigo in enumerate(ordem)}
    return np.array([traducao.get(rotulo, -1) for rotulo in rotulos])


def tabela_personas() -> pd.DataFrame:
    """As personas em formato de tabela, para publicação no relatório."""
    return pd.DataFrame(
        [
            {
                "segmento": segmento,
                "código": dados["codigo"],
                "persona": dados["nome"],
                "descrição": dados["resumo"],
                "ação diferenciada": dados["acao"],
                "métrica de acompanhamento": dados["metrica"],
                "canal": dados["canal"],
            }
            for segmento, dados in PERSONAS.items()
        ]
    ).set_index("segmento")


def cores() -> list[str]:
    """Cores das personas, na ordem canônica."""
    return [PERSONAS[i]["cor"] for i in sorted(PERSONAS)]


def nomes() -> list[str]:
    """Rótulos curtos ``código — nome``, na ordem canônica."""
    return [f"{PERSONAS[i]['codigo']} — {PERSONAS[i]['nome']}" for i in sorted(PERSONAS)]


def codigo(segmento: int) -> str:
    """Código de negócio de um segmento (``S1`` a ``S4``)."""
    return PERSONAS[int(segmento)]["codigo"]
