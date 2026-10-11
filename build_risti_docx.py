"""
Gera o .docx do artigo no formato RISTI a partir de paper_pt_risti.tex.

Uso:  py build_risti_docx.py TEMPLATE.docx SAIDA.docx
  TEMPLATE.docx: formato-pt.doc (RISTI) salvo como .docx (estilos title,
                 heading1-georgia, heading2, figlegend, tablelegend, References).
Requer: pip install python-docx
O texto vem de paper_pt_risti.tex, as referencias de references.bib e as
figuras de Figures/. Para atualizar o artigo, edite o .tex e rode de novo.
"""
import os
import re
import sys
import unicodedata
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent
TEX = Path(os.environ.get("RISTI_TEX", ROOT / "paper_pt_risti.tex"))
BIB = ROOT / "references.bib"
FIGS = ROOT / "Figures"
NBSP = "\u00a0"
TEXTWIDTH_CM = 13.0

# ------------------------------------------------------------------ helpers
def get_arg(text, cmd):
    """Conteudo do primeiro \\cmd{...} (chaves balanceadas) e o texto sem ele."""
    m = re.search(r"\\" + cmd + r"\{", text)
    if not m:
        return None, text
    i, depth = m.end(), 1
    while depth:
        c = text[i]
        depth += (c == "{") - (c == "}")
        i += 1
    return text[m.end():i - 1].strip(), text[:m.start()] + text[i:]


ACCENTS = {r"\'u": "ú", r"\~n": "ñ", r"\'i": "í", r"\'o": "ó", r"\'e": "é", r"\'a": "á"}


def clean_bib(s):
    for k, v in ACCENTS.items():
        s = s.replace(k, v)
    s = s.replace("\\&", "&").replace("--", "-")
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = s.replace("\\_", "_").replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


# --------------------------------------------------------------- bibliografia
def parse_bib():
    txt = BIB.read_text(encoding="utf-8")
    txt = "\n".join(l for l in txt.splitlines() if not l.lstrip().startswith("%"))
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),", txt):
        kind, key = m.group(1).lower(), m.group(2).strip()
        start = m.end()
        depth, i = 1, m.start() + txt[m.start():].index("{") + 1
        while depth:
            c = txt[i]
            depth += (c == "{") - (c == "}")
            i += 1
        body = txt[start:i - 1]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            j = fm.end()
            if body[j] == "{":
                d, k = 1, j + 1
                while d:
                    d += (body[k] == "{") - (body[k] == "}")
                    k += 1
                fields[fm.group(1).lower()] = body[j + 1:k - 1]
        entries[key] = {"type": kind, **fields}
    return entries


def authors_of(e):
    raw = clean_bib(e.get("author", ""))
    if e["type"] == "misc":
        return [("Instituto Pereira Passos (IPP)", "")]
    out = []
    for a in raw.split(" and "):
        last, first = [x.strip() for x in a.split(",", 1)]
        out.append((last, first))
    return out


def initials(first):
    parts = re.split(r"[\s]+", first)
    return " ".join(p[0] + "." if not p.endswith(".") else p for p in parts if p)


def apa_authors(auth):
    names = [f"{l}, {initials(f)}" if f else l for l, f in auth]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def cite_label(e, narrative=False):
    auth = authors_of(e)
    year = e["year"]
    if e["type"] == "misc":
        return f"Instituto Pereira Passos [IPP], {year}" if not narrative else year
    s = auth[0][0] if len(auth) == 1 else (f"{auth[0][0]} & {auth[1][0]}" if len(auth) == 2 else f"{auth[0][0]} et al.")
    return year if narrative else f"{s}, {year}"


def apa_reference(e):
    auth, year = apa_authors(authors_of(e)), e["year"]
    title = clean_bib(e.get("title", ""))
    doi = f" https://doi.org/{e['doi']}" if e.get("doi") else ""
    t = e["type"]
    if t == "article":
        vol = f", <i>{e['volume']}</i>" if e.get("volume") else ""
        num = f"({e['number']})" if e.get("number") else ""
        pg = f", {clean_bib(e['pages'])}" if e.get("pages") else ""
        return f"{auth} ({year}). {title}. <i>{clean_bib(e['journal'])}</i>{vol}{num}{pg}.{doi}"
    if t in ("incollection", "inproceedings"):
        extra = []
        if e.get("series"):
            extra.append(clean_bib(e["series"]))
        if e.get("volume"):
            extra.append(f"Vol. {e['volume']}")
        if e.get("pages"):
            extra.append(f"pp. {clean_bib(e['pages'])}")
        extra = f" ({', '.join(extra)})" if extra else ""
        return f"{auth} ({year}). {title}. In <i>{clean_bib(e['booktitle'])}</i>{extra}. {clean_bib(e['publisher'])}.{doi}"
    if t == "book":
        return f"{auth} ({year}). <i>{title}</i>. {clean_bib(e['publisher'])}.{doi}"
    if t == "misc":
        return (f"Instituto Pereira Passos (IPP). ({year}). <i>Limite de bairros</i> [Conjunto de dados]. "
                f"Data.Rio. {e['url']}")
    raise ValueError(t)


