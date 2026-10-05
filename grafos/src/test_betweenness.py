"""Confere betweenness.py contra networkx (usado SO' aqui, como verificacao
independente; o pipeline nao depende de networkx).

Uso:  py test_betweenness.py
"""
import networkx as nx

import betweenness as bt
import connectivity as cc
from neighborhoods import NEIGHBORHOODS
from network import load_network


def main():
    for key, cfg in NEIGHBORHOODS.items():
        data, _ = load_network(cfg)
        G = data["graph"]
        core = set(max(cc.strongly_connected_components(G), key=len))
        mine = bt.betweenness(G, core)

        D = nx.DiGraph()
        for e in G.edges:
            if e.u in core and e.v in core:
                if not D.has_edge(e.u, e.v) or D[e.u][e.v]["w"] > e.travel_time:
                    D.add_edge(e.u, e.v, w=e.travel_time)
        ref = nx.betweenness_centrality(D, weight="w", normalized=True)

        err = max(abs(mine[u] - ref[u]) for u in core)
        print(f"{key:11s} n={len(core):4d}  max meu={max(mine.values()):.6f} "
              f"networkx={max(ref.values()):.6f}  erro max={err:.2e}")
        assert err < 1e-9, f"{key}: divergencia de {err}"
    print("OK: implementacao propria confere com networkx.")


if __name__ == "__main__":
    main()
