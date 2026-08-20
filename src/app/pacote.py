"""Leitura do pacote publicado e classificação de imóveis.

Esta aplicação consome **um único arquivo**: ``models/aplicacao-segmentacao.pkl``.
O pacote foi gravado pela fase de implantação do CRISP-DM e carrega, junto, tudo
o que a tela precisa — o pipeline treinado, o contrato de entrada, o catálogo de
linhas de produto, a carteira já classificada e o plano de monitoramento. Não há
leitura de ``data/``, de ``reports/`` nem dos demais artefatos de ``models/``.

O motivo de o módulo existir é o de sempre: **a aplicação não reimplementa a
preparação**. O pré-processador que padroniza os atributos vem serializado dentro
do pacote, com as médias e os desvios do treino. Recalcular a padronização na
camada de tela é a forma mais comum de um modelo acertar no notebook e errar em
produção.

O roteiro de classificação é o declarado em ``pacote['leia_me']``:

1. completar o que faltar com ``contrato['padroes']``;
2. montar o registro com as colunas de ``modelo['espaco']``, nessa ordem;
3. transformar com ``modelo['pipeline'].named_steps['preparo']``;
4. medir a distância euclidiana até cada centroide — a razão entre a menor e a
   segunda menor é a **razão de fronteira**;
5. traduzir o rótulo cru do centroide mais próximo por ``modelo['mapa_canonico']``;
6. converter a razão em faixa de confiança pelos cortes calibrados.
"""

from __future__ import annotations

import pickle
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

#: Raiz do repositório — dois níveis acima de ``src/app/``.
RAIZ = Path(__file__).resolve().parents[2]

#: Pacote publicado pela fase 6 do CRISP-DM.
CAMINHO_PACOTE = RAIZ / "models" / "aplicacao-segmentacao.pkl"

#: Única versão de formato que esta tela sabe ler. Se o pacote for regravado com
#: outro contrato, a aplicação recusa a carga em vez de exibir número errado.
FORMATO_SUPORTADO = "meridiano.segmentacao/1"

#: Chaves obrigatórias no primeiro nível do pacote.
CHAVES_EXIGIDAS = (
    "formato",
    "versao_modelo",
    "modelo",
    "contrato",
    "atribuicao",
    "catalogo",
    "carteira",
    "monitoramento",
)


class PacoteInvalido(RuntimeError):
    """O arquivo existe, mas não é o pacote que esta aplicação sabe ler."""


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=2)
def carregar(caminho: str | Path | None = None) -> dict[str, Any]:
    """Lê o pacote do disco e confere o formato antes de devolvê-lo.

    Args:
        caminho: local do ``.pkl``. Quando omitido, usa :data:`CAMINHO_PACOTE`.

    Returns:
        O dicionário do pacote, exatamente como foi serializado.

    Raises:
        FileNotFoundError: o arquivo não existe — o pipeline ainda não rodou.
        PacoteInvalido: o arquivo existe, mas o formato ou as chaves não batem.
    """
    alvo = Path(caminho) if caminho else CAMINHO_PACOTE
    if not alvo.exists():
        raise FileNotFoundError(alvo)

    with alvo.open("rb") as arquivo:
        conteudo = pickle.load(arquivo)

    if not isinstance(conteudo, dict):
        raise PacoteInvalido(f"{alvo.name} não contém um dicionário de pacote.")

    formato = conteudo.get("formato")
    if formato != FORMATO_SUPORTADO:
        raise PacoteInvalido(
            f"Formato '{formato}' não suportado — esta tela lê '{FORMATO_SUPORTADO}'."
        )

    ausentes = [chave for chave in CHAVES_EXIGIDAS if chave not in conteudo]
    if ausentes:
        raise PacoteInvalido(f"Chaves ausentes no pacote: {', '.join(ausentes)}")

    return conteudo


# --------------------------------------------------------------------------- #
# Atalhos de leitura — para a tela não navegar o dicionário na mão
# --------------------------------------------------------------------------- #


def espaco(pacote: Mapping[str, Any]) -> list[str]:
    """Colunas que o pipeline espera, na ordem do treino."""
    return list(pacote["modelo"]["espaco"])


def rotulos(pacote: Mapping[str, Any]) -> dict[str, str]:
    """Nome de negócio de cada atributo — ``area_habitavel`` vira *Área habitável*."""
    return dict(pacote["modelo"]["rotulos_das_colunas"])


