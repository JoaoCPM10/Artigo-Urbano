"""
O NUCLEO DEPENDE DO DESEMPATE? (Secao 3.4 do artigo)

Em gateway_access_flow, o nucleo e' formado pelas k intersecoes interiores de
maior distancia (em arestas) a porta mais proxima. Quando varias intersecoes
empatam na distancia de corte, entram as que aparecem antes na lista, e a ordem
da lista vem da iteracao de um conjunto: arbitraria. Aqui embaralhamos a ordem
dos candidatos (sementes fixas), refazemos o nucleo e recalculamos as quatro
contagens de rotas (ruas e intersecoes, sem e com o sentido das vias).

A ordem 0 reproduz a regra usada no artigo e e' conferida contra
ruas_vs_intersecoes.analisa.
Escreve output/robustez_desempate.json.
Uso:  py robustez_desempate.py [N_SORTEIOS]      (padrao: 200)
"""

from __future__ import annotations
import json
import os
import random
import sys
from collections import Counter, deque

import connectivity as cc
import ruas_vs_intersecoes as ri
from neighborhoods import NEIGHBORHOODS
from network import load_network, gateway_nodes

SEMENTE = 20261012
FRAC = 0.2


def _distancias(uset, edges_in, gw):
    adj = {u: set() for u in uset}
    for a, b in edges_in:
        adj[a].add(b)
        adj[b].add(a)
    dist = {g: 0 for g in gw}
    q = deque(gw)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def _nucleo(candidatos, dist, k):
    return set(sorted(candidatos, key=lambda u: -dist.get(u, 0))[:k])


def _quatro(uset, edges_in, G, src, gw, nos, nos_div):
    out = {}
    for nome, dirigido in (("nao_dirigido", False), ("dirigido", True)):
        f_r, _ = ri._fluxo(nos, ri._rede_ruas(uset, edges_in, G, dirigido), src, gw, False)
        f_i, _ = ri._fluxo(nos_div, ri._rede_intersecoes(uset, edges_in, G, src, gw, dirigido),
                           src, gw, True)
        out[f"{nome}_ruas"] = f_r
        out[f"{nome}_intersecoes"] = f_i
    return out


def analisa(key: str, n_sorteios: int) -> dict:
    cfg = NEIGHBORHOODS[key]
    data, bbox = load_network(cfg)
    G = data["graph"]
    edges_u = [(e[0], e[1]) for e in data["undirected_edges"]]
    uset = set(max(cc.connected_components(G.nodes(), edges_u), key=len))
    gw = gateway_nodes(cfg, data, bbox, uset)
    edges_in = [(e[0], e[1]) for e in data["undirected_edges"] if e[0] in uset and e[1] in uset]
    # ri._rede_ruas e ri._rede_intersecoes aceitam arestas com campos extras
    edges_full = [e for e in data["undirected_edges"] if e[0] in uset and e[1] in uset]

    dist = _distancias(uset, edges_in, gw)
    base = [u for u in uset if u not in gw]
    k = max(1, int(round(FRAC * len(uset))))
    nos = list(uset)
    nos_div = [(v, s) for v in uset for s in (0, 1)]

    # conferencia: a ordem original reproduz o nucleo e os valores do artigo
    src0 = _nucleo(base, dist, k)
    ref = ri.analisa(key)
    assert src0 == ref["_entrada"][3], "nucleo reconstruido difere do de gateway_access_flow"
    v0 = _quatro(uset, edges_full, G, src0, gw, nos, nos_div)
    assert v0["nao_dirigido_ruas"] == ref["nao_dirigido"]["ruas"]
    assert v0["dirigido_intersecoes"] == ref["dirigido"]["intersecoes"]

    # empates na distancia de corte
    ordenados = sorted(base, key=lambda u: -dist.get(u, 0))
    d_corte = dist.get(ordenados[k - 1], 0)
    empatados = [u for u in base if dist.get(u, 0) == d_corte]
    acima = sum(1 for u in base if dist.get(u, 0) > d_corte)

    rng = random.Random(SEMENTE)
    contagens = {nome: Counter() for nome in v0}
    nucleos_distintos = set()
    for _ in range(n_sorteios):
        ordem = list(base)
        rng.shuffle(ordem)
        src = _nucleo(ordem, dist, k)
        nucleos_distintos.add(frozenset(src))
        for nome, val in _quatro(uset, edges_full, G, src, gw, nos, nos_div).items():
            contagens[nome][val] += 1

    return {
        "bairro": cfg.display_name,
        "k": k, "n_componente": len(uset), "portas": len(gw),
        "dist_corte": d_corte,
        "empatados_na_dist_corte": len(empatados),
        "acima_da_dist_corte": acima,
        "vagas_no_empate": k - acima,
        "n_sorteios": n_sorteios,
        "nucleos_distintos": len(nucleos_distintos),
        "valor_artigo": v0,
        "distribuicao": {nome: dict(sorted(c.items())) for nome, c in contagens.items()},
        "min_max": {nome: [min(c), max(c)] for nome, c in contagens.items()},
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    saida = {}
    for key in ("urca", "copacabana", "botafogo"):
        r = analisa(key, n)
        saida[key] = r
        print(f"\n{r['bairro']}: k={r['k']} de n={r['n_componente']}; distancia de corte {r['dist_corte']}; "
              f"{r['vagas_no_empate']} vagas para {r['empatados_na_dist_corte']} empatados; "
              f"{r['nucleos_distintos']} nucleos distintos em {n} sorteios")
        for nome, (lo, hi) in r["min_max"].items():
            print(f"  {nome:<26} artigo={r['valor_artigo'][nome]:>3}  sorteios: min={lo} max={hi}")
    os.makedirs(ri.OUT, exist_ok=True)
    with open(os.path.join(ri.OUT, "robustez_desempate.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
