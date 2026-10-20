"""
QUANTAS RUAS contra QUANTAS INTERSECOES precisam falhar para isolar o nucleo
do bairro de todas as suas portas de acesso? (Secao 4.2 do artigo)

Mesma origem (nucleo, f = 0,2) e mesmas portas de gateway_access_flow, quatro
contagens de rotas disjuntas (= tamanho do menor corte, pelo teorema do fluxo
maximo e corte minimo):

  1. ruas, nao dirigido        capacidade 1 por rua, nos dois sentidos
  2. interseccoes, nao dirigido  vertice dividido v_ent -> v_sai (Menger);
                                 so' interseccoes interiores tem capacidade 1;
                                 nucleo de origem e portas sao incortaveis
  3. ruas, dirigido            capacidade 1 por arco, de dentro para fora
  4. interseccoes, dirigido    vertice dividido + so' os arcos que existem

As contagens 1, 2 e 3 reproduzem a Tabela 3 do artigo; a 4 e' nova.
Escreve output/ruas_vs_intersecoes.json.
Uso:  py ruas_vs_intersecoes.py [--verifica]   (--verifica exige networkx)
"""

from __future__ import annotations
import json
import os
import sys

import connectivity as cc
import maxflow as mf
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
BIG = 10 ** 9
SS, TT = "__S__", "__T__"


def _arcos_dirigidos(G, uset):
    """Capacidade 1 por arco dirigido do grafo, dentro de `uset`."""
    cap = {}
    for e in G.edges:
        if e.u in uset and e.v in uset:
            cap[(e.u, e.v)] = cap.get((e.u, e.v), 0) + 1
    return cap


def _rede_ruas(uset, edges_in, G, dirigido):
    if dirigido:
        return _arcos_dirigidos(G, uset)
    return dict(mf.unit_capacity_network(edges_in))


def _rede_intersecoes(uset, edges_in, G, src, gw, dirigido):
    """Divide cada vertice em (v,0)=entrada e (v,1)=saida. As ruas ficam com
    capacidade infinita; so' as interseccoes interiores custam 1."""
    cap = {}
    for v in uset:
        cap[((v, 0), (v, 1))] = BIG if (v in src or v in gw) else 1
    if dirigido:
        pares = [(u, v) for (u, v) in _arcos_dirigidos(G, uset)]
    else:
        pares = []
        for e in edges_in:
            pares.append((e[0], e[1])); pares.append((e[1], e[0]))
    for (u, v) in pares:
        cap[((u, 1), (v, 0))] = BIG
    return cap


def _fluxo(nos, cap, src, gw, dividido):
    """Fluxo maximo super-fonte -> nucleo, portas -> super-sumidouro."""
    cap = dict(cap)
    for u in src:
        cap[(SS, (u, 0) if dividido else u)] = BIG
    for g in gw:
        cap[((g, 1) if dividido else g, TT)] = BIG
    fmax, _, _, cut = mf.edmonds_karp(nos + [SS, TT], cap, SS, TT)
    cut = [(a, b) for (a, b) in cut if a not in (SS, TT) and b not in (SS, TT)]
    return int(fmax), cut


