"""
Populacao atras do corte (Secao 4.3 do artigo): quantas pessoas ficam do lado da origem do corte de acesso?

O fluxo de acesso mede o acesso do nucleo do bairro, mas para o planejamento
importa a populacao que depende desse acesso. Aqui a populacao residente do
Censo 2022 (IBGE, malha de setores censitarios com atributos, variavel V0001 =
total de pessoas) e' atribuida as interseccoes da rede e somada no lado da
origem do corte minimo (as interseccoes que o corte separa das portas).

Metodo, por bairro:
  1. cada setor que cruza o poligono oficial (Data.Rio/IPP) e' recortado por ele; a
     populacao do setor e' repartida pela fracao de area dentro do poligono
     (supoe densidade uniforme no setor);
  2. a populacao de cada recorte vai para a interseccao mais proxima do ponto
     representativo do recorte (distancias em UTM 23S, EPSG:31983);
  3. regiao de origem e corte minimo exatamente como no artigo (f = 0,2, sem o
     sentido das vias, margem de 400 m); o lado da origem e' o conjunto de
     interseccoes alcancadas a partir do nucleo sem usar as ruas do corte;
  4. para os bairros com cortes de uma rua, o lado da origem de cada corte.

Limitacoes: so' moradores (nao conta trabalhadores nem visitantes); a atribuicao
pela interseccao mais proxima e' aproximada; os limites de bairro do IBGE e do
Data.Rio podem diferir.

Le grafos/data/ibge_censo2022_rj/RJ_setores_CD2022.gpkg (dados baixados, nao
executaveis). Escreve output/populacao_corte.json.
Uso:  python -m analises.populacao_atras_do_corte
"""

from __future__ import annotations

import json
import os
import sys
from collections import deque

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, shape

from analises.localiza_corte import cortes_de_uma_rua
from caminhos import OUT, ROOT
from nucleo import connectivity as cc
from nucleo import maxflow as mf
from nucleo import polygons as pg
from nucleo.neighborhoods import NEIGHBORHOODS
from nucleo.network import gateway_nodes, load_network

GPKG = os.path.join(ROOT, "data", "ibge_censo2022_rj", "RJ_setores_CD2022.gpkg")
UTM = "EPSG:31983"
FRAC = 0.2


def populacao_por_no(key, data, poly_feature, setores_utm, no_xy):
    """Dict no -> pessoas (float), pela repartição por area e no mais proximo."""
    geom = gpd.GeoSeries([shape(poly_feature["geometry"])], crs="EPSG:4326").to_crs(UTM).iloc[0]
    geom = geom.buffer(0)
    nos = list(no_xy)
    xy = np.array([no_xy[n] for n in nos])
    pop = {n: 0.0 for n in nos}
    total = 0.0
    for _, s in setores_utm.iterrows():
        g = s.geometry.buffer(0)
        if not g.intersects(geom):
            continue
        parte = g.intersection(geom)
        if parte.is_empty or g.area == 0:
            continue
        p = float(s["v0001"] or 0) * parte.area / g.area
        if p <= 0:
            continue
        pt = parte.representative_point()
        d = (xy[:, 0] - pt.x) ** 2 + (xy[:, 1] - pt.y) ** 2
        pop[nos[int(np.argmin(d))]] += p
        total += p
    return pop, total


def lado_origem(adj, src, cortadas):
    """Nos alcancados a partir de src sem usar as ruas (pares nao ordenados) em `cortadas`."""
    vis = set(src)
    q = deque(src)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in vis and frozenset((u, v)) not in cortadas:
                vis.add(v)
                q.append(v)
    return vis


