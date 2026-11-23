"""
Figura do fluxo de acesso (por ruas, sem o sentido das vias) em funcao da fracao
de origem f, uma linha por bairro. Le output/sensibilidade_fracao.json
(sensitivity.py --fracao) e escreve output/fig_fluxo_f.png.
Uso:  py fig_fluxo_f.py
"""

from __future__ import annotations
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
ORDEM = ["Urca", "Leme", "Alto da Boa Vista", "Cosme Velho", "Joá", "São Conrado",
         "Copacabana", "Botafogo", "Praça da Bandeira"]
ESTILO = {
    "Urca": ("#c0392b", "o", 3.0), "Leme": ("#e67e22", "s", 3.0),
    "Alto da Boa Vista": ("#2f855a", "^", 1.6), "Cosme Velho": ("#6b46c1", "v", 1.6),
    "Joá": ("#2b6cb0", "D", 1.6), "São Conrado": ("#b7791f", "P", 1.6),
    "Copacabana": ("#4a5568", "X", 1.6), "Botafogo": ("#718096", "h", 1.6),
    "Praça da Bandeira": ("#319795", "*", 1.6),
}


def main():
    linhas = json.load(open(os.path.join(OUT, "sensibilidade_fracao.json"), encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    for nome in ORDEM:
        pts = sorted((r["f"], r["fluxo"]) for r in linhas if r["bairro"] == nome)
        cor, mk, lw = ESTILO[nome]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=cor, marker=mk, lw=lw, ms=6, label=nome)
    ax.axvspan(0.15, 0.25, color="#cbd5e0", alpha=0.35, zorder=0, label="f used in the paper (0.15 to 0.25)")
    ax.axvline(0.2, color="#2d3748", lw=0.8, ls="--", zorder=0)
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 3, 5, 10, 20])
    ax.set_yticklabels(["1", "2", "3", "5", "10", "20"])
    ax.set_xlabel("origin fraction f")
    ax.set_ylabel("access flow (routes, ignoring one-way)")
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=8.5, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.tight_layout()
    p = os.path.join(OUT, "fig_fluxo_f.png")
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved:", p)


if __name__ == "__main__":
    main()
