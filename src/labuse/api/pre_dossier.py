"""Pack « pré-dossier PC » (mandat wave-adresses, Lot 5) — préparatoire, PAS un dossier.

Contenu du ZIP pour UNE parcelle :
 1. CERFA n° 13406*17 (vérifié en vigueur au 01/07/2026, vendorisé data/cerfa/) —
    PDF REMPLISSABLE pré-rempli des SEULS champs parcelle/terrain (références
    cadastrales, adresse BAN, superficie, cadre 3.1) ; champs projet laissés VIDES.
 2. Plan de situation auto (fond OSM + contour de la parcelle + cadastre en libellés).
 3. Fiche des règles du zonage (PLU calibré) + liste des pièces PCMI exigées +
    servitudes connues (ABF, ENS, QPV…).

LIBELLÉ IMPÉRATIF sur CHAQUE page de chaque document (mandat §5.2). Réservé au plan
Intégral (gating stubbé Phase 0).
"""
from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import plans

log = logging.getLogger("labuse.pre_dossier")
router = APIRouter(prefix="/pre-dossier", tags=["pre-dossier"])

CERFA_VERSION = "13406*17"      # vérifié le 10/07/2026 (en vigueur depuis le 01/07/2026)
_CERFA_PATH = Path(__file__).resolve().parents[3] / "data" / "cerfa" / "cerfa_13406-17.pdf"
_FONTS = Path(__file__).resolve().parent / "fonts"

LIBELLE = ("Document préparatoire établi à partir de données publiques — ne constitue "
           "pas un dossier de demande de permis. À compléter et vérifier par le "
           "pétitionnaire ou son architecte.")

#: pièces exigées pour un PC maison individuelle (bordereau du CERFA 13406)
PIECES_PCMI = [
    ("PCMI1", "Plan de situation du terrain", "fourni dans ce pack (à vérifier)"),
    ("PCMI2", "Plan de masse des constructions", "à établir par le pétitionnaire"),
    ("PCMI3", "Plan en coupe du terrain et de la construction", "à établir"),
    ("PCMI4", "Notice décrivant le terrain et le projet", "à établir"),
    ("PCMI5", "Plan des façades et des toitures", "à établir"),
    ("PCMI6", "Document graphique d'insertion", "à établir"),
    ("PCMI7", "Photographie situant le terrain dans l'environnement proche", "à fournir"),
    ("PCMI8", "Photographie situant le terrain dans le paysage lointain", "à fournir"),
]


def get_db():
    from .app import get_db as _g
    yield from _g()


def _tampon_libelle() -> bytes:
    """Une page A4 transparente portant le libellé préparatoire (bandeau bas de page)."""
    from fpdf import FPDF
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("inter", fname=str(_FONTS / "Inter-Regular.ttf"))
    pdf.add_page()
    pdf.set_fill_color(255, 244, 214)
    pdf.rect(6, 285, 198, 8, style="F")
    pdf.set_font("inter", size=6.8)
    pdf.set_text_color(120, 90, 20)
    pdf.set_xy(8, 286.6)
    pdf.multi_cell(194, 2.6, LIBELLE, align="C")
    return bytes(pdf.output())


def _cerfa_prerempli(parcelle: dict, adresse: dict | None) -> bytes:
    """Remplit les SEULS champs terrain du CERFA (cadre 3.1) + superficie totale,
    puis tamponne le libellé préparatoire sur CHAQUE page."""
    from pypdf import PdfReader, PdfWriter
    if not _CERFA_PATH.exists():
        raise HTTPException(503, f"CERFA {CERFA_VERSION} absent ({_CERFA_PATH}) — "
                                 "re-télécharger depuis formulaires.service-public.gouv.fr.")
    reader = PdfReader(str(_CERFA_PATH))
    writer = PdfWriter(clone_from=reader)
    idu = parcelle["idu"]
    champs = {
        # adresse du terrain (BAN si connue)
        "T2Q_numero": (adresse or {}).get("numero") or "",
        "T2V_voie": (adresse or {}).get("voie") or "",
        "T2W_lieudit": "",
        "T2L_localite": parcelle["commune"],
        "T2C_code": (adresse or {}).get("code_postal") or "",
        # références cadastrales — parcelle 1 (préfixe = caractères 6-8 de l'IDU)
        "T2F_prefixe": idu[5:8],
        "T2S_section": parcelle["section"] or "",
        "T2N_numero": parcelle["numero"] or "",
        "T2T_superficie": str(int(parcelle["surface_m2"])) if parcelle["surface_m2"] else "",
        "D5T_total": str(int(parcelle["surface_m2"])) if parcelle["surface_m2"] else "",
    }
    for page in writer.pages:
        writer.update_page_form_field_values(page, champs)
    # NeedAppearances : les valeurs restent visibles dans tous les lecteurs PDF
    try:
        writer.set_need_appearances_writer(True)
    except Exception:  # noqa: BLE001 — selon version pypdf
        pass
    tampon = PdfReader(io.BytesIO(_tampon_libelle())).pages[0]
    for page in writer.pages:
        page.merge_page(tampon)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


