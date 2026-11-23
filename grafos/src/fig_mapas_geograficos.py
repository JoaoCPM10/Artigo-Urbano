"""
m6: versoes dos mapas do artigo com agua, encosta e escala (nao substituem as
figuras atuais; a troca e' feita na integracao dos nove bairros).

  fig_networks_geo.png : as redes dos nove bairros (mao unica em escuro, mao dupla
                         em laranja) sobre relevo, encosta e agua;
  fig_cut_geo.png      : onde esta o corte de acesso nos bairros de rota unica
                         (Urca e Leme), sobre o mesmo contexto.

Uso:  py fig_mapas_geograficos.py [redes|corte|todas]
"""

from __future__ import annotations
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

import localiza_corte as lc
import mapa_contexto as mc
import visualize as viz
from neighborhoods import NEIGHBORHOODS
from network import load_network

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
ORDEM = ["urca", "leme", "joa", "alto_da_boa_vista", "praca_da_bandeira", "cosme_velho",
         "sao_conrado", "botafogo", "copacabana"]


def desenha_rede(ax, d):
    G = d["graph"]
    arcset = {(e.u, e.v) for e in G.edges}
    um, dois = [], []
    for (u, v, length, geom) in d["undirected_edges"]:
        fwd, bwd = (u, v) in arcset, (v, u) in arcset
        (dois if (fwd and bwd) else um).extend(zip(geom, geom[1:]))
    ax.add_collection(LineCollection(um, colors="#26324d", linewidths=0.9, zorder=3, alpha=0.95))
    ax.add_collection(LineCollection(dois, colors="#e6752f", linewidths=1.8, zorder=4))


def fig_redes():
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    for ax, key in zip(axes.ravel(), ORDEM):
        cfg = NEIGHBORHOODS[key]
        d, _ = load_network(cfg)
        info = mc.desenha_contexto(ax, key, d)
        desenha_rede(ax, d)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{cfg.display_name}: {d['graph'].n} intersections", fontsize=12)
        mc.barra_escala(ax)
        mc.seta_norte(ax)
        print(key, "ok", round(info["passo"]), "m", flush=True)
    h = mc.handles_contexto()
    h += [plt.Line2D([], [], color="#26324d", lw=2, label="one-way"),
          plt.Line2D([], [], color="#e6752f", lw=2.5, label="two-way")]
    fig.legend(handles=h, loc="lower center", ncol=6, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(OUT, "fig_networks_geo.png")
    fig.savefig(p, dpi=110, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


def fig_corte():
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
    for ax, key in zip(axes, ("urca", "leme")):
        cfg = NEIGHBORHOODS[key]
        r = lc.analisa(key)
        data, src, gw, um_corte, ek_cut = r["_objs"]
        mc.desenha_contexto(ax, key, data)
        G = data["graph"]
        lut = viz._geom_lookup(data)
        ax.add_collection(LineCollection(
            [s for (u, v, length, geom) in data["undirected_edges"] for s in zip(geom, geom[1:])],
            colors="#8a93a5", linewidths=0.9, zorder=2))
        cortes = um_corte if um_corte else [(u, v) for (u, v) in ek_cut]
        ax.add_collection(LineCollection(viz._edge_segments(cortes, lut, G), colors="#c0392b",
                                         linewidths=3.6, zorder=6))
        ax.scatter([G.coords[u][0] for u in src], [G.coords[u][1] for u in src], s=26, color="#2b6cb0", zorder=5)
        ax.scatter([G.coords[g][0] for g in gw], [G.coords[g][1] for g in gw], s=60, marker="^",
                   color="#2f855a", edgecolors="#1c4532", linewidths=0.6, zorder=7)
        n = len(um_corte) if um_corte else len(ek_cut)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{cfg.display_name}: access flow {r['fluxo']} ({n} single-street cut{'s' if n != 1 else ''})", fontsize=12)
        mc.barra_escala(ax)
        mc.seta_norte(ax)
    h = mc.handles_contexto() + [
        plt.Line2D([], [], marker="o", ls="", color="#2b6cb0", label="source region"),
        plt.Line2D([], [], marker="^", ls="", color="#2f855a", markeredgecolor="#1c4532", markersize=8, label="gateways"),
        plt.Line2D([], [], color="#c0392b", lw=3.6, label="cut streets")]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    p = os.path.join(OUT, "fig_cut_geo.png")
    fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "todas"
    if modo in ("corte", "todas"):
        fig_corte()
    if modo in ("redes", "todas"):
        fig_redes()
