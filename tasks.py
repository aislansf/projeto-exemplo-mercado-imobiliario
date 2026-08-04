"""Tarefas do projeto executadas com o invoke.

Liste as tarefas disponíveis com `uv run invoke --list`.

O caminho completo, do zero ao painel publicado:

    uv run invoke pipeline     # as seis fases do CRISP-DM
    uv run invoke app          # a aplicação de implantação
"""

import glob
import os
import shutil

from invoke import task

# --------------------------------------------------------------------------- #
# Pipeline — CRISP-DM
# --------------------------------------------------------------------------- #


@task
def ingestao(c):
    """CRISP-DM 2.1 — Baixa a base e materializa a camada bruta em data/raw."""
    c.run("python -m src.data.ingestao")


@task
def preparacao(c):
    """CRISP-DM 3 — Constrói a base curada e a matriz de modelagem."""
    c.run("python -m src.data.preparacao")


@task
def eda(c):
    """CRISP-DM 2.3 — Executa as oito fases da análise exploratória."""
    c.run("python -m src.eda.fluxo8fases")


@task
def modelagem(c):
    """CRISP-DM 4 — Clusterização: escolha de k, seis algoritmos e perfilagem."""
    c.run("python -m src.pipeline.modelagem")


@task
def regras(c):
    """CRISP-DM 4 — Regras de associação com Apriori, Eclat e FP-Growth."""
    c.run("python -m src.pipeline.regras")


@task
def avaliacao(c):
    """CRISP-DM 5 — Confronto com os critérios de aceite e leitura de negócio."""
    c.run("python -m src.pipeline.avaliacao")


@task
def implantacao(c):
    """CRISP-DM 6 — Artefatos de implantação, drift e plano de monitoramento."""
    c.run("python -m src.pipeline.implantacao")


@task
def pipeline(c):
    """Executa as seis fases do CRISP-DM na ordem, do download aos artefatos."""
    c.run('python -c "from src.pipeline import executar_tudo; executar_tudo()"')


@task
def notebooks(c):
    """Executa os notebooks na ordem e grava as versões executadas em reports/."""
    c.run("python -m src.utils.executar_notebooks")


# --------------------------------------------------------------------------- #
# Ambiente de trabalho
# --------------------------------------------------------------------------- #


@task
def lab(c):
    """Abre o JupyterLab."""
    c.run("jupyter lab")


@task
def app(c):
    """Executa a aplicação Streamlit definida em src/deployment/app.py."""
    c.run("streamlit run src/deployment/app.py")


@task
def docs(c):
    """Serve a documentação localmente em http://127.0.0.1:8000."""
    c.run("mkdocs serve")


@task
def build(c):
    """Gera o site estático da documentação no diretório site/."""
    c.run("mkdocs build")


# --------------------------------------------------------------------------- #
# Qualidade
# --------------------------------------------------------------------------- #


@task
def lint(c):
    """Verifica o código com o ruff (lint e formatação)."""
    c.run("ruff check src tasks.py tests")
    c.run("ruff format --check src tasks.py tests")


@task
def fmt(c):
    """Formata o código e aplica correções automáticas do ruff."""
    c.run("ruff format src tasks.py tests")
    c.run("ruff check --fix src tasks.py tests")


@task
def test(c):
    """Executa a suíte de testes com o pytest."""
    c.run("pytest -q")


@task
def limpar(c):
    """Remove os artefatos gerados, preservando a camada bruta em data/raw."""
    alvos = [
        "data/processed/*.parquet",
        "models/*.joblib",
        "models/*.json",
        "reports/figures",
        "reports/tables",
        "docs/imagens/evidencias",
        "site",
    ]
    for alvo in alvos:
        for caminho in glob.glob(alvo):
            if os.path.isdir(caminho):
                shutil.rmtree(caminho, ignore_errors=True)
            else:
                os.remove(caminho)
    print("Artefatos removidos. Reconstrua com: uv run invoke pipeline")
