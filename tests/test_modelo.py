"""Testes das implementações próprias e das propriedades que o projeto promete.

Três algoritmos deste repositório não vêm prontos nas bibliotecas — Gower, K-Medoids e
Eclat. São eles que precisam de teste: o resto é `scikit-learn`, que já tem os seus.
"""

import numpy as np
import pandas as pd
import pytest

from src.data import ingestao
from src.model import associacao as assoc
from src.model import distancias as dist
from src.model import particional as part
from src.model import personas as pers


@pytest.fixture
def dados_mistos() -> pd.DataFrame:
    """Um conjunto pequeno, com estrutura conhecida, para testar as propriedades."""
    gerador = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "area": np.concatenate([gerador.normal(100, 8, 40), gerador.normal(300, 8, 40)]),
            "idade": np.concatenate([gerador.normal(50, 4, 40), gerador.normal(5, 2, 40)]),
            "tipo": ["A"] * 40 + ["B"] * 40,
        }
    )


# --------------------------------------------------------------------------- #
# Gower
# --------------------------------------------------------------------------- #


def test_gower_e_simetrica_com_diagonal_zero(dados_mistos):
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    assert matriz.shape == (80, 80)
    assert np.allclose(matriz, matriz.T)
    assert np.allclose(np.diag(matriz), 0)


def test_gower_fica_no_intervalo_unitario(dados_mistos):
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    assert matriz.min() >= 0.0
    assert matriz.max() <= 1.0


def test_gower_separa_os_dois_grupos(dados_mistos):
    """A distância dentro do grupo deve ser menor que a distância entre grupos."""
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    dentro = matriz[:40, :40][np.triu_indices(40, k=1)].mean()
    entre = matriz[:40, 40:].mean()
    assert dentro < entre


def test_gower_ignora_variavel_constante():
    """Variável sem variância não contribui — e não divide por zero."""
    dados = pd.DataFrame({"a": [1.0, 2.0, 3.0], "constante": [5.0, 5.0, 5.0], "t": ["x", "y", "x"]})
    matriz = dist.gower(dados, ["a", "constante"], ["t"])
    assert np.isfinite(matriz).all()


def test_gower_exige_alguma_variavel_com_variancia():
    dados = pd.DataFrame({"constante": [5.0, 5.0, 5.0]})
    with pytest.raises(ValueError):
        dist.gower(dados, ["constante"], [])


# --------------------------------------------------------------------------- #
# K-Medoids
# --------------------------------------------------------------------------- #


def test_kmedoids_recupera_estrutura_conhecida(dados_mistos):
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    resultado = part.kmedoids(matriz, k=2, reinicios=5, semente=7)
    assert len(np.unique(resultado.rotulos)) == 2
    # Os 40 primeiros registros formam um grupo; os 40 últimos, outro.
    assert len(np.unique(resultado.rotulos[:40])) == 1
    assert len(np.unique(resultado.rotulos[40:])) == 1


def test_kmedoids_medoides_sao_registros_reais(dados_mistos):
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    resultado = part.kmedoids(matriz, k=3, reinicios=5, semente=7)
    assert len(resultado.medoides) == 3
    assert all(0 <= indice < len(dados_mistos) for indice in resultado.medoides)
    assert len(set(resultado.medoides)) == 3


def test_kmedoids_custo_nao_aumenta_ao_longo_das_iteracoes(dados_mistos):
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    resultado = part.kmedoids(matriz, k=2, reinicios=1, semente=7)
    historico = resultado.historico_custo
    assert all(b <= a + 1e-9 for a, b in zip(historico, historico[1:], strict=False))


def test_kmedoids_e_reprodutivel(dados_mistos):
    matriz = dist.gower(dados_mistos, ["area", "idade"], ["tipo"])
    primeiro = part.kmedoids(matriz, k=3, reinicios=4, semente=42)
    segundo = part.kmedoids(matriz, k=3, reinicios=4, semente=42)
    assert np.array_equal(primeiro.rotulos, segundo.rotulos)


# --------------------------------------------------------------------------- #
# Escolha de k
# --------------------------------------------------------------------------- #


def test_cotovelo_encontra_o_joelho():
    """Curva com joelho evidente em k=4."""
    inercias = pd.Series([100, 60, 35, 20, 18, 17, 16.5], index=range(2, 9))
    assert part.cotovelo(inercias) in (4, 5)


# --------------------------------------------------------------------------- #
# Eclat
# --------------------------------------------------------------------------- #


@pytest.fixture
def transacoes() -> pd.DataFrame:
    """Cesta clássica, com suportes conhecidos de cabeça."""
    dados = [
        {"pao": 1, "leite": 1, "cafe": 0},
        {"pao": 1, "leite": 1, "cafe": 1},
        {"pao": 1, "leite": 0, "cafe": 1},
        {"pao": 0, "leite": 1, "cafe": 1},
        {"pao": 1, "leite": 1, "cafe": 1},
    ]
    return pd.DataFrame(dados).astype(bool)


def test_eclat_calcula_suportes_corretos(transacoes):
    frequentes = assoc.eclat(transacoes, suporte_minimo=0.2, max_tamanho=3)
    suportes = {
        frozenset(c): s for c, s in zip(frequentes["itemsets"], frequentes["support"], strict=True)
    }
    assert suportes[frozenset({"pao"})] == pytest.approx(4 / 5)
    assert suportes[frozenset({"leite"})] == pytest.approx(4 / 5)
    assert suportes[frozenset({"pao", "leite"})] == pytest.approx(3 / 5)
    assert suportes[frozenset({"pao", "leite", "cafe"})] == pytest.approx(2 / 5)


