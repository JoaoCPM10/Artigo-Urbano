"""
Controle de tamanho da intermediacao maxima com varios bairros como origem dos
pedacos (Secao 4.4 do artigo).

controle_tamanho_intermediacao.py e valores_pareados.py sorteiam os pedacos
pareados pelo nucleo forte (65 +- 5 nos, o da Urca) so' em Copacabana e Botafogo.
Aqui o mesmo sorteio (mesma semente e mesma ordem: bola, depois Eden, com um
gerador por bairro) e' feito em todos os bairros que comportam o pedaco, e o
bairro de referencia pode ser a Urca ou o Leme:

  urca : nucleo forte de 65 +- 5 nos; origens Copacabana, Botafogo, Alto da Boa
         Vista, Sao Conrado e Praca da Bandeira (as de Copacabana e Botafogo sao
         conferidas contra o JSON existente);
  leme : nucleo forte de 20 +- 5 nos; origens as cinco acima e o Cosme Velho.

Acrescenta o resultado a output/controle_tamanho_intermediacao.json
("pareado_por_nucleo_forte" para a Urca; "referencia_leme" e
"pareado_por_nucleo_forte_leme" para o Leme), com "valores_pct".

Uso:  python -m analises.intermediacao_pareada_fontes [urca|leme] [bairro1,bairro2,...]
"""

from __future__ import annotations

import json
import os
import random
import statistics as st
import sys

from analises import controle_tamanho_intermediacao as ct
from caminhos import OUT
from nucleo import betweenness as bt
from nucleo import connectivity as cc
from nucleo import pedacos as nf
from nucleo.neighborhoods import NEIGHBORHOODS
from nucleo.network import load_network

FONTES = {
    "urca": ("copacabana", "botafogo", "alto_da_boa_vista", "sao_conrado", "praca_da_bandeira"),
    "leme": (
        "copacabana",
        "botafogo",
        "alto_da_boa_vista",
        "sao_conrado",
        "praca_da_bandeira",
        "cosme_velho",
    ),
}


def main():
    ref_nome = sys.argv[1] if len(sys.argv) > 1 else "urca"
    fontes = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else FONTES[ref_nome]
    caminho = os.path.join(OUT, "controle_tamanho_intermediacao.json")
    res = json.load(open(caminho, encoding="utf-8"))
    G_r = load_network(NEIGHBORHOODS[ref_nome])[0]["graph"]
    core_r = set(max(cc.strongly_connected_components(G_r), key=len))
    ref = bt.summary(G_r, core_r)["max"]
    ref_n = len(core_r)
    campo = "pareado_por_nucleo_forte" if ref_nome == "urca" else "pareado_por_nucleo_forte_leme"
    if ref_nome == "leme":
        rede_ref = nf.Rede("leme")
        f_ref, _ = rede_ref.fluxo(rede_ref.inside)
        res["referencia_leme"] = {
            "intersecoes": len(rede_ref.inside),
            "nucleo_forte": ref_n,
            "intermediacao_maxima_pct": round(100 * ref, 2),
            "fluxo": f_ref,
        }
    pareado_tudo = res.setdefault(campo, {})
    for key in fontes:
        rede = nf.Rede(key)
        G = load_network(NEIGHBORHOODS[key])[0]["graph"]
        rng = random.Random(nf.SEED)
        novo = {}
        for modo in ("bola", "eden"):
            maxs, tams, tent = ct.pareados(rede, G, ref, ref_n, modo, rng)
            novo[modo] = {
                "n_pedacos": len(maxs),
                "tentativas": tent,
                "nucleo_forte_min_max": [min(tams), max(tams)] if tams else None,
                "intermediacao_mediana_pct": round(100 * st.median(maxs), 1) if maxs else None,
                "intermediacao_p95_pct": round(
                    100 * sorted(maxs)[max(0, int(0.95 * len(maxs)) - 1)], 1
                )
                if maxs
                else None,
                "frac_intermediacao_ge_ref": round(sum(v >= ref for v in maxs) / len(maxs), 3)
                if maxs
                else None,
                "valores_pct": [round(100 * v, 2) for v in maxs],
            }
            if ref_nome == "urca":
                novo[modo]["frac_intermediacao_ge_urca"] = novo[modo]["frac_intermediacao_ge_ref"]
            print(
                key,
                modo,
                "n",
                len(maxs),
                "tentativas",
                tent,
                "frac >= ref",
                novo[modo]["frac_intermediacao_ge_ref"],
                flush=True,
            )
        antigo = pareado_tudo.get(key) if ref_nome == "urca" else None
        if antigo:  # regressao: reproduz o JSON existente
            for modo in ("bola", "eden"):
                assert antigo[modo]["tentativas"] == novo[modo]["tentativas"], (
                    key,
                    modo,
                    "tentativas",
                )
                if "valores_pct" in antigo[modo]:
                    assert antigo[modo]["valores_pct"] == novo[modo]["valores_pct"], (
                        key,
                        modo,
                        "valores",
                    )
            print(key, "regressao ok", flush=True)
        pareado_tudo[key] = novo
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
    print(
        "referencia", ref_nome, ": nucleo forte", ref_n, "intermediacao maxima %.2f%%" % (100 * ref)
    )


if __name__ == "__main__":
    main()
