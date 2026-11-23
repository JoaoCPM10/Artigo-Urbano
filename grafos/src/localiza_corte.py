"""
ONDE esta o corte do fluxo de acesso? (Secao 4.3 do artigo)

O fluxo de acesso da Urca vale 1. Isso e' o istmo do bairro ou uma ponte local
perto da regiao de origem (o artefato do corte no-a-no, Secao 4.2)? Aqui:

  - o corte que o Edmonds-Karp devolve (e' o mais PROXIMO DA ORIGEM, por
    construcao) e quantos nos ficam do lado da origem;
  - TODAS as ruas cujo fechamento sozinho separa a regiao de origem de todas as
    portas (cortes de uma rua), com comprimento, posicao e tamanho dos lados;
  - quais interseccoes extremas desses cortes coincidem com as de maior
    intermediacao (betweenness.py);
  - a mesma enumeracao para f de 0,05 a 0,50 (Urca e Leme, os bairros de fluxo 1).

Escreve output/localizacao_corte.json. A figura do corte e' feita por fig_mapas_geograficos.py.
Uso:  py localiza_corte.py
"""

from __future__ import annotations
import json
import os
from collections import deque

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

import betweenness as bt
import connectivity as cc
import maxflow as mf
import ruas_vs_intersecoes as rv
import visualize as viz
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
FRACOES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)


def _alcanca(adj, inicio, sem_aresta):
    """Nos alcancaveis a partir de `inicio` sem usar a rua de indice `sem_aresta`."""
    visto, fila = set(inicio), deque(inicio)
    while fila:
        u = fila.popleft()
        for v, i in adj[u]:
            if i != sem_aresta and v not in visto:
                visto.add(v); fila.append(v)
    return visto


def cortes_de_uma_rua(edges_in, adj, src, gw):
    """[(indice da rua, nos do lado da origem)] das ruas que sozinhas separam
    toda a regiao de origem de todas as portas. Ruas paralelas (capacidade 2)
    nunca sao corte de 1."""
    out = []
    for i, e in enumerate(edges_in):
        if sum(1 for f in edges_in if {f[0], f[1]} == {e[0], e[1]}) > 1:
            continue
        lado = _alcanca(adj, src, i)
        if not (lado & gw):
            out.append((i, lado))
    return out


def analisa(key: str) -> dict:
    cfg = NEIGHBORHOODS[key]
    data, bbox = load_network(cfg)
    G = data["graph"]
    edges_u = [(e[0], e[1]) for e in data["undirected_edges"]]
    uset = set(max(cc.connected_components(G.nodes(), edges_u), key=len))
    gw = gateway_nodes(cfg, data, bbox, uset)
    edges_in = [e for e in data["undirected_edges"] if e[0] in uset and e[1] in uset]
    adj = {u: [] for u in uset}
    for i, e in enumerate(edges_in):
        adj[e[0]].append((e[1], i)); adj[e[1]].append((e[0], i))
    ll = data["latlon"]

    def coords(n):
        return [round(ll[n][0], 5), round(ll[n][1], 5)]

    acc = mf.gateway_access_flow(list(uset), data["undirected_edges"], gw, frac=0.2, details=True)
    src = set(acc["origem"])
    cuts = cortes_de_uma_rua(edges_in, adj, src, gw)

    core = set(max(cc.strongly_connected_components(G), key=len))
    b = bt.betweenness(G, core)
    top5 = set(sorted(b, key=b.get, reverse=True)[:5])
    extremos = {n for i, _ in cuts for n in edges_in[i][:2]}

    res = {
        "bairro": cfg.display_name, "V": len(uset), "portas": len(gw),
        "origem": len(src), "fluxo": acc["fluxo"],
        "corte_edmonds_karp": [
            {"ruas": [list(e) for e in acc["corte_arestas"]][:40],
             "n_ruas": len(acc["corte_arestas"]), "nos_lado_origem": acc["lado_origem"]}],
        "cortes_de_uma_rua": [
            {"rua": [edges_in[i][0], edges_in[i][1]],
             "coords": [coords(edges_in[i][0]), coords(edges_in[i][1])],
             "comprimento_m": round(edges_in[i][2]),
             "nos_lado_origem": len(lado), "pct_lado_origem": round(100 * len(lado) / len(uset), 1)}
            for i, lado in cuts],
        "extremos_dos_cortes_sao_as_5_mais_centrais": bool(cuts) and extremos <= top5,
    }
    if key in ("urca", "leme"):
        varredura = []
        for f in FRACOES:
            s2 = set(mf.gateway_access_flow(list(uset), data["undirected_edges"], gw,
                                            frac=f, details=True)["origem"])
            c2 = cortes_de_uma_rua(edges_in, adj, s2, gw)
            ext2 = {n for i, _ in c2 for n in edges_in[i][:2]}
            varredura.append({"f": f, "n_origem": len(s2), "cortes_de_uma_rua": len(c2),
                              "extremos_entre_as_5_mais_centrais": ext2 <= top5})
        res["varredura_f"] = varredura
    res["_objs"] = (data, src, gw, [edges_in[i] for i, _ in cuts], acc["corte_arestas"])
    return res


def main():
    resultados = [analisa(k) for k in ("urca", "copacabana", "botafogo", "leme")]
    for r in resultados:
        r.pop("_objs")
        print(json.dumps({k: v for k, v in r.items() if k != "corte_edmonds_karp"},
                         ensure_ascii=False)[:900])
    with open(os.path.join(OUT, "localizacao_corte.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
