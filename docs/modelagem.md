# Modelagem

**CRISP-DM fase 4.** Encontrar em quantos grupos a carteira se divide e quais são,
comparando técnicas de famílias diferentes na mesma régua. A modelagem está dividida em
quatro notebooks, cada um com uma pergunta.

Corresponde aos objetivos **1**, **3** e **4** dos
[critérios de sucesso](criterios-sucesso.md).

| Notebook | Pergunta | Saída |
|:---|:---|:---|
| `04-0-modelagem-cluster` | Qual algoritmo, com qual configuração, segmenta melhor? | O modelo vencedor e o segmento de cada imóvel |
| `04-1-modelagem-cotovelo` | O que o cotovelo e a silhueta dizem, algoritmo a algoritmo? | Peso × silhueta de cada algoritmo, de *k* = 1 a 10 |
| `04-2-modelagem-reducao` | Quais variáveis carregam a estrutura da carteira? | Bases reduzidas por PCA e UMAP, com a relevância de cada variável |
| `04-3-modelagem-associacao` | Que características aparecem juntas? | Regras de associação |
| `07_modelagem_bonus` | O mesmo problema como `Pipeline` com busca em grade | Modelo da aplicação `app/app_imobiliario.py` |

## Unidade de análise

Um registro por **imóvel residencial transacionado** (`pid`). A entrada é a base
pré-processada do notebook 03: **2.927 imóveis × 236 variáveis**, todas em 0–1, das
quais 177 são colunas *one-hot*. `preco_venda` e `subclasse` são retirados antes de
qualquer algoritmo rodar.

## O desenho do experimento

Onze algoritmos, de quatro famílias, varrem suas grades de hiperparâmetros sobre a base
inteira. Todos são medidos pela **mesma régua**: a silhueta euclidiana, no mesmo
espaço. Quem vence é a maior silhueta entre as partições que o negócio consegue operar.

| Família | Algoritmos | O que é varrido |
|:---|:---|:---|
| Centroides | k-means, mini batch k-means, bisecting k-means, k-means Manhattan, k-means Mahalanobis, k-medoids | *k* ∈ {2, 3, 4, 5, 6, 8} e a variante de cada um |
| Hierárquica | Birch, Ward | *k* e o limiar do Birch |
| Probabilística | Mistura gaussiana (GMM) | número de componentes e tipo de covariância |
| Densidade | Mean Shift, DBSCAN | largura da janela e raio `eps` — o número de grupos emerge do parâmetro |

Três algoritmos não existem prontos no `scikit-learn` e são escritos no próprio
notebook, com a mesma interface (`fit`, `fit_predict`):

- **k-means Manhattan** atribui pela distância L1, e o centro vira a mediana;
- **k-medoids** usa como centro um imóvel real, o de menor soma de distâncias ao grupo;
- **k-means Mahalanobis** é o k-means no espaço **branqueado** pelo PCA, o que equivale
  a usar a distância de Mahalanobis no espaço original.

### As escalas dos parâmetros

Mahalanobis, Mean Shift e DBSCAN dependem da escala das distâncias. Por isso a grade de
cada um sai dos próprios dados, e não de um valor fixado à mão:

| Parâmetro | Como é obtido | Valores |
|:---|:---|:---|
| Posto da base (Mahalanobis) | direções com variância maior que zero | 207 de 236 — o *one-hot* cria 29 direções nulas |
| Largura do Mean Shift | `estimate_bandwidth` nos quantis 0,1 a 0,5 | 4,54 · 4,24 · 4,03 · 3,74 |
| Raio do DBSCAN | percentis 50 a 95 da distância ao 10º vizinho | 2,66 · 3,00 · 3,23 · 3,49 · 3,71 |

### A regra de admissão

Antes de comparar silhuetas, a configuração precisa passar por três filtros de
negócio:

1. **entre 2 e 8 segmentos** — a faixa que o negócio consegue operar;
2. **nenhum segmento com mais de 90% da carteira** — um grupo assim não segmenta, só
   isola exceções;
3. **no máximo 20% dos imóveis sem grupo** — o ruído do DBSCAN.

## Os algoritmos comparados

A melhor configuração aprovada de cada algoritmo, em ordem de silhueta:

