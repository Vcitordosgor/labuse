"""Pack « pré-dossier PC » (mandat wave-adresses, Lot 5) — préparatoire, PAS un dossier.

Contenu du ZIP pour UNE parcelle :
 1. CERFA n° 13406*17 (millésime vérifié le 21/08/2026, service-public.gouv.fr fiche R11637,
    vendorisé data/cerfa/) — PDF REMPLISSABLE pré-rempli des SEULS champs TERRAIN du cadre 2
    (adresse BAN du terrain + références cadastrales préfixe/section/numéro + commune) ; la
    SUPERFICIE et TOUS les champs projet/identité sont laissés VIDES (M129 §1).
 2. Plan de situation auto (fond OSM + contour de la parcelle + cadastre en libellés).
 3. Fiche des règles du zonage (PLU calibré) + liste des pièces PCMI exigées +
    servitudes connues (ABF, ENS, QPV…).

LIBELLÉ IMPÉRATIF sur CHAQUE page de chaque document (mandat §5.2). Réservé au plan
Intégral (gating stubbé Phase 0).
"""
from __future__ import annotations

import io
import logging
import math
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import plans

log = logging.getLogger("labuse.pre_dossier")
router = APIRouter(prefix="/pre-dossier", tags=["pre-dossier"])

# M129 §2 : millésime vérifié le 21/08/2026 sur service-public.gouv.fr (fiche R11637). CETTE date
# est LA source unique — le LISEZMOI l'affiche à l'identique (jamais deux dates qui divergent).
# Doctrine gravée : ne JAMAIS servir un CERFA dont le millésime n'est pas confirmé (dégrader la
# pièce en INDISPONIBLE explicite, cf. pre_dossier_zip). Contrôle réseau automatique ÉCARTÉ (Vic).
CERFA_VERSION = "13406*17"
CERFA_VERIFIE_LE = "21/08/2026"     # date de vérification service-public.gouv.fr — affichée au LISEZMOI
_CERFA_PATH = Path(__file__).resolve().parents[3] / "data" / "cerfa" / "cerfa_13406-17.pdf"
_FONTS = Path(__file__).resolve().parent / "fonts"

LIBELLE = ("Document préparatoire établi à partir de données publiques — ne constitue "
           "pas un dossier de demande de permis. À compléter et vérifier par le "
           "pétitionnaire ou son architecte.")

#: pièces PCMI (bordereau CERFA 13406) — état RÉEL de ce que le pack fournit (M129 E.2/E.3).
#: (code, libellé, état) — l'état dit fournie / partielle / à produire, et déposable ou indicative.
PIECES_PCMI = [
    ("PCMI1", "Plan de situation du terrain",
     "FOURNIE (indicative) — 2 vues (ensemble + rapprochée), Nord + échelle ; format/échelle exacte à confirmer par le porteur."),
    ("PCMI2", "Plan de masse",
     "PARTIELLE (indicative) — état EXISTANT coté fourni ; le PROJET (implantation, cotes de la construction) reste à dessiner par le porteur."),
    ("PCMI3", "Plan en coupe du terrain et de la construction",
     "À PRODUIRE par le porteur (dépend du projet)."),
    ("PCMI4", "Notice décrivant le terrain et le projet",
     "PARTIELLE — partie TERRAIN pré-rédigée (sourcée) ; partie PROJET à compléter par le porteur."),
    ("PCMI5", "Plan des façades et des toitures", "À PRODUIRE par le porteur (dépend du projet)."),
    ("PCMI6", "Document graphique d'insertion", "À PRODUIRE par le porteur (dépend du projet)."),
    ("PCMI7", "Photographie — environnement proche",
     "PARTIELLE — carte des prises de vue RECOMMANDÉES fournie ; la photo reste à réaliser par le porteur."),
    ("PCMI8", "Photographie — paysage lointain",
     "PARTIELLE — carte des prises de vue RECOMMANDÉES fournie ; la photo reste à réaliser par le porteur."),
]


