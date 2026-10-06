"""
GARGALOS via FLUXO MAXIMO / CORTE MINIMO (algoritmo de Edmonds-Karp).

Vistos em sala: Ford-Fulkerson e sua especializacao Edmonds-Karp (busca do
caminho aumentante por BFS), e o Teorema do Fluxo Maximo / Corte Minimo:

    "O valor maximo de um fluxo O-D e' igual a capacidade minima de um
     corte que separa a origem O do destino D."

Aplicacao a mobilidade urbana: atribuindo CAPACIDADE 1 a cada rua, o fluxo
maximo entre duas regioes e' o numero de ROTAS por ruas distintas (aresta-
disjuntas) entre elas, e o CORTE MINIMO e' o menor conjunto de ruas cuja
interdicao isola uma regiao da outra — ou seja, o gargalo da rede.

Implementacao: Edmonds-Karp em O(V * E^2).
"""

from __future__ import annotations
from collections import deque


def edmonds_karp(nodes, capacity, source, sink):
    """Fluxo maximo de source a sink.

    capacity: dict (u, v) -> capacidade (>0). Arestas nao listadas tem cap 0.
    Retorna (valor_do_fluxo, fluxo, reachable, cut_edges):
      - fluxo: dict (u,v) -> fluxo enviado.
      - reachable: conjunto S do corte minimo (lado da origem).
      - cut_edges: arestas (u,v) com u em S e v fora de S (o corte minimo).
    """
    # grafo residual: capacidade restante por arco
    res: dict[tuple[int, int], float] = {}
    adj: dict[int, set[int]] = {u: set() for u in nodes}
    for (u, v), c in capacity.items():
        res[(u, v)] = res.get((u, v), 0) + c
        res.setdefault((v, u), 0)        # arco reverso (residual)
        adj[u].add(v)
        adj[v].add(u)

    flow_value = 0.0
    while True:
        # BFS por um caminho aumentante (Edmonds-Karp)
        prev = {source: None}
        q = deque([source])
        while q:
            u = q.popleft()
            if u == sink:
                break
            for v in adj[u]:
                if v not in prev and res.get((u, v), 0) > 1e-9:
                    prev[v] = u
                    q.append(v)
        if sink not in prev:
            break  # sem caminho aumentante -> fluxo maximo atingido

        # gargalo do caminho encontrado
        path = []
        v = sink
        while v is not None:
            path.append(v)
            v = prev[v]
        path.reverse()
        bottleneck = min(res[(path[i], path[i + 1])]
                         for i in range(len(path) - 1))
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            res[(a, b)] -= bottleneck
            res[(b, a)] = res.get((b, a), 0) + bottleneck
        flow_value += bottleneck

    # lado da origem no corte minimo = alcancaveis na rede residual
    reachable = set()
    q = deque([source])
    reachable.add(source)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in reachable and res.get((u, v), 0) > 1e-9:
                reachable.add(v)
                q.append(v)

    cut_edges = [(u, v) for (u, v), c in capacity.items()
                 if u in reachable and v not in reachable]

    # fluxo efetivo por arco (capacidade - residual)
    flow = {}
    for (u, v), c in capacity.items():
        f = c - res.get((u, v), 0)
        if f > 1e-9:
            flow[(u, v)] = f

    return flow_value, flow, reachable, cut_edges


def unit_capacity_network(undirected_edges):
    """Capacidade 1 por rua, nos dois sentidos (rede nao-dirigida).

    undirected_edges: lista de (u, v, ...) (extras ignorados).
    """
    cap = {}
    for e in undirected_edges:
        u, v = e[0], e[1]
        cap[(u, v)] = cap.get((u, v), 0) + 1
        cap[(v, u)] = cap.get((v, u), 0) + 1
    return cap


