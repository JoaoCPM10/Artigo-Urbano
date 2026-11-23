"""
Lista de vias da Urca para conferir as tags de mao unica no Street View (M3).

Le o cache bruto do OSM usado no artigo (urca_oficial_*) e o poligono oficial,
e escreve, para cada via (way) com ao menos um no dentro do poligono: id do
way, nome, classe, a regra de sentido que o codigo aplica (osm_loader._oneway_dir),
os pontos inicial e final do trecho dentro do poligono (no sentido dos nos do
OSM, que e' o sentido permitido nas vias de mao unica) e links para o OSM e
para o Street View.

Escreve output/urca_vias_street_view.csv (UTF-8 com BOM, abre no Excel).
"""

from __future__ import annotations
import csv
import json
import os

from nucleo import polygons as pg
from nucleo.neighborhoods import NEIGHBORHOODS
from nucleo.network import union_bbox
from nucleo.osm_loader import cache_path, _oneway_dir, _haversine
from caminhos import OUT



def regra(tags: dict) -> str:
    ow = str(tags.get("oneway", "")).lower()
    d = _oneway_dir(tags)
    if d == 0:
        return "mão dupla" + (f" (tag oneway={ow})" if ow else " (sem tag)")
    origem = ("tag oneway=" + ow) if ow else (
        "rotatória" if tags.get("junction") == "roundabout" else "convenção da classe")
    return ("mão única, sentido dos nós" if d == 1 else "mão única, sentido invertido") + f" ({origem})"


def main():
    cfg = NEIGHBORHOODS["urca"]
    poly = pg.fetch_bairro_polygon(cfg.display_name)
    bbox = union_bbox(cfg.bbox, pg.polygon_bbox(poly))
    raw = json.load(open(cache_path(cfg.key + "_oficial", bbox), encoding="utf-8"))
    ll = {el["id"]: (el["lat"], el["lon"]) for el in raw["elements"] if el["type"] == "node"}
    # extremos dos tres cortes de uma rua (localiza_corte.py), para priorizar a conferencia
    cortes = json.load(open(os.path.join(OUT, "localizacao_corte.json"), encoding="utf-8"))[0]
    extremos = [tuple(c) for corte in cortes["cortes_de_uma_rua"] for c in corte["coords"]]
    linhas = []
    for el in raw["elements"]:
        if el["type"] != "way" or "nodes" not in el:
            continue
        tags = el.get("tags", {})
        pts = [n for n in el["nodes"] if n in ll]
        dentro = [n for n in pts if pg.point_in_bairro(ll[n][1], ll[n][0], poly)]
        if not dentro:
            continue
        ini, fim = ll[dentro[0]], ll[dentro[-1]]
        comp = sum(_haversine(*ll[a], *ll[b]) for a, b in zip(dentro, dentro[1:])
                   if True)
        meio = ll[dentro[len(dentro) // 2]]
        perto = any(_haversine(*ll[n], *e) <= 60 for n in dentro for e in extremos)
        linhas.append({
            "way_osm": el["id"],
            "nome": tags.get("name", "(sem nome)"),
            "classe": tags.get("highway", ""),
            "regra_aplicada": regra(tags),
            "sentido_permitido": ("de A para B" if _oneway_dir(tags) == 1 else
                                  "de B para A" if _oneway_dir(tags) == -1 else "dois sentidos"),
            "A_lat_lon": f"{ini[0]:.6f},{ini[1]:.6f}",
            "B_lat_lon": f"{fim[0]:.6f},{fim[1]:.6f}",
            "comprimento_dentro_m": round(comp),
            "prioridade": "alta (a menos de 60 m de uma rua de corte)" if perto else "normal",
            "link_osm": f"https://www.openstreetmap.org/way/{el['id']}",
            "link_street_view": ("https://www.google.com/maps/@?api=1&map_action=pano&viewpoint="
                                 f"{meio[0]:.6f},{meio[1]:.6f}"),
            "confere_no_street_view (preencher)": "",
        })
    linhas.sort(key=lambda r: (r["prioridade"] != "alta (a menos de 60 m de uma rua de corte)", r["nome"], r["way_osm"]))
    os.makedirs(OUT, exist_ok=True)
    caminho = os.path.join(OUT, "urca_vias_street_view.csv")
    with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]), delimiter=";")
        w.writeheader(); w.writerows(linhas)
    print("prioridade alta:", sum(1 for r in linhas if r["prioridade"].startswith("alta")))
    unica = sum(1 for r in linhas if r["sentido_permitido"] != "dois sentidos")
    print(f"{len(linhas)} vias dentro do poligono; {unica} de mao unica; {len(linhas) - unica} de mao dupla")
    print("salvo:", caminho)


if __name__ == "__main__":
    main()
