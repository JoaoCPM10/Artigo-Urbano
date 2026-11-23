"""
Sensibilidade da intermediacao as velocidades padrao (tempo de percurso).

O peso das arestas e' o tempo de percurso, e onde o OSM nao traz `maxspeed` a
velocidade vem de uma tabela por classe de via (osm_loader.DEFAULT_SPEED), que
segue o art. 61, par. 1, I, do Codigo de Transito Brasileiro. O fluxo de acesso
nao usa o peso; so' a intermediacao (de no e de aresta) usa.

Este script compara, em cada bairro, a tabela do CTB (a do artigo) com:
  anterior   : tabela usada antes (motorway 90, trunk 80, secondary 50,
               unclassified 40, links mais lentos);
  ctb_baixo  : CTB com `secondary` como coletora (40 km/h).
Medidas: intermediacao maxima de no (% dos pares) e o no que a atinge;
correlacao de Spearman e sobreposicao dos 10 maiores da intermediacao de aresta
(rua, soma dos dois sentidos), no nucleo fortemente conexo.

Uso:  py velocidade_ctb.py [chave ...]      Escreve output/velocidade_ctb.json
"""

from __future__ import annotations
import copy
import json
import os
import sys

import osm_loader as ol
import betweenness as bt
import connectivity as cc
from neighborhoods import NEIGHBORHOODS
from network import load_network
from simulacao_interrupcoes import spearman

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
CTB = copy.deepcopy(ol.DEFAULT_SPEED)

ANTERIOR = {
    "motorway": 90, "trunk": 80, "primary": 60, "secondary": 50,
    "tertiary": 40, "unclassified": 40, "residential": 30,
    "living_street": 20, "road": 30,
    "motorway_link": 60, "trunk_link": 50, "primary_link": 40,
    "secondary_link": 40, "tertiary_link": 30,
    "service": 20,
}
CTB_BAIXO = dict(CTB, secondary=40, secondary_link=40)
TRUNK80 = dict(CTB, trunk=80, trunk_link=80)

TABELAS = {"ctb": CTB, "anterior": ANTERIOR, "trunk80": TRUNK80, "ctb_baixo": CTB_BAIXO}


def medidas(chave: str, tabela: dict) -> dict:
    ol.DEFAULT_SPEED.clear()
    ol.DEFAULT_SPEED.update(tabela)
    data, _ = load_network(NEIGHBORHOODS[chave])
    G = data["graph"]
    nucleo = set(max(cc.strongly_connected_components(G), key=len))
    s = bt.summary(G, nucleo)
    eb = bt.edge_betweenness(G, nucleo)
    rua = {}
    for (u, v), x in eb.items():
        p = frozenset((u, v))
        rua[p] = rua.get(p, 0.0) + x
    return {"max_pct": 100 * s["max"], "no_max": s["no_max"], "nucleo": len(nucleo), "rua": rua}


def main():
    chaves = sys.argv[1:] or list(NEIGHBORHOODS)
    saida = {}
    for k in chaves:
        m = {nome: medidas(k, tab) for nome, tab in TABELAS.items()}
        ref = m["ctb"]
        linha = {"nucleo": ref["nucleo"], "ctb": {"max_pct": round(ref["max_pct"], 2), "no": ref["no_max"]}}
        for nome in ("anterior", "trunk80", "ctb_baixo"):
            alt = m[nome]
            ps = sorted(ref["rua"], key=lambda p: tuple(sorted(p)))
            rho = spearman([ref["rua"][p] for p in ps], [alt["rua"].get(p, 0.0) for p in ps])
            top = lambda d: set(sorted(d, key=lambda p: (-d[p], tuple(sorted(p))))[:10])
            inter = len(top(ref["rua"]) & top(alt["rua"]))
            linha[nome] = {"max_pct": round(alt["max_pct"], 2), "no": alt["no_max"],
                           "mesmo_no": alt["no_max"] == ref["no_max"],
                           "spearman_ruas": round(rho, 3), "top10_em_comum": inter}
        saida[k] = linha
        a, c, b = linha["anterior"], linha["trunk80"], linha["ctb_baixo"]
        print(f"{k:18s} N={linha['nucleo']:4d} max% ctb={linha['ctb']['max_pct']:5.1f} "
              f"anterior={a['max_pct']:5.1f} trunk80={c['max_pct']:5.1f} baixo={b['max_pct']:5.1f} | rho "
              f"{a['spearman_ruas']:.3f}/{c['spearman_ruas']:.3f}/{b['spearman_ruas']:.3f} | top10 "
              f"{a['top10_em_comum']}/{c['top10_em_comum']}/{b['top10_em_comum']} "
              f"| mesmo no {a['mesmo_no']}/{c['mesmo_no']}/{b['mesmo_no']}", flush=True)
    ol.DEFAULT_SPEED.clear()
    ol.DEFAULT_SPEED.update(CTB)
    if not sys.argv[1:]:
        with open(os.path.join(OUT, "velocidade_ctb.json"), "w", encoding="utf-8") as fh:
            json.dump(saida, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
