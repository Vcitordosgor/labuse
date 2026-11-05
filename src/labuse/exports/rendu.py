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


import re as _re_nb  # noqa: E402


def esc_noms(s) -> str:
    """RECETTE-7 (E7) — comme `esc`, mais les mots à TRAIT D'UNION (noms composés : « Saint-Denis »)
    ne se coupent plus à la ligne. Le trait d'union ORDINAIRE (U+002D) est CONSERVÉ — il s'extrait
    proprement (copier-coller, pdftotext), contrairement au trait insécable U+2011 que WeasyPrint 69
    n'exporte pas (le glyphe sortait en caractère parasite, cf. F2). L'anti-coupure passe donc par
    un `white-space: nowrap` (classe .nb de theme.css), pas par le caractère. Le trait « sautait »
    dans l'en-tête du Financier (h1 long à 24 pt) : « Saint-\\nDenis » → « SaintDenis » à la copie."""
    return _re_nb.sub(r'(\w+(?:-\w+)+)', r'<span class="nb">\1</span>', esc(s))


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


def _css_str(s: str) -> str:
    """Échappe une chaîne pour un `content: "…"` CSS (double-quote) : antislash, guillemets, sauts
    de ligne retirés. CHASSE-DONNEES-FIX-1 (C-28)."""
    return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


def _spans_cartouche(c: Cartouche) -> str:
    return (f'<span class="doc-title" style="display:none">{esc(c.doc_title)}</span>'
            f'<span class="doc-ref" style="display:none">{esc(c.doc_ref)}</span>'
            f'<span class="doc-foot" style="display:none">{esc(c.doc_foot)}</span>')


def page_html(titre_html: str, cartouche: Cartouche, corps_html: str, *, lang: str = "fr",
              paysage: bool = False, page_extra_css: str = "") -> str:
    """Le document HTML complet : theme.css liée + polices, cartouche @page, corps.
    DOCS-1 (Lot C) — `paysage=True` enveloppe le corps dans `.paysage` (page A4 paysage, @page
    paysage de theme.css) : le Comparatif met ses parcelles en colonnes. Rien d'autre ne change —
    même couverture/en-tête/pied/tableaux/badges."""
    corps = f'<div class="paysage">{corps_html}</div>' if paysage else corps_html
    # CHASSE-DONNEES-FIX-1 (suite 2c, C-28) — le pied @bottom-left utilisait `content: string(doc-foot)`
    # que CE WeasyPrint NE REND PAS (0 « Données LABUSE au » dans les PDF testés). On INJECTE le pied en
    # CONTENU LITTÉRAL dans une règle @page par document (chaque PDF est rendu une fois, la valeur est
    # connue) : un content string statique SE REND (le @bottom-center du Dossier le prouve). La mention
    # légale + la date de donnée s'impriment enfin sur chaque page.
    # DOCS-COHERENCE-1 (C3) — les boîtes de marge @page N'HÉRITENT PAS du body : on y REDÉSACTIVE les
    # ligatures OpenType (sinon « aﬀaires », « transme re », « éme eur » : le « tt »/« ff » ligaturé
    # tombe à l'extraction, comme RECETTE-6 pour le corps). Correctif pour les 8 documents.
    foot_css = ('@page { @bottom-left { content: "' + _css_str(cartouche.doc_foot) + '"; '
                'font: 7.2pt "Inter","DejaVu Sans",sans-serif; color:#6B746E; '
                'font-variant-ligatures: none; '
                'font-feature-settings: "liga" 0, "clig" 0, "dlig" 0, "calt" 0 } }')
    # ANNONCE-3-FIX — `page_extra_css` : règles @page SUPPLÉMENTAIRES propres à un document (ex. le
    # compteur de pages en `white-space:nowrap`). Vide par défaut → les documents existants (servis)
    # produisent EXACTEMENT le même HTML qu'avant.
    extra = f"<style>{page_extra_css}</style>" if page_extra_css else ""
    # NU5-FIX-1 (B-F7) — WeasyPrint n'estampillait aucune CreationDate dans les métadonnées PDF
    # (un archivage/outil tiers ne trouvait pas de date). On pose `dcterms.created`/`dcterms.modified`
    # au fuseau Réunion : WeasyPrint les porte en CreationDate/ModDate du PDF. La date de génération
    # reste aussi dans le corps (pied @bottom) — ceci ne change que les métadonnées.
    # Granularité au JOUR (fuseau Réunion), comme la mention « Généré le JJ/MM/AAAA » du corps : la
    # régénération reste DÉTERMINISTE (deux passes le même jour → HTML identique), tout en posant une
    # CreationDate archivable. (Un datetime à la microseconde casserait la régénération déterministe.)
    from ..tz import today_reunion
    _jour = today_reunion().isoformat()
    _meta_date = (f'<meta name="dcterms.created" content="{_jour}">'
                  f'<meta name="dcterms.modified" content="{_jour}">')
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<title>{esc(titre_html)}</title>{_meta_date}'
            f'<link rel="stylesheet" href="theme.css">'
            f'<style>{_FONT_FACE}</style><style>{foot_css}</style>{extra}</head><body>'
            f'{_spans_cartouche(cartouche)}{corps}</body></html>')


