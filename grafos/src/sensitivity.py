"""
Sensibilidade do fluxo de acesso por portas (Secao 3.3 do artigo), nos TRES
bairros e com a mesma fronteira (poligono oficial):

  - margem de busca da fronteira (metros alem do envelope): 200, 400, 800;
  - fracao f da regiao de origem: 0,15 / 0,20 / 0,25.

Cada margem diferente exige um download extra da Overpass (cacheado em
data/ apos a primeira vez). Escreve output/sensibilidade_acesso.{json,csv}.

Uso:  py sensitivity.py
"""

from __future__ import annotations
import csv
import json
import os

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
MARGENS_M = (200, 400, 800)
FRACOES = (0.15, 0.20, 0.25)


def main():
    linhas = []
    for key, cfg in NEIGHBORHOODS.items():
        data, bbox = load_network(cfg)
        G = data["graph"]
        nodes = G.nodes()
        edges_u = [(u, v) for (u, v, _, _) in data["undirected_edges"]]
        uset = set(max(cc.connected_components(nodes, edges_u), key=len))
        ul = list(uset)
        for m in MARGENS_M:
            gw = gateway_nodes(cfg, data, bbox, uset, buffer_m=m)
            for f in FRACOES:
                r = mf.gateway_access_flow(ul, data["undirected_edges"], gw, frac=f)
                linhas.append({"bairro": cfg.display_name, "margem_m": m, "f": f,
                               "portas": r["n_gateways"], "fluxo": r["fluxo"],
                               "n_origem": r["n_origem"]})
                print(f"{cfg.display_name:11s} margem={m:3d} m f={f:.2f} "
                      f"portas={r['n_gateways']:2d} fluxo={r['fluxo']}")
    with open(os.path.join(OUT, "sensibilidade_acesso.json"), "w", encoding="utf-8") as fh:
        json.dump(linhas, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "sensibilidade_acesso.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader(); w.writerows(linhas)

    print("\nResumo (faixa do fluxo de acesso sobre margem x f):")
    for cfg in NEIGHBORHOODS.values():
        fl = [r["fluxo"] for r in linhas if r["bairro"] == cfg.display_name]
        pt = [r["portas"] for r in linhas if r["bairro"] == cfg.display_name]
        print(f"  {cfg.display_name:11s} fluxo {min(fl)}-{max(fl)}  portas {min(pt)}-{max(pt)}")


if __name__ == "__main__":
    main()