| Algoritmo | Melhor configuração | Segmentos | Silhueta | Maior segmento |
|:---|:---|:-:|--:|--:|
| **mini batch k-means** | `batch_size` 64 | **3** | **0,102** | 38,4% |
| bisecting k-means | `biggest_inertia` | 3 | 0,100 | 39,7% |
| k-means | `init` k-means++ | 3 | 0,100 | 37,5% |
| Birch | limiar 2,0 | 2 | 0,094 | 68,7% |
| k-means Manhattan | — | 2 | 0,092 | 57,6% |
| k-medoids | — | 3 | 0,087 | 43,4% |
| Ward | — | 2 | 0,085 | 55,6% |
| mistura gaussiana | covariância cheia | 4 | 0,074 | 34,0% |
| k-means Mahalanobis | — | 8 | −0,053 | 89,3% |
| Mean Shift | nenhuma configuração aprovada | — | — | — |
| DBSCAN | nenhuma configuração aprovada | — | — | — |

Nenhum algoritmo ficou com ruído: as nove configurações aprovadas classificam 100% da
carteira.

## A escolha do modelo

O vencedor é o **mini batch k-means com 3 segmentos** (`batch_size` 64), com silhueta
de **0,102**. O modelo ajustado é gravado em
`models/model_imoveis_mini_batch_k_means.joblib`, o segmento de cada imóvel em
`data/processed/segmentos.csv` e o resumo da escolha em `models/selecionado.json`.

!!! note "Três algoritmos concordam no número de segmentos"
    Os três primeiros colocados — mini batch k-means, bisecting k-means e k-means —
    escolhem **3 segmentos** e estão separados por 0,002 de silhueta. A margem é pequena
    demais para distinguir um algoritmo do outro, mas a concordância sobre *k* é um bom
    sinal: o número de segmentos não depende da variante escolhida.

!!! warning "Silhueta baixa em todos os algoritmos é um resultado"
    Nenhuma configuração aprovada passa de 0,102. Em ~200 dimensões, a maioria
    *one-hot*, as distâncias se concentram e todo imóvel fica a distâncias parecidas de
    todos os grupos. O 05 lê isso como **faixas de uma carteira contínua**, e não grupos
    isolados.

## O cotovelo de cada algoritmo

O notebook 04-1 treina cada algoritmo para cada número de grupos, de 1 a 10, e traça
duas curvas: o **peso** que o algoritmo minimiza (inércia, soma das distâncias,
−log-verossimilhança), que sempre cai, e a **silhueta**, que não melhora sozinha com
*k* e por isso serve de contraprova.

| Algoritmo | *k* no cotovelo | *k* de maior silhueta | Maior silhueta (régua própria) | Silhueta comum (euclidiana) | Maior grupo | Ruído |
|:---|:-:|:-:|--:|--:|--:|--:|
| k-means | 4 | 3 | 0,100 | 0,100 | 37,5% | 0% |
| k-means Manhattan | 4 | 2 | 0,169 | 0,092 | 57,6% | 0% |
| k-means Mahalanobis | 9 | 2 | 0,080 | 0,029 | **98,3%** | 0% |
| k-medoids | 3 | 3 | 0,087 | 0,087 | 43,4% | 0% |
| GMM | 4 | 4 | 0,074 | 0,074 | 34,0% | 0% |
| Ward | 4 | 2 | 0,085 | 0,085 | 55,6% | 0% |
| Mean Shift | 6 | 2 | 0,224 | 0,224 | **99,9%** | 0% |
| DBSCAN | 1 | 7 | 0,232 | 0,232 | 8,4% | **83,1%** |

Com a regra de escolha declarada no 04-1 — *k* entre 2 e 5, ruído até 20%, nenhum grupo
acima de 90% —, **20 de 77 configurações** passam, e o vencedor é o **k-means com
*k* = 3** (silhueta comum 0,100): o mesmo número de segmentos do 04-0. DBSCAN, Mean
Shift e k-means Mahalanobis não têm nenhuma configuração aprovada. O 04-1 não inclui o
mini batch k-means, que vence no 04-0.

