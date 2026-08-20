# Segmentação da carteira residencial — Meridiano Imobiliária

> **Projeto de demonstração** da disciplina *Método de Aprendizado Não Supervisionado*.
> O ciclo CRISP-DM percorrido inteiro, do download da base à aplicação que a operação
> usa — com todas as evidências materializadas em disco.

A Meridiano Imobiliária administra sua carteira residencial tratando todos os imóveis da
mesma forma: mesma régua de preço, mesmo teto de reforma, mesmo canal de anúncio. A
diretoria quer saber como esse estoque se organiza naturalmente, e tem orçamento para
**no máximo cinco linhas de produto** com ação diferenciada.

Não existe rótulo. O preço de venda está na base e é **reservado**: usá-lo na modelagem
devolveria uma tabela de preço, que a diretoria já tem.

**O resultado:** três linhas de produto sobre uma carteira depurada de **2.350 imóveis**,
cada uma com persona, política de preço, teto de reforma, canal de venda e métrica de
acompanhamento. Silhueta de 0,1726 e estabilidade de 0,9575 sob reamostragem.

| Código | Persona | Imóveis | % receita | Ação diferenciada |
|:--|:--|--:|--:|:--|
| **S1** | Compacto herdado | 914 | 27,3% | Decisão unidade a unidade: reforma leve e venda, renda ou desinvestimento |
| **S2** | Amplo para requalificar | 667 | 27,9% | Reforma de valorização em cozinha e banheiro, antes do anúncio |
| **S3** | Recente de alto padrão | 769 | 44,8% | Sem reforma; corretagem dedicada e vitrine premium |

> **Versão publicada: 2.0.0.** A cadeia anterior (`1.0.0`, com *k* = 4 sobre 2.925
> imóveis) foi retirada do repositório: a depuração da base mudou o resultado, e manter
> as duas em disco significava duas respostas diferentes para a mesma pergunta.

---

## Objetivos e resultados-chave

**Objetivo 1 — Segmentar a carteira em linhas de produto operáveis**
- ✅ Entre 2 e 5 segmentos → **3**
- ✅ Silhueta ≥ 0,15 → **0,1726**
- ✅ Estabilidade ARI ≥ 0,75 sob reamostragem → **0,9575**
- ✅ Nenhuma linha irrelevante em receita → **a menor responde por 27,3%**

**Objetivo 2 — Descrever cada linha em linguagem de negócio**
- ✅ Persona, política de preço, teto de reforma, canal e métrica → **3 de 3**
- ✅ Não pode ser apenas faixa de preço: ARI contra quartis < 0,40 → **0,3345**
- ✅ Validação externa contra `bairro`, que nunca entrou em algoritmo nenhum → **V de Cramér 0,630**

**Objetivo 3 — Entregar em forma utilizável pela operação**
- ✅ Pacote serializado que reproduz **100%** da partição aprovada na avaliação
- ✅ Contrato de entrada com 17 campos, faixas aceitas e valor padrão declarado
- ✅ Regra de fronteira **calibrada** (cortes 0,609 e 0,915), e não escolhida por intuição
- ✅ Aplicação Streamlit local, servida só pelo pacote
- ✅ Plano de monitoramento com 6 indicadores, gatilhos e responsáveis

> **O que esta cadeia não entrega.** O Canvas §5 promete também regras de associação e
> detecção de anomalia; a cadeia 00–06 não executa nenhuma das duas sobre a base
> depurada. As implementações continuam no repositório (`src/model/associacao.py` e
> `src/model/densidade.py`), com teste, mas a etapa foi levada ao encerramento como
> deliberação em aberto — está registrada no backlog dentro do próprio pacote.

## A base

**Ames Housing** — De Cock, D. (2011). *Ames, Iowa: Alternative to the Boston Housing
Data as an End of Semester Regression Project.* **Journal of Statistics Education**,
19(3).

2.930 imóveis × 82 colunas, transacionados em Ames, Iowa, entre 2006 e 2010. Download
direto, sem cadastro, de `jse.amstat.org`. Uso educacional e de pesquisa, com citação
obrigatória. Não há dado pessoal: `PID` é a matrícula do imóvel.

