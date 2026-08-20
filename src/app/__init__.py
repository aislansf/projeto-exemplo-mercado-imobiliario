"""Aplicação de tela servida pelo pacote publicado em ``.pkl``.

Dois módulos, com responsabilidades separadas:

* :mod:`src.app.pacote` — abre ``models/aplicacao-segmentacao.pkl``, valida o
  formato e classifica imóveis com o pipeline serializado;
* :mod:`src.app.app` — a interface Streamlit que apresenta o resultado.

O pacote é autocontido: nenhum outro artefato do repositório é lido em tempo de
execução.
"""
