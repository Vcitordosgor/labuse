"""M22-0 — BRIQUES PDF PARTAGÉES · M22-F — UNE SEULE IDENTITÉ VISUELLE (DA Flash).

Sections extraites du Dossier banquier (O1) et partagées par les exports M22 (lettre de
zonage, argumentaire, rapport de potentiel). Depuis M22-F, les briques portent l'identité
IMPRESSION LABUSE du Flash (C2) : wordmark + silhouette, Space Grotesk / Inter /
JetBrains Mono (OFL, api/fonts), palette menthe print, cartouches — et le BANDEAU DE
CONTEXTE du Flash sur CHAQUE page (C7 : « LABUSE — produit · IDU — commune », aucune
page orpheline à l'impression ; la page de garde porte le wordmark graphique à la place).

Contenu :
 · `page_css(...)` — DA print A4, bandeau running, pied légal ;
 · helpers `s` (puce Sourcé/Estimé/Absent), `eur`, `esc` ;
 · `wordmark_html`, `garde_entete` — la marque + le chapeau de couverture (partagé) ;
 · `cartouche` / `cartouches` — les KPI du Flash, variante `hero=True` (C6 : le chiffre
   principal se voit à 2 mètres) ;
 · `hypotheses_encadre` — C1 : l'encadré « Hypothèses de calcul », IDENTIQUE en forme
   dans tous les documents qui chiffrent (Banquier, Argumentaire) ;
 · `collect(db, idu)` — assemblage des données (bilan sur les DÉFAUTS UNIQUES
   `bilan_params_defaut()` : mêmes totaux que la calculette, C1) ;
 · `map_html` — plan de situation, PLAN CADASTRAL CLAIR partout (C2) ;
 · sections : `cover`, `identite`, `faisabilite`, `bilan`, `comparables`, `risques` ;
 · `render_pdf(sections, libelle, produit=…, idu=…, commune=…)` — HTML → WeasyPrint.

Doctrine (inchangée) : jamais un RR ni un score interne en vitrine ; chaque chiffre porte
Sourcé/Estimé ; « non estimable » quand une donnée manque ; particulier jamais nommé.
"""
from __future__ import annotations

import html
import logging
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.briques_pdf")

_FONTS = Path(__file__).resolve().parent / "fonts"

# ── DA IMPRESSION LABUSE (portée du Flash, C2) — placeholders {fonts}/{produit_ctx}/
#    {date_edition}/{libelle} ; accolades CSS doublées. ─────────────────────────────────
PAGE_CSS = """
@font-face {{ font-family: "Inter"; src: url("{fonts}/Inter-Regular.ttf"); }}
@font-face {{ font-family: "JetBrains Mono"; src: url("{fonts}/JetBrainsMono-Regular.ttf"); }}
@font-face {{ font-family: "Space Grotesk"; font-weight: 700;
             src: url("{fonts}/SpaceGrotesk-Bold.ttf"); }}
@page {{
  size: A4; margin: 22mm 16mm 20mm 16mm;
  @top-left {{
    content: "{produit_ctx}";
    font-family: "JetBrains Mono", monospace; font-size: 7pt; color: #8C9891;
    border-bottom: 0.6pt solid #1E9E58; width: 100%; padding-bottom: 4pt;
    margin-bottom: 8pt; vertical-align: bottom;
  }}
  @top-right {{
    content: "{date_edition}";
    font-family: "JetBrains Mono", monospace; font-size: 7pt; color: #8C9891;
    border-bottom: 0.6pt solid #1E9E58; vertical-align: bottom;
    padding-bottom: 4pt; margin-bottom: 8pt;
  }}
  @bottom-center {{
    content: "{libelle} · p. " counter(page) "/" counter(pages);
    font-family: "Inter"; font-size: 6pt; color: #8C9891;
  }}
}}
@page garde {{ @top-left {{ content: none; }} @top-right {{ content: none; }} }}
.garde {{ page: garde; }}
html {{ font-size: 9.5pt; }}
body {{ font-family: "Inter", sans-serif; color: #28322D; line-height: 1.45; margin: 0; }}
h1, h2, h3 {{ font-family: "Space Grotesk", "Inter", sans-serif; font-weight: 700; color: #111814; }}
h1 {{ font-size: 21pt; margin: 0 0 2mm 0; line-height: 1.2; }}
h2 {{ font-size: 13pt; margin: 7mm 0 3mm 0; padding-bottom: 1.5mm;
     border-bottom: 1.4pt solid #1E9E58; break-after: avoid; }}
h3 {{ font-size: 10pt; margin: 4mm 0 1.5mm 0; break-after: avoid; }}
.marque {{ display: flex; align-items: center; margin-bottom: 8mm; }}
.wordmark {{ font-family: "Space Grotesk"; font-weight: 700; font-size: 16pt;
            color: #1E9E58; letter-spacing: 0.04em; margin-left: 4mm; }}
.produit {{ font-family: "JetBrains Mono", monospace; font-size: 8pt;
           color: #5F6C65; margin-left: 4mm; }}
.refs {{ font-family: "JetBrains Mono", monospace; font-size: 9pt;
        color: #5F6C65; margin-bottom: 5mm; }}
.refs b {{ color: #111814; }}
table {{ width: 100%; border-collapse: collapse; margin: 1mm 0; }}
td, th {{ border-bottom: 0.5pt solid #D8E2DC; padding: 1.6mm 2mm 1.6mm 0; text-align: left;
  font-size: 8.6pt; vertical-align: top; }}
th {{ color: #5F6C65; text-transform: uppercase; font-size: 6.8pt; letter-spacing: 0.3pt;
  border-bottom: 0.8pt solid #1E9E58; font-family: "JetBrains Mono", monospace; }}
td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.note {{ font-size: 7.6pt; color: #5F6C65; }}
.src {{ font-size: 6.6pt; text-transform: uppercase; letter-spacing: 0.3pt; padding: 0.2mm 1.2mm;
  border-radius: 1mm; white-space: nowrap; font-family: "JetBrains Mono", monospace; }}
.src-s {{ background: #E2F7ED; color: #0B6A48; }}   /* Sourcé */
.src-e {{ background: #FFF2D6; color: #7A5A12; }}   /* Estimé */
.src-a {{ background: #EFEFEF; color: #767676; }}   /* Absent / non estimable */
.cartouche {{ background: #F4F8F6; border-radius: 2mm; padding: 3mm 4mm; }}
.cartouche .titre {{ font-family: "JetBrains Mono", monospace; font-size: 7pt;
  color: #5F6C65; text-transform: uppercase; letter-spacing: 0.4pt; display: block; }}
.cartouche .valeur {{ font-family: "Space Grotesk"; font-weight: 700; font-size: 15pt;
  color: #111814; display: block; margin-top: 1mm; }}
.cartouche .valeur small {{ font-size: 8.5pt; color: #5F6C65; font-family: "Inter"; font-weight: 400; }}
.cartouche.hero .valeur {{ font-size: 27pt; color: #1E9E58; }}   /* C6 : lisible à 2 mètres */
.cartouches {{ display: flex; gap: 3mm; margin: 3mm 0; }}
.cartouches .cartouche {{ flex: 1; margin: 0; }}
.exec {{ background: #F4F8F6; border-left: 2.5pt solid #1E9E58; padding: 3mm 4mm;
  border-radius: 0 1.5mm 1.5mm 0; font-size: 9.4pt; }}
.bandeau {{ background: #FFF6DE; border-radius: 1.5mm; padding: 2.5mm 3.5mm; font-size: 7.8pt;
  color: #7A5A12; margin: 2mm 0 4mm; }}
.hyp-encadre {{ background: #F4F8F6; border: 0.8pt solid #D8E2DC; border-radius: 2mm;
  padding: 2.5mm 3.5mm; font-size: 8.2pt; color: #28322D; margin: 2mm 0; }}
.hyp-encadre .titre {{ font-family: "JetBrains Mono", monospace; font-size: 6.8pt;
  color: #5F6C65; text-transform: uppercase; letter-spacing: 0.4pt; display: block;
  margin-bottom: 1mm; }}
.cover-sub {{ color: #5F6C65; font-size: 10.5pt; margin: 0 0 3mm; }}
.map {{ border: 0.8pt solid #D8E2DC; border-radius: 2mm; overflow: hidden; }}
.pb {{ page-break-before: always; }}
"""