# --------------------------------------------------------------- conversao
SUB_O, SUB_C, SUP_O, SUP_C = "\x01", "\x02", "\x03", "\x04"


def math(m):
    s = m.replace("{,}", ",").replace(r"\,", "\u2009").replace(r"\mathrm{round}", "round")
    s = s.replace(r"\in", "∈").replace(r"\to", " → ").replace(r"\sqrt{n}", "√n")
    s = re.sub(r"_\{\\text\{(\w+)\}\}", lambda x: SUB_O + x.group(1) + SUB_C, s)
    s = re.sub(r"\^\{([^}]*)\}", lambda x: SUP_O + x.group(1) + SUP_C, s)
    s = re.sub(r"\s*\n\s*", " ", s).replace("-", "−").replace("=", " = ").replace(";", ";")
    s = re.sub(r"(?<![A-Za-z\x01-\x04])([A-Za-z])(?![A-Za-z])", r"<i>\1</i>", s)
    s = s.replace(SUB_O, "<sub>").replace(SUB_C, "</sub>").replace(SUP_O, "<sup>").replace(SUP_C, "</sup>")
    s = re.sub(r" +", " ", s).strip()
    return s.replace(") (", ")(")


class Converter:
    def __init__(self, bib):
        self.bib = bib
        self.labels = {}
        self.cited = []

    def cite(self, keys, narrative):
        keys = [k.strip() for k in keys.split(",")]
        for k in keys:
            if k not in self.cited:
                self.cited.append(k)
        if narrative:
            return "(" + "; ".join(cite_label(self.bib[k], True) for k in keys) + ")"
        return "(" + "; ".join(cite_label(self.bib[k]) for k in keys) + ")"

    def inline(self, s):
        s = re.sub(r"\s*\n\s*", " ", s)
        # citacoes (narrativas se o texto anterior termina em "et al." ou "A e B")
        def rep_cite(m):
            before = s[:m.start()]
            narr = bool(re.search(r"(et al\.|[A-Z][\w\-]+ e [A-Z][\w\-]+|\b(?:de|segue) [A-Z][\w\-]+)$", before))
            return (" " if not narr else " ") + self.cite(m.group(1), narr)
        s = re.sub(r"~?\\cite\{([^}]*)\}", rep_cite, s)
        s = re.sub(r"\\ref\{([^}]*)\}", lambda m: self.labels[m.group(1)], s)
        s = re.sub(r"\\emph\{([^}]*)\}", r"<i>\1</i>", s)
        s = re.sub(r"\\texttt\{([^}]*)\}", lambda m: "<m>" + m.group(1).replace("\\_", "_") + "</m>", s)
        s = s.replace(r"\textcopyright{}", "©").replace("\\%", "%").replace("\\_", "_")
        s = re.sub(r"\$([^$]*)\$", lambda m: math(m.group(1)), s)
        s = s.replace("\\,", " ").replace("--", "-")
        s = s.replace("~", NBSP)
        return re.sub(r" +", " ", s).strip()


# ------------------------------------------------------------ escrita docx
def set_font(run, name, size):
    run.font.name = name
    rf = run._element.rPr.rFonts
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    run.font.size = Pt(size)


def add_runs(par, text, size=10, base_bold=False, base_italic=False):
    """Escreve `text` (com <i>, <b>, <m>, <sub>, <sup>) em Georgia `size`."""
    state = {"i": base_italic, "b": base_bold, "m": False, "sub": False, "sup": False}
    for tok in re.split(r"(</?(?:i|b|m|sub|sup)>)", text):
        mt = re.fullmatch(r"<(/?)(i|b|m|sub|sup)>", tok)
        if mt:
            state[mt.group(2)] = not mt.group(1)
            continue
        if not tok:
            continue
        r = par.add_run(tok)
        r.italic = state["i"] or None
        r.bold = state["b"] or None
        set_font(r, "Courier New" if state["m"] else "Georgia", size - 1 if state["m"] else size)
        r.font.subscript = state["sub"] or None
        r.font.superscript = state["sup"] or None


def style_exists(doc, name):
    return any(s.name == name for s in doc.styles)


