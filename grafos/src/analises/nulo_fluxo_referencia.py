"""
Controle de tamanho do fluxo de acesso para um bairro de referencia qualquer
(mesmo metodo de nucleo/pedacos.py, que usa a Urca): pedacos conexos com o mesmo
numero de interseccoes do bairro de referencia, sorteados em Copacabana e
Botafogo por bola (BFS) e por crescimento aleatorio (Eden), mais a busca
adversaria de subida de encosta partindo dos 25 pedacos de menor fluxo.

Pergunta: um fluxo de acesso igual ao do bairro de referencia (por exemplo, 1
no Leme) e' so' efeito de a rede ser pequena?

Escreve output/nulo_fluxo_<referencia>.json.
Uso:  python -m analises.nulo_fluxo_referencia leme
"""

from __future__ import annotations

import json
import os
import random
import sys

from caminhos import OUT
from nucleo import pedacos as nf


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "leme"
    fontes = ("copacabana", "botafogo")
    sufixo = ""
    if "--fontes" in sys.argv:
        fontes = tuple(sys.argv[sys.argv.index("--fontes") + 1].split(","))
        sufixo = "_fontes"
    rede_ref = nf.Rede(ref)
    m = len(rede_ref.inside)
    f_ref, g_ref = rede_ref.fluxo(rede_ref.inside)
    res = {"referencia": {"bairro": ref, "n": m, "fluxo": f_ref, "portas": g_ref}, "pedacos": {}}
    for key in fontes:
        rede = nf.Rede(key)
        if len(rede.nodes) < m:
            print(key, "pulado (menos de", m, "interseccoes)")
            continue
        rng = random.Random(nf.SEED)
        bloco = {}
        sorteados = []
        for nome, gera in (("bola", rede.bola), ("eden", rede.eden)):
            fl, gw = [], []
            for _ in range(nf.N_PIECES):
                S = gera(m, rng)
                f, g = rede.fluxo(S)
                fl.append(f)
                gw.append(g)
                sorteados.append((f, S))
            bloco[nome] = {
                "fluxo": nf.resumo(fl),
                "portas": nf.resumo(gw),
                "valores_fluxo": fl,
                "frac_fluxo_le_3": round(sum(x <= 3 for x in fl) / len(fl), 3),
                "frac_fluxo_le_1": round(sum(x <= 1 for x in fl) / len(fl), 3),
                "frac_fluxo_le_ref": round(sum(x <= f_ref for x in fl) / len(fl), 3),
            }
        sorteados.sort(key=lambda x: x[0])
        f_min, g_min, S_min = rede.adversaria(sorteados[: nf.N_INICIOS], rng)
        bloco["adversaria"] = {
            "menor_fluxo": f_min,
            "portas_do_pedaco": g_min,
            "n_nos": len(S_min),
            "menor_fluxo_nos_sorteios": sorteados[0][0],
            "n_pedacos_com_o_menor_fluxo": sum(f == sorteados[0][0] for f, _ in sorteados),
            "n_inicios": nf.N_INICIOS,
            "n_iteracoes": nf.N_ITERS,
        }
        res["pedacos"][key] = bloco
        print(
            key, {k: (v["fluxo"] if k != "adversaria" else v) for k, v in bloco.items()}, flush=True
        )
    print("Referencia:", res["referencia"])
    with open(os.path.join(OUT, f"nulo_fluxo_{ref}{sufixo}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
