"""
Figura 6 do artigo: conectividade externa a 1 km nos nove bairros, sobre agua,
encosta e escala. Cada painel vem de fig_conectividade_externa.painel.
Escreve output/fig_externa.png.
Uso:  python -m figuras.fig_externa_geo
"""

from __future__ import annotations

import os

import matplotlib

from figuras.rotulos import t as _t

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analises import conectividade_externa as ce
from figuras import fig_conectividade_externa as fe
from figuras import mapa_contexto as mc
from nucleo.neighborhoods import ORDEM_FIGURAS


def main():
    fig, axes = plt.subplots(3, 3, figsize=(16, 16.5))
    for ax, key in zip(axes.ravel(), ORDEM_FIGURAS):
        res, obj = ce.analisa_bairro(key, raios=(0, fe.RAIO_M))
        o = obj[fe.RAIO_M]
        mc.desenha_contexto(ax, key, o["big"], nos=o["rede"].ring)
        fe.painel(ax, key, res, o)
        ax.set_xticks([])
        ax.set_yticks([])
        mc.barra_escala(ax)
        mc.seta_norte(ax)
        print(key, "ok", flush=True)
    h = mc.handles_contexto()[:2] + [
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            color="#2b6cb0",
            label=_t("source region (core)", "região de origem (núcleo)"),
        ),
        plt.Line2D(
            [],
            [],
            marker="^",
            ls="",
            color="#2f855a",
            markeredgecolor="#1c4532",
            markersize=8,
            label=_t("external destinations", "destinos externos"),
        ),
        plt.Line2D(
            [],
            [],
            color=fe.COR["origem"],
            lw=3,
            label=_t("minimum cut nearest the core", "corte mínimo mais próximo do núcleo"),
        ),
        plt.Line2D(
            [],
            [],
            color=fe.COR["destino"],
            lw=3,
            label=_t(
                "minimum cut nearest the destinations", "corte mínimo mais próximo dos destinos"
            ),
        ),
        plt.Line2D(
            [],
            [],
            color=fe.COR["externa"],
            lw=3,
            label=_t(
                "external streets whose closure lowers the flow",
                "ruas externas cujo fechamento reduz o fluxo",
            ),
        ),
        plt.Line2D(
            [],
            [],
            color="#2d3748",
            lw=1.3,
            ls="--",
            label=_t("official boundary", "fronteira oficial"),
        ),
    ]
    fig.legend(handles=h, loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    p = os.path.join(ce.OUT, "fig_externa.png")
    fig.savefig(p, dpi=100, bbox_inches="tight")
    plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    main()
