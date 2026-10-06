"""
Pipeline principal — Tema 5: Grafos em mobilidade urbana
Estudo de caso: bairro da URCA (Rio de Janeiro), dados reais do OpenStreetMap.

Usa SOMENTE algoritmos vistos na disciplina:
  (A) CONECTIVIDADE      -> BFS/DFS; componentes; fortemente conexo (BFS no
                            grafo e no reverso); articulacoes e pontes pela
                            definicao.
  (B) ROTAS ALTERNATIVAS -> Dijkstra (e Bellman-Ford como verificacao);
                            rota alternativa recalculada ao bloquear um trecho.
  (C) GARGALOS           -> estruturais (pontes/articulacoes, fracos e
                            fortes) e por fluxo maximo / corte minimo
                            (Edmonds-Karp).

Gera figuras (output/) e metricas (output/metrics.json).

Uso:  py main.py
"""

from __future__ import annotations
import json
import math
import os
import sys
import time

from graph import Graph
from network import load_network, gateway_nodes, GATEWAY_BUFFER_M
import betweenness as bt
from neighborhoods import NEIGHBORHOODS, resolve_od
import connectivity as cc
import shortest_paths as sp
import maxflow as mf
import visualize as viz

OUT_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

def banner(t):
    print("\n" + "=" * 64 + f"\n {t}\n" + "=" * 64)


# ---------------------------------------------------------------------------
# Copias do grafo com uma aresta ou um vertice removido, para testar pontes e
# articulacoes FORTES (conexidade dirigida) restritas ao nucleo. Usa somente
# a estrutura Graph existente (sem bibliotecas de grafos), copiando os
# atributos ja calculados de cada arco (length, travel_time) em vez de
# recalcula-los a partir das coordenadas.
# ---------------------------------------------------------------------------
def _copia_sem_aresta(G: Graph, u: int, v: int) -> Graph:
    H = Graph()
    for nid, (x, y) in G.coords.items():
        H.add_node(nid, x, y)
    par = {u, v}
    for e in G.edges:
        if {e.u, e.v} == par:
            continue
        H._add_directed(e.u, e.v, e.length, e.travel_time, e.oneway)
    return H


def _copia_sem_no(G: Graph, w: int) -> Graph:
    H = Graph()
    for nid, (x, y) in G.coords.items():
        if nid != w:
            H.add_node(nid, x, y)
    for e in G.edges:
        if e.u == w or e.v == w:
            continue
        H._add_directed(e.u, e.v, e.length, e.travel_time, e.oneway)
    return H


def _nucleo_intacto(H: Graph, alvo: set[int]) -> bool:
    """Os vertices de `alvo` (o nucleo original, menos o removido se for o
    caso) ainda formam uma unica componente fortemente conexa em H?"""
    for comp in cc.strongly_connected_components(H):
        if alvo <= set(comp):
            return True
    return False


