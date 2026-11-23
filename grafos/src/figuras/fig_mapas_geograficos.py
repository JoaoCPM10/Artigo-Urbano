"""
m6: versoes dos mapas do artigo com agua, encosta e escala (nao substituem as
figuras atuais; a troca e' feita na integracao dos nove bairros).

  fig_networks.png : as redes dos nove bairros (mao unica em escuro, mao dupla
                         em laranja) sobre relevo, encosta e agua;
  fig_cut.png      : onde esta o corte de acesso nos bairros de rota unica
                         (Urca e Leme), sobre o mesmo contexto.

Uso:  python -m figuras.fig_mapas_geograficos [redes|corte|todas]
"""

from __future__ import annotations
from figuras.rotulos import t as _t, num as _num
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from analises import localiza_corte as lc
from figuras import mapa_contexto as mc
from figuras import visualize as viz
from nucleo.neighborhoods import NEIGHBORHOODS
from nucleo.network import load_network
from caminhos import OUT

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
        ax.set_title(f"{cfg.display_name}: {d['graph'].n} " + _t("intersections", "interseções"), fontsize=12)
        mc.barra_escala(ax)
        mc.seta_norte(ax)
        print(key, "ok", round(info["passo"]), "m", flush=True)
    h = mc.handles_contexto()
    h += [plt.Line2D([], [], color="#26324d", lw=2, label=_t("one-way", "mão única")),
          plt.Line2D([], [], color="#e6752f", lw=2.5, label=_t("two-way", "mão dupla"))]
    fig.legend(handles=h, loc="lower center", ncol=6, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(OUT, "fig_networks.png")
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
                                         linewidths=3.6, zorder=9))
        # pontas das ruas de corte e comprimento de cada uma: ruas vizinhas (como duas
        # das tres da Urca) se desenham como uma curva so, e a marca mostra onde uma termina
        pontas = {n for e in cortes for n in e[:2]}
        ax.scatter([G.coords[n][0] for n in pontas], [G.coords[n][1] for n in pontas], s=22,
                   facecolor="white", edgecolor="#c0392b", linewidths=1.2, zorder=10)
        desloc = [(-50, -26), (28, -28), (28, 28)]
        for i, e in enumerate(cortes):
            if len(e) < 3:
                continue
            mx = (G.coords[e[0]][0] + G.coords[e[1]][0]) / 2
            my = (G.coords[e[0]][1] + G.coords[e[1]][1]) / 2
            ax.annotate(f"{round(e[2])} m", xy=(mx, my), xytext=desloc[i % 3], textcoords="offset points",
                        fontsize=9, color="#7b1e17", fontweight="bold", zorder=11,
                        bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.2),
                        arrowprops=dict(arrowstyle="-", color="#7b1e17", lw=0.8))
        ax.scatter([G.coords[u][0] for u in src], [G.coords[u][1] for u in src], s=26, color="#2b6cb0", zorder=5)
        ax.scatter([G.coords[g][0] for g in gw], [G.coords[g][1] for g in gw], s=60, marker="^",
                   color="#2f855a", edgecolors="#1c4532", linewidths=0.6, zorder=7)
        n = len(um_corte) if um_corte else len(ek_cut)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{cfg.display_name}: " + _t(f"access flow {r['fluxo']} ({n} single-street cut{'s' if n != 1 else ''})",
                                       f"fluxo de acesso {r['fluxo']} ({n} corte{'s' if n != 1 else ''} de uma rua)"), fontsize=12)
        mc.barra_escala(ax)
        mc.seta_norte(ax)
    h = mc.handles_contexto() + [
        plt.Line2D([], [], marker="o", ls="", color="#2b6cb0", label=_t("source region", "região de origem")),
        plt.Line2D([], [], marker="^", ls="", color="#2f855a", markeredgecolor="#1c4532", markersize=8, label=_t("gateways", "portas")),
        plt.Line2D([], [], color="#c0392b", lw=3.6, label=_t("cut streets", "ruas de corte"))]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    p = os.path.join(OUT, "fig_cut.png")
    fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "todas"
    if modo in ("corte", "todas"):
        fig_corte()
    if modo in ("redes", "todas"):
        fig_redes()
