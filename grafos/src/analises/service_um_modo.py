"""
Sensibilidade a vias `service` (Secao 3.4 do artigo), um modo por execucao.

O modo vem da variavel de ambiente GRAFOS_SERVICE ("" = artigo, "todas",
"publicas"; ver osm_loader.py). Para cada bairro, recalcula com a rede daquele
modo: interseccoes, trechos, portas, as quatro contagens de rotas (ruas e
interseccoes, sem e com o sentido das vias) e os cortes de uma rua.

Uso:  GRAFOS_SERVICE=todas python -m analises.service_um_modo urca copacabana ...
Escreve output/service_<modo>.json (modo vazio: "artigo").
"""

from __future__ import annotations

import json
import os
import sys

from analises import localiza_corte as lc
from analises import ruas_vs_intersecoes as ri
from caminhos import OUT
from nucleo import connectivity as cc
from nucleo.neighborhoods import NEIGHBORHOODS
from nucleo.network import load_network


def main():
    modo = os.environ.get("GRAFOS_SERVICE", "").strip().lower() or "artigo"
    chaves = sys.argv[1:] or list(NEIGHBORHOODS)
    caminho = os.path.join(OUT, f"service_{modo}.json")
    saida = json.load(open(caminho, encoding="utf-8")) if os.path.exists(caminho) else {}
    for k in chaves:
        data, _ = load_network(NEIGHBORHOODS[k])
        G = data["graph"]
        ue = data["undirected_edges"]
        pares = {frozenset((e[0], e[1])) for e in ue}
        comp = max(cc.connected_components(G.nodes(), [(e[0], e[1]) for e in ue]), key=len)
        r = ri.analisa(k)
        r.pop("_entrada")
        c = lc.analisa(k)
        saida[k] = {
            "modo": modo,
            "intersecoes": len(G.nodes()),
            "componente": len(comp),
            "trechos": len(ue),
            "ruas": len(pares),
            "portas": r["portas"],
            "nao_dirigido": r["nao_dirigido"],
            "dirigido": r["dirigido"],
            "cortes_de_uma_rua": len(c["cortes_de_uma_rua"]),
            "comprimentos_m": [x["comprimento_m"] for x in c["cortes_de_uma_rua"]],
        }
        s = saida[k]
        print(
            f"{modo:9s} {k:18s} V={s['intersecoes']:4d} trechos={s['trechos']:4d} portas={s['portas']:3d} "
            f"ruas nd/dir={s['nao_dirigido']['ruas']}/{s['dirigido']['ruas']} "
            f"int nd/dir={s['nao_dirigido']['intersecoes']}/{s['dirigido']['intersecoes']} "
            f"cortes1={s['cortes_de_uma_rua']}",
            flush=True,
        )
        with open(caminho, "w", encoding="utf-8") as fh:
            json.dump(saida, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
