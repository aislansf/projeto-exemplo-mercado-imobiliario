# Quadro PBL — os cinco encontros

> Preenchido no início de cada encontro. É a evidência do raciocínio, não do resultado.
>
> **Regra do quadro:** uma hipótese só sai da coluna 2 quando houver evidência que a
> confirme (vira Fato) ou que a refute (vira nota de rodapé no relatório). Hipóteses
> derrubadas **não são apagadas** — são parte do resultado.

---

## Encontro 1 — Confronto com o problema

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| A base tem 2.930 imóveis e 82 colunas | O preço deve ser o melhor separador — imóvel caro e imóvel barato são produtos diferentes | Como validar um agrupamento quando não existe gabarito? | Materializar a camada bruta com manifesto |
| Não há coluna que classifique o imóvel em linha de produto | Deve haver 3 ou 4 grupos "naturais": entrada, médio, alto padrão | O que é silhueta, e a partir de que valor ela é aceitável? | Preencher o Canvas com a diretoria |
| `SalePrice` existe na base | 82 colunas devem ser demais; a maioria deve ser descartável | Como se escolhe *k*? | Definir os critérios técnicos de sucesso |
| O orçamento comporta 5 ações | | Qual a diferença entre PCA e LDA, e por que isso importa aqui? | Levantar o perfil de qualidade da base |

**Socialização.** A discussão travou em uma pergunta: *se o preço é o melhor separador,
por que não usá-lo?* A resposta que a equipe construiu — e que virou o eixo do projeto
— é que usá-lo devolveria uma tabela de preço, que a diretoria **já tem**, e que a
pergunta feita era outra.

---

## Encontro 2 — Análise exploratória e preparação

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ `Mas Vnr Type` tem 60,6% de ausência… **ou não** | A ausência de 60% em `Mas Vnr Type` inviabiliza a coluna | O que é uma sentinela, e como se distingue de nulo real? | Inventariar as sentinelas literais do arquivo |
| ✅ As 5 colunas de garagem faltam nos mesmos 157–159 imóveis | Ausência blocada = ausência estrutural | MCAR, MAR, MNAR: qual mecanismo se aplica a `Lot Frontage`? | Aplicar rótulo próprio, não imputação |
| ✅ A área do terreno tem assimetria de 13,20 | Os 125 discrepantes de área do terreno são erro de digitação | Quando remover um outlier, e quando transformá-lo? | Testar `log1p` e medir o efeito |
| ✅ 3 colunas são praticamente constantes | | Por que a escala importa em algoritmo baseado em distância? | Executar o experimento com 4 escalonadores |

**Hipótese derrubada.** «A ausência de 60% em `Mas Vnr Type` inviabiliza a coluna.»
O inventário de sentinelas mostrou que 1.752 dos 1.775 "ausentes" são a **categoria
`None`**, convertida em nulo pela leitura padrão do `pandas`. A ausência real é de
0,8%.

**Hipótese derrubada.** «Os discrepantes de área do terreno são erro de digitação.»
São lotes grandes legítimos. Removê-los apagaria o segmento de alto padrão.

---

## Encontro 3 — Clusterização particional e hierárquica

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ Sem padronização a silhueta é 0,35; com `StandardScaler`, 0,18 | A silhueta maior indica o melhor pré-processamento | O que a silhueta mede, exatamente? | Medir por qual atributo cada versão particionou |
| ✅ Trocar o escalonador muda a partição (ARI máximo 0,354) | Gower vai dar o melhor resultado, porque trata dados mistos | Como funciona a dissimilaridade de Gower? | Implementar Gower e K-Medoids |
| ✅ A silhueta é máxima em k = 2 e cai depois | k = 5 é o melhor, porque o orçamento comporta 5 | Como saber se um agrupamento se reproduz? | Testar estabilidade por reamostragem |
| | O dendrograma vai confirmar o k do K-Means | O que é coeficiente cofenético? | Comparar 4 critérios de ligação |

**Hipótese derrubada.** «A silhueta maior indica o melhor pré-processamento.»
Sem padronização, `area_porao` (amplitude 3.206) domina a distância e o K-Means
particiona quase por ela sozinha. A silhueta é alta porque um agrupamento
unidimensional é trivialmente bem separado.

**Hipótese derrubada.** «Gower vai dar o melhor resultado.» Com peso igual por
variável, `estilo` domina: um grupo com 93% de casas térreas, outro com 90% de
sobrados. Fato construtivo, não linha de produto.

**Hipótese derrubada.** «k = 5 é o melhor.» O ARI sob reamostragem cai de 0,94 (k = 4)
para 0,44 (k = 5). A quinta linha não se reproduz.

---