_PAGE_CSS = """
@page {{ size: A4; margin: 16mm;
  @bottom-center {{ content: "{libelle}";
    font-family: sans-serif; font-size: 6.5pt; color: #78551477; }} }}
body {{ font-family: sans-serif; color: #28322D; font-size: 10pt; }}
h1 {{ font-size: 15pt; color: #111814; border-bottom: 1.4pt solid #0B8A5F;
     padding-bottom: 2mm; }}
h2 {{ font-size: 11.5pt; color: #111814; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ border-bottom: 0.5pt solid #D8E2DC; padding: 1.6mm 2mm 1.6mm 0;
         text-align: left; font-size: 9pt; vertical-align: top; }}
th {{ color: #5F6C65; text-transform: uppercase; font-size: 7pt;
     border-bottom: 0.8pt solid #0B8A5F; }}
.note {{ font-size: 8pt; color: #5F6C65; }}
.bandeau {{ background: #FFF4D6; border-radius: 2mm; padding: 3mm 4mm;
           font-size: 8.5pt; color: #785514; }}
"""


def _html_pdf(html_body: str, titre: str) -> bytes:
    from weasyprint import HTML
    css = _PAGE_CSS.format(libelle=LIBELLE.replace('"', ''))
    doc = (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>"
           f"<style>{css}</style></head><body>"
           f"<div class='bandeau'>{LIBELLE}</div><h1>{titre}</h1>{html_body}</body></html>")
    return HTML(string=doc).write_pdf()


def _plan_situation(db: Session, parcelle: dict) -> bytes | None:
    """Plan de situation : fond OSM + contour (réutilise la carte du module Flash)."""
    try:
        from ..flash.carte import build_situation_map
        from ..flash.report import storage_dir
    except ImportError:
        return None
    carte = build_situation_map(parcelle["geojson"], cache_dir=storage_dir() / "tiles")
    if not carte:
        return None
    tiles = "".join(
        f"<img src='{t['data_uri']}' style='position:absolute; left:{t['left']}px;"
        f" top:{t['top']}px; width:256px; height:256px;'>" for t in carte["tiles"])
    polys = "".join(
        f"<polygon points='{p}' fill='rgba(11,138,95,0.18)' stroke='#0B8A5F'"
        f" stroke-width='2.5'/>" for p in carte["polygons"])
    body = (f"<p>Parcelle <b>{parcelle['idu']}</b> · {parcelle['commune']} · section "
            f"{parcelle['section']} n° {parcelle['numero']} · {parcelle['surface_m2']} m²</p>"
            f"<div style='position:relative; overflow:hidden; width:{carte['width']}px;"
            f" height:{carte['height']}px; border:0.8pt solid #D8E2DC;'>{tiles}"
            f"<svg width='{carte['width']}' height='{carte['height']}'"
            f" style='position:absolute; left:0; top:0;'>{polys}</svg></div>"
            f"<p class='note'>{carte['attribution']} · pièce indicative PCMI1 — "
            f"l'échelle exacte reste à vérifier par le pétitionnaire.</p>")
    return _html_pdf(body, "Plan de situation du terrain")


