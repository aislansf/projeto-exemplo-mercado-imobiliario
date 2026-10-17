# `src/app` — a aplicação servida pelos artefatos dos notebooks

Uma tela Streamlit que lê o que os notebooks gravam em disco. Ela não treina nada:
o modelo é o vencedor do 04-0, e o pré-processador é reconstruído a partir da base
curada, do dicionário e das escalas, como no notebook 06. Ao subir, a tela confere se
esse pré-processador reproduz a saída do 03 e se o modelo relido reproduz os segmentos
gravados.

## Como executar

```bash
uv run invoke app
```

Ou, sem o invoke:

```bash
uv run streamlit run src/app/app.py
```

Se algum arquivo obrigatório ainda não existir, a tela diz qual é e qual notebook o
grava. Para gerar todos:

```bash
uv run invoke notebooks
```

## O que a tela lê

| Arquivo | Notebook | Obrigatório |
|:--|:--:|:--:|
| `models/selecionado.json` e o `.joblib` que ele aponta | 04-0 | sim |
| `data/processed/segmentos.csv` | 04-0 | sim |
| `data/processed/ames_housing_tratado.csv` | 02 | sim |
| `data/processed/dicionario.csv` e `escala.csv` | 00 | sim |
| `data/processed/ames_housing_preprocessed.csv` | 03 | sim — só para conferência |
| `data/processed/ames_housing_pca.csv` e `ames_housing_umap.csv` | 04-2 | não |
| `data/processed/regras_associacao.csv` | 04-3 | não |
| `reports/05-avaliacao.json` | 05 | não |

A tela relê os arquivos sozinha quando um notebook os regrava: o cache usa a data de
modificação de cada um.

## Os dois módulos

| Arquivo | Responsabilidade |
|:--|:--|
| `artefatos.py` | Lê os arquivos, reconstrói o espaço do modelo e classifica imóveis. Sem Streamlit — dá para usar em script, teste ou rotina de carga. |
| `app.py` | A interface. Só apresenta o que `artefatos.py` devolve. |

## As sete abas

1. **Resultado do modelo**: segmentos, participação em imóveis e em valor de venda,
   preço por segmento e, quando o 05 já rodou, os critérios de sucesso e os cenários
   financeiros.
2. **Classificar um imóvel**: o usuário preenche o que souber e o restante vem do imóvel
   mais parecido da carteira. A tela devolve o segmento, a distância até cada um, a
   razão de fronteira e o vizinho usado.
3. **Perfil dos segmentos**: retrato de cada segmento, a assinatura que os separa e a
   carteira projetada em duas dimensões (UMAP ou PCA do 04-2).
4. **Carteira classificada**: os imóveis da base curada com o segmento gravado, com
   filtros, gráficos e download.
5. **Classificação em lote**: entra um CSV, sai a lista classificada. Uma linha com erro
   não derruba o lote.
6. **Regras de associação**: as regras do 04-3, com filtros por lift, confiança e item.
7. **Procedência**: quais arquivos foram lidos, quando foram gravados e o resultado das
   duas conferências.

## Razão de fronteira

É a distância ao centro do segmento atribuído dividida pela distância ao segundo mais
próximo. Perto de 1, o imóvel está entre dois segmentos e a leitura pede revisão
humana. A tela mostra a razão e a posição dela na carteira. Os notebooks atuais não
calibram nenhum corte, então a tela também não aplica um.

## Usando `artefatos.py` fora da tela

```python
from src.app import artefatos as art

artefatos = art.carregar()
resultado = art.classificar(artefatos, {"area_habitavel": 2400, "qualidade_geral": 8})
print(resultado["segmento"], resultado["razao_de_fronteira"], resultado["completados"])

classificados = art.classificar_lote(artefatos, entrada)  # entrada: DataFrame
```
