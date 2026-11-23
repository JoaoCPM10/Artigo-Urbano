"""
Copias do grafo com uma aresta ou um vertice removido, para testar as pontes e
articulacoes FORTES (conexidade dirigida) restritas ao nucleo. Usa somente a
estrutura Graph (sem bibliotecas de grafos), copiando os atributos ja calculados
de cada arco (length, travel_time) em vez de recalcula-los das coordenadas.
"""

from __future__ import annotations
from nucleo import connectivity as cc
from nucleo.graph import Graph


def copia_sem_aresta(G: Graph, u: int, v: int) -> Graph:
    H = Graph()
    for nid, (x, y) in G.coords.items():
        H.add_node(nid, x, y)
    par = {u, v}
    for e in G.edges:
        if {e.u, e.v} == par:
            continue
        H._add_directed(e.u, e.v, e.length, e.travel_time, e.oneway)
    return H


def copia_sem_no(G: Graph, w: int) -> Graph:
    H = Graph()
    for nid, (x, y) in G.coords.items():
        if nid != w:
            H.add_node(nid, x, y)
    for e in G.edges:
        if e.u == w or e.v == w:
            continue
        H._add_directed(e.u, e.v, e.length, e.travel_time, e.oneway)
    return H


def nucleo_intacto(H: Graph, alvo: set[int]) -> bool:
    """Os vertices de `alvo` (o nucleo original, menos o removido se for o
    caso) ainda formam uma unica componente fortemente conexa em H?"""
    for comp in cc.strongly_connected_components(H):
        if alvo <= set(comp):
            return True
    return False
