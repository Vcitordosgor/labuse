"""EXPORTS-2 lot 1.2 — LE RENDU UNIQUE : un seul moteur (WeasyPrint 69), une seule feuille
(`theme.css` = `maquette.css` versionnée), un cartouche `@page` (nom du document, IDU, adresse,
n° de rapport, « données LABUSE au », version du modèle, page x/y).

Ce module porte AUSSI les primitives HTML partagées par les blocs (tableau clé/valeur, verdict,
tuiles, encarts) — les blocs composent des fragments, ils n'écrivent jamais de `<html>` ni de CSS.
Aucun calcul, aucune requête ici : de la mise en forme.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from pathlib import Path

_PKG = Path(__file__).resolve().parent
_FONTS = _PKG.parent / "api" / "fonts"

#: @font-face injecté : Inter (fournie) pour le texte ; la mono de LABUSE (JetBrains) tient la
#: place d'« IBM Plex Mono » du gabarit (même intention monospace ; la CSS garde DejaVu en repli).
_FONT_FACE = f"""
@font-face {{ font-family: "Inter"; src: url("file://{_FONTS/'Inter-Regular.ttf'}"); font-weight: 400; }}
@font-face {{ font-family: "Inter"; src: url("file://{_FONTS/'SpaceGrotesk-Bold.ttf'}"); font-weight: 700; }}
@font-face {{ font-family: "IBM Plex Mono"; src: url("file://{_FONTS/'JetBrainsMono-Regular.ttf'}"); }}
"""


def esc(s) -> str:
    """Échappe une valeur pour le HTML. `None` → chaîne vide (le bloc décide de « non chiffré »)."""
    return _html.escape("" if s is None else str(s))


# ── primitives (classes de theme.css) ────────────────────────────────────────────────────

def chip_span(classe: str, libelle: str) -> str:
    return f'<span class="chip {esc(classe)}">{esc(libelle)}</span>'


def ligne_kv(cle: str, valeur_html: str, chip_html: str = "") -> str:
    """Une ligne clé / valeur / nature. `valeur_html` est déjà du HTML sûr (composé par le bloc)."""
    return (f'<tr><td class="k">{esc(cle)}</td><td>{valeur_html}</td>'
            f'<td class="n">{chip_html}</td></tr>')


def table_kv(lignes: list[str], entete: str = "") -> str:
    return f'<table class="kv">{entete}{"".join(lignes)}</table>'


def verdict(texte_html: str, ton: str = "", petit_html: str = "") -> str:
    """Le verdict de section — l'élément mémorable. `ton` ∈ {'', 'warn', 'neutral'}."""
    classe = "verdict" + (f" {ton}" if ton else "")
    petit = f"<small>{petit_html}</small>" if petit_html else ""
    return f'<div class="{classe}">{texte_html}{petit}</div>'


def tuiles(items: list[tuple[str, str]]) -> str:
    """Trois tuiles au plus (valeur, libellé) — jamais un chiffre seul en hero (LISEZMOI)."""
    cells = "".join(f'<div class="tile"><div class="v">{esc(v)}</div>'
                    f'<div class="l">{esc(l)}</div></div>' for v, l in items)
    return f'<div class="tiles">{cells}</div>'


def section(titre: str, corps_html: str) -> str:
    return f'<section><h2>{esc(titre)}</h2>{corps_html}</section>'


def note(texte: str) -> str:
    return f'<p class="note">{esc(texte)}</p>'


def aside(texte_html: str, variante: str = "") -> str:
    classe = "aside" + (f" {variante}" if variante else "")
    return f'<div class="{classe} keep">{texte_html}</div>'


# ── le document complet + le rendu ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Cartouche:
    """Les chaînes du cartouche @page (une par document)."""
    doc_title: str        # « LABUSE — <document> · <adresse> »
    doc_ref: str          # « <IDU> · <numéro de rapport> »
    doc_foot: str         # la mention de bas de page


def _spans_cartouche(c: Cartouche) -> str:
    return (f'<span class="doc-title" style="display:none">{esc(c.doc_title)}</span>'
            f'<span class="doc-ref" style="display:none">{esc(c.doc_ref)}</span>'
            f'<span class="doc-foot" style="display:none">{esc(c.doc_foot)}</span>')


def page_html(titre_html: str, cartouche: Cartouche, corps_html: str, *, lang: str = "fr") -> str:
    """Le document HTML complet : theme.css liée + polices, cartouche @page, corps."""
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<title>{esc(titre_html)}</title>'
            f'<link rel="stylesheet" href="theme.css">'
            f'<style>{_FONT_FACE}</style></head><body>'
            f'{_spans_cartouche(cartouche)}{corps_html}</body></html>')


def render_pdf(page_html_str: str) -> bytes:
    """HTML complet → PDF (WeasyPrint 69). base_url = le paquet exports (theme.css relative)."""
    from weasyprint import HTML  # import paresseux : pango requis au rendu seulement
    return HTML(string=page_html_str, base_url=str(_PKG)).write_pdf()
