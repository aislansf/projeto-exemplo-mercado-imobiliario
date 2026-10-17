# Implementação

**CRISP-DM fase 6.** É o ponto em que o resultado da modelagem deixa de ser um notebook
e vira algo que o corretor abre no navegador para consultar um imóvel.

A fase entrega três coisas: a **classificação de imóveis novos** (notebook 06), a
**aplicação de consulta** que serve o modelo e um **plano de implantação e
monitoramento**.

!!! success "Aprovado pela fase 5, com pré-requisitos para a produção"
    A [avaliação](avaliacao.md) **aprovou** o modelo para implantação, com a ressalva da
    silhueta baixa. A aplicação já serve o modelo vencedor. A entrada em produção segue
    o plano abaixo e depende de três pré-requisitos: persona e ação por segmento, linha
    de base do monitoramento e premissas financeiras validadas.

## Classificação de imóveis novos

O notebook 06 atribui um segmento a um imóvel novo em três passos:

1. **modelo:** lê o vencedor do 04-0 a partir de `models/selecionado.json`;
2. **entrada:** o imóvel novo, em unidades de negócio (pés², nota, bairro…), passa pelo
   mesmo pré-processamento do 03;
3. **saída:** o segmento do imóvel, com o perfil desse segmento na carteira.

O 03 grava a base transformada, mas não o pré-processador. O 06 o refaz com as mesmas
regras, ajustado na mesma base tratada, e **confere que o resultado bate com a saída do
03** antes de seguir — 236 variáveis, idênticas. Também confere que o modelo relido do
disco reproduz `segmentos.csv`: **100% de concordância**.

O imóvel novo pode vir incompleto. O que não foi informado é emprestado do **imóvel
mais parecido da carteira**: o que tem as mesmas categorias informadas e os números mais
próximos. Os dois exemplos do notebook:

| Imóvel | Área habitável | Qualidade | Idade | Anos desde a reforma | Banheiros | Lareira | 2º pavimento | Segmento |
|:---|--:|--:|--:|--:|--:|:-:|:-:|:---|
| Casa nova, grande, alto padrão | 2.400 | 8 | 3 | 3 | 3,5 | sim | sim | **A** |
| Casa antiga e pequena | 950 | 4 | 80 | 50 | 1,0 | não | não | **C** |

## A aplicação

```bash
uv run invoke app
```

Sobe em `http://localhost:8501` e roda **inteiramente local**: nenhuma chamada de rede,
nenhum serviço externo. Lê os arquivos que os notebooks gravam em `data/processed/` e
`models/`; as projeções do 04-2, as regras do 04-3 e a avaliação do 05 entram quando
existem.

| Módulo | Responsabilidade |
|:---|:---|
| `src/app/artefatos.py` | Lê os arquivos, reconstrói o espaço do modelo e classifica. Sem Streamlit — serve também a script e a rotina de carga |
| `src/app/app.py` | A interface. Só apresenta o que `artefatos.py` devolve |

As sete abas seguem o caminho de quem usa:

1. **Resultado do modelo** — segmentos, participação em imóveis e em valor de venda,
   preço por segmento e os critérios de sucesso do 05;
2. **Classificar um imóvel** — o usuário informa o que souber e o restante vem do
   imóvel mais parecido da carteira; devolve segmento, distância a cada segmento e
   razão de fronteira;
3. **Perfil dos segmentos** — o retrato de cada segmento, a assinatura que os separa e
   a carteira projetada por UMAP ou PCA;
4. **Carteira classificada** — os imóveis da base tratada com filtros, gráficos e
   download;
5. **Classificação em lote** — CSV entra, lista classificada sai;
6. **Regras de associação** — as regras do 04-3, filtráveis por lift, confiança e item;
7. **Procedência** — os arquivos lidos, quando foram gravados e as duas conferências.

