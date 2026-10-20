"""
CONECTIVIDADE EXTERNA: as saidas do bairro levam a caminhos independentes ate' o
resto da cidade, ou so' alcancam a fronteira administrativa? (Secao 4.6 do artigo)

O fluxo de acesso da Tabela 3 termina nas portas administrativas. Duas ruas
podem cruzar a fronteira e, logo depois, convergir para o mesmo corredor. Aqui
o mesmo nucleo de origem (f = 0,2, o do artigo) e' ligado a destinos situados na
borda externa de uma rede ampliada em R = 500 m, 1 km e 2 km alem do poligono
oficial, com capacidade unitaria por rua e respeitando o sentido das vias.

Destino externo (variante principal, "scc"): interseccao do anel (a ate' R m do
poligono) com uma rua que sai do anel para um no que pertence ao componente
fortemente conexo gigante da rede completa (R + 400 m). So' conta como destino
o que de fato continua para a cidade; becos sem saida e ilhas ficam de fora.
Variante "qualquer": qualquer interseccao da borda com uma rua que sai (a
definicao das portas administrativas do artigo, so' que na borda externa).

Para cada raio e para o poligono (R = 0), por ruas dirigido (principal), ruas
nao dirigido e interseccoes dirigido:
  - fluxo maximo (Edmonds-Karp, o mesmo de maxflow.py);
  - corte mais proximo da origem e mais proximo do destino, classificados em
    interno / fronteira / externo;
  - ruas EXTERNAS cujo fechamento sozinho reduz o fluxo (vulnerabilidade
    externa: varias saidas existem, mas dependem de um corredor comum).

Verificacoes: com R = 0 e destino "qualquer" o fluxo reproduz a Tabela 3; o fluxo
nunca supera o do poligono (todo caminho ate' o anel cruza a fronteira);
conferencia com o networkx (--verifica).

Escreve output/conectividade_externa.{json,csv}.
Uso:  py conectividade_externa.py [--verifica] [--bairros urca,copacabana]
"""

from __future__ import annotations
import csv
import json
import os
import sys
import time
from collections import deque

import maxflow as mf
import polygons as pg
import ruas_vs_intersecoes as rv
from neighborhoods import NEIGHBORHOODS
from network import load_network
from osm_loader import expand_bbox, load_neighborhood

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
RAIOS_M = (500, 1000, 2000)
MARGEM_M = 400            # alem de R, so' para decidir se a rua que sai continua
INF = float("inf")
SS, TT, BIG = rv.SS, rv.TT, rv.BIG


# ---------------------------------------------------------------------------
# Componentes (Kosaraju iterativo; o connectivity.py usa BFS por componente,
# que e' quadratico em redes com milhares de nos de grau pequeno)
# ---------------------------------------------------------------------------
def scc_gigante(G) -> set:
    nos = G.nodes()
    visto, ordem = set(), []
    for s in nos:
        if s in visto:
            continue
        visto.add(s)
        pilha = [(s, iter(G.adj[s]))]
        while pilha:
            u, it = pilha[-1]
            for e in it:
                if e.v not in visto:
                    visto.add(e.v)
                    pilha.append((e.v, iter(G.adj[e.v])))
                    break
            else:
                ordem.append(u)
                pilha.pop()
    melhor, atribuido = set(), set()
    for s in reversed(ordem):
        if s in atribuido:
            continue
        comp, pilha = {s}, [s]
        atribuido.add(s)
        while pilha:
            u = pilha.pop()
            for e in G.radj[u]:
                if e.u not in atribuido:
                    atribuido.add(e.u)
                    comp.add(e.u)
                    pilha.append(e.u)
        if len(comp) > len(melhor):
            melhor = comp
    return melhor


def componente_gigante_nao_dirigida(G, arestas) -> set:
    adj = {u: [] for u in G.nodes()}
    for e in arestas:
        adj[e[0]].append(e[1]); adj[e[1]].append(e[0])
    visto, melhor = set(), set()
    for s in adj:
        if s in visto:
            continue
        comp, fila = {s}, deque([s])
        visto.add(s)
        while fila:
            u = fila.popleft()
            for w in adj[u]:
                if w not in visto:
                    visto.add(w); comp.add(w); fila.append(w)
        if len(comp) > len(melhor):
            melhor = comp
    return melhor


# ---------------------------------------------------------------------------
# Fluxo
# ---------------------------------------------------------------------------
def _classe(u, v, dist) -> str:
    n_in = (dist[u] == 0) + (dist[v] == 0)
    return {2: "interno", 1: "fronteira", 0: "externo"}[n_in]


