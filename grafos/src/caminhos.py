"""
Caminhos do projeto, ancorados neste arquivo (grafos/src/caminhos.py).

    ROOT    grafos/
    DATA    grafos/data      (caches do OSM, poligonos, dados do IBGE)
    OUT     grafos/output    (resultados e figuras geradas)
    FIGURES Figures/         (figuras usadas pelo artigo, na raiz do repositorio)
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
FIGURES = os.path.join(os.path.dirname(ROOT), "Figures")
