"""
C3 (orientador), segunda parte: variavel geografica explicita. Para cada bairro,
fracao do perimetro do poligono oficial que e' (a) agua (a menos de 100 m da
linha de costa ou de um corpo d'agua do OSM) ou (b) encosta (declividade de
30% ou mais, da altimetria SRTM de 30 m), e o resto.

Dados baixados (so' coordenadas de pontos do perimetro vao para o servico):
  - Overpass API: natural=coastline e natural=water (linhas, "out geom"), cache
    em data/agua_osm_<hash>.json;
  - OpenTopoData (https://api.opentopodata.org, conjunto srtm30m): altitudes,
    cache em data/elevacao_opentopodata.json.

Declividade em cada ponto do perimetro (amostrado a cada 50 m) pelo gradiente
central com passo de 45 m em x e em y (UTM 23S). Pontos de agua nao entram na
classe encosta. A SRTM e' um modelo de superficie (inclui copas e predios) e tem
30 m de resolucao: a declividade e' aproximada.

Escreve output/variavel_geografica.json.   Uso: python -m analises.variavel_geografica
"""

from __future__ import annotations
import hashlib
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import geopandas as gpd
import numpy as np
from shapely.geometry import shape, LineString, MultiLineString, Point
from shapely.ops import unary_union

from nucleo import polygons as pg
from nucleo.neighborhoods import NEIGHBORHOODS
from caminhos import DATA, OUT, ROOT

UTM = "EPSG:31983"
PASSO_M = 50.0
DELTA_M = 45.0
LIMIAR_DECL = 0.30       # 30%
DIST_AGUA_M = 100.0
BBOX = "-23.040,-43.310,-22.900,-43.145"     # S,W,N,E: cobre os nove bairros
MIRRORS = ("https://overpass-api.de/api/interpreter",
           "https://lz4.overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter")
UA = "grafos-academic/1.0 (trabalho academico)"


def agua_osm():
    h = hashlib.md5(BBOX.encode()).hexdigest()[:8]
    cache = os.path.join(DATA, f"agua_osm_{h}.json")
    if os.path.exists(cache):
        return json.load(open(cache, encoding="utf-8"))
    q = (f'[out:json][timeout:180];(way["natural"="coastline"]({BBOX});way["natural"="water"]({BBOX});'
         f'relation["natural"="water"]({BBOX}););out geom;')
    data = urllib.parse.urlencode({"data": q}).encode()
    ultimo = None
    for tentativa in range(3):
        for host in MIRRORS:
            try:
                req = urllib.request.Request(host, data=data, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=240) as r:
                    raw = json.loads(r.read())
                json.dump(raw, open(cache, "w", encoding="utf-8"))
                return raw
            except Exception as exc:
                ultimo = exc
        time.sleep(30)
    raise ultimo


def linhas_agua(raw):
    linhas = []
    for el in raw["elements"]:
        geoms = []
        if el["type"] == "way" and "geometry" in el:
            geoms.append(el["geometry"])
        elif el["type"] == "relation":
            for m in el.get("members", []):
                if m.get("geometry"):
                    geoms.append(m["geometry"])
        for g in geoms:
            if len(g) >= 2:
                linhas.append(LineString([(p["lon"], p["lat"]) for p in g]))
    return gpd.GeoSeries(linhas, crs="EPSG:4326").to_crs(UTM)


CACHE_ELEV = os.path.join(DATA, "elevacao_opentopodata.json")