def _resolve(nos, cap, src, dest, dividido):
    """Fluxo maximo super-fonte -> src, dest -> super-sumidouro. Devolve
    (fluxo, fluxo por arco, capacidades completas)."""
    cap = dict(cap)
    for u in src:
        cap[(SS, (u, 0) if dividido else u)] = BIG
    for g in dest:
        cap[((g, 1) if dividido else g, TT)] = BIG
    fmax, flow, _, cut = mf.edmonds_karp(nos + [SS, TT], cap, SS, TT)
    return int(fmax), flow, cut, cap


def _so_reais(cut):
    return [(a, b) for (a, b) in cut if a not in (SS, TT) and b not in (SS, TT)]


def corte_junto_ao_destino(nos, cap_completa):
    """Corte minimo mais proximo do destino: Edmonds-Karp na rede revertida."""
    rev = {(b, a): c for (a, b), c in cap_completa.items()}
    _, _, _, cut = mf.edmonds_karp(nos + [SS, TT], rev, TT, SS)
    return [(b, a) for (a, b) in _so_reais(cut)]


def ruas_do_corte(cut, dividido):
    """Cortes por ruas -> pares de nos; por interseccoes -> nos do arco dividido."""
    if dividido:
        return sorted({a[0] for (a, b) in cut if a[0] == b[0]})
    return [tuple(e) for e in cut]


def baixa(nome, bbox, tentativas=6, espera_s=90):
    """load_neighborhood com novas tentativas: as consultas de 2 km sao pesadas
    e as copias da Overpass respondem 500/504 de vez em quando."""
    for i in range(tentativas):
        try:
            return load_neighborhood(nome, bbox)
        except Exception as exc:
            if i == tentativas - 1:
                raise
            print(f"  Overpass falhou ({exc}); nova tentativa em {espera_s} s", flush=True)
            time.sleep(espera_s)


class Rede:
    """Rede de um raio R: nos do anel, arestas fisicas, destinos."""

    def __init__(self, G, arestas, dist, R, src, giant_scc, giant_nd):
        self.G, self.R, self.dist, self.src = G, R, dist, set(src)
        self.ring = {n for n in G.nodes() if dist.get(n, INF) <= R}
        self.edges_in = [e for e in arestas if e[0] in self.ring and e[1] in self.ring]
        self.giant_scc, self.giant_nd = giant_scc, giant_nd
        # destinos por variante e por modo (dirigido ou nao)
        d = {"scc": {"dir": set(), "nd": set()}, "qualquer": {"dir": set(), "nd": set()}}
        for u in self.ring:
            for e in G.adj[u]:                          # arco u -> w saindo do anel
                if e.v not in self.ring and dist.get(e.v, INF) < INF:
                    d["qualquer"]["dir"].add(u)
                    if e.v in giant_scc:
                        d["scc"]["dir"].add(u)
        for e in arestas:                               # rua entre anel e fora, sem sentido
            for a, b in ((e[0], e[1]), (e[1], e[0])):
                if a in self.ring and b not in self.ring and dist.get(b, INF) < INF:
                    d["qualquer"]["nd"].add(a)
                    if b in giant_nd:
                        d["scc"]["nd"].add(a)
        self.dest = d

    def fluxo(self, modo, filtro, detalhes=False):
        """modo: ruas_dir | ruas_nd | int_dir. filtro: scc | qualquer."""
        dirigido = modo.endswith("_dir")
        dest = self.dest[filtro]["dir" if dirigido else "nd"]
        src = self.src
        dividido = modo.startswith("int")
        if dividido:
            nos = [(v, s) for v in self.ring for s in (0, 1)]
            cap = rv._rede_intersecoes(self.ring, self.edges_in, self.G, src, dest, dirigido)
        else:
            nos = list(self.ring)
            cap = rv._rede_ruas(self.ring, self.edges_in, self.G, dirigido)
        f, flow, cut, cap_c = _resolve(nos, cap, src, dest, dividido)
        if not detalhes:
            return f
        return {"fluxo": f, "flow": flow, "cut_origem": _so_reais(cut),
                "nos": nos, "cap": cap, "cap_completa": cap_c, "dest": dest,
                "dividido": dividido}


def critica_externas(rede, r) -> dict:
    """Ruas cujo fechamento (os dois sentidos e todas as paralelas) reduz o
    fluxo por ruas dirigido. Candidatas: ruas com fluxo positivo no fluxo
    maximo encontrado (so' elas podem reduzi-lo)."""
    f0, nos, cap = r["fluxo"], r["nos"], r["cap"]
    candidatas = {frozenset(k) for k in r["flow"]
                  if k[0] not in (SS, TT) and k[1] not in (SS, TT) and k[0] != k[1]}
    criticas = {"interno": [], "fronteira": [], "externo": []}
    for par in candidatas:
        cap2 = {k: v for k, v in cap.items() if frozenset(k) != par}
        f, _, _, _ = _resolve(nos, cap2, rede.src, r["dest"], False)
        if f < f0:
            u, v = tuple(par)
            criticas[_classe(u, v, rede.dist)].append((u, v, f0 - f))
    return criticas


