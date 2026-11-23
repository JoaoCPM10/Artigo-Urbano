# Código e dados do estudo

Redundância do acesso viário em escala de bairro: fluxo máximo em nove bairros do Rio de
Janeiro (Urca, Leme, Alto da Boa Vista, Cosme Velho, Joá, São Conrado, Copacabana, Botafogo e
Praça da Bandeira). Este diretório reproduz as tabelas e as figuras do artigo a partir dos dados
do OpenStreetMap.

Os algoritmos (componentes, pontes e articulações, Dijkstra, Edmonds-Karp, Brandes) são
implementados sem bibliotecas de grafos. O `networkx` só entra nas verificações, o `matplotlib`
nas figuras e o `geopandas` nos mapas, na geografia e na população.

## 1. Instalação

Requer Python 3.13 (versão testada: 3.13.7). A partir de `grafos/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

No Linux ou no macOS, ative com `source .venv/bin/activate`. No Windows, defina também
`$env:PYTHONIOENCODING = "utf-8"` para os acentos dos relatórios impressos.

Todos os comandos abaixo rodam **a partir de `grafos/src`**, com `python -m pacote.script`.

## 2. Dados

| O quê | Onde | Como obter |
|---|---|---|
| Extratos do OpenStreetMap (Overpass) e polígonos oficiais dos bairros | `data/` | Já estão no repositório. Com eles, a maior parte do pipeline roda sem internet. O nome de cada cache inclui um hash do retângulo consultado, e as datas dos extratos ficam em `output/estatisticas_dados.json`. |
| Água (OSM) e altimetria SRTM de 30 m | `data/agua_osm_*.json`, `data/elevacao_*.json` | Não estão no repositório. `variavel_geografica.py` e os mapas os baixam na primeira execução (Overpass e OpenTopoData), por isso precisam de internet. |
| Malha de setores censitários do Censo 2022 (RJ) | `data/ibge_censo2022_rj/RJ_setores_CD2022.gpkg` | Não está no repositório (cerca de 75 MB). Baixe o GeoPackage do estado do Rio de Janeiro em <https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/malha_com_atributos/setores/gpkg/UF/RJ/> e, se vier compactado, descompacte na pasta. Só `populacao_atras_do_corte.py` o usa. |

Se um cache do OSM faltar, o carregador baixa o extrato de novo e o guarda em `data/`, mas a
Overpass muda com o tempo e os números podem diferir levemente dos do artigo. Dados do mapa ©
colaboradores do OpenStreetMap (ODbL); polígonos da camada "Limite de Bairros" do Data.Rio
(IPP).

## 3. Teste rápido

Confere as implementações contra o `networkx` e roda os indicadores de um bairro (alguns
minutos):

```powershell
cd src
python -m testes.test_betweenness
python -m analises.indicadores urca
```

O segundo comando escreve `output/urca/metrics.json`. O teste completo contra o `networkx`
(`python -m testes.test_vs_networkx`) leva mais tempo.

## 4. Pipeline completo

A forma mais simples é o executor, que roda as etapas abaixo na ordem certa e guarda o log de
cada uma em `output/logs/` (pasta fora do git):

```powershell
python executar_pipeline.py --listar            # mostra as etapas
python executar_pipeline.py --pular-lentas      # tudo, menos as etapas lentas (as de 2 min ou mais)
python executar_pipeline.py --etapas indicadores,tabelas
python executar_pipeline.py                     # o pipeline completo (cerca de 25 min)
```

A última etapa, `copiar_figuras`, copia as sete figuras do artigo de `output/` para `Figures/`.
As etapas dependem umas das outras: `tabelas` lê as saídas de `indicadores`, `vias_de_servico` e
`corte_dois_nos`, e `controles_de_tamanho` termina na Figura 5. Para rodar uma etapa isolada, rode
antes as que ela lê (coluna "Lê" abaixo).

| Etapa | Comandos | Escreve (em `output/`) | Lê | Tempo |
|---|---|---|---|---|
| `indicadores` | `python -m analises.indicadores all` | `<bairro>/metrics.json` | | 15 s |
| `vias_de_servico` | `python -m analises.service_um_modo` (três vezes: sem variável, `GRAFOS_SERVICE=todas` e `GRAFOS_SERVICE=publicas`) | `service_artigo.json`, `service_todas.json`, `service_publicas.json` | | 40 s |
| `estatisticas` | `python -m analises.estatisticas_dados` | `estatisticas_dados.json` | | 2 s |
| `corte_dois_nos` | `python -m analises.corte_no_a_no --verifica` | `corte_no_a_no.json` | | 9 min |
| `tabelas` | `python -m analises.tabelas_nove_bairros` | `tabelas_nove_bairros.json` | `metrics.json`, `corte_no_a_no.json`, `service_artigo.json` | 1 s |
| `fluxo_de_acesso` | `ruas_vs_intersecoes --verifica`, `casos_adicionais <seis bairros novos>`, `robustez_desempate`, `localiza_corte` | `ruas_vs_intersecoes.json`, `casos_adicionais.json`, `robustez_desempate.json`, `localizacao_corte.json` | | 25 s |
| `sensibilidade` | `python -m analises.sensitivity`; `python -m figuras.fig_fluxo_f` | `sensibilidade_acesso.*`, `sensibilidade_fracao.*`, `fig_fluxo_f.png` | | 6 s |
| `controles_de_tamanho` | `nulo_fluxo_referencia` (Urca e Leme, com `--fontes`), `pedacos_fluxo1 leme`, `controle_forma` (Urca e Leme, 1000 posições), `controle_tamanho_intermediacao`, `intermediacao_pareada_fontes` (Urca e Leme), `figuras.fig_controles` | `nulo_fluxo_*_fontes.json`, `pedacos_fluxo1_leme_fontes.json`, `controle_forma_*_fontes.json`, `controle_tamanho_intermediacao.json`, `fig_controles.png` | | 7 min |
| `conectividade_externa` | `conectividade_externa --verifica --bairros <nove>`, `analisa_portas_sem_continuacao <nove>`, `figuras.fig_externa_geo` | `conectividade_externa.*`, `portas_sem_continuacao.json`, `fig_externa.png` | | 3 min |
| `simulacao` | `simulacao_interrupcoes --verifica --bairros <nove>`, `velocidade_ctb` | `simulacao_interrupcoes.*`, `fig_simulacao.png`, `velocidade_ctb.json` | | 2 min |
| `geografia_e_populacao` | `variavel_geografica`, `variavel_geografica_sens`, `populacao_atras_do_corte` | `variavel_geografica*.json`, `populacao_corte.json` | dados do IBGE | 15 s |
| `figuras` | `figuras.fig_construcao`, `figuras.fig_mapas_geograficos todas` | `fig_construction.png`, `fig_networks.png`, `fig_cut.png` | | 10 s |
| `testes` | `testes.test_vs_networkx`, `testes.test_betweenness` | (só imprime) | | 35 s |

`<nove>` é a lista dos nove bairros separados por vírgula (`urca,leme,...`). Os bairros que servem
de origem dos pedaços sorteados nos controles de tamanho e de forma são, para a Urca, Copacabana,
Botafogo, Alto da Boa Vista, São Conrado e Praça da Bandeira, e, para o Leme, esses cinco mais o
Cosme Velho (os que têm interseções suficientes para o pedaço). A lista exata está em
`executar_pipeline.py`.

## 5. Onde sai cada tabela e cada figura do artigo

| Artigo | Script | Arquivo em `output/` |
|---|---|---|
| Tabela 1 (tags do OSM) | escrita à mão, a partir do OSM Wiki | |
| Tabela 2 (redes) e Tabela 5 (indicadores estruturais) | `tabelas_nove_bairros` | `tabelas_nove_bairros.json` |
| Tabela 3 (estratégias da simulação) | escrita à mão (descreve `simulacao_interrupcoes`) | |
| Tabela 4 (fluxo de acesso por portas) | `service_um_modo` (modo `artigo`), `ruas_vs_intersecoes`, `casos_adicionais` | `service_artigo.json` |
| Tabela 6 (corte mínimo entre dois nós) | `corte_no_a_no` | `corte_no_a_no.json` |
| Tabela 7 (população atrás do corte) | `populacao_atras_do_corte` | `populacao_corte.json` |
| Tabelas 8 e 9 (conectividade externa e portas) | `conectividade_externa`, `analisa_portas_sem_continuacao` | `conectividade_externa.json`, `portas_sem_continuacao.json` |
| Tabela 10 (dano por rua) | `simulacao_interrupcoes` | `simulacao_interrupcoes.json` |
| Tabela 11 (água e encosta) | `variavel_geografica` | `variavel_geografica.json` |
| Figura 1 (do mapa ao grafo) | `figuras.fig_construcao` | `fig_construction.png` |
| Figura 2 (redes dos nove bairros) | `figuras.fig_mapas_geograficos redes` | `fig_networks.png` |
| Figura 3 (fluxo em função de f) | `sensitivity --fracao`, `figuras.fig_fluxo_f` | `fig_fluxo_f.png` |
| Figura 4 (corte de acesso na Urca e no Leme) | `localiza_corte`, `figuras.fig_mapas_geograficos corte` | `fig_cut.png` |
| Figura 5 (controles de tamanho) | `figuras.fig_controles` | `fig_controles.png` |
| Figura 6 (conectividade externa) | `figuras.fig_externa_geo` | `fig_externa.png` |
| Figura 7 (simulação de interrupções) | `simulacao_interrupcoes` | `fig_simulacao.png` |

Resultados citados só no texto: sensibilidade a `f` e à margem (`sensitivity`), desempate do
núcleo (`robustez_desempate`, `casos_adicionais`), vias de serviço (`service_um_modo`),
velocidades padrão (`velocidade_ctb`), datas e estatísticas dos dados (`estatisticas_dados`),
controles de tamanho e de forma (`nulo_fluxo_referencia`, `pedacos_fluxo1`, `controle_forma`,
`controle_tamanho_intermediacao`, `intermediacao_pareada_fontes`) e localização do corte
(`localiza_corte`).

## 6. Estrutura

```text
grafos/
  requirements.txt
  data/        caches do OSM, polígonos, altimetria e dados do IBGE
  output/      resultados e figuras geradas
  src/
    caminhos.py            caminhos do projeto (ROOT, DATA, OUT, FIGURES)
    executar_pipeline.py   executa as etapas na ordem
    ruff.toml              padrões de estilo (PEP 8, 100 colunas)
    nucleo/                grafo, leitura do OSM, polígonos, conectividade, fluxo máximo,
                           intermediação, caminho mínimo
    analises/              uma análise por script (tabelas, controles, simulação)
    figuras/               as figuras do artigo
    testes/                verificação contra o networkx
    conferencia/           conferência manual pendente (fora do pipeline)
