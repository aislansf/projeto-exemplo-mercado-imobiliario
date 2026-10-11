# Segmentação da carteira residencial — relatório final

**Meridiano Imobiliária** · CRISP-DM, fases 1 a 6 · modelo 2.0.0 · semente 42

> Documento gerado pelo notebook `notebooks/06-implantacao.ipynb`. Todos os números vêm dos
> manifestos e tabelas da cadeia — nenhum foi digitado à mão.

## 1 · Sumário executivo

* A carteira de **2.350 imóveis** se organiza em **3 linhas de produto** com perfil,
  valor e ação distintos. O modelo é K-Means com k = 3, silhueta 0.1726 e
  estabilidade ARI 0.9575 sob reamostragem.
* As linhas **não reproduzem uma faixa de preço**: ARI 0.3345 contra os
  quartis de `preco_venda`, contra o teto de 0.40 declarado no Canvas. O preço
  ficou fora de todo artefato que alimentou algoritmo, e a verificação foi feita depois.
* A linha **S3 · Recente de alto padrão** concentra 44.8% da receita
  transacionada com 32.7% das unidades; a linha
  **S2 · Amplo para requalificar** tem o menor preço por pé² da carteira e é onde a reforma tem
  a maior alavanca.
* **339 imóveis (14.4%)** ficam na faixa de
  fronteira entre segmentos e vão para revisão humana em vez de ação automática.

## 2 · O problema

A Meridiano opera a carteira residencial com uma política de duas faixas de preço. A pergunta
que originou o projeto: **existem grupos de imóveis com necessidade comercial distinta que a
faixa de preço não enxerga?** O critério de sucesso, declarado antes de qualquer modelagem, é
o do Canvas do Problema: de 2 a 5 grupos, silhueta
≥ 0.15, estabilidade ARI ≥ 0.75, menor
grupo ≥ 2% da carteira e ARI < 0.40
contra os quartis de preço.

## 3 · Metodologia

| Fase | O que decidiu | Evidência |
|:--|:--|:--|
| 1 · Entendimento do negócio | Canvas do Problema com objetivo, critérios técnicos e de negócio, e cinco perguntas SMART | docs/pbl/canvas-do-problema.md |
| 2 · Entendimento e ajuste dos dados | 2.930 registros brutos → 2.350 imóveis curados, com 580 removidos por regra declarada | data/processed/manifesto_curadoria.json |
| 3 · Preparação dos dados | 17 variáveis no espaço euclidiano; 3 reservadas fisicamente fora do arquivo de modelagem | data/processed/manifesto_preparacao.json |
| 4 · Modelagem | K-Means com k = 3, escolhido pela regra declarada antes do resultado; 4 modelos reprovados com o motivo registrado | data/processed/manifesto_modelagem.json |
| 5 · Avaliação | 7 de 7 critérios técnicos atendidos; 126 configurações varridas; veredito de prosseguir | data/processed/manifesto_avaliacao.json |
| 6 · Implantação | Pacote 2.0.0 carimbado, contrato de entrada, catálogo de 3 linhas, regra de fronteira e plano de monitoramento com 6 indicadores | data/processed/manifesto_implantacao.json |

Três decisões de método sustentam o resto:

1. **o rótulo foi reservado fisicamente.** `preco_venda`, `preco_por_pe2` e `bairro` ficaram
   fora do arquivo de modelagem, e não apenas fora do algoritmo por disciplina;
2. **os critérios de aceitação foram escritos antes** de qualquer algoritmo rodar, e lidos do
   manifesto nas fases seguintes — nunca redigitados;
3. **cada fase gravou um manifesto** com o que decidiu e com que medida, o que tornou possível
   auditar a cadeia inteira na fase 5 e reconstruí-la aqui sem consultar ninguém.

## 4 · Resultados

| Resultado | Valor | Critério declarado |
|:--|:--|:--|
| Linhas de produto | 3 | entre 2 e 5 |
| Coesão (silhueta) | 0.1726 | ≥ 0.15 |
| Estabilidade (ARI sob reamostragem) | 0.9575 | ≥ 0.75 |
| Independência do preço (ARI contra quartis) | 0.3345 | < 0.40 |
| Receita na linha líder | 44.8% | > 40% numa única linha (SMART 2) |
| Validação externa (V de Cramér contra bairro) | 0.630 | sem piso declarado — `bairro` nunca entrou em algoritmo nenhum |

### As 3 linhas de produto

| Código | Linha | Imóveis | % unidades | % receita | Teto de reforma |
|:--|:--|:--|:--|:--|:--|
| S1 | Compacto herdado | 914 | 38.9 | 27.3 | 6% do valor de avaliação |
| S2 | Amplo para requalificar | 667 | 28.4 | 27.9 | 12% do valor de avaliação |
| S3 | Recente de alto padrão | 769 | 32.7 | 44.8 | sem reforma — o imóvel já está no padrão |

## 5 · Insights

