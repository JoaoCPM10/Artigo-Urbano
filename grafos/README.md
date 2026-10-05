# Código e dados do estudo

Análise de acesso das redes viárias de Urca, Copacabana e Botafogo (Rio de Janeiro).
Os algoritmos (componentes, pontes e articulações, Dijkstra, Edmonds-Karp, Brandes) são
implementados sem bibliotecas de grafos. O `networkx` é usado apenas nos testes de
verificação; o `matplotlib`, apenas nas figuras.

## Ambiente

- Python 3.13.7 (testado); `matplotlib` 3.10.8 e `networkx` 3.6.1.
- Os dados brutos do OpenStreetMap e os polígonos oficiais ficam em `data/`, já baixados.
  Com eles, tudo roda offline. O nome de cada cache inclui um hash do retângulo consultado.
- Extratos do OSM (base da Overpass 0.7.62): Copacabana em 21/09/2026; Urca e Botafogo em
  23/09/2026. Polígonos: camada "Limite de Bairros" do Data.Rio (IPP), acessada em
  setembro de 2026. Dados do mapa © colaboradores do OpenStreetMap (ODbL).

## Como reproduzir (a partir de `grafos/src`)

| Comando | O que gera | Seção do artigo |
|---|---|---|
| `py main.py all` | `output/<bairro>/metrics.json` (indicadores, fluxo de acesso; a resiliência exaustiva também é calculada, mas não entra no artigo) | 3, 4.1, 4.3 |
| `py compare.py` | `output/comparativo/` | 4 |
| `py estatisticas_dados.py` | `output/estatisticas_dados.json` (datas, `maxspeed`, cadeias descartadas) | 3.1 |
| `py corte_no_a_no.py` | `output/corte_no_a_no.json` (300 pares por bairro) | 4.2 |
| `py sensitivity.py` | `output/sensibilidade_acesso.json` (margem x f) | 3.4, 4.3 |
| `py robustez_recorte.py` | `output/robustez_recorte.json` (retângulo x polígono) | 4.6 |
| `py localiza_corte.py` | `output/localizacao_corte.json`, `fig_cut.png` | 4.4 |
| `py nulo_fluxo.py` | `output/nulo_fluxo.json` | 4.4 |
| `py nulo_intermediacao.py` | `output/nulo_intermediacao.json` | 4.5 |
| `py acesso_tuneis.py` | `output/acesso_tuneis.json` | 4.3 |
| `py make_en_figures.py` | figuras em `output/` | 3, 4 |
| `py test_vs_networkx.py`, `py test_betweenness.py` | verificação contra o `networkx` | 3.2 |

## Sementes

`nulo_intermediacao.py` e `nulo_fluxo.py`: 7. `corte_no_a_no.py`: 5. `test_vs_networkx.py`: 11.

## Classes de via e velocidades padrão

Vias aceitas (`highway`): motorway, trunk, primary, secondary, tertiary, unclassified,
residential, living_street, road e as variantes `*_link`. Ficam de fora `service`, `track` e
vias de pedestre. Quando a via não tem `maxspeed`, o tempo de percurso usa a velocidade
padrão da classe (km/h):

| Classe | km/h | Classe | km/h |
|---|---|---|---|
| motorway | 90 | motorway_link | 60 |
| trunk | 80 | trunk_link | 50 |
| primary | 60 | primary_link | 40 |
| secondary | 50 | secondary_link | 40 |
| tertiary | 40 | tertiary_link | 30 |
| unclassified | 40 | living_street | 20 |
| residential | 30 | road | 30 |

## Regras de sentido

`oneway=yes`, `true` ou `1` gera um arco no sentido dos nós; `-1` ou `reverse`, no sentido
contrário. Rotatórias (`junction=roundabout`) e vias `motorway`, `motorway_link` e
`trunk_link` são de mão única por convenção do OSM. As demais são de mão dupla.
