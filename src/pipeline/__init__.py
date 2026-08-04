"""Orquestração das fases do CRISP-DM.

Cada módulo corresponde a uma fase e pode ser executado isoladamente:

===========================  =========================================
Módulo                       Fase do CRISP-DM
===========================  =========================================
``src.data.ingestao``        2.1 — Coleta dos dados iniciais
``src.data.preparacao``      3   — Preparação dos dados
``src.eda.fluxo8fases``      2.3 — Exploração (as oito fases)
``src.pipeline.modelagem``   4   — Modelagem (clusterização)
``src.pipeline.regras``      4   — Modelagem (regras de associação)
``src.pipeline.avaliacao``   5   — Avaliação sob a ótica do negócio
``src.pipeline.implantacao`` 6   — Implantação e monitoramento
===========================  =========================================

``uv run invoke pipeline`` roda a sequência inteira, do download à publicação
dos artefatos de implantação.
"""

from __future__ import annotations


def executar_tudo() -> None:
    """Executa as seis fases na ordem, do zero aos artefatos de implantação."""
    from src.data import ingestao, preparacao
    from src.eda import fluxo8fases
    from src.pipeline import avaliacao, implantacao, modelagem, regras

    print("── CRISP-DM 2.1 · Coleta dos dados iniciais")
    ingestao.baixar()

    print("── CRISP-DM 3 · Preparação dos dados")
    curada = preparacao.construir_base_curada()
    preparacao.construir_matriz_modelagem(curada)

    print("── CRISP-DM 2.3 · Análise exploratória (8 fases)")
    fluxo8fases.executar()

    print("── CRISP-DM 4 · Modelagem (clusterização)")
    modelagem.executar()

    print("── CRISP-DM 4 · Modelagem (regras de associação)")
    regras.executar()

    print("── CRISP-DM 5 · Avaliação")
    avaliacao.executar()

    print("── CRISP-DM 6 · Implantação")
    implantacao.executar()

    print("\n✔ Ciclo CRISP-DM completo. Evidências em reports/, modelos em models/.")
