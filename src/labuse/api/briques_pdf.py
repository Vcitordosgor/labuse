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
    border-bottom: 0.6pt solid #0B8A5F; width: 100%; padding-bottom: 4pt;
    margin-bottom: 8pt; vertical-align: bottom;
  }}
  @top-right {{
    content: "{date_edition}";
    font-family: "JetBrains Mono", monospace; font-size: 7pt; color: #8C9891;
    border-bottom: 0.6pt solid #0B8A5F; vertical-align: bottom;
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
     border-bottom: 1.4pt solid #0B8A5F; break-after: avoid; }}
h3 {{ font-size: 10pt; margin: 4mm 0 1.5mm 0; break-after: avoid; }}
.marque {{ display: flex; align-items: center; margin-bottom: 8mm; }}
.wordmark {{ font-family: "Space Grotesk"; font-weight: 700; font-size: 16pt;
            color: #0B8A5F; letter-spacing: 0.04em; margin-left: 4mm; }}
.produit {{ font-family: "JetBrains Mono", monospace; font-size: 8pt;
           color: #5F6C65; margin-left: 4mm; }}
.refs {{ font-family: "JetBrains Mono", monospace; font-size: 9pt;
        color: #5F6C65; margin-bottom: 5mm; }}
.refs b {{ color: #111814; }}
table {{ width: 100%; border-collapse: collapse; margin: 1mm 0; }}
td, th {{ border-bottom: 0.5pt solid #D8E2DC; padding: 1.6mm 2mm 1.6mm 0; text-align: left;
  font-size: 8.6pt; vertical-align: top; }}
th {{ color: #5F6C65; text-transform: uppercase; font-size: 6.8pt; letter-spacing: 0.3pt;
  border-bottom: 0.8pt solid #0B8A5F; font-family: "JetBrains Mono", monospace; }}
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
.cartouche.hero .valeur {{ font-size: 27pt; color: #0B8A5F; }}   /* C6 : lisible à 2 mètres */
.cartouches {{ display: flex; gap: 3mm; margin: 3mm 0; }}
.cartouches .cartouche {{ flex: 1; margin: 0; }}
.exec {{ background: #F4F8F6; border-left: 2.5pt solid #0B8A5F; padding: 3mm 4mm;
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
            f"<path d='{_logo_svg_path()}' fill='#0B8A5F'/></svg>"
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


def hypotheses_encadre(cout_m2: float, marge_pct: float, composantes: str | None = None) -> str:
    """C1 — l'encadré « Hypothèses de calcul », IDENTIQUE en forme dans tous les documents
    qui chiffrent. Deux documents aux hypothèses différentes l'affichent chacun — le
    lecteur qui tient les deux comprend d'où vient tout écart.

    M54-AB C4 : `marge_pct` doit être le total RÉELLEMENT déduit par le bilan servi (24 % =
    marge + honoraires + frais financiers du secteur), pas le défaut global agrégé (21 %) —
    sinon l'encadré dit 21 % et la ligne bilan 24 %. `composantes` nomme la décomposition."""
    detail = f" (soit {composantes})" if composantes else ""
    return (f"<div class='hyp-encadre'><span class='titre'>Hypothèses de calcul</span>"
            f"Coût de construction <b>{cout_m2:g} €/m²</b> de surface de plancher · "
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
                out["prix_dvf"] = sector_price(db, pid, Hypotheses.charger())  # comparables DVF (LÉGITIME)
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

    # permis SITADEL voisins (contexte promoteur)
    try:
        from ..ingestion.permits import nearby_permits
        out["permits"] = nearby_permits(db, pid)
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
    polys = "".join(f"<polygon points='{p}' fill='rgba(11,138,95,0.16)' stroke='#0B8A5F' "
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
        kpis.append(cartouche("Charge foncière · Estimé", eur(bilan_.charge_fonciere.get("central")),
                              "médiane", hero=True))
    kpis.append(cartouche("Terrain · Sourcé", f"{p['surface_m2']:.0f} m²"))
    fo = (out.get("faisabilite").fourchette if out.get("faisabilite") else {}) or {}
    if fo.get("shab_vendable_m2"):
        kpis.append(cartouche("Surface vendable · Estimé", f"~{fo['shab_vendable_m2']:.0f} m²"))
    sa = score_e_affiche(out)
    if sa:
        # marge = charge (bilan à rebours, point de calcul unique) − prix probable du foncier
        kpis.append(cartouche("Marge estimée · Estimé", eur(sa["marge"])))
    synthese = f"<h2>{esc(synthese_titre)}</h2>{out['_synthese']}" if out.get("_synthese") else ""
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
        regles += f"<tr><td>Emprise au sol maximale</td><td class='n'>{r['emprise_max_m2']} m²</td><td>{s('E')}</td></tr>"
    if r.get("hauteur_max_m"):
        regles += f"<tr><td>Hauteur maximale</td><td class='n'>{r['hauteur_max_m']} m</td><td>{s('E')}</td></tr>"
    body = ("<table>" + "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v)}</td><td>{s(prov)}</td></tr>" for k, v, prov in rows) + "</table>"
        f"<h3>Zonage du document d'urbanisme</h3>"
        f"<table><tr><th>Zone</th><th class='n'>Part</th><th>Document</th></tr>{zonage}</table>")
    if regles:
        body += (f"<h3>Règles calibrées</h3><table><tr><th>Règle</th><th class='n'>Valeur</th><th>Nature</th></tr>"
                 f"{regles}</table><p class='note'>Règles calibrées LABUSE (Estimé) — le règlement complet "
                 f"(retraits, prospects, servitudes) peut modifier ces valeurs.</p>")
    return f"<div class='pb'></div><h2>Identité de la parcelle</h2>{body}"


def faisabilite(out: dict) -> str:
    fais = out.get("faisabilite")
    if fais is None:
        return ("<div class='pb'></div><h2>Faisabilité</h2>"
                "<p class='note'>Capacité constructible non résolue pour cette parcelle — non estimable.</p>")
    _pmap = {"sourcee": "S", "estimee": "E", "derive": "E", "": "E"}
    steps = "".join(
        f"<tr><td>{esc(st.label)}</td><td>{esc(st.formule)}</td><td class='n'>{esc(st.valeur)}</td>"
        f"<td>{s(_pmap.get(st.prov, 'E'))}</td></tr>" for st in fais.steps)
    fo = fais.fourchette or {}
    synth = ""
    if fo:
        parts = []
        if fo.get("shab_vendable_m2"):
            parts.append(f"surface vendable ~{fo['shab_vendable_m2']} m²")
        if fo.get("logements_au_sol"):
            lo, hi = fo["logements_au_sol"]
            parts.append(f"{lo} à {hi} logements")
        if fo.get("hauteur_m"):
            parts.append(f"hauteur ~{fo['hauteur_m']} m")
        synth = f"<p><b>Potentiel indicatif :</b> {esc(' · '.join(parts))} {s('E')}</p>"
        # M54-AB C3 : la surface vendable retenue (capacité en logements, portée au bilan) et la
        # dérivation de plancher ci-dessous peuvent différer de ~1-2 m² — même scénario, méthodes
        # distinctes. On l'ÉTIQUETTE plutôt que de laisser deux chiffres nus se contredire.
        if fo.get("shab_vendable_m2"):
            synth += (f"<p class='note'>Surface vendable retenue ~{fo['shab_vendable_m2']:.0f} m² "
                      f"(capacité en logements, valeur portée au bilan) ; la dérivation de plancher "
                      f"ci-dessous aboutit à la surface habitable au rendement — même scénario, "
                      f"écart de méthode/arrondi.</p>")
    avert = "".join(f"<li>{esc(a)}</li>" for a in (fais.avertissements or []))
    # M54-AB C2 : NOMMER le scénario. Ce bloc chiffre le NEUF hors bâti existant (reculs, table
    # rase) — l'autre document (dossier/flash) chiffre le résiduel « bâti conservé ». L'avertissement
    # démolition est visible PRÈS du chiffre (le coût de démolition n'est PAS inclus au bilan).
    return (f"<div class='pb'></div><h2>Faisabilité neuve — hors bâti existant</h2>"
            f"<p class='note'><b>Scénario table rase</b> : capacité en construction neuve, bâti "
            f"existant supposé démoli (reculs réglementaires appliqués). La démolition est à "
            f"chiffrer — <b>non incluse</b> dans le bilan. Le potentiel « bâti conservé » figure "
            f"au dossier parcelle.</p>{synth}"
            f"<table><tr><th>Étape</th><th>Calcul</th><th class='n'>Valeur</th><th>Nature</th></tr>{steps}</table>"
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
        _coef = (getattr(bilan_, "calc", None) or {}).get("coef")
        _marge_frais = round((1 - _coef) * 100) if _coef is not None else CALCULETTE_MARGE_FRAIS_DEFAUT_PCT
        _composantes = next((st.formule for st in (bilan_.steps or [])
                             if st.label.startswith("Marge + frais")), None)
        body += hypotheses_encadre(CALCULETTE_COUT_DEFAUT_M2, _marge_frais, composantes=_composantes)
        steps = "".join(
            f"<tr><td>{esc(st.label)}</td><td class='n'>{esc(st.valeur)}</td>"
            f"<td>{s({'sourcee':'S'}.get(st.prov, 'E'))}</td></tr>" for st in bilan_.steps)
        body += (f"<table><tr><th>Poste</th><th class='n'>Valeur</th><th>Nature</th></tr>{steps}</table>")
        cf = bilan_.charge_fonciere or {}
        if cf:
            body += (f"<h3>Charge foncière supportable (fourchette) — {s('E')}</h3>"
                     f"<table><tr><th class='n'>Basse</th><th class='n'>Centrale</th><th class='n'>Haute</th>"
                     f"<th class='n'>Par m² terrain</th></tr>"
                     f"<tr><td class='n'>{eur(cf.get('bas'))}</td><td class='n'>{eur(cf.get('central'))}</td>"
                     f"<td class='n'>{eur(cf.get('haut'))}</td><td class='n'>{esc(cf.get('par_m2_terrain'))} €/m²</td></tr></table>"
                     f"<p class='note'>Fiabilité du bilan : {esc(bilan_.fiabilite)}. {esc(bilan_.bandeau)}</p>")
    sa = score_e_affiche(out)
    if sa:
        from ..ingestion.score_e import niveau_label
        # M54-AB C3 : la charge LUE ici = celle du bilan à rebours ci-dessus (point de calcul
        # unique), jamais la charge Score É recalculée à 21 % — sinon 71 vs 69 k€ sur le même
        # document. La marge en découle. On ne réutilise plus se['detail'] (il citait 71 k€ / ×0.79).
        terrain = out["parcelle"]["surface_m2"]
        detail = (f"Charge supportable = charge foncière acceptable du bilan à rebours ci-dessus "
                  f"({eur(sa['charge'])}) ; prix probable du foncier = médiane terrain sectorielle "
                  f"× {terrain:.0f} m². Estimé — hors coûts spécifiques (démolition, dépollution, VRD, "
                  f"stationnement, TVA, aléas). N'est ni un prix ni une promesse.")
        body += (f"<h3>Score É — marge foncière estimée {s('E')}</h3>"
                 f"<p><b>{eur(sa['marge'])}</b> = charge supportable {eur(sa['charge'])} "
                 f"− prix probable du foncier {eur(sa['prix_probable'])} "
                 f"(prix de sortie neuf — {esc(niveau_label(sa['niveau_prix']))}).</p>"
                 f"<p class='note'>{esc(detail)}</p>")
    elif se:
        body += f"<h3>Score É</h3><p class='note'>Marge {s('A')} — données de marché insuffisantes.</p>"
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
        lignes = "".join(f"<li>{esc(l['phrase'])}</li>" for l in cm)
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
                 f"<p class='note'>€/m² habitable · rayon {esc(prix.get('radius_m'))} m adaptatif autour de la parcelle"
                 + (" · repli commune" if prix.get("commune_fallback") else "") + ".</p>")
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
        rows = "".join(f"<tr><td>{esc(it.get('date'))}</td><td>{esc(it.get('type_label') or it.get('type'))}</td>"
                       f"<td class='n'>{esc(it.get('distance_m'))} m</td><td>{esc(it.get('statut') or '—')}</td></tr>"
                       for it in perm["items"][:10])
        body += (f"<h3>Permis de construire voisins (SITADEL) {s('S')}</h3>"
                 f"<table><tr><th>Date</th><th>Type</th><th class='n'>Distance</th><th>Statut</th></tr>{rows}</table>")
    return body


def risques(out: dict) -> str:
    rap = out.get("rapport") or {}
    risq, pat = rap.get("risques") or {}, rap.get("patrimoine") or {}
    items = []
    for it in risq.get("couches", []):
        items.append(("Risque", it["label"], it.get("detail")))
    for it in pat.get("couches", []):
        items.append(("Servitude", it["label"], it.get("detail")))
    for m in pat.get("abf", []):
        items.append(("Patrimoine", "Abords de monument historique (~500 m)", m.get("name")))
    zan = out.get("zan")
    body = "<div class='pb'></div><h2>Risques, servitudes & sobriété foncière</h2>"
    if items:
        rows = "".join(f"<tr><td>{esc(t)}</td><td>{esc(lbl)}</td><td>{esc(d or 'parcelle concernée')}</td></tr>"
                       for t, lbl, d in items)
        body += f"<table><tr><th>Nature</th><th>Élément</th><th>Détail</th></tr>{rows}</table>"
    else:
        body += "<p class='note'>Aucune servitude ni risque connu dans les couches analysées (à confirmer).</p>"
    if zan:
        c2 = zan.get("conso_2021_2024_m2")
        body += (f"<h3>ZAN — consommation d'espaces (commune) {s('S')}</h3>"
                 f"<table><tr><th>Période</th><th class='n'>ENAF consommé</th></tr>"
                 f"<tr><td>2011–2021</td><td class='n'>{esc(round(zan['conso_2011_2021_m2']/10000, 1) if zan.get('conso_2011_2021_m2') else '—')} ha</td></tr>"
                 f"<tr><td>2021–2024</td><td class='n'>{esc(round(c2/10000, 1) if c2 else '—')} ha</td></tr></table>"
                 f"<p class='note'>Source {esc(zan.get('source_nom'))} ({esc(zan.get('millesime'))}) · "
                 f"objectif loi Climat/TRACE = −50 % de consommation d'ENAF. Voir la fiche commune pour budget/reste.</p>")
    return body


# ───────────────────────── rendu ─────────────────────────

def render_pdf(sections: list[str], libelle: str, *, produit: str = "",
               idu: str = "", commune: str = "") -> bytes:
    """Assemble les sections non vides et rend le PDF. C7 : le bandeau de contexte
    (« LABUSE — produit · IDU — commune ») court sur CHAQUE page (sauf la garde,
    qui porte le wordmark graphique — même règle que le Flash)."""
    from weasyprint import HTML
    css = page_css(libelle, produit=produit, idu=idu, commune=commune)
    doc = (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><style>{css}</style></head>"
           f"<body>{''.join(sec for sec in sections if sec)}</body></html>")
    return HTML(string=doc).write_pdf()