def _bfs_hops(adj, source):
    """Distancia em numero de arestas (BFS nao-dirigido)."""
    dist = {source: 0}
    q = deque([source])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def region_access_flow(node_list, undirected_edges, frac=0.2):
    """Fluxo maximo REGIAO-a-REGIAO ao longo do eixo mais alongado do bairro.

    Motivacao: o corte minimo entre DUAS interseccoes isoladas satura em 1
    nessas malhas (ha pontes por toda parte), entao nao mede o "gargalo" de
    acesso. Aqui medimos quantas ROTAS por ruas distintas (aresta-disjuntas)
    ligam um extremo do bairro ao outro, agregando cada extremo numa REGIAO.

    Definicao reproduzivel (sem eixo geografico escolhido a mao):
      1. dois polos p1, p2 = extremos do grafo por 'double sweep' em numero de
         arestas (BFS), o par de interseccoes mais distante uma da outra;
      2. REGIAO de origem = as `frac` interseccoes mais proximas de p1;
         REGIAO de destino = as `frac` mais proximas de p2 (sem sobreposicao);
      3. super-fonte -> origem e destino -> super-sumidouro, capacidade 1 por
         rua, e Edmonds-Karp entre elas.

    Retorna dict com polos, fluxo (nº de rotas distintas) e tamanho do corte.
    """
    S = set(node_list)
    adj = {u: set() for u in node_list}
    edges_in = []
    for e in undirected_edges:
        u, v = e[0], e[1]
        if u in S and v in S:
            adj[u].add(v); adj[v].add(u)
            edges_in.append((u, v))
    if len(node_list) < 2:
        return {"polo1": None, "polo2": None, "fluxo": 0, "corte": 0,
                "n_origem": 0, "n_destino": 0, "frac": frac}

    d0 = _bfs_hops(adj, node_list[0])
    p1 = max(d0, key=lambda u: d0[u])
    d1 = _bfs_hops(adj, p1)
    p2 = max(d1, key=lambda u: d1[u])
    d2 = _bfs_hops(adj, p2)

    k = max(1, int(round(frac * len(node_list))))
    src = set(sorted(node_list, key=lambda u: d1.get(u, 1 << 30))[:k])   # perto de p1
    snk = [u for u in sorted(node_list, key=lambda u: d2.get(u, 1 << 30))
           if u not in src][:k]                                          # perto de p2
    snk = set(snk)

    cap = dict(unit_capacity_network(edges_in))
    SS, TT = "__S__", "__T__"
    BIG = 10 ** 9
    for u in src:
        cap[(SS, u)] = BIG
    for v in snk:
        cap[(v, TT)] = BIG
    fmax, flow, reach, cut = edmonds_karp(list(node_list) + [SS, TT], cap, SS, TT)
    cut_real = [(u, v) for (u, v) in cut if u not in (SS, TT) and v not in (SS, TT)]
    return {"polo1": p1, "polo2": p2, "fluxo": int(fmax), "corte": len(cut_real),
            "n_origem": len(src), "n_destino": len(snk), "frac": frac}


