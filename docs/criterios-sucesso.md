# Critérios de sucesso

O sucesso do projeto é dado pela completude dos objetivos de negócio definidos a
seguir. Cada objetivo está no formato de história de usuário (**Como** / **Quero** /
**Para** / **Objetivo**), com os respectivos critérios de aceite.

!!! info "Origem destes critérios"
    Canvas do Problema, versão 1.0, preenchido com a Diretoria Comercial em
    04/08/2026 — [`docs/pbl/canvas-do-problema.md`](pbl/canvas-do-problema.md).
    Os valores numéricos vêm dos campos 4 (critério de sucesso do negócio) e 6
    (critério de sucesso técnico).

## Visão geral

| # | Objetivo de negócio | Solicitante | Entrega principal | Situação |
|:-:|:---|:---|:---|:-:|
| 1 | Segmentar a carteira em linhas de produto operáveis | Diretoria Comercial | Base segmentada + matriz comparativa | ✅ 4 de 4 |
| 2 | Descrever cada linha em linguagem de negócio | Diretoria Comercial | Personas com ação e métrica | ✅ 3 de 3 |
| 3 | Encontrar padrões de coocorrência que sustentem a segmentação | Gerência de Ativos | Regras de associação por segmento | ✅ 3 de 3 |
| 4 | Isolar os imóveis que não pertencem a nenhuma linha | Gerência de Ativos | Lista de imóveis fora de padrão | ✅ 1 de 1 |
| 5 | Entregar o resultado em forma utilizável pela operação | Comitê de Aquisição | Aplicação + plano de monitoramento | ✅ 2 de 2 |

---

## 1. Segmentar a carteira em linhas de produto operáveis

