"""Aplicação de tela servida pelos artefatos que os notebooks gravam.

Dois módulos, com responsabilidades separadas:

* :mod:`src.app.artefatos` — lê o modelo do 04-0, a base curada, o dicionário e
  as escalas, reconstrói o pré-processamento e classifica imóveis;
* :mod:`src.app.app` — a interface Streamlit que apresenta o resultado.
"""
