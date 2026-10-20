"""
Poligono oficial de bairro (Data.Rio / Instituto Pereira Passos).

Usado, nos TRES bairros, para (i) recortar a rede baixada do OpenStreetMap
(`clip_graph_to_polygon`) e (ii) definir a fronteira contra a qual as portas
de acesso sao medidas (ver network.py). O retangulo manual de cada bairro
(neighborhoods.py) e' so' um envelope de busca.

Motivacao: um retangulo manual e' uma escolha de modelagem sem relacao com a
fronteira administrativa. Em Copacabana ele invadia o territorio de Botafogo
(158 de 496 interseccoes); em Urca e Botafogo, o poligono oficial e' maior que
o retangulo e este truncava a rede. Usar a mesma fronteira oficial nos tres
casos evita que o pre-processamento desigual explique diferencas entre eles.

Fonte: camada "Limite de Bairros" (Cartografia/Limites_administrativos,
layer 4) do ArcGIS REST do Data.Rio/IPP.
"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.parse

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

ARCGIS_QUERY_URL = (
    "https://pgeo3.rio.rj.gov.br/arcgis/rest/services/"
    "Cartografia/Limites_administrativos/MapServer/4/query"
)


def fetch_bairro_polygon(nome: str, use_cache: bool = True) -> dict:
    """Baixa (ou le do cache) o poligono oficial do bairro `nome`.

    Retorna um GeoJSON Feature unico, cacheado em
    data/poligono_<nome em minusculas>.json (mesmo espirito do cache do
    Overpass em osm_loader.py: reprodutivel offline apos o 1o download).
    """
    slug = nome.lower()
    cache = os.path.join(DATA_DIR, f"poligono_{slug}.json")
    if use_cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    params = {
        "where": f"UPPER(nome) LIKE '%{nome.upper()}%'",
        "outFields": "nome,codbairro",
        "f": "geojson",
        "outSR": "4326",
    }
    url = ARCGIS_QUERY_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": "grafos-academic/1.0 (trabalho academico)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    feats = data.get("features", [])
    if not feats:
        raise ValueError(f"bairro nao encontrado na camada oficial (Data.Rio/IPP): {nome}")
    feat = feats[0]
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(feat, f, ensure_ascii=False)
    return feat


def _rings(feature: dict) -> list:
    """Extrai os aneis EXTERNOS (lista de (lon, lat)); ignora buracos, que
    nao existem nos poligonos de bairro do Rio."""
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        raise ValueError(f"tipo de geometria inesperado: {geom['type']}")
    return [poly[0] for poly in polys]  # anel 0 = externo


def _point_in_ring(lon: float, lat: float, ring) -> bool:
    """Ray casting par-impar padrao para um unico anel poligonal."""
    inside = False
    n = len(ring)
    x1, y1 = ring[0]
    for i in range(1, n + 1):
        x2, y2 = ring[i % n]
        if (y1 > lat) != (y2 > lat):
            x_int = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < x_int:
                inside = not inside
        x1, y1 = x2, y2
    return inside


def point_in_bairro(lon: float, lat: float, feature: dict) -> bool:
    """True se (lon, lat) esta dentro do poligono oficial do bairro."""
    return any(_point_in_ring(lon, lat, ring) for ring in _rings(feature))


def distancias_ao_poligono_m(pontos: dict, feature: dict, teto_m: float = float("inf")) -> dict:
    """Distancia (m) de cada ponto ao poligono oficial; 0 dentro dele.

    `pontos`: id -> (lat, lon). Projecao equirretangular local (a mesma ideia
    de osm_loader.load_neighborhood), suficiente para distancias de ate' alguns
    km. Pontos a mais de `teto_m` do poligono recebem `inf` sem calculo
    exato (basta um teste com o retangulo do poligono).
    """
    import math
    aneis = _rings(feature)
    lat0 = sum(la for r in aneis for _, la in r) / sum(len(r) for r in aneis)
    kx = math.cos(math.radians(lat0)) * 111320.0
    ky = 110540.0
    segs = []
    xs, ys = [], []
    for r in aneis:
        pts = [(lo * kx, la * ky) for lo, la in r]
        xs += [p[0] for p in pts]; ys += [p[1] for p in pts]
        for i in range(len(pts)):
            segs.append((pts[i], pts[(i + 1) % len(pts)]))
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    out = {}
    for nid, (la, lo) in pontos.items():
        if point_in_bairro(lo, la, feature):
            out[nid] = 0.0
            continue
        px, py = lo * kx, la * ky
        dbx = max(x0 - px, 0.0, px - x1); dby = max(y0 - py, 0.0, py - y1)
        if math.hypot(dbx, dby) > teto_m:
            out[nid] = float("inf")
            continue
        best = float("inf")
        for (ax, ay), (bx, by) in segs:
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d < best:
                best = d
        out[nid] = best
    return out


def polygon_bbox(feature: dict) -> str:
    """Bbox 'S,W,N,E' que envolve o poligono oficial do bairro."""
    lons, lats = [], []
    for ring in _rings(feature):
        for lon, lat in ring:
            lons.append(lon); lats.append(lat)
    return f"{min(lats)},{min(lons)},{max(lats)},{max(lons)}"


def clip_graph_to_polygon(data: dict, feature: dict) -> dict:
    """Recorta o resultado de load_neighborhood() para so os nos DENTRO do
    poligono oficial do bairro (e as arestas com os dois extremos dentro).

    Aplicado aos tres bairros. Nao contrai nada -- so remove nos e arestas
    fora do bairro (o envelope de busca e' maior que o poligono).
    """
    from graph import Graph  # import local: evita ciclo de import com main

    latlon = data["latlon"]
    keep = {nid for nid, (lat, lon) in latlon.items()
            if point_in_bairro(lon, lat, feature)}

    G_old = data["graph"]
    G_new = Graph()
    for nid in keep:
        x, y = G_old.coords[nid]
        G_new.add_node(nid, x, y)
    for e in G_old.edges:
        if e.u in keep and e.v in keep:
            G_new._add_directed(e.u, e.v, e.length, e.travel_time, e.oneway)

    new_undirected = [seg for seg in data["undirected_edges"]
                       if seg[0] in keep and seg[1] in keep]

    out = dict(data)
    out["graph"] = G_new
    out["undirected_edges"] = new_undirected
    out["latlon"] = {nid: latlon[nid] for nid in keep}
    out["n_removidos_fora_do_poligono"] = len(data["latlon"]) - len(keep)
    return out