def monta_rede(key: str, R: int, src=None):
    """Rede de raio R (so' a rede, sem fluxos). Devolve (rede, big, dist, src)."""
    cfg = NEIGHBORHOODS[key]
    if src is None:
        ref = rv.analisa(key)
        src = ref["_entrada"][3]
    data, bbox = load_network(cfg)
    poly = pg.fetch_bairro_polygon(cfg.display_name)
    nome = f"{key}_buffer{MARGEM_M}" if R == 0 else f"{key}_ext{R}"
    big = baixa(nome, expand_bbox(bbox, R + MARGEM_M))
    G = big["graph"]
    dist = pg.distancias_ao_poligono_m(big["latlon"], poly, teto_m=R + MARGEM_M + 1)
    arestas = big["undirected_edges"]
    rede = Rede(G, arestas, dist, R, src, scc_gigante(G),
                componente_gigante_nao_dirigida(G, arestas))
    return rede, big, dist, set(src)


def analisa_bairro(key: str, raios=(0,) + RAIOS_M) -> tuple[dict, dict]:
    cfg = NEIGHBORHOODS[key]
    ref = rv.analisa(key)                       # Tabela 3 (portas administrativas)
    uset, edges_in0, G0, src, gw = ref.pop("_entrada")
    data, bbox = load_network(cfg)
    poly = pg.fetch_bairro_polygon(cfg.display_name)
    res = {"bairro": cfg.display_name, "origem": len(src), "referencia_artigo": {
        "portas": ref["portas"],
        "ruas_nd": ref["nao_dirigido"]["ruas"], "ruas_dir": ref["dirigido"]["ruas"],
        "int_nd": ref["nao_dirigido"]["intersecoes"], "int_dir": ref["dirigido"]["intersecoes"]},
        "raios": {}}
    objetos = {}
    for R in raios:
        nome = f"{key}_buffer{MARGEM_M}" if R == 0 else f"{key}_ext{R}"
        big = baixa(nome, expand_bbox(bbox, R + MARGEM_M))
        G = big["graph"]
        dist = pg.distancias_ao_poligono_m(big["latlon"], poly, teto_m=R + MARGEM_M + 1)
        faltam = [n for n in src if n not in G.coords or dist.get(n, INF) != 0]
        assert not faltam, f"{key} R={R}: {len(faltam)} nos do nucleo fora da rede expandida"
        arestas = big["undirected_edges"]
        rede = Rede(G, arestas, dist, R, src, scc_gigante(G),
                    componente_gigante_nao_dirigida(G, arestas))
        item = {"R_m": R, "nos_anel": len(rede.ring), "ruas_anel": len(rede.edges_in),
                "destinos": {f: {m: len(rede.dest[f][m]) for m in ("dir", "nd")}
                             for f in ("scc", "qualquer")}, "fluxo": {}}
        for filtro in ("scc", "qualquer"):
            item["fluxo"][filtro] = {m: rede.fluxo(m, filtro)
                                     for m in ("ruas_dir", "ruas_nd", "int_dir")}
        # cortes e ruas criticas: variante principal, por ruas dirigido
        r = rede.fluxo("ruas_dir", "scc", detalhes=True)
        co = _so_reais(r["cut_origem"])
        cd = corte_junto_ao_destino(r["nos"], r["cap_completa"])
        cont = lambda cut: {c: sum(1 for (u, v) in cut if _classe(u, v, dist) == c)
                            for c in ("interno", "fronteira", "externo")}
        item["corte_perto_origem"] = cont(co)
        item["corte_perto_destino"] = cont(cd)
        crit = critica_externas(rede, r)
        item["ruas_criticas"] = {c: len(v) for c, v in crit.items()}
        ll = big["latlon"]
        item["ruas_criticas_externas"] = [
            {"coords": [[round(ll[u][0], 5), round(ll[u][1], 5)],
                        [round(ll[v][0], 5), round(ll[v][1], 5)]], "queda": q}
            for (u, v, q) in crit["externo"]][:40]
        res["raios"][str(R)] = item
        objetos[R] = {"big": big, "rede": rede, "corte_origem": co, "corte_destino": cd,
                      "criticas": crit, "dest": r["dest"]}
        f = item["fluxo"]
        print(f"{cfg.display_name:11s} R={R:4d} anel={len(rede.ring):5d} nos  "
              f"dest(scc/qualquer)={item['destinos']['scc']['dir']:3d}/{item['destinos']['qualquer']['dir']:3d}  "
              f"ruas dir={f['scc']['ruas_dir']:2d}/{f['qualquer']['ruas_dir']:2d}  "
              f"nd={f['scc']['ruas_nd']:2d}/{f['qualquer']['ruas_nd']:2d}  "
              f"int dir={f['scc']['int_dir']:2d}/{f['qualquer']['int_dir']:2d}  "
              f"criticas(int/front/ext)={item['ruas_criticas']['interno']}/"
              f"{item['ruas_criticas']['fronteira']}/{item['ruas_criticas']['externo']}", flush=True)
    if tuple(raios) == (0,) + RAIOS_M:
        checa_invariantes(res)
    return res, objetos