**As maiores silhuetas da tabela são de configurações degeneradas.** O DBSCAN marca
0,232 deixando 83,1% dos imóveis como ruído; o Mean Shift marca 0,224 com um grupo de
99,9%. A silhueta alta, aqui, é sinal de que a partição separou poucas exceções — e é
por isso que a regra de admissão vem antes da silhueta.

**O cotovelo e a silhueta não concordam.** Para o k-means, o cotovelo do peso está em
*k* = 4 e a maior silhueta em *k* = 3. Quando a curva de peso desce quase em linha reta,
não há cotovelo de verdade, e as duas leituras se afastam.

## Por que DBSCAN e Mean Shift falharam

Os dois dependem de **densidade**, e é a densidade que mais se dilui em alta dimensão.
O esperado — e o que aconteceu — é um grupo gigante com satélites, ou muito ruído:

- o **Mean Shift**, na largura de janela de maior silhueta, junta **99,9%** da carteira
  num grupo só;
- o **DBSCAN**, no raio de maior silhueta, deixa **83,1%** dos imóveis como ruído.

Nenhuma configuração de nenhum dos dois passou na regra de admissão do 04-0. Com isso,
o objetivo 4 — isolar os imóveis que não pertencem a nenhuma linha — fica **sem
entrega** nesta cadeia.

## Redução de dimensionalidade

O notebook 04-2 não treina agrupamentos: aplica duas reduções e mostra **quais variáveis
mais pesam** em cada uma. Como o *one-hot* espalha uma variável em várias colunas, a
relevância também é somada por **variável de origem** — 236 colunas vêm de 82 variáveis.

| Redução | Resultado | Como a relevância é medida |
|:---|:---|:---|
| **PCA** | 59 componentes guardam 90% da variância; PC1 explica 13,0% e PC2, 8,7% | Cargas ao quadrado, ponderadas pela variância de cada componente |
| **UMAP** | 5 componentes, com `n_neighbors` 30 e `min_dist` 0 | Uma random forest aprende a prever as coordenadas do UMAP (R² fora da amostra de 0,957), e a importância de cada variável nela é a relevância |

| # | PCA | UMAP |
|:-:|:---|:---|
| 1 | bairro (8,2%) | idade_imovel (66,9%) |
| 2 | revestimento_1 (7,9%) | area_pavimento_superior (6,6%) |
| 3 | revestimento_2 (7,8%) | testada_lote (6,3%) |
| 4 | estilo (6,5%) | revestimento_1 (3,4%) |
| 5 | fundacao (6,4%) | revestimento_2 (3,3%) |
| 6 | tipo_garagem (5,8%) | tem_segundo_pavimento (3,0%) |
| 7 | tipo_alvenaria_aparente (5,6%) | zoneamento (2,3%) |
| 8 | config_lote (4,5%) | condicao_venda (2,3%) |

Nove variáveis estão entre as 15 mais relevantes das **duas** reduções: `bairro`,
`condicao_venda`, `fundacao`, `revestimento_1`, `revestimento_2`,
`tem_segundo_pavimento`, `tipo_construcao`, `tipo_garagem` e `zoneamento`. São as
candidatas mais firmes a descrever a estrutura da carteira.

**Relevância na redução não é relevância para o negócio.** O PCA favorece as colunas
que **variam muito** — e, com o MinMax, uma binária dividida meio a meio varia mais que
uma contínua concentrada perto de zero. Por isso o topo do PCA é quase todo nominal. O
UMAP, que preserva a vizinhança entre imóveis, é dominado pela **idade** (66,9%).

As bases reduzidas (`ames_housing_pca.csv`, 2.927 × 59, e `ames_housing_umap.csv`,
2.927 × 5) ficam gravadas. Agrupar sobre elas é o próximo passo proposto, com a silhueta
medida no espaço original para que a comparação seja justa. A aplicação usa as duas para
desenhar a carteira em duas dimensões.

## Regras de associação

O notebook 04-3 trata cada imóvel como uma **cesta de características** e procura as
que aparecem juntas. As colunas binárias viram item quando valem 1
(`zoneamento=Residencial de baixa densidade`, `tem_lareira`); as numéricas e ordinais
são cortadas em tercis (`baixo`, `medio`, `alto`). O preço entra como item, porque é bom
candidato a consequente.