# Formatacao do template RISTI (formato-pt.doc); o template aplica fonte e
# espacamento direto nos paragrafos, e os estilos .docx convertidos ficam em
# Times 11, entao tudo e' reaplicado aqui.
# nome: (tamanho, alinhamento, antes, depois, recuo esq., recuo dir., 1a linha)
J, L, C = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER
FMT = {
    "title": (14, L, 0, 24, 0, 0, 0),
    "abstract": (9, J, 6, 6, 1.0, 1.0, 0),
    "abstract_kw": (9, L, 6, 6, 1.0, 1.0, 0),
    "abstract_title": (9, J, 30, 6, 1.0, 1.0, 0),
    "heading1-georgia": (11, L, 18, 6, 0, 0, 0),
    "heading2": (10, L, 12, 6, 0, 0, 0),
    "Normal": (10, J, 0, 6, 0, 0, 0),
    "figlegend": (9, C, 6, 12, 0, 0, 0),
    "tablelegend": (9, C, 12, 6, 0, 0, 0),
    "References": (10, L, 0, 6, 0.7, 0, -0.7),
}
STYLE_OF = {"abstract_kw": "Estilo abstract + 10 pt Antes:  12 pto", "abstract_title": "Estilo abstract + 10 pt Antes:  12 pto"}


def para(doc, kind, text="", **kw):
    size, align, before, after, left, right, first = FMT[kind]
    name = STYLE_OF.get(kind, kind)
    p = doc.add_paragraph(style=name if style_exists(doc, name) else "Normal")
    pf = p.paragraph_format
    p.alignment = align
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.left_indent, pf.right_indent, pf.first_line_indent = Cm(left), Cm(right), Cm(first)
    pf.line_spacing = 1.0
    if kind.startswith("heading") or kind == "title":
        pf.keep_with_next = True
    if text:
        add_runs(p, text, size=size, **kw)
    p._fmt_size = size
    return p


def set_cell_border(cell, **edges):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        tcPr.append(b)
    for edge, sz in edges.items():
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), "000000")
        b.append(el)


def add_table(doc, rows, conv, nheader=1, breaks=()):
    ncol = max(len(r) for r in rows)
    t = doc.add_table(rows=len(rows), cols=ncol)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    first_w = {4: 5.6, 7: 2.4}.get(ncol, 5.6)
    for ri, row in enumerate(rows):
        tr = t.rows[ri]._tr
        trPr = tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trPr.append(cs)
        for ci in range(ncol):
            cell = t.cell(ri, ci)
            txt = conv.inline(row[ci]) if ci < len(row) else ""
            p = cell.paragraphs[0]
            p.style = doc.styles["Normal"] if not style_exists(doc, "Normal") else p.style
            add_runs(p, txt, size=8, base_bold=(ri < nheader))
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 or (ncol == 7 and ci == 1) else WD_ALIGN_PARAGRAPH.RIGHT
            if ncol == 4:
                cell.width = Cm(first_w if ci == 0 else (13.0 - first_w) / 3)
            else:
                cell.width = Cm([2.2, 2.4, 1.2, 1.5, 1.6, 1.6, 1.5][ci])
            edges = {}
            if ri == 0:
                edges.update(top=8)
            if ri == nheader - 1:
                edges.update(bottom=4)
            if ri in breaks:
                edges.update(top=2)
            if ri == len(rows) - 1:
                edges.update(bottom=8)
            set_cell_border(cell, **edges)
            if ri < len(rows) - 1:
                p.paragraph_format.keep_with_next = True
    return t


