# Critérios de sucesso

O sucesso do projeto é dado pela completude dos objetivos de negócio definidos a
seguir. Cada objetivo está no formato de história de usuário (**Como** / **Quero** /
**Para** / **Objetivo**), com os respectivos critérios de aceite.

!!! info "Origem destes critérios"
    Os objetivos vêm do [Canvas do Problema](pbl/canvas-do-problema.md). Os valores
    numéricos dos critérios técnicos são os que o notebook `05-avaliacao` aplica
    (meta 1.1): eles foram declarados no código **antes** de o resultado ser lido, e são
    os mesmos que decidem se o modelo vai para implantação. Os valores obtidos vêm do
    registro `reports/05-avaliacao.json` e das saídas dos notebooks 04-0 a 04-3.

## Visão geral

| # | Objetivo de negócio | Solicitante | Entrega principal | Situação |
|:-:|:---|:---|:---|:-:|
| 1 | Segmentar a carteira em linhas de produto operáveis | Diretoria Comercial | Segmentos de cada imóvel + varredura comparativa | ⚠️ 3 de 4 |
| 2 | Descrever cada linha em linguagem de negócio | Diretoria Comercial | Perfil de cada segmento em unidades de negócio | ⚠️ 1 de 2 |
| 3 | Encontrar padrões de coocorrência que sustentem a segmentação | Gerência de Ativos | Regras de associação | ⚠️ 2 de 3 |
| 4 | Isolar os imóveis que não pertencem a nenhuma linha | Gerência de Ativos | Lista de imóveis fora de padrão | ❌ 0 de 1 |
| 5 | Entregar o resultado em forma utilizável pela operação | Comitê de Aquisição | Aplicação de consulta | ⚠️ 2 de 3 |

---

## 1. Segmentar a carteira em linhas de produto operáveis