def gateway_access_flow(node_list, undirected_edges, gateway_nodes, frac=0.2,
                        details=False):
    """Fluxo maximo NUCLEO-a-GATEWAYS: quantas rotas por ruas distintas ligam
    o interior do bairro aos pontos onde ele de fato se conecta ao resto da
    cidade.

    GATEWAY = interseccao do bairro (dentro de `node_list`) com pelo menos
    uma rua que cruza a fronteira do recorte original (calculado por quem
    chama esta funcao, comparando o grafo original com um grafo buscado com
    uma margem extra -- ver osm_loader.expand_bbox). Isso substitui a versao
    anterior (region_access_flow), que usava dois polos internos achados por
    'double sweep': aquela definicao nunca referenciava a fronteira do
    bairro e por isso nao podia, por construcao, medir acesso ao resto da
    cidade -- media apenas a travessia interna mais estreita ao longo do
    eixo mais alongado do proprio recorte.

    Definicao:
      1. GATEWAYS = `gateway_nodes` (dados por quem chama), restritos a
         `node_list`.
      2. Distancia (em numero de arestas) de cada no interior ao gateway
         mais proximo, por BFS multi-fonte a partir do conjunto de gateways.
      3. NUCLEO (regiao de origem) = as `frac` interseccoes NAO-gateway mais
         distantes de qualquer gateway -- o "fundo" do bairro.
      4. super-fonte -> nucleo e GATEWAYS -> super-sumidouro, capacidade 1
         por rua, Edmonds-Karp entre elas.

    Retorna dict com os gateways usados, fluxo (numero de rotas distintas
    nucleo->gateways) e tamanho do corte.
    """
    S = set(node_list)
    adj = {u: set() for u in S}
    edges_in = []
    for e in undirected_edges:
        u, v = e[0], e[1]
        if u in S and v in S:
            adj[u].add(v); adj[v].add(u)
            edges_in.append((u, v))

    gw = set(gateway_nodes) & S
    if not gw or len(S) < 2:
        return {"gateways": sorted(gw), "fluxo": 0, "corte": 0,
                "n_origem": 0, "n_gateways": len(gw), "frac": frac}

    # distancia (em arestas) de cada no ao gateway mais proximo (BFS
    # multi-fonte: todos os gateways comecam na fila com distancia 0)
    dist = {g: 0 for g in gw}
    q = deque(gw)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)

    interior_only = [u for u in S if u not in gw]
    k = max(1, int(round(frac * len(S))))
    src = set(sorted(interior_only, key=lambda u: -dist.get(u, 0))[:k])

    cap = dict(unit_capacity_network(edges_in))
    SS, TT = "__S__", "__T__"
    BIG = 10 ** 9
    for u in src:
        cap[(SS, u)] = BIG
    for g in gw:
        cap[(g, TT)] = BIG
    fmax, flow, reach, cut = edmonds_karp(list(S) + [SS, TT], cap, SS, TT)
    cut_real = [(u, v) for (u, v) in cut if u not in (SS, TT) and v not in (SS, TT)]
    out = {"gateways": sorted(gw), "fluxo": int(fmax), "corte": len(cut_real),
           "n_origem": len(src), "n_gateways": len(gw), "frac": frac}
    if details:
        # so' para analise/figura (localiza_corte.py); fora de metrics.json
        out["origem"] = sorted(src)
        out["corte_arestas"] = cut_real
        out["lado_origem"] = len(reach) - 1     # nos do lado da origem (sem a super-fonte)
    return out


def _core_and_gateways(node_list, undirected_edges, gateway_nodes, frac):
    """Mesma regiao de origem (nucleo) e mesmo conjunto de gateways usados por
    gateway_access_flow, para que as variantes por NO e DIRIGIDA sejam
    diretamente comparaveis com a por aresta. Retorna (S, adj, edges_in, gw,
    src)."""
    S = set(node_list)
    adj = {u: set() for u in S}
    edges_in = []
    for e in undirected_edges:
        u, v = e[0], e[1]
        if u in S and v in S:
            adj[u].add(v); adj[v].add(u)
            edges_in.append((u, v))
    gw = set(gateway_nodes) & S
    if not gw or len(S) < 2:
        return S, adj, edges_in, gw, set()
    dist = {g: 0 for g in gw}
    q = deque(gw)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    interior_only = [u for u in S if u not in gw]
    k = max(1, int(round(frac * len(S))))
    src = set(sorted(interior_only, key=lambda u: -dist.get(u, 0))[:k])
    return S, adj, edges_in, gw, src


