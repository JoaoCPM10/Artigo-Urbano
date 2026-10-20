"""
Figura da conectividade externa (Secao 4.6 do artigo): para cada bairro, a rede
ampliada em R = 1 km com o nucleo de origem, os destinos externos, o corte
minimo mais proximo da origem, o mais proximo do destino e as ruas externas
cujo fechamento sozinho reduz o fluxo.

Usa os dados ja baixados (cache de data/); recalcula so' R = 1 km.
Escreve output/fig_externa.png (e a copia em ../Figures/).
Uso:  py fig_conectividade_externa.py
"""

from __future__ import annotations
import math
import os
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

import conectividade_externa as ce
import polygons as pg
import visualize as viz
from neighborhoods import NEIGHBORHOODS

OUT = ce.OUT
RAIO_M = 1000
COR = {"origem": "#c0392b", "destino": "#6b46c1", "externa": "#e67e22"}


def _poligono_xy(big, feature):
    """Aneis do poligono oficial na mesma projecao (metros) da rede."""
    kx = math.cos(math.radians(big["lat0"])) * 111320.0
    ky = 110540.0
    return [[((lo - big["lon0"]) * kx, (la - big["lat0"]) * ky) for lo, la in ring]
            for ring in pg._rings(feature)]


def painel(ax, key, res, obj):
    cfg = NEIGHBORHOODS[key]
    big, rede = obj["big"], obj["rede"]
    G = big["graph"]
    lut = viz._geom_lookup(big)
    ring = rede.ring
    dentro = [(u, v, l, g) for (u, v, l, g) in big["undirected_edges"] if u in ring and v in ring]
    ax.add_collection(LineCollection([s for (_, _, _, g) in dentro for s in zip(g, g[1:])],
                                     colors="#d5dae3", linewidths=0.8, zorder=1))
    for anel in _poligono_xy(big, pg.fetch_bairro_polygon(cfg.display_name)):
        xs, ys = zip(*anel)
        ax.plot(xs, ys, color="#2d3748", lw=1.3, ls="--", zorder=3)
    ax.add_collection(LineCollection(viz._edge_segments(obj["corte_destino"], lut, G),
                                     colors=COR["destino"], linewidths=3.0, zorder=5))
    ax.add_collection(LineCollection(viz._edge_segments(obj["corte_origem"], lut, G),
                                     colors=COR["origem"], linewidths=3.0, zorder=6))
    ext = [(u, v) for (u, v, _) in obj["criticas"]["externo"]]
    ax.add_collection(LineCollection(viz._edge_segments(ext, lut, G),
                                     colors=COR["externa"], linewidths=3.0, zorder=7))
    src = rede.src
    ax.scatter([G.coords[u][0] for u in src], [G.coords[u][1] for u in src],
               s=14, color="#2b6cb0", zorder=4)
    dst = obj["dest"]
    ax.scatter([G.coords[g][0] for g in dst], [G.coords[g][1] for g in dst], s=46,
               marker="^", color="#2f855a", edgecolors="#1c4532", linewidths=0.6, zorder=8)
    ax.set_aspect("equal"); ax.margins(0.03)
    ax.set_xticks([]); ax.set_yticks([])
    it = res["raios"][str(RAIO_M)]
    f0 = res["raios"]["0"]["fluxo"]["qualquer"]["ruas_dir"]
    ax.set_title(f"{cfg.display_name}: directed flow {f0} at the boundary,\n"
                 f"{it['fluxo']['scc']['ruas_dir']} at the 1 km outer edge", fontsize=11)


def main():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.8))
    for ax, key in zip(axes, ("urca", "copacabana", "botafogo")):
        res, obj = ce.analisa_bairro(key, raios=(0, RAIO_M))
        painel(ax, key, res, obj[RAIO_M])
    handles = [
        plt.Line2D([], [], marker="o", ls="", color="#2b6cb0", label="source region (core)"),
        plt.Line2D([], [], marker="^", ls="", color="#2f855a", markeredgecolor="#1c4532",
                   markersize=8, label="external destinations"),
        plt.Line2D([], [], color=COR["origem"], lw=3, label="minimum cut nearest the core"),
        plt.Line2D([], [], color=COR["destino"], lw=3, label="minimum cut nearest the destinations"),
        plt.Line2D([], [], color=COR["externa"], lw=3, label="external streets whose closure lowers the flow"),
        plt.Line2D([], [], color="#2d3748", lw=1.3, ls="--", label="official boundary"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    p = os.path.join(OUT, "fig_externa.png")
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    figs = os.path.join(os.path.dirname(OUT), "..", "Figures")
    if os.path.isdir(figs):
        shutil.copy(p, os.path.join(figs, "fig_externa.png"))
    print("saved:", p)


if __name__ == "__main__":
    main()
