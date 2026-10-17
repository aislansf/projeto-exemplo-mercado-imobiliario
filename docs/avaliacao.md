# Avaliação dos resultados

**CRISP-DM fase 5.** Enquanto a modelagem compara algoritmos entre si, a avaliação
pergunta outra coisa: **o modelo escolhido atende ao negócio?** A resposta vem do
notebook `05-avaliacao` e fica registrada em `reports/05-avaliacao.json`.

| Etapa | Entrega |
|:---|:---|
| **5.1 Avaliar os resultados** | o modelo confrontado com os critérios de sucesso · impacto financeiro e operacional · decisão formal sobre a implantação |
| **5.2 Revisar o processo** | as fases concluídas · lacunas e erros · descobertas e limitações |
| **5.3 Determinar as próximas etapas** | próxima ação, com justificativa |

!!! success "Decisão formal: aprovado para implantação, com ressalva"
    5 de 6 critérios atendidos, **todos os críticos**. A ressalva é a separação dos
    grupos: silhueta de 0,102, contra a meta não crítica de 0,25. No cenário financeiro
    base, o resultado do primeiro ano é de **US$ 513** — o investimento se paga, mas
    por margem mínima.

## 5.1 · Avaliar os resultados

### O modelo avaliado

**Mini batch k-means**, `batch_size` 64, **3 segmentos**, silhueta **0,102** — o
vencedor da [varredura do 04-0](modelagem.md#a-escolha-do-modelo). A avaliação lê os
segmentos de `data/processed/segmentos.csv` e o resumo de `models/selecionado.json`, sem
reajustar nada.

### Os critérios de sucesso

Os critérios foram declarados no código do notebook **antes** de o resultado ser lido.
Os **críticos** traduzem o uso do modelo pela Meridiano: se algum falhar, o modelo não
vai para implantação. Os **não críticos** são qualidade técnica: se falharem, o modelo
pode seguir, com ressalva.

| Critério | Meta | Obtido | Atende | Crítico |
|:---|:---|:---|:-:|:-:|
| Segmentos operáveis | 2 a 5 | 3 | ✅ | sim |
| Menor segmento | ≥ 10% da carteira | 23,8% | ✅ | sim |
| O preço distingue os segmentos | razão ≥ 1,3 e p < 0,05 | 1,84 (p ≈ 0) | ✅ | sim |
| Imóvel novo classificável | acurácia ≥ 85% | 96,9% | ✅ | sim |
| Separação dos grupos | silhueta ≥ 0,25 | 0,102 | ❌ | não |
| Cobertura da carteira | 100% com segmento | 100,0% | ✅ | não |

- **Preço.** O teste de Kruskal-Wallis verifica se os segmentos têm distribuições de
  preço diferentes, e a razão entre medianas mede se a diferença é grande o bastante
  para importar.
- **Imóvel novo classificável.** Uma random forest aprende a atribuir o segmento a
  partir das mesmas variáveis, em validação cruzada estratificada de 5 partes. A
  acurácia estima quantos imóveis novos seriam classificados corretamente — e viabiliza
  usar o modelo no dia a dia mesmo quando o algoritmo vencedor não classifica imóveis
  novos sozinho.

### Quanto vale cada segmento

| Segmento | Imóveis | % da carteira | Valor de venda (VGV) | % do VGV | Preço mediano | Área habitável | Qualidade | Idade |
|:---|--:|--:|--:|--:|--:|--:|--:|--:|
| **A** | 1.105 | 37,8% | US$ 268,8 mi | 50,8% | US$ 221.000 | 1.668 | 7 | 5 |
| **B** | 1.124 | 38,4% | US$ 173,4 mi | 32,8% | US$ 145.000 | 1.227 | 5 | 43 |
| **C** | 698 | 23,8% | US$ 87,0 mi | 16,4% | US$ 120.000 | 1.304 | 5 | 80 |

O **Segmento A** tem pouco mais de um terço dos imóveis e metade do valor de venda.
Nenhum segmento é pequeno demais para uma ação dedicada: o menor, C, tem 698 imóveis.

### A segmentação é uma tabela de preço disfarçada?

**Não foi medido na cadeia atual.** O critério de preço do 05 mede o oposto — que o
preço **difere** entre os segmentos —, e o preço mediano cai na mesma ordem de A a C,
porque é assim que os segmentos são nomeados.

Há um indício em sentido contrário na própria tabela acima: **B e C têm preços
medianos próximos** (US$ 145.000 e US$ 120.000) e área parecida, e são produtos muito
diferentes — uma térrea de 43 anos no subúrbio e uma casa de 80 anos no centro, com
garagem separada. A forma de responder com número é medir o índice de Rand ajustado
entre os segmentos e as faixas de preço, o que fica como próxima etapa.

### Impacto financeiro e operacional

A base de cálculo é o valor de venda anual da carteira segmentada (VGV ÷ 5 anos
cobertos pela base): **US$ 105,8 milhões por ano**. Sobre ele incide uma comissão de 6%,
o que dá uma receita de **US$ 6,35 milhões por ano**. Cada cenário aplica um ganho de
receita atribuído à segmentação, e o resultado do primeiro ano desconta a implantação
(US$ 150 mil, uma vez) e a manutenção (US$ 40 mil por ano).

| Cenário | Ganho | Receita extra/ano | Resultado do ano 1 | ROI do ano 1 | Payback |
|:---|--:|--:|--:|--:|--:|
| Pessimista | 1% | US$ 63.504 | −US$ 126.496 | −67% | 76,6 meses |
| Base | 3% | US$ 190.513 | US$ 513 | 0% | 12,0 meses |
| Otimista | 5% | US$ 317.522 | US$ 127.522 | 67% | 6,5 meses |

!!! warning "Premissas hipotéticas, e um cenário base que empata"
    Comissão, ganho de receita e custos são **hipóteses** do notebook, não números da
    Meridiano. O cenário base fecha o primeiro ano com US$ 513 de resultado — positivo
    pela regra de aprovação, mas, na prática, um empate. Um ganho real um pouco abaixo
    de 3% já não paga a implantação no ano 1. As premissas precisam ser validadas com a
    área comercial antes de qualquer investimento.

| Indicador operacional | Valor |
|:---|:---|
| Playbooks comerciais a manter | 3 (um por segmento) |
| Imóveis da carteira com segmento | 100,0% |
| Imóveis novos classificados corretamente | 96,9% |
| Maior segmento (concentração da carga) | 38,4% da carteira |
| Reciclagem recomendada | semestral ou a cada 10% de imóveis novos |

### Decisão formal

| | |
|:---|:---|
| Critérios críticos que falharam | **nenhum** |
| Ressalvas (não críticos) | **Separação dos grupos** |
| Resultado do ano 1 no cenário base | **US$ 513** |
| Decisão | **Aprovado para implantação** |

A regra de aprovação é dupla: nenhum critério crítico pode falhar **e** o cenário base
precisa se pagar no primeiro ano. As duas condições foram atendidas.

## 5.2 · Revisar o processo

### Análise das fases

| Fase | Notebook | O que entregou | Situação |
|:---|:---|:---|:---|
| 1 · Entendimento do negócio | — | Canvas e critérios de sucesso | ✅ |
| 2 · Entendimento dos dados | 00 · 01 | dicionário, escalas ordinais, exploração | ✅ lacuna 8 corrigida |
| 3 · Preparação | 02 · 03 | base tratada (2.927 × 90) · MinMax + *one-hot* (236 variáveis no modelo) | ⚠️ ver lacunas 1 e 2 |
| 4 · Modelagem | 04-0 · 04-1 · 04-2 · 04-3 | 11 algoritmos comparados · cotovelos · PCA/UMAP · regras de associação | ⚠️ ver lacunas 3 a 6 |
| 5 · Avaliação | 05 | esta página | — |

### Lacunas e erros identificados

As sete primeiras estão registradas no notebook 05; a oitava foi encontrada na revisão
da documentação e já foi corrigida.

| # | Lacuna | Onde | Efeito | Correção |
|:-:|:---|:---|:---|:---|
| 1 | `preco_venda` e `subclasse` continuam na base pré-processada (o dicionário declara as duas como "Discreta") | 03 · 07 | Agrupar pelo preço e depois descrever pelo preço seria circular; `subclasse` é código, não medida | Já retiradas no 04; **mover a remoção para o 03** |
| 2 | O *one-hot* com MinMax dá variância alta a categorias equilibradas | 03 | As categorias dominam a distância e o PCA (visto no 04-2) | Testar FAMD ou ponderar os blocos de variáveis |
| 3 | O modelo foi escolhido na base inteira, sem validação cruzada (Ward e DBSCAN não classificam imóveis novos) | 04-0 | Risco de escolher pelo acaso — os três primeiros estão separados por 0,002 de silhueta | Mitigado pela acurácia em validação cruzada; medir a estabilidade por reamostragem |
| 4 | Silhueta baixa em todos os algoritmos | 04-0 · 04-1 | Estrutura geométrica fraca em ~200 dimensões | Agrupar sobre as bases reduzidas do 04-2 |
| 5 | Constantes do projeto (silhueta mínima, teto de ruído) definidas à mão nos notebooks | 04-1 · 05 | Risco de divergir de `src/config.py` | Centralizar no config |
| 6 | K-Medianas e K-Medoids são classes definidas no notebook | 04-0 | O `.joblib` só carrega onde a classe existe | O 04-0 já salva `segmentos.csv`; mover as classes para `src` |
| 7 | Premissas financeiras sem validação | 05 | O impacto pode estar super ou subestimado | Validar comissão, ganho e custos com a área comercial |
| 8 | ~~Os rótulos das escalas ordinais do 00 não batiam com os da ingestão~~ | 00 · 01 · 02 | O nível "Típico" virava ausente e depois "item inexistente": 2.100 imóveis "sem garagem" contra 158 reais, seis colunas removidas no 02 | **Corrigida:** escala alinhada à ingestão, com conferência no próprio notebook 00 |

!!! info "O que a correção da lacuna 8 mudou"
    Na execução com o defeito, o vencedor era um mini batch k-means com **4 segmentos**,
    e o menor deles tinha **6,4%** da carteira — o critério crítico de tamanho
    reprovava o modelo e a decisão era **iterar mais**. Com as escalas corrigidas, a
    base ganhou seis colunas de qualidade e a qualidade típica deixou de virar "item
    inexistente". O vencedor passou a ter **3 segmentos**, o menor com 23,8%, e o modelo
    foi aprovado. É a iteração do CRISP-DM acontecendo de fato: a revisão do processo
    voltou à fase 2 e mudou a decisão da fase 5.

### Sumário das descobertas

- A carteira foi dividida em **3 segmentos** pelo mini batch k-means; o menor tem 23,8%
  dos imóveis.
- O preço mediano vai de **US$ 120.000** a **US$ 221.000** (1,84×) entre os segmentos.
- As variáveis que mais separam os segmentos, pela importância no classificador, são
  **fundação, idade do imóvel e zoneamento**.
- Um imóvel novo é atribuído ao segmento certo em **96,9%** dos casos.
- A separação geométrica é **fraca** (silhueta 0,102): os segmentos são faixas de uma
  carteira contínua, não grupos isolados.

### Limitações do modelo

- A base é histórica (vendas de 2006 a 2010 em Ames, EUA): a representatividade para a
  carteira atual da Meridiano precisa ser confirmada.
- O modelo descreve imóveis, não compradores: o perfil de quem compra cada segmento
  ainda não foi medido.
- O impacto financeiro depende de premissas não validadas.
- Os segmentos refletem as escolhas de pré-processamento do 03; com outro peso para o
  *one-hot*, eles podem mudar.

### Hipóteses derrubadas

| Hipótese | O que a cadeia mostrou |
|:---|:---|
| A maior silhueta indica o melhor modelo | As maiores silhuetas do 04-1 (DBSCAN 0,232, Mean Shift 0,224) são de partições degeneradas: 83,1% de ruído, ou um grupo com 99,9% da carteira |
| O DBSCAN encontrará grupos que os métodos de centroide não veem | Nenhuma configuração de densidade passou na regra de admissão |
| O cotovelo e a silhueta apontam o mesmo *k* | No k-means, o cotovelo está em *k* = 4 e a maior silhueta em *k* = 3 |
| A variável mais relevante para a redução é a mais relevante para o negócio | O topo do PCA é quase todo nominal por efeito da escala; o do UMAP é a idade (66,9%) |
| A escala ordinal declarada no 00 cobre todos os níveis da base | Não cobria 18 das 22 colunas; corrigida (lacuna 8) |

## 5.3 · Determinar as próximas etapas

A próxima ação sai de uma regra declarada antes de olhar o resultado:

| Situação | Próxima ação |
|:---|:---|
| Nenhum critério crítico falha e o cenário base se paga | **Implantação**, com as ressalvas registradas |
| Algum critério crítico falha ou o cenário base não se paga, mas a maioria dos critérios é atendida | **Iterar mais**: voltar às fases 3 e 4 com as correções das lacunas |
| A maioria dos critérios falha | **Novo projeto**: revisar a pergunta de negócio ou os dados |

!!! abstract "Próxima ação: implantação"
    **Justificativa:** 5 de 6 critérios atendidos; críticos com falha: nenhum; resultado
    do ano 1 no cenário base: US$ 513.

    **Ação para o critério não atendido:**

    - *Separação dos grupos:* reduzir a dimensionalidade (04-2) e revisar o peso do
      *one-hot* no 03.

    **Para a implantação:** expor o classificador para atribuir imóveis novos, publicar
    os playbooks por segmento e agendar a reciclagem. Antes da entrada em produção, falta
    dar persona e ação a cada segmento, medir a linha de base do monitoramento e validar
    as premissas financeiras — ver [Implementação](implementacao.md#plano-de-implantacao).
