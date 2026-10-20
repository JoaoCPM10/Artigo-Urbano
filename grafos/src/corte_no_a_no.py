"""
Corte minimo NO-A-NO (Secao 4.1 do artigo): quantas ruas separam duas
interseccoes?

Calcula o fluxo maximo de Edmonds-Karp, com capacidade 1 por rua (ruas paralelas
contam como duas), entre TODOS os pares de interseccoes de cada bairro (rede
recortada pelo poligono), sem sorteio e portanto sem erro de amostragem:

  - nao dirigido: todos os pares nao ordenados do maior componente nao dirigido
    (o corte e' simetrico), com capacidade 1 nos dois sentidos de cada rua;
  - dirigido: todos os pares ORDENADOS (s, t) do nucleo fortemente conexo, com
    capacidade 1 por arco (o corte de s a t difere do de t a s).

Para cada medida o arquivo traz a distribuicao, a proporcao de cortes iguais a 1,
a media e a fracao de pares cujo corte e' limitado a 1 por um no de grau 1 (no
dirigido, por grau de saida de s ou de entrada de t igual a 1).

Escreve output/corte_no_a_no.json.
Uso:  py corte_no_a_no.py [--verifica]   (--verifica exige networkx)
"""

from __future__ import annotations
import json
import os
import random
import sys
import time
from itertools import combinations, permutations

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
N_VERIFICA = 40      # pares conferidos contra o networkx, por bairro e por medida


def _resumo(vals, limitado):
    """vals: cortes de cada par; limitado: True se o par tem um no de grau 1."""
    n = len(vals)
    c1 = sum(v == 1 for v in vals)
    expl = sum(1 for v, lim in zip(vals, limitado) if v == 1 and lim)
    return {
        "n_pares": n,
        "distribuicao": {str(v): vals.count(v) for v in sorted(set(vals))},
        "pct_corte_1": round(100 * c1 / n, 1),
        "media": round(sum(vals) / n, 2),
        "minimo": min(vals),
        "maximo": max(vals),
        "pct_pares_com_no_de_grau_1": round(100 * sum(limitado) / n, 1),
        "pct_cortes_1_explicados_por_grau_1": round(100 * expl / c1, 1) if c1 else 0.0,
    }


def nao_dirigido(G, ue):
    comp = sorted(max(cc.connected_components(G.nodes(), [(e[0], e[1]) for e in ue]), key=len))
    cap = mf.unit_capacity_network(ue)
    grau = {}
    for (u, _v), c in cap.items():
        grau[u] = grau.get(u, 0) + c
    pares = list(combinations(comp, 2))
    vals = [int(mf.edmonds_karp(comp, cap, s, t)[0]) for s, t in pares]
    lim = [min(grau[s], grau[t]) == 1 for s, t in pares]
    return _resumo(vals, lim), (comp, cap, pares, vals)


def dirigido(G):
    nucleo = sorted(max(cc.strongly_connected_components(G), key=len))
    ns = set(nucleo)
    cap = {}
    for e in G.edges:
        if e.u in ns and e.v in ns:
            cap[(e.u, e.v)] = cap.get((e.u, e.v), 0) + 1
    g_sai, g_ent = {}, {}
    for (u, v), c in cap.items():
        g_sai[u] = g_sai.get(u, 0) + c
        g_ent[v] = g_ent.get(v, 0) + c
    pares = list(permutations(nucleo, 2))
    vals = [int(mf.edmonds_karp(nucleo, cap, s, t)[0]) for s, t in pares]
    lim = [min(g_sai[s], g_ent[t]) == 1 for s, t in pares]
    return _resumo(vals, lim), (nucleo, cap, pares, vals)


def verifica(nome, tipo, entrada):
    """Confere uma amostra de pares contra o networkx (valida a implementacao)."""
    import networkx as nx
    nos, cap, pares, vals = entrada
    D = nx.DiGraph()
    D.add_nodes_from(nos)
    for (u, v), c in cap.items():
        D.add_edge(u, v, capacity=c)
    rng = random.Random(0)
    for i in rng.sample(range(len(pares)), min(N_VERIFICA, len(pares))):
        s, t = pares[i]
        ref = int(nx.maximum_flow_value(D, s, t))
        assert ref == vals[i], f"{nome} {tipo} par {s}->{t}: networkx {ref} != {vals[i]}"


def main():
    checar = "--verifica" in sys.argv
    res = {"metodo": "todos os pares", "bairros": {}}
    for key, cfg in NEIGHBORHOODS.items():
        t0 = time.time()
        data, _ = load_network(cfg)
        G = data["graph"]
        r_nd, ent_nd = nao_dirigido(G, data["undirected_edges"])
        r_d, ent_d = dirigido(G)
        if checar:
            verifica(cfg.display_name, "nao dirigido", ent_nd)
            verifica(cfg.display_name, "dirigido", ent_d)
        res["bairros"][cfg.display_name] = {"nao_dirigido": r_nd, "dirigido": r_d}
        for tipo, r in (("nao dirigido", r_nd), ("dirigido", r_d)):
            print(f"{cfg.display_name:11s} {tipo:12s} pares={r['n_pares']:>7d} "
                  f"corte1={r['pct_corte_1']:5.1f}% media={r['media']:.2f} "
                  f"min-max={r['minimo']}-{r['maximo']} "
                  f"grau1={r['pct_pares_com_no_de_grau_1']}% "
                  f"(expl. {r['pct_cortes_1_explicados_por_grau_1']}%)")
        print(f"  ({time.time() - t0:.0f} s)", flush=True)
    if checar:
        print("networkx: amostra de pares confere nas duas medidas e nos tres bairros")
    with open(os.path.join(OUT, "corte_no_a_no.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
