"""
Confere as implementacoes proprias (sem bibliotecas de grafos) contra o
networkx, usado SO' aqui, como verificacao independente. Nas tres redes:

  - componentes conexas e fortemente conexas;
  - pontes e pontos de articulacao (fracos), com ruas paralelas contadas como
    na definicao (um par com duas ruas nao tem ponte);
  - caminhos minimos (Dijkstra) a partir de varias origens;
  - fluxo maximo de Edmonds-Karp, em pares aleatorios e no fluxo de acesso
    real (superfonte e superssumidouro), com capacidade 1 por rua;
  - pontes e articulacoes FORTES: o networkx nao tem o algoritmo, entao o
    conjunto do pipeline (main.py) e' comparado com uma recontagem independente
    das componentes fortes por networkx apos remover cada elemento.

A intermediacao tem seu proprio teste (test_betweenness.py).
Uso:  py test_vs_networkx.py
"""

from __future__ import annotations
import math
import random
import sys

import networkx as nx

import connectivity as cc
import maxflow as mf
import shortest_paths as sp
from main import _copia_sem_aresta, _copia_sem_no, _nucleo_intacto
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

SEED = 11
FALHAS = []


def confere(cond, msg):
    if not cond:
        FALHAS.append(msg)
        print("  FALHA:", msg)


def testa(key):
    cfg = NEIGHBORHOODS[key]
    data, bbox = load_network(cfg)
    G = data["graph"]
    nodes = G.nodes()
    ue = data["undirected_edges"]
    edges_u = [(e[0], e[1]) for e in ue]
    rng = random.Random(SEED)
    print(f"[{key}] V={G.n} arcos={G.m} trechos={len(edges_u)}")

    # ---- componentes ------------------------------------------------------
    U = nx.Graph(); U.add_nodes_from(nodes); U.add_edges_from(edges_u)
    mine = sorted(map(sorted, cc.connected_components(nodes, edges_u)))
    ref = sorted(map(sorted, nx.connected_components(U)))
    confere(mine == ref, f"{key}: componentes conexas")
    D = nx.DiGraph(); D.add_nodes_from(nodes)
    for e in G.edges:
        D.add_edge(e.u, e.v)
    mine = sorted(map(sorted, cc.strongly_connected_components(G)))
    ref = sorted(map(sorted, nx.strongly_connected_components(D)))
    confere(mine == ref, f"{key}: componentes fortemente conexas")

    # ---- pontes e articulacoes fracas ------------------------------------
    mult = {}
    for (u, v) in edges_u:
        k = frozenset((u, v)); mult[k] = mult.get(k, 0) + 1
    ref_b = {frozenset(e) for e in nx.bridges(U) if mult[frozenset(e)] == 1}
    mine_b = {frozenset(e) for e in cc.bridges(nodes, edges_u)}
    confere(mine_b == ref_b, f"{key}: pontes fracas ({len(mine_b)} x {len(ref_b)})")
    confere(cc.articulation_points(nodes, edges_u) == set(nx.articulation_points(U)),
            f"{key}: pontos de articulacao fracos")

    # ---- Dijkstra ----------------------------------------------------------
    W = nx.DiGraph()
    for e in G.edges:
        if not W.has_edge(e.u, e.v) or W[e.u][e.v]["w"] > e.travel_time:
            W.add_edge(e.u, e.v, w=e.travel_time)
    for s in rng.sample(nodes, 8):
        d, _ = sp.dijkstra(G, s)
        r = nx.single_source_dijkstra_path_length(W, s, weight="w")
        confere(set(d) == set(r) and all(math.isclose(d[v], r[v], rel_tol=1e-9, abs_tol=1e-9) for v in r),
                f"{key}: Dijkstra a partir de {s}")

    # ---- fluxo maximo (pares aleatorios) ---------------------------------
    cap = mf.unit_capacity_network(ue)
    F = nx.DiGraph()
    for (u, v), c in cap.items():
        F.add_edge(u, v, capacity=c)
    comp = max(nx.connected_components(U), key=len)
    for _ in range(25):
        s, t = rng.sample(sorted(comp), 2)
        fm = mf.edmonds_karp(nodes, cap, s, t)[0]
        confere(int(fm) == nx.maximum_flow_value(F, s, t), f"{key}: fluxo {s}->{t}")

    # ---- fluxo de acesso real --------------------------------------------
    uset = set(comp)
    gw = gateway_nodes(cfg, data, bbox, uset)
    acc = mf.gateway_access_flow(list(uset), ue, gw, frac=0.2, details=True)
    H = nx.DiGraph()
    ue_in = [e for e in ue if e[0] in uset and e[1] in uset]
    for (u, v), c in mf.unit_capacity_network(ue_in).items():
        H.add_edge(u, v, capacity=c)
    for u in acc["origem"]:
        H.add_edge("S", u)                      # sem 'capacity' = infinita
    for g in gw:
        H.add_edge(g, "T")
    confere(acc["fluxo"] == nx.maximum_flow_value(H, "S", "T"), f"{key}: fluxo de acesso")

    # ---- pontes e articulacoes fortes ------------------------------------
    core = set(max(nx.strongly_connected_components(D), key=len))
    gset = set(max(cc.strongly_connected_components(G), key=len))
    confere(core == gset, f"{key}: nucleo forte")
    pares, vistos = [], set()
    for (u, v) in edges_u:
        k = frozenset((u, v))
        if u in gset and v in gset and k not in vistos:
            vistos.add(k); pares.append((u, v))
    mine_e = {frozenset(p) for p in pares if not _nucleo_intacto(_copia_sem_aresta(G, *p), gset)}
    mine_n = {u for u in gset if not _nucleo_intacto(_copia_sem_no(G, u), gset - {u})}

    def intacto(Dx, alvo):
        return any(alvo <= c for c in nx.strongly_connected_components(Dx))

    ref_e = set()
    for (u, v) in pares:
        Dx = D.copy(); Dx.remove_edges_from([(u, v), (v, u)])
        if not intacto(Dx, gset):
            ref_e.add(frozenset((u, v)))
    ref_n = set()
    for w in gset:
        Dx = D.copy(); Dx.remove_node(w)
        if not intacto(Dx, gset - {w}):
            ref_n.add(w)
    confere(mine_e == ref_e, f"{key}: pontes fortes ({len(mine_e)} x {len(ref_e)})")
    confere(mine_n == ref_n, f"{key}: articulacoes fortes ({len(mine_n)} x {len(ref_n)})")
    print(f"  pontes fracas={len(mine_b)} pontes fortes={len(mine_e)} "
          f"articulacoes fortes={len(mine_n)} fluxo de acesso={acc['fluxo']}")


def main():
    for key in NEIGHBORHOODS:
        testa(key)
    if FALHAS:
        print(f"\n{len(FALHAS)} falha(s).")
        sys.exit(1)
    print("\nOK: componentes, pontes/articulacoes, Dijkstra, fluxo maximo e "
          "pontes/articulacoes fortes conferem com o networkx nas tres redes.")


if __name__ == "__main__":
    main()