def elevacoes(pontos_latlon, cache):
    """Altitude (m) de cada (lat, lon); consulta so' o que falta, 100 pontos por chamada."""
    chaves = [f"{la:.5f},{lo:.5f}" for la, lo in pontos_latlon]
    falta = sorted({k for k in chaves if k not in cache})
    for i in range(0, len(falta), 100):
        lote = falta[i:i + 100]
        url = "https://api.opentopodata.org/v1/srtm30m?locations=" + "|".join(lote)
        for tentativa in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    resp = json.loads(r.read())
                for k, res in zip(lote, resp["results"]):
                    cache[k] = res["elevation"]
                break
            except Exception as exc:
                time.sleep(3 * (tentativa + 1))
        else:
            raise RuntimeError("OpenTopoData falhou")
        time.sleep(1.2)
        if (i // 100) % 10 == 0:
            json.dump(cache, open(CACHE_ELEV, "w", encoding="utf-8"))
    json.dump(cache, open(CACHE_ELEV, "w", encoding="utf-8"))
    return [cache[k] for k in chaves]


def amostra_perimetro(geom):
    pts = []
    fronteiras = geom.boundary
    partes = list(fronteiras.geoms) if hasattr(fronteiras, "geoms") else [fronteiras]
    for ln in partes:
        n = max(2, int(ln.length // PASSO_M))
        for i in range(n):
            pts.append(ln.interpolate(i * ln.length / n))
    return pts


def spearman(a, b):
    def ranks(x):
        o = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")


def main():
    agua = linhas_agua(agua_osm())
    agua_u = unary_union(list(agua))
    cache = json.load(open(CACHE_ELEV, encoding="utf-8")) if os.path.exists(CACHE_ELEV) else {}
    fluxos = {}
    cj = json.load(open(os.path.join(OUT, "service_artigo.json"), encoding="utf-8"))
    res = {}
    for key, cfg in NEIGHBORHOODS.items():
        poly = gpd.GeoSeries([shape(pg.fetch_bairro_polygon(cfg.display_name)["geometry"])],
                             crs="EPSG:4326").to_crs(UTM).iloc[0].buffer(0)
        pts = amostra_perimetro(poly)
        # pontos vizinhos para a declividade
        viz = []
        for p in pts:
            viz += [(p.x, p.y), (p.x + DELTA_M, p.y), (p.x - DELTA_M, p.y), (p.x, p.y + DELTA_M), (p.x, p.y - DELTA_M)]
        ll = gpd.GeoSeries([Point(x, y) for x, y in viz], crs=UTM).to_crs("EPSG:4326")
        z = elevacoes([(g.y, g.x) for g in ll], cache)
        z = np.array(z, dtype=float).reshape(-1, 5)
        decl = np.sqrt(((z[:, 1] - z[:, 2]) / (2 * DELTA_M)) ** 2 + ((z[:, 3] - z[:, 4]) / (2 * DELTA_M)) ** 2)
        e_agua = np.array([agua_u.distance(p) <= DIST_AGUA_M for p in pts])
        e_enc = (~e_agua) & (decl >= LIMIAR_DECL)
        n = len(pts)
        fa, fe = e_agua.sum() / n, e_enc.sum() / n
        res[key] = {"bairro": cfg.display_name, "perimetro_km": round(poly.length / 1e3, 1), "pontos": n,
                    "frac_agua": round(float(fa), 3), "frac_encosta": round(float(fe), 3),
                    "frac_agua_ou_encosta": round(float(fa + fe), 3),
                    "declividade_mediana_perimetro_pct": round(float(np.median(decl[~e_agua])) * 100, 1) if (~e_agua).any() else None,
                    "fluxo_nd": cj[key]["nao_dirigido"]["ruas"], "fluxo_dir": cj[key]["dirigido"]["ruas"]}
        r = res[key]
        print(f"{r['bairro']:18s} perim={r['perimetro_km']:5.1f} km agua={r['frac_agua']:.2f} encosta={r['frac_encosta']:.2f} "
              f"soma={r['frac_agua_ou_encosta']:.2f} fluxo nd/dir={r['fluxo_nd']}/{r['fluxo_dir']}", flush=True)
    chs = list(res)
    x = [res[k]["frac_agua_ou_encosta"] for k in chs]
    out = {"bairros": res,
           "spearman_fluxo_nd": round(spearman(x, [res[k]["fluxo_nd"] for k in chs]), 3),
           "spearman_fluxo_dir": round(spearman(x, [res[k]["fluxo_dir"] for k in chs]), 3),
           "parametros": {"passo_m": PASSO_M, "delta_m": DELTA_M, "limiar_declividade": LIMIAR_DECL,
                          "dist_agua_m": DIST_AGUA_M, "dem": "SRTM 30 m (OpenTopoData)"}}
    print("Spearman (agua ou encosta x fluxo): nd", out["spearman_fluxo_nd"], "dir", out["spearman_fluxo_dir"])
    json.dump(out, open(os.path.join(OUT, "variavel_geografica.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
