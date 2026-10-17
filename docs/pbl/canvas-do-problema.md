# Canvas do Problema

> Preenchido no Encontro 1 e revisado a cada encontro. É o artefato de rastreabilidade
> entre o pedido da diretoria e o que a equipe efetivamente fez.

**Equipe:** Meridiano · **Trilha:** Mercado imobiliário residencial ·
**Versão:** 1.1 · **Data:** 16/10/2026

---

## 1 · Contexto de negócio

A **Meridiano Imobiliária** compra, requalifica e revende imóveis residenciais, além de
intermediar vendas de terceiros. Opera em Ames, Iowa, com uma carteira histórica de
**2.927 imóveis**, ajustados a partir de 2.930 registros transacionados entre 2006 e
2010.

Quem decide o quê:

- **Diretoria Comercial** define a política de preço e o orçamento de cada ação;
- **Gerência de Ativos** decide o que fazer com cada unidade do estoque próprio;
- **Comitê de Aquisição** decide o que entra na carteira.

## 2 · A dor

Política **única** para quase três mil imóveis muito diferentes entre si: mesma régua de preço,
mesmo teto de reforma, mesmo canal de anúncio.

Quem sofre com isso:

- a **Gerência de Ativos**, que investe reforma em imóvel que já está no padrão e
  deixa de investir onde o retorno existiria;
- os **corretores**, que anunciam imóvel de entrada pelo mesmo canal caro do alto
  padrão;
- o **Comitê de Aquisição**, que compra sem saber em que linha o imóvel vai cair.

## 3 · Objetivo de negócio

Substituir a política única por **políticas por linha de produto**, de modo que o
capital de reforma vá para onde tem retorno e o esforço de corretagem vá para onde tem
margem.

> Não é "fazer um K-Means". É decidir onde alocar capital.

## 4 · Critério de sucesso do negócio

| Métrica | Meta |
|:---|:---|
| Percentual do estoque com linha de produto atribuída | 100% em 30 dias |
| Ganho de preço sobre custo de reforma, no segmento de maior retorno | ≥ 1,8× |
| Tempo médio de giro do segmento de entrada | de 90 para 60 dias |
| Preço realizado ÷ preço anunciado no alto padrão | ≥ 0,97 |
| Percentual do estoque herdado com destino definido | 100% em 12 meses |

## 5 · Meta de mineração

**Agrupamento** (segmentação), com **regras de associação** como leitura
independente da carteira e **detecção de anomalia** como subproduto.

Não é previsão. O preço existe na base e **não** entra na modelagem — usá-lo devolveria
uma faixa de preço, que a diretoria já tem.

## 6 · Critério de sucesso técnico

| Critério | Valor | Peso |
|:---|:---|:---|
| Número de segmentos | **entre 2 e 5** | crítico |
| Menor segmento | **≥ 10% da carteira** | crítico |
| O preço distingue os segmentos | **mais caro ≥ 1,3× o mais barato, e Kruskal-Wallis p < 0,05** | crítico |
| Imóvel novo classificável | **acurácia ≥ 85%** em validação cruzada | crítico |
| Separação dos grupos | **silhueta ≥ 0,25** | não crítico |
| Cobertura da carteira | **100% com segmento** | não crítico |

Um critério crítico reprovado barra a implantação. São os valores que o notebook
`05-avaliacao` aplica (meta 1.1).

## 7 · Entidade de análise

**Um imóvel residencial transacionado** (`pid`).

Uma linha da base é uma transação de um imóvel. Não é o bairro (a variação dentro do
bairro desapareceria) nem o comprador (não há dado sobre ele).

## 8 · Fonte e volume dos dados

| Item | Valor |
|:---|:---|
| Origem | Ames Housing — De Cock (2011), *Journal of Statistics Education*, 19(3) |
| Acesso | Download direto de `jse.amstat.org`, sem cadastro |
| Volume | 2.930 linhas × 82 colunas · 0,96 MB |
| Período | 2006 a 2010 |
| Permissões | Uso educacional e de pesquisa, com citação obrigatória |
| Dado pessoal | Nenhum — `PID` é a matrícula do imóvel |

## 9 · Perguntas orientadas a dados (SMART)

