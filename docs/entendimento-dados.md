# Entendimento dos dados

Esta página responde a três perguntas sobre o conjunto: **o que existe**, **em que
qualidade** e **o que isso impede ou permite** dentro dos objetivos do projeto.

## Dados iniciais

Os dados vêm da carga única descrita em [Fonte de dados](fonte-dados.md). A apuração
desta página está nos notebooks `00-dicionario-dados` (tipos e escalas) e
`01-analise-exploratoria` (exploração), e no módulo `src/data/qualidade.py`, que a
tarefa `uv run invoke eda` executa. As tabelas citadas estão em `docs/tabelas/` (notebook
01) e em `reports/tables/eda/` (`invoke eda`).

## Descrição dos dados

### Grão

Cada linha é **uma transação de um imóvel residencial** (`pid`).

| Conferência | Resultado |
|:---|---:|
| Linhas | 2.930 |
| Valores distintos de `PID` | 2.930 |
| Linhas duplicadas completas | 0 |
| A chave é única | **sim** |

A tabela é **achatada**: traz embutidas as dimensões de terreno, construção, garagem,
áreas externas e transação. Não há normalização a desfazer, o que elimina de saída o
erro mais comum de análise — somar coisas em grãos diferentes.

### Grupos de colunas

| Dimensão de negócio | Exemplos de colunas |
|:---|:---|
| Porte e configuração | `area_habitavel`, `area_porao`, `comodos`, `dormitorios`, `banheiros_total` |
| Padrão construtivo | `qualidade_geral`, `qualidade_externa`, `qualidade_cozinha`, `qualidade_porao` |
| Idade e conservação | `ano_construcao`, `ano_reforma`, `conservacao_geral` |
| Terreno | `area_terreno`, `testada_lote`, `formato_lote`, `zoneamento` |
| Garagem e áreas externas | `tipo_garagem`, `area_garagem`, `area_varandas`, `area_deck` |
| Localização | `bairro` — **reservada para validação externa** |
| Transação | `mes_venda`, `ano_venda`, `tipo_venda`, `condicao_venda` |
| Métrica | `preco_venda` — **rótulo reservado** |

### Cobertura frente aos critérios de sucesso

