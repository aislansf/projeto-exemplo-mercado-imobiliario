"""Dicionário de dados: nomes, tipos semânticos e escalas ordinais.

Este módulo é a **fonte única da verdade** sobre o significado de cada coluna.
A base original (Ames Housing, De Cock 2011) usa nomes em inglês com espaço no
meio (``Gr Liv Area``, ``Bsmt Qual``); a camada curada renomeia tudo para
`snake_case` em português, porque o resultado é lido por gente de negócio.

Três decisões registradas aqui, e não no código de análise:

1. **`preco_venda` é rótulo reservado.** Não entra em nenhuma etapa de
   modelagem — só na avaliação *a posteriori*. Usá-lo antes descaracterizaria o
   problema não supervisionado.
2. **`bairro` também fica de fora da modelagem.** Localização é o principal
   determinante de preço no mercado imobiliário: incluí-la faria o algoritmo
   redescobrir o preço por caminho indireto. Fica reservada para validação
   externa dos segmentos.
3. **Atributos da transação** (mês, ano, tipo e condição de venda) descrevem o
   *negócio*, não o *produto*. Ficam na base curada para a análise temporal,
   fora da matriz de modelagem.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Escalas ordinais declaradas na documentação original da base
# --------------------------------------------------------------------------- #

#: Escala de qualidade/condição usada em dez colunas da base.
#: Ausente (`NA`) significa "o item não existe no imóvel" — vira 0, não nulo.
ESCALA_QUALIDADE = {"Ex": 5, "Gd": 4, "TA": 3, "Fa": 2, "Po": 1}

ESCALAS_ORDINAIS: dict[str, dict[str, int]] = {
    "Exter Qual": ESCALA_QUALIDADE,
    "Exter Cond": ESCALA_QUALIDADE,
    "Bsmt Qual": ESCALA_QUALIDADE,
    "Bsmt Cond": ESCALA_QUALIDADE,
    "Heating QC": ESCALA_QUALIDADE,
    "Kitchen Qual": ESCALA_QUALIDADE,
    "Fireplace Qu": ESCALA_QUALIDADE,
    "Garage Qual": ESCALA_QUALIDADE,
    "Garage Cond": ESCALA_QUALIDADE,
    "Pool QC": ESCALA_QUALIDADE,
    "Bsmt Exposure": {"Gd": 4, "Av": 3, "Mn": 2, "No": 1},
    "BsmtFin Type 1": {"GLQ": 6, "ALQ": 5, "BLQ": 4, "Rec": 3, "LwQ": 2, "Unf": 1},
    "BsmtFin Type 2": {"GLQ": 6, "ALQ": 5, "BLQ": 4, "Rec": 3, "LwQ": 2, "Unf": 1},
    "Garage Finish": {"Fin": 3, "RFn": 2, "Unf": 1},
    "Functional": {
        "Typ": 8,
        "Min1": 7,
        "Min2": 6,
        "Mod": 5,
        "Maj1": 4,
        "Maj2": 3,
        "Sev": 2,
        "Sal": 1,
    },
    "Lot Shape": {"Reg": 4, "IR1": 3, "IR2": 2, "IR3": 1},
    "Land Slope": {"Gtl": 3, "Mod": 2, "Sev": 1},
    "Paved Drive": {"Y": 3, "P": 2, "N": 1},
    "Utilities": {"AllPub": 4, "NoSewr": 3, "NoSeWa": 2, "ELO": 1},
    "Fence": {"GdPrv": 4, "MnPrv": 3, "GdWo": 2, "MnWw": 1},
}

#: Colunas em que `NA` significa ausência do item (porão, garagem, lareira,
#: piscina, cerca, viela) e **não** informação faltante. Tratá-las como nulo e
#: imputar pela mediana inventaria porões que não existem.
AUSENCIA_ESTRUTURAL = {
    "Alley": "SemViela",
    "Bsmt Qual": "SemPorao",
    "Bsmt Cond": "SemPorao",
    "Bsmt Exposure": "SemPorao",
    "BsmtFin Type 1": "SemPorao",
    "BsmtFin Type 2": "SemPorao",
    "Fireplace Qu": "SemLareira",
    "Garage Type": "SemGaragem",
    "Garage Finish": "SemGaragem",
    "Garage Qual": "SemGaragem",
    "Garage Cond": "SemGaragem",
    "Pool QC": "SemPiscina",
    "Fence": "SemCerca",
    "Misc Feature": "SemExtra",
}

#: Ausências que **não** são estruturais e não podem ser lidas como "não tem".
#: `Mas Vnr Type` tem 1.752 registros com a categoria legítima `None` (sem
#: revestimento em alvenaria aparente) e apenas 23 realmente em branco.
AUSENCIA_DESCONHECIDA = {"Mas Vnr Type": "NaoInformado"}

# --------------------------------------------------------------------------- #
# Renomeação para a camada curada
# --------------------------------------------------------------------------- #

RENOMEAR: dict[str, str] = {
    "Order": "ordem",
    "PID": "pid",
    "MS SubClass": "subclasse",
    "MS Zoning": "zoneamento",
    "Lot Frontage": "testada_lote",
    "Lot Area": "area_terreno",
    "Street": "tipo_via",
    "Alley": "tipo_viela",
    "Lot Shape": "formato_lote",
    "Land Contour": "relevo",
    "Utilities": "infraestrutura",
    "Lot Config": "config_lote",
    "Land Slope": "declividade",
    "Neighborhood": "bairro",
    "Condition 1": "condicao_entorno_1",
    "Condition 2": "condicao_entorno_2",
    "Bldg Type": "tipo_construcao",
    "House Style": "estilo",
    "Overall Qual": "qualidade_geral",
    "Overall Cond": "conservacao_geral",
    "Year Built": "ano_construcao",
    "Year Remod/Add": "ano_reforma",
    "Roof Style": "estilo_telhado",
    "Roof Matl": "material_telhado",
    "Exterior 1st": "revestimento_1",
    "Exterior 2nd": "revestimento_2",
    "Mas Vnr Type": "tipo_alvenaria_aparente",
    "Mas Vnr Area": "area_alvenaria_aparente",
    "Exter Qual": "qualidade_externa",
    "Exter Cond": "conservacao_externa",
    "Foundation": "fundacao",
    "Bsmt Qual": "qualidade_porao",
    "Bsmt Cond": "conservacao_porao",
    "Bsmt Exposure": "exposicao_porao",
    "BsmtFin Type 1": "acabamento_porao_1",
    "BsmtFin SF 1": "area_porao_acabada_1",
    "BsmtFin Type 2": "acabamento_porao_2",
    "BsmtFin SF 2": "area_porao_acabada_2",
    "Bsmt Unf SF": "area_porao_bruta",
    "Total Bsmt SF": "area_porao",
    "Heating": "aquecimento",
    "Heating QC": "qualidade_aquecimento",
    "Central Air": "ar_central",
    "Electrical": "sistema_eletrico",
    "1st Flr SF": "area_terreo",
    "2nd Flr SF": "area_pavimento_superior",
    "Low Qual Fin SF": "area_acabamento_inferior",
    "Gr Liv Area": "area_habitavel",
    "Bsmt Full Bath": "banheiros_completos_porao",
    "Bsmt Half Bath": "lavabos_porao",
    "Full Bath": "banheiros_completos",
    "Half Bath": "lavabos",
    "Bedroom AbvGr": "dormitorios",
    "Kitchen AbvGr": "cozinhas",
    "Kitchen Qual": "qualidade_cozinha",
    "TotRms AbvGrd": "comodos",
    "Functional": "funcionalidade",
    "Fireplaces": "lareiras",
    "Fireplace Qu": "qualidade_lareira",
    "Garage Type": "tipo_garagem",
    "Garage Yr Blt": "ano_garagem",
    "Garage Finish": "acabamento_garagem",
    "Garage Cars": "vagas_garagem",
    "Garage Area": "area_garagem",
    "Garage Qual": "qualidade_garagem",
    "Garage Cond": "conservacao_garagem",
    "Paved Drive": "acesso_pavimentado",
    "Wood Deck SF": "area_deck",
    "Open Porch SF": "area_varanda_aberta",
    "Enclosed Porch": "area_varanda_fechada",
    "3Ssn Porch": "area_varanda_3estacoes",
    "Screen Porch": "area_varanda_tela",
    "Pool Area": "area_piscina",
    "Pool QC": "qualidade_piscina",
    "Fence": "tipo_cerca",
    "Misc Feature": "item_extra",
    "Misc Val": "valor_item_extra",
    "Mo Sold": "mes_venda",
    "Yr Sold": "ano_venda",
    "Sale Type": "tipo_venda",
    "Sale Condition": "condicao_venda",
    "SalePrice": "preco_venda",
}

# --------------------------------------------------------------------------- #
# Papel de cada coluna no projeto
# --------------------------------------------------------------------------- #

#: Rótulo reservado. Uso exclusivo na avaliação a posteriori.
ROTULO_RESERVADO = "preco_venda"

#: Reservada para validação externa: não entra na modelagem (proxy de preço).
RESERVADA_VALIDACAO = "bairro"

#: Identificadores.
IDENTIFICADORES = ["ordem", "pid"]

#: Atributos da transação, não do produto.
ATRIBUTOS_TRANSACAO = ["mes_venda", "ano_venda", "tipo_venda", "condicao_venda"]

# --------------------------------------------------------------------------- #
# Espaço de atributos da modelagem
# --------------------------------------------------------------------------- #

#: Numéricas contínuas e discretas. Descrevem tamanho, idade e contagem.
NUMERICAS = [
    "area_habitavel",
    "area_porao",
    "area_terreno",
    "area_garagem",
    "area_varandas",
    "banheiros_total",
    "comodos",
    "dormitorios",
    "lareiras",
    "idade_imovel",
    "anos_desde_reforma",
]

#: Ordinais: escala com ordem semântica, tratadas como numéricas após o mapa.
ORDINAIS = [
    "qualidade_geral",
    "conservacao_geral",
    "qualidade_externa",
    "qualidade_cozinha",
    "qualidade_porao",
    "acabamento_garagem",
]

#: Nominais: sem ordem. Entram por Gower ou por *one-hot*, nunca como inteiro.
NOMINAIS = [
    "zoneamento",
    "tipo_construcao",
    "estilo",
    "tipo_garagem",
    "ar_central",
]

#: Binárias derivadas, usadas no espaço euclidiano enxuto.
BINARIAS = ["tem_porao", "tem_garagem", "tem_lareira", "tem_segundo_pavimento"]

#: As três leituras do espaço de atributos comparadas no projeto.
ESPACO_NUMERICO = NUMERICAS + ORDINAIS
ESPACO_EUCLIDIANO = NUMERICAS + ORDINAIS + BINARIAS
ESPACO_MISTO = NUMERICAS + ORDINAIS + NOMINAIS

#: Limiar de assimetria a partir do qual a transformação se justifica. O valor
#: 0,75 é a convenção usual; abaixo dele o ganho não compensa a perda de
#: legibilidade da unidade original.
LIMIAR_ASSIMETRIA = 0.75

#: Variáveis cuja assimetria medida na 2ª fase da EDA supera o limiar e que,
#: por isso, recebem `log1p` antes da padronização.
#: Medições: área do terreno 13,20 · varandas 1,36 · área habitável 0,88.
#: A área do porão ficou de fora (0,40) — transformá-la seria hábito, não decisão.
ASSIMETRICAS = ["area_terreno", "area_varandas", "area_habitavel"]

# --------------------------------------------------------------------------- #
# Descrição de negócio, para o dicionário publicado e para a aplicação
# --------------------------------------------------------------------------- #

DESCRICOES: dict[str, str] = {
    "area_habitavel": "Área construída acima do solo, em pés quadrados",
    "area_porao": "Área total do porão, em pés quadrados (0 = sem porão)",
    "area_terreno": "Área do lote, em pés quadrados",
    "area_garagem": "Área da garagem, em pés quadrados (0 = sem garagem)",
    "area_varandas": "Soma de deck, varandas aberta, fechada, de tela e de três estações",
    "banheiros_total": "Banheiros equivalentes: completos + metade dos lavabos, incluindo porão",
    "comodos": "Cômodos acima do solo, exceto banheiros",
    "dormitorios": "Dormitórios acima do solo",
    "lareiras": "Número de lareiras",
    "idade_imovel": "Anos entre a construção e a venda",
    "anos_desde_reforma": "Anos entre a última reforma (ou a construção) e a venda",
    "qualidade_geral": "Qualidade geral de material e acabamento (1 a 10)",
    "conservacao_geral": "Estado geral de conservação (1 a 10)",
    "qualidade_externa": "Qualidade do revestimento externo (0 a 5)",
    "qualidade_cozinha": "Qualidade da cozinha (0 a 5)",
    "qualidade_porao": "Altura e qualidade do porão (0 = sem porão, 5 = excelente)",
    "acabamento_garagem": "Acabamento interno da garagem (0 = sem garagem, 3 = acabada)",
    "zoneamento": "Classificação de zoneamento urbano",
    "tipo_construcao": "Tipo de construção (isolada, geminada, sobreposta)",
    "estilo": "Estilo e número de pavimentos",
    "tipo_garagem": "Posição da garagem em relação à casa",
    "ar_central": "Possui ar-condicionado central",
    "tem_porao": "Possui porão",
    "tem_garagem": "Possui garagem",
    "tem_lareira": "Possui ao menos uma lareira",
    "tem_segundo_pavimento": "Possui pavimento superior",
    "bairro": "Bairro de Ames (reservado para validação externa)",
    "preco_venda": "Preço de venda em dólares (rótulo reservado)",
    "ano_venda": "Ano da transação",
    "mes_venda": "Mês da transação",
    "tipo_venda": "Modalidade da venda",
    "condicao_venda": "Condição da venda (normal, parcial, familiar, execução…)",
}

#: Rótulos curtos para gráficos e para a aplicação.
ROTULOS_CURTOS: dict[str, str] = {
    "area_habitavel": "Área habitável",
    "area_porao": "Área do porão",
    "area_terreno": "Área do terreno",
    "area_garagem": "Área da garagem",
    "area_varandas": "Área de varandas",
    "banheiros_total": "Banheiros",
    "comodos": "Cômodos",
    "dormitorios": "Dormitórios",
    "lareiras": "Lareiras",
    "idade_imovel": "Idade do imóvel",
    "anos_desde_reforma": "Anos desde a reforma",
    "qualidade_geral": "Qualidade geral",
    "conservacao_geral": "Conservação",
    "qualidade_externa": "Qualidade externa",
    "qualidade_cozinha": "Qualidade da cozinha",
    "qualidade_porao": "Qualidade do porão",
    "acabamento_garagem": "Acabamento da garagem",
    "zoneamento": "Zoneamento",
    "tipo_construcao": "Tipo de construção",
    "estilo": "Estilo",
    "tipo_garagem": "Tipo de garagem",
    "ar_central": "Ar central",
    "tem_porao": "Tem porão",
    "tem_garagem": "Tem garagem",
    "tem_lareira": "Tem lareira",
    "tem_segundo_pavimento": "Tem 2º pavimento",
}


def rotulo(coluna: str) -> str:
    """Devolve o rótulo curto de uma coluna, ou o próprio nome se não houver."""
    return ROTULOS_CURTOS.get(coluna, coluna.replace("_", " ").capitalize())
