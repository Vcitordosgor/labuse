"""M22-0 — BRIQUES PDF PARTAGÉES (thème clair d'impression).

Sections extraites du Dossier banquier (O1, `banquier.py`) pour être réutilisées par les
exports M22 (lettre de zonage, argumentaire de négociation, rapport de potentiel) SANS
tripliquer le HTML inline. Le Banquier reste la référence visuelle : tout changement ici
doit laisser son PDF strictement identique (preuve avant/après : qa/m22/0/).

Contenu :
 · `PAGE_CSS` + `page_css(libelle)` — thème clair print A4, pied de page légal ;
 · helpers `s` (puce Sourcé/Estimé/Absent), `eur`, `esc` ;
 · `collect(db, idu)` — assemblage des briques de données (chaque section optionnelle
   et guardée : une donnée absente devient None, jamais un chiffre inventé) ;
 · `map_html` — photo aérienne / plan de situation (IGN, cache tuiles) ;
 · sections : `cover`, `identite`, `faisabilite`, `bilan`, `comparables`, `risques` ;
 · `render_pdf(sections, libelle)` — HTML → WeasyPrint.

Doctrine (inchangée) : jamais un RR ni un score interne en vitrine ; chaque chiffre porte
Sourcé/Estimé ; « non estimable » quand une donnée manque ; particulier jamais nommé.
"""
from __future__ import annotations

import html
import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.briques_pdf")

PAGE_CSS = """
@page {{ size: A4; margin: 15mm 15mm 18mm;
  @bottom-center {{ content: "{libelle}"; font-family: sans-serif; font-size: 6pt; color: #8892908c; }}
  @bottom-right {{ content: "p. " counter(page) "/" counter(pages); font-family: sans-serif;
    font-size: 7pt; color: #889290; }} }}
body {{ font-family: sans-serif; color: #26302B; font-size: 9.7pt; line-height: 1.42; }}
h1 {{ font-size: 20pt; color: #0B120E; margin: 0 0 1mm; }}
h2 {{ font-size: 12.5pt; color: #0B120E; border-bottom: 1.2pt solid #0B8A5F; padding-bottom: 1.5mm;
  margin: 7mm 0 2.5mm; page-break-after: avoid; }}
h3 {{ font-size: 10pt; color: #35423B; margin: 4mm 0 1mm; }}
table {{ width: 100%; border-collapse: collapse; margin: 1mm 0; }}
td, th {{ border-bottom: 0.5pt solid #DCE5E0; padding: 1.5mm 2mm 1.5mm 0; text-align: left;
  font-size: 8.6pt; vertical-align: top; }}
th {{ color: #5F6C65; text-transform: uppercase; font-size: 6.8pt; letter-spacing: 0.3pt;
  border-bottom: 0.8pt solid #0B8A5F; }}
td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.note {{ font-size: 7.6pt; color: #6B7772; }}
.src {{ font-size: 6.6pt; text-transform: uppercase; letter-spacing: 0.3pt; padding: 0.2mm 1.2mm;
  border-radius: 1mm; white-space: nowrap; }}
.src-s {{ background: #DFF3EA; color: #0B6A48; }}   /* Sourcé */
.src-e {{ background: #FFF2D6; color: #7A5A12; }}   /* Estimé */
.src-a {{ background: #EFEFEF; color: #767676; }}   /* Absent / non estimable */
.kpi {{ display: inline-block; margin: 1mm 6mm 2mm 0; }}
.kpi .v {{ font-size: 16pt; font-weight: 700; color: #0B120E; display: block; }}
.kpi .l {{ font-size: 7.4pt; color: #6B7772; text-transform: uppercase; letter-spacing: 0.3pt; }}
.exec {{ background: #F5FAF8; border-left: 2.5pt solid #0B8A5F; padding: 3mm 4mm; border-radius: 0 1.5mm 1.5mm 0;
  font-size: 9.4pt; }}
.bandeau {{ background: #FFF6DE; border-radius: 1.5mm; padding: 2.5mm 3.5mm; font-size: 7.8pt;
  color: #7A5A12; margin: 2mm 0 4mm; }}
.cover-sub {{ color: #5F6C65; font-size: 10.5pt; margin: 0 0 3mm; }}
.map {{ border: 0.8pt solid #DCE5E0; border-radius: 1.5mm; overflow: hidden; }}
.pb {{ page-break-before: always; }}
"""


def page_css(libelle: str) -> str:
    """CSS de page prêt à inliner — le libellé légal va au pied de CHAQUE page."""
    return PAGE_CSS.format(libelle=libelle.replace('"', ""))


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


# ───────────────────────── assemblage données (réutilise l'existant) ─────────────────────────

