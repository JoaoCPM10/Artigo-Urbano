"""
Painel de um bairro da figura de conectividade externa (Secao 4.5 do artigo): a
rede ampliada em R = 1 km com o nucleo de origem, os destinos externos, o corte
minimo mais proximo da origem, o mais proximo do destino e as ruas externas
cujo fechamento sozinho reduz o fluxo. Modulo de apoio de fig_externa_geo.py.
"""

from __future__ import annotations

import math

import matplotlib

from figuras.rotulos import t as _t

matplotlib.use("Agg")
from matplotlib.collections import LineCollection

from figuras import visualize as viz
from nucleo import polygons as pg
from nucleo.neighborhoods import NEIGHBORHOODS

RAIO_M = 1000
COR = {"origem": "#c0392b", "destino": "#6b46c1", "externa": "#e67e22"}


def _poligono_xy(big, feature):
    """Aneis do poligono oficial na mesma projecao (metros) da rede."""
    kx = math.cos(math.radians(big["lat0"])) * 111320.0
    ky = 110540.0
    return [
        [((lo - big["lon0"]) * kx, (la - big["lat0"]) * ky) for lo, la in ring]
        for ring in pg._rings(feature)
    ]


def painel(ax, key, res, obj):
    cfg = NEIGHBORHOODS[key]
    big, rede = obj["big"], obj["rede"]
    G = big["graph"]
    lut = viz._geom_lookup(big)
    ring = rede.ring
    dentro = [(u, v, l, g) for (u, v, l, g) in big["undirected_edges"] if u in ring and v in ring]
    ax.add_collection(
        LineCollection(
            [s for (_, _, _, g) in dentro for s in zip(g, g[1:])],
            colors="#d5dae3",
            linewidths=0.8,
            zorder=1,
        )
    )
    for anel in _poligono_xy(big, pg.fetch_bairro_polygon(cfg.display_name)):
        xs, ys = zip(*anel)
        ax.plot(xs, ys, color="#2d3748", lw=1.3, ls="--", zorder=3)
    ax.add_collection(
        LineCollection(
            viz._edge_segments(obj["corte_destino"], lut, G),
            colors=COR["destino"],
            linewidths=3.0,
            zorder=5,
        )
    )
    ax.add_collection(
        LineCollection(
            viz._edge_segments(obj["corte_origem"], lut, G),
            colors=COR["origem"],
            linewidths=3.0,
            zorder=6,
        )
    )
    ext = [(u, v) for (u, v, _) in obj["criticas"]["externo"]]
    ax.add_collection(
        LineCollection(
            viz._edge_segments(ext, lut, G), colors=COR["externa"], linewidths=3.0, zorder=7
        )
    )
    src = rede.src
    ax.scatter(
        [G.coords[u][0] for u in src],
        [G.coords[u][1] for u in src],
        s=14,
        color="#2b6cb0",
        zorder=4,
    )
    dst = obj["dest"]
    ax.scatter(
        [G.coords[g][0] for g in dst],
        [G.coords[g][1] for g in dst],
        s=46,
        marker="^",
        color="#2f855a",
        edgecolors="#1c4532",
        linewidths=0.6,
        zorder=8,
    )
    ax.set_aspect("equal")
    ax.margins(0.03)
    ax.set_xticks([])
    ax.set_yticks([])
    it = res["raios"][str(RAIO_M)]
    f0 = res["raios"]["0"]["fluxo"]["qualquer"]["ruas_dir"]
    ax.set_title(
        f"{cfg.display_name}: "
        + _t(
            f"directed flow {f0} at the boundary,\n"
            f"{it['fluxo']['scc']['ruas_dir']} at the 1 km outer edge",
            f"fluxo dirigido {f0} na fronteira,\n"
            f"{it['fluxo']['scc']['ruas_dir']} na borda externa a 1 km",
        ),
        fontsize=11,
    )
