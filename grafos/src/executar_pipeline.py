"""
Executa o pipeline do artigo na ordem certa, uma etapa por vez.

Cada etapa chama os mesmos comandos listados no README (`python -m pacote.script`),
na ordem em que um depende da saida do outro. O executor so' encadeia os scripts: nao
contem logica de analise.

Uso (a partir de grafos/src):
    python executar_pipeline.py --listar
    python executar_pipeline.py --etapas indicadores,tabelas
    python executar_pipeline.py --pular-lentas        # tudo, menos as etapas marcadas como lentas
    python executar_pipeline.py                       # o pipeline completo

O log de cada comando fica em output/logs/<etapa>.log (a pasta nao vai para o git).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field

from caminhos import FIGURES, OUT

AQUI = os.path.dirname(os.path.abspath(__file__))

BAIRROS = (
    "urca,leme,alto_da_boa_vista,cosme_velho,joa,sao_conrado,copacabana,botafogo,praca_da_bandeira"
)
NOVOS = "leme joa alto_da_boa_vista cosme_velho sao_conrado praca_da_bandeira".split()
# bairros que servem de origem dos pedacos sorteados nos controles de tamanho e de forma
FONTES_URCA = "copacabana,botafogo,alto_da_boa_vista,sao_conrado,praca_da_bandeira"
FONTES_LEME = FONTES_URCA + ",cosme_velho"

# Figuras que o artigo usa: nome do arquivo em output/ (o mesmo em Figures/).
FIGURAS_DO_ARTIGO = [
    "fig_construction.png",
    "fig_networks.png",
    "fig_fluxo_f.png",
    "fig_cut.png",
    "fig_controles.png",
    "fig_externa.png",
    "fig_simulacao.png",
]


@dataclass
class Comando:
    modulo: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class Etapa:
    nome: str
    descricao: str
    comandos: list[Comando]
    lenta: bool = False


def cmd(modulo, *args, **env):
    return Comando(modulo, list(args), dict(env))


ETAPAS = [
    Etapa(
        "indicadores",
        "Rede, componentes, pontes e articulacoes, fluxo de acesso e intermediacao dos 9 bairros",
        [cmd("analises.indicadores", "all")],
    ),
    Etapa(
        "vias_de_servico",
        "Redes sem e com vias de servico (artigo, todas, publicas) e as quatro contagens de rotas",
        [
            cmd("analises.service_um_modo"),
            cmd("analises.service_um_modo", GRAFOS_SERVICE="todas"),
            cmd("analises.service_um_modo", GRAFOS_SERVICE="publicas"),
        ],
    ),
    Etapa(
        "estatisticas",
        "Datas dos extratos, velocidade declarada e cadeias descartadas",
        [cmd("analises.estatisticas_dados")],
    ),
    Etapa(
        "corte_dois_nos",
        "Corte minimo entre todos os pares de interseccoes, sem e com o sentido das vias",
        [cmd("analises.corte_no_a_no", "--verifica")],
        lenta=True,
    ),
    Etapa(
        "tabelas",
        "Valores das tabelas de redes e de indicadores estruturais",
        [cmd("analises.tabelas_nove_bairros")],
    ),
    Etapa(
        "fluxo_de_acesso",
        "Fluxo por ruas e interseccoes, localizacao do corte e sensibilidade ao desempate",
        [
            cmd("analises.ruas_vs_intersecoes", "--verifica"),
            cmd("analises.casos_adicionais", *NOVOS),
            cmd("analises.robustez_desempate"),
            cmd("analises.localiza_corte"),
        ],
    ),
    Etapa(
        "sensibilidade",
        "Fluxo de acesso conforme a fracao de origem f e a margem",
        [cmd("analises.sensitivity"), cmd("figuras.fig_fluxo_f")],
    ),
    Etapa(
        "controles_de_tamanho",
        "Controles de tamanho e de forma da Urca e do Leme; intermediacao pareada",
        [
            cmd("analises.nulo_fluxo_referencia", "urca", "--fontes", FONTES_URCA),
            cmd("analises.nulo_fluxo_referencia", "leme", "--fontes", FONTES_LEME),
            cmd("analises.pedacos_fluxo1", "leme", FONTES_LEME),
            cmd("analises.controle_forma", "urca", "1000", "--fontes", FONTES_URCA),
            cmd("analises.controle_forma", "leme", "1000", "--fontes", FONTES_LEME),
            cmd("analises.controle_tamanho_intermediacao"),
            cmd("analises.intermediacao_pareada_fontes", "urca"),
            cmd("analises.intermediacao_pareada_fontes", "leme"),
            cmd("figuras.fig_controles"),
        ],
        lenta=True,
    ),
    Etapa(
        "conectividade_externa",
        "Rede ampliada (500 m, 1 km, 2 km), cortes, portas sem continuacao e a figura",
        [
            cmd("analises.conectividade_externa", "--verifica", "--bairros", BAIRROS),
            cmd("analises.analisa_portas_sem_continuacao", BAIRROS),
            cmd("figuras.fig_externa_geo"),
        ],
        lenta=True,
    ),
    Etapa(
        "simulacao",
        "Simulacao de interrupcoes, dano por rua e sensibilidade a tabela de velocidades",
        [
            cmd("analises.simulacao_interrupcoes", "--verifica", "--bairros", BAIRROS),
            cmd("analises.velocidade_ctb"),
        ],
        lenta=True,
    ),
    Etapa(
        "geografia_e_populacao",
        "Agua e encosta no perimetro, e populacao atras do corte (precisa dos dados do IBGE)",
        [
            cmd("analises.variavel_geografica"),
            cmd("analises.variavel_geografica_sens"),
            cmd("analises.populacao_atras_do_corte"),
        ],
    ),
    Etapa(
        "figuras",
        "Figuras 1, 2 e 4 (construcao do grafo, mapas das redes e do corte)",
        [cmd("figuras.fig_construcao"), cmd("figuras.fig_mapas_geograficos", "todas")],
    ),
    Etapa(
        "testes",
        "Confere as implementacoes contra o networkx",
        [cmd("testes.test_vs_networkx"), cmd("testes.test_betweenness")],
    ),
    Etapa("copiar_figuras", "Copia as 7 figuras do artigo para Figures/", []),
]
NOMES_DAS_ETAPAS = [e.nome for e in ETAPAS]


def copiar_figuras():
    os.makedirs(FIGURES, exist_ok=True)
    for nome in FIGURAS_DO_ARTIGO:
        origem = os.path.join(OUT, nome)
        if not os.path.exists(origem):
            print(f"  [falta] {nome} (rode a etapa que a gera)")
            continue
        shutil.copyfile(origem, os.path.join(FIGURES, nome))
        print(f"  copiada: {nome}")


def rodar_comando(c: Comando, log) -> int:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", **c.env)
    linha = [sys.executable, "-m", c.modulo, *c.args]
    texto = " ".join(f"{k}={v}" for k, v in c.env.items()) + " " if c.env else ""
    resumo = texto + "python -m " + c.modulo + (" " + " ".join(c.args) if c.args else "")
    print(f"  $ {resumo[:150]}", flush=True)
    log.write(f"\n$ {resumo}\n")
    log.flush()
    r = subprocess.run(linha, cwd=AQUI, env=env, stdout=log, stderr=subprocess.STDOUT)
    return r.returncode


def listar():
    print(f"{'etapa':24s} {'lenta':5s} descricao")
    for e in ETAPAS:
        print(f"{e.nome:24s} {'sim' if e.lenta else '':5s} {e.descricao}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Executa o pipeline do artigo na ordem certa.")
    ap.add_argument("--listar", action="store_true", help="mostra as etapas e sai")
    ap.add_argument("--etapas", help="etapas separadas por virgula (padrao: todas)")
    ap.add_argument("--pular-lentas", action="store_true", help="nao roda as etapas lentas")
    args = ap.parse_args(argv)

    if args.listar:
        listar()
        return 0
    escolhidas = args.etapas.split(",") if args.etapas else NOMES_DAS_ETAPAS
    desconhecidas = [n for n in escolhidas if n not in NOMES_DAS_ETAPAS]
    if desconhecidas:
        print("etapas desconhecidas:", ", ".join(desconhecidas))
        print("use --listar para ver as etapas")
        return 2

    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    inicio = time.perf_counter()
    for e in ETAPAS:
        if e.nome not in escolhidas:
            continue
        if args.pular_lentas and e.lenta and not args.etapas:
            print(f"[pulada] {e.nome} (lenta)")
            continue
        print(f"\n== {e.nome}: {e.descricao}", flush=True)
        t0 = time.perf_counter()
        if e.nome == "copiar_figuras":
            copiar_figuras()
        else:
            with open(os.path.join(OUT, "logs", f"{e.nome}.log"), "w", encoding="utf-8") as log:
                for c in e.comandos:
                    codigo = rodar_comando(c, log)
                    if codigo != 0:
                        print(f"[erro] {c.modulo} terminou com codigo {codigo}")
                        print(f"       veja output/logs/{e.nome}.log")
                        return codigo
        print(f"   ok em {time.perf_counter() - t0:.0f} s", flush=True)
    print(f"\nPipeline concluido em {(time.perf_counter() - inicio) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
