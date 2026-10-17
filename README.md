uv run streamlit run app/app_imobiliario.py


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

**O resultado:** onze algoritmos de agrupamento comparados na mesma régua sobre
**2.927 imóveis**. O vencedor, um mini batch k-means, divide a carteira em **três
segmentos**, com preço bem separado (1,84× entre o mais caro e o mais barato), e
classifica imóveis novos com 96,9% de acerto. A avaliação **aprovou a implantação**,
com uma ressalva: a silhueta de 0,102 indica faixas de uma carteira contínua, e não
grupos isolados.

| Segmento | Retrato | Imóveis | % do valor de venda | Preço mediano |
|:--|:--|--:|--:|--:|
| **A** | Casa recente de padrão alto | 1.105 | 50,8% | US$ 221.000 |
| **B** | Térrea de meia-idade no subúrbio | 1.124 | 32,8% | US$ 145.000 |
| **C** | Casa antiga do centro | 698 | 16,4% | US$ 120.000 |

> **Uma iteração que mudou a decisão.** Na primeira execução, as escalas ordinais do
> notebook 00 não reconheciam o nível "Típico", e a base tratada marcava 2.100 imóveis
> como "sem garagem" (são 158). O modelo daquela execução tinha 4 segmentos e era
> reprovado. Com a escala corrigida — e conferida no próprio notebook 00 —, a cadeia foi
> reexecutada e chegou ao resultado acima. Ver a
> [avaliação](docs/avaliacao.md#lacunas-e-erros-identificados).

---

## Objetivos e resultados-chave

Critérios do notebook `05-avaliacao`, declarados antes de o resultado ser lido.

**Objetivo 1 — Segmentar a carteira em linhas de produto operáveis**
- ✅ Entre 2 e 5 segmentos → **3**
- ✅ Menor segmento com ao menos 10% da carteira (crítico) → **23,8%**
- ❌ Silhueta ≥ 0,25 (não crítico) → **0,102**
- ✅ 100% da carteira com segmento → **100%**

**Objetivo 2 — Descrever cada segmento em linguagem de negócio**
- ✅ O preço distingue os segmentos: razão ≥ 1,3 e p < 0,05 → **1,84**
- ⏳ Persona, ação e métrica por segmento → **ainda não definidas**

**Objetivo 3 — Entregar em forma utilizável pela operação**
- ✅ Imóvel novo classificável com acurácia ≥ 85% → **96,9%**
- ✅ Modelo relido do disco que reproduz **100%** da partição gravada pelo notebook 04-0
- ✅ Pré-processamento reconstruído e conferido contra a saída do notebook 03
- ✅ Aplicação Streamlit local, servida pelos artefatos dos notebooks
- ⏳ Linha de base do monitoramento → **ainda não medida**

> **O que esta cadeia não entrega.** A detecção de anomalia prometida no Canvas §5:
> nenhuma configuração de DBSCAN ou Mean Shift passou na regra de admissão. As regras de
> associação são geradas pelo notebook 04-3 (23.403 regras fortes), e a implementação
> própria do Eclat continua em `src/model/associacao.py`, com teste.

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

Os notebooks **são** o pipeline: é a execução deles, na ordem, que produz todos os
artefatos do projeto — inclusive os arquivos que a aplicação consome.

| Notebook | Fase do CRISP-DM | O que faz |
|:---|:---|:---|
| `00-dicionario-dados` | 2.2 | Descrição dos dados e dicionário gerado a partir do código |
| `01-analise-exploratoria` | 2.3 | Exploração dos dados, com os insights registrados |
| `02-ajustes-dados` | 3 | As regras de limpeza que produzem a carteira depurada |
| `03-preparacao` | 3 | Espaço de atributos, escalonamento e a matriz de modelagem |
| `04-0-modelagem-cluster` | 4 | Varredura de algoritmos, escolha do vencedor e os segmentos da carteira |
| `04-1-modelagem-cotovelo` | 4 | Cotovelo e silhueta por algoritmo |
| `04-2-modelagem-reducao` | 4 | PCA e UMAP da carteira |
| `04-3-modelagem-associacao` | 4 | Regras de associação (Apriori e FP-Growth) |
| `05-avaliacao` | 5 | Confronto com os critérios de sucesso e cenários financeiros |
| `06-implantacao` | 6 | Classificação de imóveis novos com o modelo do 04-0 |
| `07_modelagem_bonus` | 4 | Pipeline com pré-processamento e busca em grade; alimenta `app/app_imobiliario.py` |

Os notebooks são versionados **sem saída** (`nbstripout`). Todas as figuras e tabelas
são persistidas em `reports/`. As versões executadas, com saída, ficam em
`reports/notebooks/` após `uv run invoke notebooks`.

### Relatório

O relatório completo é o site MkDocs em `docs/`, com catorze páginas encadeadas.
Publique localmente com `uv run invoke docs`. O resumo executivo está em
[`reports/relatorio-final.md`](reports/relatorio-final.md).

### A aplicação

```bash
uv run invoke app
```

Sobe em `http://localhost:8501` e roda **inteiramente local** — nenhuma chamada de rede,
nenhum serviço externo. A tela lê o que os notebooks gravam em disco: o modelo vencedor
do 04-0 (`models/selecionado.json` e o `.joblib` que ele aponta), os segmentos da
carteira, a base curada, o dicionário e as escalas ordinais. As projeções do 04-2, as
regras do 04-3 e a avaliação do 05 entram quando existem. O pré-processador é
reconstruído como no notebook 06 e conferido contra a saída do 03.

São sete abas: resultado do modelo, classificação de um imóvel, perfil dos segmentos,
carteira classificada, classificação em lote por CSV, regras de associação e a
procedência dos arquivos. O detalhe está em [`src/app/README.md`](src/app/README.md).

O imóvel novo pode vir incompleto: o que ficar em branco é emprestado do imóvel mais
parecido da carteira, e a tela mostra qual foi o vizinho e quais campos ele completou.

### Evidências geradas

| Diretório | Conteúdo |
|:---|---:|
| `reports/figures/` | 17 figuras da análise exploratória em script |
| `reports/tables/` | 27 tabelas-fonte (CSV, `;` e decimal `,`) |
| `models/` | O modelo vencedor do 04-0, o resumo `selecionado.json` e o modelo do notebook 07 |
| `data/processed/` | Dicionário, escalas, base tratada, base pré-processada, segmentos, projeções PCA e UMAP e regras de associação |

**Regra do projeto:** nenhuma figura é gravada sem a tabela que a originou. Os números
do relatório vêm das saídas dos notebooks e dos arquivos que eles gravam.

### Algoritmos implementados no projeto

A ementa cobre técnicas que as bibliotecas não trazem prontas:

| Implementação | Onde | Por quê |
|:---|:---|:---|
| **K-Means Manhattan** e **K-Means Mahalanobis** | notebooks `04-0` e `04-1` | O `scikit-learn` só traz o K-Means euclidiano |
| **K-Medoids** | notebooks `04-0` e `04-1`; `src/model/particional.py` | Não é distribuído pelo `scikit-learn`; o centro é um imóvel real |
| **Eclat** (representação vertical) | notebook `04-3`; `src/model/associacao.py` | O `mlxtend` traz Apriori e FP-Growth, mas não o Eclat |
| **Dissimilaridade de Gower** | `src/model/distancias.py` | Medida natural para dados mistos; disponível, mas fora da cadeia atual |

As versões de `src/model/` têm teste em `tests/test_modelo.py` — inclusive o que confere
que Eclat e Apriori devolvem exatamente os mesmos conjuntos frequentes.

## Utilização

Requisitos: [`uv`](https://docs.astral.sh/uv/) e Git. A versão do Python está fixada em
[`.python-version`](.python-version) e o `uv` a instala automaticamente.

```bash
uv sync                    # cria o ambiente a partir do uv.lock
uv run invoke ingestao     # baixa a base e materializa data/raw com manifesto
uv run invoke notebooks    # as fases do CRISP-DM, do dicionário à implantação
uv run invoke app          # a aplicação, em http://localhost:8501
uv run invoke docs         # o relatório, em http://127.0.0.1:8000
```

Nada precisa ser baixado à mão e nada depende de credencial. A aplicação roda
inteiramente local: ela lê os arquivos que os notebooks gravam em `data/processed/` e
`models/`, e não faz chamada de rede nenhuma.

### Tarefas disponíveis

```bash
uv run invoke --list
```

| Tarefa | Fase | O que faz |
|:---|:---|:---|
| `ingestao` | 2.1 | Baixa a base e materializa `data/raw` com manifesto assinado |
| `preparacao` | 3 | Constrói a base curada e a matriz de modelagem |
| `eda` | 2.3 | Executa as oito fases da análise exploratória em script |
| `notebooks` | 2.2–6 | Executa os 11 notebooks na ordem e **falha** se algum quebrar |
| `app` | 6 | Aplicação Streamlit, servida pelos artefatos dos notebooks |
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
│   ├── processed/          # Base tratada, pré-processada, segmentos, projeções e regras
│   └── raw/                # Cópia imutável da origem, parquet em PT-BR e manifesto
├── docs/                   # O relatório completo, publicado com MkDocs
│   ├── imagens/evidencias/ # Cópia das figuras que o MkDocs enxerga
│   └── pbl/                # Canvas do Problema e Quadro PBL dos cinco encontros
├── models/                 # O modelo vencedor do 04-0, selecionado.json e o modelo do 07
├── notebooks/              # Os notebooks do percurso — o pipeline do projeto
├── references/             # Dicionário de dados, gerado a partir do código
├── reports/
│   ├── figures/            # 17 figuras
│   ├── tables/             # 27 tabelas-fonte
│   └── notebooks/          # Versões executadas, com saída
├── src/
│   ├── config.py           # Caminhos, semente, paleta e restrições de negócio
│   ├── app/                # A aplicação Streamlit e o leitor dos artefatos dos notebooks
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
