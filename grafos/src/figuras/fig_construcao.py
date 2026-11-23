"""
Figura 1 do artigo: do mapa ao grafo dirigido, em um trecho da grade nordeste da
Urca (interseccoes viram vertices, trechos de rua viram arcos).

Escreve output/fig_construction.png.   Uso:  python -m figuras.fig_construcao
"""

from __future__ import annotations
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

from nucleo.network import load_network
from nucleo.neighborhoods import NEIGHBORHOODS
from figuras.rotulos import t as _t
from caminhos import OUT


# mesmas fontes do restante das figuras do artigo (visualize.py)
plt.rcParams.update({"font.size": 12, "axes.titlesize": 15})


def main():
    d = load_network(NEIGHBORHOODS["urca"])[0]
    G = d["graph"]
    arcset = {(e.u, e.v) for e in G.edges}
    # janela (lat/lon): grade NE + ruas de mão dupla. Definida em graus, e não
    # em metros projetados, porque a origem da projeção depende da rede.
    LAT0, LAT1, LON0, LON1 = -22.94563, -22.94333, -43.16174, -43.15886
    inwin = {u for u, (la, lo) in d["latlon"].items()
             if LAT0 <= la <= LAT1 and LON0 <= lo <= LON1}
    edges = [(u, v, geom) for (u, v, length, geom) in d["undirected_edges"]
             if u in inwin and v in inwin]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 5.2))
    for (u, v, geom) in edges:
        xs = [p[0] for p in geom]; ys = [p[1] for p in geom]
        axL.plot(xs, ys, "-", color="#6b7785", lw=1.8)
    for u in inwin:
        x, y = G.coords[u]; axL.plot(x, y, ".", color="#9aa3b2", ms=6)
    axL.set_title(_t("(a) Map: OpenStreetMap streets", "(a) Mapa: ruas do OpenStreetMap"))

    for (u, v, geom) in edges:
        (x1, y1), (x2, y2) = G.coords[u], G.coords[v]
        two_way = (u, v) in arcset and (v, u) in arcset
        if two_way:
            axR.plot([x1, x2], [y1, y2], "-", color="#4363d8", lw=2.0, zorder=1)
        else:
            a, b = (u, v) if (u, v) in arcset else (v, u)
            (xa, ya), (xb, yb) = G.coords[a], G.coords[b]
            axR.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>",
                          mutation_scale=14, color="#c0392b", lw=1.8,
                          shrinkA=7, shrinkB=7, zorder=1))
    for u in inwin:
        x, y = G.coords[u]; axR.plot(x, y, "o", color="#1a2a44", ms=9, zorder=2)
    axR.set_title(_t("(b) Graph: vertices and arcs", "(b) Grafo: vértices e arcos"))
    axR.plot([], [], color="#4363d8", lw=2.0, label=_t("two-way street (two arcs)", "rua de mão dupla (dois arcos)"))
    axR.plot([], [], color="#c0392b", lw=1.8, label=_t("one-way street (one arc)", "rua de mão única (um arco)"))
    axR.legend(loc="upper right", fontsize=9, framealpha=0.95)

    # "intersection = vertex" -> nó mais ao sul, texto abaixo (zona livre)
    uann = min(inwin, key=lambda u: G.coords[u][1])
    xa, ya = G.coords[uann]
    axR.annotate(_t("intersection = vertex", "interseção = vértice"), xy=(xa, ya), xytext=(xa, ya - 42),
                 fontsize=9, color="#1a2a44", ha="center", va="top",
                 arrowprops=dict(arrowstyle="->", color="#1a2a44"))
    # "street segment = arc" -> aresta de mão única mais à esquerda, texto à
    # esquerda (a legenda fica no canto superior direito, sem colisão)
    oneway_edges = [(u, v) for (u, v, g) in edges
                    if not ((u, v) in arcset and (v, u) in arcset)]
    if oneway_edges:
        u0, v0 = min(oneway_edges,
                     key=lambda uv: (G.coords[uv[0]][0] + G.coords[uv[1]][0]) / 2)
        mx = (G.coords[u0][0] + G.coords[v0][0]) / 2
        my = (G.coords[u0][1] + G.coords[v0][1]) / 2
        axR.annotate(_t("street segment = arc", "trecho de rua = arco"), xy=(mx, my), xytext=(mx - 20, my - 55),
                     fontsize=9, color="#c0392b", ha="center", va="top",
                     arrowprops=dict(arrowstyle="->", color="#c0392b"))
    for ax in (axL, axR):
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.margins(0.12)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_construction.png")
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    main()
