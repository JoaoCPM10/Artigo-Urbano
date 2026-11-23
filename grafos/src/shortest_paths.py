"""
Caminho minimo de fonte unica (Dijkstra com heap binario), O((V+E) log V).
O peso das arestas e' o tempo de viagem (segundos). A implementacao e' conferida
contra o networkx em test_vs_networkx.py.
"""

from __future__ import annotations
import heapq
import math
from graph import Graph


def dijkstra(G: Graph, source: int, target: int | None = None,
             blocked_edges: set[tuple[int, int]] | None = None,
             blocked_nodes: set[int] | None = None):
    """Dijkstra com heap binario. Retorna (dist, prev)."""
    blocked_edges = blocked_edges or set()
    blocked_nodes = blocked_nodes or set()
    dist = {source: 0.0}
    prev: dict[int, int] = {}
    pq = [(0.0, source)]
    visited: set[int] = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if target is not None and u == target:
            break
        for v, e in G.neighbors(u):
            if v in blocked_nodes or (u, v) in blocked_edges:
                continue
            nd = d + e.weight
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev
