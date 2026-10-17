# Status do projeto

**Ciclo CRISP-DM percorrido; modelo aprovado.** Decisão formal da fase 5:
**implantar**, com a ressalva da silhueta.

| Indicador | Valor |
|:---|---:|
| Fases do CRISP-DM percorridas | 6 de 6 |
| Critérios de sucesso do 05 atendidos | **5 de 6** (todos os críticos) |
| Critérios de aceite dos objetivos atendidos | 8 de 13 |
| Notebooks da cadeia que executam | 11 de 11 |
| Algoritmos de agrupamento comparados | 11 |
| Segmentos do modelo vencedor | 3 |
| Insights registrados na EDA | 12 |
| Lacunas registradas na avaliação | 8 (1 corrigida) |

---

???+ success "Fase 1: Preparação do ambiente"
    - [x] Criar repositório a partir do `project-template`
    - [x] Instalar as ferramentas do projeto (`uv sync`)
    - [x] Fixar a semente aleatória em `src/config.py`
    - [x] Versionar o `uv.lock` para reprodutibilidade do ambiente

???+ success "Fase 2: Entendimento de negócio"
    - [x] Preencher o [Canvas do Problema](pbl/canvas-do-problema.md)
    - [x] Definir os [critérios de sucesso](criterios-sucesso.md) de negócio e técnicos
    - [x] Formular as 5 perguntas orientadas a dados (SMART)
    - [x] Registrar riscos, contingências e análise de custo-benefício

???+ success "Fase 3: Entendimento dos dados"
    - [x] Gerar o conjunto de dados com manifesto de carga assinado
    - [x] Gerar o dicionário de dados e as escalas ordinais (notebook 00)
    - [x] Realizar a análise exploratória nas **oito etapas** (notebook 01)
    - [x] Registrar a [coleção de insights](analise-exploratoria.md#colecao-de-insights) — 12 registros
    - [x] Alinhar os rótulos das escalas ordinais aos da ingestão — [lacuna 8](avaliacao.md#lacunas-e-erros-identificados)

???+ warning "Fase 4: Preparação dos dados"
    - [x] Aplicar os ajustes de dados, cada um com motivo registrado (notebook 02)
    - [x] Gerar a base tratada (2.927 × 90) e a base pré-processada (notebook 03)
    - [x] Produzir o relatório de [preparação dos dados](preparacao.md)
    - [ ] Retirar `preco_venda` e `subclasse` já no notebook 03

???+ warning "Fase 5: Modelagem"
    - [x] Varrer onze algoritmos de quatro famílias na mesma régua (04-0)
    - [x] Traçar o cotovelo e a silhueta de cada algoritmo (04-1)
    - [x] Reduzir dimensionalidade com PCA e UMAP (04-2)
    - [x] Minerar regras com Apriori, Eclat e FP-Growth (04-3)
    - [x] Produzir o [comparativo dos algoritmos](modelagem.md#os-algoritmos-comparados) e o [perfil dos segmentos](modelagem.md#os-tres-segmentos)
    - [ ] Medir a estabilidade da partição por reamostragem
    - [ ] Definir persona e ação para cada segmento
    - [x] Fazer o notebook bônus (07) executar com o dicionário atual

???+ success "Fase 6: Avaliação"
    - [x] Produzir o [relatório da avaliação dos resultados](avaliacao.md)
    - [x] Confrontar os critérios de sucesso (5 de 6, todos os críticos)
    - [x] Estimar o impacto financeiro em três cenários
    - [x] Registrar lacunas, descobertas e limitações
    - [x] Decidir a próxima ação: **implantar**

???+ warning "Fase 7: Implementação"
    - [x] Classificar imóveis novos com o modelo vencedor (notebook 06)
    - [x] Desenvolver a aplicação de consulta (`src/app/`)
    - [x] Produzir o [plano de monitoramento e manutenção](implementacao.md#monitoramento-e-manutencao)
    - [x] Produzir o relatório final (este site e `reports/relatorio-final.md`)
    - [ ] Medir a linha de base do monitoramento
    - [ ] Abrir a janela 1 (sombra) — aguarda persona e ação por segmento

---

## Rastreabilidade

Cada decisão do projeto está documentada na página da sua fase. A tabela abaixo é o
índice.

| Fase | Decisão | Evidência |
|:---|:---|:---|
| 2 | Escalas ordinais com os mesmos rótulos da ingestão, conferidas no notebook 00 | [Entendimento dos dados](entendimento-dados.md#as-escalas-ordinais) |
| 2 | Ausência de garagem, porão e lareira na origem é estrutural, não faltante | [Análise exploratória](analise-exploratoria.md) |
| 2 | Lotes e porões grandes são discrepantes legítimos, e ficam | [Análise exploratória](analise-exploratoria.md) |
| 3 | Remover só as 3 vendas parciais acima de 4.000 pés² | [Preparação](preparacao.md#a-curadoria-regra-a-regra) |
| 3 | `testada_lote` imputada pela mediana do bairro | [Preparação](preparacao.md#a-curadoria-regra-a-regra) |
| 3 | `MinMaxScaler` para contínuas e ordinais, *one-hot* para nominais | [Preparação](preparacao.md#o-pre-processamento) |
| 4 | Silhueta euclidiana como régua comum dos onze algoritmos | [Modelagem](modelagem.md#o-desenho-do-experimento) |
| 4 | Regra de admissão antes da silhueta: 2 a 8 segmentos, nenhum acima de 90%, ruído até 20% | [Modelagem](modelagem.md#a-regra-de-admissao) |
| 4 | Mini batch k-means com 3 segmentos; os três primeiros colocados escolhem *k* = 3 | [Modelagem](modelagem.md#a-escolha-do-modelo) |
| 4 | DBSCAN e Mean Shift sem configuração admitida | [Modelagem](modelagem.md#por-que-dbscan-e-mean-shift-falharam) |
| 5 | Aprovado: todos os critérios críticos atendidos | [Avaliação](avaliacao.md#os-criterios-de-sucesso) |
| 5 | Próxima ação: implantação | [Avaliação](avaliacao.md#53-determinar-as-proximas-etapas) |
| 6 | A aplicação reconstrói o pré-processamento e confere contra o 03 | [Implementação](implementacao.md#o-artefato) |

## O que ficou em aberto

1. **Dar persona e ação** a cada um dos três segmentos — pré-requisito da janela 1.
2. **Medir a linha de base** do monitoramento e **calibrar o corte de fronteira**.
3. **Validar as premissas financeiras**: o cenário base fecha o ano 1 com US$ 513.
4. **Medir a estabilidade** da partição por reamostragem e o índice de Rand contra as
   faixas de preço.
5. **Pendências de dados**, que não dependem de análise: tempo de permanência em
   estoque, custo efetivo de reforma e atributo do comprador. Ver
   [pendências de dados](criterios-sucesso.md#pendencias-de-dados).