def main(cfg):
    t0_all = time.perf_counter()
    metrics = {}
    OUT = os.path.join(OUT_BASE, cfg.key)
    os.makedirs(OUT, exist_ok=True)

    # ----------------------------------------------------------- carrega mapa
    data, bbox_usado = load_network(cfg)
    G = data["graph"]
    edges_u = [(u, v) for (u, v, _, _) in data["undirected_edges"]]
    nodes = G.nodes()
    banner(f"REDE DE RUAS — {cfg.display_name.upper()}, OpenStreetMap")
    print(f"Pontos OSM brutos: {data['n_raw_nodes']} | vias OSM: {data['n_ways']}")
    print(f"Apos simplificacao: {G.n} intersecoes (V), {G.m} arcos (E), "
          f"{len(edges_u)} trechos de rua")
    metrics["rede"] = {
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
    viz.fig_overview(data, os.path.join(OUT, f"01_{cfg.key}.png"),
                     display_name=cfg.display_name)

    # --------------------------------------------------------- conectividade
    banner("(A) CONECTIVIDADE")
    t0 = time.perf_counter()
    comps = cc.connected_components(nodes, edges_u)
    scc = cc.strongly_connected_components(G)
    t_conn = time.perf_counter() - t0
    comp_sizes = sorted((len(c) for c in comps), reverse=True)
    scc_sizes = sorted((len(c) for c in scc), reverse=True)
    deg = {u: 0 for u in nodes}
    for (u, v) in edges_u:
        deg[u] += 1; deg[v] += 1
    dead_ends = [u for u in nodes if deg[u] == 1]
    n_nao_triviais = sum(1 for c in scc if len(c) > 1)
    print(f"Componentes (nao-dirigido): {len(comps)} (maior = {comp_sizes[0]})")
    print(f"Componentes fortemente conexas: {len(scc)} (maior = {scc_sizes[0]})")
    print(f"Intersecoes fora da CFC gigante: {G.n - scc_sizes[0]} "
          f"(efeito das mãos únicas)")
    print(f"Ruas sem saida (cul-de-sac, grau 1): {len(dead_ends)}")
    print(f"Tempo: {t_conn*1000:.1f} ms")
    metrics["conectividade"] = {
        "componentes": len(comps),
        "maior_componente": comp_sizes[0],
        "scc": len(scc),
        "maior_scc": scc_sizes[0],
        "fora_da_scc_gigante": G.n - scc_sizes[0],
        "ruas_sem_saida": len(dead_ends),
        "tempo_ms": round(t_conn * 1000, 2),
    }
    viz.fig_scc(data, scc, os.path.join(OUT, "02_scc.png"))

    # nucleo fortemente conexo gigante -- usado no restante do pipeline
    giant = max(scc, key=len)
    gset = set(giant)
    gl = list(giant)

    # maior componente NAO-dirigida -- universo certo para "existe uma rua
    # de saida", que e' uma pergunta nao-dirigida (capacidade 1 por rua nos
    # dois sentidos, C.2.6 abaixo). Restringir a pergunta de acesso fisico
    # ao nucleo FORTEMENTE conexo (ida-e-volta) descartaria gateways reais
    # que so permitem entrar OU so sair por mao unica -- ver nota em C.2.6.
    giant_und = max(comps, key=len)
    uset = set(giant_und)
    ul = list(giant_und)

    # ---------------------------------------------- gargalos estruturais
    banner("(C.1) GARGALOS ESTRUTURAIS: pontes e articulacoes (definicao)")
    t0 = time.perf_counter()
    aps = cc.articulation_points(nodes, edges_u)
    brs = cc.bridges(nodes, edges_u)
    t_struct = time.perf_counter() - t0
    print(f"Pontos de articulacao: {len(aps)} de {G.n} intersecoes")
    print(f"Pontes (cut-edges): {len(brs)} de {len(edges_u)} trechos")
    print(f"Tempo: {t_struct*1000:.1f} ms")
    metrics["gargalos_estruturais"] = {
        "articulacoes": len(aps),
        "pontes": len(brs),
        "tempo_ms": round(t_struct * 1000, 2),
    }
    viz.fig_critical(data, brs, aps, os.path.join(OUT, "03_criticos.png"))

    # ------------------------------------- gargalos estruturais DIRIGIDOS
    banner("(C.1.5) GARGALOS ESTRUTURAIS DIRIGIDOS: pontes/articulacoes "
           "FORTES restritas ao nucleo")
    t0 = time.perf_counter()
    weak_edge_pairs = {frozenset(e) for e in brs}
    aps_set = set(aps)

    # pares de nos unicos dentro do nucleo (uma rua com trechos paralelos
    # entre o mesmo par de intersecoes conta como UMA rua para efeito de
    # fechamento: fechar a rua fecha os dois trechos ao mesmo tempo).
    pares_nucleo = []
    vistos = set()
    for (u, v) in edges_u:
        if u in gset and v in gset:
            k = frozenset((u, v))
            if k not in vistos:
                vistos.add(k)
                pares_nucleo.append((u, v))

    core_breaking_edges = []
    for (u, v) in pares_nucleo:
        H = _copia_sem_aresta(G, u, v)
        if not _nucleo_intacto(H, gset):
            core_breaking_edges.append((u, v))

    core_breaking_nodes = []
    for u in gset:
        H = _copia_sem_no(G, u)
        if not _nucleo_intacto(H, gset - {u}):
            core_breaking_nodes.append(u)
    t_forte = time.perf_counter() - t0

    edges_both = [e for e in core_breaking_edges if frozenset(e) in weak_edge_pairs]
    edges_strong_only = [e for e in core_breaking_edges if frozenset(e) not in weak_edge_pairs]
    core_pairs_set = {frozenset(e) for e in core_breaking_edges}
    edges_weak_only = [e for e in brs if frozenset(e) not in core_pairs_set]

    nodes_both = [n for n in core_breaking_nodes if n in aps_set]
    nodes_strong_only = [n for n in core_breaking_nodes if n not in aps_set]

    print(f"Nucleo fortemente conexo: {len(gset)} intersecoes")
    print(f"Pontes fortes (fragmentam o nucleo): {len(core_breaking_edges)} "
          f"de {len(pares_nucleo)} pares de rua do nucleo")
    print(f"Articulacoes fortes (fragmentam o nucleo): {len(core_breaking_nodes)} "
          f"de {len(gset)} intersecoes do nucleo")
    print(f"  cruzamento pontes:       fraca+forte={len(edges_both)}  "
          f"so forte={len(edges_strong_only)}  so fraca={len(edges_weak_only)}")
    print(f"  cruzamento articulacoes: fraca+forte={len(nodes_both)}  "
          f"so forte={len(nodes_strong_only)}")
    print(f"Tempo: {t_forte*1000:.1f} ms")
    metrics["gargalos_estruturais_dirigidos"] = {
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
    viz.fig_strong_gargalos(data, gl, edges_both, edges_strong_only,
                             edges_weak_only, nodes_both, nodes_strong_only,
                             os.path.join(OUT, "07_gargalos_dirigidos_categorizado.png"))

    # ---- escolhe origem (O) e destino (D) para o corte minimo -------------
    # Cada bairro declara seu proprio criterio em neighborhoods.py; a
    # heuristica da Urca fica congelada (ver rationale de cada config).
    od_ctx = {"gset": gset, "deg": deg, "giant": giant, "gl": gl}
    O, D = resolve_od(cfg.mincut_od, G, od_ctx)

    # ---------------------------------------------- gargalo por fluxo/corte
    banner("(C.2) GARGALOS POR FLUXO MAXIMO / CORTE MINIMO (Edmonds-Karp)")
    cap = mf.unit_capacity_network(data["undirected_edges"])
    t0 = time.perf_counter()
    fmax, flow, reach, cut = mf.edmonds_karp(nodes, cap, O, D)
    t_flow = time.perf_counter() - t0
    print(f"Origem O={O}  Destino D={D}")
    print(f"Fluxo maximo (rotas por ruas distintas): {int(fmax)}")
    print(f"Corte minimo (ruas que isolam O de D): {len(cut)}")
    print(f"  -> {cut}")
    print(f"Tempo Edmonds-Karp: {t_flow*1000:.1f} ms")

    # a rota fisica de O a D pode ter, alem do corte relatado pelo Edmonds-
    # Karp, outros trechos que, isoladamente, tambem sao corte de valor 1
    # (pontos unicos de falha em serie na mesma rota; ver Secao 4.4).
    rota_od, _ = sp.shortest_path(G, O, D)
    rota_arestas = list(zip(rota_od, rota_od[1:])) if rota_od else []
    adj_und = cc._undirected_adjacency(nodes, edges_u)
    reportado = {frozenset(e) for e in cut}
    alt_cut_edges = []
    for (u, v) in rota_arestas:
        if frozenset((u, v)) in reportado:
            continue
        comps_sem = cc._count_components(nodes, adj_und, skip_edge={u, v})
        comps_base = cc._count_components(nodes, adj_und)
        if comps_sem > comps_base:
            # confirma que O e D ficam em componentes diferentes sem essa rua
            seen = {O}
            stack = [O]
            while stack:
                x = stack.pop()
                for w in adj_und[x]:
                    if w in seen or frozenset((x, w)) == frozenset((u, v)):
                        continue
                    seen.add(w); stack.append(w)
            if D not in seen:
                alt_cut_edges.append((u, v))
    print(f"Rota fisica O->D: {len(rota_arestas)} rua(s); outros pontos "
          f"unicos de falha na mesma rota: {alt_cut_edges}")

    metrics["gargalo_corte_minimo"] = {
        "origem": O, "destino": D,
        "fluxo_maximo": int(fmax),
        "corte_minimo": len(cut),
        "ruas_do_corte": [list(e) for e in cut],
        "outros_pontos_unicos_de_falha_na_rota": [list(e) for e in alt_cut_edges],
        "tempo_ms": round(t_flow * 1000, 2),
    }
    viz.fig_mincut(data, O, D, cut, reach, fmax,
                   os.path.join(OUT, "04_corte_minimo.png"),
                   alt_cut_edges=alt_cut_edges)

    # ------------------------------------ acesso: fluxo regiao-a-regiao
    # O corte minimo no-a-no (acima) satura em 1 nessas malhas, porque ha
    # pontes por toda parte. Para MEDIR o gargalo de acesso do bairro,
    # agregamos cada extremo do eixo mais alongado numa REGIAO e medimos
    # quantas rotas por ruas distintas ligam uma regiao a outra.
    banner("(C.2.5) ACESSO: fluxo maximo REGIAO-a-REGIAO (eixo do bairro) "
           "[verificacao de sanidade -- ver C.2.6 para a metrica de acesso real]")
    acc = mf.region_access_flow(gl, data["undirected_edges"], frac=0.2)
    print(f"Polos p1={acc['polo1']} p2={acc['polo2']} | regioes de "
          f"{acc['n_origem']}/{acc['n_destino']} nos (frac={acc['frac']})")
    print(f"Rotas por ruas distintas entre os DOIS EXTREMOS INTERNOS do "
          f"bairro (nao e' acesso ao resto da cidade): "
          f"{acc['fluxo']} (corte = {acc['corte']} ruas)")
    metrics["travessia_interna_polos"] = acc

    # ---------------------------------- acesso real: nucleo -> GATEWAYS ----
    # `acc` acima mede a travessia interna mais estreita entre dois polos
    # achados dentro do proprio bairro -- nao referencia a fronteira do
    # recorte, entao nao mede literalmente "conexao com o resto da cidade".
    # Aqui buscamos o mesmo bairro com uma margem extra (GATEWAY_BUFFER_M)
    # so para descobrir quais interseccoes tem uma rua saindo do POLIGONO
    # oficial (a mesma fronteira usada para recortar a rede, nos tres
    # bairros): essas sao os GATEWAYS de verdade, e o fluxo nucleo->gateways
    # e' o que o artigo quer afirmar (rotas ate o resto da cidade).
    banner("(C.2.6) ACESSO REAL: fluxo maximo NUCLEO -> GATEWAYS do bairro")
    # restrito a' maior componente NAO-dirigida (uset), nao ao nucleo
    # fortemente conexo: um gateway pode ser so-entrada ou so-saida por mao
    # unica e ainda assim ser uma rua de acesso real ao resto da cidade.
    gw_nodes = gateway_nodes(cfg, data, bbox_usado, uset)
    print(f"[nota] gateways dentro do nucleo fortemente conexo: "
          f"{len(gw_nodes & gset)} de {len(gw_nodes)} "
          f"(mao unica pode deixar um gateway fora do nucleo forte)")

    acc_gw = mf.gateway_access_flow(ul, data["undirected_edges"], gw_nodes, frac=0.2)
    print(f"Gateways identificados (ruas que cruzam o poligono oficial, "
          f"margem={GATEWAY_BUFFER_M}m): {acc_gw['n_gateways']}")
    print(f"Rotas por ruas distintas do nucleo ate qualquer gateway "
          f"(acesso ao resto da cidade): {acc_gw['fluxo']} "
          f"(corte = {acc_gw['corte']} ruas, nucleo={acc_gw['n_origem']} nos)")
    metrics["gargalo_acesso_gateway"] = acc_gw

    # variante por INTERSECCOES (Menger): rotas internamente disjuntas por
    # vertices; so interiores sao cortaveis, nucleo e portas incortaveis.
    acc_gw_v = mf.gateway_access_flow_nodes(ul, data["undirected_edges"],
                                            gw_nodes, frac=0.2, details=True)
    print(f"Rotas disjuntas por INTERSECCOES (nucleo->gateways): "
          f"{acc_gw_v['fluxo']} (corte = {acc_gw_v['corte']} interseccoes)")
    # variante DIRIGIDA: capacidade 1 por arco (respeita mao unica).
    acc_gw_d = mf.gateway_access_flow_directed(
        ul, [(e.u, e.v) for e in G.edges], data["undirected_edges"],
        gw_nodes, frac=0.2)
    print(f"Rotas disjuntas por ruas DIRIGIDAS (nucleo->gateways, saida): "
          f"{acc_gw_d['fluxo']} (corte = {acc_gw_d['corte']} arcos)")
    metrics["gargalo_acesso_gateway_vertices"] = {
        k: v for k, v in acc_gw_v.items() if k != "intersecoes_de_corte"}
    metrics["gargalo_acesso_gateway_vertices"]["intersecoes_de_corte"] = \
        acc_gw_v.get("intersecoes_de_corte", [])
    metrics["gargalo_acesso_gateway_dirigido"] = acc_gw_d

    # ------------------------------------------------ intermediacao (Brandes)
    banner("(C.4) INTERMEDIACAO dirigida ponderada por tempo (nucleo forte)")
    t0 = time.perf_counter()
    bsum = bt.summary(G, gset)
    print(f"Intermediacao maxima: {100*bsum['max']:.1f}% dos pares "
          f"(no {bsum['no_max']}; nucleo de {bsum['n_nucleo']} nos); "
          f"{(time.perf_counter()-t0)*1000:.0f} ms")
    metrics["intermediacao"] = {
        "max_pct_pares": round(100 * bsum["max"], 2),
        "no_max": bsum["no_max"],
        "n_nucleo": bsum["n_nucleo"],
    }

    # ---------------------------------------------------- rotas alternativas
    banner("(B) ROTAS ALTERNATIVAS (Dijkstra)")
    # par O-D DENTRO da grade residencial (onde a malha oferece redundancia),
    # para demonstrar de fato uma rota alternativa.
    Or, Dr = resolve_od(cfg.altroute_od, G, od_ctx)
    t0 = time.perf_counter()
    main_route, main_cost = sp.shortest_path(G, Or, Dr)
    t_dij = time.perf_counter() - t0
    # verificacao independente com Bellman-Ford
    t0 = time.perf_counter()
    bf_dist, _ = sp.bellman_ford(G, Or)
    t_bf = time.perf_counter() - t0
    bf_cost = bf_dist.get(Dr, math.inf)
    confere = abs(bf_cost - main_cost) < 1e-6

    # bloqueia um trecho da rota principal (preferindo uma ponte/corte) e
    # recalcula -> rota alternativa
    # Para DEMONSTRAR uma rota alternativa, bloqueia um trecho da rota que NAO
    # seja ponte (assim existe desvio pela malha). Trechos do meio primeiro.
    bridge_set = {frozenset(e) for e in brs}
    route_pairs = list(zip(main_route, main_route[1:])) if main_route else []
    order = sorted(range(len(route_pairs)),
                   key=lambda i: abs(i - len(route_pairs) / 2))
    blocked_edge = None
    for i in order:
        a, b = route_pairs[i]
        if frozenset((a, b)) not in bridge_set:
            blocked_edge = (a, b)
            break
    # quantas pontes a rota atravessa (trechos sem alternativa)
    route_bridges = [pair for pair in route_pairs
                     if frozenset(pair) in bridge_set]
    blocked = {blocked_edge, (blocked_edge[1], blocked_edge[0])} if blocked_edge else set()
    alt_route, alt_cost = sp.alternative_route(G, Or, Dr, blocked)

    print(f"Rota principal: {main_cost/60:.2f} min, {len(main_route)} intersecoes")
    print(f"Verificacao Bellman-Ford: {bf_cost/60:.2f} min "
          f"({'confere' if confere else 'DIVERGE'}); "
          f"Dijkstra {t_dij*1000:.1f} ms vs Bellman-Ford {t_bf*1000:.1f} ms")
    print(f"Origem Or={Or}  Destino Dr={Dr}  (dentro da grade residencial)")
    if alt_route:
        extra = 100.0 * (alt_cost - main_cost) / main_cost
        print(f"Trecho (nao-ponte) bloqueado: {blocked_edge}")
        print(f"Rota alternativa: {alt_cost/60:.2f} min  ({extra:+.1f}% vs principal)")
    else:
        print(f"Sem rota alternativa ao bloquear {blocked_edge}.")
    print(f"A rota atravessa {len(route_bridges)} ponte(s) — trechos SEM "
          f"alternativa (fechá-los desconecta a rota).")
    metrics["rotas_alternativas"] = {
        "origem": Or, "destino": Dr,
        "rota_principal_min": round(main_cost / 60, 2),
        "intersecoes_rota": len(main_route),
        "bellman_ford_confere": confere,
        "tempo_dijkstra_ms": round(t_dij * 1000, 2),
        "tempo_bellman_ford_ms": round(t_bf * 1000, 2),
        "trecho_bloqueado": list(blocked_edge) if blocked_edge else None,
        "rota_alternativa_min": (round(alt_cost / 60, 2)
                                 if alt_route else None),
        "acrescimo_pct": (round(100.0 * (alt_cost - main_cost) / main_cost, 1)
                          if alt_route else None),
        "pontes_na_rota": len(route_bridges),
    }
    viz.fig_routes(data, main_route, alt_route, Or, Dr, blocked,
                   os.path.join(OUT, "05_rotas.png"))

    # ------------------------------------------------------------ resiliencia
    banner("(C.3) RESILIENCIA: impacto EXAUSTIVO de cada ponte/articulacao "
           "forte sobre o nucleo")
    t0 = time.perf_counter()
    all_pairs = [(a, b) for a in gl for b in gl if a != b]
    print(f"Pares origem-destino exaustivos no nucleo: {len(all_pairs)}")

    def custos(blocked_edges=None, blocked_node=None):
        # Um Dijkstra por ORIGEM (le todos os destinos do mapa de distancias),
        # em vez de um por par: mesma saida exata, ~V vezes menos Dijkstras.
        # Semantica preservada: destino == no removido conta como desconectado
        # (b == blocked_node -> inf); origem == no removido usa blocked_nodes,
        # que so bloqueia a ENTRADA no no removido, nao a saida dele.
        out = {}
        blocked_nodes = {blocked_node} if blocked_node is not None else None
        for a in gl:
            dist, _ = sp.dijkstra(G, a, target=None,
                                   blocked_edges=blocked_edges,
                                   blocked_nodes=blocked_nodes)
            for b in gl:
                if a == b:
                    continue
                if blocked_node is not None and b == blocked_node:
                    out[(a, b)] = math.inf
                else:
                    out[(a, b)] = dist.get(b, math.inf)
        return out

    base_costs = custos()

    def resumo(valores):
        vals = sorted(valores)
        n = len(vals)
        med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        return {"min": vals[0], "mediana": med, "max": vals[-1]}

    impacto_pontes = []
    deltas_min_todos = []
    n_binarias = 0
    for (u, v) in core_breaking_edges:
        novo = custos(blocked_edges={(u, v), (v, u)})
        desconectados = sum(1 for k in base_costs
                             if base_costs[k] != math.inf and novo[k] == math.inf)
        deltas = [(novo[k] - base_costs[k]) / 60 for k in base_costs
                  if base_costs[k] != math.inf and novo[k] != math.inf
                  and novo[k] > base_costs[k] + 1e-9]
        impacto_pontes.append(desconectados)
        if deltas:
            deltas_min_todos.extend(deltas)
        else:
            n_binarias += 1

    impacto_nos = []
    for u in core_breaking_nodes:
        novo = custos(blocked_node=u)
        desconectados = sum(1 for k in base_costs
                             if base_costs[k] != math.inf and novo[k] == math.inf)
        impacto_nos.append(desconectados)

    t_res = time.perf_counter() - t0
    resumo_pontes = resumo(impacto_pontes)
    resumo_nos = resumo(impacto_nos)
    resumo_deltas = resumo(deltas_min_todos) if deltas_min_todos else None

    print(f"Pontes fortes, pares desconectados: min={resumo_pontes['min']} "
          f"mediana={resumo_pontes['mediana']} max={resumo_pontes['max']}")
    print(f"  binarias (sem desvio parcial): {n_binarias}  "
          f"com desvio parcial: {len(core_breaking_edges) - n_binarias}")
    if resumo_deltas:
        print(f"  desvio parcial ({len(deltas_min_todos)} pares): "
              f"min={resumo_deltas['min']:.2f} min "
              f"mediana={resumo_deltas['mediana']:.2f} min "
              f"max={resumo_deltas['max']:.2f} min")
    print(f"Articulacoes fortes, pares desconectados: min={resumo_nos['min']} "
          f"mediana={resumo_nos['mediana']} max={resumo_nos['max']}")
    print(f"Tempo: {t_res*1000:.1f} ms")

    metrics["resiliencia"] = {
        "n_pares_nucleo": len(all_pairs),
        "pontes_fortes": {
            "n": len(core_breaking_edges),
            "pares_desconectados": resumo_pontes,
            "binarias": n_binarias,
            "com_desvio_parcial": len(core_breaking_edges) - n_binarias,
            "n_pares_com_desvio_parcial": len(deltas_min_todos),
            "acrescimo_min": resumo_deltas,
        },
        "articulacoes_fortes": {
            "n": len(core_breaking_nodes),
            "pares_desconectados": resumo_nos,
        },
        "tempo_ms": round(t_res * 1000, 2),
    }

    # ------------------------------------------------------------------ saida
    metrics["tempo_total_s"] = round(time.perf_counter() - t0_all, 2)
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    banner("CONCLUIDO")
    print(f"Figuras e metricas em: {OUT}")
    print(f"Tempo total: {metrics['tempo_total_s']} s")


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]
    if not args:
        alvos = ["urca"]                       # retrocompatibilidade: so a Urca
    elif args == ["all"]:
        alvos = list(NEIGHBORHOODS.keys())
    else:
        alvos = args
    for _key in alvos:
        if _key not in NEIGHBORHOODS:
            print(f"[aviso] bairro desconhecido: {_key} "
                  f"(conhecidos: {', '.join(NEIGHBORHOODS)})")
            continue
        main(NEIGHBORHOODS[_key])