???+ success "Objetivo 1 — atendido, com ressalva"
    **Como** Diretoria Comercial<br>
    **Quero** saber em quantos grupos naturais a carteira se divide e quais são<br>
    **Para** substituir a política única por políticas por linha de produto<br>
    **Objetivo** alocar capital de reforma e esforço de corretagem por retorno esperado

    **Critérios de aceite:**

    - [x] **Entre 2 e 5 segmentos** *(crítico)* — o orçamento financia até cinco ações
      diferenciadas. *Obtido: 3.*
    - [x] **Menor segmento com ao menos 10% da carteira** *(crítico)* — abaixo disso o
      segmento não paga uma ação dedicada. *Obtido: 23,8% (Segmento C, 698 imóveis).*
    - [ ] **Silhueta ≥ 0,25** *(não crítico)* — separação geométrica dos grupos.
      *Obtido: 0,102.*
    - [x] **100% da carteira com segmento** *(não crítico)* — nenhum imóvel como ruído.
      *Obtido: 100%.*

    **Entrega:** [varredura e escolha do modelo](modelagem.md#os-algoritmos-comparados) ·
    `data/processed/segmentos.csv` · `models/selecionado.json`

## 2. Descrever cada linha em linguagem de negócio

???+ warning "Objetivo 2 — parcialmente atendido"
    **Como** Diretoria Comercial<br>
    **Quero** que cada grupo tenha nome, descrição, ação e forma de medir o efeito<br>
    **Para** conseguir apresentar ao conselho e delegar a execução<br>
    **Objetivo** transformar um agrupamento estatístico em política comercial

    **Critérios de aceite:**

    - [x] **O preço distingue os segmentos** *(crítico)* — razão entre o preço mediano
      do segmento mais caro e o do mais barato ≥ 1,30, com Kruskal-Wallis p < 0,05.
      *Obtido: 1,84 (US$ 221.000 contra US$ 120.000), p ≈ 0.*
    - [ ] **Persona, política de preço, teto de reforma, canal e métrica** para cada
      segmento. *Não feito na cadeia atual:* os três segmentos têm perfil em unidades
      de negócio, mas ainda não têm ação nem métrica. O catálogo em
      `src/model/personas.py` descreve as três linhas da cadeia anterior, com outra
      base e outro espaço de atributos, e não se aplica aos segmentos A a C.

    **Entrega:** [os três segmentos](modelagem.md#os-tres-segmentos)

## 3. Encontrar padrões de coocorrência que sustentem a segmentação

???+ warning "Objetivo 3 — parcialmente atendido"
    **Como** Gerência de Ativos<br>
    **Quero** saber que combinações de atributos aparecem juntas com mais frequência
    do que o acaso explicaria<br>
    **Para** ter uma leitura da carteira que não dependa de abrir um modelo<br>
    **Objetivo** validar — ou contestar — a segmentação por um caminho independente

    **Critérios de aceite:**

    - [x] **Regras fortes em volume utilizável.** *Obtido no notebook 04-3: 177.294
      regras geradas, 23.403 com confiança ≥ 60% e lift ≥ 1,20, sobre conjuntos com
      suporte ≥ 15%.*
    - [x] **Apriori, Eclat e FP-Growth devolvem os mesmos conjuntos frequentes** para
      os mesmos limiares. *Obtido: os três encontraram os mesmos 31.601 conjuntos, com o
      mesmo suporte.*
    - [ ] **Ao menos um padrão diferencial por segmento** — regra que vale dentro do
      grupo e não vale na carteira inteira. *Não feito:* as regras foram mineradas na
      carteira inteira, sem cruzamento com os segmentos.

    **Entrega:** [Regras de associação](modelagem.md#regras-de-associacao) ·
    `data/processed/regras_associacao.csv`

## 4. Isolar os imóveis que não pertencem a nenhuma linha

???+ failure "Objetivo 4 — não atendido"
    **Como** Gerência de Ativos<br>
    **Quero** a lista dos imóveis que não se encaixam em nenhum grupo<br>
    **Para** tratá-los individualmente, em vez de forçá-los a uma política que não
    lhes serve<br>
    **Objetivo** parar de aplicar política de massa a ativo atípico

    **Critérios de aceite:**

    - [ ] **Ruído ≤ 20% da carteira e nenhum grupo com mais de 90% dos imóveis**, a
      regra de admissão do 04-0.

    **Situação.** Nem o DBSCAN nem o Mean Shift tiveram configuração aprovada. No
    notebook 04-1, a melhor silhueta do DBSCAN (0,232) vem com **83,1% da carteira como
    ruído**, e a do Mean Shift (0,224) junta **99,9% dos imóveis num grupo só**. Em ~200
    dimensões, a maioria *one-hot*, a densidade se dilui e não há vale entre grupos —
    ver [Modelagem](modelagem.md#por-que-dbscan-e-mean-shift-falharam).

## 5. Entregar o resultado em forma utilizável pela operação

???+ warning "Objetivo 5 — parcialmente atendido"
    **Como** Comitê de Aquisição<br>
    **Quero** consultar a linha de produto de um imóvel antes de decidir comprá-lo<br>
    **Para** aplicar a política certa desde a aquisição<br>
    **Objetivo** que o resultado exista depois que o notebook fechar

    **Critérios de aceite:**

    - [x] **Imóvel novo classificável** *(crítico)* — acurácia ≥ 85% de uma random
      forest que aprende o segmento a partir das mesmas variáveis, em validação cruzada
      de 5 partes. *Obtido: 96,9%.*
    - [x] **Modelo serializado e aplicação de consulta publicada.** *Obtido: a
      aplicação em `src/app/` lê o modelo do notebook 04-0, reconstrói o
      pré-processamento do 03 e confere, ao subir, que ele reproduz a saída do 03 e que
      o modelo reproduz 100% de `segmentos.csv`.*
    - [ ] **Plano de monitoramento com gatilho quantitativo**, periodicidade e
      responsável nominal. *Ainda não medido:* o plano em
      [Implementação](implementacao.md#monitoramento-e-manutencao) é a proposta, e a
      linha de base de cada indicador precisa ser medida antes da janela 1.

    **Entrega:** [Implementação](implementacao.md) · `src/app/`

---

## Consolidado dos critérios de aceite

| Objetivo | Critérios de aceite | Atendidos | Observação |
|:---|:-:|:-:|:---|
| 1. Segmentar a carteira | 4 | 3 | A silhueta (0,102) fica abaixo de 0,25 — critério não crítico |
| 2. Descrever em linguagem de negócio | 2 | 1 | Falta transformar o perfil em ação e métrica |
| 3. Padrões de coocorrência | 3 | 2 | Falta cruzar as regras com os segmentos |
| 4. Imóveis fora de padrão | 1 | 0 | Nenhum algoritmo de densidade foi admitido |
| 5. Entrega operacional | 3 | 2 | Falta medir a linha de base do monitoramento |
| **Total** | **13** | **8** | |

Todos os critérios **críticos** da fase 5 foram atendidos, e a decisão registrada é
**implantar**, com a ressalva da silhueta. Os critérios em aberto acima não barram a
implantação, mas são pré-requisitos da entrada em produção — ver
[Implementação](implementacao.md#plano-de-implantacao). O confronto detalhado está em
[Avaliação dos resultados](avaliacao.md).

## Critérios de negócio

Os critérios de negócio do Canvas §4 — giro, preço realizado sobre anunciado, retorno
da reforma, destino do estoque herdado — **não têm leitura**: só existem depois que uma
política por segmento entra em operação, e dependem de dados que a base não traz.

## Pendências de dados

Critérios que **não** dependem de análise, e sim de dado que não veio na origem.

| # | Pendência | Destrava |
|:-:|:---|:---|
| 1 | **Tempo de permanência em estoque** por imóvel | As metas de giro deixariam de ser proposta e passariam a ser indicador medido |
| 2 | **Custo efetivo de reforma** por imóvel | Permitiria calcular o retorno real da reforma por segmento |
| 3 | **Canal de origem do comprador** | Habilitaria a segmentação de **demanda**, que a base atual não permite: aqui só há atributo de produto |

!!! warning "Sobre a pendência 3"
    É a limitação mais importante do projeto, e ela é estrutural: a base descreve o
    **imóvel**, não quem o comprou. Nenhuma ação de segmentação de clientes pode ser
    derivada daqui, e afirmar o contrário seria estender o resultado além do que o
    dado sustenta.
