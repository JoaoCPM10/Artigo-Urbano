"""
SIMULACAO DE INTERRUPCOES: os indicadores apontam as ruas cujo fechamento de
fato isola o nucleo? (Secao 4.6 do artigo)

Variavel de avaliacao independente: fracao dos nos do nucleo que ainda alcancam,
por caminho dirigido, algum destino externo da rede ampliada em 1 km (os
destinos da Secao 4.5), depois de fechar k ruas (os dois sentidos). Os
indicadores sao calculados sobre o bairro (poligono oficial) e os cortes usam as
portas administrativas; o desfecho mede outra coisa, a chegada a borda externa
de uma rede maior. Remover so' as arestas do proprio corte e constatar que isola
seria uma verificacao matematica, e por isso o relatorio compara estrategias de
mesmo orcamento k e olha k menor que o tamanho do corte.

Ruas removiveis: as que ficam dentro do poligono (as mesmas dos indicadores).

Estrategias (orcamento k = 1, 2, 4, 8, 16 ruas):
  aleatoria              200 sorteios (media e intervalo de 10 a 90%)
  intermediacao          as k ruas de maior intermediacao de aresta dirigida
  pontes_fortes          sorteio entre as pontes fortes do nucleo
  pontes_fracas          sorteio entre as pontes do grafo nao dirigido
  fluxo_corte            sorteio dentro de um corte minimo nucleo-portas
  fluxo_criticas         sorteio entre as ruas cujo fechamento reduz o fluxo de acesso
  guloso                 a cada passo, a rua que mais reduz o desfecho (limite superior)

Tambem, com k = 1: dano de cada rua isolada e quanto cada indicador o antecipa.

Escreve output/simulacao_interrupcoes.{json,csv} e fig_simulacao.png.
Uso:  python -m analises.simulacao_interrupcoes [--verifica] [--bairros urca,copacabana]
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import sys
from collections import deque

from analises import conectividade_externa as ce
from caminhos import OUT
from nucleo import betweenness as bt
from nucleo import connectivity as cc
from nucleo.neighborhoods import NEIGHBORHOODS, ORDEM_FIGURAS

RAIO_M = 1000
KS = (1, 2, 4, 8, 16)
SORTEIOS = 200
SEMENTE = 13
ESTRATEGIAS = (
    "aleatoria",
    "intermediacao",
    "pontes_fortes",
    "pontes_fracas",
    "fluxo_corte",
    "fluxo_criticas",
    "guloso",
)


# ---------------------------------------------------------------------------
# Rede de trabalho
# ---------------------------------------------------------------------------
class Mundo:
    def __init__(self, key: str):
        self.key = key
        rede0, big0, dist0, src = ce.monta_rede(key, 0)
        rede, big, dist, _ = ce.monta_rede(key, RAIO_M, src)
        self.rede0, self.rede, self.big, self.dist, self.src = rede0, rede, big, dist, set(src)
        G = rede.G
        self.G = G
        ring = rede.ring
        self.dest = set(rede.dest["scc"]["dir"])
        self.interior = {n for n in ring if dist[n] == 0}
        # arcos entre nos do anel; chave da rua = par nao ordenado
        self.arcos = [(e.u, e.v) for e in G.edges if e.u in ring and e.v in ring and e.u != e.v]
        self.radj = {n: [] for n in ring}
        self.fadj = {n: [] for n in ring}
        for u, v in self.arcos:
            p = frozenset((u, v))
            self.radj[v].append((u, p))
            self.fadj[u].append((v, p))
        self.ruas = {frozenset((u, v)) for (u, v) in self.arcos}
        self.pool = sorted(
            (p for p in self.ruas if all(n in self.interior for n in p)),
            key=lambda p: tuple(sorted(p)),
        )
        self.base = self.alcanca(frozenset())
        self.n_src_ok = len(self.src & self.base)

    def alcanca(self, removidas) -> set:
        """Nos que ainda alcancam algum destino sem usar as ruas `removidas`."""
        visto = set(self.dest)
        fila = deque(visto)
        while fila:
            v = fila.popleft()
            for u, p in self.radj[v]:
                if u not in visto and p not in removidas:
                    visto.add(u)
                    fila.append(u)
        return visto

    def desfecho(self, removidas) -> tuple[float, float]:
        """(perda do nucleo, perda do interior), relativas ao que alcancava sem falhas."""
        r = self.alcanca(removidas)
        n0 = self.src & self.base
        i0 = self.interior & self.base
        return (1 - len(self.src & r) / len(n0), 1 - len(self.interior & r) / len(i0))


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def _scc_maior(nodes, fadj, radj, p_fora=None):
    """Maior componente fortemente conexa do subgrafo induzido por `nodes`
    (Kosaraju iterativo; `p_fora` e' uma rua ignorada)."""
    S = set(nodes)
    visto, ordem = set(), []
    for s in S:
        if s in visto:
            continue
        visto.add(s)
        pilha = [(s, iter(fadj[s]))]
        while pilha:
            u, it = pilha[-1]
            for v, p in it:
                if v in S and v not in visto and p != p_fora:
                    visto.add(v)
                    pilha.append((v, iter(fadj[v])))
                    break
            else:
                ordem.append(u)
                pilha.pop()
    melhor, atrib = set(), set()
    for s in reversed(ordem):
        if s in atrib:
            continue
        comp, pilha = {s}, [s]
        atrib.add(s)
        while pilha:
            u = pilha.pop()
            for w, p in radj[u]:
                if w in S and w not in atrib and p != p_fora:
                    atrib.add(w)
                    comp.add(w)
                    pilha.append(w)
        if len(comp) > len(melhor):
            melhor = comp
    return melhor


def indicadores(m: Mundo) -> dict:
    inter = m.interior
    fadj = {n: [(v, p) for (v, p) in m.fadj[n] if v in inter] for n in inter}
    radj = {n: [(u, p) for (u, p) in m.radj[n] if u in inter] for n in inter}
    nucleo = _scc_maior(inter, fadj, radj)

    # pontes fortes: fechar a rua desfaz o nucleo fortemente conexo
    ruas_nucleo = [p for p in m.pool if all(n in nucleo for n in p)]
    fortes = []
    for p in ruas_nucleo:
        if len(_scc_maior(nucleo, fadj, radj, p_fora=p)) < len(nucleo):
            fortes.append(p)

    # pontes fracas: fechar a rua desconecta o grafo nao dirigido do interior
    arestas = []
    for e in m.big["undirected_edges"]:
        if e[0] in inter and e[1] in inter:
            arestas.append((e[0], e[1]))
    pontes = cc.bridges(list(inter), arestas)
    fracas = [frozenset(b) for b in pontes]

    # intermediacao de aresta dirigida no nucleo; a rua soma os dois sentidos
    eb = bt.edge_betweenness(m.G, nucleo)
    score_bt = {}
    for (u, v), x in eb.items():
        p = frozenset((u, v))
        score_bt[p] = score_bt.get(p, 0.0) + x
    por_bt = sorted(m.pool, key=lambda p: (-score_bt.get(p, 0.0), tuple(sorted(p))))

    # fluxo de acesso: ruas do corte minimo e ruas cujo fechamento reduz o fluxo
    r = m.rede0.fluxo("ruas_dir", "qualquer", detalhes=True)
    corte = sorted(
        {frozenset((u, v)) for (u, v) in r["cut_origem"]}, key=lambda p: tuple(sorted(p))
    )
    criticas = ce.critica_externas(m.rede0, r)
    crit = sorted(
        {frozenset((u, v)) for (u, v, _) in criticas["interno"]}, key=lambda p: tuple(sorted(p))
    )
    return {
        "nucleo": nucleo,
        "ruas_nucleo": ruas_nucleo,
        "fortes": fortes,
        "fracas": fracas,
        "score_bt": score_bt,
        "por_bt": por_bt,
        "corte": corte,
        "criticas": crit,
        "fluxo_acesso": r["fluxo"],
    }


# ---------------------------------------------------------------------------
# Estrategias
# ---------------------------------------------------------------------------
def _sorteio(rng, preferidas, pool, k):
    """k ruas: primeiro do conjunto `preferidas`; se faltar, completa do restante."""
    pref = [p for p in preferidas if p in set(pool)]
    pegas = rng.sample(pref, min(k, len(pref)))
    if len(pegas) < k:
        resto = [p for p in pool if p not in set(pegas)]
        pegas += rng.sample(resto, min(k - len(pegas), len(resto)))
    return pegas


def guloso(m: Mundo, kmax: int) -> list:
    """Ataque guloso: a cada passo fecha a rua que mais reduz o desfecho
    (perda do nucleo, depois perda do interior); desempate pela ordem fixa do pool."""
    removidas, ordem = set(), []
    for _ in range(kmax):
        melhor, chave = None, None
        for p in m.pool:
            if p in removidas:
                continue
            c = m.desfecho(removidas | {p})
            if chave is None or c > chave:
                melhor, chave = p, c
        removidas.add(melhor)
        ordem.append(melhor)
        if chave[0] >= 1.0:
            break
    return ordem


def simula(m: Mundo, ind: dict) -> dict:
    rng = random.Random(SEMENTE)
    pool = m.pool
    res = {e: {} for e in ESTRATEGIAS}

    def estat(vals):
        vals = sorted(vals)
        q = lambda f: vals[min(len(vals) - 1, int(f * len(vals)))]
        return {"media": sum(vals) / len(vals), "p10": q(0.10), "p90": q(0.90)}

    ordem_g = guloso(m, max(KS))
    for k in KS:
        # estrategias com sorteio
        for nome, pref in (
            ("aleatoria", pool),
            ("pontes_fortes", ind["fortes"]),
            ("pontes_fracas", ind["fracas"]),
            ("fluxo_corte", ind["corte"]),
            ("fluxo_criticas", ind["criticas"]),
        ):
            c, i = [], []
            for _ in range(SORTEIOS):
                sel = _sorteio(rng, pref, pool, k)
                a, b = m.desfecho(set(sel))
                c.append(a)
                i.append(b)
            res[nome][k] = {"nucleo": estat(c), "interior": estat(i), "conjunto": len(pref)}
        # determinísticas
        sel = set(ind["por_bt"][:k])
        a, b = m.desfecho(sel)
        res["intermediacao"][k] = {"nucleo": {"media": a}, "interior": {"media": b}}
        sel = set(ordem_g[:k])
        a, b = m.desfecho(sel)
        res["guloso"][k] = {"nucleo": {"media": a}, "interior": {"media": b}}
    return res


def dano_isolado(m: Mundo, ind: dict) -> dict:
    """Dano de cada rua fechada sozinha e quanto cada indicador o antecipa."""
    dano = {p: m.desfecho({p})[0] for p in m.pool}
    D = {p for p, d in dano.items() if d > 0}
    out = {
        "ruas_com_dano": len(D),
        "ruas": len(m.pool),
        "dano_maximo": max(dano.values()) if dano else 0.0,
    }

    def pr(conj):
        conj = set(conj) & set(m.pool)
        inter = len(conj & D)
        return {
            "tamanho": len(conj),
            "acertos": inter,
            "precisao": inter / len(conj) if conj else None,
            "revocacao": inter / len(D) if D else None,
        }

    out["fortes"] = pr(ind["fortes"])
    out["fracas"] = pr(ind["fracas"])
    out["fluxo_corte"] = pr(ind["corte"])
    out["fluxo_criticas"] = pr(ind["criticas"])
    out["intermediacao_top_|D|"] = pr(ind["por_bt"][: len(D)])
    out["spearman_intermediacao"] = spearman(
        [ind["score_bt"].get(p, 0.0) for p in m.pool], [dano[p] for p in m.pool]
    )
    # sobreposicao entre indicadores (Jaccard)
    base = {
        "fortes": set(ind["fortes"]),
        "fracas": set(ind["fracas"]),
        "corte": set(ind["corte"]),
        "criticas": set(ind["criticas"]),
        "intermediacao_top_f": set(ind["por_bt"][: max(1, ind["fluxo_acesso"])]),
    }
    nomes = sorted(base)
    out["jaccard"] = {
        f"{a}|{b}": (len(base[a] & base[b]) / len(base[a] | base[b]) if base[a] | base[b] else None)
        for i, a in enumerate(nomes)
        for b in nomes[i + 1 :]
    }
    return out, dano


def _ranks(x):
    idx = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and x[idx[j + 1]] == x[idx[i]]:
            j += 1
        for t in range(i, j + 1):
            r[idx[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else None


# ---------------------------------------------------------------------------
# Verificacao com o networkx
# ---------------------------------------------------------------------------
def verifica(m: Mundo, ind: dict) -> None:
    import networkx as nx

    nucleo = ind["nucleo"]
    D = nx.DiGraph()
    D.add_nodes_from(nucleo)
    for e in m.G.edges:
        if e.u in nucleo and e.v in nucleo and e.u != e.v:
            if not D.has_edge(e.u, e.v) or e.travel_time < D[e.u][e.v]["w"]:
                D.add_edge(e.u, e.v, w=e.travel_time)
    ref = nx.edge_betweenness_centrality(D, weight="w", normalized=True)
    mio = bt.edge_betweenness(m.G, nucleo)
    for a, v in ref.items():
        assert abs(mio[a] - v) < 1e-9, f"intermediacao de aresta {a}: {mio[a]} != {v}"
    # alcancabilidade a destino, em remocoes sorteadas
    H = nx.DiGraph()
    H.add_nodes_from(m.rede.ring)
    pares = {}
    for u, v in m.arcos:
        H.add_edge(u, v)
        pares.setdefault(frozenset((u, v)), []).append((u, v))
    rng = random.Random(5)
    for _ in range(25):
        rem = set(rng.sample(m.pool, rng.choice([1, 4, 16])))
        H2 = H.copy()
        for p in rem:
            for u, v in pares[p]:
                if H2.has_edge(u, v):
                    H2.remove_edge(u, v)
        esperado = set(m.dest)
        for d in m.dest:
            esperado |= nx.ancestors(H2, d)
        assert esperado == m.alcanca(rem), "alcancabilidade difere do networkx"


# ---------------------------------------------------------------------------
# Figura
# ---------------------------------------------------------------------------
def figura(resultados) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from figuras.rotulos import t as _t

    estilo = {
        "aleatoria": ("#7a7a7a", "-", "o", _t("random streets", "sorteio")),
        "intermediacao": (
            "#2b6cb0",
            "-",
            "s",
            _t("edge betweenness (top k)", "intermediação de aresta (k maiores)"),
        ),
        "pontes_fortes": ("#2f855a", "-", "^", _t("strong bridges", "pontes fortes")),
        "pontes_fracas": ("#b7791f", "-", "v", _t("bridges (undirected)", "pontes fracas")),
        "fluxo_corte": (
            "#c0392b",
            "-",
            "D",
            _t("access flow: one minimum cut", "corte mínimo do fluxo de acesso"),
        ),
        "fluxo_criticas": (
            "#6b46c1",
            "-",
            "P",
            _t("access flow: critical streets", "ruas críticas de fluxo"),
        ),
        "guloso": (
            "#111111",
            "--",
            "x",
            _t("greedy attack (upper bound)", "ataque guloso (limite superior)"),
        ),
    }
    ordem = ORDEM_FIGURAS
    chaves = [k for k in ordem if k in resultados] + [k for k in resultados if k not in ordem]
    ncol = 3
    nlin = (len(chaves) + ncol - 1) // ncol
    fig, axes = plt.subplots(nlin, ncol, figsize=(16, 4.6 * nlin), sharey=True, squeeze=False)
    axes = axes.ravel()
    for ax, (key, r) in zip(axes, [(k, resultados[k]) for k in chaves]):
        for e in ESTRATEGIAS:
            cor, ls, mk, lab = estilo[e]
            ys = [100 * r["estrategias"][e][str(k)]["nucleo"]["media"] for k in KS]
            ax.plot(
                range(len(KS)), ys, color=cor, ls=ls, marker=mk, ms=6, lw=1.8, label=lab, zorder=3
            )
            if e == "aleatoria":
                lo = [100 * r["estrategias"][e][str(k)]["nucleo"]["p10"] for k in KS]
                hi = [100 * r["estrategias"][e][str(k)]["nucleo"]["p90"] for k in KS]
                ax.fill_between(range(len(KS)), lo, hi, color=cor, alpha=0.18, zorder=1)
        ax.set_xticks(range(len(KS)))
        ax.set_xticklabels([str(k) for k in KS])
        ax.set_xlabel(_t("streets closed (k)", "ruas fechadas (k)"))
        ax.set_ylim(-3, 103)
        fl = r["indicadores"]["fluxo_acesso"]
        # k = fluxo de acesso: a escala dos k e' logaritmica (indice = log2 k)
        ax.axvline(
            math.log2(fl),
            color="#c0392b",
            ls=":",
            lw=1.4,
            zorder=2,
            label=_t("k = access flow", "k = fluxo de acesso"),
        )
        ax.set_title(
            f"{r['bairro']} " + _t(f"(access flow {fl})", f"(fluxo de acesso {fl})"), fontsize=12
        )
        ax.grid(alpha=0.25)
    for i in range(0, len(chaves), ncol):
        axes[i].set_ylabel(
            _t(
                "core intersections that lose every route\nto the external edge (%)",
                "interseções do núcleo que perdem todas as rotas\naté a borda externa (%)",
            )
        )
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    p = os.path.join(OUT, "fig_simulacao.png")
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved:", p, "(a copia para Figures e feita na integracao)")


# ---------------------------------------------------------------------------
def analisa(key: str, checar: bool) -> dict:
    m = Mundo(key)
    ind = indicadores(m)
    if checar:
        verifica(m, ind)
        print(f"{key}: networkx confere (intermediacao de aresta e alcancabilidade)", flush=True)
    est = simula(m, ind)
    isolado, _ = dano_isolado(m, ind)
    res = {
        "bairro": NEIGHBORHOODS[key].display_name,
        "rede": {
            "nos_anel": len(m.rede.ring),
            "destinos": len(m.dest),
            "ruas_removiveis": len(m.pool),
            "nucleo_origem": len(m.src),
            "nucleo_alcanca_no_inicio": m.n_src_ok,
        },
        "indicadores": {
            "fluxo_acesso": ind["fluxo_acesso"],
            "nucleo_forte_nos": len(ind["nucleo"]),
            "ruas_nucleo_forte": len(ind["ruas_nucleo"]),
            "pontes_fortes": len(ind["fortes"]),
            "pct_pontes_fortes": round(100 * len(ind["fortes"]) / len(ind["ruas_nucleo"]), 1),
            "pontes_fracas": len(ind["fracas"]),
            "ruas_corte_minimo": len(ind["corte"]),
            "ruas_criticas_de_fluxo": len(ind["criticas"]),
        },
        "estrategias": {e: {str(k): v for k, v in est[e].items()} for e in ESTRATEGIAS},
        "dano_isolado": isolado,
    }
    ln = (
        f"{res['bairro']:11s} f={ind['fluxo_acesso']:2d} pontes fortes={res['indicadores']['pct_pontes_fortes']}% "
        f"fracas={len(ind['fracas'])} criticas={len(ind['criticas'])} | perda do nucleo (%) por k="
        f"{','.join(map(str, KS))}"
    )
    print(ln)
    for e in ESTRATEGIAS:
        print(
            f"   {e:15s}",
            "  ".join(f"{100 * est[e][k]['nucleo']['media']:5.1f}" for k in KS),
            flush=True,
        )
    return res


def escreve(resultados) -> None:
    with open(os.path.join(OUT, "simulacao_interrupcoes.json"), "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=2)
    linhas = []
    for key, r in resultados.items():
        for e in ESTRATEGIAS:
            for k in KS:
                v = r["estrategias"][e][str(k)]
                linhas.append(
                    {
                        "bairro": r["bairro"],
                        "estrategia": e,
                        "k": k,
                        "perda_nucleo_media": round(v["nucleo"]["media"], 4),
                        "perda_nucleo_p10": round(v["nucleo"].get("p10", v["nucleo"]["media"]), 4),
                        "perda_nucleo_p90": round(v["nucleo"].get("p90", v["nucleo"]["media"]), 4),
                        "perda_interior_media": round(v["interior"]["media"], 4),
                    }
                )
    with open(
        os.path.join(OUT, "simulacao_interrupcoes.csv"), "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


def junta_com_existente(caminho, novos):
    """Com --bairros, mantem no JSON os bairros ja calculados e troca so os pedidos."""
    if "--bairros" in sys.argv and os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as fh:
            antigos = json.load(fh)
        antigos.update(novos)
        return antigos
    return novos


def main():
    chaves = ["urca", "copacabana", "botafogo"]
    if "--bairros" in sys.argv:
        chaves = sys.argv[sys.argv.index("--bairros") + 1].split(",")
    checar = "--verifica" in sys.argv
    resultados = {k: analisa(k, checar) for k in chaves}
    resultados = junta_com_existente(os.path.join(OUT, "simulacao_interrupcoes.json"), resultados)
    escreve(resultados)
    figura(resultados)


if __name__ == "__main__":
    main()
