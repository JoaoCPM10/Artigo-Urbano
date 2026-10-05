"""
O maximo da intermediacao (betweenness.py) separa a Urca das malhas abertas por
GEOGRAFIA ou so' por TAMANHO do nucleo? (Secao 4.4 do artigo)

Tres verificacoes, todas com semente fixa:

  1. Escala: em malhas planares o maximo normalizado cai como n^(-1/2); se
     max * sqrt(n) e' quase constante entre os bairros, a diferenca e' de tamanho.
  2. NULO POR SUBAMOSTRAGEM (o que responde a pergunta): sub-redes conexas de
     tamanho igual ao do nucleo da Urca, sorteadas dentro de Copacabana e de
     Botafogo (crescimento em bola por BFS e crescimento aleatorio tipo Eden).
     Se um pedaco de uma malha aberta desse tamanho chega ao maximo da Urca com
     frequencia, o maximo nao evidencia geografia.
  3. Religacao com grau preservado (nulo usual, NAO espacial): destroi a
     planaridade e compara com grafos aleatorios; incluida so' para mostrar que
     nao distingue tamanho de geografia (todos os bairros ficam muito acima).
     Grafo nao dirigido e sem pesos.

Escreve output/nulo_intermediacao.json.  Uso:  py nulo_intermediacao.py
"""

from __future__ import annotations
import json
import math
import os
import random
import statistics as st

import networkx as nx

import betweenness as bt
import connectivity as cc
from neighborhoods import NEIGHBORHOODS
from network import load_network

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
SEED = 7
N_SUB = 300          # sub-redes por bairro e por modo de crescimento
N_REWIRE = 50        # religacoes por bairro
TOL = 5              # a maior CFC da sub-rede deve ter n_urca +- TOL nos


def carrega():
    nets = {}
    for k, cfg in NEIGHBORHOODS.items():
        data, _ = load_network(cfg)
        G = data["graph"]
        core = set(max(cc.strongly_connected_components(G), key=len))
        D = nx.DiGraph()
        for e in G.edges:
            D.add_edge(e.u, e.v)
        nets[k] = (G, core, D)
    return nets


def escala(nets):
    out = {}
    for k, (G, core, D) in nets.items():
        m = bt.summary(G, core)["max"]
        out[k] = {"n_nucleo": len(core), "max_pct": round(100 * m, 2),
                  "max_vezes_raiz_n": round(m * math.sqrt(len(core)), 2)}
    return out


def _cresce(U, m, modo, rng):
    seed = rng.choice(list(U.nodes))
    if modo == "bola":
        return list(nx.bfs_tree(U, seed))[:m]
    S = {seed}
    front = set(U[seed])
    while len(S) < m and front:
        v = rng.choice(sorted(front))
        S.add(v)
        front |= set(U[v]); front -= S
    return list(S)


def subamostragem(nets, n_alvo, ref):
    rng = random.Random(SEED)
    out = {}
    for k in ("copacabana", "botafogo"):
        G, core, D = nets[k]
        U = D.to_undirected()
        for modo in ("bola", "eden"):
            vals, tent = [], 0
            while len(vals) < N_SUB and tent < 40 * N_SUB:
                tent += 1
                S = _cresce(U, rng.randint(n_alvo, n_alvo + 13), modo, rng)
                scc = max(nx.strongly_connected_components(D.subgraph(S)), key=len)
                if abs(len(scc) - n_alvo) > TOL:
                    continue
                vals.append(bt.summary(G, set(scc))["max"])
            vals.sort()
            mu, sd = st.mean(vals), st.pstdev(vals)
            out[f"{k}_{modo}"] = {
                "n_amostras": len(vals), "valores_pct": [round(100 * v, 2) for v in vals],
                "media_pct": round(100 * mu, 1),
                "mediana_pct": round(100 * st.median(vals), 1),
                "p95_pct": round(100 * vals[max(0, int(0.95 * len(vals)) - 1)], 1),
                "frac_maior_ou_igual_urca": round(sum(v >= ref for v in vals) / len(vals), 3),
                "z_urca": round((ref - mu) / sd, 2) if sd else None,
            }
    return out


def religacao(nets):
    out = {}
    for k, (G, core, D) in nets.items():
        U = nx.Graph()
        for e in G.edges:
            if e.u in core and e.v in core:
                U.add_edge(e.u, e.v)
        obs = max(nx.betweenness_centrality(U, normalized=True).values())
        nulos = []
        for i in range(N_REWIRE):
            H = U.copy()
            nx.connected_double_edge_swap(H, nswap=2 * H.number_of_edges(), seed=SEED + i)
            nulos.append(max(nx.betweenness_centrality(H, normalized=True).values()))
        mu, sd = st.mean(nulos), st.pstdev(nulos)
        out[k] = {"obs_pct": round(100 * obs, 1), "nulo_media_pct": round(100 * mu, 1),
                  "z": round((obs - mu) / sd, 1), "n_nulos": len(nulos)}
    return out


def main():
    nets = carrega()
    esc = escala(nets)
    ref = esc["urca"]["max_pct"] / 100
    res = {"escala": esc,
           "subamostragem": subamostragem(nets, esc["urca"]["n_nucleo"], ref),
           "religacao": religacao(nets)}
    print(json.dumps(res, indent=2, ensure_ascii=False))
    with open(os.path.join(OUT, "nulo_intermediacao.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