def analisa(key: str) -> dict:
    cfg = NEIGHBORHOODS[key]
    data, bbox = load_network(cfg)
    G = data["graph"]
    edges_u = [(e[0], e[1]) for e in data["undirected_edges"]]
    uset = set(max(cc.connected_components(G.nodes(), edges_u), key=len))
    gw = gateway_nodes(cfg, data, bbox, uset)
    edges_in = [e for e in data["undirected_edges"] if e[0] in uset and e[1] in uset]
    acc = mf.gateway_access_flow(list(uset), data["undirected_edges"], gw, frac=0.2, details=True)
    src = set(acc["origem"])
    ll = data["latlon"]
    nos = list(uset)
    nos_div = [(v, s) for v in uset for s in (0, 1)]

    res = {"bairro": cfg.display_name, "portas": len(gw), "origem": len(src),
           "fluxo_ruas_referencia_gateway_access_flow": acc["fluxo"]}
    for nome, dirigido in (("nao_dirigido", False), ("dirigido", True)):
        f_ruas, cut_r = _fluxo(nos, _rede_ruas(uset, edges_in, G, dirigido), src, gw, False)
        f_int, cut_i = _fluxo(nos_div, _rede_intersecoes(uset, edges_in, G, src, gw, dirigido),
                              src, gw, True)
        verts = sorted({a[0] for (a, b) in cut_i if a[0] == b[0]})
        res[nome] = {
            "ruas": f_ruas, "intersecoes": f_int,
            "corte_ruas": [list(e) for e in cut_r][:40],
            "corte_intersecoes": [{"no": v, "coords": [round(ll[v][0], 5), round(ll[v][1], 5)]}
                                  for v in verts][:40],
        }
    assert res["nao_dirigido"]["ruas"] == acc["fluxo"], "contagem por ruas nao bate com gateway_access_flow"
    res["_entrada"] = (uset, edges_in, G, src, gw)
    return res


def verifica(res) -> None:
    """Confere as quatro contagens com o networkx (maximum_flow), montando as
    redes de novo, por outro caminho de codigo."""
    import networkx as nx
    uset, edges_in, G, src, gw = res["_entrada"]

    def nx_fluxo(D):
        for u in src:
            D.add_edge(SS, u)             # sem 'capacity' = infinita
        for g in gw:
            D.add_edge(g, TT)
        return nx.maximum_flow_value(D, SS, TT)

    for dirigido in (False, True):
        # ruas
        D = nx.DiGraph()
        D.add_nodes_from(uset)
        if dirigido:
            for e in G.edges:
                if e.u in uset and e.v in uset:
                    c = D[e.u][e.v]["capacity"] + 1 if D.has_edge(e.u, e.v) else 1
                    D.add_edge(e.u, e.v, capacity=c)
        else:
            for e in edges_in:
                for a, b in ((e[0], e[1]), (e[1], e[0])):
                    c = D[a][b]["capacity"] + 1 if D.has_edge(a, b) else 1
                    D.add_edge(a, b, capacity=c)
        r = nx_fluxo(D)
        # interseccoes
        D = nx.DiGraph()
        for v in uset:
            if v in src or v in gw:
                D.add_edge(("e", v), ("s", v))
            else:
                D.add_edge(("e", v), ("s", v), capacity=1)
        if dirigido:
            for e in G.edges:
                if e.u in uset and e.v in uset:
                    D.add_edge(("s", e.u), ("e", e.v))
        else:
            for e in edges_in:
                D.add_edge(("s", e[0]), ("e", e[1])); D.add_edge(("s", e[1]), ("e", e[0]))
        for u in src:
            D.add_edge(SS, ("e", u))
        for g in gw:
            D.add_edge(("s", g), TT)
        i = nx.maximum_flow_value(D, SS, TT)
        nome = "dirigido" if dirigido else "nao_dirigido"
        assert r == res[nome]["ruas"], f"networkx ruas {nome}: {r} != {res[nome]['ruas']}"
        assert i == res[nome]["intersecoes"], f"networkx intersecoes {nome}: {i} != {res[nome]['intersecoes']}"


def main():
    chaves = ["urca", "copacabana", "botafogo"]
    saida = {}
    checar = "--verifica" in sys.argv
    print(f"{'bairro':<12}{'portas':>7}{'ruas':>6}{'inters.':>8}{'ruas(dir)':>10}{'inters.(dir)':>13}")
    for k in chaves:
        r = analisa(k)
        if checar:
            verifica(r)
        nd, d = r["nao_dirigido"], r["dirigido"]
        print(f"{r['bairro']:<12}{r['portas']:>7}{nd['ruas']:>6}{nd['intersecoes']:>8}"
              f"{d['ruas']:>10}{d['intersecoes']:>13}")
        r.pop("_entrada")
        saida[k] = r
    if checar:
        print("networkx: as quatro contagens conferem nos tres bairros")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "ruas_vs_intersecoes.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
