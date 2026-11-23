"""
Indicadores estruturais de cada bairro (Secoes 3 e 4 do artigo).

Para cada bairro: carrega a rede (recortada pelo poligono oficial), calcula a
conectividade (componentes e componentes fortemente conexas), as pontes e
articulacoes fracas e fortes, o fluxo de acesso (nucleo ate as portas) e a
intermediacao maxima, e escreve output/<bairro>/metrics.json.

Uso:  python -m analises.indicadores [bairro ...]
      (sem argumento, so a Urca; "all" roda os nove bairros)
"""

from __future__ import annotations

import json
import os
import sys
import time

from caminhos import OUT as OUT_BASE
from nucleo import betweenness as bt
from nucleo import connectivity as cc
from nucleo import maxflow as mf
from nucleo.neighborhoods import NEIGHBORHOODS
from nucleo.network import GATEWAY_BUFFER_M, gateway_nodes, load_network
from nucleo.remocao import copia_sem_aresta, copia_sem_no, nucleo_intacto


def banner(t):
    print("\n" + "=" * 64 + f"\n {t}\n" + "=" * 64)


# ---------------------------------------------------------------------------
# Um indicador por funcao. Cada uma imprime o resumo e devolve o dicionario que
# vai para metrics.json.
# ---------------------------------------------------------------------------
def rede(cfg, data, bbox_usado, G, edges_u):
    banner(f"REDE DE RUAS — {cfg.display_name.upper()}, OpenStreetMap")
    print(f"Pontos OSM brutos: {data['n_raw_nodes']} | vias OSM: {data['n_ways']}")
    print(
        f"Apos simplificacao: {G.n} intersecoes (V), {G.m} arcos (E), {len(edges_u)} trechos de rua"
    )
    return {
        "fonte": "OpenStreetMap (Overpass API)",
        "bairro": cfg.bairro_full,
        "bairro_slug": cfg.key,
        "bbox": bbox_usado,
        "bbox_recortado_por_poligono_oficial": True,
        "n_removidos_fora_do_poligono": data["n_removidos_fora_do_poligono"],
        "pontos_osm": data["n_raw_nodes"],
        "vias_osm": data["n_ways"],
        "V_intersecoes": G.n,
        "E_arcos": G.m,
        "trechos": len(edges_u),
    }


def conectividade(G, edges_u):
    """Componentes (nao dirigido) e componentes fortemente conexas. Devolve (metricas, comps, scc)."""
    banner("(A) CONECTIVIDADE")
    nodes = G.nodes()
    t0 = time.perf_counter()
    comps = cc.connected_components(nodes, edges_u)
    scc = cc.strongly_connected_components(G)
    t_conn = time.perf_counter() - t0
    comp_sizes = sorted((len(c) for c in comps), reverse=True)
    scc_sizes = sorted((len(c) for c in scc), reverse=True)
    deg = {u: 0 for u in nodes}
    for u, v in edges_u:
        deg[u] += 1
        deg[v] += 1
    dead_ends = [u for u in nodes if deg[u] == 1]
    print(f"Componentes (nao-dirigido): {len(comps)} (maior = {comp_sizes[0]})")
    print(f"Componentes fortemente conexas: {len(scc)} (maior = {scc_sizes[0]})")
    print(f"Intersecoes fora da CFC gigante: {G.n - scc_sizes[0]} (efeito das mãos únicas)")
    print(f"Ruas sem saida (cul-de-sac, grau 1): {len(dead_ends)}")
    print(f"Tempo: {t_conn * 1000:.1f} ms")
    metricas = {
        "componentes": len(comps),
        "maior_componente": comp_sizes[0],
        "scc": len(scc),
        "maior_scc": scc_sizes[0],
        "fora_da_scc_gigante": G.n - scc_sizes[0],
        "ruas_sem_saida": len(dead_ends),
        "tempo_ms": round(t_conn * 1000, 2),
    }
    return metricas, comps, scc


