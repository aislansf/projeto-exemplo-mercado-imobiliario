# Entendimento de negócio

**CRISP-DM fase 1.** Compreender os objetivos e requisitos do projeto sob a
perspectiva do negócio — antes de olhar uma linha de dado.

## A situação-problema

!!! quote "Memorando interno — Diretoria Comercial"
    Administramos hoje quase três mil imóveis residenciais e tratamos todos da mesma
    forma: mesma régua de preço, mesmo teto de reforma, mesmo anúncio.

    Sabemos que isso está errado, mas não sabemos **em quantas partes** a carteira se
    divide, nem **o que caracteriza** cada parte. Não temos essa classificação em
    lugar nenhum — nunca marcamos qual imóvel é de entrada e qual é de alto padrão.

    Precisamos saber como esses imóveis se organizam naturalmente e o que fazer de
    diferente com cada grupo. Uma restrição: **conseguimos financiar uma ação
    diferenciada por grupo, e no máximo cinco grupos.** Se vocês entregarem quinze
    segmentos, não agiremos sobre nenhum.

    Apresentem ao conselho em linguagem de negócio. Queremos entender **por que**
    confiar no que vocês encontraram.

### Por que este é um problema não supervisionado

Não existe variável-alvo. A classificação que se busca é exatamente o que **não**
existe na base. Isso muda três coisas de forma prática:

1. **Não há acurácia atrás da qual se esconder.** A defesa do resultado é a
   combinação de métricas internas, teste de estabilidade e leitura de negócio.
2. **O rótulo que existe precisa ser reservado.** `preco_venda` está na base, e usá-lo
   na modelagem descaracterizaria o problema — devolveria uma faixa de preço, não uma
   linha de produto.
3. **O monitoramento é diferente.** Sem gabarito não há erro de previsão para
   acompanhar; o que se monitora é o desvio de distribuição da entrada e a perda de
   coesão dos grupos. Ver [Implementação](implementacao.md).

## Marcos do projeto

???+ abstract "Fase 1: Preparação do ambiente"
    - [x] Criar repositório a partir do `project-template`
    - [x] Instalar ferramentas do projeto (`uv sync`)
    - [x] Fixar semente aleatória e versionar o `uv.lock`

???+ abstract "Fase 2: Entendimento de negócio"
    - [x] Preencher o Canvas do Problema ([docs/pbl/canvas-do-problema.md](pbl/canvas-do-problema.md))
    - [x] Definir critérios de sucesso de negócio e técnicos
    - [x] Formular as perguntas orientadas a dados (SMART)

???+ abstract "Fase 3: Entendimento dos dados"
    - [x] Materializar a camada bruta com manifesto de carga
    - [x] Produzir o perfil de qualidade dos dados
    - [x] Descrever grão, tipos e cobertura frente aos critérios
    - [x] Executar as oito fases da análise exploratória
    - [x] Consolidar a coleção de insights (21 registros)

???+ abstract "Fase 4: Preparação dos dados"
    - [x] Implementar as 10 regras de limpeza, com motivo registrado
    - [x] Derivar os atributos consolidados
    - [x] Executar o experimento de sensibilidade à escala
    - [x] Gerar a base curada e a matriz de modelagem

???+ abstract "Fase 5: Modelagem"
    - [x] Comparar três leituras do espaço de atributos
    - [x] Determinar *k* por quatro métricas, estabilidade e restrição operacional
    - [x] Aplicar seis famílias de algoritmo e consolidar a matriz comparativa
    - [x] Reduzir dimensionalidade com PCA e Kernel PCA
    - [x] Minerar regras com Apriori, Eclat e FP-Growth
    - [x] Perfilar os segmentos e nomear as personas

???+ abstract "Fase 6: Avaliação"
    - [x] Confrontar cada critério de aceite (13 de 13 atendidos)
    - [x] Produzir a leitura de negócio com o rótulo reservado
    - [x] Registrar limitações e hipóteses derrubadas
    - [x] Decidir formalmente: implantar

???+ abstract "Fase 7: Implementação"
    - [x] Serializar o pipeline e gravar a linha de base de monitoramento
    - [x] Publicar a aplicação de consulta
    - [x] Definir o plano de monitoramento com gatilhos e responsáveis
    - [x] Definir o plano de reciclagem e o critério de aceite da nova partição

## 1.1 · Determinar os objetivos de negócio

### O que a organização quer realizar

Substituir a política única por **políticas por linha de produto**, de modo que o
capital de reforma vá para onde tem retorno e o esforço de corretagem vá para onde tem
margem. A segmentação é o meio; a decisão de alocação é o fim.

### Critérios de sucesso do negócio