def _commune_de(commune: str) -> str:
    """M129-2 H.1 — « commune de X » avec l'article contracté : Le Tampon → du Tampon, Les Avirons →
    des Avirons ; La/L' (féminin, élidé) → « de La… » / « de L'… » sans contraction."""
    c = (commune or "").strip()
    if c.startswith("Le "):
        return "du " + c[3:]
    if c.startswith("Les "):
        return "des " + c[4:]
    return "de " + c


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
    """Pré-remplit les SEULS champs TERRAIN du cadre 2 : adresse du terrain (BAN, rattachement
    automatique à vérifier) et références cadastrales (préfixe, section, numéro) + la commune.
    La SUPERFICIE n'est PAS remplie (M129 §1 : contenance à relever par le déposant). Aucun champ
    d'identité du demandeur, aucune donnée de projet. Chaque page est tamponnée du libellé
    préparatoire."""
    from pypdf import PdfReader, PdfWriter
    if not _CERFA_PATH.exists():
        # M129 §2.2 : millésime non confirmable (fichier absent) → on NE sert PAS un CERFA douteux.
        # La pièce est dégradée en INDISPONIBLE explicite (le reste du pack est généré) ; jamais un
        # formulaire périmé servi en silence, jamais tout le pack cassé par un 503.
        return None
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
        # M129 §1 (arbitrage Vic) : la SUPERFICIE (T2T_superficie, D5T_total) n'est PLUS remplie.
        # Le CERFA fait CERTIFIER la superficie par le déposant ; `ST_Area(geom)` n'est pas la
        # contenance cadastrale officielle — un champ faux est pire qu'un champ vide. La contenance
        # doit être relevée par le pétitionnaire (relevé de propriété / cadastre.gouv.fr) ; cf.
        # LISEZMOI. Dette : persister le champ `contenance` de la source Etalab (cadastre_bulk.py:54)
        # relève d'un mandat ingestion + migration séparé (consigné qa/m129/).
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
h1 {{ font-size: 15pt; color: #111814; border-bottom: 1.4pt solid #1E9E58;
     padding-bottom: 2mm; }}
h2 {{ font-size: 11.5pt; color: #111814; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ border-bottom: 0.5pt solid #D8E2DC; padding: 1.6mm 2mm 1.6mm 0;
         text-align: left; font-size: 9pt; vertical-align: top; }}
