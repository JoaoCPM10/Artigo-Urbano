"""
Gera os fontes do formato RISTI a partir de paper_pt.tex (fonte unica).

Uso:  py sync_risti.py [PASTA_DE_SAIDA] [--drop recorte,betweenness,controles,construction]
Le   : paper_pt.tex (corpo do artigo) e risti_front.tex (titulo, resumos e
       palavras-chave no formato RISTI, sem autoria).
Grava: paper_pt_risti.tex (versao completa) e paper_pt_risti_15p.tex (sem os
       itens de --drop, para caber em 15 paginas). Depois, build_risti_docx.py
       gera o .docx a partir de cada um (variavel de ambiente RISTI_TEX).

Itens que podem ser retirados da versao curta:
  recorte       Tabela de sensibilidade ao recorte (os numeros ficam no texto)
  betweenness   Figura da intermediacao dirigida
  controles     Figura (histogramas) do controle de tamanho
  construction  Figura do esquema mapa -> grafo
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALL = ("recorte", "betweenness", "controles", "construction")


def drop_env(t, label):
    pat = r"\\begin\{(figure|table)\}(?:(?!\\end\{\1\}).)*?\\label\{" + re.escape(label) + r"\}.*?\\end\{\1\}\n"
    out = re.sub(pat, "", t, flags=re.S)
    assert out != t, label
    return out


def sub_once(pattern, repl, text, label, count=1):
    out, n = re.subn(pattern, repl, text)
    assert n == count, (label, n)
    return out


def body_from_paper(src):
    i = src.index("\\section{Introdução}")
    j = src.index("\\bibliographystyle")
    body = src[i:j]
    body = body.replace("\\FloatBarrier\n", "")
    body = body.replace("\\section{Conclusão}", "\\section{Conclusões}")
    m = re.search(r"\\subsubsection\*\{Reprodutibilidade\.\}\s*(.*?)\s*$", body, re.S)
    assert m, "reprodutibilidade"
    repro = re.sub(r"\s*\n\s*", " ", m.group(1))
    return body[:m.start()] + "\\reproducibility{" + repro + "}\n"


def short_version(body, drops):
    if "recorte" in drops:
        body = drop_env(body, "tab:recorte")
        body = sub_once(r"A Tabela~\\ref\{tab:recorte\} compara", "Comparamos", body, "recorte")
    if "betweenness" in drops:
        body = drop_env(body, "fig:betweenness")
        body = sub_once(r"A Figura~\\ref\{fig:betweenness\} mostra a intermediação dirigida\.\s+",
                        "", body, "betweenness")
    if "controles" in drops:
        body = drop_env(body, "fig:controles")
        body = sub_once(r",\s*Figura~\\ref\{fig:controles\}b\)", ")", body, "controles b")
        body = sub_once(r"\s*\(Figura~\\ref\{fig:controles\}a\)", "", body, "controles a")
    if "construction" in drops:
        body = drop_env(body, "fig:construction")
        body = sub_once(r"\s*A\s+Figura~\\ref\{fig:construction\}\s+ilustra\s+a\s+conversão\s+do\s+mapa\s+para\s+o\s+grafo\s+dirigido\.",
                        "", body, "construction")
    return body


def main():
    args = [a for a in sys.argv[1:]]
    drops = {"recorte", "betweenness", "construction"}   # cabe em 15 paginas, com folga
    if "--drop" in args:
        k = args.index("--drop")
        drops = set(x for x in args[k + 1].split(",") if x)
        del args[k:k + 2]
    out = Path(args[0]) if args else ROOT
    paper = (ROOT / "paper_pt.tex").read_text(encoding="utf-8")
    front = (ROOT / "risti_front.tex").read_text(encoding="utf-8")
    body = body_from_paper(paper)
    (out / "paper_pt_risti.tex").write_text(front + "\n" + body, encoding="utf-8")
    (out / "paper_pt_risti_15p.tex").write_text(front + "\n" + short_version(body, drops), encoding="utf-8")
    print("gerados em", out, "| retirados da versao curta:", sorted(drops))


if __name__ == "__main__":
    main()