## Encontro 4 — Densidade, GMM e redução de dimensionalidade

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ k = 3, com silhueta 0,1726 e estabilidade 0,9575 | O DBSCAN vai encontrar grupos de forma arbitrária que o K-Means não vê | Como calibrar `eps` sem tentativa e erro? | Construir o gráfico k-distância |
| ✅ Ward tem o pior cofenético e o melhor equilíbrio | O BIC vai indicar o k do GMM claramente | Por que o BIC penaliza a complexidade? | Varrer k e 4 tipos de covariância |
| ✅ `average` e `single` produzem um grupo de 1 imóvel | O Kernel PCA vai dar uma projeção melhor | O que se perde ao usar Kernel PCA? | Comparar 3 kernels |
| | | Por que o LDA não pode entrar na modelagem? | Reservar o LDA para a avaliação |

**Hipótese derrubada.** «O DBSCAN vai encontrar grupos que o K-Means não vê.» Em 21
dimensões padronizadas não há vale de densidade: em toda a faixa de `eps`, um grupo com
mais de 90% da carteira. O Mean Shift falha pelo mesmo motivo.

**Hipótese derrubada.** «O BIC vai indicar o k do GMM claramente.» Nenhuma das quatro
curvas apresenta mínimo entre k = 2 e 10 — os dados não são uma mistura de gaussianas
separadas, e cada componente a mais sempre melhora a verossimilhança.

**Fato novo, inesperado.** O ruído do DBSCAN, que parecia resíduo, virou a entrega do
objetivo 4: 53 imóveis fora de padrão, com perfil descrito e lista com identificador.

---

## Encontro 5 — Regras, avaliação e implantação

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ Apriori, Eclat e FP-Growth devolvem os mesmos 1.597 conjuntos | Suporte de 5% vai dar um conjunto de regras utilizável | Como calibrar suporte e confiança? | Medir o efeito do limiar sobre o volume |
| ✅ Lift ≤ 1 significa regra pior que o acaso | As regras de cada segmento serão as mesmas da base inteira | Por que lift, se já há confiança? | Cruzar regras por segmento |
| ✅ A segmentação tem ARI 0,31 contra quartis de preço | Regras com lift alto são sempre descobertas | O que é *data drift* quando não há gabarito? | Medir PSI entre dois períodos |
| ✅ Nenhum atributo em drift de ação | | | Serializar o pipeline e publicar a aplicação |

**Hipótese derrubada.** «Suporte de 5% vai dar um conjunto utilizável.» Devolveu 6.274
regras. O limiar foi recalibrado para 10%, com evidência.

**Hipótese derrubada.** «Regras com lift alto são sempre descobertas.»
`tem 2º pavimento → estilo:2Story` tem lift 3,03 e é uma **tautologia**: `2Story`
significa dois pavimentos. Nenhuma métrica detecta isso — só o conhecimento do domínio.

**Hipótese confirmada.** «As regras de cada segmento serão as mesmas da base inteira.»
**Refutada**: 252 das 280 regras de segmento são exclusivas dele. A segmentação e as
regras se sustentam mutuamente.

---

## Consolidado das hipóteses

| # | Hipótese | Destino | Evidência |
|:-:|:---|:---|:---|
| H1 | O preço é o melhor separador e deveria ser usado | **descartada por método** | Critério eliminatório: descaracterizaria o problema |
| H2 | A ausência de 60% em `Mas Vnr Type` inviabiliza a coluna | **derrubada** | `eda-exploratoria/valores-ausentes.csv` |
| H3 | Os discrepantes de área do terreno são erro | **derrubada** | `eda-exploratoria/valores-discrepantes.csv` |
| H4 | A silhueta maior indica o melhor pré-processamento | **derrubada** | `preparacao/sensibilidade-a-escala.csv` |
| H5 | Gower dará o melhor resultado | **derrubada** | `modelagem/gower-por-estilo.csv` |
| H6 | O maior *k* dentro do orçamento é o melhor | **derrubada** | `modelagem/decisao-de-k.csv` |
| H7 | O DBSCAN encontrará grupos que o K-Means não vê | **derrubada** | `modelagem/densidade-dbscan-e-mean-shift.csv` |
| H8 | O BIC indicará o *k* do GMM claramente | **derrubada** | `modelagem/gmm-selecao.csv` |
| H9 | A maior silhueta da varredura indica o melhor modelo | **derrubada** | `avaliacao/as-dez-maiores-silhuetas.csv` |
| H10 | Reduzir a dimensão melhora o agrupamento | **derrubada** | `avaliacao/sensibilidade-de-dimensao.csv` |
| H11 | O modelo pode agir sozinho em toda a carteira | **derrubada** | `implantacao/calibracao-da-fronteira.csv` |
| H12 | Haverá 3 ou 4 grupos naturais | **confirmada** | 3 grupos, estáveis (ARI 0,9575) |

Onze hipóteses derrubadas e uma confirmada. É o retrato honesto de como um projeto de
dados anda: a maior parte do trabalho é descobrir que o palpite inicial estava errado —
e registrar por quê.