```

## 7. Parâmetros fixos

Sementes: o sorteio de pedaços (`nucleo/pedacos.py`) e quem o usa (`nulo_fluxo_referencia`,
`pedacos_fluxo1`, `controle_tamanho_intermediacao`, `intermediacao_pareada_fontes`) usam 7; `controle_forma` e
`test_vs_networkx`, 11; `simulacao_interrupcoes`, 13; `robustez_desempate`, 20261012.
`corte_no_a_no` não sorteia (usa todos os pares); com `--verifica`, a amostra de conferência
usa a semente 0. Núcleo: `f = 0,2` (varreduras de 0,05 a 0,5 em `sensitivity`), margem de 400 m
para descobrir as portas (`nucleo/network.py`). Pedaços sorteados: 500 por bairro e por tipo de
crescimento (bola por BFS e crescimento tipo Eden); busca de subida de encosta a partir dos 25
de menor fluxo, com 3.000 trocas por início.

### Classes de via e velocidades padrão

Vias aceitas (`highway`): motorway, trunk, primary, secondary, tertiary, unclassified,
residential, living_street, road e as variantes `*_link`. Ficam de fora `service`, `track` e
vias de pedestre (as de serviço entram só na sensibilidade, com `GRAFOS_SERVICE`). Quando a via
não tem `maxspeed`, o tempo de percurso usa a velocidade padrão da classe (km/h). Os valores
seguem o art. 61, § 1º, I, do Código de Trânsito Brasileiro (vias urbanas sem sinalização
regulamentadora: trânsito rápido 80, arteriais 60, coletoras 40, locais 30), com o mapeamento de
classes do OSM Wiki ("Default speed limits", Brasil). `motorway` = trânsito rápido; `trunk`,
`primary` e `secondary` = arterial; `tertiary` = coletora; `unclassified`, `residential` e `road` =
local; as variantes `*_link` seguem a classe-mãe. `living_street` e `service`, sem equivalente
no CTB, ficam em 20.

| Classe | km/h | Classe | km/h |
|---|---|---|---|
| motorway | 80 | motorway_link | 80 |
| trunk | 60 | trunk_link | 60 |
| primary | 60 | primary_link | 60 |
| secondary | 60 | secondary_link | 60 |
| tertiary | 40 | tertiary_link | 40 |
| unclassified | 30 | living_street | 20 |
| residential | 30 | road | 30 |

`velocidade_ctb` compara essa tabela com a usada antes (motorway 90, secondary 50, unclassified
40, links mais lentos) e com as variantes `trunk` a 80 e `secondary` a 40 km/h, na intermediação
máxima e na intermediação de aresta (Spearman e 10 maiores). O fluxo de acesso não usa o peso.

### Regras de sentido

`oneway=yes`, `true` ou `1` gera um arco no sentido dos nós; `-1` ou `reverse`, no sentido
contrário. Rotatórias (`junction=roundabout`) e vias `motorway`, `motorway_link` e `trunk_link`
são de mão única por convenção do OSM. As demais são de mão dupla.

## 8. Solução de problemas

- **`ModuleNotFoundError: nucleo`**: rode a partir de `grafos/src` e com `python -m`, sem `-I`
  e sem executar o arquivo direto.
- **A Overpass não responde (500 ou 504)**: o carregador tenta espelhos e repete; espere e rode
  de novo a etapa. Os caches em `data/` evitam o download das etapas já feitas.
- **Os números diferem dos do artigo**: confira se os caches de `data/` são os versionados (o
  nome inclui o hash do retângulo) e se as versões das bibliotecas são as de `requirements.txt`.
- **Falta o GeoPackage do IBGE**: só afeta `populacao_atras_do_corte`; as demais etapas rodam.