th {{ color: #5F6C65; text-transform: uppercase; font-size: 7pt;
     border-bottom: 0.8pt solid #1E9E58; }}
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
        # M129-2 A/A.3 : hauteur du PLU CALIBRÉ (source unique collect_report_data → resolve_zone),
        # égout et faîtage nommés distinctement ; plus de « hauteur max » générique (9 m). D : plus de
        # « Confiance du calibrage » (indice interne) sur un exportable.
        if r.get("hauteur_egout_m"):
            regles += f"<tr><td>Hauteur d'égout (PLU calibré)</td><td>{r['hauteur_egout_m']:g} m</td></tr>"
        if r.get("hauteur_faitage_m"):
            regles += f"<tr><td>Hauteur au faîtage (PLU calibré)</td><td>{r['hauteur_faitage_m']:g} m</td></tr>"
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
            + (f"<h2>Règles calibrées LABUSE</h2><table>{regles}</table>"
               f"<p class='note'>Les règles complètes du règlement (retraits, prospects, "
               f"servitudes) peuvent modifier ces valeurs.</p>" if regles else "")
            + (f"<h2>Prescriptions graphiques</h2><ul>{presc}</ul>" if presc else "")
            + f"<h2>Servitudes et périmètres connus</h2><ul>{serv_html}</ul>"
            f"<h2>Pièces à joindre (CERFA {CERFA_VERSION}, maison individuelle)</h2>"
            f"<table><tr><th>Code</th><th>Pièce</th><th>État</th></tr>{pieces}</table>")
    return _html_pdf(body, f"Règles du zonage — parcelle {idu}")


# ─────────────────────────── pièces graphiques fpdf2 (Nord + échelle) ───────────────────────────
# Réutilisent le générateur de plan du premium (plan_ortho → ortho IGN + contour) et son tracé
# Nord + échelle (repris de pdf_premium._bloc_plan) — jamais réécrit, jamais un fournisseur de tuiles
# appelé en direct. Chaque page porte le libellé préparatoire (footer).
_ENCRE = (40, 50, 45)


def _pdf_a4():
    from fpdf import FPDF

    class _Doc(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_fill_color(255, 244, 214)
            self.rect(6, self.h - 12, self.w - 12, 8, style="F")
            self.set_font("inter", size=6.6)
            self.set_text_color(120, 90, 20)
            self.set_xy(8, self.h - 11)
            self.multi_cell(self.w - 16, 2.6, LIBELLE, align="C")

    pdf = _Doc(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("inter", fname=str(_FONTS / "Inter-Regular.ttf"))
    pdf.add_font("mono", fname=str(_FONTS / "JetBrainsMono-Regular.ttf"))
    pdf.add_font("display", fname=str(_FONTS / "SpaceGrotesk-Bold.ttf"))
    return pdf


def _nord_echelle(pdf, y0: float, disp_w: float, disp_h: float, plan: dict) -> None:
    """Barre d'échelle (bas-gauche, valeur ronde) + flèche Nord (haut-droite) — repris de premium."""
    mm_par_srcpx = disp_w / plan["width"]
    mpp = plan.get("metres_par_px")
    if mpp:
        m_par_mm = mpp / mm_par_srcpx
        cible_m = 28 * m_par_mm
        p = 10 ** math.floor(math.log10(cible_m)) if cible_m > 0 else 1
        nice = next((f * p for f in (5, 2, 1) if f * p <= cible_m), p)
        bar_mm = nice / m_par_mm
        bx, by = 18, y0 + disp_h - 6
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(bx - 2, by - 3.4, bar_mm + 4, 6.4, style="F")
        pdf.set_draw_color(*_ENCRE)
        pdf.set_line_width(0.5)
        pdf.line(bx, by, bx + bar_mm, by)
        pdf.line(bx, by - 1.2, bx, by + 1.2)
        pdf.line(bx + bar_mm, by - 1.2, bx + bar_mm, by + 1.2)
        pdf.set_font("mono", size=6)
        pdf.set_text_color(*_ENCRE)
        pdf.set_xy(bx, by - 3.4)
        pdf.cell(bar_mm, 2.2, f"{round(nice)} m", align="C")
        pdf.set_line_width(0.2)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(pdf.w - 22, y0 + 2, 6, 8, style="F")
    pdf.set_font("mono", size=7)
    pdf.set_text_color(*_ENCRE)
    pdf.set_xy(pdf.w - 22, y0 + 2.2)
    pdf.cell(6, 3.4, "N", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(pdf.w - 22, y0 + 5.4)
    pdf.cell(6, 3.4, "^", align="C")


def _nord_echelle_mm(pdf, ox: float, oy: float, draw_w: float, draw_h: float, mm_par_m: float) -> None:
    """Barre d'échelle + Nord pour un DESSIN VECTORIEL (échelle mm/m connue) — plan de masse PCMI2."""
    cible_m = 28 / mm_par_m
    p = 10 ** math.floor(math.log10(cible_m)) if cible_m > 0 else 1
    nice = next((f * p for f in (5, 2, 1) if f * p <= cible_m), p)
    bar_mm = nice * mm_par_m
    bx, by = ox, oy + draw_h + 10
    pdf.set_draw_color(*_ENCRE)
    pdf.set_line_width(0.5)
    pdf.line(bx, by, bx + bar_mm, by)
    pdf.line(bx, by - 1.2, bx, by + 1.2)
    pdf.line(bx + bar_mm, by - 1.2, bx + bar_mm, by + 1.2)
    pdf.set_font("mono", size=6.5)
    pdf.set_text_color(*_ENCRE)
    pdf.set_xy(bx, by - 3.6)
    pdf.cell(bar_mm, 2.4, f"{round(nice)} m", align="C")
    pdf.set_line_width(0.2)
    pdf.set_font("mono", size=8)
    pdf.set_xy(ox + draw_w - 4, oy - 1)
    pdf.cell(6, 3.4, "N", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(ox + draw_w - 4, oy + 2.2)
    pdf.cell(6, 3.4, "^", align="C")


def _carte_page(pdf, titre: str, sous_titre: str, plan: dict, note: str,
                cotes=None) -> None:
    """Une page : titre + sous-titre + carte (ortho + contour) + Nord + échelle + note de source.
    `cotes(pdf, x0, y0, scale)` : rappel optionnel pour tracer des cotes sur la carte (PCMI2)."""
    pdf.add_page()
    pdf.set_font("display", size=13)
    pdf.set_text_color(17, 24, 20)
    pdf.set_x(14)
    pdf.cell(0, 7, titre, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=9)
    pdf.set_text_color(95, 108, 101)
    pdf.set_x(14)
    pdf.multi_cell(pdf.w - 28, 4, sous_titre, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    disp_w = pdf.w - 28
    if plan.get("ok"):
        disp_h = disp_w * (plan["height"] / plan["width"])
        y0 = pdf.get_y()
        pdf.image(io.BytesIO(plan["jpeg"]), x=14, y=y0, w=disp_w, h=disp_h)
        if cotes:
            cotes(pdf, 14, y0, disp_w / plan["width"])
        _nord_echelle(pdf, y0, disp_w, disp_h, plan)
        pdf.set_y(y0 + disp_h + 1.5)
        pdf.set_font("inter", size=7)
        pdf.set_text_color(120, 130, 124)
        pdf.set_x(14)
        pdf.multi_cell(pdf.w - 28, 3.2,
                       f"Fond : {plan.get('attribution') or 'IGN — BD ORTHO'}. {note}",
                       new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("inter", size=8)
        pdf.set_text_color(150, 90, 40)
        pdf.set_x(14)
        pdf.multi_cell(pdf.w - 28, 4,
                       f"Carte indisponible — {plan.get('echec', 'raison inconnue')}. "
                       "Le pétitionnaire fournira cette vue.", new_x="LMARGIN", new_y="NEXT")


def _tiles_dir():
    from ..flash.report import storage_dir
    return storage_dir() / "tiles"


def _bati_geojson(db: Session, idu: str) -> str | None:
    """Emprise du bâti existant (BD TOPO, spatial_layers kind='batiment') intersectant la parcelle,
    en GeoJSON WGS84 — pour le plan de masse de l'existant (PCMI2)."""
    row = db.execute(text(
        """SELECT ST_AsGeoJSON(ST_Transform(ST_Union(sl.geom_2975), 4326), 7) AS gj
           FROM spatial_layers sl JOIN parcels p ON ST_Intersects(sl.geom_2975, p.geom_2975)
           WHERE sl.kind = 'batiment' AND p.idu = :idu"""), {"idu": idu}).scalar()
    return row


def _terrain_dims(db: Session, idu: str) -> dict:
    """Enveloppe rectangulaire du terrain (bbox, mètres vrais 2975), surface réelle, et emprise
    bâtie DANS la parcelle. M129-2 E : l'emprise est CLIPPÉE à la parcelle (ST_Intersection) — seule
    la surface bâtie DANS le terrain a un sens sur un plan de masse (jamais l'emprise totale d'un
    bâtiment qui déborde). F : la bbox est une ENVELOPPE, pas la surface (terrain non rectangulaire)."""
    r = db.execute(text(
        """SELECT round((ST_XMax(geom_2975) - ST_XMin(geom_2975))::numeric) AS larg,
                  round((ST_YMax(geom_2975) - ST_YMin(geom_2975))::numeric) AS prof,
                  round(ST_Area(geom_2975)::numeric) AS surface
           FROM parcels WHERE idu = :idu"""), {"idu": idu}).mappings().first() or {}
    emp = db.execute(text(
        """SELECT round(coalesce(sum(ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975))), 0)) AS emprise
           FROM spatial_layers sl JOIN parcels p ON ST_Intersects(sl.geom_2975, p.geom_2975)
           WHERE sl.kind = 'batiment' AND p.idu = :idu"""), {"idu": idu}).scalar()
    _int = lambda v: int(v) if v is not None else None    # noqa: E731 — cast Decimal → int
    return {"largeur_m": _int(r.get("larg")), "profondeur_m": _int(r.get("prof")),
            "surface_m2": _int(r.get("surface")), "emprise_batie_m2": _int(emp)}


def _pcmi1(parcelle: dict) -> bytes:
    """A (PCMI1) — plan de situation aux normes : DEUX vues (ensemble + rapprochée), Nord + échelle."""
    from .plan_situation import plan_ortho
    cd = _tiles_dir()
    gj = parcelle["geojson"]
    ens = plan_ortho(gj, cd, zoom_delta=-3)
    rap = plan_ortho(gj, cd, zoom_delta=0)
    pdf = _pdf_a4()
    ref = f"{parcelle['commune']} · section {parcelle['section']} n° {parcelle['numero']}"
    _carte_page(pdf, "PCMI1 — Plan de situation du terrain",
                f"Vue d'ensemble — situer la parcelle dans la commune. {ref}.", ens,
                "Contour parcellaire (cadastre) sur orthophotographie. Vue indicative — "
                "l'échelle graphique fait foi, à confirmer par le pétitionnaire.")
    _carte_page(pdf, "PCMI1 — Plan de situation du terrain",
                f"Vue rapprochée — situer la parcelle dans le quartier. {ref}.", rap,
                "Contour parcellaire (cadastre) sur orthophotographie. Échelle graphique et Nord "
                "présents ; à confirmer par le pétitionnaire.")
    return bytes(pdf.output())


def _rings_2975(gj_str: str | None) -> list[list[tuple[float, float]]]:
    """Anneaux extérieurs (x, y en mètres 2975) d'un GeoJSON Polygon/MultiPolygon."""
    if not gj_str:
        return []
    import json
    g = json.loads(gj_str)
    t = g.get("type")
    coords = g.get("coordinates") or []
    if t == "Polygon":
        return [[(float(x), float(y)) for x, y in coords[0]]] if coords else []
    if t == "MultiPolygon":
        return [[(float(x), float(y)) for x, y in poly[0]] for poly in coords if poly]
    return []


def _pcmi2(db: Session, parcelle: dict) -> bytes:
    """B (PCMI2) — plan de masse de l'ÉTAT EXISTANT, coté. M129-2 C : DESSIN VECTORIEL (contour
    cadastral + bâti) à une ÉCHELLE du domaine plan de masse (1/200–1/500), qui remplit la feuille —
    l'ortho plafonne à z18 (flou au recadrage serré). Cotes lisibles, Nord + barre d'échelle. La
    partie PROJET reste vide : c'est au pétitionnaire de la dessiner."""
    idu = parcelle["idu"]
    dims = _terrain_dims(db, idu)
    pgj = db.execute(text("SELECT ST_AsGeoJSON(geom_2975, 2) FROM parcels WHERE idu = :i"),
                     {"i": idu}).scalar()
    bgj = db.execute(text(
        """SELECT ST_AsGeoJSON(ST_Union(ST_Intersection(sl.geom_2975, p.geom_2975)), 2)
           FROM spatial_layers sl JOIN parcels p ON ST_Intersects(sl.geom_2975, p.geom_2975)
           WHERE sl.kind = 'batiment' AND p.idu = :i"""), {"i": idu}).scalar()
    pr = _rings_2975(pgj)
    br = _rings_2975(bgj)
    pdf = _pdf_a4()
    pdf.add_page()
    pdf.set_font("display", size=13)
    pdf.set_text_color(17, 24, 20)
    pdf.set_x(14)
    pdf.cell(0, 7, "PCMI2 — Plan de masse (état existant, indicatif)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("inter", size=9)
    pdf.set_text_color(95, 108, 101)
    pdf.set_x(14)
    pdf.multi_cell(pdf.w - 28, 4, f"État EXISTANT : contour cadastral + bâti existant (BD TOPO). "
                   f"Commune {_commune_de(parcelle['commune'])} · section {parcelle['section']} "
                   f"n° {parcelle['numero']}.", new_x="LMARGIN", new_y="NEXT")
    if pr:
        pts = [q for r in pr for q in r]
        minx, maxx = min(x for x, _ in pts), max(x for x, _ in pts)
        miny, maxy = min(y for _, y in pts), max(y for _, y in pts)
        w_m, h_m = max(1.0, maxx - minx), max(1.0, maxy - miny)
        y_top = pdf.get_y() + 3
        avail_w, avail_h = pdf.w - 40, pdf.h - y_top - 60      # marge pour cotes + bloc texte
        # échelle : mm/m au plus proche palier normalisé (1/500=2, 1/250=4, 1/200=5, 1/100=10 mm/m)
        fit = min(avail_w / w_m, avail_h / h_m) * 0.92
        mm_par_m = next((s for s in (10, 5, 4, 2, 1) if s <= fit), 1)
        denom = round(1000 / mm_par_m)
        draw_w, draw_h = w_m * mm_par_m, h_m * mm_par_m
        ox = 20 + max(0, (avail_w - draw_w) / 2)
        oy = y_top + 4

        def _P(x, y):                                          # mètres 2975 → mm page (Nord en haut)
            return ox + (x - minx) * mm_par_m, oy + (maxy - y) * mm_par_m
        # bâti (aplat gris) SOUS le contour
        pdf.set_fill_color(150, 158, 152)
        pdf.set_draw_color(90, 98, 92)
        pdf.set_line_width(0.2)
        for r in br:
            pdf.polygon([_P(x, y) for x, y in r], style="DF")
        # contour parcellaire (mint épais)
        pdf.set_draw_color(30, 158, 88)
        pdf.set_line_width(0.8)
        for r in pr:
            pts_mm = [_P(x, y) for x, y in r]
            pdf.polygon(pts_mm, style="D")
        # cotes hors-tout (largeur sous, profondeur à gauche) — lisibles, hors du bâti
        pdf.set_draw_color(*_ENCRE)
        pdf.set_line_width(0.3)
        x1, x2 = ox, ox + draw_w
        yb = oy + draw_h
        pdf.line(x1, yb + 3, x2, yb + 3)
        pdf.line(x1 - 3, oy, x1 - 3, yb)
        pdf.set_font("mono", size=7)
        pdf.set_text_color(*_ENCRE)
        pdf.set_xy(x1, yb + 3.4)
        pdf.cell(draw_w, 3, f"{int(round(w_m))} m", align="C")
        # barre d'échelle + Nord + mention d'échelle (sous la barre, sans chevauchement)
        _nord_echelle_mm(pdf, ox, oy, draw_w, draw_h, mm_par_m)
        pdf.set_xy(20, oy + draw_h + 16)
        pdf.set_font("inter", size=7.5)
        pdf.set_text_color(95, 108, 101)
        pdf.cell(0, 4, f"Échelle ~1/{denom} (contour cadastral 2975). Bâti existant en gris (BD TOPO).",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(oy + draw_h + 22)
    else:
        pdf.set_font("inter", size=8)
        pdf.set_text_color(150, 90, 40)
        pdf.set_x(14)
        pdf.multi_cell(pdf.w - 28, 4, "Contour cadastral indisponible — plan de masse non traçable.",
                       new_x="LMARGIN", new_y="NEXT")
    # ce que la pièce EST / n'est PAS
    pdf.ln(2)
    pdf.set_font("inter", size=8.5)
    pdf.set_text_color(40, 50, 45)
    pdf.set_x(14)
    d = dims
    # M129-2 F : la bbox est une ENVELOPPE rectangulaire — dite comme telle, avec la surface RÉELLE
    # du terrain (non rectangulaire). M129-2 E : emprise bâtie CLIPPÉE à la parcelle.
    faits = (f"Enveloppe rectangulaire du terrain (le terrain n'est pas rectangulaire) : "
             f"~{int(d['largeur_m'])} × ~{int(d['profondeur_m'])} m"
             + (f" ; surface réelle ~{int(d['surface_m2'])} m². " if d.get("surface_m2") else ". ")
             if d.get("largeur_m") and d.get("profondeur_m") else "")
    emp = (f"Emprise bâtie existante DANS la parcelle : ~{int(d['emprise_batie_m2'])} m² (BD TOPO). "
           if d.get("emprise_batie_m2") else "")
    pdf.multi_cell(pdf.w - 28, 4.2,
                   f"{faits}{emp}\n\nCE QUE CETTE PIÈCE EST : l'état EXISTANT du terrain (contour "
                   "cadastral et bâti relevé). CE QU'ELLE N'EST PAS : le plan de masse du PROJET "
                   "(implantation, cotes de la construction projetée, reculs, réseaux raccordés) — "
                   "à dessiner par le pétitionnaire ou son architecte.", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _pcmi4(db: Session, idu: str, parcelle: dict) -> bytes:
    """C (PCMI4) — notice décrivant le TERRAIN, pré-rédigée (partie projet laissée vide).
    Chaque affirmation porte sa source ; aucun verdict, aucune appréciation (doctrine)."""
    from ..flash.data import collect_report_data
    data = collect_report_data(db, idu)
    ident = data.get("identite") or {}
    terr = data.get("terrain") or {}
    lignes = []
    zone = (ident.get("zones") or [{}])[0]
    if zone.get("libelle") or zone.get("classe"):
        lignes.append(("Situation et zonage",
                       f"Parcelle {idu}, commune {_commune_de(parcelle['commune'])}, section "
                       f"{parcelle['section']} n° {parcelle['numero']}. Zone du document d'urbanisme : "
                       f"{zone.get('libelle') or zone.get('classe')}.", "cadastre · PLU (GPU)"))
    pente = terr.get("pente") or {}
    if pente.get("moy_deg") is not None:
        lignes.append(("Topographie",
                       f"Pente moyenne du terrain d'environ {pente.get('moy_pct', '?')} % "
                       f"({pente['moy_deg']}°).", "RGE ALTI 5 m (IGN)"))
    if terr.get("canopee") and terr["canopee"].get("ombrage_pct") is not None:
        lignes.append(("Végétation",
                       f"Couvert arboré estimé à ~{terr['canopee']['ombrage_pct']} % de la parcelle.",
                       "détection canopée (ortho)"))
    dims = _terrain_dims(db, idu)
    if dims.get("emprise_batie_m2"):
        lignes.append(("Bâti existant",
                       f"Emprise bâtie existante estimée à ~{int(dims['emprise_batie_m2'])} m² (au sol).",
                       "BD TOPO (IGN)"))
    via = terr.get("viabilisation") or {}
    if via.get("libelle"):
        preuves = " ; ".join(pr["libelle"] for pr in (via.get("preuves") or [])[:3])
        lignes.append(("Accès et réseaux",
                       f"{via['libelle']}." + (f" Indices : {preuves}." if preuves else ""),
                       "viabilisation LABUSE (voirie, bâti, permis, assainissement)"))
    anc = terr.get("anc") or {}
    if anc.get("libelle"):
        # M129-2 B : la SOURCE réellement interrogée (souvent INSEE RP2022 EGOUL par IRIS, le zonage
        # assainissement étant NON DISPONIBLE sur ces communes), et la PHRASE qui porte le garde-fou
        # « taux de SECTEUR, pas la parcelle — à vérifier auprès du SPANC » (jamais un constat parcelle).
        lignes.append(("Assainissement",
                       anc.get("phrase") or f"{anc['libelle']}.",
                       anc.get("source") or "assainissement (LABUSE)"))
    rows = "".join(
        f"<tr><td style='width:26%'><b>{titre}</b></td><td>{txt}<div class='src'>Source : {src}</div></td></tr>"
        for titre, txt, src in lignes) or "<tr><td colspan='2'>Données terrain non disponibles.</td></tr>"
    projet = "".join(f"<tr><td><b>{t}</b></td><td class='vide'>À compléter par le pétitionnaire.</td></tr>"
                     for t in ("Présentation du projet", "Matériaux et couleurs des façades",
                               "Traitement des toitures", "Clôtures et abords",
                               "Insertion paysagère", "Stationnement"))
    css_add = " .src{color:#8A9691;font-size:7pt;margin-top:1mm} .vide{color:#9AA89E;font-style:italic}"
    body = (f"<style>{css_add}</style>"
            f"<h2>1 — Le terrain (pré-rédigé à partir de données publiques)</h2>"
            f"<table>{rows}</table>"
            f"<h2>2 — Le projet (à compléter par le pétitionnaire)</h2>"
            f"<table>{projet}</table>"
            f"<p class='note'>Partie terrain établie à partir de données publiques, chaque ligne "
            f"sourcée ; à vérifier sur place. La partie projet relève exclusivement du pétitionnaire "
            f"et de son architecte.</p>")
    return _html_pdf(body, "PCMI4 — Notice décrivant le terrain")


def _points_de_vue(db: Session, idu: str, rayon_m: float = 70.0, n_max: int = 4) -> list[tuple]:
    """M129-2 G — positions de prise de vue ACCESSIBLES : points sur la VOIRIE publique proche
    (spatial_layers kind='voirie', le point le plus proche de chaque tronçon voisin), donc jamais sur
    du bâti. Renvoie [(lon, lat), …] triés par proximité ; vide si aucune voirie dans le rayon."""
    rows = db.execute(text(
        """WITH p AS (SELECT geom_2975 g, ST_Centroid(geom_2975) c FROM parcels WHERE idu = :idu)
           SELECT ST_X(ST_Transform(pt, 4326)) AS lon, ST_Y(ST_Transform(pt, 4326)) AS lat
           FROM (SELECT ST_ClosestPoint(sl.geom_2975, (SELECT c FROM p)) AS pt,
                        ST_Distance(sl.geom_2975, (SELECT c FROM p)) AS d
                 FROM spatial_layers sl, p
                 WHERE sl.kind = 'voirie' AND ST_DWithin(sl.geom_2975, p.g, :r)
                 ORDER BY d LIMIT :n) q"""),
        {"idu": idu, "r": rayon_m, "n": n_max}).mappings().all()
    return [(r["lon"], r["lat"]) for r in rows]


def _pcmi78(db: Session, parcelle: dict) -> bytes:
    """D (PCMI7/8) — carte des prises de vue RECOMMANDÉES (proche + lointain), Nord + échelle.
    M129-2 G : positions ACCESSIBLES (sur voirie publique, jamais sur du bâti) ; si aucune, le dit."""
    from .plan_situation import plan_ortho
    cd = _tiles_dir()
    gj = parcelle["geojson"]
    idu = parcelle["idu"]
    # centroïde parcelle en lon/lat (pour projeter les points de vue dans le repère image)
    c = db.execute(text("SELECT ST_X(ST_Transform(ST_Centroid(geom_2975),4326)) lon, "
                        "ST_Y(ST_Transform(ST_Centroid(geom_2975),4326)) lat FROM parcels WHERE idu=:i"),
                   {"i": idu}).mappings().first() or {}
    lon0, lat0 = c.get("lon"), c.get("lat")
    vues = _points_de_vue(db, idu)

    def _draw(pdf, x0, y0, scale, plan):
        rings = plan.get("parcel_px") or []
        if not rings or lon0 is None:
            return
        mpp = plan.get("metres_par_px") or 0.5
        xs = [px for r in rings for px, _ in r]
        ys = [py for r in rings for _, py in r]
        cx, cy = (min(xs) + max(xs)) / 2 * scale + x0, (min(ys) + max(ys)) / 2 * scale + y0
        if not vues:
            pdf.set_font("inter", size=7.5)
            pdf.set_text_color(150, 90, 40)
            pdf.set_xy(x0 + 4, y0 + 4)
            pdf.cell(0, 4, "Aucune position accessible identifiée à proximité (pas de voirie publique "
                     "relevée) — le pétitionnaire choisit ses prises de vue depuis la voie publique.")
            return
        for i, (lon, lat) in enumerate(vues, 1):
            dxm = (lon - lon0) * 111320.0 * math.cos(math.radians(lat0))
            dym = (lat - lat0) * 110540.0
            px, py = cx + (dxm / mpp) * scale, cy - (dym / mpp) * scale
            pdf.set_draw_color(*_ENCRE)
            pdf.set_line_width(0.4)
            pdf.line(px, py, cx, cy)                       # visée vers la parcelle
            pdf.set_fill_color(74, 222, 128)
            pdf.ellipse(px - 3.4, py - 3.4, 6.8, 6.8, style="DF")
            pdf.set_font("display", size=8)
            pdf.set_text_color(17, 24, 20)
            pdf.set_xy(px - 3.4, py - 2.4)
            pdf.cell(6.8, 4, str(i), align="C")            # numéro lisible dans la pastille

    prox = plan_ortho(gj, cd, zoom_delta=0, crop_margin_m=80.0)   # proche : parcelle + voirie visées
    loin = plan_ortho(gj, cd, zoom_delta=-2)                      # lointain : paysage large
    n = len(vues)
    sous = (f"Points 1 à {n} sur la voirie publique proche (accessibles), face à la parcelle."
            if n else "Aucune position accessible relevée à proximité (voir la carte).")
    pdf = _pdf_a4()
    _carte_page(pdf, "PCMI7 — Prises de vue recommandées (environnement proche)", sous, prox,
                "Positions RECOMMANDÉES (pas une prescription), placées sur la voirie publique — le "
                "pétitionnaire ajuste selon l'accès réel et la végétation.",
                cotes=lambda p, x, y, s: _draw(p, x, y, s, prox))
    _carte_page(pdf, "PCMI8 — Prises de vue recommandées (paysage lointain)",
                "Mêmes points, vus dans le paysage lointain.", loin,
                "Positions RECOMMANDÉES (pas une prescription).",
                cotes=lambda p, x, y, s: _draw(p, x, y, s, loin))
    return bytes(pdf.output())


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

    # M-K : porte de quota M23-E — le pré-dossier ZIP est l'export le PLUS lourd (weasyprint +
    # CERFA + plans ortho). Il manquait la porte que dossier.pdf a déjà ; on la pose par cohérence,
    # APRÈS le 404 (jamais de quota consommé pour une parcelle inconnue).
    from ..quota import porte_export
    porte_export(request, db)

    parcelle = dict(p)
    # M129 E — nommage aligné sur la doctrine {IDU}-labuse (pack multi-pièces : préfixe commun +
    # suffixe de pièce explicite). Le ZIP lui-même : {IDU}-labuse-predossier-pc.zip.
    pfx = f"{idu}-labuse"
    cerfa = _cerfa_prerempli(parcelle, dict(adresse) if adresse else None)   # None si INDISPONIBLE
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if cerfa is not None:
            z.writestr(f"{pfx}-CERFA-{CERFA_VERSION.replace('*', '-')}-prerempli.pdf", cerfa)
        for nom, gen in (
            (f"{pfx}-PCMI1-plan-situation.pdf", lambda: _pcmi1(parcelle)),
            (f"{pfx}-PCMI2-plan-masse-existant.pdf", lambda: _pcmi2(db, parcelle)),
            (f"{pfx}-PCMI4-notice-terrain.pdf", lambda: _pcmi4(db, idu, parcelle)),
            (f"{pfx}-PCMI7-8-prises-de-vue.pdf", lambda: _pcmi78(db, parcelle)),
            (f"{pfx}-regles-zonage.pdf", lambda: _regles_et_pieces(db, idu)),
        ):
            try:
                z.writestr(nom, gen())
            except Exception as exc:  # noqa: BLE001 — une pièce en échec ne casse jamais le pack
                log.warning("pré-dossier %s : pièce %s en échec (%s)", idu, nom, exc)
        z.writestr(zipfile.ZipInfo(f"{pfx}-LISEZMOI.txt"),
                   _lisezmoi(idu, parcelle["commune"], adresse is not None, cerfa is not None),
                   compress_type=zipfile.ZIP_STORED)   # non compressé : libellé vérifiable tel quel
    log.info("pré-dossier PC %s généré", idu)
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{pfx}-predossier-pc.zip"'})


def _lisezmoi(idu: str, commune: str, adresse_ok: bool, cerfa_ok: bool) -> str:
    """M129 E — LISEZMOI fusionné : libellé préparatoire, millésime CERFA daté (§2), superficie non
    servie (§1), qualification adresse BAN (§3), checklist PCMI cohérente avec le pack réel, nommage."""
    cerfa_ligne = (f"CERFA {CERFA_VERSION} — version vérifiée le {CERFA_VERIFIE_LE} sur "
                   "service-public.gouv.fr (fiche R11637). Seuls les champs TERRAIN du cadre 2 sont "
                   "pré-remplis (adresse du terrain + références cadastrales préfixe/section/numéro + "
                   "commune)."
                   if cerfa_ok else
                   f"CERFA {CERFA_VERSION} — INDISPONIBLE dans ce pack (formulaire non confirmable). "
                   "À télécharger sur service-public.gouv.fr (fiche R11637).")
    adr = ("L'adresse du terrain provient d'un rattachement automatique (BAN) — à VÉRIFIER par le "
           "porteur, en particulier sur une parcelle nue (elle peut désigner une adresse voisine)."
           if adresse_ok else "Aucune adresse BAN rattachée — à renseigner par le porteur.")
    check = "\n".join(f"  [{('X' if e.startswith(('FOURNIE', 'PARTIELLE')) else ' ')}] {c} — {lib} : {e}"
                      for c, lib, e in PIECES_PCMI)
    return (
        f"PRÉ-DOSSIER PERMIS DE CONSTRUIRE (maison individuelle) — parcelle {idu} ({commune})\n"
        f"{'=' * 78}\n\n"
        f"{LIBELLE}\n\n"
        f"CERFA\n-----\n{cerfa_ligne}\n"
        f"Doctrine : LABUSE ne sert jamais un CERFA dont le millésime n'est pas confirmé.\n\n"
        f"SUPERFICIE (non servie — arbitrage)\n-----------------------------------\n"
        f"La superficie du terrain n'est PAS pré-remplie : le CERFA fait CERTIFIER cette valeur par le\n"
        f"déposant, et l'aire géométrique calculée par LABUSE n'est pas la contenance cadastrale\n"
        f"officielle. Relevez la contenance sur votre relevé de propriété ou sur cadastre.gouv.fr.\n\n"
        f"ADRESSE DU TERRAIN\n------------------\n{adr}\n\n"
        f"CHECKLIST DES PIÈCES (PCMI1 à PCMI8) — état RÉEL de ce pack\n"
        f"{'-' * 58}\n{check}\n\n"
        f"[X] = fournie ou partielle dans ce pack · [ ] = à produire par le porteur.\n"
        f"Les pièces fournies sont INDICATIVES (à confirmer par le porteur ou son architecte) ; "
        f"aucune n'est garantie déposable en l'état.\n\n"
        f"PIÈCE D'INFORMATION (hors bordereau PCMI)\n----------------------------------------\n"
        f"  [X] Règles du zonage — fiche récapitulative (zonage, hauteurs PLU calibrées, servitudes "
        f"connues) : {idu}-labuse-regles-zonage.pdf. Aide à la préparation, pas une pièce du dossier.\n\n"
        f"NOMMAGE\n-------\nToutes les pièces suivent la doctrine {{IDU}}-labuse : « {idu}-labuse-<pièce>.pdf ».\n")
