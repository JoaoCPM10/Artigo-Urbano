"""
Sensibilidade da variavel geografica (C3) ao limiar de declividade e a distancia
da agua. Reusa o cache de altitudes e a agua do OSM de variavel_geografica.py.
Escreve output/variavel_geografica_sens.json.   Uso: python -m analises.variavel_geografica_sens
"""

from __future__ import annotations
import json
import os

import geopandas as gpd
import numpy as np
from shapely.geometry import shape, Point
from shapely.ops import unary_union

from nucleo import polygons as pg
from analises import variavel_geografica as vg
from nucleo.neighborhoods import NEIGHBORHOODS


def main():
    agua_u = unary_union(list(vg.linhas_agua(vg.agua_osm())))
    cache = json.load(open(vg.CACHE_ELEV, encoding="utf-8"))
    cj = json.load(open(os.path.join(vg.OUT, "service_artigo.json"), encoding="utf-8"))
    base = {}
    for key, cfg in NEIGHBORHOODS.items():
        poly = gpd.GeoSeries([shape(pg.fetch_bairro_polygon(cfg.display_name)["geometry"])],
                             crs="EPSG:4326").to_crs(vg.UTM).iloc[0].buffer(0)
        pts = vg.amostra_perimetro(poly)
        viz = []
        for p in pts:
            viz += [(p.x, p.y), (p.x + vg.DELTA_M, p.y), (p.x - vg.DELTA_M, p.y),
                    (p.x, p.y + vg.DELTA_M), (p.x, p.y - vg.DELTA_M)]
        ll = gpd.GeoSeries([Point(x, y) for x, y in viz], crs=vg.UTM).to_crs("EPSG:4326")
        z = np.array(vg.elevacoes([(g.y, g.x) for g in ll], cache), dtype=float).reshape(-1, 5)
        decl = np.sqrt(((z[:, 1] - z[:, 2]) / (2 * vg.DELTA_M)) ** 2 + ((z[:, 3] - z[:, 4]) / (2 * vg.DELTA_M)) ** 2)
        dist = np.array([agua_u.distance(p) for p in pts])
        base[key] = (decl, dist)
    chs = list(base)
    fl_nd = [cj[k]["nao_dirigido"]["ruas"] for k in chs]
    fl_d = [cj[k]["dirigido"]["ruas"] for k in chs]
    saida = []
    print("limiar  dist_agua | Spearman nd  dir | fracoes (agua+encosta) por bairro")
    for lim in (0.20, 0.30, 0.40):
        for da in (50, 100, 200):
            x = []
            for k in chs:
                decl, dist = base[k]
                a = dist <= da
                e = (~a) & (decl >= lim)
                x.append(float((a.sum() + e.sum()) / len(a)))
            r1, r2 = vg.spearman(x, fl_nd), vg.spearman(x, fl_d)
            saida.append({"limiar": lim, "dist_agua_m": da, "spearman_nd": round(r1, 3), "spearman_dir": round(r2, 3),
                          "fracoes": {k: round(v, 3) for k, v in zip(chs, x)}})
            print(f"{lim:5.2f} {da:6d} m | {r1:7.3f} {r2:6.3f} | " + " ".join(f"{v:.2f}" for v in x))
    json.dump(saida, open(os.path.join(vg.OUT, "variavel_geografica_sens.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("ordem dos bairros:", chs)


if __name__ == "__main__":
    main()
