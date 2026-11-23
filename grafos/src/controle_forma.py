"""
C3 (orientador): o controle de tamanho nao isola a geografia. Pedacos sorteados
dentro de uma malha tem portas em todo o perimetro por construcao; o controle
mostra que recortes de malha sao porosos, mas nao que a diferenca vem da
geografia e nao da forma da fronteira.

Este controle repete o fluxo de acesso sobre pedacos das malhas abertas
(Copacabana e Botafogo) delimitados pela FORMA do poligono oficial do bairro de
referencia (Urca ou Leme): copia do poligono, girada ao acaso (e espelhada ao
acaso), com o centroide em um ponto sorteado do bairro e reduzida (escala
uniforme, forma preservada) ate' que a maior parte conexa dentro dela tenha o
numero de interseccoes do bairro de referencia (+-10%). Portas do pedaco =
interseccoes com uma rua para fora dele, na rede ampliada (1 km).

Escreve output/controle_forma_<referencia>.json.
Uso:  py controle_forma.py urca [N_POSICOES]
"""

from __future__ import annotations
import json
import os
import random
import statistics as st
import sys
from collections import deque

import geopandas as gpd
import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import shape

import conectividade_externa as ce
import maxflow as mf
import polygons as pg
import nulo_fluxo as nf
from neighborhoods import NEIGHBORHOODS

UTM = "EPSG:31983"
SEED = 11
OUT = nf.OUT


def poligono_utm(nome):
    f = pg.fetch_bairro_polygon(nome)
    return gpd.GeoSeries([shape(f["geometry"])], crs="EPSG:4326").to_crs(UTM).iloc[0].buffer(0)


class Universo:
    """Rede ampliada (1 km) de uma malha aberta, com coordenadas em UTM."""

    def __init__(self, key):
        rede, big, dist, _ = ce.monta_rede(key, 1000)
        ll = big["latlon"]
        ring = [n for n in rede.ring if n in ll]
        pts = gpd.GeoSeries(gpd.points_from_xy([ll[n][1] for n in ring], [ll[n][0] for n in ring]),
                            crs="EPSG:4326").to_crs(UTM)
        self.nos = ring
        self.xy = np.array([(p.x, p.y) for p in pts])
        idx = {n: i for i, n in enumerate(self.nos)}
        self.adj = {n: set() for n in self.nos}
        self.edges = []
        for e in big["undirected_edges"]:
            if e[0] in idx and e[1] in idx and e[0] != e[1]:
                self.adj[e[0]].add(e[1]); self.adj[e[1]].add(e[0])
                self.edges.append((e[0], e[1]))
        self.poly = poligono_utm(NEIGHBORHOODS[key].display_name)
        self.dentro_bairro = [n for n in self.nos if dist[n] == 0]

    def maior_conexa(self, S):
        S = set(S)
        vis, melhor = set(), set()
        for s in S:
            if s in vis:
                continue
            comp, q = {s}, deque([s])
            vis.add(s)
            while q:
                u = q.popleft()
                for v in self.adj[u]:
                    if v in S and v not in vis:
                        vis.add(v); comp.add(v); q.append(v)
            if len(comp) > len(melhor):
                melhor = comp
        return melhor

    def pedaco(self, poligono):
        m = shapely.contains_xy(poligono, self.xy[:, 0], self.xy[:, 1])
        S = [self.nos[i] for i in np.nonzero(m)[0]]
        return self.maior_conexa(S) if S else set()

    def fluxo(self, S):
        gw = {u for u in S if any(v not in S for v in self.adj[u])}
        r = mf.gateway_access_flow(list(S), self.edges, gw, frac=0.2)
        return r["fluxo"], len(gw)


def ajusta_escala(univ, forma, centro, alvo, tol=0.10):
    """Escala (em torno de `centro`) em que a maior parte conexa tem ~alvo nos."""
    lo, hi = 0.02, 1.0
    for _ in range(14):
        meio = (lo * hi) ** 0.5
        S = univ.pedaco(affinity.scale(forma, meio, meio, origin=centro))
        n = len(S)
        if abs(n - alvo) <= tol * alvo:
            return meio, S
        if n < alvo:
            lo = meio
        else:
            hi = meio
    return None, None


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "urca"
    n_pos = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 600
    fontes = ("copacabana", "botafogo")
    sufixo = ""
    if "--fontes" in sys.argv:
        fontes = tuple(sys.argv[sys.argv.index("--fontes") + 1].split(","))
        sufixo = "_fontes"
    rede_ref = nf.Rede(ref)
    alvo = len(rede_ref.inside)
    f_ref, g_ref = rede_ref.fluxo(rede_ref.inside)
    poly_ref = poligono_utm(NEIGHBORHOODS[ref].display_name)
    c_ref = poly_ref.centroid
    res = {"referencia": {"bairro": ref, "interseccoes": alvo, "fluxo": f_ref, "portas": g_ref,
                          "area_km2": round(poly_ref.area / 1e6, 2), "perimetro_km": round(poly_ref.length / 1e3, 1)},
           "pedacos": {}}
    rng = random.Random(SEED)
    for key in fontes:
        univ = Universo(key)
        minx, miny, maxx, maxy = univ.poly.bounds
        fl, gws, esc = [], [], []
        tent = 0
        while len(fl) < n_pos and tent < 40 * n_pos:
            tent += 1
            p = shapely.geometry.Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
            if not univ.poly.contains(p):
                continue
            forma = affinity.rotate(poly_ref, rng.uniform(0, 360), origin=c_ref)
            if rng.random() < 0.5:
                forma = affinity.scale(forma, xfact=-1, yfact=1, origin=c_ref)
            forma = affinity.translate(forma, p.x - c_ref.x, p.y - c_ref.y)
            s, S = ajusta_escala(univ, forma, p, alvo)
            if S is None:
                continue
            f, g = univ.fluxo(S)
            fl.append(f); gws.append(g); esc.append(s)
        res["pedacos"][key] = {
            "n": len(fl), "tentativas": tent,
            "fluxo": nf.resumo(fl), "portas": nf.resumo(gws), "valores_fluxo": fl,
            "escala_mediana": round(st.median(esc), 3),
            "n_fluxo_le_ref": sum(x <= f_ref for x in fl),
            "frac_fluxo_le_ref": round(sum(x <= f_ref for x in fl) / len(fl), 4) if fl else None,
        }
        b = res["pedacos"][key]
        print(key, "n", b["n"], "fluxo", b["fluxo"], "portas", b["portas"], "escala med", b["escala_mediana"],
              f"<= {f_ref}:", b["n_fluxo_le_ref"], flush=True)
    with open(os.path.join(OUT, f"controle_forma_{ref}{sufixo}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    print("referencia:", res["referencia"])


if __name__ == "__main__":
    main()
