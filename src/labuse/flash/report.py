"""Générateur du rapport Flash — HTML/CSS (Jinja2) → PDF (WeasyPrint).

- Template VERSIONNÉ (TEMPLATE_VERSION estampillé sur la page de garde et dans le nom
  de fichier) : un changement de maquette = bump de version, jamais un écrasement muet.
- Génération IDEMPOTENTE : même (order_ref, idu, version) → même chemin ; le fichier
  existant est réutilisé sauf force=True. Objectif < 30 s.
- DA print : fond blanc, typos de la marque (fonts OFL de api/fonts, les mêmes que les
  exports fpdf2 existants), accents menthe #0B8A5F.
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import session_scope
from .carte import build_situation_map
from .data import collect_report_data

log = logging.getLogger("labuse.flash")

#: Version de la maquette du rapport (page de garde + nom de fichier).
#: 1.1 (O2) — wordmark de la page de garde « LA BUSE » → « LABUSE » (le contenu du
#: template a changé ; la version suit pour rester traçable).
TEMPLATE_VERSION = "1.1"

_TEMPLATES = Path(__file__).resolve().parent / "templates"
#: Fonts du design system (OFL) — déjà embarquées pour les exports PDF existants.
_FONTS = Path(__file__).resolve().parents[1] / "api" / "fonts"

_env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=True)


def _logo_svg_path() -> str:
    """Silhouette officielle de la buse — réutilise les points de pdf_premium (source unique)."""
    from ..api.pdf_premium import _LOGO_PTS
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in _LOGO_PTS) + " Z"


def storage_dir() -> Path:
    """Répertoire de stockage des PDF Flash (config, créé à la demande)."""
    s = get_settings()
    p = Path(s.flash_storage_dir)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[3] / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


def pdf_path_for(idu: str, order_ref: str) -> Path:
    return storage_dir() / f"flash_{_safe_name(order_ref)}_{_safe_name(idu)}_v{TEMPLATE_VERSION}.pdf"


def render_report_html(db: Session, idu: str, *, order_ref: str, adresse: str | None = None,
                       watermark: str | None = None, with_map: bool = True,
                       produit: str = "Rapport Flash",
                       produit_sous_titre: str = "RAPPORT FLASH · parcelle à l'unité") -> str:
    """Assemble les données et rend le HTML complet du rapport (CSS inliné)."""
    data = collect_report_data(db, idu, adresse=adresse)
    carte = None
    if with_map:
        carte = build_situation_map(data["parcelle"]["geojson"],
                                    cache_dir=storage_dir() / "tiles",
                                    timeout_s=get_settings().http_timeout_s)
    from ..api.export_commun import SOURCES_ATTRIBUTION  # source unique (M6 2a)
    css = _env.get_template("rapport.css").render(
        fonts_dir=_FONTS.as_uri(), order_ref=order_ref, produit=produit,
        date_generation=data["date_generation"], watermark=watermark)
    return _env.get_template("rapport.html.j2").render(
        data=data, carte=carte, css=Markup(css), order_ref=order_ref,
        produit_sous_titre=produit_sous_titre,
        watermark=watermark, template_version=TEMPLATE_VERSION,
        logo_path=_logo_svg_path(), sources_attribution=SOURCES_ATTRIBUTION)


def generate_flash_report(idu: str, *, order_ref: str = "DEMO", adresse: str | None = None,
                          watermark: str | None = None, force: bool = False,
                          db: Session | None = None, with_map: bool = True) -> Path:
    """Génère (ou réutilise) le rapport Flash d'une parcelle → chemin du PDF.

    Idempotent : si le PDF de ce (order_ref, idu, version de maquette) existe déjà et
    que force=False, il est réutilisé tel quel (re-livraison sans double génération).
    """
    target = pdf_path_for(idu, order_ref)
    if target.exists() and not force:
        log.info("flash %s : PDF déjà présent (%s) — réutilisé", order_ref, target.name)
        return target

    t0 = time.monotonic()
    if db is not None:
        html = render_report_html(db, idu, order_ref=order_ref, adresse=adresse,
                                  watermark=watermark, with_map=with_map)
    else:
        with session_scope() as session:
            html = render_report_html(session, idu, order_ref=order_ref, adresse=adresse,
                                      watermark=watermark, with_map=with_map)

    from weasyprint import HTML  # import paresseux : lib système (pango) requise au rendu seulement
    tmp = target.with_suffix(".pdf.tmp")
    HTML(string=html, base_url=str(_TEMPLATES)).write_pdf(str(tmp))
    tmp.replace(target)  # écriture atomique : jamais de PDF tronqué servi à un client
    log.info("flash %s : rapport %s généré en %.1f s", order_ref, target.name,
             time.monotonic() - t0)
    return target
