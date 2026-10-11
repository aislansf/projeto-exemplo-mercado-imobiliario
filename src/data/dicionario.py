"""Dicionário de dados: nomes, tipos semânticos e escalas ordinais.

Este módulo é a **fonte única da verdade** sobre o significado de cada coluna.
A base original (Ames Housing, De Cock 2011) usa nomes em inglês com espaço no
meio (``Gr Liv Area``, ``Bsmt Qual``) e categorias em código (``RL``, ``1Fam``,
``Ex``). A ingestão renomeia as colunas para `snake_case` em português e traduz
as categorias já na camada bruta, porque o resultado é lido por gente de
negócio. O arquivo de texto baixado continua intocado em ``data/raw/``.

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

#: Cada nível ordinal: código da origem → (rótulo em português, posição na escala).
#: O código só existe no arquivo baixado; da ingestão em diante vale o rótulo.
_QUALIDADE = {
    "Ex": ("Excelente", 5),
    "Gd": ("Bom", 4),
    "TA": ("Típico", 3),
    "Fa": ("Regular", 2),
    "Po": ("Ruim", 1),
}
_ACABAMENTO_PORAO = {
    "GLQ": ("Habitável, bom padrão", 6),
    "ALQ": ("Habitável, padrão médio", 5),
    "BLQ": ("Habitável, abaixo do padrão", 4),
    "Rec": ("Recreação", 3),
    "LwQ": ("Baixa qualidade", 2),
    "Unf": ("Sem acabamento", 1),
}

_NIVEIS_ORDINAIS: dict[str, dict[str, tuple[str, int]]] = {
    "qualidade_externa": _QUALIDADE,
    "conservacao_externa": _QUALIDADE,
    "qualidade_porao": _QUALIDADE,
    "conservacao_porao": _QUALIDADE,
    "qualidade_aquecimento": _QUALIDADE,
    "qualidade_cozinha": _QUALIDADE,
    "qualidade_lareira": _QUALIDADE,
    "qualidade_garagem": _QUALIDADE,
    "conservacao_garagem": _QUALIDADE,
    "qualidade_piscina": _QUALIDADE,
    "exposicao_porao": {
        "Gd": ("Boa", 4),
        "Av": ("Média", 3),
        "Mn": ("Mínima", 2),
        "No": ("Nenhuma", 1),
    },
    "acabamento_porao_1": _ACABAMENTO_PORAO,
    "acabamento_porao_2": _ACABAMENTO_PORAO,
    "acabamento_garagem": {
        "Fin": ("Acabada", 3),
        "RFn": ("Parcialmente acabada", 2),
        "Unf": ("Sem acabamento", 1),
    },
    "funcionalidade": {
        "Typ": ("Típica", 8),
        "Min1": ("Dedução mínima 1", 7),
        "Min2": ("Dedução mínima 2", 6),
        "Mod": ("Dedução moderada", 5),
        "Maj1": ("Dedução grave 1", 4),
        "Maj2": ("Dedução grave 2", 3),
        "Sev": ("Muito comprometida", 2),
        "Sal": ("Só para aproveitamento", 1),
    },
    "formato_lote": {
        "Reg": ("Regular", 4),
        "IR1": ("Levemente irregular", 3),
        "IR2": ("Moderadamente irregular", 2),
        "IR3": ("Irregular", 1),
    },
    "declividade": {
        "Gtl": ("Suave", 3),
        "Mod": ("Moderada", 2),
        "Sev": ("Acentuada", 1),
    },
    "acesso_pavimentado": {
        "Y": ("Pavimentado", 3),
        "P": ("Parcialmente pavimentado", 2),
        "N": ("Terra ou cascalho", 1),
    },
    "infraestrutura": {
        "AllPub": ("Todos os serviços", 4),
        "NoSewr": ("Sem esgoto", 3),
        "NoSeWa": ("Só eletricidade e gás", 2),
        "ELO": ("Só eletricidade", 1),
    },
    "tipo_cerca": {
        "GdPrv": ("Boa privacidade", 4),
        "MnPrv": ("Privacidade mínima", 3),
        "GdWo": ("Boa madeira", 2),
        "MnWw": ("Madeira ou arame mínimo", 1),
    },
}

#: Escala de qualidade/condição usada em dez colunas da base.
#: Ausente (`NA`) significa "o item não existe no imóvel" — vira 0, não nulo.
ESCALA_QUALIDADE = dict(_QUALIDADE.values())

#: Rótulo em português → posição na escala, por coluna ordinal.
ESCALAS_ORDINAIS: dict[str, dict[str, int]] = {
    coluna: dict(niveis.values()) for coluna, niveis in _NIVEIS_ORDINAIS.items()
}

#: Colunas em que `NA` significa ausência do item (porão, garagem, lareira,
#: piscina, cerca, viela) e **não** informação faltante. Tratá-las como nulo e
#: imputar pela mediana inventaria porões que não existem.
AUSENCIA_ESTRUTURAL = {
    "tipo_viela": "Sem viela",
    "qualidade_porao": "Sem porão",
    "conservacao_porao": "Sem porão",
    "exposicao_porao": "Sem porão",
    "acabamento_porao_1": "Sem porão",
    "acabamento_porao_2": "Sem porão",
    "qualidade_lareira": "Sem lareira",
    "tipo_garagem": "Sem garagem",
    "acabamento_garagem": "Sem garagem",
    "qualidade_garagem": "Sem garagem",
    "conservacao_garagem": "Sem garagem",
    "qualidade_piscina": "Sem piscina",
    "tipo_cerca": "Sem cerca",
    "item_extra": "Sem item extra",
}

#: Ausências que **não** são estruturais e não podem ser lidas como "não tem".
#: `tipo_alvenaria_aparente` tem 1.752 registros com a categoria legítima
#: `Sem alvenaria aparente` (a palavra `None` na origem) e apenas 23 realmente
#: em branco.
AUSENCIA_DESCONHECIDA = {"tipo_alvenaria_aparente": "Não informado"}

# --------------------------------------------------------------------------- #
# Renomeação, aplicada na ingestão
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
# Tradução das categorias, aplicada na ingestão
# --------------------------------------------------------------------------- #

#: Rótulos compartilhados por mais de uma coluna.
_PAVIMENTO = {"Grvl": "Cascalho", "Pave": "Pavimentada"}

_ENTORNO = {
    "Norm": "Normal",
    "Artery": "Junto a via arterial",
    "Feedr": "Junto a via coletora",
    "RRNn": "Até 200 pés da ferrovia norte-sul",
    "RRAn": "Vizinho à ferrovia norte-sul",
    "RRNe": "Até 200 pés da ferrovia leste-oeste",
    "RRAe": "Vizinho à ferrovia leste-oeste",
    "PosN": "Próximo a área verde",
    "PosA": "Vizinho a área verde",
}

#: As duas colunas de revestimento grafam o mesmo material de formas diferentes
#: na origem (`CemntBd` × `CmentBd`, `WdShing` × `Wd Shng`, `BrkComm` ×
#: `Brk Cmn`). A tradução unifica a grafia: o material é um só.
_REVESTIMENTO = {
    "AsbShng": "Placas de amianto",
    "AsphShn": "Placas asfálticas",
    "BrkComm": "Tijolo comum",
    "Brk Cmn": "Tijolo comum",
    "BrkFace": "Tijolo aparente",
    "CBlock": "Bloco de concreto",
    "CemntBd": "Placa cimentícia",
    "CmentBd": "Placa cimentícia",
    "HdBoard": "Chapa de fibra",
    "ImStucc": "Estuque imitação",
    "MetalSd": "Metálico",
    "Other": "Outro",
    "Plywood": "Compensado",
    "PreCast": "Pré-moldado",
    "Stone": "Pedra",
    "Stucco": "Estuque",
    "VinylSd": "Vinil",
    "Wd Sdng": "Tábuas de madeira",
    "WdShing": "Escamas de madeira",
    "Wd Shng": "Escamas de madeira",
}

#: Códigos da origem (De Cock, 2011) → rótulo em português, por coluna.
#:
#: A ingestão aplica o mapa logo depois da renomeação, e a camada bruta em
#: parquet já nasce traduzida. A tradução troca só o texto: cada coluna continua
#: com o mesmo número de categorias e os mesmos imóveis em cada uma, o que deixa
#: Gower, *one-hot* e qualquer contagem inalterados. O vazio (`NA`) não é
#: código e passa intacto: vira rótulo de ausência só na curadoria.
#:
#: Bairro é nome próprio: o código abreviado dá lugar ao nome por extenso, sem
#: tradução. As colunas ordinais entram pelo fim do mapa, a partir das escalas.
TRADUCAO_CATEGORIAS: dict[str, dict[str, str]] = {
    "zoneamento": {
        "RL": "Residencial de baixa densidade",
        "RM": "Residencial de média densidade",
        "RH": "Residencial de alta densidade",
        "FV": "Residencial em vila planejada",
        "C (all)": "Comercial",
        "I (all)": "Industrial",
        "A (agr)": "Agrícola",
    },
    "tipo_via": _PAVIMENTO,
    "tipo_viela": _PAVIMENTO,
    "relevo": {
        "Lvl": "Plano",
        "Bnk": "Talude",
        "HLS": "Encosta",
        "Low": "Baixada",
    },
    "config_lote": {
        "Inside": "Meio de quadra",
        "Corner": "Esquina",
        "CulDSac": "Rua sem saída",
        "FR2": "Duas frentes",
        "FR3": "Três frentes",
    },
    "bairro": {
        "Blmngtn": "Bloomington Heights",
        "Blueste": "Bluestem",
        "BrDale": "Briardale",
        "BrkSide": "Brookside",
        "ClearCr": "Clear Creek",
        "CollgCr": "College Creek",
        "Crawfor": "Crawford",
        "Edwards": "Edwards",
        "Gilbert": "Gilbert",
        "Greens": "Greens",
        "GrnHill": "Green Hills",
        "IDOTRR": "Iowa DOT and Rail Road",
        "Landmrk": "Landmark",
        "MeadowV": "Meadow Village",
        "Mitchel": "Mitchell",
        "NAmes": "North Ames",
        "NoRidge": "Northridge",
        "NPkVill": "Northpark Villa",
        "NridgHt": "Northridge Heights",
        "NWAmes": "Northwest Ames",
        "OldTown": "Old Town",
        "SWISU": "South & West of ISU",
        "Sawyer": "Sawyer",
        "SawyerW": "Sawyer West",
        "Somerst": "Somerset",
        "StoneBr": "Stone Brook",
        "Timber": "Timberland",
        "Veenker": "Veenker",
    },
    "condicao_entorno_1": _ENTORNO,
    "condicao_entorno_2": _ENTORNO,
    "tipo_construcao": {
        "1Fam": "Unifamiliar isolada",
        "2fmCon": "Bifamiliar convertida",
        "Duplex": "Duplex",
        "TwnhsE": "Casa em fileira, ponta",
        "Twnhs": "Casa em fileira, meio",
    },
    "estilo": {
        "1Story": "Térrea",
        "1.5Fin": "1,5 pavimento, superior acabado",
        "1.5Unf": "1,5 pavimento, superior inacabado",
        "2Story": "Dois pavimentos",
        "2.5Fin": "2,5 pavimentos, superior acabado",
        "2.5Unf": "2,5 pavimentos, superior inacabado",
        "SFoyer": "Entrada em meio-nível",
        "SLvl": "Meios-níveis",
    },
    "estilo_telhado": {
        "Flat": "Plano",
        "Gable": "Duas águas",
        "Gambrel": "Holandês",
        "Hip": "Quatro águas",
        "Mansard": "Mansarda",
        "Shed": "Uma água",
    },
    "material_telhado": {
        "ClyTile": "Telha cerâmica",
        "CompShg": "Telha asfáltica",
        "Membran": "Membrana",
        "Metal": "Metal",
        "Roll": "Manta em rolo",
        "Tar&Grv": "Piche e cascalho",
        "WdShake": "Lascas de madeira",
        "WdShngl": "Telha de madeira",
    },
    "revestimento_1": _REVESTIMENTO,
    "revestimento_2": _REVESTIMENTO,
    "tipo_alvenaria_aparente": {
        "BrkCmn": "Tijolo comum",
        "BrkFace": "Tijolo aparente",
        "CBlock": "Bloco de concreto",
        "Stone": "Pedra",
        "None": "Sem alvenaria aparente",
    },
    "fundacao": {
        "BrkTil": "Tijolo e telha",
        "CBlock": "Bloco de concreto",
        "PConc": "Concreto moldado",
        "Slab": "Radier",
        "Stone": "Pedra",
        "Wood": "Madeira",
    },
    "aquecimento": {
        "Floor": "Fornalha de piso",
        "GasA": "Ar forçado a gás",
        "GasW": "Água quente a gás",
        "Grav": "Fornalha por gravidade",
        "OthW": "Água quente, outro combustível",
        "Wall": "Fornalha de parede",
    },
    "ar_central": {"Y": "Sim", "N": "Não"},
    "sistema_eletrico": {
        "SBrkr": "Disjuntores",
        "FuseA": "Fusíveis acima de 60 A",
        "FuseF": "Fusíveis de 60 A",
        "FuseP": "Fusíveis de 60 A, fiação antiga",
        "Mix": "Misto",
    },
    "tipo_garagem": {
        "Attchd": "Anexa à casa",
        "Detchd": "Separada da casa",
        "BuiltIn": "Embutida",
        "Basment": "No porão",
        "CarPort": "Telheiro",
        "2Types": "Mais de um tipo",
    },
    "item_extra": {
        "Elev": "Elevador",
        "Gar2": "Segunda garagem",
        "Othr": "Outro",
        "Shed": "Depósito",
        "TenC": "Quadra de tênis",
    },
    "tipo_venda": {
        "WD ": "Escritura convencional",
        "CWD": "Escritura com pagamento à vista",
        "VWD": "Escritura com financiamento de veterano",
        "New": "Imóvel novo",
        "COD": "Escritura judicial ou de espólio",
        "Con": "Contrato, entrada de 15%",
        "ConLw": "Contrato, entrada e juros baixos",
        "ConLI": "Contrato, juros baixos",
        "ConLD": "Contrato, entrada baixa",
        "Oth": "Outra",
    },
    "condicao_venda": {
        "Normal": "Normal",
        "Abnorml": "Anormal",
        "AdjLand": "Terreno adjacente",
        "Alloca": "Matrículas conjuntas",
        "Family": "Entre familiares",
        "Partial": "Parcial",
    },
}

TRADUCAO_CATEGORIAS.update(
    {
        coluna: {codigo: rotulo for codigo, (rotulo, _) in niveis.items()}
        for coluna, niveis in _NIVEIS_ORDINAIS.items()
    }
)

#: Condição de venda que a depuração da carteira mantém.
VENDA_NORMAL = TRADUCAO_CATEGORIAS["condicao_venda"]["Normal"]

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

#: Variáveis contínuas cuja assimetria **na base curada** supera o limiar e que,
#: por isso, recebem `log1p` antes da padronização.
#: Medições: varandas 0,974 · área habitável 0,747 · terreno 0,417 · porão 0,296.
#:
#: A lista encolheu quando a depuração da carteira entrou em cena, e as duas
#: mudanças estão medidas, não estimadas:
#:
#: * **área do terreno** marcava 13,20 na base bruta e caiu para 0,417. O que
#:   parecia forma da distribuição era um punhado de lotes acima de 200.000
#:   pés², removidos como valores extremos. Transformá-la agora seria hábito;
#: * **área habitável** ficou em 0,747, logo abaixo do limiar de 0,75. Fica de
#:   fora pelo critério declarado — mudar o limiar para acomodar a variável
#:   inverteria a ordem entre regra e resultado.
#:
#: Só entram contínuas. As ordinais `qualidade_externa` (0,81) e
#: `qualidade_porao` (−1,38) também passam do limiar, mas `log1p` sobre nota de
#: 0 a 5 destrói o passo constante que dá sentido à escala.
ASSIMETRICAS = ["area_varandas"]

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
