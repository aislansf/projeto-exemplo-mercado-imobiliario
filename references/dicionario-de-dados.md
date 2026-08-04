# Dicionário de dados

> Gerado a partir de `src/data/dicionario.py`, que é a fonte única da verdade sobre o
> significado de cada coluna. Não edite este arquivo à mão: edite o módulo.

A base de origem (Ames Housing, De Cock 2011) usa nomes em inglês com espaço no meio.
A camada curada renomeia tudo para `snake_case` em português, porque o resultado é lido
por gente de negócio.

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

As 20 colunas ordinais da origem e o mapa aplicado a cada uma.

| Coluna na origem | Escala |
|:---|:---|
| `Exter Qual` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Exter Cond` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Bsmt Qual` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Bsmt Cond` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Heating QC` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Kitchen Qual` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Fireplace Qu` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Garage Qual` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Garage Cond` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Pool QC` | Ex=5, Gd=4, TA=3, Fa=2, Po=1, ausente=0 |
| `Bsmt Exposure` | Gd=4, Av=3, Mn=2, No=1, ausente=0 |
| `BsmtFin Type 1` | GLQ=6, ALQ=5, BLQ=4, Rec=3, LwQ=2, Unf=1, ausente=0 |
| `BsmtFin Type 2` | GLQ=6, ALQ=5, BLQ=4, Rec=3, LwQ=2, Unf=1, ausente=0 |
| `Garage Finish` | Fin=3, RFn=2, Unf=1, ausente=0 |
| `Functional` | Typ=8, Min1=7, Min2=6, Mod=5, Maj1=4, Maj2=3, Sev=2, Sal=1, ausente=0 |
| `Lot Shape` | Reg=4, IR1=3, IR2=2, IR3=1, ausente=0 |
| `Land Slope` | Gtl=3, Mod=2, Sev=1, ausente=0 |
| `Paved Drive` | Y=3, P=2, N=1, ausente=0 |
| `Utilities` | AllPub=4, NoSewr=3, NoSeWa=2, ELO=1, ausente=0 |
| `Fence` | GdPrv=4, MnPrv=3, GdWo=2, MnWw=1, ausente=0 |

## Ausência estrutural

Colunas em que `NA` significa **o item não existe**, e não informação faltante.
Tratá-las como nulo e imputar pela mediana inventaria porões que nunca existiram.

| Coluna na origem | Rótulo aplicado |
|:---|:---|
| `Alley` | `SemViela` |
| `Bsmt Qual` | `SemPorao` |
| `Bsmt Cond` | `SemPorao` |
| `Bsmt Exposure` | `SemPorao` |
| `BsmtFin Type 1` | `SemPorao` |
| `BsmtFin Type 2` | `SemPorao` |
| `Fireplace Qu` | `SemLareira` |
| `Garage Type` | `SemGaragem` |
| `Garage Finish` | `SemGaragem` |
| `Garage Qual` | `SemGaragem` |
| `Garage Cond` | `SemGaragem` |
| `Pool QC` | `SemPiscina` |
| `Fence` | `SemCerca` |
| `Misc Feature` | `SemExtra` |

### Exceção declarada

| Coluna | Rótulo | Por quê |
|:---|:---|:---|
| `Mas Vnr Type` | `NaoInformado` | 1.752 registros têm a categoria legítima `None` (sem revestimento); apenas 23 estão realmente em branco. A ausência **não** é estrutural. |

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