| Etapa | Resultado |
|:---|:---|
| Itens gerados | 286, dos quais 16 descartados por estarem em mais de 90% dos imóveis (ar central, aquecimento a gás, telha asfáltica…) |
| Itens com suporte ≥ 15% | 112 |
| Conjuntos frequentes (até 3 itens) | **31.601** — os mesmos nos três algoritmos |
| Tempo | Apriori 0,72 s · Eclat 0,87 s · FP-Growth 27,77 s |
| Regras geradas | 177.294 |
| Regras fortes (confiança ≥ 60% e lift ≥ 1,20) | **23.403**, gravadas em `data/processed/regras_associacao.csv` |

Apriori, Eclat e FP-Growth **encontraram exatamente os mesmos conjuntos, com o mesmo
suporte** — o notebook confere antes de gerar as regras. O Eclat não existe no `mlxtend`
e é escrito no próprio notebook.

As regras mais úteis para a Meridiano são as que têm o **preço como consequente**:

| Características | → | Confiança | Lift |
|:---|:-:|--:|--:|
| `qualidade_geral=alto` | preço alto | 93,6% | 2,83 |
| `area_habitavel=alto` + `idade_imovel=baixo` | preço alto | 92,3% | 2,79 |
| `area_garagem=alto` + `idade_imovel=baixo` | preço alto | 91,1% | 2,75 |
| `area_pavimento_superior=baixo` + `area_terreo=baixo` | preço baixo | 89,6% | 2,67 |
| `area_garagem=baixo` + `area_habitavel=baixo` | preço baixo | 84,3% | 2,52 |
| `area_garagem=baixo` + `qualidade_geral=baixo` | preço baixo | 81,3% | 2,43 |

**Regras óbvias aparecem no topo.** As de maior lift ligam itens derivados uns dos
outros — `banheiros_total=alto` com `banheiros_completos=medio`, ou `tem_segundo_pavimento`
com `estilo=Dois pavimentos`. São verdadeiras, mas não ensinam nada. E **associação não é
causa**: lareira e preço alto aparecem juntos porque ambos estão em imóveis maiores e
mais novos.

## Os três segmentos

Os segmentos do vencedor, renomeados de A a C do preço mediano mais alto ao mais
baixo. O preço não entrou no agrupamento.

| | Segmento A | Segmento B | Segmento C |
|:---|--:|--:|--:|
| Imóveis | 1.105 | 1.124 | 698 |
| % da carteira | 37,8% | 38,4% | 23,8% |
| Preço mediano | US$ 221.000 | US$ 145.000 | US$ 120.000 |
| Área habitável mediana (pé²) | 1.668 | 1.227 | 1.304 |
| Qualidade geral mediana | 7 | 5 | 5 |
| Idade mediana (anos) | 5 | 43 | 80 |
| Anos desde a reforma (mediana) | 4 | 35 | 44 |
| Com segundo pavimento | 51% | 16% | 73% |
| Com lareira | 68% | 49% | 29% |
| Silhueta média | 0,154 | 0,085 | 0,045 |

O que distingue cada um, nas variáveis que o 05 aponta como as que mais separam os
segmentos (fundação, idade e zoneamento):

- **Segmento A — casa recente de padrão alto.** Fundação em concreto moldado (98%),
  revestimento em vinil (77%), garagem anexa (80%), qualidade externa e de cozinha
  "Bom" em mais de 70% dos imóveis, zona residencial de baixa densidade (84%). College
  Creek é o bairro mais frequente (21%). É também onde estão as vendas de imóvel novo:
  21,4% são vendas parciais.
- **Segmento B — térrea de meia-idade no subúrbio.** Fundação em bloco de concreto
  (88%), casa térrea (71%), zona de baixa densidade (97%), qualidade externa típica
  (88%). North Ames concentra 36%.
- **Segmento C — casa antiga do centro.** 80 anos de idade mediana, fundação em tijolo
  e telha (43%), garagem separada da casa (73%), zona de média densidade (55%), casa de
  um pavimento e meio (37%). Old Town concentra 33%.

