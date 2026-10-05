"""
Carregamento UNICO da rede de cada bairro, compartilhado por main.py, pelos
scripts de figura e pelos de sensibilidade.

Regra de recorte (a mesma para os TRES bairros): o retangulo manual de
`neighborhoods.py` e' so um ENVELOPE de busca; ele e' unido ao retangulo do
poligono administrativo oficial (Data.Rio/IPP, `polygons.py`) para garantir
cobertura total, e o grafo e' recortado por esse poligono. Assim, a fronteira
do bairro e' a mesma (o poligono oficial) tanto para a rede analisada quanto
para a definicao das portas de acesso (`gateway_nodes`).

Por que nao usar so o retangulo: ele cortava a rede de forma desigual entre
bairros. Em Copacabana invadia o territorio de Botafogo (158 de 496
interseccoes); em Urca e Botafogo, o poligono oficial e' MAIOR que o
retangulo manual, e o retangulo truncava a rede na borda.
"""

from __future__ import annotations

from osm_loader import load_neighborhood, expand_bbox
import polygons as pg

# margem padrao (metros) alem do envelope, so' para achar a primeira
# interseccao alem da fronteira em toda rua que a cruza.
GATEWAY_BUFFER_M = 400


def union_bbox(bbox_a: str, bbox_b: str) -> str:
    """Menor bbox 'S,W,N,E' que contem os dois bbox dados."""
    sa, wa, na, ea = (float(x) for x in bbox_a.split(","))
    sb, wb, nb, eb = (float(x) for x in bbox_b.split(","))
    return f"{min(sa, sb)},{min(wa, wb)},{max(na, nb)},{max(ea, eb)}"


def load_network(cfg, clip: bool = True) -> "tuple[dict, str]":
    """Carrega a rede do bairro. Retorna (data, bbox_usado).

    clip=True (padrao, usado em todo o artigo): envelope = uniao do retangulo
    manual com o do poligono oficial; grafo recortado pelo poligono.
    clip=False: so' o retangulo manual, sem recorte (usado apenas para
    comparar com a versao antiga em analises de sensibilidade).
    """
    if not clip:
        return load_neighborhood(cfg.key, cfg.bbox), cfg.bbox
    poly = pg.fetch_bairro_polygon(cfg.display_name)
    bbox_usado = union_bbox(cfg.bbox, pg.polygon_bbox(poly))
    raw = load_neighborhood(cfg.key + "_oficial", bbox_usado)
    data = pg.clip_graph_to_polygon(raw, poly)
    return data, bbox_usado


def gateway_nodes(cfg, data: dict, bbox_usado: str, uset: set,
                  buffer_m: float = GATEWAY_BUFFER_M) -> set:
    """Portas de acesso: interseccoes do grafo recortado com pelo menos uma
    rua que sai dele. Busca-se a rede com uma margem extra (`buffer_m`) so'
    para que o no do outro lado da fronteira exista; uma porta e' um no do
    grafo recortado (dentro do poligono) ligado a um no fora dele.

    Restrito a `uset` (maior componente NAO-dirigida): uma saida so-entrada
    ou so-saida por mao unica ainda e' uma saida real.
    """
    data_buf = load_neighborhood(f"{cfg.key}_buffer{int(buffer_m)}",
                                 expand_bbox(bbox_usado, buffer_m))
    inside = set(data["graph"].nodes())
    gw = set()
    for e in data_buf["undirected_edges"]:
        u, v = e[0], e[1]
        u_in, v_in = u in inside, v in inside
        if u_in and not v_in:
            gw.add(u)
        elif v_in and not u_in:
            gw.add(v)
    return gw & uset