def estruturais_fracos(G, edges_u):
    """Pontes e articulacoes pela definicao, no grafo nao dirigido. Devolve (metricas, aps, brs)."""
    banner("(C.1) GARGALOS ESTRUTURAIS: pontes e articulacoes (definicao)")
    nodes = G.nodes()
    t0 = time.perf_counter()
    aps = cc.articulation_points(nodes, edges_u)
    brs = cc.bridges(nodes, edges_u)
    t_struct = time.perf_counter() - t0
    print(f"Pontos de articulacao: {len(aps)} de {G.n} intersecoes")
    print(f"Pontes (cut-edges): {len(brs)} de {len(edges_u)} trechos")
    print(f"Tempo: {t_struct * 1000:.1f} ms")
    metricas = {
        "articulacoes": len(aps),
        "pontes": len(brs),
        "tempo_ms": round(t_struct * 1000, 2),
    }
    return metricas, aps, brs


def estruturais_fortes(G, edges_u, gset, aps, brs):
    """Pontes e articulacoes FORTES: as que fragmentam o nucleo fortemente conexo."""
    banner("(C.1.5) GARGALOS ESTRUTURAIS DIRIGIDOS: pontes/articulacoes FORTES restritas ao nucleo")
    t0 = time.perf_counter()
    weak_edge_pairs = {frozenset(e) for e in brs}
    aps_set = set(aps)

    # pares de nos unicos dentro do nucleo (uma rua com trechos paralelos
    # entre o mesmo par de intersecoes conta como UMA rua para efeito de
    # fechamento: fechar a rua fecha os dois trechos ao mesmo tempo).
    pares_nucleo = []
    vistos = set()
    for u, v in edges_u:
        if u in gset and v in gset:
            k = frozenset((u, v))
            if k not in vistos:
                vistos.add(k)
                pares_nucleo.append((u, v))

    core_breaking_edges = []
    for u, v in pares_nucleo:
        H = copia_sem_aresta(G, u, v)
        if not nucleo_intacto(H, gset):
            core_breaking_edges.append((u, v))

    core_breaking_nodes = []
    for u in gset:
        H = copia_sem_no(G, u)
        if not nucleo_intacto(H, gset - {u}):
            core_breaking_nodes.append(u)
    t_forte = time.perf_counter() - t0

    edges_both = [e for e in core_breaking_edges if frozenset(e) in weak_edge_pairs]
    edges_strong_only = [e for e in core_breaking_edges if frozenset(e) not in weak_edge_pairs]
    core_pairs_set = {frozenset(e) for e in core_breaking_edges}
    edges_weak_only = [e for e in brs if frozenset(e) not in core_pairs_set]

    nodes_both = [n for n in core_breaking_nodes if n in aps_set]
    nodes_strong_only = [n for n in core_breaking_nodes if n not in aps_set]

    print(f"Nucleo fortemente conexo: {len(gset)} intersecoes")
    print(
        f"Pontes fortes (fragmentam o nucleo): {len(core_breaking_edges)} "
        f"de {len(pares_nucleo)} pares de rua do nucleo"
    )
    print(
        f"Articulacoes fortes (fragmentam o nucleo): {len(core_breaking_nodes)} "
        f"de {len(gset)} intersecoes do nucleo"
    )
    print(
        f"  cruzamento pontes:       fraca+forte={len(edges_both)}  "
        f"so forte={len(edges_strong_only)}  so fraca={len(edges_weak_only)}"
    )
    print(
        f"  cruzamento articulacoes: fraca+forte={len(nodes_both)}  "
        f"so forte={len(nodes_strong_only)}"
    )
    print(f"Tempo: {t_forte * 1000:.1f} ms")
    return {
        "nucleo_n": len(gset),
        "pares_nucleo": len(pares_nucleo),
        "pontes_fortes": len(core_breaking_edges),
        "articulacoes_fortes": len(core_breaking_nodes),
        "pontes_fraca_e_forte": len(edges_both),
        "pontes_so_forte": len(edges_strong_only),
        "pontes_so_fraca_fora_do_nucleo": len(edges_weak_only),
        "articulacoes_fraca_e_forte": len(nodes_both),
        "articulacoes_so_forte": len(nodes_strong_only),
        "tempo_ms": round(t_forte * 1000, 2),
    }


def acesso_por_portas(cfg, data, bbox_usado, componente, gset):
    """Fluxo maximo do nucleo ate as portas do bairro (o fluxo de acesso).

    As portas sao as interseccoes com uma rua que sai do POLIGONO oficial (a
    mesma fronteira que recorta a rede); a rede e' buscada com uma margem extra
    (GATEWAY_BUFFER_M) so para descobri-las. O universo e' a maior componente
    NAO dirigida (uset), e nao o nucleo fortemente conexo: uma porta pode ser so
    entrada ou so saida por mao unica e ainda assim ser acesso real ao resto da
    cidade.
    """
    banner("(C.2.6) ACESSO REAL: fluxo maximo NUCLEO -> GATEWAYS do bairro")
    uset = set(componente)
    gw_nodes = gateway_nodes(cfg, data, bbox_usado, uset)
    print(
        f"[nota] gateways dentro do nucleo fortemente conexo: "
        f"{len(gw_nodes & gset)} de {len(gw_nodes)} "
        f"(mao unica pode deixar um gateway fora do nucleo forte)"
    )

    # a ordem dos vertices da componente desempata a escolha do nucleo
    acc_gw = mf.gateway_access_flow(list(componente), data["undirected_edges"], gw_nodes, frac=0.2)
    print(
        f"Gateways identificados (ruas que cruzam o poligono oficial, "
        f"margem={GATEWAY_BUFFER_M}m): {acc_gw['n_gateways']}"
    )
    print(
        f"Rotas por ruas distintas do nucleo ate qualquer gateway "
        f"(acesso ao resto da cidade): {acc_gw['fluxo']} "
        f"(corte = {acc_gw['corte']} ruas, nucleo={acc_gw['n_origem']} nos)"
    )
    return acc_gw


def intermediacao(G, gset):
    """Intermediacao dirigida ponderada por tempo (Brandes), no nucleo forte."""
    banner("(C.4) INTERMEDIACAO dirigida ponderada por tempo (nucleo forte)")
    t0 = time.perf_counter()
    bsum = bt.summary(G, gset)
    print(
        f"Intermediacao maxima: {100 * bsum['max']:.1f}% dos pares "
        f"(no {bsum['no_max']}; nucleo de {bsum['n_nucleo']} nos); "
        f"{(time.perf_counter() - t0) * 1000:.0f} ms"
    )
    return {
        "max_pct_pares": round(100 * bsum["max"], 2),
        "no_max": bsum["no_max"],
        "n_nucleo": bsum["n_nucleo"],
    }


# ---------------------------------------------------------------------------
def main(cfg):
    t0_all = time.perf_counter()
    metrics = {}
    out = os.path.join(OUT_BASE, cfg.key)
    os.makedirs(out, exist_ok=True)

    data, bbox_usado = load_network(cfg)
    G = data["graph"]
    edges_u = [(u, v) for (u, v, _, _) in data["undirected_edges"]]

    metrics["rede"] = rede(cfg, data, bbox_usado, G, edges_u)
    metrics["conectividade"], comps, scc = conectividade(G, edges_u)

    # nucleo fortemente conexo gigante: usado nos indicadores seguintes
    gset = set(max(scc, key=len))
    # maior componente nao dirigida: universo do fluxo de acesso
    giant_und = max(comps, key=len)

    metrics["gargalos_estruturais"], aps, brs = estruturais_fracos(G, edges_u)
    metrics["gargalos_estruturais_dirigidos"] = estruturais_fortes(G, edges_u, gset, aps, brs)
    metrics["gargalo_acesso_gateway"] = acesso_por_portas(cfg, data, bbox_usado, giant_und, gset)
    metrics["intermediacao"] = intermediacao(G, gset)

    metrics["tempo_total_s"] = round(time.perf_counter() - t0_all, 2)
    with open(os.path.join(out, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    banner("CONCLUIDO")
    print(f"Metricas em: {out}")
    print(f"Tempo total: {metrics['tempo_total_s']} s")


def alvos_da_linha_de_comando(argumentos):
    """Sem argumento, so a Urca; 'all', os nove bairros; senao, os bairros dados."""
    args = [a.lower() for a in argumentos]
    if not args:
        return ["urca"]
    if args == ["all"]:
        return list(NEIGHBORHOODS)
    return args


if __name__ == "__main__":
    for chave in alvos_da_linha_de_comando(sys.argv[1:]):
        if chave not in NEIGHBORHOODS:
            print(f"[aviso] bairro desconhecido: {chave} (conhecidos: {', '.join(NEIGHBORHOODS)})")
            continue
        main(NEIGHBORHOODS[chave])