| # | Insight | Evidência | Dono |
|:--|:--|:--|:--|
| 1 | A segmentação não é uma tabela de preço com outro nome | ARI 0.3345 contra os quartis de preço, teto de 0.40 | Diretoria Comercial |
| 2 | Um terço das unidades responde por 44.8% da receita | S3 · 769 imóveis, 32.7% da carteira | Diretoria Comercial |
| 3 | A alavanca de reforma está no S2, e não no segmento mais caro | S2 tem 105.42 US$/pé² contra 133.90 do S3, com 55% mais área que o S1 | Gerência de Ativos |
| 4 | O estoque herdado é decisão de destino, não de preço | S1 · 38.9% das unidades e 27.3% da receita, com 39 anos desde a última reforma | Gerência de Ativos |
| 5 | Os segmentos existem fora do espaço em que foram criados | V de Cramér 0.630 contra `bairro`, variável que nenhum algoritmo viu | Diretoria Comercial |
| 6 | Uma das três linhas é assistida — o modelo diz onde não sabe | 25.8% do S2 na faixa de fronteira · 339 imóveis da carteira para revisão humana | Gerência de Ativos |
| 7 | A estrutura sobreviveu a um choque de mercado | PSI máximo 0.0369 entre 2006–2008 e 2009–2010 · silhueta 0.1712 → 0.1751 · ARI 0.9366 na reciclagem simulada | Área de Dados |

## 6 · As perguntas SMART, respondidas

| Pergunta | Resposta medida nesta cadeia | Situação |
|:--|:--|:--|
| Quantos grupos distintos emergem, com silhueta ≥ 0,15 e no máximo 5 grupos? | 3 (silhueta 0.1726; base de 2.350 imóveis) | resposta mudou |
| Qual grupo concentra mais de 40% da receita transacionada? | Segmento 2, com 44.8% | resposta mudou de rótulo, conclusão preservada |
| Que combinações de até três atributos ocorrem juntas com suporte ≥ 10% e lift ≥ 1,30? | não refeita — a cadeia 00–04 não contém a etapa de regras | sem resposta na cadeia atual |
| Que percentual dos imóveis é classificado como ruído por um DBSCAN com minPts = 2 × d? | a fase 4 varreu eps e não encontrou configuração com ruído dentro do teto e número de grupos na faixa | resposta mudou |
| A segmentação é distinguível de uma faixa de preço (ARI < 0,40)? | sim — ARI de 0.3345 | conclusão confirmada, número atualizado |

## 7 · Implantação

* **Pacote 2.0.0**, carimbado por SHA-256 (`bca92cfd54faf635…`): receita e
  agrupador no mesmo objeto, com o mapa canônico dos segmentos;
* **contrato de entrada** com 17 campos, faixa aceita, faixa observada e padrão;
* **regra de atribuição com faixa de confiança**: corte de fronteira 0.915,
  calibrado sobre a carteira, com teto operacional de 15%;
* **entrada em produção em 3 janelas**, a primeira em sombra por 30 dias;
* **7 entregas** com consumidor, meio, periodicidade, prazo e responsável.

## 8 · Monitoramento e manutenção

Sem gabarito, o que se acompanha é a entrada, a coesão e a composição. A primeira leitura,
feita entre 2006–2008 e 2009–2010, está publicada:

* PSI máximo **0.0369** (limiar de ação 0.25);
* silhueta **0.1712 → 0.1751** entre os dois períodos;
* maior variação de composição **3.79 p.p.** (limiar 10 p.p.);
* reciclagem simulada com **ARI 0.9366** contra a partição vigente (piso
  0.75).

| Indicador | Periodicidade | Gatilho | Responsável |
|:--|:--|:--|:--|
| 1 · Data drift dos atributos | mensal | PSI ≥ 0.25 em qualquer atributo, ou ≥ 0.1 em três simultaneamente | Área de Dados |
| 2 · Cluster drift — coesão | trimestral | silhueta < 0.15 por dois trimestres consecutivos | Área de Dados |
| 3 · Composição da carteira | mensal | variação ≥ 10 p.p. em qualquer linha contra a linha de base | Diretoria Comercial |
| 4 · Imóveis de fronteira | mensal | acima de 15% das entradas do mês | Gerência de Ativos |
| 5 · Volume e integridade da carga | a cada carga | queda de volume > 30%, rejeição > 5% dos registros, ou carimbo divergente | Engenharia de Dados |
| 6 · Efeito da ação diferenciada | trimestral | meta não atingida em dois trimestres consecutivos | Diretoria Comercial |

## 9 · O que não foi entregue

* **4 dos 5 critérios de negócio do Canvas continuam
  sem leitura**: três dependem de campos que o sistema comercial ainda não coleta — preço
  anunciado, data de anúncio e custo de reforma executada — e o quarto depende da decisão
  unidade a unidade do estoque herdado, que ainda não começou;
* **as regras de associação e a detecção de anomalia**, prometidas no Canvas §5, não fazem
  parte desta cadeia — a decisão sobre refazê-las ou revisar a meta está entre as deliberações
  da sessão de encerramento;
* **a documentação publicada descreve o experimento anterior** em 6
  ocorrências, e precisa ser reescrita antes de qualquer divulgação externa;
* **o candidato k = 4** foi reprovado por 0.0112 de silhueta e
  fica registrado para revisão do critério, não para revisão do resultado.

## 10 · Como reproduzir

```bash
uv sync
uv run invoke notebooks
```

A semente do projeto é 42. A cadeia reexecutada devolve a mesma partição — a fase 5
mediu ARI 1.0000 na reexecução.