???+ success "Objetivo 1"
    **Como** Diretoria Comercial<br>
    **Quero** saber em quantos grupos naturais a carteira se divide e quais são<br>
    **Para** substituir a política única por políticas por linha de produto<br>
    **Objetivo** alocar capital de reforma e esforço de corretagem por retorno esperado

    **Critérios de aceite:**

    - [x] **No máximo 5 segmentos** — o orçamento financia cinco ações diferenciadas.
      *Obtido: 4.*
    - [x] **Silhueta ≥ 0,15** — piso abaixo do qual os grupos não têm separação
      defensável. *Obtido: 0,1775.*
    - [x] **Estabilidade ARI ≥ 0,75** sob reamostragem de 80% da carteira, em 40
      repetições. *Obtido: 0,9433.*
    - [x] **Nenhum segmento abaixo de 2% da carteira** — abaixo disso não há massa
      para uma ação própria. *Obtido: 2,7% no menor.*

    **Entrega:** `data/processed/imoveis_segmentados.parquet` ·
    [matriz comparativa](modelagem.md#a-matriz-comparativa) ·
    `reports/tables/modelagem/m12-matriz-comparativa.csv`

## 2. Descrever cada linha em linguagem de negócio

???+ success "Objetivo 2"
    **Como** Diretoria Comercial<br>
    **Quero** que cada grupo tenha nome, descrição, ação e forma de medir o efeito<br>
    **Para** conseguir apresentar ao conselho e delegar a execução<br>
    **Objetivo** transformar um agrupamento estatístico em política comercial

    **Critérios de aceite:**

    - [x] **Persona, ação diferenciada e métrica de acompanhamento** para cada
      segmento. *Obtido: 4 de 4.*
    - [x] **Um imóvel real representante** por segmento, com identificador — o
      medoide, e não o centroide, que é uma média inexistente. *Obtido: 4 medoides.*
    - [x] **A segmentação não pode ser apenas uma faixa de preço**, medida pelo índice
      de Rand ajustado contra os quartis de `preco_venda`. Meta: < 0,40.
      *Obtido: 0,3112.*

    **Entrega:** [Personas](modelagem.md#as-quatro-personas) ·
    `reports/tables/modelagem/m14-personas.csv` ·
    `reports/tables/modelagem/m13-medoides-reais.csv`

## 3. Encontrar padrões de coocorrência que sustentem a segmentação

???+ success "Objetivo 3"
    **Como** Gerência de Ativos<br>
    **Quero** saber que combinações de atributos aparecem juntas com mais frequência
    do que o acaso explicaria<br>
    **Para** ter uma leitura da carteira que não dependa de abrir um modelo<br>
    **Objetivo** validar — ou contestar — a segmentação por um caminho independente

    **Critérios de aceite:**

    - [x] **Ao menos 10 regras** com suporte ≥ 10%, confiança ≥ 70% e lift ≥ 1,30,
      após a poda de trivialidade e redundância. *Obtido: 25 publicadas, de 256
      sobreviventes.*
    - [x] **Ao menos um padrão diferencial por segmento** — regra que vale dentro do
      grupo e não vale na carteira inteira. *Obtido: os 4 segmentos cobertos.*
    - [x] **Apriori, Eclat e FP-Growth devolvem os mesmos conjuntos frequentes** para
      os mesmos limiares. *Obtido: 3 de 3 idênticos, 1.597 conjuntos cada.*

    **Entrega:** [Regras de associação](modelagem.md#regras-de-associacao) ·
    `reports/tables/associacao/r2-principais-regras.csv` ·
    `reports/tables/associacao/r3-regras-diferenciais.csv`

## 4. Isolar os imóveis que não pertencem a nenhuma linha

???+ success "Objetivo 4"
    **Como** Gerência de Ativos<br>
    **Quero** a lista dos imóveis que não se encaixam em nenhum grupo<br>
    **Para** tratá-los individualmente, em vez de forçá-los a uma política que não
    lhes serve<br>
    **Objetivo** parar de aplicar política de massa a ativo atípico

    **Critérios de aceite:**

    - [x] **Ruído ≤ 10% da carteira** — acima disso, a "exceção" vira regra e a lista
      deixa de ser acionável. *Obtido: 1,81% (53 imóveis).*

    **Entrega:** `reports/tables/modelagem/m7-imoveis-fora-de-padrao.csv` ·
    coluna `fora_de_padrao_dbscan` na base segmentada · filtro dedicado na aplicação

    !!! note "O ruído como produto"
        O DBSCAN **falhou** como algoritmo de segmentação neste conjunto — devolve um
        grupo com 92% da carteira. O que ele entrega de valor é justamente o que
        costuma ser descartado: os pontos que não entraram em grupo nenhum.

## 5. Entregar o resultado em forma utilizável pela operação

???+ success "Objetivo 5"
    **Como** Comitê de Aquisição<br>
    **Quero** consultar a linha de produto de um imóvel antes de decidir comprá-lo<br>
    **Para** aplicar a política certa desde a aquisição<br>
    **Objetivo** que o resultado exista depois que o notebook fechar

    **Critérios de aceite:**

    - [x] **Modelo serializado e aplicação de consulta publicada**, com o
      pré-processamento embutido no artefato. *Obtido: `pipeline_segmentacao.joblib`
      reproduz 100% da classificação de treino; aplicação em `src/deployment/app.py`.*
    - [x] **Plano de monitoramento com gatilho quantitativo**, periodicidade e
      responsável nominal. *Obtido: 6 indicadores, com gatilho e responsável.*

    **Entrega:** [Implementação](implementacao.md) · `models/` ·
    `reports/tables/implantacao/i3-plano-de-monitoramento.csv`

---

## Consolidado dos critérios de aceite

| Objetivo | Critérios de aceite | Atendidos | Observação |
|:---|:-:|:-:|:---|
| 1. Segmentar a carteira | 4 | 4 | `k=5` foi testado e reprovado na estabilidade |
| 2. Descrever em linguagem de negócio | 3 | 3 | — |
| 3. Padrões de coocorrência | 3 | 3 | Limiar recalibrado após a primeira rodada |
| 4. Imóveis fora de padrão | 1 | 1 | — |
| 5. Entrega operacional | 2 | 2 | — |
| **Total** | **13** | **13** | |

![Confronto com os critérios](imagens/evidencias/avaliacao/a1-criterios-por-objetivo.png)

O confronto detalhado, critério a critério, está em
[Avaliação dos resultados](avaliacao.md).

## Pendências de dados

Critérios que **não** dependem de análise, e sim de dado que não veio na origem.

| # | Pendência | Destrava |
|:-:|:---|:---|
| 1 | **Tempo de permanência em estoque** por imóvel | As metas de giro das personas S2 e S4 deixariam de ser propostas e passariam a ser indicadores medidos |
| 2 | **Custo efetivo de reforma** por imóvel | Permitiria calcular o retorno real da reforma por segmento, hoje estimado |
| 3 | **Canal de origem do comprador** | Habilitaria a segmentação de **demanda**, que a base atual não permite: aqui só há atributo de produto |

!!! warning "Sobre a pendência 3"
    É a limitação mais importante do projeto, e ela é estrutural: a base descreve o
    **imóvel**, não quem o comprou. Nenhuma ação de segmentação de clientes pode ser
    derivada daqui, e afirmar o contrário seria estender o resultado além do que o
    dado sustenta.