| Requisito vindo dos critérios | Situação |
|:---|:---|
| Atributos de **porte** para separar linhas de produto | **atendida** — 5 medidas de área e 4 de contagem |
| Atributos de **padrão construtivo** | **atendida** — 10 escalas ordinais de qualidade |
| Atributos de **idade e conservação** | **atendida** — ano de construção, de reforma e escala de conservação |
| Base para regras de associação **sem discretizar tudo** | **atendida** — 23 colunas nominais nativas |
| **Tempo de permanência em estoque** | **inviável** — não existe na origem; ver [pendências](criterios-sucesso.md#pendencias-de-dados) |
| **Custo de reforma** por imóvel | **inviável** — não existe na origem |
| Atributos de **quem comprou** | **inviável** — a base descreve o produto, não a demanda |

## Qualidade dos dados

### Valores sentinela

Muitos sistemas de origem não gravam nulo: a ausência de informação vira uma categoria
de texto ou um código. Sem tratamento, essas sentinelas aparecem nas distribuições
como se fossem valores reais — ou, pior, informação real desaparece como se fosse
ausência.

| Sentinela | Onde | Significado na origem |
|:---|:---|:---|
| `NA` | 14 colunas de porão, garagem, lareira, piscina, cerca e viela | **o item não existe no imóvel** |
| `None` | `Mas Vnr Type` (1.752 registros) | **categoria legítima** — sem revestimento em alvenaria aparente |
| *(vazio)* | `Mas Vnr Area`, `Mas Vnr Type` (23 registros) | ausência de fato |

!!! danger "O achado que muda a leitura da base"
    A leitura padrão do `pandas` converte **as duas primeiras** em nulo. O efeito
    sobre `Mas Vnr Type` é grosseiro: 1.752 imóveis **descritos** — aqueles sem
    revestimento em alvenaria aparente — passam a contar como imóveis
    **desconhecidos**, e a coluna aparenta **60,6% de ausência** quando a ausência
    real é de **0,8%** (23 registros).

    A correção é declarar as sentinelas na leitura:

    ```python
    pd.read_csv(caminho, sep="\t", keep_default_na=False, na_values=["NA", ""])
    ```

    Está implementada em `src.data.ingestao.ler_origem`, e a evidência que a
    justifica é a contagem literal de cada sentinela, coluna a coluna, em
    `reports/tables/eda/f5-inventario-sentinelas.csv`.

Depois do tratamento, as colunas de ausência estrutural recebem **rótulo próprio**
(`Sem porão`, `Sem garagem`, `Sem lareira`) e as escalas ordinais recebem **0**, que na
escala significa "não tem". Imputar pela mediana criaria porões que nunca existiram.

### Mapa da ausência

![Ausência por coluna, separada por natureza](imagens/eda/valores-ausentes.png)

| Coluna | Ausentes | % | Natureza |
|:---|---:|---:|:---|
| `Pool QC` | 2.917 | 99,6% | estrutural — sem piscina |
| `Misc Feature` | 2.824 | 96,4% | estrutural — sem item extra |
| `Alley` | 2.732 | 93,2% | estrutural — sem acesso por viela |
| `Fence` | 2.358 | 80,5% | estrutural — sem cerca |
| `Fireplace Qu` | 1.422 | 48,5% | estrutural — sem lareira |
| `Lot Frontage` | 490 | 16,7% | **faltante de fato** |
| `Garage *` (5 colunas) | 157–159 | 5,4% | estrutural — sem garagem |
| `Bsmt *` (5 colunas) | 79–83 | 2,8% | estrutural — sem porão |
| `Mas Vnr Type` / `Mas Vnr Area` | 23 | 0,8% | **faltante de fato** |
| `Electrical` | 1 | 0,03% | **faltante de fato** |

### A ausência é blocada, não aleatória

![Coocorrência de ausência](imagens/ajustes/ausencia-por-natureza.png)

As cinco colunas de garagem faltam nos **mesmos** 157 a 159 imóveis; as cinco de porão,
nos mesmos 79 a 83. Quando duas colunas faltam sempre juntas, a ausência não é
aleatória: é a marca de um item que não existe. É essa figura que sustenta a decisão
de tratar `NA` como rótulo, e não como valor a imputar.

`Lot Frontage` é a única ausência numérica relevante que **não** é estrutural. Ela se
concentra em lotes de esquina e de fundo, onde a testada não é registrada da mesma
forma — ausência do tipo **MAR**, explicada pela geometria do lote. Por isso a
imputação usa a mediana do bairro, e não a mediana global: a global achataria a
variação entre bairros, que é exatamente a informação útil da coluna.

### Achados que mudam a análise

1. **A categoria `None` virava nulo.** Sem declarar `na_values`, `Mas Vnr Type`
   aparentava 60,6% de ausência contra 0,8% reais.
   → *Consequência:* a leitura da origem passou a declarar as sentinelas
   explicitamente, e a coluna deixou de ser candidata a descarte.

2. **Um imóvel tem garagem construída no ano 2207.** Erro de digitação evidente: o
   imóvel foi vendido em 2007.
   → *Consequência:* sem a correção, a idade da garagem fica negativa em 200 anos e
   domina qualquer normalização. O notebook 02 troca o valor por 2007.

3. **Três colunas são praticamente constantes.** `Street` (99,6% `Pave`), `Utilities`
   (99,9% `AllPub`) e `Pool Area` (99,6% zeros).
   → *Consequência:* variância desprezível não separa grupo nenhum. Na cadeia atual
   elas ainda entram no *one-hot* do notebook 03; só o 04-3 descarta, nas regras, os
   itens presentes em mais de 90% dos imóveis.

4. **Cinco imóveis acima de 4.000 pés² são vendas atípicas.** O próprio autor da base
   recomenda removê-los (De Cock, 2011, §4).
   → *Consequência:* o notebook 02 remove os **três** que são vendas parciais com preço
   incompatível; os outros dois ficam.

5. **A área do terreno tem assimetria de 12,8.** Cauda longa legítima — são lotes
   grandes de verdade, não erro de digitação.
   → *Consequência:* discrepante legítimo não se remove. A cadeia atual também não
   transforma a coluna: o MinMax do 03 só a leva para 0–1, e quase todos os lotes ficam
   perto de zero nessa escala.

6. **17,6% das vendas não são "normais"** — são parciais, familiares, execuções ou
   realocações.
   → *Consequência:* mantidas. A condição da venda descreve a **transação**, não o
   **produto**, mas na cadeia atual ela entra no espaço do modelo pelo *one-hot*, e
   pesa: aparece entre as variáveis relevantes no PCA e no UMAP do 04-2.

7. **`bairro` explica 56% da variância da qualidade geral e 78% da idade do imóvel**
   (razão de correlação η²) — de longe a nominal com maior poder explicativo.
   → *Consequência:* o bairro carrega informação de produto e, por tabela, de preço.
   Na cadeia atual ele **entra** no espaço do modelo pelo *one-hot* e é a variável de
   maior peso no PCA (8,2%). Com isso, ele deixa de servir como régua de validação
   externa, como era o plano.

A coleção registrada pelo notebook 01, com 12 entradas, está em
[Análise exploratória](analise-exploratoria.md#colecao-de-insights).

## Dimensões-chave

### As escalas ordinais

Vinte e duas colunas da base são **ordinais**, a maioria disfarçada de texto.
`Ex > Gd > TA > Fa > Po` tem ordem semântica: excelente, bom, típico, regular, ruim.
Tratá-las como nominais e aplicar *one-hot* destruiria a ordem e multiplicaria a
dimensionalidade sem ganho.

O notebook 00 declara a escala de cada ordinal e a grava em
`data/processed/escala.csv`. O 03 troca cada nível pela sua posição na escala, e o
rótulo de ausência do 02 (`Sem porão`, `Sem garagem`…) entra como o menor nível:

| Valor na base | Origem | Código |
|:---|:---|:---|
| Excelente | `Ex` | 5 |
| Bom | `Gd` | 4 |
| Típico | `TA` | 3 |
| Regular | `Fa` | 2 |
| Ruim | `Po` | 1 |
| Sem porão, Sem garagem… | `NA` — o item não existe | **0** |

O zero não é "pior que ruim": é uma categoria à parte, "não tem".

!!! success "Os rótulos da escala são os mesmos da ingestão — e o notebook confere"
    Numa versão anterior, a escala do notebook 00 chamava de "Médio" o nível que a
    ingestão (`src/data/dicionario.py`) chama de "Típico", e o mesmo desencontro de
    nomes atingia 18 das 22 colunas ordinais. O notebook 01 transformava todo valor fora
    da escala em ausente, e o 02 o lia como item inexistente: a base tratada chegou a ter
    **2.100 imóveis "Sem garagem"**, contra 158 reais, e seis colunas de qualidade
    removidas por excesso de "ausentes".

    A escala foi alinhada aos rótulos da ingestão, e o notebook 00 passou a **conferir**,
    antes de gravar `escala.csv`, que todo valor das ordinais na base está na escala. Na
    base tratada atual, `qualidade_garagem` tem 2.613 imóveis "Típico" e 158 "Sem
    garagem", e nenhuma coluna é removida no 02.

### O rótulo reservado

`preco_venda` está na base e **não entra em nenhuma etapa de modelagem**: o notebook
04-0 o retira da matriz antes de qualquer algoritmo rodar. Ele reaparece só depois que os
segmentos já estão definidos, para responder a duas perguntas de negócio:

- quanto vale cada segmento (participação no valor de venda);
- se o preço difere entre os segmentos — razão entre medianas e teste de
  Kruskal-Wallis, no notebook 05.

Na base bruta:

| | Valor |
|:---|---:|
| Mediana | US$ 160.000 |
| Média | US$ 180.796 |
| Mínimo | US$ 12.789 |
| Máximo | US$ 755.000 |
| Assimetria | 1,74 |

## Limitações

| Limitação | Objetivo afetado | Consequência declarada |
|:---|:---|:---|
| **Não há tempo de permanência em estoque** | 1, 2 | As metas de giro das personas são propostas de meta, não medições. Precisam de instrumentação antes de virar indicador. |
| **Não há custo de reforma** | 2 | O retorno da reforma por segmento é estimado a partir do diferencial de preço, não medido. |
| **Não há atributo do comprador** | 2 | A segmentação descreve o **produto**. Nenhuma ação de segmentação de demanda pode ser derivada daqui. |
| **Período 2006–2010** | 5 | Inclui a crise imobiliária americana. Os patamares de preço não devem ser lidos como preço corrente, e a estabilidade dos segmentos entre períodos ainda não foi medida. |
| **Mercado único** | todos | Ames, Iowa, ~60 mil habitantes. A estrutura encontrada não se transfere automaticamente para outro mercado sem reciclagem. |

As três primeiras estão registradas também como
[pendências de dados](criterios-sucesso.md#pendencias-de-dados), para que a conversa
com a área provedora tenha uma lista objetiva.
