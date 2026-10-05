"""
Estatisticas de construcao das redes (Secao 3.1 do artigo), para que os numeros
do texto possam ser conferidos:

  - data do extrato do OSM (base da Overpass) e versao da Overpass;
  - vias devolvidas para o envelope de busca e parcela com `maxspeed`;
  - cadeias mantidas e descartadas (lacos; sentido inconsistente);
  - pares de intersecoes ligados por mais de uma rua (ruas paralelas), na rede
    ja recortada pelo poligono;
  - classes de via aceitas e velocidades padrao por classe.

As contagens de vias e de cadeias se referem a rede do envelope de busca, antes
do recorte pelo poligono. Escreve output/estatisticas_dados.json.

Uso:  py estatisticas_dados.py
"""

from __future__ import annotations
import json
import os

from neighborhoods import NEIGHBORHOODS
from network import load_network
import osm_loader as ol

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def main():
    res = {"classes_de_via": ol.DRIVE.split("|"),
           "velocidade_padrao_kmh": ol.DEFAULT_SPEED, "bairros": {}}
    for key, cfg in NEIGHBORHOODS.items():
        data, _ = load_network(cfg)
        st = dict(data["stats"])
        mult = {}
        for e in data["undirected_edges"]:
            k = frozenset((e[0], e[1]))
            mult[k] = mult.get(k, 0) + 1
        st["pares_com_rua_paralela_na_rede_recortada"] = sum(1 for v in mult.values() if v > 1)
        st["pct_vias_com_maxspeed"] = round(100 * st["vias_com_maxspeed"] / st["vias"], 1)
        st["pct_cadeias_descartadas"] = round(
            100 * (st["lacos_descartados"] + st["cadeias_mistas_descartadas"])
            / (st["cadeias_mantidas"] + st["lacos_descartados"] + st["cadeias_mistas_descartadas"]), 2)
        res["bairros"][cfg.display_name] = st
        print(cfg.display_name, st)
    with open(os.path.join(OUT, "estatisticas_dados.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
