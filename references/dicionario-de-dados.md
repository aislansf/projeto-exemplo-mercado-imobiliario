# Dicionário de dados

> Gerado a partir de `src/data/dicionario.py`, que é a fonte única da verdade sobre o
> significado de cada coluna. Não edite este arquivo à mão: edite o módulo.

A base de origem (Ames Housing, De Cock 2011) usa nomes em inglês com espaço no meio e
categorias em código (`RL`, `1Fam`, `Ex`). A ingestão renomeia as colunas para
`snake_case` em português e troca os códigos pelos rótulos já na camada bruta
(`data/raw/ames_housing.parquet`), porque o resultado é lido por gente de negócio. O
arquivo da fonte continua intacto em `data/raw/ames_housing.txt`.

## Espaço de atributos da modelagem

### Numéricas (11)

| Coluna curada | Coluna na origem | Descrição |
|:---|:---|:---|
| `area_habitavel` | `Gr Liv Area` | Área construída acima do solo, em pés quadrados |
| `area_porao` | `Total Bsmt SF` | Área total do porão, em pés quadrados (0 = sem porão) |
| `area_terreno` | `Lot Area` | Área do lote, em pés quadrados |
| `area_garagem` | `Garage Area` | Área da garagem, em pés quadrados (0 = sem garagem) |
| `area_varandas` | soma de 5 colunas de varanda | Soma de deck, varandas aberta, fechada, de tela e de três estações |
| `banheiros_total` | derivada de 4 colunas de banheiro | Banheiros equivalentes: completos + metade dos lavabos, incluindo porão |
| `comodos` | `TotRms AbvGrd` | Cômodos acima do solo, exceto banheiros |
| `dormitorios` | `Bedroom AbvGr` | Dormitórios acima do solo |
| `lareiras` | `Fireplaces` | Número de lareiras |
| `idade_imovel` | ano_venda − ano_construcao | Anos entre a construção e a venda |
| `anos_desde_reforma` | ano_venda − ano_reforma | Anos entre a última reforma (ou a construção) e a venda |

### Ordinais (6)

| Coluna curada | Coluna na origem | Escala | Descrição |
|:---|:---|:---|:---|
| `qualidade_geral` | `Overall Qual` | 1 a 10 (oficial da base) | Qualidade geral de material e acabamento (1 a 10) |
| `conservacao_geral` | `Overall Cond` | 1 a 10 (oficial da base) | Estado geral de conservação (1 a 10) |
| `qualidade_externa` | `Exter Qual` | 0 a 5 · NA=0, Po=1, Fa=2, TA=3, Gd=4, Ex=5 | Qualidade do revestimento externo (0 a 5) |
| `qualidade_cozinha` | `Kitchen Qual` | 0 a 5 · NA=0, Po=1, Fa=2, TA=3, Gd=4, Ex=5 | Qualidade da cozinha (0 a 5) |
| `qualidade_porao` | `Bsmt Qual` | 0 a 5 · **0 = sem porão** | Altura e qualidade do porão (0 = sem porão, 5 = excelente) |
| `acabamento_garagem` | `Garage Finish` | 0 a 3 · 0 = sem garagem, Unf=1, RFn=2, Fin=3 | Acabamento interno da garagem (0 = sem garagem, 3 = acabada) |

### Nominais (5)

| Coluna curada | Coluna na origem | Categorias | Descrição |
|:---|:---|:---|:---|
| `zoneamento` | `MS Zoning` | 7 | Classificação de zoneamento urbano |
| `tipo_construcao` | `Bldg Type` | 5 | Tipo de construção (isolada, geminada, sobreposta) |
| `estilo` | `House Style` | 8 | Estilo e número de pavimentos |
| `tipo_garagem` | `Garage Type` | 7 | Posição da garagem em relação à casa |
| `ar_central` | `Central Air` | 2 | Possui ar-condicionado central |

### Binárias derivadas (4)

| Coluna | Regra de derivação | Descrição |
|:---|:---|:---|
| `tem_porao` | `area_porao > 0` | Possui porão |
| `tem_garagem` | `area_garagem > 0` | Possui garagem |
| `tem_lareira` | `lareiras > 0` | Possui ao menos uma lareira |
| `tem_segundo_pavimento` | `area_pavimento_superior > 0` | Possui pavimento superior |

## Colunas reservadas

| Coluna | Origem | Papel |
|:---|:---|:---|
| `preco_venda` | `SalePrice` | **Rótulo reservado.** Não entra em nenhuma etapa de modelagem. Uso exclusivo na avaliação a posteriori — critério eliminatório da disciplina. |
| `bairro` | `Neighborhood` | **Validação externa.** 28 categorias; explica 56% da variância da qualidade geral. Proxy de preço por caminho indireto. |

