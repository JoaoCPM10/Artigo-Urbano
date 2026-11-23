"""
Valores das Tabelas 1 e 3 do artigo para os nove bairros, calculados a partir de
output/<bairro>/metrics.json e output/corte_no_a_no.json. Os tres bairros
originais devem reproduzir os valores ja impressos no artigo (conferencia no fim).

Escreve output/tabelas_nove_bairros.json.   Uso: python -m analises.tabelas_nove_bairros
"""

from __future__ import annotations

import json
import os

from caminhos import OUT
from nucleo.neighborhoods import NOMES, ORDEM_TABELAS

# valores ja impressos no artigo (tres bairros originais)
ARTIGO = {
    "urca": {
        "V": 70,
        "trechos": 104,
        "mao_unica_pct": 91.3,
        "nucleo_forte": 65,
        "fora_pct": 7.1,
        "pontes_fracas_pct": 10.6,
        "pontes_fortes_pct": 61.5,
        "articulacoes_pct": 73.8,
        "inter_max": 54.2,
        "pares": 2415,
        "pct_corte1": 68.4,
        "media": 1.49,
        "pct_corte1_dir": 95.6,
        "media_dir": 1.04,
    },
    "copacabana": {
        "V": 345,
        "trechos": 494,
        "mao_unica_pct": 74.9,
        "nucleo_forte": 331,
        "fora_pct": 4.1,
        "pontes_fracas_pct": 15.8,
        "pontes_fortes_pct": 45.3,
        "articulacoes_pct": 54.1,
        "inter_max": 27.8,
        "pares": 58996,
        "pct_corte1": 40.7,
        "media": 1.94,
        "pct_corte1_dir": 81.5,
        "media_dir": 1.19,
    },
    "botafogo": {
        "V": 434,
        "trechos": 563,
        "mao_unica_pct": 76.2,
        "nucleo_forte": 392,
        "fora_pct": 9.7,
        "pontes_fracas_pct": 20.2,
        "pontes_fortes_pct": 68.4,
        "articulacoes_pct": 63.5,
        "inter_max": 20.9,
        "pares": 93528,
        "pct_corte1": 51.7,
        "media": 1.68,
        "pct_corte1_dir": 93.1,
        "media_dir": 1.07,
    },
}


def r1(x):
    return round(x + 1e-9, 1)


def main():
    cn = json.load(open(os.path.join(OUT, "corte_no_a_no.json"), encoding="utf-8"))["bairros"]
    res = {}
    for k in ORDEM_TABELAS:
        m = json.load(open(os.path.join(OUT, k, "metrics.json"), encoding="utf-8"))
        rd, est, dr = m["rede"], m["gargalos_estruturais"], m["gargalos_estruturais_dirigidos"]
        V, T, E = rd["V_intersecoes"], rd["trechos"], rd["E_arcos"]
        c = cn[NOMES[k]]
        res[k] = {
            "bairro": NOMES[k],
            "V": V,
            "trechos": T,
            "ruas": None,
            "mao_unica_pct": r1(100 * (2 * T - E) / T),
            "nucleo_forte": dr["nucleo_n"],
            "fora_pct": r1(100 * (V - dr["nucleo_n"]) / V),
            "pontes_fracas_pct": r1(100 * est["pontes"] / T),
            "pontes_fortes_pct": r1(100 * dr["pontes_fortes"] / dr["pares_nucleo"]),
            "articulacoes_pct": r1(100 * dr["articulacoes_fortes"] / dr["nucleo_n"]),
            "inter_max": round(m["intermediacao"]["max_pct_pares"], 1),
            "pares": c["nao_dirigido"]["n_pares"],
            "pct_corte1": c["nao_dirigido"]["pct_corte_1"],
            "media": c["nao_dirigido"]["media"],
            "pct_grau1_nd": c["nao_dirigido"]["pct_cortes_1_explicados_por_grau_1"],
            "pct_corte1_dir": c["dirigido"]["pct_corte_1"],
            "media_dir": c["dirigido"]["media"],
        }
    ruas = json.load(open(os.path.join(OUT, "service_artigo.json"), encoding="utf-8"))
    for k in ORDEM_TABELAS:
        res[k]["ruas"] = ruas[k]["ruas"]
    print(
        f"{'bairro':18s} {'V':>4s} {'trech':>5s} {'ruas':>4s} {'1via%':>6s} {'nuc':>4s} {'fora%':>6s} {'pfr%':>6s} {'pfo%':>6s} {'art%':>6s} {'imax':>5s} {'pares':>6s} {'c1%':>5s} {'med':>5s} {'c1d%':>5s} {'medd':>5s}"
    )
    for k in ORDEM_TABELAS:
        r = res[k]
        print(
            f"{r['bairro']:18s} {r['V']:4d} {r['trechos']:5d} {r['ruas']:4d} {r['mao_unica_pct']:6.1f} {r['nucleo_forte']:4d} {r['fora_pct']:6.1f} "
            f"{r['pontes_fracas_pct']:6.1f} {r['pontes_fortes_pct']:6.1f} {r['articulacoes_pct']:6.1f} {r['inter_max']:5.1f} {r['pares']:6d} "
            f"{r['pct_corte1']:5.1f} {r['media']:5.2f} {r['pct_corte1_dir']:5.1f} {r['media_dir']:5.2f}"
        )
    # regressao: os tres originais reproduzem o artigo
    ok = True
    for k, ref in ARTIGO.items():
        for campo, v in ref.items():
            if abs(res[k][campo] - v) > 0.051:
                ok = False
                print("DIFERE", k, campo, res[k][campo], "artigo", v)
    print("regressao com o artigo:", "ok" if ok else "FALHOU")
    json.dump(
        res,
        open(os.path.join(OUT, "tabelas_nove_bairros.json"), "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    main()