def collect(db: Session, idu: str) -> dict:
    """Rassemble toutes les briques du dossier. Chaque section est optionnelle et guardée :
    une donnée absente devient None (la page l'omet proprement), jamais un chiffre inventé."""
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
        from ..faisabilite.bilan import sector_price, compute_bilan
        from ..faisabilite.engine import Hypotheses
        fa = parcel_faisabilite(db, pid)
        if fa:
            ctx, fais = fa
            out["faisabilite"] = fais
            shab = (fais.fourchette or {}).get("shab_vendable_m2")
            if shab and shab > 0:
                hyp = Hypotheses()
                prix = sector_price(db, pid, hyp)
                out["prix_dvf"] = prix
                out["bilan"] = compute_bilan(float(shab), float(ctx.surface_m2 or 0), prix, hyp)
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
    return out


# ───────────────────────── sections HTML ─────────────────────────

def map_html(geojson: str, ign: bool) -> str:
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


def cover(out: dict, *, titre: str = "Dossier foncier", bandeau: str = "",
          synthese_titre: str = "Synthèse exécutive") -> str:
    """Couverture : titre, référence parcelle, bandeau légal, synthèse (si `out['_synthese']`),
    KPI disponibles, plan de situation. Les défauts reproduisent le Banquier à l'identique."""
    p = out["parcelle"]
    photo = map_html(p["geojson"], ign=True)
    kpis = []
    kpis.append(f"<div class='kpi'><span class='v'>{p['surface_m2']:.0f} m²</span>"
                f"<span class='l'>Terrain · Sourcé</span></div>")
    fo = (out.get("faisabilite").fourchette if out.get("faisabilite") else {}) or {}
    if fo.get("shab_vendable_m2"):
        kpis.append(f"<div class='kpi'><span class='v'>~{fo['shab_vendable_m2']:.0f} m²</span>"
                    f"<span class='l'>Surface vendable · Estimé</span></div>")
    bilan_ = out.get("bilan")
    if bilan_ and bilan_.charge_fonciere:
        kpis.append(f"<div class='kpi'><span class='v'>{eur(bilan_.charge_fonciere.get('central'))}</span>"
                    f"<span class='l'>Charge foncière · Estimé</span></div>")
    se = out.get("score_e")
    if se and se["estimable"]:
        kpis.append(f"<div class='kpi'><span class='v'>{eur(se['marge_estimee'])}</span>"
                    f"<span class='l'>Marge estimée · Estimé</span></div>")
    synthese = f"<h2>{esc(synthese_titre)}</h2>{out['_synthese']}" if out.get("_synthese") else ""
    return (f"<h1>{esc(titre)}</h1>"
            f"<p class='cover-sub'>Parcelle {esc(p['idu'])} — {esc(p['commune'])} · "
            f"section {esc(p['section'])} n° {esc(p['numero'])}</p>"
            f"<div class='bandeau'>{bandeau}</div>"
            f"{synthese}"
            f"<div style='margin-top:4mm;'>{''.join(kpis)}</div>"
            f"<h2>Situation</h2>{photo}")


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
    avert = "".join(f"<li>{esc(a)}</li>" for a in (fais.avertissements or []))
    return (f"<div class='pb'></div><h2>Faisabilité — dérivation détaillée</h2>{synth}"
            f"<table><tr><th>Étape</th><th>Calcul</th><th class='n'>Valeur</th><th>Nature</th></tr>{steps}</table>"
            + (f"<p class='note'>Avertissements : <ul>{avert}</ul></p>" if avert else "")
            + f"<p class='note'>{esc(fais.bandeau)}</p>")


def bilan(out: dict) -> str:
    bilan_ = out.get("bilan")
    se = out.get("score_e")
    if bilan_ is None and not se:
        return ""
    body = "<div class='pb'></div><h2>Bilan promoteur & charge foncière</h2>"
    if bilan_ is not None:
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
    if se and se["estimable"]:
        from ..ingestion.score_e import niveau_label
        body += (f"<h3>Score É — marge foncière estimée {s('E')}</h3>"
                 f"<p><b>{eur(se['marge_estimee'])}</b> = charge supportable {eur(se['charge_supportable'])} "
                 f"− prix probable du foncier {eur(se['prix_probable'])} "
                 f"(prix de sortie neuf — {esc(niveau_label(se['niveau_prix']))}).</p>"
                 f"<p class='note'>{esc(se['detail'])}</p>")
    elif se:
        body += f"<h3>Score É</h3><p class='note'>Marge {s('A')} — données de marché insuffisantes.</p>"
    return body


def comparables(out: dict) -> str:
    prix = out.get("prix_dvf")
    perm = out.get("permits")
    if not prix and not perm:
        return ""
    body = "<div class='pb'></div><h2>Marché de comparaison</h2>"
    if prix and prix.get("median"):
        body += (f"<h3>Prix de sortie du secteur (DVF) {s('S')}</h3>"
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

def render_pdf(sections: list[str], libelle: str) -> bytes:
    """Assemble les sections non vides et rend le PDF (WeasyPrint, thème clair)."""
    from weasyprint import HTML
    doc = (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><style>{page_css(libelle)}</style></head>"
           f"<body>{''.join(sec for sec in sections if sec)}</body></html>")
    return HTML(string=doc).write_pdf()
