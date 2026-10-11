"""Testes de fumaça: o pacote importa e as constantes do projeto estão coerentes."""

import src
from src import config
from src.data import dicionario as dic


def test_version_disponivel():
    assert src.__version__


def test_caminhos_apontam_para_dentro_do_projeto():
    assert config.RAIZ.exists()
    assert config.DATA.parent == config.RAIZ
    assert config.MODELS.parent == config.RAIZ


def test_restricoes_de_negocio_sao_coerentes():
    assert config.K_MINIMO_NEGOCIO < config.K_MAXIMO_NEGOCIO
    assert 0 < config.SILHUETA_MINIMA < 1
    assert 0 < config.RUIDO_MAXIMO < 1


def test_rotulo_reservado_fora_do_espaco_de_atributos():
    """O critério eliminatório da disciplina, verificado por teste."""
    espaco = set(dic.ESPACO_MISTO) | set(dic.BINARIAS) | set(dic.ESPACO_EUCLIDIANO)
    assert dic.ROTULO_RESERVADO not in espaco
    assert dic.RESERVADA_VALIDACAO not in espaco
    for coluna in dic.ATRIBUTOS_TRANSACAO:
        assert coluna not in espaco


def test_espacos_de_atributos_nao_tem_duplicata():
    assert len(dic.ESPACO_MISTO) == len(set(dic.ESPACO_MISTO))
    assert len(dic.ESPACO_EUCLIDIANO) == len(set(dic.ESPACO_EUCLIDIANO))
    assert not set(dic.NUMERICAS) & set(dic.NOMINAIS)
    assert not set(dic.ORDINAIS) & set(dic.NOMINAIS)


def test_toda_variavel_do_espaco_tem_descricao_e_rotulo():
    for coluna in dic.ESPACO_MISTO + dic.BINARIAS:
        assert coluna in dic.DESCRICOES, f"sem descrição: {coluna}"
        assert coluna in dic.ROTULOS_CURTOS, f"sem rótulo curto: {coluna}"


def test_assimetricas_sao_subconjunto_das_numericas():
    assert set(dic.ASSIMETRICAS) <= set(dic.NUMERICAS)


def test_traducao_cobre_as_nominais_e_nao_funde_categorias():
    """Toda nominal do espaço tem tradução, e códigos distintos não viram o mesmo rótulo.

    A exceção são as grafias diferentes do mesmo material nas duas colunas de
    revestimento, que nunca aparecem juntas na mesma coluna.
    """
    assert set(dic.NOMINAIS) <= set(dic.TRADUCAO_CATEGORIAS)
    sinonimos = {"Brk Cmn", "CmentBd", "Wd Shng"}
    for coluna, mapa in dic.TRADUCAO_CATEGORIAS.items():
        codigos = [c for c in mapa if c not in sinonimos]
        rotulos = [mapa[c] for c in codigos]
        assert len(set(rotulos)) == len(rotulos), coluna


def test_escalas_ordinais_usam_os_rotulos_da_traducao():
    """A curadoria mapeia para inteiro exatamente os rótulos que a ingestão grava."""
    for coluna, escala in dic.ESCALAS_ORDINAIS.items():
        assert set(escala) == set(dic.TRADUCAO_CATEGORIAS[coluna].values()), coluna
    rotulos = set(dic.RENOMEAR.values())
    assert set(dic.AUSENCIA_ESTRUTURAL) <= rotulos
    assert set(dic.AUSENCIA_DESCONHECIDA) <= rotulos
