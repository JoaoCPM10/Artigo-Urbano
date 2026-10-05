"""
ONDE esta o corte do fluxo de acesso? (Secao 4.3 do artigo)

O fluxo de acesso da Urca vale 1. Isso e' o istmo do bairro ou uma ponte local
perto da regiao de origem (o artefato do corte no-a-no, Secao 4.2)? Aqui:

  - o corte que o Edmonds-Karp devolve (e' o mais PROXIMO DA ORIGEM, por
    construcao) e quantos nos ficam do lado da origem;
  - TODAS as ruas cujo fechamento sozinho separa a regiao de origem de todas as
    portas (cortes de uma rua), com comprimento, posicao e tamanho dos lados;
  - quais interseccoes extremas desses cortes coincidem com as de maior
    intermediacao (betweenness.py);
  - a mesma enumeracao para f de 0,05 a 0,50 (so' Urca).

Escreve output/localizacao_corte.json e output/fig_cut.png.
Uso:  py localiza_corte.py
"""

from __future__ import annotations
import json
import os
from collections import deque

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

import betweenness as bt
import connectivity as cc
import maxflow as mf
import visualize as viz
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
FRACOES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)


def _alcanca(adj, inicio, sem_aresta):
    """Nos alcancaveis a partir de `inicio` sem usar a rua de indice `sem_aresta`."""
    visto, fila = set(inicio), deque(inicio)
    while fila:
        u = fila.popleft()
        for v, i in adj[u]:
            if i != sem_aresta and v not in visto:
                visto.add(v); fila.append(v)
    return visto


def cortes_de_uma_rua(edges_in, adj, src, gw):
    """[(indice da rua, nos do lado da origem)] das ruas que sozinhas separam
    toda a regiao de origem de todas as portas. Ruas paralelas (capacidade 2)
    nunca sao corte de 1."""
    out = []
    for i, e in enumerate(edges_in):
        if sum(1 for f in edges_in if {f[0], f[1]} == {e[0], e[1]}) > 1:
            continue
        lado = _alcanca(adj, src, i)
        if not (lado & gw):
            out.append((i, lado))
    return out


def analisa(key: str) -> dict:
    cfg = NEIGHBORHOODS[key]
    data, bbox = load_network(cfg)
    G = data["graph"]
    edges_u = [(e[0], e[1]) for e in data["undirected_edges"]]
    uset = set(max(cc.connected_components(G.nodes(), edges_u), key=len))
    gw = gateway_nodes(cfg, data, bbox, uset)
    edges_in = [e for e in data["undirected_edges"] if e[0] in uset and e[1] in uset]
    adj = {u: [] for u in uset}
    for i, e in enumerate(edges_in):
        adj[e[0]].append((e[1], i)); adj[e[1]].append((e[0], i))
    ll = data["latlon"]

    def coords(n):
        return [round(ll[n][0], 5), round(ll[n][1], 5)]

    acc = mf.gateway_access_flow(list(uset), data["undirected_edges"], gw, frac=0.2, details=True)
    src = set(acc["origem"])
    cuts = cortes_de_uma_rua(edges_in, adj, src, gw)

    core = set(max(cc.strongly_connected_components(G), key=len))
    b = bt.betweenness(G, core)
    top5 = set(sorted(b, key=b.get, reverse=True)[:5])
    extremos = {n for i, _ in cuts for n in edges_in[i][:2]}

    res = {
        "bairro": cfg.display_name, "V": len(uset), "portas": len(gw),
        "origem": len(src), "fluxo": acc["fluxo"],
        "corte_edmonds_karp": [
            {"ruas": [list(e) for e in acc["corte_arestas"]][:40],
             "n_ruas": len(acc["corte_arestas"]), "nos_lado_origem": acc["lado_origem"]}],
        "cortes_de_uma_rua": [
            {"rua": [edges_in[i][0], edges_in[i][1]],
             "coords": [coords(edges_in[i][0]), coords(edges_in[i][1])],
             "comprimento_m": round(edges_in[i][2]),
             "nos_lado_origem": len(lado), "pct_lado_origem": round(100 * len(lado) / len(uset), 1)}
            for i, lado in cuts],
        "extremos_dos_cortes_sao_as_5_mais_centrais": bool(cuts) and extremos <= top5,
    }
    if key == "urca":
        varredura = []
        for f in FRACOES:
            s2 = set(mf.gateway_access_flow(list(uset), data["undirected_edges"], gw,
                                            frac=f, details=True)["origem"])
            c2 = cortes_de_uma_rua(edges_in, adj, s2, gw)
            ext2 = {n for i, _ in c2 for n in edges_in[i][:2]}
            varredura.append({"f": f, "n_origem": len(s2), "cortes_de_uma_rua": len(c2),
                              "extremos_entre_as_5_mais_centrais": ext2 <= top5})
        res["varredura_f"] = varredura
    res["_objs"] = (data, src, gw, [edges_in[i] for i, _ in cuts], acc["corte_arestas"])
    return res


def figura(resultados):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
    for ax, r in zip(axes, resultados):
        data, src, gw, um_corte, ek_cut = r["_objs"]
        G = data["graph"]
        lut = viz._geom_lookup(data)
        viz.draw_base(data, ax, color="#dfe3ea")
        cortes = um_corte if um_corte else [(u, v) for (u, v) in ek_cut]
        ax.add_collection(LineCollection(viz._edge_segments(cortes, lut, G),
                                         colors="#c0392b", linewidths=3.4, zorder=5))
        ax.scatter([G.coords[u][0] for u in src], [G.coords[u][1] for u in src],
                   s=26, color="#2b6cb0", zorder=4)
        ax.scatter([G.coords[g][0] for g in gw], [G.coords[g][1] for g in gw],
                   s=60, marker="^", color="#2f855a", edgecolors="#1c4532",
                   linewidths=0.6, zorder=6)
        n = len(um_corte) if um_corte else len(ek_cut)
        sub = f"{n} single-street cuts" if um_corte else f"minimum cut of {n} streets"
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{r['bairro']}: access flow {r['fluxo']}\n({sub})", fontsize=12)
    handles = [
        plt.Line2D([], [], marker="o", ls="", color="#2b6cb0", label="source region"),
        plt.Line2D([], [], marker="^", ls="", color="#2f855a", markeredgecolor="#1c4532",
                   markersize=8, label="gateways"),
        plt.Line2D([], [], color="#c0392b", lw=3.4, label="cut streets"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    p = os.path.join(OUT, "fig_cut.png")
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


def main():
    resultados = [analisa(k) for k in ("urca", "copacabana", "botafogo")]
    figura(resultados)
    for r in resultados:
        r.pop("_objs")
        print(json.dumps({k: v for k, v in r.items() if k != "corte_edmonds_karp"},
                         ensure_ascii=False)[:900])
    with open(os.path.join(OUT, "localizacao_corte.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
