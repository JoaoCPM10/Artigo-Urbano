"""
HIPOTESE: parte das "rotas ate' a fronteira" de um bairro termina em portas que
nao continuam para a cidade (a rua que sai leva a um beco, a uma encosta ou a um
trecho que so' volta ao bairro), e por isso o fluxo cai quando o destino passa
a ser a borda externa da rede ampliada (Tabela 4: Copacabana 8 -> 7 -> 6).

Teste, por bairro e por raio R, com o mesmo nucleo, ruas, dirigido:
  1. porta que CONTINUA: interseccao do poligono com uma rua u -> w que sai do
     bairro e de onde, por caminhos dirigidos que ficam FORA do poligono e a ate'
     R m dele, se alcanca algum destino externo;
  2. fluxo do nucleo ate' as portas que continuam, dentro do poligono;
  3. comparacao: fluxo nas portas (todas) >= fluxo nas portas que continuam
     >= fluxo ate' a borda externa (Tabela 4).
A primeira diferenca e' o efeito das portas sem continuacao; a segunda, a de
rotas que atravessam a fronteira por ruas distintas e convergem fora do bairro.

Escreve output/portas_sem_continuacao.json.
Uso:  py analisa_portas_sem_continuacao.py [urca,copacabana,botafogo]
"""

from __future__ import annotations
import json
import os
import sys
from collections import deque

import conectividade_externa as ce

OUT = ce.OUT
RAIOS = (500, 1000, 2000)


def continuacao(rede, dist, G) -> dict:
    """Para cada arco u -> w que sai do poligono (u dentro, w fora, w no anel),
    True se de w se alcanca um destino externo por nos fora do poligono."""
    destinos = rede.dest["scc"]["dir"]
    exterior = {n for n in rede.ring if dist[n] > 0}
    cache = {}

    def alcanca(w):
        if w in cache:
            return cache[w]
        visto, fila, ok = {w}, deque([w]), False
        while fila:
            x = fila.popleft()
            if x in destinos:
                ok = True
                break
            for e in G.adj[x]:
                if e.v in exterior and e.v not in visto:
                    visto.add(e.v); fila.append(e.v)
        cache[w] = ok
        return ok

    saidas = {}
    for u in rede.ring:
        if dist[u] != 0:
            continue
        for e in G.adj[u]:
            if e.v in exterior:
                saidas.setdefault(u, []).append((e.v, alcanca(e.v)))
    return saidas


def analisa(key: str) -> dict:
    rede0, big0, dist0, src = ce.monta_rede(key, 0)
    f_todas = rede0.fluxo("ruas_dir", "qualquer")
    res = {"bairro": key, "fluxo_portas_todas": f_todas, "raios": {}}
    for R in RAIOS:
        rede, big, dist, _ = ce.monta_rede(key, R, src)
        G = rede.G
        saidas = continuacao(rede, dist, G)
        continua = {u for u, ls in saidas.items() if any(ok for _, ok in ls)}
        sem = sorted(set(saidas) - continua)
        # fluxo do nucleo ate' as portas que continuam: so' o interior do poligono
        rede_i = ce.Rede(G, big["undirected_edges"], dist, 0, src, rede.giant_scc, rede.giant_nd)
        rede_i.dest["qualquer"]["dir"] = continua
        f_cont = rede_i.fluxo("ruas_dir", "qualquer")
        f_ext = rede.fluxo("ruas_dir", "scc")
        ll = big["latlon"]
        res["raios"][str(R)] = {
            "portas_dirigidas_com_saida": len(saidas), "portas_que_continuam": len(continua),
            "portas_sem_continuacao": [[round(ll[u][0], 5), round(ll[u][1], 5)] for u in sem],
            "fluxo_portas_que_continuam": f_cont, "fluxo_borda_externa": f_ext,
            "efeito_portas_sem_continuacao": f_todas - f_cont,
            "efeito_convergencia_externa": f_cont - f_ext}
        print(f"{key:11s} R={R:4d} portas={len(saidas):2d} continuam={len(continua):2d}  "
              f"fluxo: todas={f_todas} -> continuam={f_cont} -> borda externa={f_ext}", flush=True)
        assert f_ext <= f_cont <= f_todas, "ordem esperada violada"
    return res


def main():
    chaves = sys.argv[1].split(",") if len(sys.argv) > 1 else ["copacabana", "urca", "botafogo"]
    resultados = {k: analisa(k) for k in chaves}
    with open(os.path.join(OUT, "portas_sem_continuacao.json"), "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
