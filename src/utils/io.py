"""Gravação padronizada de figuras e tabelas.

Regra do projeto: **nenhuma figura é gravada sem a tabela que a originou**. Os
notebooks são versionados sem saída (`nbstripout`), de modo que o que não for
persistido em disco desaparece do repositório.

Cada figura é gravada em dois lugares:

* ``reports/figures/<secao>/<nome>.png`` — artefato exigido pela disciplina;
* ``docs/imagens/evidencias/<secao>/<nome>.png`` — cópia que o MkDocs enxerga,
  já que o site só publica arquivos abaixo de ``docs/``.

O CSV de origem vai para ``reports/tables/<secao>/<nome>.csv``, sempre com
separador ``;`` e decimal ``,`` (abre direto no Excel em português).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from src import config


def configurar_estilo() -> None:
    """Aplica o estilo visual único do projeto ao matplotlib."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": config.DPI,
            "savefig.bbox": "tight",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#C9D3DB",
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#E6EBEF",
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlecolor": config.AZUL_PROFUNDO,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "font.size": 10,
        }
    )


def salvar_figura(
    fig: plt.Figure, secao: str, nome: str, dados: pd.DataFrame | None = None
) -> Path:
    """Grava a figura nos dois destinos e, opcionalmente, a tabela-fonte.

    Args:
        fig: figura do matplotlib já montada.
        secao: subdiretório lógico (``eda``, ``modelagem``, ``avaliacao``…).
        nome: nome do arquivo, sem extensão.
        dados: tabela que originou o gráfico. Quando informada, é gravada em
            ``reports/tables/<secao>/<nome>.csv``.

    Returns:
        Caminho do arquivo gravado em ``reports/figures``.
    """
    destino = config.FIGURES / secao
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{nome}.png"
    fig.savefig(caminho)

    espelho = config.DOCS_EVIDENCIAS / secao
    espelho.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(caminho, espelho / f"{nome}.png")

    if dados is not None:
        salvar_tabela(dados, secao, nome)

    plt.close(fig)
    return caminho


def salvar_tabela(dados: pd.DataFrame, secao: str, nome: str, indice: bool = True) -> Path:
    """Grava uma tabela em ``reports/tables/<secao>/<nome>.csv``."""
    destino = config.TABLES / secao
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{nome}.csv"
    dados.to_csv(caminho, sep=";", decimal=",", index=indice, encoding="utf-8-sig")
    return caminho


def salvar_json(conteudo: Any, caminho: Path) -> Path:
    """Grava um dicionário como JSON legível, criando o diretório se preciso."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(conteudo, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return caminho


def ler_json(caminho: Path) -> Any:
    """Lê um JSON gravado por :func:`salvar_json`."""
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def rotular_barras(ax: plt.Axes, formato: str = "{:.0f}", deslocamento: float = 3.0) -> None:
    """Escreve o valor no topo de cada barra de um eixo."""
    for container in ax.containers:
        ax.bar_label(
            container,
            fmt=lambda v: formato.format(v),
            padding=deslocamento,
            fontsize=8,
            color="#33454F",
        )
