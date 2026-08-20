# Status do projeto

**Ciclo CRISP-DM concluído.** Decisão formal: **implantar**.

| Indicador | Valor |
|:---|---:|
| Fases do CRISP-DM concluídas | 6 de 6 |
| Critérios de aceite atendidos | **13 de 13** |
| Notebooks que executam de ponta a ponta | 7 de 7 |
| Figuras persistidas | 46 |
| Tabelas-fonte persistidas | 98 |
| Insights registrados na EDA | 21 |
| Hipóteses derrubadas e documentadas | 3 |

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
    - [x] Produzir o relatório de qualidade dos dados
    - [x] Realizar a descrição dos dados (grão, tipos, cobertura)
    - [x] Realizar a análise exploratória nas **oito fases**
    - [x] Produzir a [coleção de insights](analise-exploratoria.md#colecao-de-insights) — 21 registros

???+ success "Fase 4: Preparação dos dados"
    - [x] Gerar o script de limpeza (10 regras, cada uma com motivo registrado)
    - [x] Gerar o conjunto de dados processado
    - [x] Executar o [experimento de sensibilidade à escala](preparacao.md#o-experimento-de-sensibilidade-a-escala)
    - [x] Produzir o relatório de [preparação dos dados](preparacao.md)

???+ success "Fase 5: Modelagem"
    - [x] Comparar três leituras do espaço de atributos
    - [x] Gerar o desenho do experimento de modelagem
    - [x] Determinar *k* por 4 métricas, estabilidade e restrição operacional
    - [x] Aplicar 6 famílias de algoritmo (K-Means, K-Medoids, hierárquica, DBSCAN, Mean Shift, GMM)
    - [x] Reduzir dimensionalidade com PCA e Kernel PCA
    - [x] Minerar regras com Apriori, Eclat e FP-Growth
    - [x] Produzir o [placar dos candidatos](modelagem.md#os-algoritmos-comparados) e as [linhas de produto](modelagem.md#as-tres-linhas-de-produto)

???+ success "Fase 6: Avaliação"
    - [x] Produzir o [relatório da avaliação dos resultados](avaliacao.md)
    - [x] Confrontar cada critério de aceite (13 de 13)
    - [x] Registrar limitações e hipóteses derrubadas
    - [x] Produzir o relatório das próximas etapas

???+ success "Fase 7: Implementação"
    - [x] Gerar o desenho da implementação
    - [x] Desenvolver a aplicação de implantação (`src/app/`)
    - [x] Produzir o [relatório de monitoramento e manutenção](implementacao.md#monitoramento-e-manutencao)
    - [x] Produzir o relatório final contendo todas as fases anteriores (este site)

---

## Rastreabilidade

Cada decisão do projeto tem uma evidência em disco. A tabela abaixo é o índice.

| Fase | Decisão | Evidência |
|:---|:---|:---|
| 2 | Ausência de garagem e porão é estrutural, não faltante | `reports/tables/eda-exploratoria/valores-ausentes.csv` |
| 2 | 8,6% fora das cercas de Tukey é discrepância de escala | `reports/tables/eda-exploratoria/valores-discrepantes.csv` |
| 3 | Remover 492 vendas não normais — 85% do que a curadoria corta | `reports/tables/ajustes-dados/funil-da-curadoria.csv` |
| 3 | 3×IQR em vez do 1,5 de Tukey | `reports/tables/ajustes-dados/discrepantes-dois-criterios.csv` |
| 3 | Raiz quadrada em `area_varandas`, e só nela | `reports/tables/preparacao/transformacoes-da-assimetrica.csv` |
| 3 | `StandardScaler`, apesar de não ter a melhor silhueta | `reports/tables/preparacao/sensibilidade-a-escala.csv` |
| 3 | `preco_venda`, `preco_por_pe2` e `bairro` reservados **fisicamente** | `reports/tables/preparacao/evidencia-das-reservadas.csv` |
| 4 | *k* = 3 — o maior *k* que passa em todos os critérios | `reports/tables/modelagem/decisao-de-k.csv` |
| 4 | K-Means sobre espaço euclidiano de 17 variáveis | `reports/tables/modelagem/placar-dos-candidatos.csv` |
| 4 | Ward, apesar do pior coeficiente cofenético | `reports/tables/modelagem/ligacoes-e-dendrograma.csv` |
| 4 | GMM (diag) recusado por estar fora do protocolo declarado | `reports/tables/modelagem/gmm-selecao.csv` |
| 5 | Não é tabela de preço (ARI 0,3345) | `reports/tables/avaliacao/independencia-do-preco.csv` |
| 5 | As maiores silhuetas da varredura ampla são degeneradas | `reports/tables/avaliacao/as-dez-maiores-silhuetas.csv` |
| 6 | Corte de fronteira 0,915, calibrado por F1 sob teto de 15% | `reports/tables/implantacao/calibracao-da-fronteira.csv` |
| 6 | O pacote relido reproduz 100% da partição aprovada | `reports/tables/implantacao/conferencia-do-pacote.csv` |
| 6 | Nenhum atributo em drift de ação (PSI máximo 0,0369) | `reports/tables/implantacao/desvio-medido.csv` |

## O que ficou em aberto

Nada dos critérios de aceite. Três **pendências de dados**, que não dependem de
análise:

1. Tempo de permanência em estoque — destravaria as metas de giro como indicadores
   medidos.
2. Custo efetivo de reforma — destravaria o retorno real por segmento.
3. Atributo do comprador — destravaria a segmentação de demanda, que a base atual não
   permite.

Ver [pendências de dados](criterios-sucesso.md#pendencias-de-dados).
