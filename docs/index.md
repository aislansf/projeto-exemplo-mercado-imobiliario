# Segmentação da carteira residencial — Meridiano Imobiliária

## Introdução

A Meridiano Imobiliária administra uma carteira residencial transacionada em Ames,
Iowa, entre 2006 e 2010 — **2.350 imóveis** depois da curadoria, partindo de 2.930
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
    Três linhas de produto, cada uma com persona, política de preço, teto de reforma,
    canal de venda e métrica de acompanhamento próprios. Silhueta de **0,1726**,
    estabilidade de **0,9575** sob reamostragem e **7 de 7** critérios técnicos
    atendidos. A entrega operacional é a [aplicação de consulta](implementacao.md) que
    o corretor abre no navegador, servida por um pacote autocontido.

## Dados do projeto

A base é o **Ames Housing**, publicado por De Cock (2011) no *Journal of Statistics
Education*. São 2.930 imóveis descritos por 82 colunas — 23 nominais, 23 ordinais, 14
discretas e 20 contínuas. É, provavelmente, o conjunto de dados residencial público
mais rico em atributos de **produto**, e é isso que o torna adequado a uma pergunta
de segmentação.

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
    - [ ] Detecção de anomalias *(prometida no Canvas §5; ver [o que não foi entregue](avaliacao.md))*
    - [ ] Mineração de regras de associação *(idem)*

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

!!! warning "O que esta cadeia não entrega"
    Os objetivos **3** e **4** não foram executados sobre a carteira depurada. A
    varredura da fase 4 não encontrou configuração de DBSCAN com ruído dentro do teto
    **e** número de grupos na faixa, e a etapa de regras de associação não foi refeita.
    As duas decisões estão registradas como deliberações em aberto na sessão de
    encerramento — não como resultados.

## As três linhas de produto

| Código | Persona | Imóveis | % da carteira | % da receita | Ação diferenciada |
|:--|:--|--:|--:|--:|:--|
| **S1** | Compacto herdado | 914 | 38,9% | 27,3% | Decisão unidade a unidade: reforma leve e venda, renda ou desinvestimento |
| **S2** | Amplo para requalificar | 667 | 28,4% | 27,9% | Reforma de valorização em cozinha e banheiro, antes do anúncio |
| **S3** | Recente de alto padrão | 769 | 32,7% | 44,8% | Sem reforma; corretagem dedicada e vitrine premium |

![As três linhas de produto](imagens/implantacao/linhas-de-produto.png)

Um terço das unidades responde por quase metade da receita, e a alavanca de reforma não
está no segmento mais caro: o **S2** tem o menor preço por pé² da carteira — US$ 105,42
contra US$ 133,90 do S3 — com 55% mais área que o S1.

!!! note "O modelo diz onde não sabe"
    **339 imóveis (14,4%)** ficam na faixa de fronteira entre duas linhas e vão para
    revisão humana em vez de receber ação automática. A regra que decide isso foi
    calibrada sobre a carteira, não escolhida por intuição — ver
    [Implementação](implementacao.md).

## Como reproduzir

```bash
uv sync                    # cria o ambiente a partir do uv.lock
uv run invoke ingestao     # baixa a base e materializa data/raw com manifesto
uv run invoke notebooks    # os notebooks 00 a 06 — do dicionário ao pacote publicado
uv run invoke app          # a aplicação, em http://localhost:8501
uv run invoke docs         # este site, em http://127.0.0.1:8000
```

A semente do projeto é **42**, e a cadeia reexecutada devolve a mesma partição: a fase 5
mediu **ARI 1,0000** na reexecução. Nada precisa ser baixado à mão, e nada depende de
credencial.

## Sobre o projeto

### Histórico do documento

| Data       | Versão | Descrição                                                    | Autor          |
| :--------- | :----- | :----------------------------------------------------------- | :------------- |
| 04/08/2026 | 1.0    | Ciclo CRISP-DM completo, com aplicação de implantação publicada | Aislan Freitas |
| 20/08/2026 | 2.0    | Cadeia reconstruída nos notebooks 00–06 sobre a carteira depurada: três linhas de produto, critérios lidos dos manifestos e aplicação servida por pacote autocontido | Aislan Freitas |

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