def test_eclat_respeita_o_suporte_minimo(transacoes):
    frequentes = assoc.eclat(transacoes, suporte_minimo=0.7, max_tamanho=3)
    assert (frequentes["support"] >= 0.7).all()


def test_eclat_concorda_com_apriori(transacoes):
    """A promessa central da fase 4: os três algoritmos dão o mesmo resultado."""
    from mlxtend.frequent_patterns import apriori

    do_eclat = {frozenset(c) for c in assoc.eclat(transacoes, 0.2, 3)["itemsets"]}
    do_apriori = {
        frozenset(c)
        for c in apriori(transacoes, min_support=0.2, use_colnames=True, max_len=3)["itemsets"]
    }
    assert do_eclat == do_apriori


def test_eclat_respeita_o_tamanho_maximo(transacoes):
    frequentes = assoc.eclat(transacoes, suporte_minimo=0.2, max_tamanho=2)
    assert frequentes["itemsets"].apply(len).max() <= 2


# --------------------------------------------------------------------------- #
# Poda de regras
# --------------------------------------------------------------------------- #


def test_remove_tautologias_semanticas():
    regras = pd.DataFrame(
        {
            "antecedents": [frozenset({"tem_2º_pavimento:sim"}), frozenset({"qualidade:alta"})],
            "consequents": [frozenset({"estilo:2Story"}), frozenset({"cozinha:superior"})],
            "lift": [3.03, 2.14],
            "support": [0.11, 0.14],
            "confidence": [0.90, 0.86],
            "antecedentes": ["tem_2º_pavimento:sim", "qualidade:alta"],
            "consequentes": ["estilo:2Story", "cozinha:superior"],
        }
    )
    mantidas, descartadas = assoc.remover_tautologias(regras)
    assert len(mantidas) == 1
    assert len(descartadas) == 1
    assert "estilo:2Story" in descartadas.iloc[0]["consequentes"]


# --------------------------------------------------------------------------- #
# Ordenação canônica dos segmentos
# --------------------------------------------------------------------------- #


def test_ordenacao_canonica_e_estavel_a_permutacao():
    """Trocar o número dos grupos não pode mudar a persona atribuída."""
    curada = pd.DataFrame(
        {
            "qualidade_geral": [4] * 10 + [6] * 10 + [8] * 10,
            "area_habitavel": [900] * 10 + [1500] * 10 + [2200] * 10,
        }
    )
    original = np.array([0] * 10 + [1] * 10 + [2] * 10)
    permutado = np.array([2] * 10 + [0] * 10 + [1] * 10)

    assert np.array_equal(
        pers.ordenar_canonicamente(curada, original),
        pers.ordenar_canonicamente(curada, permutado),
    )


def test_ordenacao_canonica_poe_o_padrao_mais_baixo_em_zero():
    curada = pd.DataFrame(
        {
            "qualidade_geral": [8] * 5 + [4] * 5,
            "area_habitavel": [2200] * 5 + [900] * 5,
        }
    )
    canonico = pers.ordenar_canonicamente(curada, np.array([0] * 5 + [1] * 5))
    assert canonico[0] == 1  # o grupo de qualidade 8 vira o último
    assert canonico[-1] == 0  # o de qualidade 4 vira o primeiro


def test_toda_persona_tem_acao_e_metrica():
    """Sem os três — nome, ação e métrica — o agrupamento não vira decisão."""
    for indice, persona in pers.PERSONAS.items():
        assert persona["nome"]
        assert persona["acao"]
        assert persona["metrica"]
        assert persona["codigo"] == f"S{indice + 1}"


# --------------------------------------------------------------------------- #
# Tradução na ingestão
# --------------------------------------------------------------------------- #


def test_traducao_renomeia_e_preserva_as_categorias():
    origem = pd.DataFrame(
        {
            "Central Air": ["Y", "N", "Y", None],
            "Garage Type": ["Attchd", None, "Detchd", "Attchd"],
            "Kitchen Qual": ["Gd", "TA", "Ex", "Fa"],
            "Gr Liv Area": [1000, 1200, 900, 1500],
        }
    )
    traduzida = ingestao.traduzir(origem)
    assert list(traduzida.columns) == [
        "ar_central",
        "tipo_garagem",
        "qualidade_cozinha",
        "area_habitavel",
    ]
    assert traduzida["ar_central"].tolist()[:3] == ["Sim", "Não", "Sim"]
    assert traduzida["ar_central"].isna().iloc[3]
    # O vazio não é código: vira rótulo de ausência só na curadoria.
    assert traduzida["tipo_garagem"].isna().iloc[1]
    assert traduzida["qualidade_cozinha"].tolist() == ["Bom", "Típico", "Excelente", "Regular"]
    assert traduzida["area_habitavel"].equals(origem["Gr Liv Area"])


def test_traducao_recusa_codigo_desconhecido():
    with pytest.raises(ValueError, match="sem tradução"):
        ingestao.traduzir(pd.DataFrame({"MS Zoning": ["RL", "XYZ"]}))


def test_traducao_recusa_coluna_sem_nome_curado():
    with pytest.raises(ValueError, match="sem nome curado"):
        ingestao.traduzir(pd.DataFrame({"Coluna Nova": [1]}))