O Segmento A é o mais coeso (silhueta média de 0,154); o C, o menos (0,045). No total,
7% dos imóveis têm silhueta negativa — estão mais perto de outro segmento do que do
próprio.

Os perfis estão em unidades de negócio, mas ainda **não viraram política**: nenhum
segmento tem ação, teto de reforma, canal ou métrica definidos. O catálogo de personas em
`src/model/personas.py` descreve as três linhas de uma cadeia anterior, com outra base e
outro espaço de atributos, e não se aplica a estes três.

## O modelo bônus

O notebook `07_modelagem_bonus` resolve o mesmo problema de outro jeito: o
pré-processamento e o agrupamento num único `Pipeline` do `scikit-learn`, com busca em
grade e silhueta em validação cruzada (10 divisões de 80/20). Ele parte da base curada
de `src.data.preparacao` (`imoveis_curados.parquet`, 2.350 × 83), e não da cadeia
01 → 03: o espaço pré-processado tem 207 colunas.

| Algoritmo | Silhueta em validação cruzada | Tempo de ajuste |
|:---|:---|--:|
| **k-means** | **0,104 ± 0,005** | 20,6 s |
| bisecting k-means | 0,099 ± 0,012 | 5,2 s |
| mini batch k-means | 0,092 ± 0,014 | 7,7 s |
| Birch | 0,086 ± 0,007 | 165,2 s |

O vencedor é o **k-means com 3 grupos** (`init` aleatório), com silhueta de 0,103 na
base inteira. Ele é gravado, com o pré-processamento, em
`models/model_bonus_imoveis_k_means.joblib` — o modelo que a aplicação
`app/app_imobiliario.py` usa.

| Grupo | Imóveis | % da carteira | Preço mediano | Área habitável | Qualidade | Idade |
|:---|--:|--:|--:|--:|--:|--:|
| 1 | 794 | 33,8% | US$ 215.000 | 1.660 | 7 | 6 |
| 2 | 907 | 38,6% | US$ 145.500 | 1.211 | 5 | 42 |
| 0 | 649 | 27,6% | US$ 125.000 | 1.328 | 5 | 76 |

Partindo de outra base e de outro pré-processamento, o 07 chega à mesma leitura da
cadeia principal: **três segmentos**, separados por idade e padrão — recente de padrão
alto, meia-idade e antigo.

!!! note "As ordinais que chegam como texto"
    A base curada entrega quase todas as ordinais já como número, mas `sistema_eletrico`
    chega como texto ("Disjuntores", "Fusíveis de 60 A"…). O 07 a codifica dentro do
    próprio `Pipeline`, com um `OrdinalEncoder` na ordem da escala do notebook 00, antes
    do MinMax. Assim o modelo gravado recebe o texto bruto, e a aplicação não precisa
    repetir a conversão.

## O que esta fase não entregou

| Prometido no Canvas | Situação |
|:---|:---|
| **Objetivo 3** — padrões que valem dentro de um segmento | As regras foram mineradas na carteira inteira; o cruzamento com os segmentos não foi feito |
| **Objetivo 4** — isolar os imóveis fora de padrão | Nenhuma configuração de densidade foi admitida (ver acima). Sem entrega |
| **Estabilidade da partição** | Não medida: a escolha foi feita na base inteira, sem reamostragem. O 05 mitiga com a acurácia de um classificador em validação cruzada |

## Saídas

| Arquivo | Conteúdo |
|:---|:---|
| `data/processed/segmentos.csv` | Segmento de cada imóvel da carteira, na ordem da base tratada (04-0) |
| `models/model_imoveis_<modelo>.joblib` | O modelo vencedor, ajustado (04-0) |
| `models/selecionado.json` | Nome, parâmetros, número de segmentos, silhueta e arquivo do vencedor (04-0) |
| `data/processed/ames_housing_pca.csv`, `ames_housing_umap.csv` | A carteira reduzida por PCA e por UMAP (04-2) |
| `data/processed/regras_associacao.csv` | As 23.403 regras fortes (04-3) |
| `models/model_bonus_imoveis_k_means.joblib` | O modelo do notebook bônus (07) |

## Reprodução

```bash
uv run invoke notebooks     # executa a cadeia 00–07; a fase 4 são os notebooks 04-0 a 04-3
```