def padroes(pacote: Mapping[str, Any]) -> dict[str, float]:
    """Valor neutro de cada campo: a mediana da carteira de treino."""
    return {campo: float(valor) for campo, valor in pacote["contrato"]["padroes"].items()}


def campos(pacote: Mapping[str, Any]) -> pd.DataFrame:
    """Contrato de entrada: tipo, obrigatoriedade e faixas aceitas por campo."""
    return pacote["contrato"]["campos"].copy()


def linhas_de_produto(pacote: Mapping[str, Any]) -> pd.DataFrame:
    """Catálogo das linhas de produto, uma por segmento canônico."""
    return pacote["catalogo"]["linhas"].copy()


def persona(pacote: Mapping[str, Any], segmento: int) -> dict[str, Any]:
    """Ficha de negócio do segmento: retrato, política, ação, canal e métrica."""
    return dict(pacote["catalogo"]["personas"][int(segmento)])


def cores(pacote: Mapping[str, Any]) -> dict[int, str]:
    """Cor de cada segmento, a mesma da identidade visual do relatório."""
    return {int(segmento): cor for segmento, cor in pacote["catalogo"]["cores"].items()}


def carteira(pacote: Mapping[str, Any]) -> pd.DataFrame:
    """Os imóveis de treino já classificados, com faixa de confiança."""
    return pacote["carteira"].copy()


# --------------------------------------------------------------------------- #
# Preparo da entrada
# --------------------------------------------------------------------------- #


def montar_registro(atributos: Mapping[str, Any], pacote: Mapping[str, Any]) -> pd.DataFrame:
    """Monta a linha de entrada completando o que faltar com o padrão do contrato.

    Campo ausente, vazio ou não numérico cai no padrão declarado no pacote — a
    mediana da carteira de treino. A suposição fica visível na tela em vez de
    virar zero silencioso, que deslocaria o imóvel para outro segmento.
    """
    referencia = padroes(pacote)
    registro: dict[str, float] = {}
    for campo, padrao in referencia.items():
        bruto = atributos.get(campo)
        try:
            numero = float(bruto)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            numero = padrao
        registro[campo] = padrao if pd.isna(numero) else numero
    return pd.DataFrame([registro], dtype="float64")[espaco(pacote)]


def campos_completados(atributos: Mapping[str, Any], pacote: Mapping[str, Any]) -> list[str]:
    """Lista os campos que o usuário não informou e o contrato preencheu."""
    ausentes = []
    for campo in padroes(pacote):
        bruto = atributos.get(campo)
        if bruto is None or (isinstance(bruto, float) and pd.isna(bruto)):
            ausentes.append(campo)
    return ausentes


def conferir_contrato(atributos: Mapping[str, Any], pacote: Mapping[str, Any]) -> list[str]:
    """Confronta os valores informados com as faixas aceitas do contrato.

    Devolve avisos legíveis. Fora da faixa **observada** o modelo ainda
    classifica, mas extrapola; fora da faixa **aceita** — a observada mais 25% de
    folga — o registro deveria ser recusado já na carga.
    """
    avisos: list[str] = []
    tabela = campos(pacote).set_index("campo")
    for campo, bruto in atributos.items():
        if campo not in tabela.index or bruto is None:
            continue
        try:
            valor = float(bruto)
        except (TypeError, ValueError):
            continue
        linha = tabela.loc[campo]
        if valor < linha["aceito_minimo"] or valor > linha["aceito_maximo"]:
            avisos.append(
                f"**{linha['rotulo']}** = {valor:g} está fora da faixa aceita "
                f"({linha['aceito_minimo']:g} a {linha['aceito_maximo']:g}) — "
                "registro recusável na carga."
            )
        elif valor < linha["observado_minimo"] or valor > linha["observado_maximo"]:
            avisos.append(
                f"**{linha['rotulo']}** = {valor:g} está fora do observado no treino "
                f"({linha['observado_minimo']:g} a {linha['observado_maximo']:g}) — "
                "a classificação extrapola."
            )
    return avisos


# --------------------------------------------------------------------------- #
# Classificação
# --------------------------------------------------------------------------- #


def _transformar(registros: pd.DataFrame, pacote: Mapping[str, Any]) -> np.ndarray:
    """Aplica o pré-processador serializado — nunca uma reimplementação."""
    preparo = pacote["modelo"]["pipeline"].named_steps["preparo"]
    return np.asarray(preparo.transform(registros[espaco(pacote)]), dtype="float64")


