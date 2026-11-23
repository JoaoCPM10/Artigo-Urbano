"""
Quem sao os pedacos de fluxo 1? Regenera os pedacos sorteados de nulo_fluxo_referencia.py
(mesma semente e mesma ordem de sorteio, conferidos contra o JSON) e, para cada um
com fluxo <= 1, registra as portas, a rua do corte (comprimento e extremos) e o
numero de interseccoes do lado da origem (a regiao pendente). Agrupa os pedacos
pela rua de corte para saber quantas regioes pendentes distintas existem.

Escreve output/pedacos_fluxo1_<ref>_fontes.json.
Uso:  python -m analises.pedacos_fluxo1 leme copacabana,botafogo,alto_da_boa_vista,...
"""

from __future__ import annotations
import json
import os
import random
import statistics as st
import sys

from nucleo import maxflow as mf
from analises import nulo_fluxo as nf


def main():
    ref = sys.argv[1]
    fontes = sys.argv[2].split(",")
    guardado = json.load(open(os.path.join(nf.OUT, f"nulo_fluxo_{ref}_fontes.json"), encoding="utf-8"))
    m = guardado["referencia"]["n"]
    linhas, resumo = [], {}
    for key in fontes:
        rede = nf.Rede(key)
        comp = {frozenset((e[0], e[1])): e[2] for e in rede.edges}
        rng = random.Random(nf.SEED)
        n_src = 0
        for nome, gera in (("bola", rede.bola), ("eden", rede.eden)):
            valores = guardado["pedacos"][key][nome]["valores_fluxo"]
            for i in range(nf.N_PIECES):
                S = gera(m, rng)
                f, g = rede.fluxo(S)
                assert f == valores[i], (key, nome, i)
                if f <= 1:
                    gw = {u for u in S if any(v not in S for v in rede.full_adj.get(u, ()))}
                    r = mf.gateway_access_flow(list(S), rede.edges, gw, frac=0.2, details=True)
                    cortes = sorted((tuple(sorted(c)) for c in r["corte_arestas"]))
                    linhas.append({"fonte": key, "tipo": nome, "fluxo": f, "portas": g,
                                   "nucleo": r["n_origem"], "lado_origem": r["lado_origem"],
                                   "corte": [list(c) for c in cortes],
                                   "corte_m": [round(comp[frozenset(c)]) for c in cortes]})
                    n_src += 1
        resumo[key] = n_src
    # agrupar pelas ruas do corte
    grupos = {}
    for l in linhas:
        chave = (l["fonte"], tuple(tuple(c) for c in l["corte"]))
        grupos.setdefault(chave, []).append(l)
    print("pedacos com fluxo <= 1 por fonte:", resumo, "total", len(linhas))
    saida_grupos = []
    for (fonte, corte), ls in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        saida_grupos.append({"fonte": fonte, "pedacos": len(ls), "corte_m": ls[0]["corte_m"],
                             "lado_origem": sorted({l["lado_origem"] for l in ls}),
                             "portas_min_max": [min(l["portas"] for l in ls), max(l["portas"] for l in ls)]})
    print("regioes pendentes distintas (fonte + rua do corte):", len(saida_grupos))
    for g in saida_grupos[:15]:
        print(" ", g)
    lado = [l["lado_origem"] for l in linhas]
    ncl = [l["nucleo"] for l in linhas]
    est = {"n": len(linhas), "lado_origem_min": min(lado), "lado_origem_mediana": st.median(lado),
           "lado_origem_max": max(lado), "nucleo": sorted(set(ncl)),
           "portas_min": min(l["portas"] for l in linhas), "portas_mediana": st.median(l["portas"] for l in linhas),
           "portas_max": max(l["portas"] for l in linhas),
           "um_so_corte_de_uma_rua": sum(len(l["corte"]) == 1 for l in linhas)}
    print("resumo:", est)
    json.dump({"referencia": ref, "por_fonte": resumo, "grupos": saida_grupos, "resumo": est, "pedacos": linhas},
              open(os.path.join(nf.OUT, f"pedacos_fluxo1_{ref}_fontes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