def page_css(libelle: str, *, produit: str = "", idu: str = "", commune: str = "") -> str:
    """CSS de page : pied légal + BANDEAU DE CONTEXTE C7 sur chaque page
    (« LABUSE — produit · IDU — commune », même forme que le Flash)."""
    def _c(x: str) -> str:
        return (x or "").replace('"', "'").replace("\\", "")
    ctx = f"LABUSE — {_c(produit)}"
    if idu:
        ctx += f" · {_c(idu)}"
    if commune:
        ctx += f" — {_c(commune)}"
    return PAGE_CSS.format(fonts=_FONTS.as_uri(), produit_ctx=ctx,
                           date_edition=date.today().strftime("%d/%m/%Y"), libelle=_c(libelle))


def s(prov: str) -> str:
    """Puce Sourcé / Estimé / Absent."""
    return {"S": "<span class='src src-s'>Sourcé</span>",
            "E": "<span class='src src-e'>Estimé</span>",
            "A": "<span class='src src-a'>non estimable</span>"}.get(prov, "")


def eur(x) -> str:
    if x is None:
        return "—"
    x = float(x)
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x/1_000_000:.2f} M€".replace(".", ",")
    if ax >= 1_000:
        return f"{x/1_000:.0f} k€"
    return f"{x:.0f} €"


def esc(x) -> str:
    return html.escape(str(x if x is not None else "—"))


# ── marque & chapeau de couverture (C2 : une seule identité) ─────────────────────────────

def wordmark_html(produit_sous_titre: str) -> str:
    """Le bloc marque de la page de garde Flash : silhouette + wordmark + produit."""
    from ..flash.report import _logo_svg_path
    return (f"<div class='marque'>"
            f"<svg width='46' height='13' viewBox='0 0 240 62'>"
            f"<path d='{_logo_svg_path()}' fill='#1E9E58'/></svg>"
            f"<span class='wordmark'>LABUSE</span>"
            f"<span class='produit'>{esc(produit_sous_titre)}</span></div>")


def garde_entete(p: dict, *, produit_sous_titre: str, titre: str, bandeau: str,
                 sous_titre: str | None = None, marque: dict | None = None) -> str:
    """Chapeau de couverture partagé par les 4 briques : marque, H1, référence parcelle
    (ligne mono comme le Flash), bandeau légal. À rendre DANS une section `garde`
    (pas de bandeau running en tête de couverture — même règle que le Flash)."""
    st = f"<div class='cover-sub'>{esc(sous_titre)}</div>" if sous_titre else ""
    # M23-A : bloc marque CLIENT (abonné seulement — le Flash n'atteint jamais ces briques
    # avec une marque) ; wordmark LABUSE inchangé + mention « Généré via LABUSE » dans le bloc.
    from ..marque import bloc_html as _marque_bloc
    return (f"{_marque_bloc(marque)}{wordmark_html(produit_sous_titre)}"
            f"<h1>{esc(titre)}</h1>{st}"
            f"<div class='refs'>Parcelle <b>{esc(p['idu'])}</b> · {esc(p['commune'])} · "
            f"section {esc(p['section'])} n° {esc(p['numero'])}</div>"
            f"<div class='bandeau'>{bandeau}</div>")


def cartouche(titre: str, valeur: str, note: str | None = None, *, hero: bool = False) -> str:
    """Cartouche KPI du Flash. `hero=True` (C6) : le chiffre principal, très grand, menthe."""
    small = f" <small>{esc(note)}</small>" if note else ""
    return (f"<div class='cartouche{' hero' if hero else ''}'>"
            f"<span class='titre'>{esc(titre)}</span>"
            f"<span class='valeur'>{esc(valeur)}{small}</span></div>")


def cartouches(items: list[str]) -> str:
    return f"<div class='cartouches'>{''.join(items)}</div>"


