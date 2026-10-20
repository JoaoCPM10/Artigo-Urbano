"""
Sensibilidade do fluxo de acesso por portas (Secao 3.3 do artigo), nos TRES
bairros e com a mesma fronteira (poligono oficial):

  - margem de busca da fronteira (metros alem do envelope): 200, 400, 800;
  - fracao f da regiao de origem: 0,15 / 0,20 / 0,25.

Cada margem diferente exige um download extra da Overpass (cacheado em
data/ apos a primeira vez). Escreve output/sensibilidade_acesso.{json,csv}.

Varredura ampla de f (0,05 a 0,50, margem padrao de 400 m), nos tres bairros:
mostra ate' onde o fluxo de acesso e' estavel quando o nucleo cresce. Escreve
output/sensibilidade_fracao.{json,csv}.

Uso:  py sensitivity.py            (as duas analises)
      py sensitivity.py --fracao   (so' a varredura ampla de f)
"""

from __future__ import annotations
import csv
import json
import os
import sys

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
MARGENS_M = (200, 400, 800)
FRACOES = (0.15, 0.20, 0.25)
FRACOES_AMPLAS = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)


def varre_fracao():
    """Fluxo de acesso (por ruas, nao dirigido) para f de 0,05 a 0,50, com a
    margem padrao. Acima de ~0,25 o nucleo passa a incluir o corredor da Urca."""
    linhas = []
    for key, cfg in NEIGHBORHOODS.items():
        data, bbox = load_network(cfg)
        G = data["graph"]
        edges_u = [(e[0], e[1]) for e in data["undirected_edges"]]
        uset = set(max(cc.connected_components(G.nodes(), edges_u), key=len))
        ul = list(uset)
        gw = gateway_nodes(cfg, data, bbox, uset)
        for f in FRACOES_AMPLAS:
            r = mf.gateway_access_flow(ul, data["undirected_edges"], gw, frac=f)
            linhas.append({"bairro": cfg.display_name, "f": f, "n_origem": r["n_origem"],
                           "portas": r["n_gateways"], "fluxo": r["fluxo"]})
    with open(os.path.join(OUT, "sensibilidade_fracao.json"), "w", encoding="utf-8") as fh:
        json.dump(linhas, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "sensibilidade_fracao.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader(); w.writerows(linhas)
    print("\nFluxo de acesso em funcao de f (margem padrao):")
    print(f"  {'bairro':<11}" + "".join(f"{f:>6.2f}" for f in FRACOES_AMPLAS))
    for cfg in NEIGHBORHOODS.values():
        fl = [r["fluxo"] for r in linhas if r["bairro"] == cfg.display_name]
        print(f"  {cfg.display_name:<11}" + "".join(f"{x:>6d}" for x in fl))


def main():
    if "--fracao" in sys.argv:
        varre_fracao()
        return
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
    varre_fracao()


if __name__ == "__main__":
    main()
