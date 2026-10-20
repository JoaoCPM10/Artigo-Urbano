"""
CONTROLE DE TAMANHO, fluxo de acesso x intermediacao maxima, nos MESMOS pedacos
(Secao 4.4 do artigo).

nulo_fluxo.py sorteia, dentro de Copacabana e de Botafogo, pedacos conexos com o
mesmo numero de intersecoes da Urca (70), por crescimento em bola (BFS) e por
crescimento aleatorio (Eden). Este script regenera EXATAMENTE esses pedacos
(mesma semente e mesma ordem de sorteio) e mede, em cada um, duas coisas:

  - o fluxo de acesso (o mesmo valor de nulo_fluxo.py, conferido);
  - o maximo da intermediacao dirigida no maior componente fortemente conexo do
    pedaco (betweenness.py), para comparar com o da Urca (nucleo de 65 nos).

Como os pedacos sao os mesmos, a comparacao entre as duas medidas nao depende de
tamanho nem de sorteio. O tamanho do componente forte de cada pedaco tambem e'
registrado, porque um componente menor que o da Urca tende a elevar o maximo.

Pareamento pelo nucleo forte: como a intermediacao e' definida no componente
fortemente conexo, e pedacos de 70 intersecoes costumam ter um nucleo forte bem
menor que o da Urca (65), um segundo conjunto de pedacos e' sorteado com tamanho
bruto de 65 a 130 intersecoes e mantido so' se o nucleo forte tem 65 +- 5 nos.

Escreve output/controle_tamanho_intermediacao.json.  Uso:  py controle_tamanho_intermediacao.py
"""

from __future__ import annotations
import json
import os
import random
import statistics as st

import networkx as nx

import betweenness as bt
import connectivity as cc
import nulo_fluxo as nf
from neighborhoods import NEIGHBORHOODS
from network import load_network

OUT = nf.OUT
JANELA_NUCLEO = 60      # pedacos cujo componente forte tem ao menos 60 nos
TOL_NUCLEO = 5          # pareamento: nucleo forte do pedaco = nucleo da Urca +- 5
N_PAREADOS = 300        # pedacos pareados por bairro e por modo de crescimento
TENTATIVAS = 200        # no maximo TENTATIVAS * N_PAREADOS sorteios por modo


def maximo_intermediacao(G, S):
    D = nx.DiGraph()
    D.add_nodes_from(S)
    for e in G.edges:
        if e.u in S and e.v in S and e.u != e.v:
            D.add_edge(e.u, e.v)
    scc = max(nx.strongly_connected_components(D), key=len)
    return bt.summary(G, set(scc))["max"], len(scc)


def pareados(rede, G, ref, ref_n, modo, rng):
    """Pedacos com nucleo forte de ref_n +- TOL_NUCLEO nos; devolve (maximos, tamanhos, tentativas)."""
    gera = rede.bola if modo == "bola" else rede.eden
    maxs, tams, tent = [], [], 0
    while len(maxs) < N_PAREADOS and tent < TENTATIVAS * N_PAREADOS:
        tent += 1
        S = gera(rng.randint(ref_n, 2 * ref_n), rng)
        D = nx.DiGraph()
        D.add_nodes_from(S)
        for e in G.edges:
            if e.u in S and e.v in S and e.u != e.v:
                D.add_edge(e.u, e.v)
        scc = max(nx.strongly_connected_components(D), key=len)
        if abs(len(scc) - ref_n) > TOL_NUCLEO:
            continue
        maxs.append(bt.summary(G, set(scc))["max"])
        tams.append(len(scc))
    return maxs, tams, tent


def main():
    cfg_u = NEIGHBORHOODS["urca"]
    G_u = load_network(cfg_u)[0]["graph"]
    core_u = set(max(cc.strongly_connected_components(G_u), key=len))
    ref = bt.summary(G_u, core_u)["max"]
    ref_n = len(core_u)
    urca = nf.Rede("urca")
    m = len(urca.inside)
    ref_fluxo, _ = urca.fluxo(urca.inside)
    res = {"referencia_urca": {"intersecoes": m, "nucleo_forte": ref_n,
                               "intermediacao_maxima_pct": round(100 * ref, 2),
                               "fluxo": ref_fluxo},
           "pedacos": {}}
    guardado = json.load(open(os.path.join(OUT, "nulo_fluxo.json"), encoding="utf-8"))

    for key in ("copacabana", "botafogo"):
        rede = nf.Rede(key)
        G = load_network(NEIGHBORHOODS[key])[0]["graph"]
        rng = random.Random(nf.SEED)
        bloco = {}
        for nome, gera in (("bola", rede.bola), ("eden", rede.eden)):
            fluxos, maxs, tams = [], [], []
            for _ in range(nf.N_PIECES):
                S = gera(m, rng)
                f, _g = rede.fluxo(S)
                mx, n_scc = maximo_intermediacao(G, S)
                fluxos.append(f); maxs.append(mx); tams.append(n_scc)
            # os pedacos sao os de nulo_fluxo.py: o fluxo tem de coincidir
            assert fluxos == guardado["pedacos"][key][nome]["valores_fluxo"], \
                f"{key} {nome}: pedacos diferentes dos de nulo_fluxo.json"
            idx = [i for i, t in enumerate(tams) if t >= JANELA_NUCLEO]
            ge = [mx >= ref for mx in maxs]
            bloco[nome] = {
                "n_pedacos": len(maxs),
                "fluxo_minimo": min(fluxos),
                "intermediacao_mediana_pct": round(100 * st.median(maxs), 1),
                "intermediacao_p95_pct": round(100 * sorted(maxs)[int(0.95 * len(maxs)) - 1], 1),
                "nucleo_forte_mediana": st.median(tams),
                "frac_intermediacao_ge_urca": round(sum(ge) / len(ge), 3),
                "n_com_nucleo_ge_60": len(idx),
                "frac_intermediacao_ge_urca_nucleo_ge_60":
                    round(sum(ge[i] for i in idx) / len(idx), 3) if idx else None,
                "frac_fluxo_le_1": round(sum(f <= 1 for f in fluxos) / len(fluxos), 3),
            }
            print(key, nome, json.dumps(bloco[nome], ensure_ascii=False))
        res["pedacos"][key] = bloco
        rng2 = random.Random(nf.SEED)
        pareado = {}
        for modo in ("bola", "eden"):
            maxs, tams, tent = pareados(rede, G, ref, ref_n, modo, rng2)
            pareado[modo] = {
                "n_pedacos": len(maxs), "tentativas": tent,
                "nucleo_forte_min_max": [min(tams), max(tams)],
                "intermediacao_mediana_pct": round(100 * st.median(maxs), 1),
                "intermediacao_p95_pct": round(100 * sorted(maxs)[max(0, int(0.95 * len(maxs)) - 1)], 1),
                "frac_intermediacao_ge_urca": round(sum(v >= ref for v in maxs) / len(maxs), 3),
            }
            print(key, modo, "PAREADO", json.dumps(pareado[modo], ensure_ascii=False))
        res.setdefault("pareado_por_nucleo_forte", {})[key] = pareado
    print("Urca:", res["referencia_urca"])
    with open(os.path.join(OUT, "controle_tamanho_intermediacao.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