def gateway_access_flow_nodes(node_list, undirected_edges, gateway_nodes,
                              frac=0.2, details=False):
    """Versao por INTERSECCOES (vertices) do fluxo de acesso: quantas rotas
    internamente disjuntas por INTERSECCOES (teorema de Menger) ligam o nucleo
    do bairro as suas portas de acesso.

    Complementa gateway_access_flow (que conta rotas disjuntas por RUAS). Usa a
    transformacao padrao de divisao de nos: cada vertice vira v_in -> v_out.
    So os vertices INTERIORES (nao sao nem nucleo de origem nem porta de
    acesso) recebem capacidade 1 nessa aresta interna; o nucleo de origem e as
    portas ficam INCORTAVEIS (capacidade infinita). Sem isso, o valor ficaria
    trivialmente limitado pelo numero de portas, medindo duas vezes a mesma
    coisa; com portas incortaveis, a medida isola o afunilamento interno ate a
    fronteira. As arestas de rua ficam com capacidade infinita.

    Retorna o numero de rotas disjuntas por interseccoes e, se details=True, as
    interseccoes do corte minimo (para marcar na figura)."""
    S, adj, edges_in, gw, src = _core_and_gateways(
        node_list, undirected_edges, gateway_nodes, frac)
    if not gw or not src:
        return {"gateways": sorted(gw), "fluxo": 0, "corte": 0,
                "n_origem": 0, "n_gateways": len(gw), "frac": frac}

    BIG = 10 ** 9
    uncortavel = src | gw                     # nucleo e portas sao incortaveis
    cap = {}
    for w in S:                               # aresta interna v_in -> v_out
        cap[((w, "i"), (w, "o"))] = BIG if w in uncortavel else 1
    for (u, v) in edges_in:                   # ruas: capacidade infinita
        cap[((u, "o"), (v, "i"))] = BIG
        cap[((v, "o"), (u, "i"))] = BIG
    SS, TT = "__S__", "__T__"
    for u in src:
        cap[(SS, (u, "i"))] = BIG
    for g in gw:
        cap[((g, "o"), TT)] = BIG
    nodes = [SS, TT] + [(w, s) for w in S for s in ("i", "o")]
    fmax, flow, reach, cut = edmonds_karp(nodes, cap, SS, TT)
    # um arco (w_in -> w_out) no corte minimo = a interseccao w e' um ponto de
    # corte por vertices; vertices incortaveis nunca entram num corte finito.
    cut_nodes = sorted({a[0] for (a, b) in cut
                        if isinstance(a, tuple) and isinstance(b, tuple)
                        and a[0] == b[0]})
    out = {"gateways": sorted(gw), "fluxo": int(fmax), "corte": len(cut_nodes),
           "n_origem": len(src), "n_gateways": len(gw), "frac": frac}
    if details:
        out["intersecoes_de_corte"] = cut_nodes
    return out


def gateway_access_flow_directed(node_list, directed_arcs, undirected_edges,
                                 gateway_nodes, frac=0.2):
    """Versao DIRIGIDA do fluxo de acesso: respeita o sentido das vias. Mesma
    regiao de origem (nucleo) e mesmas portas da versao por aresta, mas a
    capacidade unitaria e' atribuida por ARCO (so no sentido real da via), e
    nao nos dois sentidos de cada rua. Uma saida de mao unica so conta no
    sentido que de fato permite deixar o bairro, de modo que o fluxo dirigido
    e' menor ou igual ao nao dirigido; se for menor, a direcao tem efeito
    proprio sobre o acesso.

    directed_arcs: iteravel de (u, v) (arcos dirigidos de G.edges)."""
    S, adj, edges_in, gw, src = _core_and_gateways(
        node_list, undirected_edges, gateway_nodes, frac)
    if not gw or not src:
        return {"gateways": sorted(gw), "fluxo": 0, "corte": 0,
                "n_origem": 0, "n_gateways": len(gw), "frac": frac}

    cap = {}
    for (u, v) in directed_arcs:              # capacidade 1 por arco, no sentido real
        if u in S and v in S:
            cap[(u, v)] = cap.get((u, v), 0) + 1
    SS, TT = "__S__", "__T__"
    BIG = 10 ** 9
    for u in src:
        cap[(SS, u)] = BIG
    for g in gw:
        cap[(g, TT)] = BIG
    fmax, flow, reach, cut = edmonds_karp(list(S) + [SS, TT], cap, SS, TT)
    cut_real = [(u, v) for (u, v) in cut if u not in (SS, TT) and v not in (SS, TT)]
    return {"gateways": sorted(gw), "fluxo": int(fmax), "corte": len(cut_real),
            "n_origem": len(src), "n_gateways": len(gw), "frac": frac}