# ------------------------------------------------------------------ build
def main(template, out):
    bib = parse_bib()
    conv = Converter(bib)
    tex = TEX.read_text(encoding="utf-8")
    tex = "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))

    front = {}
    for cmd in ("title", "abstractpt", "keywordspt", "entitle", "abstracten", "keywordsen"):
        front[cmd], tex = get_arg(tex, cmd)
    repro, tex = get_arg(tex, "reproducibility")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", tex) if b.strip()]

    # 1a passada: numeracao e rotulos
    sec = sub = fig = tab = 0
    parsed = []
    for b in blocks:
        m = re.match(r"\\(section|subsection)\{(.*?)\}\s*(?:\\label\{(.*?)\})?$", b, re.S)
        if m:
            if m.group(1) == "section":
                sec, sub = sec + 1, 0
                num = f"{sec}"
            else:
                sub += 1
                num = f"{sec}.{sub}"
            if m.group(3):
                conv.labels[m.group(3)] = num
            parsed.append(("sec" if m.group(1) == "section" else "sub", num, m.group(2)))
            continue
        m = re.match(r"\\begin\{(figure|table)\}(.*)\\end\{\1\}$", b, re.S)
        if m:
            if m.group(1) == "figure":
                fig += 1
                num = fig
            else:
                tab += 1
                num = tab
            body = m.group(2)
            cap, body = get_arg(body, "caption")
            lab, body = get_arg(body, "label")
            conv.labels[lab] = str(num)
            parsed.append((m.group(1), num, cap, body))
            continue
        parsed.append(("p", b))

    doc = Document(template)
    body_el = doc.element.body
    for child in list(body_el):
        if child.tag != qn("w:sectPr"):
            body_el.remove(child)

    # ---- frente: titulo, resumo, abstract (sem autoria: revisao duplo-cega)
    para(doc, "title", conv.inline(front["title"]), base_bold=True)
    para(doc, "abstract", "<b>Resumo:</b> " + conv.inline(front["abstractpt"]))
    para(doc, "abstract_kw", "<b>Palavras-chave:</b> " + conv.inline(front["keywordspt"]) + ".")
    para(doc, "abstract_title", conv.inline(front["entitle"]), base_bold=True, base_italic=True)
    para(doc, "abstract", "<b>Abstract:</b> " + conv.inline(front["abstracten"]))
    para(doc, "abstract_kw", "<b>Keywords:</b> " + conv.inline(front["keywordsen"]) + ".")

    # ---- corpo
    for it in parsed:
        kind = it[0]
        if kind == "sec":
            para(doc, "heading1-georgia", f"{it[1]}.\t{conv.inline(it[2])}", base_bold=True)
        elif kind == "sub":
            para(doc, "heading2", f"{it[1]}. {conv.inline(it[2])}", base_bold=True)
        elif kind == "p":
            para(doc, "Normal", conv.inline(it[1]))
        elif kind == "figure":
            num, cap, body = it[1], it[2], it[3]
            m = re.search(r"\\includegraphics\[width=([\d.]*)(?:\\textwidth)?\]\{(?:Figures/)?(.*?)\}", body)
            frac = float(m.group(1)) if m.group(1) else 1.0
            pp = doc.add_paragraph(style="Normal")
            pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pp.paragraph_format.keep_with_next = True
            pp.paragraph_format.space_before = Pt(6)
            pp.add_run().add_picture(str(FIGS / m.group(2)), width=Cm(min(frac * TEXTWIDTH_CM, 12.5)))
            para(doc, "figlegend", f"Figura {num} \u2013 {conv.inline(cap)}")
        elif kind == "table":
            num, cap, body = it[1], it[2], it[3]
            c = para(doc, "tablelegend", f"Tabela {num} \u2013 {conv.inline(cap)}")
            c.paragraph_format.keep_with_next = True
            tb = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*)\\end\{tabular\}", body, re.S).group(1)
            tb = tb.replace("\\toprule", "").replace("\\bottomrule", "")
            blocks = tb.split("\\midrule")
            rows, breaks, nheader = [], set(), 1
            for bi, b in enumerate(blocks):
                brows = [[x.strip() for x in r.split("&")] for r in re.split(r"\\\\\s*", b.strip()) if r.strip()]
                if bi == 0 and len(blocks) > 1:
                    nheader = len(brows)
                if bi >= 2:
                    breaks.add(len(rows))
                rows += brows
            add_table(doc, rows, conv, nheader=nheader, breaks=breaks)
            sp = doc.add_paragraph(style="Normal")
            sp.paragraph_format.space_before = sp.paragraph_format.space_after = Pt(0)
            sp.paragraph_format.line_spacing = Pt(8)

    para(doc, "Normal", "<b>Reprodutibilidade:</b> " + conv.inline(repro))

    # ---- referencias (APA 7, ordem alfabetica)
    para(doc, "heading1-georgia", "Referências", base_bold=True)
    keys = sorted(conv.cited, key=lambda k: (strip_accents(authors_of(bib[k])[0][0]), bib[k]["year"]))
    for k in keys:
        para(doc, "References", apa_reference(bib[k]))
    unused = [k for k in bib if k not in conv.cited]

    cp = doc.core_properties
    for attr in ("author", "last_modified_by", "title", "subject", "comments", "keywords", "category"):
        setattr(cp, attr, "")
    doc.save(out)
    scrub(out)
    print(f"salvo {out}; refs citadas: {len(conv.cited)}; nao citadas (omitidas): {unused}")


def scrub(path):
    """Remove metadados herdados do template (propriedades personalizadas,
    e-mail de exemplo, hiperlinks) para a versao de revisao duplo-cega."""
    import shutil
    import zipfile
    tmp = str(path) + ".tmp"
    empty_custom = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
                    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"/>')
    empty_app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                 '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                 '<Application>Microsoft Office Word</Application></Properties>')
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/custom.xml":
                data = empty_custom.encode("utf-8")
            elif item.filename == "docProps/app.xml":
                data = empty_app.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                data = re.sub(rb'<Relationship [^>]*TargetMode="External"[^>]*/>', b"", data)
            zout.writestr(item, data)
    shutil.move(tmp, path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
