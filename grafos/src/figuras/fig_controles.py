"""
Figura 5 do artigo: controles de tamanho, em quatro paineis (Secao 4.4).

(a) Fluxo de acesso de pedacos de 70 interseccoes (o tamanho da Urca) sorteados em
    cinco bairros (output/nulo_fluxo_urca_fontes.json), contra o fluxo da Urca.
(b) Fluxo de acesso de pedacos de 27 interseccoes (o tamanho do Leme) sorteados em
    seis bairros (output/nulo_fluxo_leme_fontes.json), contra o fluxo do Leme.
(c) Intermediacao maxima de pedacos com nucleo forte de 65 +- 5 nos (o da Urca), em
    Copacabana, Botafogo, Alto da Boa Vista e Sao Conrado, contra a da Urca.
(d) O mesmo com nucleo forte de 20 +- 5 nos (o do Leme), em seis bairros, contra a do
    Leme. (c) e (d) leem output/controle_tamanho_intermediacao.json.

Escreve output/fig_controles.png.   Uso:  python -m figuras.fig_controles
"""

from __future__ import annotations

import json
import os

import matplotlib

from caminhos import OUT
from figuras.rotulos import num as _num
from figuras.rotulos import t as _t

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from nucleo.neighborhoods import NOMES

COR = {
    "copacabana": "#4a5568",
    "botafogo": "#718096",
    "alto_da_boa_vista": "#2f855a",
    "sao_conrado": "#b7791f",
    "praca_da_bandeira": "#319795",
    "cosme_velho": "#6b46c1",
}
plt.rcParams.update({"font.size": 10})


def painel_fluxo(ax, arq, ref_nome, ref_cor, titulo, xmax):
    d = json.load(open(os.path.join(OUT, arq), encoding="utf-8"))
    bins = [x - 0.5 for x in range(0, xmax + 2)]
    for k, b in d["pedacos"].items():
        v = b["bola"]["valores_fluxo"] + b["eden"]["valores_fluxo"]
        ax.hist(
            v,
            bins=bins,
            weights=[100 / len(v)] * len(v),
            histtype="step",
            lw=1.8,
            color=COR[k],
            label=f"{NOMES[k]} (n = {len(v):,})".replace(",", " "),
        )
    ref = d["referencia"]["fluxo"]
    ax.set_ylim(top=ax.get_ylim()[1] * 1.18)  # a etiqueta da referencia fica acima das curvas
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.axvline(ref, color=ref_cor, lw=2.5)
    ax.annotate(
        f"{ref_nome}: {ref}",
        xy=(ref, 0.94),
        xycoords=("data", "axes fraction"),
        xytext=(ref + 0.8, 0.94),
        textcoords=("data", "axes fraction"),
        color=ref_cor,
        fontsize=10,
        fontweight="bold",
        va="center",
        bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=1.5),
    )
    ax.set_xlim(-0.5, xmax + 0.5)
    ax.set_xlabel(_t("access flow of a piece (routes)", "fluxo de acesso do pedaço (rotas)"))
    ax.set_ylabel(_t("share of pieces (%)", "parcela dos pedaços (%)"))
    ax.set_title(titulo, fontsize=11)
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)


def painel_intermediacao(ax, pareado, ref_pct, ref_nome, ref_cor, titulo, fontes, xlim):
    """Intermediacao maxima de pedacos pareados pelo nucleo forte do bairro de referencia."""
    bins = list(range(xlim[0], xlim[1] + 2, 2))
    for k in fontes:
        p = pareado[k]
        v = p["bola"]["valores_pct"] + p["eden"]["valores_pct"]
        ax.hist(
            v,
            bins=bins,
            weights=[100 / len(v)] * len(v),
            histtype="step",
            lw=1.8,
            color=COR[k],
            label=f"{NOMES[k]} (n = {len(v)})",
        )
    ax.axvline(ref_pct, color=ref_cor, lw=2.5)
    ax.annotate(
        _num(f"{ref_nome}: {ref_pct:.1f}%"),
        xy=(ref_pct, 0.92),
        xycoords=("data", "axes fraction"),
        xytext=(ref_pct + 0.8, 0.92),
        textcoords=("data", "axes fraction"),
        color=ref_cor,
        fontsize=10,
        fontweight="bold",
        va="center",
        bbox=dict(facecolor="white", alpha=0.9, edgecolor="none", pad=1.5),
    )
    ax.set_xlim(*xlim)
    ax.set_xlabel(
        _t(
            "maximum betweenness of a piece (% of pairs)",
            "intermediação máxima do pedaço (% dos pares)",
        )
    )
    ax.set_ylabel(_t("share of pieces (%)", "parcela dos pedaços (%)"))
    ax.set_title(titulo, fontsize=11)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_ylim(top=ax.get_ylim()[1] * 1.7)  # a legenda fica acima das curvas
    ax.grid(axis="y", alpha=0.3)


def main():
    bt = json.load(open(os.path.join(OUT, "controle_tamanho_intermediacao.json"), encoding="utf-8"))
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2))
    axes = axes.ravel()
    painel_fluxo(
        axes[0],
        "nulo_fluxo_urca_fontes.json",
        "Urca",
        "#c0392b",
        _t("(a) Pieces of 70 intersections", "(a) Pedaços de 70 interseções"),
        31,
    )
    painel_fluxo(
        axes[1],
        "nulo_fluxo_leme_fontes.json",
        "Leme",
        "#e67e22",
        _t("(b) Pieces of 27 intersections", "(b) Pedaços de 27 interseções"),
        20,
    )
    painel_intermediacao(
        axes[2],
        bt["pareado_por_nucleo_forte"],
        bt["referencia_urca"]["intermediacao_maxima_pct"],
        "Urca",
        "#c0392b",
        _t("(c) Betweenness, strong core of 65 ± 5", "(c) Intermediação, núcleo forte de 65 ± 5"),
        ("copacabana", "botafogo", "alto_da_boa_vista", "sao_conrado"),
        (20, 80),
    )
    painel_intermediacao(
        axes[3],
        bt["pareado_por_nucleo_forte_leme"],
        bt["referencia_leme"]["intermediacao_maxima_pct"],
        "Leme",
        "#e67e22",
        _t("(d) Betweenness, strong core of 20 ± 5", "(d) Intermediação, núcleo forte de 20 ± 5"),
        (
            "copacabana",
            "botafogo",
            "alto_da_boa_vista",
            "sao_conrado",
            "praca_da_bandeira",
            "cosme_velho",
        ),
        (20, 90),
    )
    fig.tight_layout()
    p = os.path.join(OUT, "fig_controles.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    main()
