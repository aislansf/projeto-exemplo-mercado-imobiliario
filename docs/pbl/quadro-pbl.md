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
| O orçamento comporta 5 ações | | Qual a diferença entre PCA e UMAP, e por que isso importa aqui? | Gerar o dicionário de dados e as escalas ordinais |

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
| ✅ A área do terreno tem assimetria de 12,8 | Os discrepantes de área do terreno são erro de digitação | Quando remover um outlier, e quando transformá-lo? | Medir os limites de Tukey |
| ✅ 3 colunas são praticamente constantes | A escala ordinal declarada no 00 cobre todos os níveis da base | Por que a escala importa em algoritmo baseado em distância? | Normalizar com MinMax e codificar as nominais |

**Hipótese derrubada.** «A ausência de 60% em `Mas Vnr Type` inviabiliza a coluna.»
O inventário de sentinelas mostrou que 1.752 dos 1.775 "ausentes" são a **categoria
`None`**, convertida em nulo pela leitura padrão do `pandas`. A ausência real é de
0,8%.

**Hipótese derrubada.** «Os discrepantes de área do terreno são erro de digitação.»
São lotes grandes legítimos, até 215.245 pés². Removê-los apagaria o alto padrão.

**Hipótese derrubada — tarde.** «A escala ordinal do 00 cobre todos os níveis da
base.» A escala chamava de "Médio" o nível que a ingestão chama de "Típico", e o mesmo
desencontro atingia 18 colunas. A falha só apareceu na revisão da documentação, depois
da primeira avaliação: 2.100 imóveis tinham ficado "sem garagem", contra 158 reais.
Corrigida a escala e reexecutada a cadeia, o resultado mudou — de 4 segmentos
reprovados para 3 aprovados. É a
[lacuna 8](../avaliacao.md#lacunas-e-erros-identificados).

---

## Encontro 3 — Clusterização particional e hierárquica

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ A base tem 236 variáveis, mas posto 207: o *one-hot* cria 29 direções nulas | A maior silhueta indica o melhor modelo | O que a silhueta mede, exatamente? | Comparar todos os algoritmos na mesma régua: silhueta euclidiana |
| ✅ Nenhuma configuração aprovada passa de 0,102 de silhueta | O cotovelo e a silhueta apontam o mesmo *k* | Por que as distâncias se concentram em alta dimensão? | Traçar peso e silhueta de cada algoritmo, de *k* = 1 a 10 |
| ✅ O Mean Shift de maior silhueta (0,224) junta 99,9% num grupo | Haverá 3 ou 4 grupos naturais | Como comparar algoritmos que minimizam pesos diferentes? | Declarar uma regra de admissão antes de ler a silhueta |

**Hipótese derrubada.** «A maior silhueta indica o melhor modelo.» As maiores silhuetas
do 04-1 são de partições degeneradas: o DBSCAN marca 0,232 com 83,1% de ruído e o Mean
Shift, 0,224 com 99,9% dos imóveis num grupo só. Uma partição que separa meia dúzia de
exceções é trivialmente "bem separada". Daí a regra de admissão: nenhum grupo com mais
de 90% da carteira.

**Hipótese derrubada.** «O cotovelo e a silhueta apontam o mesmo *k*.» No k-means, o
cotovelo do peso está em *k* = 4 e a maior silhueta em *k* = 3.

**Hipótese confirmada, com ressalva.** «Haverá 3 ou 4 grupos naturais.» Os três
primeiros colocados do 04-0 e o vencedor do 04-1 escolhem **3 segmentos** — mas a
silhueta de 0,102 diz que eles são faixas de uma carteira contínua, e não grupos
isolados.

---

## Encontro 4 — Densidade, GMM e redução de dimensionalidade

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ O DBSCAN de maior silhueta deixa 83,1% como ruído | O DBSCAN vai encontrar grupos de forma arbitrária que o K-Means não vê | Como calibrar `eps` sem tentativa e erro? | Tirar os raios da curva k-distância |
| ✅ O UMAP é explicado em 95,7% por um modelo substituto | A variável mais relevante na redução é a mais relevante para o negócio | Como explicar uma redução não linear, que não tem cargas? | Explicar o UMAP com um modelo substituto |
| ✅ O PCA precisa de 59 componentes para 90% da variância | Reduzir a dimensão vai melhorar o agrupamento | Por que o MinMax favorece as binárias equilibradas? | Gravar as bases reduzidas para agrupar sobre elas |

**Hipótese derrubada.** «O DBSCAN vai encontrar grupos que o K-Means não vê.» Em ~200
dimensões a densidade se dilui e não há vale entre grupos. Nenhuma configuração de
DBSCAN ou Mean Shift passou na regra de admissão.

**Hipótese derrubada.** «A variável mais relevante na redução é a mais relevante para o
negócio.» O topo do PCA é quase todo nominal (`bairro`, revestimentos, `estilo`) porque,
com o MinMax, uma binária dividida meio a meio varia mais que uma contínua. O UMAP, que
preserva vizinhança, é dominado pela idade (66,9%).

**Hipótese em aberto.** «Reduzir a dimensão vai melhorar o agrupamento.» As bases
reduzidas estão gravadas, mas o agrupamento sobre elas ainda não foi feito.

---

## Encontro 5 — Regras, avaliação e implantação

| FATOS | HIPÓTESES | QUESTÕES DE APRENDIZAGEM | PLANO DE AÇÃO |
|:---|:---|:---|:---|
| ✅ Apriori, Eclat e FP-Growth devolvem os mesmos 31.601 conjuntos | Regras com lift alto são sempre descobertas | Por que lift, se já há confiança? | Separar as regras que terminam no preço |
| ✅ 23.403 regras fortes, com confiança ≥ 60% e lift ≥ 1,20 | O vencedor da silhueta passa nos critérios de negócio | Como avaliar um agrupamento pelo uso, e não pela geometria? | Declarar os critérios de sucesso no código, antes de ler o resultado |
| ✅ Um classificador acerta o segmento de 96,9% dos imóveis novos | A segmentação se paga no primeiro ano | Como estimar o impacto financeiro sem dado de venda futura? | Estimar três cenários com premissas declaradas |
| ✅ O menor segmento tem 23,8% da carteira | | | Decidir a próxima ação por regra declarada |

**Hipótese derrubada.** «Regras com lift alto são sempre descobertas.» As de maior lift
ligam itens derivados uns dos outros — `tem_segundo_pavimento` com
`estilo=Dois pavimentos`. São verdadeiras e não ensinam nada.

**Hipótese confirmada — na segunda execução.** «O vencedor da silhueta passa nos
critérios de negócio.» Na primeira execução, com o defeito das escalas, o vencedor
tinha 4 segmentos e o menor, com 6,4% da carteira, reprovava o critério crítico de
tamanho. Com as escalas corrigidas, o vencedor tem 3 segmentos, o menor com 23,8%, e
passa em todos os critérios críticos.

**Hipótese em aberto.** «A segmentação se paga no primeiro ano.» No cenário base, o
resultado é de US$ 513: passa na regra de aprovação, mas é um empate. Depende de
premissas que a área comercial ainda precisa validar.

---

## Consolidado das hipóteses

| # | Hipótese | Destino | Evidência |
|:-:|:---|:---|:---|
| H1 | O preço é o melhor separador e deveria ser usado | **descartada por método** | Critério eliminatório: descaracterizaria o problema |
| H2 | A ausência de 60% em `Mas Vnr Type` inviabiliza a coluna | **derrubada** | [Entendimento dos dados](../entendimento-dados.md#valores-sentinela) |
| H3 | Os discrepantes de área do terreno são erro | **derrubada** | [Análise exploratória](../analise-exploratoria.md) |
| H4 | A escala ordinal do 00 cobre todos os níveis da base | **derrubada** | [Entendimento dos dados](../entendimento-dados.md#as-escalas-ordinais) |
| H5 | A maior silhueta indica o melhor modelo | **derrubada** | [Modelagem](../modelagem.md#o-cotovelo-de-cada-algoritmo) |
| H6 | O cotovelo e a silhueta apontam o mesmo *k* | **derrubada** | [Modelagem](../modelagem.md#o-cotovelo-de-cada-algoritmo) |
| H7 | O DBSCAN encontrará grupos que o K-Means não vê | **derrubada** | [Modelagem](../modelagem.md#por-que-dbscan-e-mean-shift-falharam) |
| H8 | A variável mais relevante na redução é a mais relevante para o negócio | **derrubada** | [Modelagem](../modelagem.md#reducao-de-dimensionalidade) |
| H9 | Regras com lift alto são sempre descobertas | **derrubada** | [Modelagem](../modelagem.md#regras-de-associacao) |
| H10 | O vencedor da silhueta passa nos critérios de negócio | **confirmada** na segunda execução | [Avaliação](../avaliacao.md#os-criterios-de-sucesso) |
| H11 | Haverá 3 ou 4 grupos naturais | **confirmada, com ressalva** | 3 segmentos, mas silhueta de 0,102 |
| H12 | Reduzir a dimensão vai melhorar o agrupamento | **em aberto** | Bases reduzidas gravadas, agrupamento não feito |
| H13 | A segmentação se paga no primeiro ano | **em aberto** | US$ 513 no cenário base, com premissas a validar |

Oito hipóteses derrubadas, duas confirmadas, duas em aberto e uma descartada por
método. É o retrato honesto de como um projeto de dados anda: a maior parte do trabalho
é descobrir que o palpite inicial estava errado — e registrar por quê.