def _distancias(matriz: np.ndarray, pacote: Mapping[str, Any]) -> np.ndarray:
    """Distância euclidiana de cada registro até cada centroide."""
    centroides = np.asarray(pacote["modelo"]["centroides"], dtype="float64")
    return np.linalg.norm(matriz[:, None, :] - centroides[None, :, :], axis=2)


def faixa_de_confianca(razao: float, pacote: Mapping[str, Any]) -> str:
    """Converte a razão de fronteira na faixa operacional calibrada."""
    if razao < pacote["atribuicao"]["corte_de_nucleo"]:
        return "núcleo"
    if razao < pacote["atribuicao"]["corte_de_fronteira"]:
        return "típico"
    return "fronteira"


def classificar(atributos: Mapping[str, Any], pacote: Mapping[str, Any]) -> dict[str, Any]:
    """Classifica um imóvel e devolve o resultado já traduzido para o negócio.

    A razão de fronteira é a distância ao centroide mais próximo dividida pela
    distância ao segundo mais próximo. Perto de 1, o imóvel está entre dois
    segmentos: a faixa vira ``fronteira`` e a ação automática **não** dispara,
    conforme a regra calibrada em ``atribuicao``.
    """
    registro = montar_registro(atributos, pacote)
    distancias = _distancias(_transformar(registro, pacote), pacote)[0]

    ordem = np.argsort(distancias)
    mapa = pacote["modelo"]["mapa_canonico"]
    segmento = int(mapa[int(ordem[0])])
    segundo = int(mapa[int(ordem[1])])
    razao = float(distancias[ordem[0]] / distancias[ordem[1]])
    faixa = faixa_de_confianca(razao, pacote)

    ficha = persona(pacote, segmento)
    return {
        "segmento": segmento,
        "codigo": ficha["codigo"],
        "persona": ficha["nome"],
        "cor": cores(pacote)[segmento],
        "ficha": ficha,
        "confianca": faixa,
        "razao_de_fronteira": round(razao, 4),
        "acao_automatica_liberada": faixa != "fronteira",
        "segundo_mais_proximo": persona(pacote, segundo)["codigo"],
        "distancias": {
            int(mapa[int(bruto)]): float(distancia) for bruto, distancia in enumerate(distancias)
        },
        "registro": registro.iloc[0].to_dict(),
        "campos_completados": campos_completados(atributos, pacote),
        "avisos": conferir_contrato(atributos, pacote),
        "versao_modelo": pacote["versao_modelo"],
    }


def classificar_lote(dados: pd.DataFrame, pacote: Mapping[str, Any]) -> pd.DataFrame:
    """Classifica um conjunto inteiro — o caminho usado a cada carga mensal.

    Colunas ausentes são completadas com o padrão do contrato; colunas extras são
    preservadas no resultado, mas não entram no cálculo.
    """
    referencia = padroes(pacote)
    entrada = pd.DataFrame(index=dados.index)
    for campo in espaco(pacote):
        if campo in dados.columns:
            valores = pd.to_numeric(dados[campo], errors="coerce").fillna(referencia[campo])
        else:
            valores = pd.Series(referencia[campo], index=dados.index)
        entrada[campo] = valores.astype("float64")

    distancias = _distancias(_transformar(entrada, pacote), pacote)
    ordenadas = np.sort(distancias, axis=1)
    razoes = np.divide(
        ordenadas[:, 0],
        ordenadas[:, 1],
        out=np.zeros(len(ordenadas)),
        where=ordenadas[:, 1] > 0,
    )

    mapa = pacote["modelo"]["mapa_canonico"]
    segmentos = [int(mapa[int(bruto)]) for bruto in np.argmin(distancias, axis=1)]
    faixas = [faixa_de_confianca(float(razao), pacote) for razao in razoes]
    catalogo = linhas_de_produto(pacote)

    return dados.assign(
        segmento=segmentos,
        codigo_segmento=[catalogo.loc[segmento, "codigo"] for segmento in segmentos],
        persona=[catalogo.loc[segmento, "nome"] for segmento in segmentos],
        razao_de_fronteira=np.round(razoes, 4),
        confianca=faixas,
        acao_automatica_liberada=[faixa != "fronteira" for faixa in faixas],
        versao_modelo=pacote["versao_modelo"],
    )
