# Segmentação da carteira residencial — relatório final

**Meridiano Imobiliária** · CRISP-DM, fases 1 a 6 · semente 42

> Todos os números deste relatório vêm das saídas dos notebooks 00 a 07 e dos arquivos
> que eles gravam (`models/selecionado.json`, `data/processed/segmentos.csv`,
> `reports/05-avaliacao.json`). O detalhe de cada fase está no site do projeto, em
> `docs/`.

## 1 · Sumário executivo

* Onze algoritmos de agrupamento foram comparados na mesma régua sobre **2.927
  imóveis**. O vencedor é um **mini batch k-means com 3 segmentos**, com silhueta de
  0,102. Os três primeiros colocados — mini batch k-means, bisecting k-means e
  k-means — escolhem os mesmos 3 segmentos.
* O **Segmento A** (casa recente de padrão alto) tem 37,8% dos imóveis e **50,8% do
  valor de venda**. O preço mediano vai de US$ 120.000 (C) a US$ 221.000 (A): 1,84×.
* Um classificador atribui o segmento certo a **96,9%** dos imóveis novos, o que
  viabiliza usar o modelo na aquisição.
* **O modelo foi aprovado para implantação**: todos os critérios críticos foram
  atendidos, e o menor segmento tem 23,8% da carteira. A ressalva é a silhueta baixa —
  os segmentos são faixas de uma carteira contínua, não grupos isolados.
* A aprovação veio na segunda execução. Na primeira, um **defeito nas escalas
  ordinais** apagava o nível "Típico" da base e o modelo, com 4 segmentos, era reprovado
  por um segmento de 6,4%. Corrigida a escala, a cadeia foi reexecutada.

## 2 · O problema

A Meridiano opera a carteira residencial com uma política única de preço, reforma e
anúncio. A pergunta que originou o projeto: **em quantos grupos a carteira se organiza
naturalmente, e o que fazer de diferente com cada um?** Há orçamento para no máximo
cinco linhas de produto. O preço existe na base, mas é rótulo reservado: entra só
depois, para ler o resultado.

Os critérios de sucesso foram declarados no notebook 05 antes de o resultado ser lido.
Críticos: de 2 a 5 segmentos, menor segmento ≥ 10% da carteira, preço mediano do
segmento mais caro ≥ 1,3× o do mais barato (com Kruskal-Wallis p < 0,05) e acurácia ≥
85% para imóveis novos. Não críticos: silhueta ≥ 0,25 e 100% da carteira com segmento.

## 3 · Metodologia

| Fase | O que decidiu | Evidência |
|:--|:--|:--|
| 1 · Entendimento do negócio | Canvas do Problema com objetivo, critérios técnicos e de negócio, e cinco perguntas SMART | docs/pbl/canvas-do-problema.md |
| 2 · Entendimento dos dados | Dicionário com o tipo de cada coluna, escalas ordinais conferidas contra a base e exploração em oito etapas | docs/entendimento-dados.md · docs/analise-exploratoria.md |
| 3 · Preparação dos dados | 2.930 → 2.927 imóveis (3 vendas parciais atípicas removidas); MinMax nas contínuas e ordinais, *one-hot* nas nominais: 236 variáveis no modelo | docs/preparacao.md |
| 4 · Modelagem | Onze algoritmos de quatro famílias, regra de admissão antes da silhueta; mini batch k-means com 3 segmentos; PCA, UMAP e regras de associação como leituras complementares | docs/modelagem.md |
| 5 · Avaliação | 5 de 6 critérios atendidos, todos os críticos; cenário base de US$ 513 no ano 1; próxima ação: implantação | docs/avaliacao.md |
| 6 · Implantação | Classificação de imóveis novos (notebook 06) e aplicação de consulta sobre os artefatos dos notebooks; plano de entrada em produção em três janelas | docs/implementacao.md |

Três decisões de método sustentam o resto:

1. **o preço ficou fora do agrupamento.** `preco_venda` e `subclasse` são retirados da
   matriz antes de qualquer algoritmo rodar, e o preço só é lido para descrever os
   segmentos;
2. **todos os algoritmos foram medidos na mesma régua**, a silhueta euclidiana no mesmo
   espaço, e só depois de passar por uma regra de admissão declarada antes do resultado;
3. **a decisão de implantar saiu de uma regra**, também declarada antes: um critério
   crítico reprovado basta para barrar — e barrou, na primeira execução.

## 4 · Resultados

| Resultado | Valor | Critério declarado |
|:--|:--|:--|
| Segmentos | 3 | entre 2 e 5 ✅ |
| Menor segmento | 23,8% da carteira | ≥ 10% ✅ |
| O preço distingue os segmentos | 1,84× (p ≈ 0) | ≥ 1,3× e p < 0,05 ✅ |
| Imóvel novo classificável | 96,9% de acurácia | ≥ 85% ✅ |
| Separação dos grupos (silhueta) | 0,102 | ≥ 0,25 ❌ (não crítico) |
| Cobertura da carteira | 100% | 100% ✅ |

### Os 3 segmentos