| Critério | Métrica | Meta |
|:---|:---|:---|
| A carteira passa a ser tratada por linha de produto | % do estoque com linha atribuída | 100% em 30 dias |
| O capital de reforma é alocado por retorno esperado | ganho de preço sobre custo de reforma, por linha | ≥ 1,8× no segmento de maior retorno |
| O estoque de entrada gira mais rápido | tempo médio de giro do segmento de entrada | de 90 para 60 dias |
| O estoque de alto padrão não é vendido com desconto | preço realizado ÷ preço anunciado | ≥ 0,97 |
| O estoque herdado deixa de ser inerte | % do segmento com destino definido | 100% em 12 meses |

## 1.2 · Avaliar a situação

### Recursos

#### Equipe técnica

| Nome | Cargo / Função | E-mail |
|:---|:---|:---|
| Aislan Freitas | Cientista de dados — responsável pelo ciclo completo | aislansf@gmail.com |

Em um projeto real esta tabela teria analista de negócios, engenheiro de dados e
cientista de dados. Aqui o projeto é de demonstração, e a concentração em uma pessoa
é declarada como o que é: uma limitação de processo, não uma virtude.

#### Especialistas de negócio

| Papel | Contribuição esperada | Contato |
|:---|:---|:---|
| Diretoria Comercial | Define o teto de cinco linhas e valida as ações | comercial@meridiano.exemplo |
| Gerência de Ativos | Traduz o perfil técnico em viabilidade operacional | ativos@meridiano.exemplo |
| Comitê de Aquisição | Consome a classificação na decisão de compra | aquisicao@meridiano.exemplo |

#### Infraestrutura

Nenhuma além de um notebook. É uma característica do problema, não um atalho: 2.925
registros e 82 colunas cabem em memória com folga, e a matriz de dissimilaridade de
Gower — o artefato mais pesado do projeto — ocupa **34 MB**. Um projeto que precisasse
de cluster para 2.925 linhas teria um problema de engenharia, não de dados.

#### Recursos financeiros

O orçamento da diretoria comporta **cinco ações diferenciadas**. Essa é a única
restrição financeira que entra no projeto, e ela é técnica na prática: define o teto
de *k*.

### Requisitos do projeto

#### Necessidades de negócio

- Uma classificação **estável**: se a linha de produto de um imóvel mudar a cada
  reexecução, nenhuma política se sustenta.
- Uma classificação **explicável**: o corretor precisa entender por que aquele imóvel
  caiu naquela linha, sem abrir um modelo.
- Um **representante real** por linha: "me mostre um imóvel deste grupo" é a primeira
  pergunta de qualquer reunião.

#### Requisitos funcionais

| # | Requisito |
|:-:|:---|
| RF1 | Classificar todo imóvel da carteira em exatamente uma linha de produto |
| RF2 | Classificar um imóvel **novo**, ainda não adquirido, a partir de seus atributos |
| RF3 | Sinalizar imóveis de fronteira, em que a ação automática não deve ser disparada |
| RF4 | Listar os imóveis que não pertencem a nenhuma linha |
| RF5 | Permitir consulta filtrada da carteira e exportação do recorte |
| RF6 | Medir e exibir o desvio de distribuição desde a última reciclagem |

#### Requisitos técnicos

| Ferramenta | Uso no projeto |
|:---|:---|
| :simple-github: GitHub | Controle de versões e histórico do processo |
| :simple-uv: uv | Gerenciamento de dependências e do ambiente |
| :simple-python: Python 3.12 | Linguagem de todo o pipeline |
| :simple-jupyter: Jupyter | Os sete notebooks do percurso |
| :material-bookshelf: Bibliotecas | `pandas`, `numpy`, `scipy`, `scikit-learn`, `mlxtend`, `matplotlib`, `seaborn`, `plotly` |
| :material-web: Streamlit | Aplicação de implantação |
| :material-file-document: MkDocs Material | Este site |

Três algoritmos da ementa **não** existem prontos nas bibliotecas e foram
implementados no projeto — o que é parte do material didático:

| Implementação própria | Onde | Por quê |
|:---|:---|:---|
| Dissimilaridade de Gower | `src/model/distancias.py` | Não existe no `scikit-learn`, e a fórmula cabe em quinze linhas |
| K-Medoids (iteração de Voronoi) | `src/model/particional.py` | Não é distribuído pelo `scikit-learn`; opera sobre qualquer matriz de dissimilaridade |
| Eclat (representação vertical) | `src/model/associacao.py` | O `mlxtend` traz Apriori e FP-Growth, mas não o Eclat |

#### Requisitos de dados

