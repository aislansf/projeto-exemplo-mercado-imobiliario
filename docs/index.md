# Segmentação da carteira residencial — Meridiano Imobiliária

## Introdução

A Meridiano Imobiliária administra uma carteira residencial transacionada em Ames,
Iowa, entre 2006 e 2010 — **2.927 imóveis** depois dos ajustes, partindo de 2.930
registros brutos. Compra, requalifica e revende parte desse estoque; intermedeia o
restante. Hoje todos os imóveis recebem a **mesma** política de preço, o mesmo teto de
reforma e o mesmo canal de anúncio.

O pedido que chegou à área de dados foi curto: *como esses imóveis se organizam
naturalmente, e o que devemos fazer de diferente com cada grupo?* Com uma restrição
que muda tudo — **há orçamento para no máximo cinco linhas de produto**.

Não existe rótulo. Ninguém nunca marcou qual imóvel é "de entrada" e qual é "de alto
padrão": essa é justamente a pergunta. O preço de venda existe na base, mas é
**rótulo reservado** — usá-lo na modelagem transformaria a tarefa em regressão e
devolveria uma tabela de preço, que a diretoria já tem.

!!! success "O resultado"
    Onze algoritmos foram comparados na mesma régua. O vencedor, um **mini batch
    k-means com 3 segmentos**, passa em todos os critérios críticos da avaliação: o menor
    segmento tem **23,8%** da carteira, o segmento mais caro vale **1,84×** o mais barato
    e um imóvel novo é classificado no segmento certo em **96,9%** dos casos. A fase 5
    **aprovou a implantação**, com uma ressalva: a silhueta de **0,102** indica que os
    segmentos são faixas de uma carteira contínua, e não grupos isolados.

    A entrega operacional é a [aplicação de consulta](implementacao.md), que lê os
    arquivos gravados pelos notebooks.

## Dados do projeto

A base é o **Ames Housing**, publicado por De Cock (2011) no *Journal of Statistics
Education*. São 2.930 imóveis descritos por 82 colunas — pelo dicionário do notebook
00, 23 nominais, 22 ordinais, 22 discretas, 10 contínuas e 5 temporais. É,
provavelmente, o conjunto de dados residencial público mais rico em atributos de
**produto**, e é isso que o torna adequado a uma pergunta de segmentação.

!!! tip "Por que esta base, e não outra"
    O Ames Housing é conhecido como um problema de **regressão de preço** — foi
    publicado com essa finalidade. Este projeto faz o oposto: joga o preço fora e
    pergunta o que sobra. A mesma base, sem a variável-alvo, responde a uma pergunta
    completamente diferente.

### Levantamento inicial

