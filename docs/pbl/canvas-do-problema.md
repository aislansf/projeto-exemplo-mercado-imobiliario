# Canvas do Problema

> Preenchido no Encontro 1 e revisado a cada encontro. É o artefato de rastreabilidade
> entre o pedido da diretoria e o que a equipe efetivamente fez.

**Equipe:** Meridiano · **Trilha:** Mercado imobiliário residencial ·
**Versão:** 1.0 · **Data:** 04/08/2026

---

## 1 · Contexto de negócio

A **Meridiano Imobiliária** compra, requalifica e revende imóveis residenciais, além de
intermediar vendas de terceiros. Opera em Ames, Iowa, com uma carteira histórica de
**2.350 imóveis comercializáveis**, depurados de 2.930 registros transacionados entre
2006 e 2010.

Quem decide o quê:

- **Diretoria Comercial** define a política de preço e o orçamento de cada ação;
- **Gerência de Ativos** decide o que fazer com cada unidade do estoque próprio;
- **Comitê de Aquisição** decide o que entra na carteira.

## 2 · A dor

Política **única** para 2.350 imóveis muito diferentes entre si: mesma régua de preço,
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

**Agrupamento** (segmentação), com **regras de associação** como validação
independente e **detecção de anomalia** como subproduto.

Não é previsão. O preço existe na base e **não** entra na modelagem — usá-lo devolveria
uma faixa de preço, que a diretoria já tem.

## 6 · Critério de sucesso técnico

| Critério | Valor |
|:---|:---|
| Silhueta mínima aceitável | **≥ 0,15** |
| Número de grupos | **entre 2 e 5** |
| Percentual máximo de ruído | **≤ 10%** |
| Estabilidade sob reamostragem de 80% | **ARI ≥ 0,75** |
| Menor segmento | **≥ 2% da carteira** |
| Independência do rótulo reservado | **ARI contra quartis de preço < 0,40** |

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

1. **Quantos grupos distintos emergem** entre os 2.350 imóveis quando se consideram
   porte, configuração, padrão construtivo e idade, com silhueta ≥ 0,15 e no máximo 5
   grupos?
   → *Resposta: **3**, com silhueta 0,1726.* [Escolha de k](../modelagem.md#a-escolha-de-k)

2. **Qual grupo concentra mais de 40% da receita** transacionada no período de 2006 a
   2010?
   → *Resposta: **S3 · Recente de alto padrão, com 44,8%**.*
   [Leitura de negócio](../avaliacao.md#quanto-vale-cada-segmento)

3. **Quais combinações de até três atributos construtivos** ocorrem juntas com suporte
   ≥ 10% e lift ≥ 1,30, e quais delas valem apenas dentro de um grupo específico?
   → ***Sem resposta nesta cadeia.*** A etapa de regras não foi executada sobre a
   carteira depurada; a decisão entre refazê-la ou revisar esta meta está entre as
   deliberações da sessão de encerramento.
   [O que esta fase não entregou](../modelagem.md#o-que-esta-fase-nao-entregou)

4. **Que percentual dos imóveis é classificado como ruído** por um DBSCAN calibrado com
   `minPts = 2 × d`, e qual é o perfil desses imóveis?
   → *Resposta: **a varredura não encontrou configuração admissível** — nenhum `eps`
   entrega simultaneamente ruído ≤ 10% e de 2 a 5 grupos.*
   [DBSCAN](../modelagem.md#por-que-dbscan-e-mean-shift-falharam)

5. **A segmentação é distinguível de uma faixa de preço**, medida por índice de Rand
   ajustado abaixo de 0,40 contra os quartis de `preco_venda`?
   → *Resposta: **sim — ARI de 0,3345**.*
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

As três ações definidas estão em [As três linhas de produto](../modelagem.md#as-tres-linhas-de-produto).

---

## Revisões do Canvas

| Encontro | O que mudou | Motivo |
|:-:|:---|:---|
| 1 | Versão inicial | — |
| 2 | Acrescentado o critério de **estabilidade ARI ≥ 0,75** | A silhueta sozinha não distingue estrutura real de artefato da amostra |
| 3 | Acrescentado o critério **ARI contra preço < 0,40** | Surgiu a dúvida sobre a segmentação ser uma faixa de preço disfarçada |
| 4 | Meta de regras revista de "suporte ≥ 5%" para **"≥ 10%"** | A 5% o resultado foi de 6.274 regras, volume que nenhuma área comercial lê |
| 5 | Nenhuma | — |

Um Canvas que não muda entre encontros é sinal de que ninguém o consultou.