| Segmento | Retrato | Imóveis | % unidades | % valor de venda | Preço mediano |
|:--|:--|--:|--:|--:|--:|
| A | Casa recente de padrão alto | 1.105 | 37,8 | 50,8 | US$ 221.000 |
| B | Térrea de meia-idade no subúrbio | 1.124 | 38,4 | 32,8 | US$ 145.000 |
| C | Casa antiga do centro | 698 | 23,8 | 16,4 | US$ 120.000 |

## 5 · Insights

| # | Insight | Evidência | Dono |
|:--|:--|:--|:--|
| 1 | Pouco mais de um terço das unidades responde por metade do valor de venda | Segmento A: 37,8% dos imóveis, 50,8% do VGV | Diretoria Comercial |
| 2 | Os segmentos B e C têm preços próximos e são produtos diferentes | US$ 145.000 e US$ 120.000; térrea de 43 anos no subúrbio contra casa de 80 anos no centro | Gerência de Ativos |
| 3 | O que mais separa os segmentos é fundação, idade e zoneamento | Importância das variáveis no classificador do notebook 05 | Área de Dados |
| 4 | A carteira é contínua, não uma soma de grupos isolados | Silhueta máxima de 0,102 entre os nove algoritmos admitidos | Área de Dados |
| 5 | Densidade não serve para isolar imóveis atípicos nesta base | DBSCAN e Mean Shift sem configuração admitida; o DBSCAN de maior silhueta deixa 83,1% como ruído | Gerência de Ativos |
| 6 | A idade estrutura a vizinhança entre imóveis | 66,9% da relevância no UMAP | Área de Dados |
| 7 | Qualidade alta, área grande e imóvel novo levam ao preço alto | Regras com confiança de 91% a 94% e lift de 2,75 a 2,83 | Diretoria Comercial |
| 8 | Um erro de rótulo na preparação mudou a decisão do projeto | 2.100 imóveis "sem garagem" contra 158 reais; corrigido, o modelo passou de reprovado a aprovado | Área de Dados |

## 6 · As perguntas SMART, respondidas

| Pergunta | Resposta medida nesta cadeia | Situação |
|:--|:--|:--|
| Quantos grupos distintos emergem, com no máximo 5? | 3, com silhueta de 0,102 — faixas de uma carteira contínua | respondida, com ressalva |
| Qual grupo concentra mais de 40% da receita transacionada? | Segmento A, com 50,8% do valor de venda | respondida |
| Que combinações de até três atributos ocorrem juntas, e quais valem só dentro de um grupo? | 23.403 regras fortes na carteira inteira; o cruzamento com os segmentos não foi feito | parcial |
| Que percentual dos imóveis é ruído num DBSCAN calibrado? | Nenhuma configuração foi admitida; a de maior silhueta deixa 83,1% como ruído | respondida: sem entrega |
| A segmentação é distinguível de uma faixa de preço? | Não medido na cadeia atual | sem resposta |

## 7 · Implantação

* **Classificação de imóveis novos** no notebook 06: o pré-processamento do 03 é
  refeito e conferido contra a saída do 03, e o modelo relido reproduz 100% dos
  segmentos;
* **aplicação de consulta** em `src/app/`, local, que lê os arquivos dos notebooks e
  faz as mesmas duas conferências a cada carga;
* **plano de entrada em produção em 3 janelas**, a primeira em sombra por 30 dias. Os
  pré-requisitos da janela 1 são persona e ação por segmento, a linha de base do
  monitoramento e as premissas financeiras validadas.

## 8 · Monitoramento e manutenção

Sem gabarito, o que se acompanha é a entrada, a coesão e a composição. O plano propõe
seis indicadores — desvio de distribuição (PSI), coesão, composição, imóveis de
fronteira, integridade da carga e efeito da ação — com gatilho e responsável. A linha de
base de cada um ainda não foi medida. A reciclagem recomendada pelo notebook 05 é
semestral, ou a cada 10% de imóveis novos.

## 9 · O que não foi entregue

* **persona e ação por segmento**: os três segmentos têm perfil, mas não política;
* **a lista de imóveis fora de padrão** (objetivo 4): nenhuma configuração de densidade
  foi admitida;
* **a estabilidade da partição**: a escolha foi feita na base inteira, sem
  reamostragem;
* **os critérios de negócio do Canvas**: giro, preço realizado sobre anunciado e retorno
  da reforma só existem depois que uma política entra em operação.

## 10 · Próximos passos

1. Definir persona, ação, teto de reforma, canal e métrica para cada segmento.
2. Medir a linha de base do monitoramento e calibrar o corte de fronteira.
3. Validar as premissas financeiras com a área comercial — o cenário base empata.
4. Medir a estabilidade por reamostragem e o índice de Rand contra as faixas de preço.
5. Agrupar sobre as bases reduzidas do 04-2 e revisar o peso do *one-hot* no 03, para
   tentar melhorar a separação.

## 11 · Como reproduzir

```bash
uv sync
uv run invoke notebooks
```

A semente do projeto é 42.