def hypotheses_encadre(cout_m2: float, marge_pct: float, composantes: str | None = None,
                       cout_m2_haut: float | None = None) -> str:
    """C1 — l'encadré « Hypothèses de calcul », IDENTIQUE en forme dans tous les documents
    qui chiffrent. Deux documents aux hypothèses différentes l'affichent chacun — le
    lecteur qui tient les deux comprend d'où vient tout écart.

    M54-AB C4 : `marge_pct` doit être le total RÉELLEMENT déduit par le bilan servi (24 % =
    marge + honoraires + frais financiers du secteur), pas le défaut global agrégé (21 %) —
    sinon l'encadré dit 21 % et la ligne bilan 24 %. `composantes` nomme la décomposition.
    M128-2-F1 : le coût est annoncé en FOURCHETTE (celle réellement utilisée par le bilan,
    ex. 2100–2550 €/m²), jamais une valeur unique qui contredit le CA calculé sur la fourchette."""
    cout_txt = (f"{cout_m2:g}–{cout_m2_haut:g} €/m²"
                if cout_m2_haut and round(cout_m2_haut) != round(cout_m2) else f"{cout_m2:g} €/m²")
    detail = f" (soit {composantes})" if composantes else ""
    return (f"<div class='hyp-encadre'><span class='titre'>Hypothèses de calcul</span>"
            f"Coût de construction <b>{cout_txt}</b> de surface de plancher · "
            f"marge &amp; frais <b>{marge_pct:g} %</b> du chiffre d'affaires{detail} — hypothèses "
            f"à ajuster : LABUSE ne les estime pas. Les valeurs sourcées "
            f"(surface vendable, prix DVF) viennent du moteur.</div>")


# ───────────────────────── assemblage données (réutilise l'existant) ─────────────────────────

