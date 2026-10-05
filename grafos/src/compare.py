"""
Sintese comparativa entre bairros (Urca / Copacabana / Botafogo).

Le os output/<bairro>/metrics.json ja gerados e produz, em output/comparativo/:
  - tabela_comparativa.{csv,json}                : indicadores normalizados
    (proporcoes), uma linha por bairro, para colar direto em tabela LaTeX;
  - tabela_cruzamento_pontes_articulacoes.{csv,json}
    : a classificacao cruzada fraca x forte de pontes e articulacoes;
  - fig_comparativo_gargalos.png                 : barras agrupadas dos
    indicadores normalizados que sustentam o eixo pequeno/grande/sem gargalo.

Normaliza por PROPORCAO (nao contagem bruta), porque os bairros tem escalas
diferentes (a Urca tem ~60 interseccoes; Copacabana e Botafogo, algumas
centenas). Contagens brutas nao sao comparaveis; proporcoes sao.

Uso:  py compare.py
"""

from __future__ import annotations
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from neighborhoods import NEIGHBORHOODS

OUT_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
COMP_DIR = os.path.join(OUT_BASE, "comparativo")


def _pct(num, den):
    """Percentual num/den, ou None quando o denominador falta/zera."""
    if num is None or den in (None, 0):
        return None
    return round(100.0 * num / den, 1)


def _fmt(v):
    return "" if v is None else (f"{v}".replace(".", ","))


