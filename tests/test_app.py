"""Testes da aplicação servida pelo pacote ``.pkl``.

O que precisa de teste aqui não é o K-Means — é o **contrato entre o pacote e a
tela**: o formato recusado quando não bate, o campo ausente completado pelo
contrato e, sobretudo, a promessa de que a releitura do artefato reproduz a
partição publicada. Um modelo que classifica diferente depois de serializado é o
modo de falha clássico da fase de implantação.
"""

import pickle

import pandas as pd
import pytest

from src.app import pacote as pac

pytestmark = pytest.mark.skipif(
    not pac.CAMINHO_PACOTE.exists(),
    reason="o pacote ainda não foi gravado — execute `invoke pipeline`",
)

BASE_DE_TREINO = pac.RAIZ / "data" / "processed" / "base_modelagem.parquet"


@pytest.fixture(scope="module")
def pacote() -> dict:
    """O pacote publicado, lido uma vez para todos os testes do módulo."""
    return pac.carregar()


# --------------------------------------------------------------------------- #
# Carga e validação do artefato
# --------------------------------------------------------------------------- #


def test_pacote_traz_tudo_que_a_tela_precisa(pacote):
    assert pacote["formato"] == pac.FORMATO_SUPORTADO
    for chave in pac.CHAVES_EXIGIDAS:
        assert chave in pacote
    assert len(pac.espaco(pacote)) == len(pacote["contrato"]["padroes"])
    assert set(pac.rotulos(pacote)) == set(pac.espaco(pacote))


def test_formato_desconhecido_e_recusado(tmp_path):
    """A tela não pode exibir número de um pacote que não sabe interpretar."""
    caminho = tmp_path / "outro-formato.pkl"
    caminho.write_bytes(pickle.dumps({"formato": "outra.coisa/9"}))
    with pytest.raises(pac.PacoteInvalido):
        pac.carregar(caminho)


def test_pacote_ausente_avisa_em_vez_de_estourar_generico(tmp_path):
    with pytest.raises(FileNotFoundError):
        pac.carregar(tmp_path / "nao-existe.pkl")


# --------------------------------------------------------------------------- #
# Preparo da entrada
# --------------------------------------------------------------------------- #


def test_registro_sai_na_ordem_do_treino_e_completa_o_que_falta(pacote):
    registro = pac.montar_registro({"area_habitavel": 1500}, pacote)
    assert list(registro.columns) == pac.espaco(pacote)
    assert registro.loc[0, "area_habitavel"] == 1500
    assert registro.loc[0, "idade_imovel"] == pac.padroes(pacote)["idade_imovel"]
    assert not registro.isna().to_numpy().any()


def test_campos_completados_denunciam_a_suposicao(pacote):
    completados = pac.campos_completados({"area_habitavel": 1500}, pacote)
    assert "area_habitavel" not in completados
    assert len(completados) == len(pac.espaco(pacote)) - 1


def test_valor_fora_da_faixa_aceita_vira_aviso(pacote):
    avisos = pac.conferir_contrato({"area_habitavel": 99_000}, pacote)
    assert avisos and "fora da faixa aceita" in avisos[0]
    assert pac.conferir_contrato({"area_habitavel": 1500}, pacote) == []


# --------------------------------------------------------------------------- #
# Classificação
# --------------------------------------------------------------------------- #


def test_perfil_mediano_de_cada_linha_volta_para_a_propria_linha(pacote):
    """O imóvel mediano de um segmento não pode cair em outro."""
    perfil = pacote["catalogo"]["perfil_por_linha"]
    for segmento in perfil.index:
        atributos = {campo: float(perfil.loc[segmento, campo]) for campo in pac.espaco(pacote)}
        resultado = pac.classificar(atributos, pacote)
        assert resultado["segmento"] == segmento
        assert resultado["confianca"] == "núcleo"


def test_faixa_de_confianca_respeita_os_cortes_calibrados(pacote):
    nucleo = pacote["atribuicao"]["corte_de_nucleo"]
    fronteira = pacote["atribuicao"]["corte_de_fronteira"]
    assert pac.faixa_de_confianca(nucleo - 0.01, pacote) == "núcleo"
    assert pac.faixa_de_confianca(nucleo, pacote) == "típico"
    assert pac.faixa_de_confianca(fronteira, pacote) == "fronteira"
    assert pac.faixa_de_confianca(1.0, pacote) == "fronteira"


def test_fronteira_bloqueia_a_acao_automatica(pacote):
    """A regra operacional que a tela promete: na fronteira, ninguém age sozinho."""
    perfil = pacote["catalogo"]["perfil_por_linha"]
    atributos = {campo: float(perfil.loc[0, campo]) for campo in pac.espaco(pacote)}
    resultado = pac.classificar(atributos, pacote)
    assert resultado["acao_automatica_liberada"] is (resultado["confianca"] != "fronteira")
    assert resultado["segundo_mais_proximo"] != resultado["codigo"]
    assert len(resultado["distancias"]) == pacote["modelo"]["k"]


def test_lote_completa_colunas_ausentes_e_preserva_as_extras(pacote):
    entrada = pd.DataFrame({"matricula": [1, 2], "area_habitavel": [900.0, 2600.0]})
    saida = pac.classificar_lote(entrada, pacote)
    assert list(saida["matricula"]) == [1, 2]
    assert set(saida["codigo_segmento"]) <= set(pac.linhas_de_produto(pacote)["codigo"])
    assert saida["razao_de_fronteira"].between(0, 1).all()


@pytest.mark.skipif(not BASE_DE_TREINO.exists(), reason="base de modelagem não materializada")
def test_releitura_do_pacote_reproduz_a_particao_publicada(pacote):
    """O critério de aceite da fase 6, verificado por teste em vez de por promessa."""
    base = pd.read_parquet(BASE_DE_TREINO)
    obtido = pac.classificar_lote(base, pacote).set_index(base["pid"])
    publicado = pac.carteira(pacote).set_index("pid")

    comum = obtido.index.intersection(publicado.index)
    assert len(comum) == len(publicado)
    assert (obtido.loc[comum, "segmento"] == publicado.loc[comum, "segmento"]).all()
    assert (obtido.loc[comum, "confianca"] == publicado.loc[comum, "confianca"]).all()
