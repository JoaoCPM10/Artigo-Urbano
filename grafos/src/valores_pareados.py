"""
Acrescenta a output/controle_tamanho_intermediacao.json os valores individuais
("valores_pct") da intermediacao maxima dos pedacos pareados pelo nucleo forte,
para desenhar o painel (b) da figura dos controles sem refazer os 2.000 pedacos
de 70 interseccoes. Regenera os pedacos pareados com a mesma semente e a mesma
ordem de sorteio de controle_tamanho_intermediacao.py e confere a mediana e o
numero de tentativas contra o JSON antes de gravar.

Uso:  py valores_pareados.py
"""

from __future__ import annotations
import json
import os
import random
import statistics as st

import betweenness as bt
import connectivity as cc
import nulo_fluxo as nf
import controle_tamanho_intermediacao as ct
from neighborhoods import NEIGHBORHOODS
from network import load_network


def main():
    caminho = os.path.join(ct.OUT, "controle_tamanho_intermediacao.json")
    res = json.load(open(caminho, encoding="utf-8"))
    G_u = load_network(NEIGHBORHOODS["urca"])[0]["graph"]
    core_u = set(max(cc.strongly_connected_components(G_u), key=len))
    ref = bt.summary(G_u, core_u)["max"]
    ref_n = len(core_u)
    for key in ("copacabana", "botafogo"):
        rede = nf.Rede(key)
        G = load_network(NEIGHBORHOODS[key])[0]["graph"]
        rng2 = random.Random(nf.SEED)
        for modo in ("bola", "eden"):
            maxs, tams, tent = ct.pareados(rede, G, ref, ref_n, modo, rng2)
            guardado = res["pareado_por_nucleo_forte"][key][modo]
            assert tent == guardado["tentativas"], f"{key} {modo}: tentativas {tent} != {guardado['tentativas']}"
            assert round(100 * st.median(maxs), 1) == guardado["intermediacao_mediana_pct"], \
                f"{key} {modo}: mediana diferente do JSON"
            guardado["valores_pct"] = [round(100 * v, 2) for v in maxs]
            print(key, modo, "ok", len(maxs))
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
