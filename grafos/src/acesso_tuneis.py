"""
Quantas das portas de acesso de cada bairro sao saidas por TUNEL, e quanto cai
o fluxo de acesso se elas forem removidas.

Uma porta e' "de tunel" quando a rua que sai do bairro por ela passa por uma via
do OpenStreetMap com tunnel=yes (ou building_passage), com a mesma fronteira
(poligono oficial) e a mesma margem (400 m) do calculo principal.

Escreve output/acesso_tuneis.json. Uso:  py acesso_tuneis.py
"""

from __future__ import annotations
import json
import math
import os

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes, GATEWAY_BUFFER_M
from osm_loader import fetch_osm, load_neighborhood, expand_bbox

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
TUNNEL_TAGS = ("yes", "building_passage")
TOL_M = 2.0     # um no do tunel a menos de 2 m da geometria da rua de saida


def analisa(cfg) -> dict:
    data, bbox = load_network(cfg)
    G = data["graph"]
    edges_u = [(u, v) for (u, v, _, _) in data["undirected_edges"]]
    uset = set(max(cc.connected_components(G.nodes(), edges_u), key=len))
    gw = gateway_nodes(cfg, data, bbox, uset)

    # mesma rede (e mesma projecao) usada para achar as portas
    name, bb = f"{cfg.key}_buffer{GATEWAY_BUFFER_M}", expand_bbox(bbox, GATEWAY_BUFFER_M)
    buf = load_neighborhood(name, bb)
    raw = fetch_osm(name, bb)
    ll = {e["id"]: (e["lat"], e["lon"]) for e in raw["elements"] if e["type"] == "node"}

    tunnel_nodes, tunnel_names = {}, {}
    for e in raw["elements"]:
        if e["type"] == "way" and e.get("tags", {}).get("tunnel") in TUNNEL_TAGS:
            for n in e["nodes"]:
                tunnel_nodes[n] = e["tags"].get("name", "(sem nome)")
    lat0, lon0 = buf["lat0"], buf["lon0"]
    kx, ky = math.cos(math.radians(lat0)) * 111320.0, 110540.0
    txy = [((ll[n][1] - lon0) * kx, (ll[n][0] - lat0) * ky, nm)
           for n, nm in tunnel_nodes.items() if n in ll]

    inside = set(G.nodes())
    tunnel_gw: dict[int, set] = {}
    for (u, v, _, geom) in buf["undirected_edges"]:
        if (u in inside) == (v in inside):
            continue
        g = u if u in inside else v
        if g not in gw:
            continue
        for (px, py) in geom:
            for (x, y, nm) in txy:
                if math.hypot(px - x, py - y) < TOL_M:
                    tunnel_gw.setdefault(g, set()).add(nm)

    base = mf.gateway_access_flow(list(uset), data["undirected_edges"], gw, frac=0.2)
    sem = mf.gateway_access_flow(list(uset), data["undirected_edges"],
                                 gw - set(tunnel_gw), frac=0.2)
    return {
        "bairro": cfg.display_name,
        "portas": len(gw),
        "portas_de_tunel": len(tunnel_gw),
        "tuneis": sorted({nm for s in tunnel_gw.values() for nm in s}),
        "fluxo": base["fluxo"],
        "fluxo_sem_portas_de_tunel": sem["fluxo"],
        "portas_restantes": sem["n_gateways"],
    }


def main():
    res = [analisa(cfg) for cfg in NEIGHBORHOODS.values()]
    for r in res:
        print(r)
    with open(os.path.join(OUT, "acesso_tuneis.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