def checa_invariantes(res) -> None:
    """Regressao e limite superior (ver o docstring do modulo)."""
    ref, r0 = res["referencia_artigo"], res["raios"]["0"]["fluxo"]["qualquer"]
    # regressao: a rede ampliada em R=0 pode diferir do artigo so' na contracao de
    # grau 2 junto ao envelope antigo; registramos a diferenca em vez de esconde-la
    res["regressao_R0"] = {m: {"artigo": ref[m], "rede_ampliada": r0[m]}
                          for m in ("ruas_nd", "ruas_dir", "int_dir")}
    for m in ("ruas_dir", "ruas_nd", "int_dir"):
        base = r0[m]
        for R in map(str, RAIOS_M):
            for filtro in ("qualquer", "scc"):
                v = res["raios"][R]["fluxo"][filtro][m]
                assert v <= base, (f"{res['bairro']}: fluxo({R} m, {filtro}, {m}) = {v} "
                                   f"supera o do poligono ({base})")


# ---------------------------------------------------------------------------
# Conferencia com o networkx
# ---------------------------------------------------------------------------
def verifica(res_obj) -> None:
    import networkx as nx
    for R, o in res_obj.items():
        if R not in (0, 1000):
            continue
        rede, G = o["rede"], o["rede"].G
        src = rede.src
        for filtro in ("scc", "qualquer"):
            for dirigido in (True, False):
                dest = rede.dest[filtro]["dir" if dirigido else "nd"]
                D = nx.DiGraph()
                D.add_nodes_from(rede.ring)
                if dirigido:
                    for e in G.edges:
                        if e.u in rede.ring and e.v in rede.ring:
                            c = D[e.u][e.v]["capacity"] + 1 if D.has_edge(e.u, e.v) else 1
                            D.add_edge(e.u, e.v, capacity=c)
                else:
                    for e in rede.edges_in:
                        for a, b in ((e[0], e[1]), (e[1], e[0])):
                            c = D[a][b]["capacity"] + 1 if D.has_edge(a, b) else 1
                            D.add_edge(a, b, capacity=c)
                for u in src:
                    D.add_edge(SS, u)
                for g in dest:
                    D.add_edge(g, TT)
                esperado = nx.maximum_flow_value(D, SS, TT)
                obtido = rede.fluxo("ruas_dir" if dirigido else "ruas_nd", filtro)
                assert esperado == obtido, f"networkx R={R} {filtro} dir={dirigido}: {esperado} != {obtido}"
        # componente gigante fortemente conexa
        Dg = nx.DiGraph()
        Dg.add_nodes_from(G.nodes())
        Dg.add_edges_from((e.u, e.v) for e in G.edges)
        gnx = max(nx.strongly_connected_components(Dg), key=len)
        assert gnx == rede.giant_scc, f"networkx R={R}: componente gigante difere"


def escreve(resultados) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "conectividade_externa.json"), "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=2)
    linhas = []
    for k, r in resultados.items():
        for R, it in r["raios"].items():
            for filtro in ("scc", "qualquer"):
                for modo, v in it["fluxo"][filtro].items():
                    linhas.append({"bairro": r["bairro"], "R_m": R, "destino": filtro,
                                   "modo": modo, "fluxo": v,
                                   "n_destinos": it["destinos"][filtro]["nd" if modo == "ruas_nd" else "dir"],
                                   "nos_anel": it["nos_anel"]})
    with open(os.path.join(OUT, "conectividade_externa.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader(); w.writerows(linhas)


def main():
    chaves = ["urca", "copacabana", "botafogo"]
    if "--bairros" in sys.argv:
        chaves = sys.argv[sys.argv.index("--bairros") + 1].split(",")
    resultados, objetos = {}, {}
    for k in chaves:
        resultados[k], objetos[k] = analisa_bairro(k)
        if "--verifica" in sys.argv:
            verifica(objetos[k])
            print(f"{k}: networkx confere (fluxos e componente gigante)")
    escreve(resultados)
    print("\nRegressao R=0 (artigo | rede ampliada):")
    for k, r in resultados.items():
        print(" ", r["bairro"], r["regressao_R0"])
    return resultados, objetos


if __name__ == "__main__":
    main()