| Requisito | Situação |
|:---|:---|
| Ao menos 800 registros e 8 atributos, sendo 4 numéricos | **atendido** — 2.925 × 82, com 34 numéricas |
| Atributos que descrevam o **produto**, não só a transação | **atendido** — porte, configuração, padrão e idade |
| Ausência de dado pessoal identificável | **atendido** — `PID` é matrícula do imóvel |
| Licença compatível com uso educacional | **atendido** — citação do artigo original é suficiente |
| Dado de tempo de permanência em estoque | **inviável** — não existe na origem; ver [limitações](avaliacao.md) |

### Riscos e contingências

| Risco | Probabilidade | Impacto | Contingência adotada |
|:---|:-:|:-:|:---|
| A base sair do ar durante o projeto | baixa | alto | A camada bruta é versionada com `sha256` no manifesto; o projeto reexecuta sem rede |
| Usar o rótulo reservado por descuido | média | **eliminatório** | `preco_venda` e `bairro` declarados fora da matriz de modelagem em `src/data/dicionario.py`; a única função que os toca está isolada em `perfilagem.leitura_a_posteriori` |
| A escala do pré-processamento definir os grupos | alta | alto | Experimento de sensibilidade com quatro escalonadores, comparados por ARI |
| O agrupamento não se reproduzir | média | alto | Teste de estabilidade por reamostragem, em 40 repetições, para cada *k* candidato |
| Entregar mais grupos do que o orçamento comporta | média | alto | Teto de 5 embutido em `config.K_MAXIMO_NEGOCIO` e verificado na avaliação |
| Regras de associação triviais apresentadas como descoberta | alta | médio | Funil de poda em quatro etapas, incluindo tautologia semântica |

### Análise de custo-benefício

| Item | Estimativa |
|:---|:---|
| **Custo** — esforço técnico | ~40 h de análise, sem infraestrutura adicional |
| **Custo** — manutenção | 2 h/mês de monitoramento, 8 h/ano de reciclagem |
| **Benefício** — alocação de reforma | Redirecionar o capital de reforma de S4 (que não precisa) e S1 (onde não se paga) para S3, onde o retorno é maior |
| **Benefício** — giro | Precificação por giro em S2, o maior segmento em unidades |
| **Benefício** — estoque inerte | 80 imóveis de S1 saem do limbo com decisão binária |
| **Risco de não fazer** | Continuar reformando imóvel que já está no padrão e anunciando imóvel de entrada por corretagem cara |

## 1.3 · Determinar as metas de mineração de dados

| Meta técnica | Critério |
|:---|:---|
| **Agrupamento** da carteira | silhueta ≥ 0,15; entre 2 e 5 grupos; estabilidade ARI ≥ 0,75 |
| **Detecção de anomalia** | ruído ≤ 10% da carteira, com perfil descrito |
| **Regras de associação** | suporte ≥ 10%, confiança ≥ 70%, lift ≥ 1,30, com poda de trivialidade |
| **Redução de dimensionalidade** | projeção 2D interpretável, com cargas nomeadas |

!!! warning "O que **não** é meta de mineração"
    Prever o preço. A base permite, e é para isso que ela costuma ser usada — mas
    seria outro projeto, com outra pergunta e outro método de validação.

## 1.4 · Produzir o plano do projeto

```mermaid
flowchart LR
    A["1 · Entendimento<br/>de negócio"] --> B["2 · Entendimento<br/>dos dados"]
    B --> C["3 · Preparação<br/>dos dados"]
    C --> D["4 · Modelagem"]
    D --> E["5 · Avaliação"]
    E --> F["6 · Implantação"]
    E -.->|"iterar"| B
    D -.->|"iterar"| C
```

| Fase | Entregável | Notebook | Módulo |
|:---|:---|:---|:---|
| 1 · Entendimento de negócio | Canvas, critérios de sucesso | `01` | — |
| 2 · Entendimento dos dados | Manifesto, perfil de qualidade, 21 insights | `01`, `02` | `src.data.ingestao`, `src.eda` |
| 3 · Preparação | Base curada, matriz de modelagem, experimento de escala | `02b` | `src.data.preparacao` |
| 4 · Modelagem | Matriz comparativa, personas, regras | `03`, `04`, `05` | `src.pipeline.modelagem`, `src.pipeline.regras` |
| 5 · Avaliação | Confronto com critérios, limitações | `06` | `src.pipeline.avaliacao` |
| 6 · Implantação | Pipeline serializado, aplicação, plano de monitoramento | `06` | `src.pipeline.implantacao`, `src.deployment` |

Cada fase é executável isoladamente por uma tarefa do `invoke`; `uv run invoke pipeline`
roda a sequência inteira.