def collect(db: Session, idu: str) -> dict:
    """Rassemble toutes les briques du dossier. Chaque section est optionnelle et guardée :
    une donnée absente devient None (la page l'omet proprement), jamais un chiffre inventé.
    C1 : le bilan tourne sur `bilan_params_defaut()` — LES MÊMES hypothèses que la
    calculette et l'argumentaire par défaut → totaux identiques entre documents."""
    row = db.execute(text(
        "SELECT id, idu, commune, section, numero, round(surface_m2) AS surface_m2, "
        "ST_AsGeoJSON(geom, 7) AS geojson FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
    if not row:
        raise HTTPException(404, f"Parcelle {idu} inconnue.")
    pid = row["id"]
    out: dict = {"parcelle": dict(row)}

    # rapport « flash » : identité (zonage, règles calibrées, prescriptions), risques, servitudes
    try:
        from ..flash.data import collect_report_data
        out["rapport"] = collect_report_data(db, idu)
    except Exception as exc:  # noqa: BLE001
        log.warning("collect_report_data %s : %s", idu, exc)
        out["rapport"] = None

    # faisabilité (11 steps déterministes) + bilan promoteur + charge foncière
    try:
        from ..faisabilite.db import parcel_faisabilite
        from ..faisabilite.bilan import sector_price, compute_bilan_servi
        from ..faisabilite.engine import Hypotheses
        fa = parcel_faisabilite(db, pid)
        if fa:
            ctx, fais = fa
            out["faisabilite"] = fais
            shab = (fais.fourchette or {}).get("shab_vendable_m2")
            if shab and shab > 0:
                # M73-B Volet C — le banquier LIT le marché par le point d'appel UNIQUE (profil nommé).
                from .. import marche_service
                out["prix_dvf"] = marche_service.marche_dvf(db, idu, profil=marche_service.DVF_BANQUIER_ADAPTATIF)
                # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — Banquier + Argumentaire servent
                # LE MÊME bilan que la fiche (compute_bilan_servi : charge COHÉRENTE À L'EURO — même
                # capacité, hypothèses résolues, prix de sortie neuf, contexte éco). Non calculable
                # (social-dominant) → dossier SERVI avec la mention, jamais un chiffre de marché.
                b, ps = compute_bilan_servi(db, pid, fa)
                out["bilan"] = b
                if ps is not None:
                    out["bilan_non_calculable"] = bool(ps["non_calculable"])
                    out["prix_neuf_label"] = ps["motif"] if ps["non_calculable"] else ps["label"]
                    out["prix_neuf_repli_ile"] = ps["repli_ile"]
    except Exception as exc:  # noqa: BLE001
        log.warning("faisabilité/bilan %s : %s", idu, exc)

    # Score É V2 (marge € — O0)
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar() is not None:
            out["score_e"] = db.execute(text(
                "SELECT estimable, marge_estimee, charge_supportable, prix_probable, niveau_prix, "
                "libelle_court, detail FROM score_e WHERE idu = :i"), {"i": idu}).mappings().first()
    except Exception:  # noqa: BLE001
        pass

    # permis SITADEL voisins (contexte promoteur) — M73-B Volet C : par le point d'appel UNIQUE.
    try:
        from .. import marche_service
        out["permits"] = marche_service.permits(db, idu, profil=marche_service.PERMITS_FLASH_500M)
    except Exception as exc:  # noqa: BLE001
        log.warning("permits %s : %s", idu, exc)

    # ZAN (consommation ENAF commune) — guardé, feat/zan-enrichi peut être absent
    try:
        insee = idu[:5]
        if db.execute(text("SELECT to_regclass('commune_conso_enaf')")).scalar() is not None:
            out["zan"] = db.execute(text(
                "SELECT insee, commune, conso_2011_2021_m2, conso_2021_2024_m2, source_nom, millesime "
                "FROM commune_conso_enaf WHERE insee = :c LIMIT 1"), {"c": insee}).mappings().first()
    except Exception:  # noqa: BLE001
        pass
    # M54-AB C5 : bloc Marché commune (M-U) condensé — 3 lignes pour le banquier (tendance,
    # liquidité, offre engagée), chacune datée. Consommé, jamais recalculé.
    try:
        from .marche_bloc import bloc_condense
        commune = db.execute(text("SELECT commune FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if commune:
            out["commune_marche"] = bloc_condense(db, commune,
                                                  ["tendance_12m", "liquidite", "offre_engagee"])
    except Exception:  # noqa: BLE001
        pass
    # M128-B6 : le verdict LABUSE (tier/rang/motif) n'est PLUS collecté pour le dossier banquier —
    # aucun classement interne en vitrine (retiré de la couverture, même règle que fiche et dossier).
    # M73-D — assainissement + réhabilitation, via les helpers UNIQUES (jamais recalculés ni lus depuis
    # zone_anc/proba_anc). L'absence est un état (statut_anc renvoie toujours un dict ; compute_mode_b
    # « non disponible »). Rendus par blocs_documents (écrit une fois).
    try:
        from ..anc_service import statut_anc
        out["anc"] = statut_anc(db, idu)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..faisabilite.bilan import compute_mode_b
        out["mode_b"] = compute_mode_b(db, idu)          # run=None → run servi (Q_A_RUN_LABEL)
    except Exception:  # noqa: BLE001
        pass
    return out


# ───────────────────────── sections HTML ─────────────────────────

def map_html(geojson: str, ign: bool = False) -> str:
    """Plan de situation. C2 : LE PLAN CADASTRAL CLAIR partout (le lisible) — le fond
    ortho IGN reste disponible (`ign=True`) mais n'est plus le défaut d'aucune brique."""
    try:
        from ..flash.carte import build_situation_map, IGN_ORTHO_URL, IGN_ORTHO_ATTRIBUTION
        from ..flash.report import storage_dir
        kw = {"tile_url": IGN_ORTHO_URL, "tile_mime": "image/jpeg", "cache_prefix": "ign",
              "attribution": IGN_ORTHO_ATTRIBUTION} if ign else {}
        carte = build_situation_map(geojson, cache_dir=storage_dir() / "tiles", **kw)
    except Exception as exc:  # noqa: BLE001
        log.warning("carte : %s", exc)
        carte = None
    if not carte:
        return "<p class='note'>Fond de carte momentanément indisponible.</p>"
    tiles = "".join(f"<img src='{t['data_uri']}' style='position:absolute;left:{t['left']}px;"
                    f"top:{t['top']}px;width:256px;height:256px;'>" for t in carte["tiles"])
    polys = "".join(f"<polygon points='{p}' fill='rgba(11,138,95,0.16)' stroke='#1E9E58' "
                    f"stroke-width='2.5'/>" for p in carte["polygons"])
    return (f"<div class='map' style='position:relative;width:{carte['width']}px;height:{carte['height']}px;'>"
            f"{tiles}<svg width='{carte['width']}' height='{carte['height']}' "
            f"style='position:absolute;left:0;top:0;'>{polys}</svg></div>"
            f"<p class='note'>{esc(carte['attribution'])}</p>")


def score_e_affiche(out: dict) -> dict | None:
    """M54-AB C3 — POINT DE CALCUL UNIQUE de la charge foncière DANS le dossier banquier.

    Le Score É (table précalculée `score_e`) déduit 21 % du CA (× 0.79) ; le bilan à rebours
    SERVI en déduit 24 % (hypothèses de la commune, honoraires calibrés) → deux « charges »
    (71 vs 69 k€) sur le même document. On SERT la charge du bilan à rebours partout ; la marge
    en découle (charge − prix probable du foncier). Le prix probable du foncier reste la donnée
    Score É (médiane terrain sectorielle × surface), non recalculée ici."""
    se = out.get("score_e")
    if not (se and se.get("estimable")):
        return None
    bilan_ = out.get("bilan")
    cf_central = (getattr(bilan_, "charge_fonciere", None) or {}).get("central") if bilan_ else None
    charge = cf_central if cf_central is not None else se["charge_supportable"]
    prix_probable = se["prix_probable"]
    return {"charge": charge, "prix_probable": prix_probable,
            "marge": round(charge - prix_probable), "niveau_prix": se["niveau_prix"],
            "charge_du_bilan": cf_central is not None}


def cover(out: dict, *, titre: str = "Dossier foncier", bandeau: str = "",
          produit_sous_titre: str = "DOSSIER BANQUIER · présentation financeur",
          synthese_titre: str = "Synthèse exécutive", marque: dict | None = None) -> str:
    """Couverture générique (Banquier) : chapeau de marque (C2), synthèse, cartouches
    avec la charge foncière en HÉROS (C6), plan de situation clair (C2)."""
    p = out["parcelle"]
    photo = map_html(p["geojson"])
    kpis = []
    bilan_ = out.get("bilan")
    if bilan_ and bilan_.charge_fonciere:
        kpis.append(cartouche("Charge foncière supportable · Estimé", eur(bilan_.charge_fonciere.get("central")),
                              "médiane", hero=True))
    kpis.append(cartouche("Terrain · Sourcé", f"{p['surface_m2']:.0f} m²"))
    fo = (out.get("faisabilite").fourchette if out.get("faisabilite") else {}) or {}
    if fo.get("shab_vendable_m2"):
        kpis.append(cartouche("Surface vendable · Estimé", f"~{fo['shab_vendable_m2']:.0f} m²"))
    sa = score_e_affiche(out)
    if sa:
        # marge = charge (bilan à rebours, point de calcul unique) − prix probable du foncier.
        # M97 G2 : en repli (bilan indisponible), la provenance Score É est dite sur le cartouche.
        label_marge = "Marge estimée · Estimé" if sa["charge_du_bilan"] else "Marge estimée · barème sectoriel"
        kpis.append(cartouche(label_marge, eur(sa["marge"])))
    synthese = f"<h2>{esc(synthese_titre)}</h2>{out['_synthese']}" if out.get("_synthese") else ""
    # M128-B6 : l'encadré « Verdict LABUSE » (verdict, rang île, motif copropriétés) est RETIRÉ du
    # dossier banquier — aucun verdict, rang ni score sur ce document (même règle que fiche et dossier).
    # Le financeur lit des attributs factuels et le bilan, pas un classement interne.
    return (f"<section class='garde'>"
            f"{garde_entete(p, produit_sous_titre=produit_sous_titre, titre=titre, bandeau=bandeau, marque=marque)}"
            f"{synthese}"
            f"{cartouches(kpis)}"
            f"<h2>Situation</h2>{photo}</section>")


def identite(out: dict) -> str:
    p = out["parcelle"]
    rap = out.get("rapport") or {}
    ident = rap.get("identite") or {}
    adresse = rap.get("adresse")
    rows = [("Références cadastrales", f"{p['idu']} · section {p['section']} n° {p['numero']}", "S"),
            ("Commune", p["commune"], "S"),
            ("Surface du terrain", f"{p['surface_m2']:.0f} m²", "S")]
    if adresse:
        rows.append(("Adresse (BAN)", adresse, "S"))
    zonage = "".join(f"<tr><td>{esc(z['libelle'] or z['classe'])}</td>"
                     f"<td class='n'>{esc(z['pct'])} %</td><td>{esc(z['idurba'] or '—')}</td></tr>"
                     for z in ident.get("zones", [])) or "<tr><td colspan='3'>Zonage non résolu</td></tr>"
    regles = ""
    r = ident.get("regles") or {}
    if r.get("emprise_max_m2"):
        regles += f"<tr><td>Emprise au sol maximale</td><td class='n'>{r['emprise_max_m2']:g} m²</td><td>{s('E')}</td></tr>"
    # M128-2-A : la hauteur affichée vient du PLU CALIBRÉ (résolu par zone + commune) — EXACTEMENT
    # la même source que le scénario de faisabilité ci-après. On cesse de servir la hauteur générique
    # de parcel_residuel_bati (9 m sur 207 k parcelles, faux sur 66,7 %). Égout ET faîtage, Sourcé
    # (article PLU) quand la calibration le porte.
    from ..faisabilite.plu_rules import resolve_zone
    # le code de zone précis est dans `libelle` (« Ua », « UB »), pas `classe` (famille « U »/« AU »).
    _zone_code = next((z.get("libelle") or z.get("classe")
                       for z in (ident.get("zones") or []) if (z.get("libelle") or z.get("classe"))), None)
    _zr = resolve_zone(_zone_code, p["commune"]) if _zone_code else None
    if _zr and isinstance(getattr(_zr, "he_m", None), (int, float)):
        _src_h = (getattr(_zr, "sources", None) or {}).get("hauteur")
        _nat = s("S") if _src_h else s("E")
        regles += (f"<tr><td>Hauteur d'égout retenue (PLU)</td><td class='n'>{_zr.he_m:g} m</td><td>{_nat}</td></tr>")
        if isinstance(getattr(_zr, "hf_m", None), (int, float)):
            regles += (f"<tr><td>Hauteur au faîtage (PLU)</td><td class='n'>{_zr.hf_m:g} m</td><td>{_nat}</td></tr>")
    body = ("<table>" + "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v)}</td><td>{s(prov)}</td></tr>" for k, v, prov in rows) + "</table>"
        f"<h3>Zonage du document d'urbanisme</h3>"
        f"<table><tr><th>Zone</th><th class='n'>Part</th><th>Document</th></tr>{zonage}</table>")
    # M73 « le dryrun servi fait foi » : verdict de constructibilité du zonage SERVI (arbitré/
    # libellé) — même énoncé que la fiche écran & le dossier, jamais recalculé au fil des documents.
    zv = ident.get("zonage_verdict")
    if zv and zv.get("detail"):
        body += f"<p class='note'>{esc(zv['detail'])}</p>"
    if regles:
        body += (f"<h3>Règles calibrées</h3><table><tr><th>Règle</th><th class='n'>Valeur</th><th>Nature</th></tr>"
                 f"{regles}</table><p class='note'>Règles calibrées LABUSE (nature par ligne) — le règlement "
                 f"complet (retraits, prospects, servitudes) peut modifier ces valeurs.</p>")
    return f"<div class='pb'></div><h2>Identité de la parcelle</h2>{body}"


def faisabilite(out: dict) -> str:
    fais = out.get("faisabilite")
    if fais is None:
        return ("<div class='pb'></div><h2>Faisabilité</h2>"
                "<p class='note'>Capacité constructible non résolue pour cette parcelle — non estimable.</p>")
    import re as _re
    def _borne(v: str) -> str:  # M54-AB F10 : « 2 à 2 » / « 2–2 » → « 2 » (borner quand min = max)
        return _re.sub(r"(\d+(?:[.,]\d+)?)\s*(?:à|–|-)\s*\1\b", r"\1", v or "")
    _pmap = {"sourcee": "S", "estimee": "E", "derive": "E", "": "E"}
    steps = "".join(
        f"<tr><td>{esc(st.label)}</td><td>{esc(_borne(st.formule))}</td><td class='n'>{esc(_borne(st.valeur))}</td>"
        f"<td>{s(_pmap.get(st.prov, 'E'))}</td></tr>" for st in fais.steps)
    fo = fais.fourchette or {}
    synth = ""
    if fo:
        parts = []
        if fo.get("shab_vendable_m2"):
            parts.append(f"surface vendable ~{fo['shab_vendable_m2']} m²")
        if fo.get("logements_au_sol"):
            lo, hi = fo["logements_au_sol"]
            parts.append(f"~{lo} logements" if lo == hi else f"{lo} à {hi} logements")
        if fo.get("hauteur_m"):
            # M54-AB C6 : hauteur d'égout RETENUE (R+2), distincte de la hauteur totale de zone
            # (plafond PLU) citée en Identité — chaque valeur étiquetée par ce qu'elle mesure.
            parts.append(f"hauteur d'égout retenue ~{fo['hauteur_m']:g} m")
        synth = f"<p><b>Potentiel indicatif :</b> {esc(' · '.join(parts))} {s('E')}</p>"
        # M128-3-§1/H : depuis que la SDP du bilan = vendable ÷ rendement, vendable et plancher du
        # bilan COÏNCIDENT par construction — l'écart « méthode/arrondi » a disparu. Reste seulement
        # l'écart avec la surface habitable BRUTE du gabarit quand le PLAFOND DE DENSITÉ écrête les
        # logements. Sous 5 m² : AUCUNE ligne (pas de « 0 m² » vide) ; au-delà, on l'affiche et on le nomme.
        if fo.get("shab_vendable_m2"):
            _vend = fo["shab_vendable_m2"]
            _sh = next((st.valeur for st in (fais.steps or [])
                        if "habitable" in (st.label or "").lower()), None)
            _m = _re.search(r"(\d[\d\s ]*)", _sh) if _sh else None
            _deriv = int(_re.sub(r"[\s ]", "", _m.group(1))) if _m else None
            if _deriv and (_deriv - round(_vend)) > 5:      # plafond écrête sous le rendement du gabarit
                _pct = 100 * (_deriv - round(_vend)) / max(_deriv, 1)
                synth += (f"<p class='note'>Surface vendable retenue ~{_vend:.0f} m² &lt; surface habitable "
                          f"au rendement du gabarit ~{_deriv} m² ({_deriv - round(_vend)} m², {_pct:.0f} %) : "
                          f"le plafond de densité écrête le nombre de logements — c'est cette surface "
                          f"vendable écrêtée qui est portée au bilan.</p>")
    avert = "".join(f"<li>{esc(a)}</li>" for a in (fais.avertissements or []))
    # M54-AB C2 : NOMMER le scénario. Ce bloc chiffre le NEUF hors bâti existant (reculs, table
    # rase) — l'autre document (dossier/flash) chiffre le résiduel « bâti conservé ». L'avertissement
    # démolition est visible PRÈS du chiffre (le coût de démolition n'est PAS inclus au bilan).
    return (f"<div class='pb'></div><h2>Faisabilité neuve — hors bâti existant</h2>"
            f"<p class='note'><b>Scénario table rase</b> : capacité en construction neuve, bâti "
            f"existant supposé démoli (reculs réglementaires appliqués). La démolition est à "
            f"chiffrer — <b>non incluse</b> dans le bilan. Le potentiel « bâti conservé » figure "
            f"au dossier parcelle.</p>{synth}"
            # M73 C4 : jamais un tableau à en-têtes seuls. Sans étape (zone inconstructible), une phrase.
            + (f"<table><tr><th>Étape</th><th>Calcul</th><th class='n'>Valeur</th><th>Nature</th></tr>{steps}</table>"
               if fais.steps else
               "<p class='note'>Aucune étape de capacité — la construction neuve n'est pas autorisée "
               "sur cette parcelle (zonage/PPR excluant le neuf).</p>")
            + (f"<p class='note'>Avertissements : <ul>{avert}</ul></p>" if avert else "")
            + f"<p class='note'>{esc(fais.bandeau)}</p>")


def bilan(out: dict) -> str:
    bilan_ = out.get("bilan")
    se = out.get("score_e")
    if bilan_ is None and not se:
        return ""
    body = "<div class='pb'></div><h2>Bilan promoteur & charge foncière</h2>"
    if bilan_ is not None and getattr(bilan_, "fiabilite", None) == "non_calculable":
        # MANDAT PRIX SORTIE CONSOMMATEURS (Vic 28/07/2026) — commune sans marché du collectif neuf
        # observable / social-dominante : la MENTION est servie (jamais un chiffre de marché faux),
        # le dossier reste généré. Comportement M26-A « non estimable — non filtrée ».
        body += (f"<p class='note'><b>Charge foncière de marché non calculable.</b> "
                 f"{esc(getattr(bilan_, 'verdict', '') or getattr(bilan_, 'bandeau', ''))}</p>")
    elif bilan_ is not None:
        # C1/C4 — l'encadré d'hypothèses reflète le bilan RÉELLEMENT servi : le total marge & frais
        # DÉDUIT du CA (24 % = marge + honoraires + frais financiers du secteur), avec ses composantes
        # nommées — jamais le défaut global agrégé (21 %) qui contredirait la ligne bilan.
        from ..faisabilite.bilan import CALCULETTE_COUT_DEFAUT_M2, CALCULETTE_MARGE_FRAIS_DEFAUT_PCT
        _calc = getattr(bilan_, "calc", None) or {}
        _coef = _calc.get("coef")
        _marge_frais = round((1 - _coef) * 100) if _coef is not None else CALCULETTE_MARGE_FRAIS_DEFAUT_PCT
        _composantes = next((st.formule for st in (bilan_.steps or [])
                             if st.label.startswith("Marge + frais")), None)
        body += hypotheses_encadre(_calc.get("cm_bas", CALCULETTE_COUT_DEFAUT_M2), _marge_frais,
                                   composantes=_composantes, cout_m2_haut=_calc.get("cm_haut"))
        steps = "".join(
            f"<tr><td>{esc(st.label)}</td><td class='n'>{esc(st.valeur)}</td>"
            f"<td>{s({'sourcee':'S'}.get(st.prov, 'E'))}</td></tr>" for st in bilan_.steps)
        body += (f"<table><tr><th>Poste</th><th class='n'>Valeur</th><th>Nature</th></tr>{steps}</table>")
        cf = bilan_.charge_fonciere or {}
        if cf:
            # M128-2-D : UNIQUE occurrence de la fourchette (retirée de la ligne d'étape). D2(a) : la
            # borne basse RÉELLE (négative = plancher), la médiane au centre. Note « plancher » si < 0.
            _bas = cf.get("bas")
            _plancher = ""
            if isinstance(_bas, (int, float)) and _bas < 0:
                _plancher = ("<p class='note'>Borne basse négative : aux coûts hauts / prix bas, "
                             "l'opération ne dégage aucune valeur pour le terrain (plancher de la "
                             "fourchette, pas un prix). La médiane est au centre de la fourchette.</p>")
            body += (f"<h3>Charge foncière supportable — fourchette {s('E')}</h3>"
                     f"<table><tr><th class='n'>Basse (plancher)</th><th class='n'>Médiane</th><th class='n'>Haute</th>"
                     f"<th class='n'>Par m² terrain</th></tr>"
                     f"<tr><td class='n'>{eur(_bas)}</td><td class='n'>{eur(cf.get('central'))}</td>"
                     f"<td class='n'>{eur(cf.get('haut'))}</td><td class='n'>{esc(cf.get('par_m2_terrain'))} €/m²</td></tr></table>"
                     f"{_plancher}"
                     f"<p class='note'>Fiabilité du bilan : {esc(bilan_.fiabilite)}. {esc(bilan_.bandeau)}</p>")
    sa = score_e_affiche(out)
    if sa:
        # M54-AB C3 : la charge LUE ici = celle du bilan à rebours ci-dessus (point de calcul
        # unique). M128-2-C : CHAQUE montant porte la qualification de SA source — la charge vient du
        # bilan à rebours, le prix PROBABLE du foncier est une médiane terrain sectorielle. Ne plus
        # coller « prix de sortie neuf » sur le prix probable (deux objets marché différents).
        # M128-2-E : terme unique « charge foncière supportable ». B7 : plus de « Score É » en vitrine.
        terrain = out["parcelle"]["surface_m2"]
        if sa["charge_du_bilan"]:
            provenance = "<p><b>Charge foncière supportable issue du bilan à rebours</b> (ci-dessus).</p>"
            detail = (f"Charge foncière supportable = bilan à rebours ci-dessus ({eur(sa['charge'])}) ; "
                      f"prix probable du foncier = médiane terrain sectorielle × {terrain:.0f} m². Estimé — "
                      f"hors coûts spécifiques (démolition, dépollution, VRD, stationnement, TVA, aléas). "
                      f"N'est ni un prix ni une promesse.")
        else:
            provenance = ("<p><b>Charge foncière supportable estimée au barème sectoriel — bilan "
                          "complet indisponible sur cette parcelle.</b></p>")
            detail = (f"Charge foncière supportable = barème sectoriel ({eur(sa['charge'])}, le bilan à "
                      f"rebours n'a pas pu être calculé ici) ; prix probable du foncier = médiane terrain "
                      f"sectorielle × {terrain:.0f} m². Estimé — hors coûts spécifiques (démolition, "
                      f"dépollution, VRD, stationnement, TVA, aléas). N'est ni un prix ni une promesse.")
        body += (f"<h3>Marge foncière estimée {s('E')}</h3>"
                 f"{provenance}"
                 f"<p><b>{eur(sa['marge'])}</b> = charge foncière supportable {eur(sa['charge'])} "
                 f"− prix probable du foncier {eur(sa['prix_probable'])} "
                 f"(médiane terrain sectorielle × {terrain:.0f} m²).</p>"
                 f"<p class='note'>{esc(detail)}</p>")
        # MANDAT_DVF-B Phase 2 — le garde-fou du 2× : la charge foncière SUPPORTABLE (projection du
        # bilan à rebours) confrontée au prix PROBABLE du foncier (référence marché, médiane terrain
        # sectorielle). Un écart > 2× = information manquante (coûts sous-estimés ou référence trop
        # mince), jamais une affaire. Il ANNOTE : ne bloque, ne masque, ne retire aucun chiffre. Si la
        # référence manque, il le DIT (écart non mesurable) plutôt que de se taire.
        from ..marche_service import garde_fou_signal
        gf = garde_fou_signal(sa.get("charge"), sa.get("prix_probable"))
        if gf["note"]:
            couleur = "#A87916" if gf["declenche"] else "#5F6C65"   # ambre (alerte) / gris (non mesurable)
            body += f"<p class='note' style='color:{couleur}'>{esc(gf['note'])}</p>"
    elif se:
        body += f"<h3>Marge foncière estimée</h3><p class='note'>Marge {s('A')} — données de marché insuffisantes.</p>"
    return body


def comparables(out: dict) -> str:
    prix = out.get("prix_dvf")
    perm = out.get("permits")
    if not prix and not perm:
        return ""
    body = "<div class='pb'></div><h2>Marché de comparaison</h2>"
    # M54-AB C5 : 3 lignes commune du bloc Marché M-U (tendance, liquidité, offre), chacune datée.
    cm = out.get("commune_marche") or []
    if cm:
        import re as _re2
        # M128-2-L2 : règle unique de séparateur — les €/m² s'écrivent sans espace de milliers,
        # comme les tableaux du bilan (« 2192 €/m² », pas « 2 192 » ici et « 2192 » là).
        def _sep(txt: str) -> str:
            return _re2.sub(r"(?<=\d)\s(?=\d{3}\b)", "", txt or "")
        lignes = "".join(f"<li>{esc(_sep(l['phrase']))}</li>" for l in cm)
        body += f"<h3>Marché de la commune {s('S')}</h3><ul>{lignes}</ul>"
    if prix and prix.get("median"):
        # Comparables DVF de l'EXISTANT (pas le prix de sortie neuf du bilan — mandat prix sortie
        # consommateurs, Vic 28/07/2026 : ne pas étiqueter « prix de sortie » ce qui est l'existant).
        body += (f"<h3>Prix du marché — comparables DVF (existant) {s('S')}</h3>"
                 f"<table><tr><th class='n'>Q1</th><th class='n'>Médiane</th><th class='n'>Q3</th>"
                 f"<th class='n'>Ventes</th><th>Période</th><th>Fiabilité</th></tr>"
                 f"<tr><td class='n'>{esc(prix.get('q1'))}</td><td class='n'>{esc(prix.get('median'))}</td>"
                 f"<td class='n'>{esc(prix.get('q3'))}</td><td class='n'>{esc(prix.get('n'))}</td>"
                 f"<td>{esc(prix.get('periode'))}</td><td>{esc(prix.get('fiabilite'))}</td></tr></table>"
                 f"<p class='note'>€/m² habitable · rayon {int(prix.get('radius_m') or 0)} m adaptatif autour de la parcelle"
                 + (" · repli commune" if prix.get("commune_fallback") else "") + ".</p>")
        # MANDAT_DVF-B — la RÉSERVE de méthode accompagne le chiffre (helper unique, écrite une fois).
        from ..marche_service import reserve_methode
        body += f"<p class='note'>{esc(reserve_methode())}</p>"
        comp = prix.get("comparables")
        if isinstance(comp, dict) and (comp.get("mediane_ancien") or comp.get("mediane_vefa")):
            body += (f"<table><tr><th>Segment</th><th class='n'>Ventes</th><th class='n'>Médiane €/m²</th></tr>"
                     f"<tr><td>Ancien</td><td class='n'>{esc(comp.get('n_ancien'))}</td>"
                     f"<td class='n'>{esc(comp.get('mediane_ancien'))}</td></tr>"
                     f"<tr><td>Neuf / VEFA</td><td class='n'>{esc(comp.get('n_vefa'))}</td>"
                     f"<td class='n'>{esc(comp.get('mediane_vefa'))}</td></tr></table>"
                     + (f"<p class='note'>Écart neuf / ancien : {esc(comp.get('ecart_vefa_ancien_pct'))} %.</p>"
                        if comp.get("ecart_vefa_ancien_pct") is not None else ""))
    if perm and perm.get("items"):
        # M128-C8 : devant un financeur, les permis voisins sont filtrés à ≤ 5 ans — un dépôt de
        # 2014-2018 n'est plus un signal de dynamique. Le compte « dynamique » du bloc reste, lui,
        # borné en amont (nearby_permits) ; ici on borne la LISTE affichée.
        from datetime import date as _date, timedelta as _td
        _cut = (_date.today() - _td(days=5 * 365)).isoformat()
        recents = [it for it in perm["items"] if (it.get("date") or "") >= _cut]
        if recents:
            rows = "".join(f"<tr><td>{esc(it.get('date'))}</td><td>{esc(it.get('type_label') or it.get('type'))}</td>"
                           f"<td class='n'>{esc(it.get('distance_m'))} m</td><td>{esc(it.get('statut') or '—')}</td></tr>"
                           for it in recents[:10])
            body += (f"<h3>Permis de construire voisins (SITADEL, ≤ 5 ans) {s('S')}</h3>"
                     f"<table><tr><th>Date</th><th>Type</th><th class='n'>Distance</th><th>Statut</th></tr>{rows}</table>")
    return body


def risques(out: dict) -> str:
    # M128-C11 : même hygiène de libellé que la fiche/dossier (M125-1ter) — on nettoie les détails
    # servis (codes techniques, proxys SAFER/SAR-couche/OCS GE/ENS) avant impression au financeur.
    from .export_commun import nettoyer_libelle_client as _net
    rap = out.get("rapport") or {}
    risq, pat = rap.get("risques"), rap.get("patrimoine")
    zan = out.get("zan")
    body = "<div class='pb'></div><h2>Risques, servitudes & sobriété foncière</h2>"

    # M128-2-K : panne ≠ absence. CHAQUE famille annoncée par le titre porte un état EXPLICITE :
    # constat listé, sinon « aucun constat » (couche interrogée, rien trouvé), sinon INDISPONIBLE
    # (couche non interrogée). Un tableau vide ne doit jamais se lire « aucune servitude » par défaut.
    def _famille(titre: str, data: dict | None, avec_abf: bool = False) -> str:
        if data is None:
            return (f"<h3>{titre}</h3><p class='note'><b>INDISPONIBLE</b> — couche non interrogée "
                    f"pour cette parcelle (absence de donnée, pas absence de contrainte).</p>")
        rows = [(c["label"], _net(c.get("kind"), c.get("detail"))) for c in (data.get("couches") or [])]
        if avec_abf and data.get("abf_note"):
            rows.append(("Abords de monument historique", _net("abf", data["abf_note"])))
        if rows:
            body_rows = "".join(f"<tr><td>{esc(lbl)}</td><td>{esc(d or 'parcelle concernée')}</td></tr>"
                                for lbl, d in rows)
            return (f"<h3>{titre}</h3><table><tr><th>Élément</th><th>Détail / niveau</th></tr>"
                    f"{body_rows}</table>")
        return (f"<h3>{titre}</h3><p class='note'>Aucun constat dans les couches analysées "
                f"(état renseigné, pas « inconnu »).</p>")

    body += _famille("Risques (aléas, PPR, pollution, mouvements de terrain, ICPE…)", risq)
    body += _famille("Servitudes &amp; patrimoine (ABF, espaces protégés, QPV…)", pat, avec_abf=True)
    if zan:
        c2 = zan.get("conso_2021_2024_m2")
        c1 = zan.get("conso_2011_2021_m2")
        # M128-2-L1 : hectares sans décimale parasite (« 20 ha », pas « 20.0 ha »).
        _ha1 = f"{round(c1 / 10000)} ha" if c1 else "—"
        _ha2 = f"{round(c2 / 10000)} ha" if c2 else "—"
        # M54-AB C8 : le banquier montre le TOTAL consommé sur la période (ha) ; le dossier/flash
        # montre le RYTHME annuel (m²/an) sur les MÊMES périodes — chaque métrique est étiquetée.
        body += (f"<h3>ZAN — consommation d'espaces (commune) {s('S')}</h3>"
                 f"<table><tr><th>Période</th><th class='n'>ENAF consommé (total période)</th></tr>"
                 f"<tr><td>2011–2021</td><td class='n'>{esc(_ha1)}</td></tr>"
                 f"<tr><td>2021–2024</td><td class='n'>{esc(_ha2)}</td></tr></table>"
                 f"<p class='note'>Source {esc(zan.get('source_nom'))} ({esc(zan.get('millesime'))}) · "
                 f"objectif loi Climat/TRACE = −50 % de consommation d'ENAF. Voir la fiche commune pour budget/reste.</p>")
    return body


def assainissement_rehab(out: dict) -> str:
    """M73-D — les blocs ASSAINISSEMENT + RÉHABILITATION, rendu PARTAGÉ (blocs_documents, écrit une
    fois). Jamais recalculé (helpers uniques statut_anc / compute_mode_b posés dans collect), jamais
    masqué : l'absence est un état affiché (« Absent » / « Non évaluée »)."""
    from .blocs_documents import anc_bloc_html, rehab_bloc_html
    return ("<div class='pb'></div><h2>Assainissement &amp; réhabilitation</h2>"
            + anc_bloc_html(out.get("anc")) + rehab_bloc_html(out.get("mode_b")))


def limites_section(doc: str) -> str:
    """M73 §5 — « Ce que ce document ne peut pas dire » : absences + où le destinataire peut les
    chercher (matérialise le 3e terme de la doctrine). Contenu = source unique export_commun."""
    from .export_commun import LIMITES_TITRE, limites_document
    rows = "".join(f"<tr><td>{esc(a)}</td><td class='note'>→ {esc(o)}</td></tr>"
                   for a, o in limites_document(doc))
    return (f"<div class='pb'></div><h2>{esc(LIMITES_TITRE)}</h2>"
            f"<table><tr><th>Ce que le dossier n'établit pas</th><th>Où le vérifier</th></tr>"
            f"{rows}</table>")


# ───────────────────────── rendu ─────────────────────────

def render_pdf(sections: list[str], libelle: str, *, produit: str = "",
               idu: str = "", commune: str = "") -> bytes:
    """Assemble les sections non vides et rend le PDF. C7 : le bandeau de contexte
    (« LABUSE — produit · IDU — commune ») court sur CHAQUE page (sauf la garde,
    qui porte le wordmark graphique — même règle que le Flash)."""
    from weasyprint import HTML
    from .blocs_documents import BLOC_CSS            # M73-G — habillage des blocs, écrit une fois
    css = page_css(libelle, produit=produit, idu=idu, commune=commune) + BLOC_CSS
    doc = (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><style>{css}</style></head>"
           f"<body>{''.join(sec for sec in sections if sec)}</body></html>")
    return HTML(string=doc).write_pdf()
