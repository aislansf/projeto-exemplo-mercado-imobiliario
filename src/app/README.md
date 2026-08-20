# `src/app` — a aplicação servida pelo pacote `.pkl`

Uma tela Streamlit que consome **um único artefato**: `models/aplicacao-segmentacao.pkl`.

O pacote é autocontido (`formato: meridiano.segmentacao/1`). Dentro dele viajam o
pipeline treinado, o contrato de entrada, o catálogo de linhas de produto, a carteira
já classificada, o plano de monitoramento e as evidências. A aplicação **não lê**
`data/`, `reports/` nem os demais arquivos de `models/` — copiar o `.pkl` e este
diretório para outra máquina é suficiente para a tela subir.

## Como executar

```bash
uv run invoke app-pkl
```

Ou, sem o invoke:

```bash
uv run streamlit run src/app/app.py
```

Se o pacote ainda não existir, ele é gravado na fase 6 do CRISP-DM:

```bash
uv run invoke pipeline
```

## Os dois módulos

| Arquivo | Responsabilidade |
|:--|:--|
| `pacote.py` | Abre o `.pkl`, valida o formato e classifica imóveis com o pipeline serializado. Sem Streamlit — dá para usar em script, teste ou rotina de carga. |
| `app.py` | A interface. Só apresenta o que `pacote.py` devolve. |

## As sete abas

1. **Resultado do modelo** — k, coesão, composição por unidades e por receita, confronto
   com os critérios de aceite.
2. **Classificar um imóvel** — o formulário é gerado a partir do contrato de entrada
   gravado no pacote; devolve linha de produto, faixa de confiança, distância até cada
   centroide e a ação de negócio correspondente.
3. **Linhas de produto** — a ficha de cada segmento e a assinatura que os separa.
4. **Carteira classificada** — os imóveis do treino com filtros, gráficos e download.
5. **Classificação em lote** — CSV entra, lista classificada sai.
6. **Monitoramento** — painel de indicadores, plano, gatilhos e a calibração do corte
   de fronteira.
7. **O pacote** — o `leia_me` gravado no artefato, o carimbo SHA-256 de origem e o
   espaço de atributos publicado.

## A regra que a tela respeita

A razão de fronteira é a distância ao centroide mais próximo dividida pela distância ao
segundo mais próximo. Acima de `atribuicao['corte_de_fronteira']`, o imóvel está entre
duas linhas de produto e **a ação automática não dispara** — vai para avaliação humana.
Os cortes não foram escolhidos por intuição: saíram da varredura em
`atribuicao['calibracao']`, exibida na aba de monitoramento.

## Usando `pacote.py` fora da tela

```python
from src.app import pacote as pac

modelo = pac.carregar()
imovel = {"area_habitavel": 2600, "idade_imovel": 3, "qualidade_geral": 9}
resultado = pac.classificar(imovel, modelo)
print(resultado["codigo"], resultado["confianca"], resultado["acao_automatica_liberada"])

classificados = pac.classificar_lote(entrada, modelo)  # entrada: DataFrame
```

Campos ausentes entram com a mediana da carteira de treino, declarada em
`contrato['padroes']` — e `resultado["campos_completados"]` diz quais foram.
