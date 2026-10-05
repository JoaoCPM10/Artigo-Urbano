"""
Robustez ao TIPO DE RECORTE: recompara, nos tres bairros, a rede recortada pelo
poligono oficial (usada no artigo) com a rede do retangulo manual sem recorte.
Em ambos os casos, a fronteira das portas de acesso e' a do proprio recorte
(poligono ou retangulo), como na versao anterior do pipeline.

Escreve output/robustez_recorte.{json,csv}. So' a intermediacao e o fluxo de
acesso dependem de downloads; o resto usa o cache (uma busca extra para o
retangulo de Copacabana + margem, feita na 1a execucao).

Uso:  py robustez_recorte.py
"""

from __future__ import annotations
import csv
import json
import os

import betweenness as bt
import connectivity as cc
import maxflow as mf
from main import _copia_sem_aresta, _copia_sem_no, _nucleo_intacto
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def indicadores(cfg, clip: bool) -> dict:
    data, bbox = load_network(cfg, clip=clip)
    G = data["graph"]
    nodes = G.nodes()
    edges_u = [(u, v) for (u, v, _, _) in data["undirected_edges"]]
    scc = cc.strongly_connected_components(G)
    gset = set(max(scc, key=len))
    uset = set(max(cc.connected_components(nodes, edges_u), key=len))

    pares, vistos = [], set()
    for (u, v) in edges_u:
        if u in gset and v in gset and frozenset((u, v)) not in vistos:
            vistos.add(frozenset((u, v))); pares.append((u, v))
    n_pf = sum(1 for (u, v) in pares
               if not _nucleo_intacto(_copia_sem_aresta(G, u, v), gset))
    n_af = sum(1 for u in gset
               if not _nucleo_intacto(_copia_sem_no(G, u), gset - {u}))

    gw = gateway_nodes(cfg, data, bbox, uset)
    acc = mf.gateway_access_flow(list(uset), data["undirected_edges"], gw, frac=0.2)
    return {
        "bairro": cfg.display_name,
        "recorte": "poligono oficial" if clip else "retangulo manual",
        "V": G.n, "trechos": len(edges_u), "nucleo": len(gset),
        "fora_nucleo_pct": round(100 * (G.n - len(gset)) / G.n, 1),
        "pontes_fortes_pct": round(100 * n_pf / len(pares), 1),
        "articulacoes_fortes_pct": round(100 * n_af / len(gset), 1),
        "portas": acc["n_gateways"], "fluxo": acc["fluxo"],
        "intermediacao_max_pct": round(100 * bt.summary(G, gset)["max"], 1),
    }


def main():
    linhas = []
    for cfg in NEIGHBORHOODS.values():
        for clip in (False, True):
            r = indicadores(cfg, clip)
            linhas.append(r)
            print(r)
    with open(os.path.join(OUT, "robustez_recorte.json"), "w", encoding="utf-8") as f:
        json.dump(linhas, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "robustez_recorte.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)


if __name__ == "__main__":
    main()
