"""Executa todos os notebooks na ordem e falha se algum quebrar.

É a conferência que sustenta o critério eliminatório da disciplina: *entrega cujo
notebook não executa em ambiente limpo recebe Insuficiente*. Rodar isto antes de
entregar é mais barato do que descobrir na banca.

As versões executadas, com saída, vão para ``reports/notebooks/``. Os notebooks
versionados em ``notebooks/`` continuam sem saída, como o `nbstripout` exige.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

from src import config

ORIGEM = config.RAIZ / "notebooks"
DESTINO = config.REPORTS / "notebooks"


def executar_um(caminho: Path) -> tuple[bool, float, str]:
    """Executa um notebook e devolve (sucesso, duração, mensagem)."""
    inicio = time.perf_counter()
    caderno = nbformat.read(caminho, as_version=4)
    cliente = NotebookClient(
        caderno,
        timeout=1800,
        kernel_name="python3",
        resources={"metadata": {"path": str(ORIGEM)}},
    )
    try:
        cliente.execute()
    except CellExecutionError as erro:
        return False, time.perf_counter() - inicio, str(erro).split("\n")[-2][:200]

    DESTINO.mkdir(parents=True, exist_ok=True)
    nbformat.write(caderno, DESTINO / caminho.name)
    return True, time.perf_counter() - inicio, "ok"


def executar_todos() -> int:
    """Executa todos os notebooks em ordem alfabética. Devolve o código de saída."""
    cadernos = sorted(ORIGEM.glob("*.ipynb"))
    if not cadernos:
        print("Nenhum notebook encontrado.")
        return 1

    falhas = 0
    for caderno in cadernos:
        print(f"▶ {caderno.name}", flush=True)
        sucesso, duracao, mensagem = executar_um(caderno)
        marca = "✔" if sucesso else "✘"
        print(f"  {marca} {duracao:6.1f}s · {mensagem}", flush=True)
        falhas += int(not sucesso)

    print(f"\n{len(cadernos) - falhas} de {len(cadernos)} notebooks executaram sem erro.")
    if falhas == 0:
        print(f"Versões com saída em {DESTINO}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(executar_todos())