> **A escolha do tema.** Este conjunto é conhecido como um problema de **regressão de
> preço** — foi publicado com essa finalidade. Aqui ele faz o oposto: joga o preço fora
> e pergunta o que sobra. A mesma base, sem a variável-alvo, responde a uma pergunta
> completamente diferente.

## Conteúdo

### Notebooks

Os sete notebooks **são** o pipeline: é a execução deles, na ordem, que produz todos os
artefatos do projeto — inclusive o pacote que a aplicação consome.

| Notebook | Fase do CRISP-DM | O que faz |
|:---|:---|:---|
| `00-dicionario-dados` | 2.2 | Descrição dos dados e dicionário gerado a partir do código |
| `01-analise-exploratoria` | 2.3 | Exploração dos dados, com os insights registrados |
| `02-ajustes-dados` | 3 | As regras de limpeza que produzem a carteira depurada |
| `03-preparacao` | 3 | Espaço de atributos, escalonamento e a matriz de modelagem |
| `04-modelagem` | 4 | Escolha de *k*, K-Means, K-Medoids, hierárquica e perfilagem |
| `05-avaliacao` | 5 | Confronto com os critérios de aceite e leitura de negócio |
| `06-implantacao` | 6 | Contrato de entrada, regra de fronteira, monitoramento e o pacote `.pkl` |

Os notebooks são versionados **sem saída** (`nbstripout`). Todas as figuras e tabelas
são persistidas em `reports/`. As versões executadas, com saída, ficam em
`reports/notebooks/` após `uv run invoke notebooks`.

### Relatório

O relatório completo é o site MkDocs em `docs/`, com doze páginas encadeadas. Publique
localmente com `uv run invoke docs`.

### A aplicação

```bash
uv run invoke app
```

Sobe em `http://localhost:8501` e roda **inteiramente local** — nenhuma chamada de rede,
nenhum serviço externo. A tela lê um único arquivo, `models/aplicacao-segmentacao.pkl`,
que é autocontido: dentro dele viajam o pipeline treinado, o contrato de entrada, o
catálogo das três linhas de produto, a carteira já classificada, o plano de
monitoramento e as evidências. Copiar `src/app/` mais esse `.pkl` para outra máquina é
suficiente para a aplicação subir.

São sete abas: resultado do modelo, classificação de um imóvel, linhas de produto,
carteira classificada, classificação em lote por CSV, monitoramento e a procedência do
pacote. O detalhe está em [`src/app/README.md`](src/app/README.md).

A regra que a tela respeita: quando a distância até os dois centroides mais próximos é
parecida demais — razão acima de **0,915**, o corte calibrado — o imóvel é marcado como
*fronteira* e **a ação automática não dispara**, indo para avaliação humana.

### Evidências geradas

| Diretório | Conteúdo |
|:---|---:|
| `reports/figures/` | 46 figuras |
| `reports/tables/` | 289 tabelas-fonte (CSV, `;` e decimal `,`) |
| `models/` | O pacote `.pkl` da aplicação, o pré-processador, o catálogo de personas, o contrato de entrada e a linha de base de monitoramento |
| `data/processed/` | Base curada, base de modelagem, base segmentada e os manifestos assinados de cada fase |

**Regra do projeto:** nenhuma figura é gravada sem a tabela que a originou. Toda
afirmação do relatório é rastreável até um CSV.

### Três algoritmos implementados no projeto

A ementa cobre técnicas que as bibliotecas não trazem prontas:

| Implementação | Arquivo | Por quê |
|:---|:---|:---|
| **Dissimilaridade de Gower** | `src/model/distancias.py` | Não existe no `scikit-learn`; é a medida natural para dados mistos |
| **K-Medoids** (iteração de Voronoi) | `src/model/particional.py` | Não é distribuído pelo `scikit-learn`; opera sobre qualquer dissimilaridade |
| **Eclat** (representação vertical) | `src/model/associacao.py` | O `mlxtend` traz Apriori e FP-Growth, mas não o Eclat |

