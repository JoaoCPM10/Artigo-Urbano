"""
Auxiliares de desenho das figuras (geometria real das ruas do OpenStreetMap).
Backend 'Agg' para funcionar sem interface grafica.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# fontes maiores para boa leitura na impressao do artigo
plt.rcParams.update(
    {
        "font.size": 13,
        "axes.titlesize": 15,
        "legend.fontsize": 12,
    }
)


def _geom_lookup(data):
    """frozenset(u,v) -> geometria (lista de pontos), na ordem u->v."""
    lut = {}
    for u, v, length, geom in data["undirected_edges"]:
        lut[(u, v)] = geom
    return lut


def draw_base(data, ax, color="#c2c7d0", lw=1.0, node_color="#9aa3b2"):
    G = data["graph"]
    segs = []
    for u, v, length, geom in data["undirected_edges"]:
        segs.extend(zip(geom, geom[1:]))
    ax.add_collection(LineCollection(segs, colors=color, linewidths=lw, zorder=1))
    xs = [c[0] for c in G.coords.values()]
    ys = [c[1] for c in G.coords.values()]
    ax.scatter(xs, ys, s=6, c=node_color, zorder=2)
    ax.set_aspect("equal")
    ax.margins(0.04)
    ax.set_xticks([])
    ax.set_yticks([])


def _edge_segments(edges, lut, G):
    """Concatena as polilinhas de uma lista de arestas (u, v, ...)."""
    segs = []
    for e in edges:
        u, v = e[0], e[1]
        g = lut.get((u, v)) or lut.get((v, u))
        if g:
            segs.extend(zip(g, g[1:]))
        else:
            segs.append((G.coords[u], G.coords[v]))
    return segs
