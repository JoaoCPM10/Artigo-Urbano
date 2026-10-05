"""Gera a figura didatica da conversao mapa -> grafo (ponto 6)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from osm_loader import load_neighborhood

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
plt.rcParams.update({"font.size": 12})

d = load_neighborhood("urca", "-22.958,-43.171,-22.943,-43.155")
G = d["graph"]
arcset = {(e.u, e.v) for e in G.edges}

# janela de recorte
X0, X1, Y0, Y1 = 270, 460, 410, 590
inwin = {u for u, (x, y) in G.coords.items() if X0 <= x <= X1 and Y0 <= y <= Y1}
edges = [(u, v, geom) for (u, v, length, geom) in d["undirected_edges"]
         if u in inwin and v in inwin]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 5.2))

# ---- painel esquerdo: "mapa" (geometria das ruas) ----
for (u, v, geom) in edges:
    xs = [p[0] for p in geom]; ys = [p[1] for p in geom]
    axL.plot(xs, ys, "-", color="#6b7785", lw=1.8)
for u in inwin:
    x, y = G.coords[u]
    axL.plot(x, y, ".", color="#9aa3b2", ms=6)
axL.set_title("(a) Mapa: ruas do OpenStreetMap")

# ---- painel direito: "grafo" (vertices e arcos orientados) ----
for (u, v, geom) in edges:
    (x1, y1), (x2, y2) = G.coords[u], G.coords[v]
    two_way = (u, v) in arcset and (v, u) in arcset
    if two_way:
        axR.plot([x1, x2], [y1, y2], "-", color="#4363d8", lw=2.0, zorder=1)
    else:
        a, b = (u, v) if (u, v) in arcset else (v, u)
        (xa, ya), (xb, yb) = G.coords[a], G.coords[b]
        axR.add_patch(FancyArrowPatch(
            (xa, ya), (xb, yb), arrowstyle="-|>", mutation_scale=14,
            color="#c0392b", lw=1.8, shrinkA=7, shrinkB=7, zorder=1))
for u in inwin:
    x, y = G.coords[u]
    axR.plot(x, y, "o", color="#1a2a44", ms=9, zorder=2)
axR.set_title("(b) Grafo: vértices e arcos")

# legenda de sentido no painel direito
axR.plot([], [], color="#4363d8", lw=2.0, label="rua de mão dupla (dois arcos)")
axR.plot([], [], color="#c0392b", lw=1.8, label="rua de mão única (um arco)")
axR.legend(loc="upper left", fontsize=9, framealpha=0.9)

# anotacao do vertice: nó mais ao sul (longe do título), texto deslocado p/ baixo
uann = min(inwin, key=lambda u: G.coords[u][1])
xa, ya = G.coords[uann]
axR.annotate("interseção = vértice", xy=(xa, ya), xytext=(xa + 8, ya - 34),
             fontsize=9, color="#1a2a44", ha="center",
             arrowprops=dict(arrowstyle="->", color="#1a2a44"))
# anotacao do arco: aponta para uma rua de mão única (vermelha) da janela
oneway_edges = [(u, v) for (u, v, g) in edges
                if not ((u, v) in arcset and (v, u) in arcset)]
if oneway_edges:
    u0, v0 = oneway_edges[0]
    mx = (G.coords[u0][0] + G.coords[v0][0]) / 2
    my = (G.coords[u0][1] + G.coords[v0][1]) / 2
    axR.annotate("trecho de rua = arco", xy=(mx, my), xytext=(mx + 55, my + 18),
                 fontsize=9, color="#c0392b", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#c0392b"))

for ax in (axL, axR):
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.margins(0.12)

fig.tight_layout()
path = os.path.join(OUT, "08_construcao_grafo.png")
fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
print("salvo:", path, "| edges na janela:", len(edges), "| nós:", len(inwin))