O detalhe está em
[`src/app/README.md`](https://github.com/aislansf/projeto-exemplo-mercado-imobiliario/blob/main/src/app/README.md).

### O artefato

A aplicação não tem um artefato próprio: ela lê o que os notebooks gravam.

| Arquivo | Notebook | Papel |
|:---|:-:|:---|
| `models/selecionado.json` | 04-0 | nome, parâmetros, número de segmentos, silhueta e arquivo do vencedor |
| `models/model_imoveis_<modelo>.joblib` | 04-0 | o modelo vencedor, ajustado |
| `data/processed/segmentos.csv` | 04-0 | o segmento de cada imóvel da carteira |
| `data/processed/ames_housing_tratado.csv` | 02 | a base tratada, em unidades de negócio |
| `data/processed/dicionario.csv`, `escala.csv` | 00 | o tipo de cada variável e os níveis ordinais |
| `data/processed/ames_housing_preprocessed.csv` | 03 | só para conferir o pré-processamento reconstruído |

!!! success "Conferido a cada carga"
    Ao subir, a aplicação confere duas coisas: que o pré-processamento reconstruído é
    idêntico à saída do notebook 03 e que o modelo relido do disco reproduz 100% de
    `segmentos.csv`. As duas aparecem na aba *Procedência*. Se um notebook regravar
    algum arquivo, a aplicação relê tudo sozinha.

### A arquitetura de integração

| Etapa | O que acontece | Onde | O que acontece na falha |
|:---|:---|:---|:---|
| **1 · Carga** | O cadastro publica a base do mês | `data/raw/` — job mensal | A carga é bloqueada e a classificação vigente permanece |
| **2 · Validação** | Cada registro é validado antes de entrar | `src/app/artefatos.py` (`validar`) | O registro é rejeitado **com o motivo**: coluna desconhecida, categoria que o modelo nunca viu ou nível fora da escala |
| **3 · Preparo** | Codificação ordinal, normalização e *one-hot*, com as regras do notebook 03 | `src/app/artefatos.py` (`transformar`) | A aplicação confere, ao subir, que o resultado é idêntico à saída do 03 |
| **4 · Atribuição** | Segmento e razão de fronteira | `predict` do modelo do 04-0 | Razão perto de 1 indica imóvel entre dois segmentos: revisão humana |
| **5 · Entrega em lote** | Carteira classificada em CSV | aba *Classificação em lote* | A linha com erro sai sem segmento e com o motivo, sem derrubar o lote |
| **6 · Consulta** | Classificação de um imóvel novo, sob demanda | aba *Classificar um imóvel* | — |

A etapa 3 é a que costuma quebrar em produção, e por isso é a que tem regra explícita:
**a preparação tem uma única receita**, a do notebook 03. A aplicação a reconstrói a
partir da base tratada, do dicionário e das escalas e confere o resultado contra
`ames_housing_preprocessed.csv`; se não bater, a aba *Procedência* acusa.

### O grau de confiança

A **razão de fronteira** é a distância ao centro do segmento atribuído dividida pela
distância ao segundo mais próximo. Perto de 1, o imóvel está entre dois segmentos. A
aplicação a calcula para cada imóvel da carteira:

| Segmento | Razão mediana | Imóveis com razão acima de 0,9 |
|:---|--:|--:|
| **A** | 0,770 | 17,1% |
| **B** | 0,844 | 28,0% |
| **C** | 0,862 | 36,4% |
| **Carteira** | **0,824** | **25,9%** (758 imóveis) |

O Segmento A é o mais coeso; no C, mais de um terço dos imóveis está quase à mesma
distância de dois segmentos. É coerente com a silhueta baixa: os segmentos são faixas
de uma carteira contínua.

!!! note "Sem corte calibrado"
    A razão é exibida, mas nenhum corte decide quando a ação automática dispara. Um corte
    precisa ser calibrado contra o volume que a Gerência de Ativos consegue revisar à
    mão — o 0,9 da tabela é só uma referência de leitura. Calibrar o corte é parte do
    plano abaixo.

## Plano de implantação

A entrada em produção é em **três janelas**, e nenhuma delas começa com a operação
mudando de comportamento. O plano vale para o modelo aprovado na fase 5.

| Janela | Período | Escopo | Critério de aceite | Plano de retorno |
|:---|:---|:---|:---|:---|
| **1 · Sombra** | D+0 a D+30 | Todos os segmentos classificados; **nenhuma ação comercial muda** | 100% da carteira classificada · corte de fronteira calibrado · zero rejeições sem motivo registrado | Nada a desfazer — nenhuma ação foi tomada |
| **2 · Piloto dirigido** | D+31 a D+90 | Ação diferenciada **apenas no segmento mais coeso**, e apenas fora da fronteira | Preço realizado ÷ anunciado capturado em ≥ 90% das vendas · nenhuma unidade de fronteira com ação automática | Suspender a ação e retomar a precificação anterior; a classificação continua em sombra |
| **3 · Operação plena** | D+91 em diante | Todos os segmentos com orçamento próprio, teto de reforma e canal | Gatilhos ativos · primeira leitura mensal de desvio publicada · métricas de negócio instrumentadas | Voltar à janela 2 |

Pré-requisitos para abrir a janela 1:

- [x] a fase 5 aprovar o modelo — aprovado, com a ressalva da silhueta;
- [ ] cada segmento ter persona, ação, teto de reforma, canal e métrica — hoje nenhum
  tem;
- [ ] a linha de base do monitoramento estar medida;
- [ ] as premissas financeiras da fase 5 estarem validadas com a área comercial.

## Monitoramento e manutenção

### O problema de monitorar um modelo sem gabarito

Num modelo supervisionado, o acompanhamento é direto: chega o resultado real e se mede o
erro. Aqui **não existe resposta certa** — ninguém vai dizer que o imóvel "era mesmo do
Segmento B". O que se acompanha, então, é a **entrada**, a **coesão** e a
**composição**.

### O plano

Os indicadores e gatilhos abaixo são a **proposta**. A linha de base de cada um ainda
precisa ser medida sobre o modelo aprovado, antes da janela 1.

| # | Indicador | Periodicidade | Gatilho | Responsável |
|:-:|:---|:---|:---|:---|
| 1 | Desvio de distribuição dos atributos (PSI) | mensal | PSI ≥ 0,25 em qualquer atributo, ou ≥ 0,1 em três | Área de Dados |
| 2 | Coesão dos segmentos (silhueta) | trimestral | queda de mais de 20% contra a linha de base, por dois trimestres seguidos | Área de Dados |
| 3 | Composição da carteira | mensal | variação ≥ 10 p.p. em qualquer segmento | Diretoria Comercial |
| 4 | Imóveis de fronteira | mensal | acima do volume que a Gerência de Ativos consegue revisar | Gerência de Ativos |
| 5 | Volume e integridade da carga | a cada carga | queda > 30% ou rejeição > 5% dos registros | Engenharia de Dados |
| 6 | Efeito da ação diferenciada | trimestral | meta não atingida em dois trimestres seguidos | Diretoria Comercial |

O indicador 6 é o que fecha o ciclo — e o que **revisa a ação, não o modelo**: o
agrupamento pode estar certo e a política, errada.

### Reciclagem

A carteira recebe imóveis novos, e a segmentação envelhece sem avisar. O 05 recomenda
reciclar **semestralmente ou a cada 10% de imóveis novos**: reajustar o agrupamento com
os dados acumulados e comparar a nova partição com a vigente.

| Resultado da comparação (índice de Rand ajustado) | Interpretação | Decisão |
|:---|:---|:---|
| ARI ≥ 0,90 | A estrutura é a mesma | Reajustar os centros e manter o catálogo |
| 0,75 ≤ ARI < 0,90 | A estrutura mudou de forma | Revisar os perfis antes de publicar |
| ARI < 0,75 | É outra segmentação | Nova varredura do 04-0 |

## As entregas

| Entrega | Consumidor | Periodicidade | Situação |
|:---|:---|:---|:---|
| Carteira classificada | Sistema comercial e Gerência de Ativos | a cada carga | disponível na aplicação |
| Classificação de um imóvel novo, antes da aquisição | Comitê de Aquisição | sob demanda | disponível na aplicação |
| Lista de imóveis para revisão humana | Gerência de Ativos | a cada carga | aguarda a calibração do corte de fronteira |
| Catálogo de segmentos, com ação, teto e métrica | Diretoria Comercial | por versão | aguarda a definição das ações |
| Painel de monitoramento de desvio | Área de Dados | mensal | aguarda a linha de base |
| Relatório final | Diretoria Comercial | por versão | [`reports/relatorio-final.md`](https://github.com/aislansf/projeto-exemplo-mercado-imobiliario/blob/main/reports/relatorio-final.md) |

## Reprodução

```bash
uv run invoke notebooks     # a fase 6 é o notebook 06
uv run invoke app           # a aplicação, em http://localhost:8501
```

| Artefato | Onde |
|:---|:---|
| Modelo vencedor | `models/selecionado.json` e o `.joblib` que ele aponta |
| Segmentos da carteira | `data/processed/segmentos.csv` |
| Avaliação | `reports/05-avaliacao.json` |
| Aplicação | `src/app/` |
| Relatório final | `reports/relatorio-final.md` |
