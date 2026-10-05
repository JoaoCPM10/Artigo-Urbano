"""
Figura dos controles de tamanho (Secoes 4.4 e 4.5 do artigo): distribuicao do
fluxo de acesso e do maximo de intermediacao em pedacos de tamanho igual ao da
Urca, sorteados em Copacabana e Botafogo, contra o valor da propria Urca.

Le output/nulo_fluxo.json e output/nulo_intermediacao.json (ver nulo_fluxo.py e
nulo_intermediacao.py) e escreve output/fig_controles.png.

Uso:  py fig_controles.py
"""

from __future__ import annotations
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
COR = {"urca": "#1f77b4", "copacabana": "#ff7f0e", "botafogo": "#2ca02c"}
NOME = {"copacabana": "Copacabana", "botafogo": "Botafogo"}
plt.rcParams.update({"font.size": 11})


def main():
    with open(os.path.join(OUT, "nulo_fluxo.json"), encoding="utf-8") as f:
        fl = json.load(f)
    with open(os.path.join(OUT, "nulo_intermediacao.json"), encoding="utf-8") as f:
        bt = json.load(f)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.7))


    # ---- (a) fluxo de acesso dos pedacos de 70 interseccoes ---------------
    bins = [x - 0.5 for x in range(0, 34)]
    for k in ("copacabana", "botafogo"):
        v = fl["pedacos"][k]["bola"]["valores_fluxo"] + fl["pedacos"][k]["eden"]["valores_fluxo"]
        ax1.hist(v, bins=bins, weights=[100 / len(v)] * len(v), color=COR[k], alpha=0.55,
                 label=f"{NOME[k]} pieces (n = {len(v):,})".replace(",", " "))
    urca = fl["referencia_urca"]["fluxo"]
    ax1.axvline(urca, color=COR["urca"], lw=2.5)
    ax1.annotate(f"Urca: {urca}", xy=(urca, 0.9), xycoords=("data", "axes fraction"),
                 xytext=(urca + 1.0, 0.9), textcoords=("data", "axes fraction"),
                 color=COR["urca"], fontsize=11, fontweight="bold", va="center")
    ax1.set_xlim(-0.5, 32.5)
    ax1.set_xlabel("access flow of a piece of 70 intersections (routes)")
    ax1.set_ylabel("share of pieces (%)")
    ax1.set_title("(a) Access flow", fontsize=12)
    ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)
    ax1.grid(axis="y", alpha=0.3)

    # ---- (b) maximo de intermediacao dos pedacos --------------------------
    bins2 = [x for x in range(20, 72, 2)]
    for k in ("copacabana", "botafogo"):
        v = bt["subamostragem"][f"{k}_bola"]["valores_pct"] + bt["subamostragem"][f"{k}_eden"]["valores_pct"]
        ax2.hist(v, bins=bins2, weights=[100 / len(v)] * len(v), color=COR[k], alpha=0.55,
                 label=f"{NOME[k]} pieces (n = {len(v)})")
    urca_b = bt["escala"]["urca"]["max_pct"]
    ax2.axvline(urca_b, color=COR["urca"], lw=2.5)
    ax2.annotate(f"Urca: {urca_b:.1f}%", xy=(urca_b, 0.9), xycoords=("data", "axes fraction"),
                 xytext=(urca_b + 0.8, 0.9), textcoords=("data", "axes fraction"),
                 color=COR["urca"], fontsize=11, fontweight="bold", va="center")
    ax2.set_ylim(0, 28)
    ax2.set_xlim(20, 70)
    ax2.set_xlabel("maximum betweenness of a piece (% of pairs)")
    ax2.set_ylabel("share of pieces (%)")
    ax2.set_title("(b) Betweenness maximum", fontsize=12)
    ax2.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    p = os.path.join(OUT, "fig_controles.png")
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    main()
