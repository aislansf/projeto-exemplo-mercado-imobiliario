"""Configuração central do projeto.

Concentra caminhos, semente aleatória, paleta e parâmetros que precisam ser
idênticos entre notebooks, scripts de pipeline e aplicação Streamlit. Nenhum
outro módulo deve montar caminho na mão.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Caminhos
# --------------------------------------------------------------------------- #

RAIZ = Path(__file__).resolve().parents[1]

DATA = RAIZ / "data"
DATA_RAW = DATA / "raw"
DATA_PROCESSED = DATA / "processed"
DATA_EXTERNAL = DATA / "external"

MODELS = RAIZ / "models"
REPORTS = RAIZ / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
REFERENCES = RAIZ / "references"
DOCS = RAIZ / "docs"

# As figuras são gravadas duas vezes: em `reports/figures/` (artefato exigido
# pela disciplina) e em `docs/imagens/evidencias/` (para o MkDocs, que só
# enxerga arquivos abaixo de `docs/`). Ver `src/utils/io.py`.
DOCS_EVIDENCIAS = DOCS / "imagens" / "evidencias"

# --------------------------------------------------------------------------- #
# Fonte dos dados
# --------------------------------------------------------------------------- #

# Ames Housing — De Cock (2011), Journal of Statistics Education, v.19, n.3.
# Download direto, sem cadastro, do endereço oficial do artigo.
URL_AMES = "https://jse.amstat.org/v19n3/decock/AmesHousing.txt"
ARQUIVO_BRUTO = DATA_RAW / "ames_housing.txt"
ARQUIVO_BRUTO_PARQUET = DATA_RAW / "ames_housing.parquet"

BASE_CURADA = DATA_PROCESSED / "imoveis_curados.parquet"
MATRIZ_MODELAGEM = DATA_PROCESSED / "matriz_modelagem.parquet"
TRANSACOES = DATA_PROCESSED / "transacoes.parquet"
SEGMENTOS = DATA_PROCESSED / "imoveis_segmentados.parquet"

# --------------------------------------------------------------------------- #
# Reprodutibilidade
# --------------------------------------------------------------------------- #

SEMENTE = 42

# --------------------------------------------------------------------------- #
# Regras de negócio vindas do Canvas do Problema
# --------------------------------------------------------------------------- #

#: A diretoria financia no máximo cinco linhas de produto distintas.
K_MAXIMO_NEGOCIO = 5
#: Abaixo de dois grupos não existe segmentação.
K_MINIMO_NEGOCIO = 2
#: Silhueta mínima aceita no critério técnico do Canvas.
SILHUETA_MINIMA = 0.15
#: Percentual máximo de imóveis que podem cair como ruído em métodos de densidade.
RUIDO_MAXIMO = 0.10

# --------------------------------------------------------------------------- #
# Identidade visual (espelha docs/assets/css/brand.css)
# --------------------------------------------------------------------------- #

AZUL_PROFUNDO = "#1B4965"
AZUL_COBALTO = "#2A6F97"
AZUL_CLARO = "#62B6CB"
VERDE = "#74C69D"
AMARELO = "#F4D35E"
CORAL = "#EE6C4D"
ROXO = "#8E7DBE"
LARANJA = "#F49D6E"
ROSA = "#F2A6A6"
CINZA = "#8A9BA8"

PALETA = [AZUL_PROFUNDO, CORAL, VERDE, AMARELO, ROXO, AZUL_CLARO, LARANJA, ROSA]
PALETA_SEGMENTOS = [AZUL_PROFUNDO, CORAL, VERDE, AMARELO, ROXO]

DPI = 150


def garantir_diretorios() -> None:
    """Cria os diretórios de saída caso ainda não existam."""
    for caminho in (
        DATA_RAW,
        DATA_PROCESSED,
        DATA_EXTERNAL,
        MODELS,
        FIGURES,
        TABLES,
        REFERENCES,
        DOCS_EVIDENCIAS,
    ):
        caminho.mkdir(parents=True, exist_ok=True)
