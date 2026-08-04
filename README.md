# Segmentação da carteira residencial — Meridiano Imobiliária

> **Projeto de demonstração** da disciplina *Método de Aprendizado Não Supervisionado*.
> O ciclo CRISP-DM percorrido inteiro, do download da base à aplicação que a operação
> usa — com todas as evidências materializadas em disco.

A Meridiano Imobiliária administra **2.925 imóveis residenciais** e trata todos da
mesma forma: mesma régua de preço, mesmo teto de reforma, mesmo canal de anúncio. A
diretoria quer saber como esse estoque se organiza naturalmente, e tem orçamento para
**no máximo cinco linhas de produto** com ação diferenciada.

Não existe rótulo. O preço de venda está na base e é **reservado**: usá-lo na modelagem
devolveria uma tabela de preço, que a diretoria já tem.

**O resultado:** quatro linhas de produto, cada uma com persona, política de reforma,
canal de venda e métrica de acompanhamento. Silhueta de 0,1775, estabilidade de 0,943
sob reamostragem e 13 de 13 critérios de aceite atendidos.

| Código | Persona | Imóveis | % receita | Ação diferenciada |
|:--|:--|--:|--:|:--|
| **S1** | Requalificação sem porão | 80 | 1,6% | Decisão binária por unidade: renda ou desinvestimento |
| **S2** | Compacto de entrada | 1.010 | 23,3% | Precificação por giro e reforma leve padronizada |
| **S3** | Familiar consolidado | 794 | 25,5% | Reforma de valorização em cozinha e banheiro |
| **S4** | Novo de alto padrão | 1.041 | 49,5% | Sem reforma; corretagem dedicada e vitrine premium |

---

## Objetivos e resultados-chave

**Objetivo 1 — Segmentar a carteira em linhas de produto operáveis**
- ✅ No máximo 5 segmentos → **4**
- ✅ Silhueta ≥ 0,15 → **0,1775**
- ✅ Estabilidade ARI ≥ 0,75 sob reamostragem de 80% → **0,9433**
- ✅ Nenhum segmento abaixo de 2% da carteira → **2,7%**

**Objetivo 2 — Descrever cada linha em linguagem de negócio**
- ✅ Persona, ação e métrica por segmento → **4 de 4**
- ✅ Imóvel real representante (medoide), com matrícula → **4 medoides**
- ✅ Não pode ser apenas faixa de preço: ARI contra quartis < 0,40 → **0,3112**

**Objetivo 3 — Encontrar padrões de coocorrência que sustentem a segmentação**
- ✅ Regras com suporte ≥ 10%, confiança ≥ 70%, lift ≥ 1,30 → **256 após poda**
- ✅ Ao menos um padrão diferencial por segmento → **4 segmentos cobertos**
- ✅ Apriori, Eclat e FP-Growth com os mesmos conjuntos → **3 de 3 idênticos**

**Objetivo 4 — Isolar os imóveis fora de padrão**
- ✅ Ruído ≤ 10% → **1,81% (53 imóveis)**

**Objetivo 5 — Entregar em forma utilizável pela operação**
- ✅ Pipeline serializado que reproduz **100%** da classificação de treino
- ✅ Aplicação Streamlit com sete abas
- ✅ Plano de monitoramento com 6 indicadores, gatilhos e responsáveis

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

| Notebook | Fase do CRISP-DM | O que faz |
|:---|:---|:---|
| `01-entendimento-e-descricao-dos-dados` | 1 e 2.1–2.2 | Canvas do Problema, carga com manifesto assinado, perfil de qualidade, achado das sentinelas |
| `02-eda-fluxo-8-fases` | 2.3–2.4 | As oito fases da análise exploratória, com 21 insights registrados |
| `02b-sensibilidade-escala` | 3 | As 10 regras de limpeza e o experimento com quatro escalonadores |
| `03-clusterizacao-particional-hierarquica` | 4 | Gower, K-Means, K-Medoids, hierárquica, escolha de *k* e personas |
| `04-densidade-gmm-reducao-dimensional` | 4 | DBSCAN, Mean Shift, GMM, PCA, Kernel PCA e a matriz comparativa |
| `05-regras-de-associacao` | 4 | Apriori, Eclat e FP-Growth; funil de poda; cruzamento com os segmentos |
| `06-avaliacao-e-implantacao` | 5 e 6 | Confronto com os critérios, leitura de negócio, drift e artefatos |

Os notebooks são versionados **sem saída** (`nbstripout`). Todas as figuras e tabelas
são persistidas em `reports/`. As versões executadas, com saída, ficam em
`reports/notebooks/` após `uv run invoke notebooks`.

### Relatório

O relatório completo é o site MkDocs em `docs/`, com doze páginas encadeadas. Publique
localmente com `uv run invoke docs`.

### Evidências geradas

| Diretório | Conteúdo |
|:---|---:|
| `reports/figures/` | 46 figuras |
| `reports/tables/` | 98 tabelas-fonte (CSV, `;` e decimal `,`) |
| `models/` | Pipeline serializado, metadados e linha de base de monitoramento |
| `data/processed/` | Base curada, matriz de modelagem, transações e base segmentada |

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
uv run invoke pipeline     # as seis fases do CRISP-DM, do download aos artefatos
uv run invoke app          # a aplicação de implantação
uv run invoke docs         # o relatório, em http://127.0.0.1:8000
```

O ciclo inteiro roda em cerca de dez minutos em um notebook comum. Nada precisa ser
baixado à mão e nada depende de credencial.

### Tarefas disponíveis

```bash
uv run invoke --list
```

| Tarefa | Fase | O que faz |
|:---|:---|:---|
| `ingestao` | 2.1 | Baixa a base e materializa `data/raw` com manifesto assinado |
| `preparacao` | 3 | Constrói a base curada e a matriz de modelagem |
| `eda` | 2.3 | Executa as oito fases da análise exploratória |
| `modelagem` | 4 | Escolha de *k*, seis algoritmos, perfilagem |
| `regras` | 4 | Apriori, Eclat e FP-Growth |
| `avaliacao` | 5 | Confronto com os critérios de aceite |
| `implantacao` | 6 | Artefatos, drift e planos de monitoramento |
| `pipeline` | 1–6 | Tudo, na ordem |
| `notebooks` | — | Executa os 7 notebooks e **falha** se algum quebrar |
| `app` | 6 | Aplicação Streamlit |
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
│   ├── processed/          # Base curada, matriz de modelagem, transações, segmentada
│   └── raw/                # Cópia imutável da origem + manifesto assinado
├── docs/                   # O relatório completo, publicado com MkDocs
│   ├── imagens/evidencias/ # Cópia das figuras que o MkDocs enxerga
│   └── pbl/                # Canvas do Problema e Quadro PBL dos cinco encontros
├── models/                 # Pipeline serializado, metadados, linha de base
├── notebooks/              # Os sete notebooks do percurso
├── references/             # Dicionário de dados, gerado a partir do código
├── reports/
│   ├── figures/            # 46 figuras
│   ├── tables/             # 98 tabelas-fonte
│   └── notebooks/          # Versões executadas, com saída
├── src/
│   ├── config.py           # Caminhos, semente, paleta e restrições de negócio
│   ├── data/               # Ingestão, dicionário, qualidade e preparação
│   ├── eda/                # As oito fases e as medidas de associação
│   ├── model/              # Distâncias, clusterização, redução, associação, personas
│   ├── pipeline/           # Orquestração por fase do CRISP-DM
│   ├── deployment/         # Aplicação, scoring e monitoramento
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
