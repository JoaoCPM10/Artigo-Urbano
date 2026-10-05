"""
Corte minimo NO-A-NO (Secao 4.2 do artigo): quantas ruas separam dois
interseccoes escolhidas ao acaso?

Sorteia N_PARES pares de interseccoes do maior componente nao dirigido de cada
bairro (rede recortada pelo poligono, semente fixa) e calcula o fluxo maximo de
Edmonds-Karp com capacidade 1 por rua (rede nao dirigida; ruas paralelas contam
como duas). Substitui a escolha de UM par por bairro por heuristica, que nao
representa a distribuicao.

Escreve output/corte_no_a_no.json.  Uso:  py corte_no_a_no.py
"""

from __future__ import annotations
import json
import os
import random

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
SEED = 5
N_PARES = 300


def main():
    rng = random.Random(SEED)
    res = {"n_pares": N_PARES, "semente": SEED, "bairros": {}}
    for key, cfg in NEIGHBORHOODS.items():
        data, _ = load_network(cfg)
        G = data["graph"]
        ue = data["undirected_edges"]
        comp = sorted(max(cc.connected_components(G.nodes(), [(e[0], e[1]) for e in ue]), key=len))
        cap = mf.unit_capacity_network(ue)
        vals = []
        for _ in range(N_PARES):
            s, t = rng.sample(comp, 2)
            vals.append(int(mf.edmonds_karp(G.nodes(), cap, s, t)[0]))
        dist = {str(v): vals.count(v) for v in sorted(set(vals))}
        res["bairros"][cfg.display_name] = {
            "distribuicao": dist,
            "pct_corte_1": round(100 * vals.count(1) / N_PARES, 1),
            "media": round(sum(vals) / N_PARES, 2),
            "maximo": max(vals),
        }
        print(cfg.display_name, res["bairros"][cfg.display_name])
    with open(os.path.join(OUT, "corte_no_a_no.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
