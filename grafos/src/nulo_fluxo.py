"""
CONTROLE DE TAMANHO para o fluxo de acesso: um valor de 1, como o da Urca, e'
so' efeito de a rede ser pequena (70 interseccoes)?

Sorteamos, dentro de Copacabana e de Botafogo, sub-redes conexas com o MESMO
numero de interseccoes da Urca (70), as tratamos como bairros e medimos o fluxo
de acesso ate a fronteira de cada uma:

  - portas do pedaco = interseccoes do pedaco com pelo menos uma rua para um no
    fora dele, na rede COMPLETA (com margem de 400 m, inclusive fora do
    poligono, para que ruas que saem do bairro tambem contem);
  - regiao de origem e fluxo exatamente como no artigo (maxflow.gateway_access_flow,
    f = 0,2, capacidade 1 por rua, rede nao dirigida).

Tres geradores de pedacos: bola por BFS, crescimento aleatorio (Eden) e uma BUSCA
ADVERSARIA (subida de encosta que troca nos do pedaco para MINIMIZAR o fluxo),
que estima o menor fluxo que um pedaco de uma malha aberta desse tamanho pode ter.

Escreve output/nulo_fluxo.json.  Uso:  py nulo_fluxo.py
"""

from __future__ import annotations
import json
import os
import random
import statistics as st
from collections import deque

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network, GATEWAY_BUFFER_M
from osm_loader import load_neighborhood, expand_bbox

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
SEED = 7
N_PIECES = 500            # pedacos por bairro e por gerador
N_RESTARTS, N_ITERS = 8, 1500


class Rede:
    """Rede de um bairro para amostrar pedacos."""

    def __init__(self, key):
        cfg = NEIGHBORHOODS[key]
        data, bbox = load_network(cfg)
        self.edges = data["undirected_edges"]                 # dentro do poligono
        nodes = data["graph"].nodes()
        comp = set(max(cc.connected_components(nodes, [(e[0], e[1]) for e in self.edges]), key=len))
        self.inside = comp
        self.adj = {u: set() for u in comp}
        for e in self.edges:
            if e[0] in comp and e[1] in comp:
                self.adj[e[0]].add(e[1]); self.adj[e[1]].add(e[0])
        buf = load_neighborhood(f"{key}_buffer{GATEWAY_BUFFER_M}",
                                expand_bbox(bbox, GATEWAY_BUFFER_M))
        self.full_adj = {}
        for e in buf["undirected_edges"]:
            self.full_adj.setdefault(e[0], set()).add(e[1])
            self.full_adj.setdefault(e[1], set()).add(e[0])
        self.nodes = sorted(comp)

    def fluxo(self, S):
        S = set(S)
        gw = {u for u in S if any(v not in S for v in self.full_adj.get(u, ()))}
        r = mf.gateway_access_flow(list(S), self.edges, gw, frac=0.2)
        return r["fluxo"], len(gw)

    def bola(self, m, rng):
        seed = rng.choice(self.nodes)
        seen, q = [seed], deque([seed])
        vis = {seed}
        while q and len(seen) < m:
            u = q.popleft()
            for v in sorted(self.adj[u]):
                if v not in vis:
                    vis.add(v); seen.append(v); q.append(v)
                    if len(seen) == m:
                        break
        return set(seen)

    def eden(self, m, rng):
        S = {rng.choice(self.nodes)}
        front = set(self.adj[next(iter(S))])
        while len(S) < m and front:
            v = rng.choice(sorted(front))
            S.add(v)
            front |= self.adj[v]; front -= S
        return S

    def conexo(self, S):
        S = set(S)
        s0 = next(iter(S)); vis = {s0}; q = deque([s0])
        while q:
            u = q.popleft()
            for v in self.adj[u]:
                if v in S and v not in vis:
                    vis.add(v); q.append(v)
        return len(vis) == len(S)

    def adversaria(self, m, rng):
        """Subida de encosta: troca 1 no do pedaco por um vizinho, aceita se o
        fluxo nao aumenta. Devolve o menor fluxo encontrado."""
        melhor = None
        for _ in range(N_RESTARTS):
            S = self.eden(m, rng)
            f, g = self.fluxo(S)
            for _ in range(N_ITERS):
                fora = {v for u in S for v in self.adj[u]} - S
                if not fora:
                    break
                sai = rng.choice(sorted(S)); entra = rng.choice(sorted(fora))
                T = (S - {sai}) | {entra}
                if not self.conexo(T):
                    continue
                f2, g2 = self.fluxo(T)
                if f2 <= f:
                    S, f, g = T, f2, g2
            if melhor is None or f < melhor[0]:
                melhor = (f, g, S)
        return melhor


def resumo(vals):
    v = sorted(vals)
    return {"n": len(v), "min": v[0], "p5": v[int(0.05 * len(v))], "mediana": st.median(v),
            "p95": v[int(0.95 * len(v)) - 1], "max": v[-1]}


def main():
    urca = Rede("urca")
    m = len(urca.inside)
    f_urca, g_urca = urca.fluxo(urca.inside)
    res = {"referencia_urca": {"n": m, "fluxo": f_urca, "portas": g_urca}, "pedacos": {}}
    for key in ("copacabana", "botafogo"):
        rede = Rede(key)
        rng = random.Random(SEED)
        bloco = {}
        for nome, gera in (("bola", rede.bola), ("eden", rede.eden)):
            fl, gw = [], []
            for _ in range(N_PIECES):
                f, g = rede.fluxo(gera(m, rng))
                fl.append(f); gw.append(g)
            bloco[nome] = {"fluxo": resumo(fl), "portas": resumo(gw), "valores_fluxo": fl,
                           "frac_fluxo_le_3": round(sum(x <= 3 for x in fl) / len(fl), 3),
                           "frac_fluxo_le_1": round(sum(x <= 1 for x in fl) / len(fl), 3)}
        f_min, g_min, S_min = rede.adversaria(m, rng)
        bloco["adversaria"] = {"menor_fluxo": f_min, "portas_do_pedaco": g_min,
                               "n_nos": len(S_min)}
        res["pedacos"][key] = bloco
        print(key, json.dumps(bloco, ensure_ascii=False))
    print("Urca:", res["referencia_urca"])
    with open(os.path.join(OUT, "nulo_fluxo.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
