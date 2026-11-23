"""
Camada de contexto geografico para os mapas: agua, encosta e
escala. Para um bairro, ajusta a projecao local da rede (x, y em metros), busca a
altimetria SRTM de 30 m em uma grade sobre o poligono oficial (OpenTopoData, com
cache em data/elevacao_grade_<chave>.json) e desenha, sob a rede:

  - relevo sombreado (cinza);
  - encosta: declividade >= 30% (marrom translucido);
  - agua: celulas com altitude <= 0,5 m (azul claro) e as linhas de costa e de
    corpos d'agua do OSM (azul);
  - fronteira oficial tracejada, barra de escala e seta do norte.

Limitacoes: a SRTM e' modelo de superficie com 30 m de resolucao (a grade de
alguns bairros e' mais grossa, ver `passo_m`); canais e rios estreitos aparecem
so' pelas linhas do OSM.
"""

from __future__ import annotations

import json
import os

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import shape

from analises import variavel_geografica as vg
from figuras.rotulos import t as _t
from nucleo import polygons as pg
from nucleo.neighborhoods import NEIGHBORHOODS

LIMIAR_DECL = 0.30
MAX_PONTOS_LADO = 70
MARGEM_M = 300.0


def ajuste_xy(data):
    """Transformacao (lon, lat) -> (x, y) da rede, por minimos quadrados."""
    ll, co = data["latlon"], data["graph"].coords
    ids = [n for n in ll if n in co]
    lon = np.array([ll[n][1] for n in ids])
    lat = np.array([ll[n][0] for n in ids])
    x = np.array([co[n][0] for n in ids])
    y = np.array([co[n][1] for n in ids])
    a, b = np.polyfit(lon, x, 1)
    c, d = np.polyfit(lat, y, 1)
    return (a, b, c, d)


def para_xy(T, lon, lat):
    a, b, c, d = T
    return a * np.asarray(lon) + b, c * np.asarray(lat) + d


def para_ll(T, x, y):
    a, b, c, d = T
    return (np.asarray(x) - b) / a, (np.asarray(y) - d) / c


def grade_elevacao(key, T, ext_xy):
    """(X, Y, Z, passo) em metros locais; Z em metros (SRTM). `ext_xy` = (minx, miny, maxx, maxy)."""
    cache_path = os.path.join(vg.DATA, f"elevacao_grade_{key}.json")
    minx, miny, maxx, maxy = ext_xy
    minx -= MARGEM_M
    miny -= MARGEM_M
    maxx += MARGEM_M
    maxy += MARGEM_M
    passo = max(25.0, max(maxx - minx, maxy - miny) / MAX_PONTOS_LADO)
    xs = np.arange(minx, maxx + passo, passo)
    ys = np.arange(miny, maxy + passo, passo)
    X, Y = np.meshgrid(xs, ys)
    lon, lat = para_ll(T, X.ravel(), Y.ravel())
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    antigo = vg.CACHE_ELEV
    vg.CACHE_ELEV = cache_path
    try:
        z = vg.elevacoes(list(zip(lat, lon)), cache)
    finally:
        vg.CACHE_ELEV = antigo
    Z = np.array(z, dtype=float).reshape(X.shape)
    return X, Y, Z, passo


_AGUA = None


def linhas_agua_xy(T):
    global _AGUA
    if _AGUA is None:
        raw = vg.agua_osm()
        linhas = []
        for el in raw["elements"]:
            geoms = []
            if el["type"] == "way" and "geometry" in el:
                geoms.append(el["geometry"])
            elif el["type"] == "relation":
                geoms += [m["geometry"] for m in el.get("members", []) if m.get("geometry")]
            for g in geoms:
                if len(g) >= 2:
                    linhas.append(np.array([(p["lon"], p["lat"]) for p in g]))
        _AGUA = linhas
    segs = []
    for ln in _AGUA:
        x, y = para_xy(T, ln[:, 0], ln[:, 1])
        segs.append(np.column_stack([x, y]))
    return segs