## Atributos da transação

Descrevem o **negócio**, não o **produto**. Ficam na base curada para a análise
temporal e o monitoramento de drift, fora da matriz de modelagem.

| Coluna | Origem | Descrição |
|:---|:---|:---|
| `mes_venda` | `Mo Sold` | Mês da transação |
| `ano_venda` | `Yr Sold` | Ano da transação |
| `tipo_venda` | `Sale Type` | Modalidade da venda |
| `condicao_venda` | `Sale Condition` | Condição da venda (normal, parcial, familiar, execução…) |

## Escalas ordinais completas

As 20 colunas ordinais e o mapa aplicado a cada uma: o rótulo em português, o código da
fonte entre parênteses e a posição na escala. Ausência do item vale 0.

| Coluna | Coluna na origem | Escala |
|:---|:---|:---|
| `qualidade_externa` | `Exter Qual` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `conservacao_externa` | `Exter Cond` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `qualidade_porao` | `Bsmt Qual` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `conservacao_porao` | `Bsmt Cond` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `qualidade_aquecimento` | `Heating QC` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `qualidade_cozinha` | `Kitchen Qual` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `qualidade_lareira` | `Fireplace Qu` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `qualidade_garagem` | `Garage Qual` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `conservacao_garagem` | `Garage Cond` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `qualidade_piscina` | `Pool QC` | Excelente (Ex)=5, Bom (Gd)=4, Típico (TA)=3, Regular (Fa)=2, Ruim (Po)=1, ausente=0 |
| `exposicao_porao` | `Bsmt Exposure` | Boa (Gd)=4, Média (Av)=3, Mínima (Mn)=2, Nenhuma (No)=1, ausente=0 |
| `acabamento_porao_1` | `BsmtFin Type 1` | Habitável, bom padrão (GLQ)=6, Habitável, padrão médio (ALQ)=5, Habitável, abaixo do padrão (BLQ)=4, Recreação (Rec)=3, Baixa qualidade (LwQ)=2, Sem acabamento (Unf)=1, ausente=0 |
| `acabamento_porao_2` | `BsmtFin Type 2` | Habitável, bom padrão (GLQ)=6, Habitável, padrão médio (ALQ)=5, Habitável, abaixo do padrão (BLQ)=4, Recreação (Rec)=3, Baixa qualidade (LwQ)=2, Sem acabamento (Unf)=1, ausente=0 |
| `acabamento_garagem` | `Garage Finish` | Acabada (Fin)=3, Parcialmente acabada (RFn)=2, Sem acabamento (Unf)=1, ausente=0 |
| `funcionalidade` | `Functional` | Típica (Typ)=8, Dedução mínima 1 (Min1)=7, Dedução mínima 2 (Min2)=6, Dedução moderada (Mod)=5, Dedução grave 1 (Maj1)=4, Dedução grave 2 (Maj2)=3, Muito comprometida (Sev)=2, Só para aproveitamento (Sal)=1, ausente=0 |
| `formato_lote` | `Lot Shape` | Regular (Reg)=4, Levemente irregular (IR1)=3, Moderadamente irregular (IR2)=2, Irregular (IR3)=1, ausente=0 |
| `declividade` | `Land Slope` | Suave (Gtl)=3, Moderada (Mod)=2, Acentuada (Sev)=1, ausente=0 |
| `acesso_pavimentado` | `Paved Drive` | Pavimentado (Y)=3, Parcialmente pavimentado (P)=2, Terra ou cascalho (N)=1, ausente=0 |
| `infraestrutura` | `Utilities` | Todos os serviços (AllPub)=4, Sem esgoto (NoSewr)=3, Só eletricidade e gás (NoSeWa)=2, Só eletricidade (ELO)=1, ausente=0 |
| `tipo_cerca` | `Fence` | Boa privacidade (GdPrv)=4, Privacidade mínima (MnPrv)=3, Boa madeira (GdWo)=2, Madeira ou arame mínimo (MnWw)=1, ausente=0 |

## Ausência estrutural

Colunas em que `NA` significa **o item não existe**, e não informação faltante.
Tratá-las como nulo e imputar pela mediana inventaria porões que nunca existiram.

