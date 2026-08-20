"""As três linhas de produto: nome, ação diferenciada e métrica de acompanhamento.

Um agrupamento vira produto quando cada grupo tem **um nome**, **uma ação** e
**uma forma de saber se a ação funcionou**. Sem os três, o resultado é um gráfico
bonito que ninguém usa.

O catálogo aqui é o mesmo que a fase 6 publica em
``models/catalogo_de_personas.json`` e embute no pacote da aplicação. Ele está
declarado no código — e não lido do JSON — porque o notebook 04 importa este
módulo antes de o notebook 06 gravar o arquivo; uma leitura em tempo de importação
quebraria a cadeia numa reconstrução limpa. O que impede as duas cópias de
divergirem é um teste: :func:`tests.test_modelo.test_catalogo_bate_com_o_manifesto`
compara ``len(PERSONAS)`` com o *k* do manifesto publicado.

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

#: Versão do modelo a que este catálogo pertence. Muda junto com as personas.
VERSAO_DO_CATALOGO = "2.0.0"

PERSONAS: dict[int, dict[str, str]] = {
    0: {
        "codigo": "S1",
        "nome": "Compacto herdado",
        "retrato": (
            "1048 pé² habitáveis, 52 anos de idade e 39 anos desde a última reforma; "
            "qualidade geral 5, 1.5 banheiros e sem lareira. 30% em zoneamento de "
            "média densidade."
        ),
        "politica_de_preco": "Percentil 40 do bairro — precificação por giro, não por margem",
        "teto_de_reforma": "6% do valor de avaliação",
        "acao": (
            "Decisão unidade a unidade em 12 meses: reforma leve padronizada (pintura, "
            "piso e louças) e venda, ou conversão em ativo de renda, ou desinvestimento. "
            "Acima do teto de 6%, o retorno não se paga neste padrão."
        ),
        "canal": "Digital, com foco em primeira aquisição e crédito facilitado",
        "metrica": ("Percentual do grupo com destino definido em 12 meses e tempo médio de giro"),
        "meta": "100% com destino definido · giro de 90 para 60 dias",
        "cor": config.AZUL_PROFUNDO,
    },
    1: {
        "codigo": "S2",
        "nome": "Amplo para requalificar",
        "retrato": (
            "1628 pé² habitáveis — 55% mais espaço que o S1 — com 7 cômodos, 2.0 "
            "banheiros e lareira, aos 43 anos. É o **menor preço por pé² da carteira**: "
            "105.42 dólares contra 133.90 do S3."
        ),
        "politica_de_preco": "Comparação direta de bairro, com reavaliação após a reforma",
        "teto_de_reforma": "12% do valor de avaliação",
        "acao": (
            "Pacote de valorização concentrado em cozinha e banheiro — os dois atributos "
            "em que o grupo fica meio nível abaixo do S3 — executado antes do anúncio. É "
            "onde a reforma tem a maior alavanca da carteira: espaço barato que a reforma "
            "reprecifica."
        ),
        "canal": "Corretagem tradicional, com foco em família em segunda aquisição",
        "metrica": (
            "Ganho de preço realizado sobre o custo da reforma e percentual reformado "
            "antes do anúncio"
        ),
        "meta": "ganho ≥ 1,8× o investido · ≥ 70% reformados antes do anúncio",
        "cor": config.CORAL,
    },
    2: {
        "codigo": "S3",
        "nome": "Recente de alto padrão",
        "retrato": (
            "6 anos de idade mediana, qualidade geral 7, 3.0 banheiros e porão de 1254 "
            "pé². É 33% da carteira em unidades e 44.8% da receita transacionada."
        ),
        "politica_de_preco": (
            "Comparação com lançamentos do período; desconto só acima de 90 dias em estoque"
        ),
        "teto_de_reforma": "sem reforma — o imóvel já está no padrão",
        "acao": (
            "Corretor dedicado, material de venda com fotografia profissional e vitrine "
            "premium. Nenhum orçamento de requalificação: gastar aqui é destruir margem "
            "no grupo que sustenta a receita."
        ),
        "canal": "Corretagem dedicada e vitrine premium",
        "metrica": (
            "Razão entre preço realizado e preço anunciado e percentual de vendas sem desconto"
        ),
        "meta": "realizado ÷ anunciado ≥ 0,97 · ≥ 60% sem desconto",
        "cor": config.VERDE,
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
        criterio: colunas de ordenação; o padrão é :data:`CRITERIO_ORDENACAO`.

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
                "retrato": dados["retrato"],
                "política de preço": dados["politica_de_preco"],
                "teto de reforma": dados["teto_de_reforma"],
                "ação diferenciada": dados["acao"],
                "canal": dados["canal"],
                "métrica de acompanhamento": dados["metrica"],
                "meta": dados["meta"],
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
    """Código de negócio de um segmento (``S1`` a ``S3``)."""
    return PERSONAS[int(segmento)]["codigo"]