Os três têm teste em `tests/test_modelo.py` — inclusive o que confere que Eclat e
Apriori devolvem exatamente os mesmos conjuntos frequentes.

## Utilização

Requisitos: [`uv`](https://docs.astral.sh/uv/) e Git. A versão do Python está fixada em
[`.python-version`](.python-version) e o `uv` a instala automaticamente.

```bash
uv sync                    # cria o ambiente a partir do uv.lock
uv run invoke ingestao     # baixa a base e materializa data/raw com manifesto
uv run invoke notebooks    # as fases do CRISP-DM, do dicionário ao pacote publicado
uv run invoke app          # a aplicação, em http://localhost:8501
uv run invoke docs         # o relatório, em http://127.0.0.1:8000
```

Nada precisa ser baixado à mão e nada depende de credencial. A aplicação roda
inteiramente local: ela lê um arquivo em disco, `models/aplicacao-segmentacao.pkl`, e
não faz chamada de rede nenhuma.

### Tarefas disponíveis

```bash
uv run invoke --list
```

| Tarefa | Fase | O que faz |
|:---|:---|:---|
| `ingestao` | 2.1 | Baixa a base e materializa `data/raw` com manifesto assinado |
| `preparacao` | 3 | Constrói a base curada e a matriz de modelagem |
| `eda` | 2.3 | Executa as oito fases da análise exploratória em script |
| `notebooks` | 2.2–6 | Executa os 7 notebooks na ordem e **falha** se algum quebrar |
| `app` | 6 | Aplicação Streamlit, servida pelo pacote `.pkl` |
| `docs` / `build` | — | Serve ou gera o site de documentação |
| `test` / `lint` / `fmt` | — | Testes, lint e formatação |
| `limpar` | — | Remove os artefatos gerados, preservando `data/raw` |

## Desenvolvedores

- [Aislan Freitas](http://github.com/aislansf) — aislansf@gmail.com

## Organização de diretórios

```
.
├── .github/                # Templates de issues/PRs e CODEOWNERS
├── data/
│   ├── external/           # Arquivos de fontes externas (vazio neste projeto)
│   ├── processed/          # Base curada, de modelagem, segmentada e os manifestos
│   └── raw/                # Cópia imutável da origem + manifesto assinado
├── docs/                   # O relatório completo, publicado com MkDocs
│   ├── imagens/evidencias/ # Cópia das figuras que o MkDocs enxerga
│   └── pbl/                # Canvas do Problema e Quadro PBL dos cinco encontros
├── models/                 # O pacote .pkl da aplicação, contrato, catálogo e linha de base
├── notebooks/              # Os sete notebooks do percurso — o pipeline do projeto
├── references/             # Dicionário de dados, gerado a partir do código
├── reports/
│   ├── figures/            # 46 figuras
│   ├── tables/             # 98 tabelas-fonte
│   └── notebooks/          # Versões executadas, com saída
├── src/
│   ├── config.py           # Caminhos, semente, paleta e restrições de negócio
│   ├── app/                # A aplicação Streamlit e o leitor do pacote .pkl
│   ├── data/               # Ingestão, dicionário, qualidade e preparação
│   ├── eda/                # As oito fases e as medidas de associação
│   ├── model/              # Distâncias, clusterização, redução, associação, personas
│   └── utils/              # Gravação padronizada de figuras e tabelas
├── tests/                  # Testes das implementações próprias
├── .pre-commit-config.yaml # ruff, nbstripout e conferências antes de cada commit
├── .python-version         # Versão do Python usada pelo uv
├── mkdocs.yml              # Configuração do site
├── pyproject.toml          # Dependências do projeto
├── uv.lock                 # Lockfile — versionado, para reprodutibilidade
└── tasks.py                # Tarefas do invoke
```

## Licença

O código deste repositório está sob a licença [MIT](LICENSE).

Os **dados** são de De Cock (2011) e distribuídos para uso educacional e de pesquisa,
com citação obrigatória do artigo original. A Meridiano Imobiliária é uma organização
fictícia; os dados são reais e públicos.
