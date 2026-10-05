"""Gera as figuras em INGLES referenciadas pelo relatorio_icits.tex, sem
sobrescrever as figuras em portugues (nomes proprios: fig_construction.png,
fig_urca_strong.png, fig_comparison.png). Reaproveita os dados e os helpers
neutros de idioma do visualize.py."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.collections import LineCollection

from network import load_network
from neighborhoods import NEIGHBORHOODS
import betweenness as bt
import connectivity as cc
import visualize as viz
from main import _copia_sem_aresta, _copia_sem_no, _nucleo_intacto
from compare import carrega_metricas

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

def _rede(key):
    """Rede recortada pelo poligono oficial (a mesma de main.py) do bairro."""
    return load_network(NEIGHBORHOODS[key])[0]

plt.rcParams.update({"font.size": 12})


# ---------------------------------------------------------------------------
def fig_construction():
    d = _rede("urca")
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
    axL.set_title("(a) Map: OpenStreetMap streets")

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
    axR.set_title("(b) Graph: vertices and arcs")
    axR.plot([], [], color="#4363d8", lw=2.0, label="two-way street (two arcs)")
    axR.plot([], [], color="#c0392b", lw=1.8, label="one-way street (one arc)")
    axR.legend(loc="upper right", fontsize=9, framealpha=0.95)

    # "intersection = vertex" -> nó mais ao sul, texto abaixo (zona livre)
    uann = min(inwin, key=lambda u: G.coords[u][1])
    xa, ya = G.coords[uann]
    axR.annotate("intersection = vertex", xy=(xa, ya), xytext=(xa, ya - 42),
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
        axR.annotate("street segment = arc", xy=(mx, my), xytext=(mx - 20, my - 55),
                     fontsize=9, color="#c0392b", ha="center", va="top",
                     arrowprops=dict(arrowstyle="->", color="#c0392b"))
    for ax in (axL, axR):
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.margins(0.12)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_construction.png")
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


# ---------------------------------------------------------------------------
def _urca_strong_categories():
    d = _rede("urca")
    G = d["graph"]
    edges_u = [(u, v) for (u, v, _, _) in d["undirected_edges"]]
    nodes = G.nodes()
    giant = max(cc.strongly_connected_components(G), key=len)
    gset = set(giant); gl = list(giant)
    aps = cc.articulation_points(nodes, edges_u)
    brs = cc.bridges(nodes, edges_u)
    weak_edge_pairs = {frozenset(e) for e in brs}; aps_set = set(aps)
    pares_nucleo, vistos = [], set()
    for (u, v) in edges_u:
        if u in gset and v in gset:
            k = frozenset((u, v))
            if k not in vistos:
                vistos.add(k); pares_nucleo.append((u, v))
    cbe = [(u, v) for (u, v) in pares_nucleo
           if not _nucleo_intacto(_copia_sem_aresta(G, u, v), gset)]
    cbn = [u for u in gset if not _nucleo_intacto(_copia_sem_no(G, u), gset - {u})]
    core_pairs_set = {frozenset(e) for e in cbe}
    cats = {
        "edges_both": [e for e in cbe if frozenset(e) in weak_edge_pairs],
        "edges_strong_only": [e for e in cbe if frozenset(e) not in weak_edge_pairs],
        "edges_weak_only": [e for e in brs if frozenset(e) not in core_pairs_set],
        "nodes_both": [n for n in cbn if n in aps_set],
        "nodes_strong_only": [n for n in cbn if n not in aps_set],
    }
    return d, gl, cats


def fig_urca_strong():
    d, gl, c = _urca_strong_categories()
    G = d["graph"]; lut = viz._geom_lookup(d); core_set = set(gl)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    viz.draw_base(d, ax, color="#dfe3ea")
    ax.scatter([G.coords[u][0] for u in core_set], [G.coords[u][1] for u in core_set],
               s=34, color="#9ecae1", zorder=2,
               label=f"strongly connected core ({len(core_set)} nodes)")
    if c["edges_weak_only"]:
        ax.add_collection(LineCollection(viz._edge_segments(c["edges_weak_only"], lut, G),
                          colors="#807dba", linewidths=3.0, zorder=3))
        ax.plot([], [], color="#807dba", lw=3,
                label=f"weak-only bridge, keeps core ({len(c['edges_weak_only'])})")
    if c["edges_strong_only"]:
        ax.add_collection(LineCollection(viz._edge_segments(c["edges_strong_only"], lut, G),
                          colors="#fb6a4a", linewidths=3.2, zorder=4))
        ax.plot([], [], color="#fb6a4a", lw=3,
                label=f"strong-only bridge ({len(c['edges_strong_only'])})")
    if c["edges_both"]:
        ax.add_collection(LineCollection(viz._edge_segments(c["edges_both"], lut, G),
                          colors="#a50f15", linewidths=3.6, zorder=5))
        ax.plot([], [], color="#a50f15", lw=3,
                label=f"weak and strong bridge ({len(c['edges_both'])})")
    if c["nodes_strong_only"]:
        ax.scatter([G.coords[u][0] for u in c["nodes_strong_only"]],
                   [G.coords[u][1] for u in c["nodes_strong_only"]],
                   s=85, facecolors="none", edgecolors="#ff8c00", linewidths=2.2,
                   zorder=6, label=f"strong-only articulation ({len(c['nodes_strong_only'])})")
    if c["nodes_both"]:
        ax.scatter([G.coords[u][0] for u in c["nodes_both"]],
                   [G.coords[u][1] for u in c["nodes_both"]],
                   s=85, facecolors="#ff8c00", edgecolors="#7a3d00", linewidths=1.6,
                   zorder=7, label=f"weak and strong articulation ({len(c['nodes_both'])})")
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    ax.set_title("Directed structural bottlenecks (Urca)\n"
                 f"(elements that fragment the strongly connected core of {len(core_set)} intersections)")
    fig.tight_layout()
    p = os.path.join(OUT, "fig_urca_strong.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    print("saved:", p)


# ---------------------------------------------------------------------------
def fig_comparison():
    dados = carrega_metricas()
    def pct(n, dd): return 100.0 * n / dd if dd else 0.0
    labels = ["One-way\n(% segments)", "Outside core\n(% of V)",
              "Strong bridges\n(% core streets)", "Strong artic.\n(% of core)"]
    def series(m):
        duplas = m["rede"]["E_arcos"] - m["rede"]["trechos"]
        gd = m["gargalos_estruturais_dirigidos"]
        return [pct(m["rede"]["trechos"] - duplas, m["rede"]["trechos"]),
                pct(m["conectividade"]["fora_da_scc_gigante"], m["rede"]["V_intersecoes"]),
                pct(gd["pontes_fortes"], gd.get("pares_nucleo")),
                pct(gd["articulacoes_fortes"], gd["nucleo_n"])]
    bairros = [nome for nome, _ in dados]
    vals = [series(m) for _, m in dados]
    x = list(range(len(labels))); n_b = len(bairros); w = 0.8 / max(n_b, 1)
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for j, nome in enumerate(bairros):
        pos = [xi + (j - (n_b - 1) / 2) * w for xi in x]
        ax.bar(pos, vals[j], w, label=nome, color=cmap(j % 10))
        for p, v in zip(pos, vals[j]):
            ax.text(p, v + 0.7, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("% (normalised)")
    ax.set_title("Normalised structural indicators per neighbourhood")
    ax.legend(loc="upper right", framealpha=0.9); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_comparison.png")
    fig.savefig(p, dpi=140); plt.close(fig)
    print("saved:", p)


def _draw_network(ax, d, title):
    """Rede de um bairro: mão única (escuro) x mão dupla (laranja)."""
    G = d["graph"]
    arcset = {(e.u, e.v) for e in G.edges}
    one_segs, two_segs = [], []
    for (u, v, length, geom) in d["undirected_edges"]:
        fwd = (u, v) in arcset; bwd = (v, u) in arcset
        pts = list(zip(geom, geom[1:]))
        (two_segs if (fwd and bwd) else one_segs).extend(pts)
    ax.add_collection(LineCollection(one_segs, colors="#4a5a78", linewidths=0.8,
                                     zorder=2, alpha=0.85))
    ax.add_collection(LineCollection(two_segs, colors="#e6752f", linewidths=1.8,
                                     zorder=3))
    xs = [c[0] for c in G.coords.values()]; ys = [c[1] for c in G.coords.values()]
    ax.scatter(xs, ys, s=3, c="#9aa3b2", zorder=4)
    ax.set_aspect("equal"); ax.margins(0.04)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=12)


def fig_networks():
    keys = ["urca", "copacabana", "botafogo"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.0))
    for ax, key in zip(axes, keys):
        cfg = NEIGHBORHOODS[key]
        d = _rede(key)
        G = d["graph"]
        title = f"{cfg.display_name}\n{G.n} intersections, {len(d['undirected_edges'])} segments"
        _draw_network(ax, d, title)
    # legenda única
    axes[0].plot([], [], color="#4a5a78", lw=1.5, label="one-way")
    axes[0].plot([], [], color="#e6752f", lw=2.5, label="two-way")
    axes[0].legend(loc="upper left", fontsize=9, framealpha=0.9)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_networks.png")
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


def fig_betweenness():
    """Intermediacao dirigida (tempo minimo, nucleo forte) nos tres bairros."""
    keys = ["urca", "copacabana", "botafogo"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    vmax = 0.0
    dados = []
    for key in keys:
        d = _rede(key)
        G = d["graph"]
        core = set(max(cc.strongly_connected_components(G), key=len))
        bc = bt.betweenness(G, core)
        dados.append((key, d, core, bc))
        vmax = max(vmax, max(bc.values()))
    sc = None
    for ax, (key, d, core, bc) in zip(axes, dados):
        G = d["graph"]
        viz.draw_base(d, ax, color="#dfe3ea")
        us = sorted(core, key=lambda u: bc[u])           # maiores por cima
        v = [bc[u] for u in us]
        sc = ax.scatter([G.coords[u][0] for u in us], [G.coords[u][1] for u in us],
                        c=v, cmap="Reds", vmin=0, vmax=vmax,
                        s=[8 + 260 * x / vmax for x in v],
                        edgecolors="#333333", linewidths=0.3, zorder=3)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{NEIGHBORHOODS[key].display_name}\n"
                     f"max = {100 * max(v):.1f}% of pairs", fontsize=12)
    fig.subplots_adjust(right=0.9)
    cax = fig.add_axes([0.92, 0.12, 0.012, 0.75])
    fig.colorbar(sc, cax=cax, label="betweenness centrality (fraction of core pairs)")
    p = os.path.join(OUT, "fig_betweenness.png")
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    fig_construction()
    fig_urca_strong()
    fig_comparison()
    fig_networks()
    fig_betweenness()
