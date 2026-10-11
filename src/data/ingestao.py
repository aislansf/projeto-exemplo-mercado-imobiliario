"""CRISP-DM 2.1 — Coleta dos dados iniciais.

Baixa a base Ames Housing do endereço oficial do artigo que a publicou e
materializa a camada bruta em ``data/raw/``. A operação é **idempotente**: se o
arquivo já existe e tem o tamanho esperado, o download não é refeito.

Dois arquivos, com papéis diferentes:

* ``ames_housing.txt`` — o arquivo **como a fonte o publica**, byte a byte. É a
  prova de origem, conferida pelo SHA-256 do manifesto, e nada o altera;
* ``ames_housing.parquet`` — a camada bruta que o projeto lê. Mesmas linhas,
  mesmas células, com as colunas renomeadas para `snake_case` em português e os
  códigos das categorias traduzidos (:data:`dic.TRADUCAO_CATEGORIAS`). Nenhum
  valor é corrigido, imputado ou removido aqui: isso é trabalho da curadoria.

A camada bruta é tratada como imutável — nenhuma outra parte do projeto escreve
em ``data/raw/``.
"""

from __future__ import annotations

import hashlib
import urllib.request
from datetime import UTC, datetime

import pandas as pd

from src import config
from src.data import dicionario as dic
from src.utils.io import ler_json, salvar_json

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


def ler_origem(caminho=None) -> pd.DataFrame:
    """Lê o arquivo da fonte, com os nomes e os códigos originais.

    Só as sentinelas declaradas viram nulo. É a leitura que a ingestão traduz e
    que a curadoria usa para provar que a tradução não mudou o dado.
    """
    caminho = caminho or config.ARQUIVO_BRUTO
    return pd.read_csv(caminho, sep="\t", keep_default_na=False, na_values=SENTINELAS)


def traduzir(dados: pd.DataFrame) -> pd.DataFrame:
    """Renomeia as colunas e troca os códigos das categorias pelo rótulo em português.

    Coluna sem nome curado ou código sem tradução interrompe a ingestão: um valor
    novo na origem precisa ganhar rótulo antes de chegar à camada bruta. O vazio
    não é código e passa intacto.
    """
    sem_nome = [coluna for coluna in dados.columns if coluna not in dic.RENOMEAR]
    if sem_nome:
        raise ValueError(f"colunas sem nome curado: {sem_nome}")

    traduzida = dados.rename(columns=dic.RENOMEAR)
    for coluna, mapa in dic.TRADUCAO_CATEGORIAS.items():
        if coluna not in traduzida.columns:
            continue
        sem_traducao = sorted(set(traduzida[coluna].dropna()) - set(mapa))
        if sem_traducao:
            raise ValueError(f"`{coluna}` tem códigos sem tradução: {sem_traducao}")
        traduzida[coluna] = traduzida[coluna].map(mapa)
    return traduzida


def inventario_sentinelas() -> pd.DataFrame:
    """Conta, coluna a coluna, as ocorrências literais de `NA`, `None` e vazio.

    É a evidência de que a decisão sobre `na_values` foi tomada a partir do
    arquivo, e não por hábito. A contagem é sobre o texto da fonte; o índice sai
    com o nome curado, e o original fica ao lado.
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
                    "coluna": dic.RENOMEAR[coluna],
                    "coluna_original": coluna,
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

    caminho_manifesto = config.DATA_RAW / "manifesto_carga.json"
    baixou = forcar or not config.ARQUIVO_BRUTO.exists()
    if baixou:
        with urllib.request.urlopen(config.URL_AMES, timeout=120) as resposta:
            conteudo = resposta.read()
        config.ARQUIVO_BRUTO.write_bytes(conteudo)
    else:
        conteudo = config.ARQUIVO_BRUTO.read_bytes()

    dados = ler_origem(config.ARQUIVO_BRUTO)

    # Conferência de carga: contagem contra o que a fonte declara.
    if dados.shape != (LINHAS_ESPERADAS, COLUNAS_ESPERADAS):
        raise ValueError(
            f"Dimensões inesperadas na origem: {dados.shape}, "
            f"esperado ({LINHAS_ESPERADAS}, {COLUNAS_ESPERADAS}). "
            "A fonte mudou — registre o fato antes de prosseguir."
        )

    # Camada bruta em parquet, já com nomes e categorias em português. A leitura
    # passa de ~1 s para ~20 ms e o tipo das colunas deixa de ser reinferido.
    dados = traduzir(dados)
    dados.to_parquet(config.ARQUIVO_BRUTO_PARQUET, index=False)

    # Sem download novo, a data da carga continua sendo a do download que houve.
    baixado_em = datetime.now(UTC).isoformat(timespec="seconds")
    if not baixou and caminho_manifesto.exists():
        baixado_em = ler_json(caminho_manifesto).get("baixado_em", baixado_em)

    manifesto = {
        "origem": config.URL_AMES,
        "referencia": (
            "De Cock, D. (2011). Ames, Iowa: Alternative to the Boston Housing Data "
            "as an End of Semester Regression Project. Journal of Statistics "
            "Education, 19(3)."
        ),
        "baixado_em": baixado_em,
        "bytes": len(conteudo),
        "sha256": hashlib.sha256(conteudo).hexdigest(),
        "linhas": int(dados.shape[0]),
        "colunas": int(dados.shape[1]),
        "periodo_venda": f"{int(dados['ano_venda'].min())}–{int(dados['ano_venda'].max())}",
        "licenca": "Uso educacional e de pesquisa, com citação do artigo original",
    }
    salvar_json(manifesto, caminho_manifesto)
    return manifesto


def carregar_bruto() -> pd.DataFrame:
    """Lê a camada bruta em português, materializando-a se necessário."""
    if not config.ARQUIVO_BRUTO_PARQUET.exists():
        baixar()
    return pd.read_parquet(config.ARQUIVO_BRUTO_PARQUET)


if __name__ == "__main__":
    info = baixar()
    print(f"Camada bruta materializada: {info['linhas']} × {info['colunas']}")
    print(f"Arquivo: {config.ARQUIVO_BRUTO}")