1. **Quantos grupos distintos emergem** entre os imóveis da carteira quando se
   consideram porte, configuração, padrão construtivo e idade, com no máximo 5 grupos?
   → *Resposta: **3**, pelo mini batch k-means — com silhueta de 0,102, abaixo da
   meta de 0,25: a carteira se divide em faixas contínuas, não em grupos isolados.*
   [A escolha do modelo](../modelagem.md#a-escolha-do-modelo)

2. **Qual grupo concentra mais de 40% da receita** transacionada no período de 2006 a
   2010?
   → *Resposta: **Segmento A, com 50,8% do valor de venda** e 37,8% dos imóveis.*
   [Leitura de negócio](../avaliacao.md#quanto-vale-cada-segmento)

3. **Quais combinações de até três atributos construtivos** ocorrem juntas com
   frequência, e quais delas valem apenas dentro de um grupo específico?
   → *Resposta parcial: o notebook 04-3 encontrou **23.403 regras** com suporte ≥ 15%,
   confiança ≥ 60% e lift ≥ 1,20 na carteira inteira. O cruzamento com os segmentos
   não foi feito.* [Regras de associação](../modelagem.md#regras-de-associacao)

4. **Que percentual dos imóveis é classificado como ruído** por um DBSCAN calibrado
   pela curva k-distância, e qual é o perfil desses imóveis?
   → *Resposta: **nenhuma configuração foi admitida**. A de maior silhueta deixa 83,1%
   da carteira como ruído.* [DBSCAN](../modelagem.md#por-que-dbscan-e-mean-shift-falharam)

5. **A segmentação é distinguível de uma faixa de preço?**
   → *Resposta: **não foi medido na cadeia atual.** A avaliação mede o oposto — que o
   preço difere entre os segmentos (1,84×) —, e o preço mediano cai na mesma ordem de
   A a C. Se os segmentos são mais que uma faixa de preço continua em aberto.*
   [Confronto](../avaliacao.md#a-segmentacao-e-uma-tabela-de-preco-disfarcada)

## 10 · Restrições e riscos

| Tipo | Descrição |
|:---|:---|
| **Orçamentária** | No máximo 5 ações diferenciadas — o teto de *k* |
| **Legal** | Citação obrigatória do artigo original; sem licença aberta nomeada |
| **Ética** | Nenhum dado pessoal na base; `PID` é matrícula do imóvel |
| **Temporal** | Período inclui a crise imobiliária de 2008 |
| **Qualidade** | Sentinelas literais (`NA`, `None`) que a leitura padrão interpreta errado |
| **Metodológica** | Risco de usar o rótulo reservado por descuido — critério eliminatório |
| **Escopo** | A base descreve o produto, não o comprador: não há segmentação de demanda possível |

## 11 · Ação esperada por grupo

Para cada linha de produto encontrada, a diretoria decidirá:

1. **política de precificação** (por giro ou por margem);
2. **teto de investimento em reforma**, como percentual do valor de avaliação;
3. **canal de venda** (digital, corretagem tradicional, corretagem dedicada,
   investidor);
4. **métrica de acompanhamento**, com meta.

> Se a resposta a "que decisão será tomada com o resultado" fosse "nenhuma", o projeto
> não deveria existir.

As ações por segmento ainda não foram definidas: os três segmentos têm perfil, mas não
política — ver [Os três segmentos](../modelagem.md#os-tres-segmentos).

---

## Revisões do Canvas

| Encontro | O que mudou | Motivo |
|:-:|:---|:---|
| 1 | Versão inicial | — |
| 2 | Acrescentado o critério de **estabilidade ARI ≥ 0,75** | A silhueta sozinha não distingue estrutura real de artefato da amostra |
| 3 | Acrescentado o critério **ARI contra preço < 0,40** | Surgiu a dúvida sobre a segmentação ser uma faixa de preço disfarçada |
| 4 | Meta de regras revista de "suporte ≥ 5%" para **"≥ 10%"** | A 5% o resultado foi de 6.274 regras, volume que nenhuma área comercial lê |
| 5 | Nenhuma | — |
| 6 | Critérios técnicos substituídos pelos da meta 1.1 do notebook 05: menor segmento ≥ **10%**, razão de preço ≥ **1,3**, acurácia ≥ **85%**, silhueta ≥ **0,25** (não crítico) | A cadeia atual mede operabilidade e uso no dia a dia; estabilidade por reamostragem e ARI contra o preço deixaram de ser medidos |

Um Canvas que não muda entre encontros é sinal de que ninguém o consultou.
