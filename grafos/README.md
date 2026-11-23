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
  23/09/2026; extratos ampliados (conectividade externa) em 11/10/2026. Polígonos: camada "Limite de Bairros" do Data.Rio (IPP), acessada em
  setembro de 2026. Dados do mapa © colaboradores do OpenStreetMap (ODbL).

## Como reproduzir (a partir de `grafos/src`)

| Comando | O que gera | Seção do artigo |
|---|---|---|
| `py main.py all` | `output/<bairro>/metrics.json` (indicadores, fluxo de acesso; a resiliência exaustiva também é calculada, mas não entra no artigo) | 3, 4.1, 4.2 |
| `py compare.py` | `output/comparativo/` | 4.1 |
| `py estatisticas_dados.py` | `output/estatisticas_dados.json` (datas, `maxspeed`, cadeias descartadas) | 3.1 |
| `py corte_no_a_no.py` | `output/corte_no_a_no.json` (todos os pares de cada bairro, sem sorteio, sem o sentido das vias e com ele; `--verifica` confere uma amostra com o `networkx`) | 4.1 |
| `py sensitivity.py` | `output/sensibilidade_acesso.json` (margem x f) e `output/sensibilidade_fracao.json` (f de 0,05 a 0,50); `--fracao` roda só a segunda | 3.4, 4.2 |
| `py robustez_recorte.py` | `output/robustez_recorte.json` (retângulo x polígono) | fora do artigo (o retângulo manual saiu) |
| `py localiza_corte.py` | `output/localizacao_corte.json`, `fig_cut.png` | 4.3 |
| `py nulo_fluxo.py` | `output/nulo_fluxo.json` (controle de tamanho do fluxo; a busca adversária parte dos 25 pedaços de menor fluxo) | 3.4, 4.4 |
| `py nulo_intermediacao.py` | `output/nulo_intermediacao.json` | fora do artigo (versão anterior do controle de tamanho da intermediação; ver `controle_tamanho_intermediacao.py`) |
| `py ruas_vs_intersecoes.py --verifica` | `output/ruas_vs_intersecoes.json` (fluxo de acesso por ruas e por interseções, com e sem o sentido das vias; confere com o `networkx`) | 4.2 |
| `py acesso_tuneis.py` | `output/acesso_tuneis.json` | fora do artigo (fluxo sem as saídas de túnel) |
| `py controle_tamanho_intermediacao.py` | `output/controle_tamanho_intermediacao.json` (intermediação máxima de pedaços das malhas abertas pareados pelo núcleo forte de 65 ± 5 nós; mede também os pedaços de 70 interseções do controle do fluxo, que não entram no artigo) | 3.4, 4.4 |
| `py valores_pareados.py` | acrescenta `valores_pct` (intermediação máxima de cada pedaço pareado) a `output/controle_tamanho_intermediacao.json`, conferindo mediana e tentativas | 4.4 |
| `py fig_controles.py` | `output/fig_controles.png` (painel a: fluxo dos pedaços de 70 interseções; painel b: intermediação máxima dos pedaços pareados) | 4.4 |
| `py robustez_desempate.py [N]` | `output/robustez_desempate.json` (200 sorteios da ordem dos empates na escolha do núcleo; as quatro contagens) | 3.4, 4.2 |
| `py conectividade_externa.py --verifica` | `output/conectividade_externa.{json,csv}` (fluxo ate a borda externa da rede ampliada em 500 m, 1 km e 2 km; cortes; ruas externas criticas; regressao com a Tabela 4) | 4.5 |
| `py analisa_portas_sem_continuacao.py` | `output/portas_sem_continuacao.json` (criterio de continuacao das portas e fluxo ate as que continuam) | 4.5 |
| `py fig_conectividade_externa.py` | `output/fig_externa.png` | 4.5 |
| `py velocidade_ctb.py` | `output/velocidade_ctb.json` (intermediação com a tabela do CTB, a anterior e `secondary` = 40 km/h) | 4.1, Discussão |
| `py simulacao_interrupcoes.py --verifica` | `output/simulacao_interrupcoes.{json,csv}`, `output/fig_simulacao.png` (perda de alcancabilidade do nucleo ao fechar k ruas; dano de cada rua; 7 estrategias) | 4.6 |
| `py make_en_figures.py` | figuras em `output/` | 3, 4 |
| `py test_vs_networkx.py`, `py test_betweenness.py` | verificação contra o `networkx` | 3.2 |

## Sementes

`nulo_intermediacao.py` e `nulo_fluxo.py`: 7. `simulacao_interrupcoes.py`: 13. `test_vs_networkx.py`: 11. `corte_no_a_no.py` não sorteia (usa todos os pares).

## Classes de via e velocidades padrão

Vias aceitas (`highway`): motorway, trunk, primary, secondary, tertiary, unclassified,
residential, living_street, road e as variantes `*_link`. Ficam de fora `service`, `track` e
vias de pedestre. Quando a via não tem `maxspeed`, o tempo de percurso usa a velocidade
padrão da classe (km/h). Os valores seguem o art. 61, § 1º, I, do Código de Trânsito
Brasileiro (vias urbanas sem sinalização regulamentadora: trânsito rápido 80, arteriais 60,
coletoras 40, locais 30), com o mapeamento de classes do OSM Wiki ("Default speed limits",
Brasil). `motorway` = trânsito rápido; `trunk`, `primary` e `secondary` = arterial; `tertiary` = coletora; `unclassified`, `residential` e `road` = local;
as variantes `*_link` seguem a classe-mãe. `living_street` (valor típico dos limites implícitos
em outros países) e `service`, sem equivalente no CTB, ficam em 20.

| Classe | km/h | Classe | km/h |
|---|---|---|---|
| motorway | 80 | motorway_link | 80 |
| trunk | 60 | trunk_link | 60 |
| primary | 60 | primary_link | 60 |
| secondary | 60 | secondary_link | 60 |
| tertiary | 40 | tertiary_link | 40 |
| unclassified | 30 | living_street | 20 |
| residential | 30 | road | 30 |

`velocidade_ctb.py` compara essa tabela com a usada antes (motorway 90, secondary 50,
unclassified 40, links mais lentos) e com as variantes `trunk` a 80 e `secondary` a 40 km/h,
na intermediação máxima e na intermediação de aresta (Spearman e 10 maiores).
O fluxo de acesso não usa o peso e não muda.

## Regras de sentido

`oneway=yes`, `true` ou `1` gera um arco no sentido dos nós; `-1` ou `reverse`, no sentido
contrário. Rotatórias (`junction=roundabout`) e vias `motorway`, `motorway_link` e
`trunk_link` são de mão única por convenção do OSM. As demais são de mão dupla.
