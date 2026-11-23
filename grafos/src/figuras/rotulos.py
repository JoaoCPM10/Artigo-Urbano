"""
Idioma dos rotulos das figuras. O padrao e' o portugues (artigo em portugues);
FIG_LANG=en gera as mesmas figuras em ingles (para a versao em ingles).

    from figuras.rotulos import t, num
    ax.set_xlabel(t("origin fraction f", "fração de origem f"))
    ax.set_title(num(f"{x:.1f}%"))      # virgula decimal no portugues
"""
import os

LANG = os.environ.get("FIG_LANG", "pt").lower()
PT = LANG.startswith("pt")


def t(en: str, pt: str) -> str:
    """Devolve o rotulo no idioma escolhido."""
    return pt if PT else en


def num(s: str) -> str:
    """Troca o ponto decimal por virgula no portugues."""
    return s.replace(".", ",") if PT else s