class RenderError(RuntimeError):
    """NU4-FIX-1 (E/R1) — un rendu PDF a échoué PROPREMENT (crash natif de l'enfant, OOM borné, ou
    dépassement de délai). Remonte comme erreur applicative — jamais la mort du worker API."""


# ── NU4-FIX-1 (E/R1) — rendu HORS-PROCESS ──────────────────────────────────────────────────────
# L'audit NU4-E a mesuré 22 morts de worker sous charge, TOUTES pendant un rendu weasyprint (crash
# natif Cairo/Pango/fontTools ou tuerie mémoire OS), SANS trace Python : le rendu tournait DANS le
# worker (threads) → sa mort emportait les requêtes en vol. On isole le rendu dans un POOL DE
# PROCESSUS enfants (spawn) : un crash/OOM tue l'enfant, le worker API survit et sert une 500 propre.
import concurrent.futures as _cf  # noqa: E402
import multiprocessing as _mp  # noqa: E402
import threading as _threading  # noqa: E402

_PDF_POOL: _cf.ProcessPoolExecutor | None = None
_PDF_POOL_LOCK = _threading.Lock()


def _pdf_child_init() -> None:
    """Exécuté une fois dans CHAQUE process enfant : borne sa mémoire (RLIMIT_AS). Un PDF pathologique
    meurt alors DANS l'enfant (MemoryError/kill), pas en OOM-killant le worker API. Best-effort."""
    try:
        import resource

        from ..config import get_settings
        mo = int(get_settings().pdf_mem_max_mo)
        if mo > 0:
            octets = mo * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (octets, octets))
    except Exception:  # noqa: BLE001 — plateformes sans `resource` / setrlimit refusé : on continue
        pass


def _pdf_pool() -> _cf.ProcessPoolExecutor:
    global _PDF_POOL
    with _PDF_POOL_LOCK:
        if _PDF_POOL is None:
            from ..config import get_settings
            s = get_settings()
            _PDF_POOL = _cf.ProcessPoolExecutor(
                max_workers=max(1, int(s.pdf_rendu_max)),
                mp_context=_mp.get_context("spawn"),
                initializer=_pdf_child_init,
                max_tasks_per_child=max(1, int(s.pdf_recycle_tasks)))  # recyclage → mémoire bornée
        return _PDF_POOL


def _reset_pdf_pool() -> None:
    """Oublie le pool (après un BrokenProcessPool : un enfant est mort, on repart propre)."""
    global _PDF_POOL
    with _PDF_POOL_LOCK:
        if _PDF_POOL is not None:
            try:
                _PDF_POOL.shutdown(wait=False, cancel_futures=True)
            except Exception:  # noqa: BLE001
                pass
            _PDF_POOL = None


def _execute_isole(fn, *args, timeout: float):
    """Exécute `fn(*args)` dans le pool de processus et renvoie son résultat. Un crash de l'enfant
    (SIGSEGV, OOM) → `BrokenProcessPool` → on réinitialise le pool et on lève `RenderError`. Un
    dépassement de `timeout` → `RenderError`. Dans TOUS les cas, l'appelant (worker API) survit."""
    try:
        return _pdf_pool().submit(fn, *args).result(timeout=timeout)
    except _cf.process.BrokenProcessPool as exc:
        _reset_pdf_pool()
        raise RenderError(f"processus de rendu terminé anormalement ({type(exc).__name__})") from exc
    except _cf.TimeoutError as exc:
        raise RenderError(f"rendu PDF trop long (> {timeout:.0f}s)") from exc


def _render_worker(page_html_str: str, forms: bool) -> bytes:
    """Fonction exécutée DANS l'enfant (picklable, module-level). Importe weasyprint à froid."""
    from weasyprint import HTML  # import paresseux : pango requis au rendu seulement
    return HTML(string=page_html_str, base_url=str(_PKG)).write_pdf(pdf_forms=forms)


def render_pdf(page_html_str: str, *, forms: bool = False) -> bytes:
    """HTML complet → PDF (WeasyPrint 69). base_url = le paquet exports (theme.css relative).
    `forms=True` : les <input>/<textarea> du gabarit deviennent des champs remplissables PDF.

    NU4-FIX-1 (E/R1) : rendu HORS-PROCESS par défaut (un crash natif/OOM ne tue plus le worker).
    `LABUSE_PDF_PROCESS_ISOLE=0` repasse en rendu in-process (CI/plateformes sans spawn). La FILE
    `pdf_slot` (FIX-NU3-3) garde la concurrence bornée dans les deux modes."""
    import os

    from ..config import get_settings
    from ..perf_limits import pdf_slot
    s = get_settings()
    # Sous pytest, rendu IN-PROCESS (spawn d'un enfant weasyprint à chaque PDF = lent/fragile en CI ;
    # le mécanisme d'isolation est prouvé à part par `_execute_isole`). En service, isolé par défaut.
    isole = s.pdf_process_isole and not os.environ.get("PYTEST_CURRENT_TEST")
    with pdf_slot():                       # au plus `pdf_rendu_max` rendus à la fois (file d'attente)
        if not isole:
            return _render_worker(page_html_str, forms)   # legacy / CI : in-process
        return _execute_isole(_render_worker, page_html_str, forms,
                              timeout=float(s.pdf_rendu_timeout_s))
