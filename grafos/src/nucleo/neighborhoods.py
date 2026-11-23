"""
Configuracao por bairro para o pipeline multi-bairro.

Cada bairro declara:
  - key          : identificador curto (pasta de saida e nome do cache OSM).
  - display_name : nome curto para titulos de figura ("Urca").
  - bairro_full  : rotulo completo salvo em metrics["rede"]["bairro"].
  - bbox         : retangulo "S,W,N,E" usado so' como ENVELOPE de busca na
                   Overpass. O grafo analisado e' recortado pelo poligono
                   oficial do bairro (Data.Rio/IPP) nos nove bairros; ver
                   network.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NeighborhoodConfig:
    key: str
    display_name: str
    bairro_full: str
    bbox: str


# ---------------------------------------------------------------------------
# Bairros
# ---------------------------------------------------------------------------
NEIGHBORHOODS: "dict[str, NeighborhoodConfig]" = {
    "urca": NeighborhoodConfig(
        key="urca",
        display_name="Urca",
        bairro_full="Urca, Rio de Janeiro",
        bbox="-22.958,-43.171,-22.943,-43.155",
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
    ),
    # bbox = so' envelope de busca (o grafo e' recortado pelo poligono oficial,
    # que e' maior que este retangulo).
    "botafogo": NeighborhoodConfig(
        key="botafogo",
        display_name="Botafogo",
        bairro_full="Botafogo, Rio de Janeiro",
        bbox="-22.960,-43.195,-22.945,-43.170",
    ),
    # Bairros de encosta (casos adicionais).
    # bbox = envelope do poligono oficial (Data.Rio/IPP), com folga de ~0,001 grau.
    "alto_da_boa_vista": NeighborhoodConfig(
        key="alto_da_boa_vista",
        display_name="Alto da Boa Vista",
        bairro_full="Alto da Boa Vista, Rio de Janeiro",
        bbox="-22.989,-43.302,-22.930,-43.201",
    ),
    "cosme_velho": NeighborhoodConfig(
        key="cosme_velho",
        display_name="Cosme Velho",
        bairro_full="Cosme Velho, Rio de Janeiro",
        bbox="-22.947,-43.209,-22.934,-43.191",
    ),
    "leme": NeighborhoodConfig(
        key="leme",
        display_name="Leme",
        bairro_full="Leme, Rio de Janeiro",
        bbox="-22.968,-43.175,-22.956,-43.146",
    ),
    "joa": NeighborhoodConfig(
        key="joa",
        display_name="Joá",
        bairro_full="Joá, Rio de Janeiro",
        bbox="-23.018,-43.298,-23.000,-43.275",
    ),
    "sao_conrado": NeighborhoodConfig(
        key="sao_conrado",
        display_name="São Conrado",
        bairro_full="São Conrado, Rio de Janeiro",
        bbox="-23.032,-43.287,-22.978,-43.248",
    ),
    "praca_da_bandeira": NeighborhoodConfig(
        key="praca_da_bandeira",
        display_name="Praça da Bandeira",
        bairro_full="Praça da Bandeira, Rio de Janeiro",
        bbox="-22.917,-43.221,-22.906,-43.207",
    ),
}

# Ordem de apresentacao dos nove bairros: nas tabelas, nos mapas de redes e de
# corte (ORDEM_TABELAS) e nas figuras de resultados (ORDEM_FIGURAS).
ORDEM_TABELAS = [
    "urca",
    "leme",
    "joa",
    "alto_da_boa_vista",
    "praca_da_bandeira",
    "cosme_velho",
    "sao_conrado",
    "botafogo",
    "copacabana",
]
ORDEM_FIGURAS = [
    "urca",
    "leme",
    "alto_da_boa_vista",
    "cosme_velho",
    "joa",
    "sao_conrado",
    "copacabana",
    "botafogo",
    "praca_da_bandeira",
]
NOMES = {chave: cfg.display_name for chave, cfg in NEIGHBORHOODS.items()}