| Coluna | Coluna na origem | Rótulo aplicado |
|:---|:---|:---|
| `tipo_viela` | `Alley` | `Sem viela` |
| `qualidade_porao` | `Bsmt Qual` | `Sem porão` |
| `conservacao_porao` | `Bsmt Cond` | `Sem porão` |
| `exposicao_porao` | `Bsmt Exposure` | `Sem porão` |
| `acabamento_porao_1` | `BsmtFin Type 1` | `Sem porão` |
| `acabamento_porao_2` | `BsmtFin Type 2` | `Sem porão` |
| `qualidade_lareira` | `Fireplace Qu` | `Sem lareira` |
| `tipo_garagem` | `Garage Type` | `Sem garagem` |
| `acabamento_garagem` | `Garage Finish` | `Sem garagem` |
| `qualidade_garagem` | `Garage Qual` | `Sem garagem` |
| `conservacao_garagem` | `Garage Cond` | `Sem garagem` |
| `qualidade_piscina` | `Pool QC` | `Sem piscina` |
| `tipo_cerca` | `Fence` | `Sem cerca` |
| `item_extra` | `Misc Feature` | `Sem item extra` |

### Exceção declarada

| Coluna | Rótulo | Por quê |
|:---|:---|:---|
| `tipo_alvenaria_aparente` | `Não informado` | 1.752 registros têm a categoria legítima `Sem alvenaria aparente` (a palavra `None` na fonte); apenas 23 estão realmente em branco. A ausência **não** é estrutural. |

## Tradução das categorias

Na ingestão, os códigos da origem dão lugar a rótulos em português
(`dic.TRADUCAO_CATEGORIAS`), e a camada bruta em parquet já nasce traduzida. A tradução
troca só o texto: cada coluna mantém as mesmas categorias com os mesmos imóveis. Abaixo,
as cinco nominais do espaço de atributos; as ordinais estão nas escalas acima, e o mapa
completo está em `dic.TRADUCAO_CATEGORIAS`, em `src/data/dicionario.py`. Bairro é nome próprio: o
código abreviado vira o nome por extenso (`NAmes` → `North Ames`), sem tradução.

### `zoneamento`

| Código na origem | Rótulo curado |
|:---|:---|
| `RL` | Residencial de baixa densidade |
| `RM` | Residencial de média densidade |
| `RH` | Residencial de alta densidade |
| `FV` | Residencial em vila planejada |
| `C (all)` | Comercial |
| `I (all)` | Industrial |
| `A (agr)` | Agrícola |

### `tipo_construcao`

| Código na origem | Rótulo curado |
|:---|:---|
| `1Fam` | Unifamiliar isolada |
| `2fmCon` | Bifamiliar convertida |
| `Duplex` | Duplex |
| `TwnhsE` | Casa em fileira, ponta |
| `Twnhs` | Casa em fileira, meio |

### `estilo`

| Código na origem | Rótulo curado |
|:---|:---|
| `1Story` | Térrea |
| `1.5Fin` | 1,5 pavimento, superior acabado |
| `1.5Unf` | 1,5 pavimento, superior inacabado |
| `2Story` | Dois pavimentos |
| `2.5Fin` | 2,5 pavimentos, superior acabado |
| `2.5Unf` | 2,5 pavimentos, superior inacabado |
| `SFoyer` | Entrada em meio-nível |
| `SLvl` | Meios-níveis |

### `tipo_garagem`

| Código na origem | Rótulo curado |
|:---|:---|
| `Attchd` | Anexa à casa |
| `Detchd` | Separada da casa |
| `BuiltIn` | Embutida |
| `Basment` | No porão |
| `CarPort` | Telheiro |
| `2Types` | Mais de um tipo |
| `SemGaragem` | Sem garagem |

### `ar_central`

| Código na origem | Rótulo curado |
|:---|:---|
| `Y` | Sim |
| `N` | Não |

## Transformações antes da modelagem

`log1p` é aplicado apenas onde a assimetria medida supera o limiar de 0.75:

| Coluna | Assimetria medida | Transformação |
|:---|---:|:---|
| `area_habitavel` | 0.88 | `log1p` |
| `area_porao` | 0.40 | — |
| `area_terreno` | 13.20 | `log1p` |
| `area_garagem` | 0.21 | — |
| `area_varandas` | 1.36 | `log1p` |
| `banheiros_total` | 0.49 | — |
| `comodos` | 0.70 | — |
| `dormitorios` | 0.31 | — |
| `lareiras` | 0.73 | — |
| `idade_imovel` | 0.60 | — |
| `anos_desde_reforma` | 0.45 | — |

Em seguida, todas passam por `StandardScaler`. Ver
[Preparação dos dados](../docs/preparacao.md).