def analisa(key, setores_all):
    cfg = NEIGHBORHOODS[key]
    data, bbox = load_network(cfg)
    G = data["graph"]
    ue = data["undirected_edges"]
    uset = set(max(cc.connected_components(G.nodes(), [(e[0], e[1]) for e in ue]), key=len))
    gw = gateway_nodes(cfg, data, bbox, uset)
    edges_in = [e for e in ue if e[0] in uset and e[1] in uset]
    adj = {u: set() for u in uset}
    adj_i = {u: [] for u in uset}
    for i, e in enumerate(edges_in):
        adj[e[0]].add(e[1])
        adj[e[1]].add(e[0])
        adj_i[e[0]].append((e[1], i))
        adj_i[e[1]].append((e[0], i))
    r = mf.gateway_access_flow(list(uset), ue, gw, frac=FRAC, details=True)
    src = set(r["origem"])
    cortadas = {frozenset(c) for c in r["corte_arestas"]}
    lado = lado_origem(adj, src, cortadas)

    poly = pg.fetch_bairro_polygon(cfg.display_name)
    ll = data["latlon"]
    nos = sorted(uset)
    pts = gpd.GeoSeries([Point(ll[n][1], ll[n][0]) for n in nos], crs="EPSG:4326").to_crs(UTM)
    no_xy = {n: (p.x, p.y) for n, p in zip(nos, pts)}

    minx, miny, maxx, maxy = (
        pg.polygon_bbox(poly).split(",")[1],
        pg.polygon_bbox(poly).split(",")[0],
        pg.polygon_bbox(poly).split(",")[3],
        pg.polygon_bbox(poly).split(",")[2],
    )
    sub = setores_all.cx[float(minx) : float(maxx), float(miny) : float(maxy)].to_crs(UTM)
    pop, total = populacao_por_no(key, data, poly, sub, no_xy)

    ibge_bairro = float(
        setores_all.loc[
            (setores_all["NM_MUN"] == "Rio de Janeiro")
            & (setores_all["NM_BAIRRO"] == cfg.display_name),
            "v0001",
        ].sum()
    )
    res = {
        "bairro": cfg.display_name,
        "fluxo": r["fluxo"],
        "portas": len(gw),
        "nucleo_nos": len(src),
        "populacao_ibge_bairro": round(ibge_bairro),
        "populacao_alocada_no_poligono": round(total),
        "populacao_nucleo": round(sum(pop[n] for n in src)),
        "lado_origem_nos": len(lado),
        "populacao_lado_origem": round(sum(pop[n] for n in lado)),
        "pct_populacao_lado_origem": round(100 * sum(pop[n] for n in lado) / total, 1)
        if total
        else None,
        "pessoas_por_rota": round(sum(pop[n] for n in lado) / r["fluxo"]) if r["fluxo"] else None,
    }
    cortes1 = cortes_de_uma_rua(edges_in, adj_i_to_list(adj_i), src, gw)
    res["cortes_de_uma_rua"] = [
        {
            "comprimento_m": round(edges_in[i][2]),
            "nos_lado_origem": len(l),
            "populacao_lado_origem": round(sum(pop[n] for n in l)),
            "pct": round(100 * sum(pop[n] for n in l) / total, 1) if total else None,
        }
        for i, l in cortes1
    ]
    return res


def adj_i_to_list(adj_i):
    return adj_i


def main():
    chaves = [a for a in sys.argv[1:] if not a.startswith("--")] or list(NEIGHBORHOODS)
    setores = gpd.read_file(GPKG, engine="pyogrio") if False else gpd.read_file(GPKG)
    setores = setores.set_crs("EPSG:4674", allow_override=True)
    saida = {}
    print(
        f"{'bairro':18s} {'fluxo':>5s} {'IBGE':>8s} {'alocada':>8s} {'nucleo':>7s} {'lado':>6s} {'pop lado':>9s} {'%':>6s} {'pess/rota':>9s}"
    )
    for k in chaves:
        r = analisa(k, setores)
        saida[k] = r
        print(
            f"{r['bairro']:18s} {r['fluxo']:5d} {r['populacao_ibge_bairro']:8d} {r['populacao_alocada_no_poligono']:8d} "
            f"{r['populacao_nucleo']:7d} {r['lado_origem_nos']:6d} {r['populacao_lado_origem']:9d} "
            f"{r['pct_populacao_lado_origem']:6.1f} {r['pessoas_por_rota'] or 0:9d}  cortes1={r['cortes_de_uma_rua']}",
            flush=True,
        )
    with open(os.path.join(OUT, "populacao_corte.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
