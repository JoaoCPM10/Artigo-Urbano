"""
Configuracao por bairro para o pipeline multi-bairro.

Cada bairro declara:
  - key          : identificador curto (pasta de saida e nome do cache OSM).
  - display_name : nome curto para titulos de figura ("Urca").
  - bairro_full  : rotulo completo salvo em metrics["rede"]["bairro"].
  - bbox         : retangulo "S,W,N,E" usado so' como ENVELOPE de busca na
                   Overpass. O grafo analisado e' recortado pelo poligono
                   oficial do bairro (Data.Rio/IPP) nos TRES bairros; ver
                   network.py.
  - mincut_od    : criterio de escolha de origem/destino para o corte minimo.
  - altroute_od  : criterio de origem/destino para a demonstracao de rota
                   alternativa.
  - rationale    : justificativa textual dos criterios acima (documentada no
                   artigo, Secao de metodologia).

mincut_od e altroute_od aceitam DUAS formas:
  1. uma funcao selector(G, ctx) -> (O, D), onde ctx = {"gset","deg","giant",
     "gl"} traz o nucleo fortemente conexo e os graus ja calculados; ou
  2. uma tupla literal (id_O, id_D) de node-ids OSM escolhidos manualmente
     inspecionando o mapa (recomendado para pontos geograficos especificos,
     como as bocas dos tuneis de Copacabana).

A heuristica geometrica da Urca fica CONGELADA nas funcoes urca_* abaixo, para
que os numeros ja citados no artigo nao mudem. Bairros sem um eixo geografico
privilegiado (ex.: Botafogo, o controle "sem gargalo") usam o fallback
generico double_sweep, que nao impoe nenhuma direcao especial.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Union

import shortest_paths as sp

# selector: funcao (G, ctx) -> (O, D)  OU  tupla literal (id_O, id_D)
ODSelector = Union[Callable[[object, dict], "tuple[int, int]"], "tuple[int, int]"]


@dataclass
class NeighborhoodConfig:
    key: str
    display_name: str
    bairro_full: str
    bbox: str
    mincut_od: ODSelector
    altroute_od: ODSelector
    rationale: str = ""


def resolve_od(selector: ODSelector, G, ctx: dict) -> "tuple[int, int]":
    """Resolve o par (O, D) a partir de um selector (funcao ou tupla literal)."""
    if callable(selector):
        return selector(G, ctx)
    O, D = selector
    if O not in G.coords or D not in G.coords:
        raise ValueError(
            f"node-ids de O/D fora do grafo apos simplificacao: O={O}, D={D}. "
            "Escolha interseccoes que sobrevivam a contracao de grau 2.")
    return O, D


# ---------------------------------------------------------------------------
# Criterios de O/D
# ---------------------------------------------------------------------------
def urca_mincut(G, ctx) -> "tuple[int, int]":
    """Corte minimo da Urca (CONGELADO): interseccoes bem conectadas (grau>=3)
    da CFC gigante nos extremos opostos da peninsula, para que o corte reflita
    o 'pescoco' geografico do bairro e nao um cul-de-sac local."""
    gset, deg = ctx["gset"], ctx["deg"]
    inner = [u for u in gset if deg[u] >= 3] or list(gset)
    O = max(inner, key=lambda u: G.coords[u][0] + G.coords[u][1])
    D = min(inner, key=lambda u: G.coords[u][0] + G.coords[u][1])
    return O, D


def urca_altroute(G, ctx) -> "tuple[int, int]":
    """Rota alternativa da Urca (CONGELADO): par O-D dentro da grade
    residencial (y>150 na projecao local), onde a malha oferece redundancia,
    para de fato demonstrar uma rota alternativa."""
    giant = ctx["giant"]
    grid = [u for u in giant if G.coords[u][1] > 150] or list(giant)
    Or = max(grid, key=lambda u: G.coords[u][0])
    Dr = min(grid, key=lambda u: G.coords[u][0])
    return Or, Dr


def double_sweep(G, ctx) -> "tuple[int, int]":
    """Fallback generico, sem eixo geografico privilegiado (duas varreduras de
    Dijkstra): a partir de um no do nucleo, acha o mais distante em tempo (b);
    a partir de b, o mais distante dele (c). Devolve (b, c). Serve para
    qualquer topologia, inclusive o controle 'sem gargalo' (Botafogo), onde
    impor uma direcao seria artificial."""
    gl = ctx["gl"]
    seed = gl[0]
    d1, _ = sp.dijkstra(G, seed)
    b = max(gl, key=lambda u: d1.get(u, -1.0))
    d2, _ = sp.dijkstra(G, b)
    c = max(gl, key=lambda u: d2.get(u, -1.0))
    return b, c


# ---------------------------------------------------------------------------
# Bairros
# ---------------------------------------------------------------------------
NEIGHBORHOODS: "dict[str, NeighborhoodConfig]" = {
    "urca": NeighborhoodConfig(
        key="urca",
        display_name="Urca",
        bairro_full="Urca, Rio de Janeiro",
        bbox="-22.958,-43.171,-22.943,-43.155",
        mincut_od=urca_mincut,
        altroute_od=urca_altroute,
        rationale=(
            "Peninsula com corredor unico de acesso a cidade (gargalo "
            "geografico pequeno). O/D do corte minimo nos extremos opostos da "
            "grade; O/D da rota alternativa dentro da grade residencial."),
    ),
    # bbox = so' envelope de busca (o grafo e' recortado pelo poligono oficial).
    # Ao norte contem as bocas dos tuneis Velho e Novo; ao sul/oeste, o
    # encontro da malha com Ipanema. Um bbox manual invadia o territorio de
    # Botafogo (158 de 496 interseccoes), motivo do recorte por poligono.
    "copacabana": NeighborhoodConfig(
        key="copacabana",
        display_name="Copacabana",
        bairro_full="Copacabana, Rio de Janeiro",
        bbox="-22.988,-43.196,-22.955,-43.176",
        # PROVISORIO: double_sweep ate escolher manualmente os node-ids das
        # bocas dos tuneis (gargalo grande). Substituir por uma tupla literal
        # (id_tunel, id_interior) apos inspecionar 01_copacabana.png.
        mincut_od=double_sweep,
        altroute_od=double_sweep,
        rationale=(
            "Bairro denso com acesso a cidade estrangulado por poucos tuneis "
            "(gargalo geografico grande). O/D do corte minimo deve ligar a "
            "boca de um tunel a uma interseccao interior; pendente de escolha "
            "manual de node-ids."),
    ),
    # bbox = so' envelope de busca (o grafo e' recortado pelo poligono oficial,
    # que e' maior que este retangulo).
    "botafogo": NeighborhoodConfig(
        key="botafogo",
        display_name="Botafogo",
        bairro_full="Botafogo, Rio de Janeiro",
        bbox="-22.960,-43.195,-22.945,-43.170",
        # Controle 'sem gargalo': varias vias de saida em direcoes diferentes;
        # nao impor eixo -> double_sweep e o criterio correto.
        mincut_od=double_sweep,
        altroute_od=double_sweep,
        rationale=(
            "Multiplas vias de saida em direcoes diferentes, sem ponto unico "
            "de estrangulamento (controle 'sem gargalo'). Nenhum eixo "
            "geografico privilegiado: O/D por double_sweep."),
    ),
}
