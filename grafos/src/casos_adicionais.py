"""
Casos adicionais (bairros de encosta pedidos na revisao): roda, para cada bairro
dado, as analises do nucleo do artigo sem mexer nos JSON dos tres bairros
originais:

  - ruas_vs_intersecoes.analisa  : portas e as quatro contagens de rotas;
  - localiza_corte.analisa       : cortes de uma rua e onde estao;
  - robustez_desempate.analisa   : 200 sorteios da ordem dos empates.

Escreve output/casos_adicionais.json (mescla com o que ja existe).
Uso:  py casos_adicionais.py alto_da_boa_vista cosme_velho
"""

from __future__ import annotations
import json
import os
import sys

import ruas_vs_intersecoes as ri
import localiza_corte as lc
import robustez_desempate as rd

OUT = ri.OUT


def main():
    chaves = [a for a in sys.argv[1:] if not a.startswith("--")]
    caminho = os.path.join(OUT, "casos_adicionais.json")
    saida = {}
    if os.path.exists(caminho):
        saida = json.load(open(caminho, encoding="utf-8"))
    for k in chaves:
        r = ri.analisa(k)
        if "--verifica" in sys.argv:
            ri.verifica(r)
        r.pop("_entrada")
        c = lc.analisa(k)
        for campo in ("_objs", "_vertices_corte"):
            c.pop(campo, None)
        d = rd.analisa(k, 200)
        saida[k] = {"quatro_contagens": r, "localizacao_corte": c, "desempate": d}
        print(k, "portas", r["portas"], "| ruas nd", r["nao_dirigido"]["ruas"],
              "int nd", r["nao_dirigido"]["intersecoes"], "| ruas dir", r["dirigido"]["ruas"],
              "int dir", r["dirigido"]["intersecoes"],
              "| cortes de 1 rua", len(c["cortes_de_uma_rua"]), "| desempate", d["min_max"],
              flush=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
