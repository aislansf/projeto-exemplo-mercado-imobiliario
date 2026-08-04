"""CRISP-DM 2.1 — Coleta dos dados iniciais.

Baixa a base Ames Housing do endereço oficial do artigo que a publicou e
materializa a camada bruta em ``data/raw/``. A operação é **idempotente**: se o
arquivo já existe e tem o tamanho esperado, o download não é refeito.

A camada bruta é tratada como imutável — nenhuma outra parte do projeto escreve
em ``data/raw/``.
"""

from __future__ import annotations

import hashlib
import urllib.request
from datetime import UTC, datetime

import pandas as pd

from src import config
from src.utils.io import salvar_json

#: Dimensões declaradas por De Cock (2011) e conferidas no arquivo.
LINHAS_ESPERADAS = 2930
COLUNAS_ESPERADAS = 82

#: Sentinelas de ausência realmente usadas pela origem.
#:
#: O arquivo grava `NA` para "não se aplica" e a palavra `None` como **categoria
#: legítima** de `Mas Vnr Type` ("sem revestimento em alvenaria aparente"). A
#: leitura padrão do pandas converte as duas em nulo, e com isso 1.752 imóveis
#: sem revestimento aparecem como informação faltante. Declarar `na_values`
#: explicitamente é o que separa 1.775 falsos ausentes de 23 ausentes de fato.
SENTINELAS = ["NA", ""]


def _ler_origem(caminho) -> pd.DataFrame:
    """Lê o arquivo tabulado tratando apenas as sentinelas declaradas como nulo."""
    return pd.read_csv(caminho, sep="\t", keep_default_na=False, na_values=SENTINELAS)


def inventario_sentinelas() -> pd.DataFrame:
    """Conta, coluna a coluna, as ocorrências literais de `NA`, `None` e vazio.

    É a evidência de que a decisão sobre `na_values` foi tomada a partir do
    arquivo, e não por hábito.
    """
    cru = pd.read_csv(config.ARQUIVO_BRUTO, sep="\t", keep_default_na=False, dtype=str)
    linhas = []
    for coluna in cru.columns:
        serie = cru[coluna]
        na_literal = int((serie == "NA").sum())
        none_literal = int((serie == "None").sum())
        vazio = int((serie == "").sum())
        if na_literal or none_literal or vazio:
            linhas.append(
                {
                    "coluna": coluna,
                    "NA_literal": na_literal,
                    "None_literal": none_literal,
                    "vazio": vazio,
                    "interpretacao": (
                        "categoria legítima ('sem revestimento')"
                        if none_literal
                        else "ausência estrutural ou faltante"
                    ),
                }
            )
    return pd.DataFrame(linhas).set_index("coluna").sort_values("NA_literal", ascending=False)


def baixar(forcar: bool = False) -> dict:
    """Baixa o arquivo bruto e grava o manifesto da carga.

    Args:
        forcar: quando ``True``, refaz o download mesmo que o arquivo exista.

    Returns:
        O manifesto da carga (origem, data, tamanho, hash, dimensões).
    """
    config.garantir_diretorios()

    if forcar or not config.ARQUIVO_BRUTO.exists():
        with urllib.request.urlopen(config.URL_AMES, timeout=120) as resposta:
            conteudo = resposta.read()
        config.ARQUIVO_BRUTO.write_bytes(conteudo)
    else:
        conteudo = config.ARQUIVO_BRUTO.read_bytes()

    dados = _ler_origem(config.ARQUIVO_BRUTO)

    # Conferência de carga: contagem contra o que a fonte declara.
    if dados.shape != (LINHAS_ESPERADAS, COLUNAS_ESPERADAS):
        raise ValueError(
            f"Dimensões inesperadas na origem: {dados.shape}, "
            f"esperado ({LINHAS_ESPERADAS}, {COLUNAS_ESPERADAS}). "
            "A fonte mudou — registre o fato antes de prosseguir."
        )

    # Cópia em parquet: a leitura passa de ~1 s para ~20 ms e o tipo das
    # colunas deixa de ser reinferido a cada execução.
    dados.to_parquet(config.ARQUIVO_BRUTO_PARQUET, index=False)

    manifesto = {
        "origem": config.URL_AMES,
        "referencia": (
            "De Cock, D. (2011). Ames, Iowa: Alternative to the Boston Housing Data "
            "as an End of Semester Regression Project. Journal of Statistics "
            "Education, 19(3)."
        ),
        "baixado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "bytes": len(conteudo),
        "sha256": hashlib.sha256(conteudo).hexdigest(),
        "linhas": int(dados.shape[0]),
        "colunas": int(dados.shape[1]),
        "periodo_venda": f"{int(dados['Yr Sold'].min())}–{int(dados['Yr Sold'].max())}",
        "licenca": "Uso educacional e de pesquisa, com citação do artigo original",
    }
    salvar_json(manifesto, config.DATA_RAW / "manifesto_carga.json")
    return manifesto


def carregar_bruto() -> pd.DataFrame:
    """Lê a camada bruta, baixando-a se necessário."""
    if not config.ARQUIVO_BRUTO_PARQUET.exists():
        baixar()
    return pd.read_parquet(config.ARQUIVO_BRUTO_PARQUET)


if __name__ == "__main__":
    info = baixar()
    print(f"Camada bruta materializada: {info['linhas']} × {info['colunas']}")
    print(f"Arquivo: {config.ARQUIVO_BRUTO}")