def _regles_et_pieces(db: Session, idu: str) -> bytes:
    """Fiche des règles du zonage (PLU calibré) + servitudes connues + pièces PCMI."""
    from ..flash.data import collect_report_data
    data = collect_report_data(db, idu)
    ident, pat, risq = data["identite"], data["patrimoine"], data["risques"]
    zones = "".join(f"<tr><td>{z['libelle'] or z['classe']}</td><td>{z['pct']} %</td>"
                    f"<td>{z['idurba'] or '—'}</td></tr>" for z in ident["zones"]) or \
            "<tr><td colspan='3'>Zonage non résolu</td></tr>"
    regles = ""
    if ident["regles"]:
        r = ident["regles"]
        if r.get("emprise_max_m2"):
            regles += f"<tr><td>Emprise au sol maximale (calibrée)</td><td>{r['emprise_max_m2']} m²</td></tr>"
        if r.get("hauteur_max_m"):
            regles += f"<tr><td>Hauteur maximale de la zone</td><td>{r['hauteur_max_m']} m</td></tr>"
        if r.get("confiance"):
            regles += f"<tr><td>Confiance du calibrage</td><td>{r['confiance']}</td></tr>"
    presc = "".join(f"<li>{p['libelle']}</li>" for p in ident["prescriptions"])
    servitudes = []
    if pat and pat.get("abf"):
        servitudes.append("Abords de Monument historique (~500 m) — avis ABF probable : "
                          + ", ".join(m["name"] or "monument" for m in pat["abf"]))
    for it in (pat or {}).get("couches", []):
        servitudes.append(f"{it['label']} : {it['detail'] or 'parcelle concernée'}")
    for it in (risq or {}).get("couches", []):
        servitudes.append(f"{it['label']} : {it['detail'] or 'parcelle concernée'}")
    serv_html = "".join(f"<li>{s}</li>" for s in servitudes) or \
                "<li>Aucune servitude connue dans les couches analysées.</li>"
    pieces = "".join(f"<tr><td>{c}</td><td>{lib}</td><td>{etat}</td></tr>"
                     for c, lib, etat in PIECES_PCMI)
    body = (f"<h2>Zonage du document d'urbanisme</h2>"
            f"<table><tr><th>Zone</th><th>Part</th><th>Document</th></tr>{zones}</table>"
            + (f"<h2>Règles calibrées LA BUSE</h2><table>{regles}</table>"
               f"<p class='note'>Les règles complètes du règlement (retraits, prospects, "
               f"servitudes) peuvent modifier ces valeurs.</p>" if regles else "")
            + (f"<h2>Prescriptions graphiques</h2><ul>{presc}</ul>" if presc else "")
            + f"<h2>Servitudes et périmètres connus</h2><ul>{serv_html}</ul>"
            f"<h2>Pièces à joindre (CERFA {CERFA_VERSION}, maison individuelle)</h2>"
            f"<table><tr><th>Code</th><th>Pièce</th><th>État</th></tr>{pieces}</table>")
    return _html_pdf(body, f"Règles du zonage — parcelle {idu}")


@router.get("/{idu}.zip")
def pre_dossier_zip(idu: str, request: Request, db: Session = Depends(get_db)) -> Response:
    """Pack pré-dossier PC — réservé Intégral (mandat §5.3, gating stubbé Phase 0)."""
    if not plans.acces("pre_dossier_pc"):
        raise HTTPException(403, detail=plans.refus("pre_dossier_pc"))
    p = db.execute(text(
        """SELECT idu, commune, section, numero, round(surface_m2) AS surface_m2,
                  ST_AsGeoJSON(geom, 7) AS geojson
           FROM parcels WHERE idu = :idu"""), {"idu": idu}).mappings().first()
    if not p:
        raise HTTPException(404, f"Parcelle {idu} inconnue.")
    adresse = db.execute(text(
        """SELECT a.numero, a.rep, a.voie, a.code_postal FROM adresse_parcelles ap
           JOIN adresses a ON a.id_ban = ap.id_ban WHERE ap.idu = :idu
           ORDER BY (ap.source = 'principal') DESC, a.id_ban LIMIT 1"""),
        {"idu": idu}).mappings().first() if db.execute(text(
            "SELECT to_regclass('adresse_parcelles') IS NOT NULL")).scalar() else None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"cerfa_{CERFA_VERSION.replace('*', '-')}_prerempli_{idu}.pdf",
                   _cerfa_prerempli(dict(p), dict(adresse) if adresse else None))
        plan = _plan_situation(db, dict(p))
        if plan:
            z.writestr("plan_de_situation.pdf", plan)
        z.writestr("regles_du_zonage_et_pieces.pdf", _regles_et_pieces(db, idu))
        z.writestr(zipfile.ZipInfo("LISEZMOI.txt"),
                   f"Pré-dossier PC — parcelle {idu} ({p['commune']})\n\n{LIBELLE}\n\n"
                   f"CERFA {CERFA_VERSION} : seuls les champs parcelle/terrain sont "
                   "pré-remplis ; les champs du PROJET sont volontairement vides.\n",
                   compress_type=zipfile.ZIP_STORED)   # non compressé : libellé vérifiable tel quel
    log.info("pré-dossier PC %s généré", idu)
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="pre_dossier_pc_{idu}.zip"'})
