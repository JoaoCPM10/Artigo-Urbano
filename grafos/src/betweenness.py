"""
Centralidade de intermediacao dirigida e ponderada (algoritmo de Brandes,
2001), implementada do zero sobre a estrutura Graph, sem bibliotecas de grafos.

Definicao usada no artigo:
  - grafo: o nucleo fortemente conexo gigante, dirigido;
  - peso do arco: tempo de percurso (Graph.Edge.travel_time); em arcos
    paralelos vale o menor;
  - escore de v: fracao dos pares ordenados (s, t), s != t != v, cujo(s)
    caminho(s) de tempo minimo passam por v (com divisao proporcional quando
    ha empate), i.e. sum_{s,t} sigma_st(v)/sigma_st / ((n-1)(n-2)).

A normalizacao por (n-1)(n-2) e' a de networkx.betweenness_centrality
(normalized=True, grafo dirigido); test_betweenness.py confere as duas.
"""

from __future__ import annotations
import heapq

EPS = 1e-9


def betweenness(G, nodes) -> "dict[int, float]":
    """Intermediacao normalizada de cada no de `nodes` (subgrafo induzido)."""
    S = set(nodes)
    adj: dict[int, dict[int, float]] = {u: {} for u in S}
    for e in G.edges:
        if e.u in S and e.v in S and e.u != e.v:
            w = e.travel_time
            if e.v not in adj[e.u] or w < adj[e.u][e.v]:
                adj[e.u][e.v] = w

    bc = {u: 0.0 for u in S}
    for s in S:
        stack = []
        pred: dict[int, list[int]] = {u: [] for u in S}
        sigma = {u: 0.0 for u in S}
        dist: dict[int, float] = {}
        sigma[s] = 1.0
        seen = {s: 0.0}
        counter = 0
        heap = [(0.0, counter, s)]    # (dist, desempate, no)
        while heap:
            d, _, v = heapq.heappop(heap)
            if v in dist:
                continue
            dist[v] = d
            stack.append(v)
            for w, wt in adj[v].items():
                nd = d + wt
                if w not in dist and (w not in seen or nd < seen[w] - EPS):
                    seen[w] = nd
                    counter += 1
                    heapq.heappush(heap, (nd, counter, w))
                    sigma[w] = sigma[v]
                    pred[w] = [v]
                elif w not in dist and abs(nd - seen[w]) <= EPS:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = {u: 0.0 for u in stack}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += sigma[v] / sigma[w] * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]

    n = len(S)
    scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return {u: b * scale for u, b in bc.items()}


def summary(G, nodes) -> dict:
    """Maximo (e o no que o atinge) da intermediacao normalizada."""
    bc = betweenness(G, nodes)
    top = max(bc, key=bc.get)
    return {"max": bc[top], "no_max": top, "n_nucleo": len(bc)}
