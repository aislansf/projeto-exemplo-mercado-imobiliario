"""Testes da aplicação servida pelos artefatos dos notebooks.

O que precisa de teste aqui não é o agrupamento — é o **contrato entre os
notebooks e a tela**: o pré-processador reconstruído tem de ser o mesmo do 03, a
releitura do modelo tem de reproduzir a partição gravada pelo 04-0 e o imóvel
incompleto tem de ser completado sem virar zero silencioso. Um modelo que
classifica diferente fora do notebook é o modo de falha clássico da implantação.
"""

import numpy as np
import pandas as pd
import pytest

from src.app import artefatos as art

pytestmark = pytest.mark.skipif(
    bool(art.arquivos_ausentes()),
    reason="os artefatos ainda não foram gravados — execute `invoke notebooks`",
)


@pytest.fixture(scope="module")
def artefatos() -> art.Artefatos:
    """Os artefatos lidos uma vez para todos os testes do módulo."""
    return art.carregar()


# --------------------------------------------------------------------------- #
# Carga e coerência entre notebooks
# --------------------------------------------------------------------------- #


def test_preprocessamento_reconstruido_confere_com_o_03(artefatos):
    assert artefatos.confere_com_03
    assert len(artefatos.X) == len(artefatos.base) == len(artefatos.rotulos)


def test_modelo_relido_reproduz_os_segmentos_do_04_0(artefatos):
    if not artefatos.classifica_novos:
        pytest.skip("o modelo vencedor não tem predict")
    assert artefatos.concordancia == 1.0


def test_segmento_a_e_o_de_maior_preco_mediano(artefatos):
    perfil = art.perfil(artefatos)
    assert perfil.index[0] == "Segmento A"
    assert perfil["preco_mediano"].is_monotonic_decreasing
    assert perfil["pct_carteira"].sum() == pytest.approx(100)


def test_artefato_ausente_avisa_o_notebook_que_grava(monkeypatch):
    ausente = (art.config.MODELS / "nao-gravado.json", "04-0", True)
    monkeypatch.setitem(art.ARQUIVOS, "selecionado", ausente)
    assert art.arquivos_ausentes()[0][1] == "04-0"
    with pytest.raises(art.ArtefatosAusentes):
        art.carregar()


# --------------------------------------------------------------------------- #
# Imóveis novos
# --------------------------------------------------------------------------- #


def test_imovel_da_carteira_volta_para_o_proprio_segmento(artefatos):
    carteira = art.carteira(artefatos)
    for posicao in np.random.default_rng(42).choice(len(carteira), size=20, replace=False):
        imovel = artefatos.base.iloc[posicao][artefatos.colunas_de_entrada].to_dict()
        resultado = art.classificar(artefatos, imovel)
        assert resultado["segmento"] == carteira.iloc[posicao]["segmento"]
        assert resultado["completados"] == []


def test_campo_em_branco_e_completado_pelo_vizinho(artefatos):
    resultado = art.classificar(artefatos, {"area_habitavel": 1500, "bairro": None})
    assert resultado["informados"] == ["area_habitavel"]
    assert "bairro" in resultado["completados"]
    assert resultado["registro"]["area_habitavel"] == 1500
    assert resultado["vizinho"] in set(artefatos.base["pid"])
    assert resultado["segmento"] in artefatos.segmentos
    assert 0 < resultado["razao_de_fronteira"] <= 1
    assert resultado["segundo_mais_proximo"] != resultado["segmento"]


def test_categoria_desconhecida_e_recusada(artefatos):
    with pytest.raises(ValueError, match="não existe na base"):
        art.classificar(artefatos, {"bairro": "Bairro que não existe"})
    with pytest.raises(ValueError, match="fora da escala"):
        art.classificar(artefatos, {"qualidade_geral": 11})
    with pytest.raises(ValueError, match="não existem na base curada"):
        art.classificar(artefatos, {"coluna_inventada": 1})


def test_lote_reproduz_a_carteira(artefatos):
    obtido = art.classificar_lote(artefatos, artefatos.base)
    assert (obtido["segmento"] == art.carteira(artefatos)["segmento"]).all()
    assert (obtido["erro"] == "").all()


def test_lote_preserva_extras_e_isola_a_linha_com_erro(artefatos):
    entrada = pd.DataFrame(
        {
            "matricula": [1, 2, 3],
            "area_habitavel": [900.0, 2600.0, None],
            "bairro": ["Old Town", "Bairro que não existe", None],
        }
    )
    saida = art.classificar_lote(artefatos, entrada)
    assert list(saida["matricula"]) == [1, 2, 3]
    assert pd.isna(saida.loc[1, "segmento"]) and saida.loc[1, "erro"]
    assert set(saida.loc[[0, 2], "segmento"]) <= set(artefatos.segmentos)