def barra_escala(ax, comprimento_m=None):
    x0, x1 = ax.get_xlim()
    larg = x1 - x0
    if comprimento_m is None:
        alvo = larg * 0.22
        comprimento_m = min([200, 500, 1000, 2000, 5000], key=lambda v: abs(v - alvo))
    xa = x0 + 0.05 * larg
    ya = ax.get_ylim()[0] + 0.045 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    ax.plot(
        [xa, xa + comprimento_m], [ya, ya], color="black", lw=3, solid_capstyle="butt", zorder=20
    )
    rot = f"{comprimento_m / 1000:g} km" if comprimento_m >= 1000 else f"{comprimento_m} m"
    ax.text(
        xa + comprimento_m / 2,
        ya + 0.012 * (ax.get_ylim()[1] - ax.get_ylim()[0]),
        rot,
        ha="center",
        va="bottom",
        fontsize=9,
        zorder=20,
        bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=1),
    )


def seta_norte(ax):
    ax.annotate(
        "N",
        xy=(0.93, 0.93),
        xytext=(0.93, 0.80),
        xycoords="axes fraction",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        zorder=20,
        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5),
    )


def desenha_contexto(ax, key, data, nos=None):
    """Desenha agua, encosta, fronteira, escala e norte sob a rede. Retorna dados uteis."""
    cfg = NEIGHBORHOODS[key]
    T = ajuste_xy(data)
    f = pg.fetch_bairro_polygon(cfg.display_name)
    geom = shape(f["geometry"])
    # poligono em x, y
    from shapely.ops import transform as sh_transform

    poly_xy = sh_transform(lambda lon, lat, z=None: tuple(para_xy(T, lon, lat)), geom)
    coords = data["graph"].coords
    co = np.array([coords[n] for n in (nos if nos is not None else coords)])
    ext_xy = (co[:, 0].min(), co[:, 1].min(), co[:, 0].max(), co[:, 1].max())
    X, Y, Z, passo = grade_elevacao(key, T, ext_xy)
    ls = LightSource(azdeg=315, altdeg=40)
    sombra = ls.hillshade(Z, vert_exag=2.0, dx=passo, dy=passo)
    ext = (X.min() - passo / 2, X.max() + passo / 2, Y.min() - passo / 2, Y.max() + passo / 2)
    ax.imshow(
        sombra, cmap="Greys_r", extent=ext, origin="lower", vmin=0.2, vmax=1.0, alpha=0.55, zorder=0
    )
    gy, gx = np.gradient(Z, passo)
    decl = np.hypot(gx, gy)
    agua = Z <= 0.5
    enc = (decl >= LIMIAR_DECL) & ~agua
    rgba = np.zeros(Z.shape + (4,))
    rgba[enc] = (0.65, 0.40, 0.10, 0.35)
    rgba[agua] = (0.55, 0.78, 0.95, 0.85)
    ax.imshow(rgba, extent=ext, origin="lower", zorder=0.5)
    ax.add_collection(
        LineCollection(linhas_agua_xy(T), colors="#2a7fba", linewidths=0.9, zorder=0.8)
    )
    partes = list(poly_xy.geoms) if hasattr(poly_xy, "geoms") else [poly_xy]
    for p in partes:
        x, y = p.exterior.xy
        ax.plot(x, y, color="#2d3748", lw=1.2, ls="--", zorder=1.5)
    ax.set_xlim(ext[0] + passo * 0.5, ext[1] - passo * 0.5)
    ax.set_ylim(ext[2] + passo * 0.5, ext[3] - passo * 0.5)
    ax.set_aspect("equal")
    return {
        "T": T,
        "passo": passo,
        "frac_agua_celulas": float(agua.mean()),
        "frac_encosta_celulas": float(enc.mean()),
    }


def handles_contexto():
    return [
        Patch(
            facecolor=(0.55, 0.78, 0.95),
            label=_t("water (elevation <= 0.5 m)", "água (altitude ≤ 0,5 m)"),
        ),
        Patch(
            facecolor=(0.65, 0.40, 0.10, 0.45),
            label=_t("slope >= 30% (SRTM 30 m)", "encosta (declividade ≥ 30%, SRTM de 30 m)"),
        ),
        Line2D(
            [],
            [],
            color="#2a7fba",
            lw=1.2,
            label=_t("OSM coastline and water", "costa e água do OSM"),
        ),
        Line2D(
            [],
            [],
            color="#2d3748",
            lw=1.2,
            ls="--",
            label=_t("official boundary", "fronteira oficial"),
        ),
    ]