def carrega_metricas() -> "list[tuple[str, dict]]":
    """(display_name, metrics) para cada bairro com metrics.json, na ordem
    canonica de NEIGHBORHOODS."""
    out = []
    for key, cfg in NEIGHBORHOODS.items():
        p = os.path.join(OUT_BASE, key, "metrics.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                out.append((cfg.display_name, json.load(f)))
    return out


# ---------------------------------------------------------------------------
# Tabela comparativa (indicadores normalizados)
# ---------------------------------------------------------------------------
# rotulo do indicador -> funcao(metrics) -> valor
INDICADORES = [
    ("Interseções (V)",
     lambda m: m["rede"]["V_intersecoes"]),
    ("Trechos de rua",
     lambda m: m["rede"]["trechos"]),
    ("Mão única (% dos trechos)",
     lambda m: _pct(m["rede"]["trechos"] - _duplas(m), m["rede"]["trechos"])),
    ("Núcleo fortemente conexo (V)",
     lambda m: m["gargalos_estruturais_dirigidos"]["nucleo_n"]),
    ("Portas de acesso identificadas",
     lambda m: m["gargalo_acesso_gateway"]["n_gateways"]),
    ("Fluxo de acesso: rotas por ruas distintas do núcleo às portas",
     lambda m: m["gargalo_acesso_gateway"]["fluxo"]),
    ("Intermediação máxima (% dos pares)",
     lambda m: m["intermediacao"]["max_pct_pares"]),
    ("Fora da CFC gigante (% de V)",
     lambda m: _pct(m["conectividade"]["fora_da_scc_gigante"],
                    m["rede"]["V_intersecoes"])),
    ("Pontes fracas (% dos trechos)",
     lambda m: _pct(m["gargalos_estruturais"]["pontes"], m["rede"]["trechos"])),
    ("Pontes fortes (% das ruas do núcleo)",
     lambda m: _pct(m["gargalos_estruturais_dirigidos"]["pontes_fortes"],
                    m["gargalos_estruturais_dirigidos"].get("pares_nucleo"))),
    ("Articulações fortes (% do núcleo)",
     lambda m: _pct(m["gargalos_estruturais_dirigidos"]["articulacoes_fortes"],
                    m["gargalos_estruturais_dirigidos"]["nucleo_n"])),
    ("Mediana de pares desconectados por ponte forte (% do núcleo)",
     lambda m: _pct(m["resiliencia"]["pontes_fortes"]["pares_desconectados"]["mediana"],
                    m["resiliencia"]["n_pares_nucleo"])),
    ("Mediana de pares desconectados por articulação forte (% do núcleo)",
     lambda m: _pct(m["resiliencia"]["articulacoes_fortes"]["pares_desconectados"]["mediana"],
                    m["resiliencia"]["n_pares_nucleo"])),
]


def _duplas(m) -> int:
    """Numero de trechos de mao dupla = trechos - (arcos - trechos), pois cada
    trecho de mao dupla gera 2 arcos e cada trecho de mao unica gera 1:
      arcos = 2*duplas + (trechos - duplas)  ->  duplas = arcos - trechos."""
    return m["rede"]["E_arcos"] - m["rede"]["trechos"]


def build_summary_table(dados):
    linhas = []  # cada linha: [indicador, valor_bairro1, valor_bairro2, ...]
    for rotulo, fn in INDICADORES:
        linha = [rotulo]
        for _, m in dados:
            try:
                linha.append(fn(m))
            except (KeyError, TypeError):
                linha.append(None)
        linhas.append(linha)
    header = ["indicador"] + [nome for nome, _ in dados]
    return header, linhas


# ---------------------------------------------------------------------------
# Tabela de cruzamento fraca x forte
# ---------------------------------------------------------------------------
CRUZAMENTO = [
    ("Pontes: fraca e forte",
     lambda m: m["gargalos_estruturais_dirigidos"]["pontes_fraca_e_forte"]),
    ("Pontes: só forte",
     lambda m: m["gargalos_estruturais_dirigidos"]["pontes_so_forte"]),
    ("Pontes: só fraca (fora do núcleo)",
     lambda m: m["gargalos_estruturais_dirigidos"]["pontes_so_fraca_fora_do_nucleo"]),
    ("Articulações: fraca e forte",
     lambda m: m["gargalos_estruturais_dirigidos"]["articulacoes_fraca_e_forte"]),
    ("Articulações: só forte",
     lambda m: m["gargalos_estruturais_dirigidos"]["articulacoes_so_forte"]),
]


def build_crosstab_table(dados):
    linhas = []
    for rotulo, fn in CRUZAMENTO:
        linha = [rotulo]
        for _, m in dados:
            try:
                linha.append(fn(m))
            except (KeyError, TypeError):
                linha.append(None)
        linhas.append(linha)
    header = ["categoria"] + [nome for nome, _ in dados]
    return header, linhas


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------
def escreve_csv(path, header, linhas):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for linha in linhas:
            w.writerow([linha[0]] + [_fmt(v) for v in linha[1:]])


def escreve_json(path, header, linhas):
    obj = [dict(zip(header, [linha[0]] + list(linha[1:]))) for linha in linhas]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Figura de barras agrupadas (indicadores normalizados percentuais)
# ---------------------------------------------------------------------------
FIG_INDICADORES = [
    "Fora da CFC gigante (% de V)",
    "Pontes fracas (% dos trechos)",
    "Pontes fortes (% das ruas do núcleo)",
    "Articulações fortes (% do núcleo)",
    "Mediana de pares desconectados por ponte forte (% do núcleo)",
    "Mediana de pares desconectados por articulação forte (% do núcleo)",
]
FIG_ROTULOS = [
    "fora da\nCFC gigante",
    "pontes\nfracas",
    "pontes\nfortes",
    "articulações\nfortes",
    "med. desc.\nponte forte",
    "med. desc.\nartic. forte",
]


def fig_comparativo(dados, header, linhas, path):
    idx = {linha[0]: linha for linha in linhas}
    bairros = [nome for nome, _ in dados]
    series = []  # um valor por indicador, por bairro
    for j in range(len(bairros)):
        series.append([(idx[r][j + 1] or 0) for r in FIG_INDICADORES])

    n_ind = len(FIG_INDICADORES)
    n_b = len(bairros)
    x = list(range(n_ind))
    largura = 0.8 / max(n_b, 1)
    cmap = plt.get_cmap("tab10")

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for j, nome in enumerate(bairros):
        pos = [xi + (j - (n_b - 1) / 2) * largura for xi in x]
        barras = ax.bar(pos, series[j], largura, label=nome, color=cmap(j % 10))
        for p, v in zip(pos, series[j]):
            ax.text(p, v + 0.6, f"{v:.0f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(FIG_ROTULOS, fontsize=9)
    ax.set_ylabel("% (proporção normalizada)")
    ax.set_title("Indicadores estruturais normalizados por bairro\n"
                 "(eixo gargalo pequeno / grande / sem gargalo)")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main():
    dados = carrega_metricas()
    if not dados:
        print("Nenhum output/<bairro>/metrics.json encontrado. "
              "Rode 'py main.py <bairro>' antes.")
        return
    os.makedirs(COMP_DIR, exist_ok=True)
    print(f"Bairros com dados: {', '.join(nome for nome, _ in dados)}")

    h1, l1 = build_summary_table(dados)
    escreve_csv(os.path.join(COMP_DIR, "tabela_comparativa.csv"), h1, l1)
    escreve_json(os.path.join(COMP_DIR, "tabela_comparativa.json"), h1, l1)

    h2, l2 = build_crosstab_table(dados)
    escreve_csv(os.path.join(COMP_DIR, "tabela_cruzamento_pontes_articulacoes.csv"), h2, l2)
    escreve_json(os.path.join(COMP_DIR, "tabela_cruzamento_pontes_articulacoes.json"), h2, l2)

    fig_comparativo(dados, h1, l1,
                    os.path.join(COMP_DIR, "fig_comparativo_gargalos.png"))

    print(f"Artefatos comparativos em: {COMP_DIR}")
    # previa no console
    print("\n== tabela_comparativa ==")
    print(" | ".join(h1))
    for linha in l1:
        print(" | ".join([linha[0]] + [_fmt(v) for v in linha[1:]]))


if __name__ == "__main__":
    main()