!!! info "Tipo do projeto"
    - [ ] Análise exploratória
    - [ ] Modelo preditivo
    - [ ] Modelo de classificação
    - [x] **Modelo de agrupamento**
    - [ ] Detecção de anomalias *(prometida no Canvas §5; nenhuma configuração de densidade foi aprovada — ver [Modelagem](modelagem.md#por-que-dbscan-e-mean-shift-falharam))*
    - [x] Mineração de regras de associação *(notebook 04-3, como leitura complementar)*

### Nível de acesso

!!! warning "Confidencialidade"
    - [x] **Público** — a base de origem é publicada com licença de uso educacional
      e de pesquisa, mediante citação. Não há dado pessoal identificável: o `PID` é o
      número da matrícula do imóvel, não do proprietário.
    - [ ] Interno (toda a organização)
    - [ ] Restrito (apenas a área requisitante)

### Objetivos de negócio

!!! quote ""
    **1.** Segmentar a carteira em, no máximo, cinco linhas de produto operáveis.

    **2.** Descrever cada linha em linguagem de negócio, com persona, ação
    diferenciada e métrica de acompanhamento.

    **3.** Encontrar padrões de coocorrência entre atributos construtivos que
    sustentem — ou contestem — a segmentação.

    **4.** Isolar os imóveis que não pertencem a nenhuma linha e exigem avaliação
    individual.

    **5.** Entregar o resultado em forma utilizável pela operação, com plano de
    monitoramento.

Os critérios de aceite de cada objetivo estão em
[Critérios de sucesso](criterios-sucesso.md), e o confronto entre o prometido e o
entregue está em [Avaliação dos resultados](avaliacao.md).

## Os três segmentos

Os segmentos são nomeados de A a C, do preço mediano mais alto ao mais baixo. O preço
não entrou no agrupamento: aparece aqui só para ler o resultado.

| Segmento | Imóveis | % da carteira | % do valor de venda | Preço mediano | Retrato |
|:--|--:|--:|--:|--:|:--|
| **A** | 1.105 | 37,8% | 50,8% | US$ 221.000 | Casa recente (5 anos) de padrão alto, fundação em concreto moldado |
| **B** | 1.124 | 38,4% | 32,8% | US$ 145.000 | Casa térrea de meia-idade (43 anos) em bairro residencial de baixa densidade |
| **C** | 698 | 23,8% | 16,4% | US$ 120.000 | Casa antiga (80 anos) do centro, com garagem separada |

Um pouco mais de um terço das unidades (o **Segmento A**) responde por metade do valor
de venda da carteira. Os segmentos ainda não têm persona nem ação comercial definidas —
é o passo seguinte da implantação.

## Como reproduzir

```bash
uv sync                    # cria o ambiente a partir do uv.lock
uv run invoke ingestao     # baixa a base e materializa data/raw com manifesto
uv run invoke notebooks    # os notebooks 00 a 07, do dicionário à implantação
uv run invoke app          # a aplicação, em http://localhost:8501
uv run invoke docs         # este site, em http://127.0.0.1:8000
```

A semente do projeto é **42**. Nada precisa ser baixado à mão, e nada depende de
credencial.

## Sobre o projeto

### Histórico do documento

| Data       | Versão | Descrição                                                    | Autor          |
| :--------- | :----- | :----------------------------------------------------------- | :------------- |
| 04/08/2026 | 1.0    | Ciclo CRISP-DM completo, com aplicação de implantação publicada | Aislan Freitas |
| 20/08/2026 | 2.0    | Cadeia reconstruída nos notebooks 00–06 sobre a carteira depurada | Aislan Freitas |
| 16/10/2026 | 3.0    | Site reescrito sobre a cadeia atual (notebooks 00 a 07) e aplicação servida pelos artefatos dos notebooks | Aislan Freitas |
| 16/10/2026 | 3.1    | Escalas ordinais do notebook 00 alinhadas aos rótulos da ingestão; cadeia reexecutada: 3 segmentos, modelo aprovado para implantação | Aislan Freitas |

### Dados do solicitante

``` mermaid
flowchart TD
    id1[Diretoria Comercial] --o id2[Gerência de Ativos]
    id1 --o id3[Comitê de Aquisição]
```

| Nome                      | Cargo / Função                | E-mail            |
| :------------------------ | :---------------------------- | :---------------- |
| Diretoria Comercial       | Patrocinadora do projeto      | comercial@meridiano.exemplo |
| Gerência de Ativos        | Dona da operação de estoque   | ativos@meridiano.exemplo |
| Comitê de Aquisição       | Consumidor da classificação   | aquisicao@meridiano.exemplo |

### Dados da equipe técnica

| Nome               | Cargo / Função        | E-mail            |
| :----------------- | :-------------------- | :---------------- |
| Aislan Freitas     | Cientista de dados    | aislansf@gmail.com |

!!! note "Sobre este repositório"
    Este é um **projeto de demonstração** da disciplina *Método de Aprendizado Não
    Supervisionado*, construído a partir do
    [`project-template`](https://github.com/aislansf/project-template). A Meridiano
    Imobiliária é uma organização fictícia; os dados são reais e públicos. O objetivo
    é mostrar o ciclo CRISP-DM percorrido inteiro, com todas as evidências
    materializadas em disco.
