"""
Figura dos controles de tamanho (Secao 4.4 do artigo), em tres paineis.

(a) Fluxo de acesso de pedacos de 70 interseccoes (o tamanho da Urca) sorteados em
    cinco bairros (output/nulo_fluxo_urca_fontes.json), contra o fluxo da Urca.
(b) Fluxo de acesso de pedacos de 27 interseccoes (o tamanho do Leme) sorteados em
    seis bairros (output/nulo_fluxo_leme_fontes.json), contra o fluxo do Leme.
(c) Intermediacao maxima de pedacos de Copacabana e Botafogo com nucleo forte de
    65 +- 5 nos (output/controle_tamanho_intermediacao.json, campo "valores_pct"
    gravado por valores_pareados.py), contra a da Urca.

Escreve output/fig_controles.png e copia para ../Figures.   Uso:  py fig_controles.py
"""

from __future__ import annotations
import json
import os
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
COR = {"copacabana": "#4a5568", "botafogo": "#718096", "alto_da_boa_vista": "#2f855a",
       "sao_conrado": "#b7791f", "praca_da_bandeira": "#319795", "cosme_velho": "#6b46c1"}
NOME = {"copacabana": "Copacabana", "botafogo": "Botafogo", "alto_da_boa_vista": "Alto da Boa Vista",
        "sao_conrado": "São Conrado", "praca_da_bandeira": "Praça da Bandeira", "cosme_velho": "Cosme Velho"}
plt.rcParams.update({"font.size": 10})


def painel_fluxo(ax, arq, ref_nome, ref_cor, titulo, xmax):
    d = json.load(open(os.path.join(OUT, arq), encoding="utf-8"))
    bins = [x - 0.5 for x in range(0, xmax + 2)]
    for k, b in d["pedacos"].items():
        v = b["bola"]["valores_fluxo"] + b["eden"]["valores_fluxo"]
        ax.hist(v, bins=bins, weights=[100 / len(v)] * len(v), histtype="step", lw=1.8,
                color=COR[k], label=f"{NOME[k]} (n = {len(v):,})".replace(",", " "))
    ref = d["referencia"]["fluxo"]
    ax.axvline(ref, color=ref_cor, lw=2.5)
    ax.annotate(f"{ref_nome}: {ref}", xy=(ref, 0.92), xycoords=("data", "axes fraction"),
                xytext=(ref + 0.8, 0.92), textcoords=("data", "axes fraction"),
                color=ref_cor, fontsize=10, fontweight="bold", va="center",
                bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=1.5))
    ax.set_xlim(-0.5, xmax + 0.5)
    ax.set_xlabel("access flow of a piece (routes)")
    ax.set_ylabel("share of pieces (%)")
    ax.set_title(titulo, fontsize=11)
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)


def main():
    bt = json.load(open(os.path.join(OUT, "controle_tamanho_intermediacao.json"), encoding="utf-8"))
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.9))
    painel_fluxo(axes[0], "nulo_fluxo_urca_fontes.json", "Urca", "#c0392b",
                 "(a) Pieces of 70 intersections", 31)
    painel_fluxo(axes[1], "nulo_fluxo_leme_fontes.json", "Leme", "#e67e22",
                 "(b) Pieces of 27 intersections", 20)
    ax = axes[2]
    bins2 = list(range(20, 72, 2))
    for k, cor in (("copacabana", COR["copacabana"]), ("botafogo", COR["botafogo"])):
        p = bt["pareado_por_nucleo_forte"][k]
        v = p["bola"]["valores_pct"] + p["eden"]["valores_pct"]
        ax.hist(v, bins=bins2, weights=[100 / len(v)] * len(v), histtype="step", lw=1.8, color=cor,
                label=f"{NOME[k]} (n = {len(v)})")
    urca_b = bt["referencia_urca"]["intermediacao_maxima_pct"]
    ax.axvline(urca_b, color="#c0392b", lw=2.5)
    ax.annotate(f"Urca: {urca_b:.1f}%", xy=(urca_b, 0.92), xycoords=("data", "axes fraction"),
                xytext=(urca_b + 0.8, 0.92), textcoords=("data", "axes fraction"),
                color="#c0392b", fontsize=10, fontweight="bold", va="center",
                bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=1.5))
    ax.set_xlim(20, 80)
    ax.set_xlabel("maximum betweenness of a piece (% of pairs)")
    ax.set_ylabel("share of pieces (%)")
    ax.set_title("(c) Betweenness, strong core of 65 ± 5", fontsize=11)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_controles.png")
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    figs = os.path.join(os.path.dirname(OUT), "..", "Figures")
    print("saved:", p, "(a copia para Figures e' feita na integracao)")


if __name__ == "__main__":
    main()
