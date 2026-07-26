"""M22-C — ARGUMENTAIRE DE NÉGOCIATION : la contre-offre démontrée, chiffres sourcés.

Scénario : le promoteur a une parcelle en vue, le propriétaire demande un prix. Ce PDF
(5-7 pages, briques M22-0, thème clair) démontre ce que le foncier peut SUPPORTER — et
fonde une contre-offre. Doctrine actée par Vic (mandat M22) :
 · le raisonnement passe par la CHARGE FONCIÈRE SUPPORTABLE (bilan à rebours, mode
   inverse M22-A), JAMAIS par des « décotes % sur le prix affiché » ;
 · ce qui n'est pas chiffrable (viabilisation, servitudes hors PPR, risques « à
   étudier ») apparaît en POINTS DE VIGILANCE qualitatifs — jamais en euros ;
 · ton factuel, vérifiable, jamais dénigrant : le document doit pouvoir être MONTRÉ
   AU VENDEUR sans embarras — c'est sa force.

Structure : 1 synthèse (prix demandé vs prix d'achat max, écart) · 2 le marché réel
(DVF, fiabilité affichée telle quelle) · 3 ce que le terrain permet (faisabilité, articles)
· 4 ce qui réduit la capacité (modulations CHIFFRABLES, en réductions de SDP/capacité)
· 5 le bilan à rebours ligne à ligne (→ foncier max) · 6 points de vigilance (sans euros)
· 7 sources et millésimes.

Entrée : IDU + prix demandé (optionnel) + hypothèses calculette (mêmes défauts que M15-C2).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from . import briques_pdf as bq
from .briques_pdf import esc, eur, s

log = logging.getLogger("labuse.argumentaire")
router = APIRouter(prefix="/argumentaire", tags=["argumentaire"])

LIBELLE = ("Argumentaire de négociation établi à partir de données publiques (cadastre, DVF, PLU) "
           "et des hypothèses saisies — estimation indicative, ni un prix ni une promesse ; "
           "ne vaut pas conseil. À vérifier par l'acquéreur et ses conseils.")


def get_db():
    from .app import get_db as _g
    yield from _g()


# ───────────────────────── assemblage ─────────────────────────

def _collect(db: Session, idu: str, cout_m2: float, marge_pct: float,
             prix_demande: float | None) -> dict:
    """Briques banquier (bq.collect) + calculette en MODE INVERSE (M22-A) + viabilisation."""
    from ..faisabilite.bilan import compute_calculette
    out = bq.collect(db, idu)
    p = out["parcelle"]
    fais = out.get("faisabilite")
    shab = (fais.fourchette or {}).get("shab_vendable_m2") if fais else None
    prix = out.get("prix_dvf")
    if shab and prix:
        out["calc"] = compute_calculette(float(shab), float(p["surface_m2"] or 0), prix,
                                         cout_m2, marge_pct, prix_demande, mode="achat_max")
    else:
        out["calc"] = {"calculable": False,
                       "raison": "capacité constructible ou prix de sortie non résolus"}
    out["hyp_saisies"] = {"cout_m2": cout_m2, "marge_pct": marge_pct}
    try:
        from .app import _viabilisation_block
        out["viab"] = _viabilisation_block(db, idu)
    except Exception as exc:  # noqa: BLE001
        log.warning("viabilisation %s : %s", idu, exc)
        out["viab"] = None
    return out


# ───────────────────────── dataviz C9 (SVG inline, DA existante) ─────────────────────────

def _svg_bande_points(prix: dict) -> str:
    """C9 — les ventes DVF en BANDE DE POINTS : chaque vente retenue = un point (aucune
    agrégation nouvelle), médiane marquée. Inter, vert LABUSE, fond clair — DA existante."""
    pts = prix.get("prix_points") or []
    if len(pts) < 5:
        return ""
    lo, hi = min(pts), max(pts)
    if hi <= lo:
        return ""
    W, H, PAD = 640, 74, 34
    x = lambda v: PAD + (W - 2 * PAD) * (v - lo) / (hi - lo)  # noqa: E731
    med = prix.get("median")
    cercles = "".join(
        f"<circle cx='{x(v):.1f}' cy='40' r='3.2' fill='#0B8A5F' fill-opacity='0.45'/>" for v in pts)
    med_svg = (f"<line x1='{x(med):.1f}' y1='16' x2='{x(med):.1f}' y2='58' stroke='#111814' "
               f"stroke-width='1.6'/>"
               f"<text x='{x(med):.1f}' y='12' text-anchor='middle' font-family='Inter' "
               f"font-size='10' fill='#111814'>médiane {med} €/m²</text>") if med else ""
    return (f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
            f"style='background:#F4F8F6;border-radius:6px'>"
            f"<line x1='{PAD}' y1='40' x2='{W - PAD}' y2='40' stroke='#D8E2DC' stroke-width='1'/>"
            f"{cercles}{med_svg}"
            f"<text x='{PAD}' y='68' font-family='Inter' font-size='9' fill='#5F6C65'>{lo} €/m²</text>"
            f"<text x='{W - PAD}' y='68' text-anchor='end' font-family='Inter' font-size='9' "
            f"fill='#5F6C65'>{hi} €/m²</text></svg>"
            f"<p class='note'>Chaque point est une vente DVF retenue dans le comparable "
            f"({len(pts)} ventes) — aucune vente n'est fabriquée ni lissée.</p>")


def _svg_cascade(calc: dict) -> str:
    """C9 — le bilan à rebours en CASCADE : CA → − marge & frais → − construction → − VRD →
    = terrain (prix d'achat max). Valeurs = les termes exacts du moteur (calc), scénario médian."""
    c = calc.get("calc") or {}
    cf = calc.get("prix_achat_max") or {}
    ca = (calc.get("ca") or {}).get("central")
    coef = c.get("coef")
    if not (ca and coef and cf):
        return ""
    marge = ca * (1.0 - float(coef))
    construction = (float(c.get("cc_bas") or 0) + float(c.get("cc_haut") or 0)) / 2
    vrd = float(c.get("cout_vrd") or 0)
    terrain = float(cf.get("central") or 0)
    etapes = [("Chiffre d'affaires", ca, "#0B8A5F"), ("− Marge & frais", -marge, "#A87916"),
              ("− Construction", -construction, "#A87916")]
    if vrd:
        etapes.append(("− VRD", -vrd, "#A87916"))
    etapes.append(("= Terrain (max)", terrain, "#111814"))
    W, H, PAD, BW = 640, 150, 30, 96
    ymax = max(ca, 1.0)
    yh = lambda v: max(2.0, 108.0 * abs(v) / ymax)  # noqa: E731
    bars, cursor = [], 0.0
    for i, (lab, v, col) in enumerate(etapes):
        x0 = PAD + i * ((W - 2 * PAD - BW) / max(1, len(etapes) - 1))
        if i == 0:
            top, cursor = ca, ca
            y0, h = 118 - yh(ca), yh(ca)
        elif lab.startswith("="):
            y0, h = 118 - yh(max(terrain, 0.0)), yh(max(terrain, 0.0))
        else:
            nouveau = cursor + v
            y0, h = 118 - yh(cursor) , yh(v)
            cursor = nouveau
        bars.append(
            f"<rect x='{x0:.1f}' y='{y0:.1f}' width='{BW}' height='{h:.1f}' rx='3' "
            f"fill='{col}' fill-opacity='{0.85 if lab.startswith(('Chiffre', '=')) else 0.35}'/>"
            f"<text x='{x0 + BW / 2:.1f}' y='132' text-anchor='middle' font-family='Inter' "
            f"font-size='8.6' fill='#5F6C65'>{lab}</text>"
            f"<text x='{x0 + BW / 2:.1f}' y='{max(y0 - 4, 10):.1f}' text-anchor='middle' "
            f"font-family='Inter' font-size='9' fill='#111814'>{eur(abs(v))}</text>")
    return (f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
            f"style='background:#F4F8F6;border-radius:6px'>"
            f"<line x1='{PAD}' y1='118' x2='{W - PAD}' y2='118' stroke='#D8E2DC' stroke-width='1'/>"
            f"{''.join(bars)}</svg>"
            f"<p class='note'>Cascade du scénario médian — mêmes termes que le tableau ci-dessus "
            f"(aucun recalcul) ; les scénarios bas/haut suivent la fourchette DVF.</p>")


# ───────────────────────── sections ─────────────────────────

def _synthese(out: dict) -> str:
    """Page 1 — LES chiffres de la négociation, ton factuel (montrable au vendeur)."""
    p = out["parcelle"]
    calc = out["calc"]
    fais = out.get("faisabilite")
    # zone_resolue peut porter le renvoi complet (« AU2c → règles de U2c (…) ») : trop verbeux
    # pour une phrase de synthèse — on garde le CODE (le détail vit dans la partie 3).
    zone = (fais.zone_resolue or fais.zone) if fais else None
    if zone and len(str(zone)) > 12:
        zone = str(fais.zone) if fais and fais.zone else str(zone).split(" ", 1)[0]
    prix = out.get("prix_dvf") or {}
    phrases: list[str] = []
    kpis: list[str] = []
    if calc.get("calculable"):
        cf = calc["prix_achat_max"]
        # C3 — borne basse à 0 INTERDITE dans la phrase : si le scénario bas ne supporte
        # rien, on le DIT (honnêteté) au lieu d'écrire « entre 0 € et X ».
        if cf["bas"] <= 0:
            fourchette_txt = (f"s'établit à {eur(cf['central'])} en médiane (haut de fourchette "
                              f"{eur(cf['haut'])}) ; dans le scénario bas, l'opération ne "
                              f"supporte aucune charge foncière")
        else:
            fourchette_txt = (f"s'établit entre {eur(cf['bas'])} et {eur(cf['haut'])} "
                              f"(médiane {eur(cf['central'])})")
        phrases.append(
            f"Au regard des règles applicables{f' (zone {zone})' if zone else ''} et du marché "
            f"observé ({prix.get('n', '?')} ventes DVF, fiabilité {prix.get('fiabilite', '?')}), "
            f"la charge foncière supportable — ce que l'opération peut payer le terrain — "
            f"{fourchette_txt}, selon les hypothèses de coût et de marge rappelées en partie 5.")
        # C6 — le chiffre-héros : le prix d'achat max se voit à 2 mètres
        kpis.append(bq.cartouche("Prix d'achat max (médiane) · Estimé", eur(cf["central"]),
                                 hero=True))
        kpis.append(bq.cartouche("Terrain · Sourcé", f"{p['surface_m2']:.0f} m²"))
        e = calc.get("ecart_negociation")
        if e:
            kpis.append(bq.cartouche("Prix demandé · saisi", eur(e["prix_demande_eur"])))
            if e["sens"] == "surcout":
                phrases.append(
                    f"Le prix demandé ({eur(e['prix_demande_eur'])}) excède ce maximum de "
                    f"{eur(e['demande_moins_max_eur'])} (+{e['demande_moins_max_pct']} %) : "
                    f"l'écart constitue la base factuelle d'une contre-proposition.")
                kpis.append(bq.cartouche("Écart demandé − max · dérivé",
                                         f"+{eur(e['demande_moins_max_eur'])}"))
            else:
                phrases.append(
                    f"Le prix demandé ({eur(e['prix_demande_eur'])}) s'inscrit sous ce maximum "
                    f"(marge {eur(abs(e['demande_moins_max_eur']))}) : l'opération reste "
                    f"finançable à ce prix selon ces hypothèses.")
    else:
        kpis.append(bq.cartouche("Terrain · Sourcé", f"{p['surface_m2']:.0f} m²"))
        phrases.append("La charge foncière supportable n'est pas chiffrable sur cette parcelle "
                       f"({esc(calc.get('raison') or 'données insuffisantes')}) — l'argumentaire "
                       "se limite aux faits qualitatifs des parties suivantes.")
    return (f"<section class='garde'>"
            f"{bq.garde_entete(p, produit_sous_titre='ARGUMENTAIRE DE NÉGOCIATION · contre-offre fondée', titre='Argumentaire de négociation foncière', bandeau=LIBELLE)}"
            f"<h2>1 · Synthèse</h2>"
            f"<div class='exec'>{esc(' '.join(phrases))}</div>"
            f"{bq.cartouches(kpis)}"
            f"<h2>Situation</h2>{bq.map_html(p['geojson'])}</section>")


def _reductions(out: dict) -> str:
    """4 — CE QUI RÉDUIT LA CAPACITÉ : les modulations CHIFFRABLES du moteur (pente, PPR,
    littoral, SAR), présentées comme réductions de capacité constructible — JAMAIS comme
    des « décotes » sur le prix affiché (doctrine Vic)."""
    fais = out.get("faisabilite")
    modul = list(fais.modulation or []) if fais else []
    body = ("<h2>4 · Ce qui réduit la capacité constructible</h2>"
            "<p class='note'>Les facteurs ci-dessous réduisent la SURFACE CONSTRUCTIBLE (donc le "
            "chiffre d'affaires possible, donc la charge foncière supportable). Ils ne sont jamais "
            "présentés comme des rabais sur le prix affiché : c'est la capacité qui baisse, "
            "le calcul de la partie 5 en tient compte.</p>")
    if modul:
        rows = "".join(f"<tr><td>{esc(m)}</td><td>{s('S') if 'PPR' in m or 'SAR' in m or 'côte' in m else s('E')}</td></tr>"
                       for m in modul)
        body += f"<table><tr><th>Facteur (appliqué au calcul)</th><th>Nature</th></tr>{rows}</table>"
        body += ("<p class='note'>Sources : PPR/aléas (DEAL), SAR (PEIGEO), trait de côte (Cerema), "
                 "pente (RGE ALTI 5 m) — telles qu'ingérées ; le détail figure dans la dérivation "
                 "de la partie 3.</p>")
    else:
        body += ("<p class='note'>Aucune réduction chiffrable appliquée par le moteur dans les "
                 "couches analysées — ce constat ne couvre pas les contraintes non modélisées "
                 "(voir points de vigilance, partie 6).</p>")
    return body


def _bilan_rebours(out: dict) -> str:
    """5 — LE BILAN À REBOURS ligne à ligne (mode inverse M22-A) → prix d'achat max."""
    calc = out["calc"]
    hyp = out["hyp_saisies"]
    # C1 — le MÊME encadré d'hypothèses que le Dossier banquier (forme identique)
    body = ("<div class='pb'></div><h2>5 · Le bilan à rebours — du prix de sortie au foncier</h2>"
            + bq.hypotheses_encadre(hyp["cout_m2"], hyp["marge_pct"]))
    if not calc.get("calculable"):
        return body + ("<p class='note'>Non chiffrable : "
                       f"{esc(calc.get('raison') or 'données insuffisantes')} — aucun chiffre "
                       "n'est fabriqué (doctrine).</p>")
    rows = "".join(
        f"<tr><td>{esc(st['label'])}</td><td>{esc(st['formule'])}</td>"
        f"<td class='n'>{esc(st['valeur'])}</td>"
        f"<td>{s({'sourcee': 'S', 'estimee': 'E'}.get(st.get('prov'), 'E'))}</td></tr>"
        for st in calc.get("steps", []))
    body += (f"<table><tr><th>Étape</th><th>Calcul</th><th class='n'>Valeur</th><th>Nature</th></tr>"
             f"{rows}</table>")
    cf = calc["prix_achat_max"]
    body += (f"<h3>Prix d'achat maximal admissible {s('E')}</h3>"
             f"<table><tr><th class='n'>Bas</th><th class='n'>Médiane</th><th class='n'>Haut</th>"
             f"<th class='n'>Par m² terrain</th></tr>"
             f"<tr><td class='n'>{eur(cf['bas'])}</td><td class='n'><b>{eur(cf['central'])}</b></td>"
             f"<td class='n'>{eur(cf['haut'])}</td>"
             f"<td class='n'>{esc(cf.get('par_m2_terrain'))} €/m²</td></tr></table>")
    # C9 — le même bilan, en cascade (CA → coûts → marge → terrain), scénario médian
    cascade = _svg_cascade(calc)
    if cascade:
        body += f"<h3>Le même calcul, en un coup d'œil</h3>{cascade}"
    e = calc.get("ecart_negociation")
    if e:
        if e["sens"] == "surcout":
            body += (f"<p><b>Écart de négociation :</b> prix demandé {eur(e['prix_demande_eur'])} "
                     f"− prix d'achat max {eur(e['prix_achat_max_eur'])} = "
                     f"<b>{eur(e['demande_moins_max_eur'])} au-dessus du max admissible "
                     f"(+{e['demande_moins_max_pct']} %)</b>.</p>")
        else:
            body += (f"<p><b>Écart :</b> prix demandé {eur(e['prix_demande_eur'])} sous le max "
                     f"admissible ({eur(e['prix_achat_max_eur'])}) — marge "
                     f"{eur(abs(e['demande_moins_max_eur']))}.</p>")
    for a in calc.get("avertissements", []):
        body += f"<p class='note'>{esc(a)}</p>"
    return body


def _vigilance(out: dict) -> str:
    """6 — POINTS DE VIGILANCE : qualitatifs, SANS euros (doctrine, test l'atteste).
    Formulation neutre : coûts ou délais potentiels POUR TOUT ACQUÉREUR."""
    body = ("<div class='pb'></div><h2>6 · Points de vigilance (non chiffrés)</h2>"
            "<p class='note'>Éléments non chiffrables en l'état — ce sont des coûts ou délais "
            "potentiels pour TOUT acquéreur de cette parcelle, pas des arguments à charge. "
            "Aucun montant n'est avancé : chacun relève d'un devis ou d'une étude.</p>")
    viab = out.get("viab")
    if viab:
        cr = viab.get("cout_raccordement") or {}
        body += (f"<h3>Viabilisation et raccordements</h3>"
                 f"<p>Indicateur de viabilisation : <b>{esc(viab.get('score'))}/100</b> — "
                 f"{esc(viab.get('libelle'))}.</p>"
                 f"<p class='note'>{esc(cr.get('niveau'))}</p>"
                 f"<p class='note'>{esc(cr.get('assainissement'))}</p>")
    rap = out.get("rapport") or {}
    items = []
    for it in (rap.get("risques") or {}).get("couches", []):
        items.append(("Risque cartographié", it.get("label"), it.get("detail")))
    for it in (rap.get("patrimoine") or {}).get("couches", []):
        items.append(("Servitude / protection", it.get("label"), it.get("detail")))
    for m in (rap.get("patrimoine") or {}).get("abf", []) or []:
        items.append(("Patrimoine", "Abords de monument historique (~500 m) — avis ABF probable",
                      m.get("name")))
    if items:
        rows = "".join(f"<tr><td>{esc(t)}</td><td>{esc(l)}</td><td>{esc(d or 'parcelle concernée')}</td></tr>"
                       for t, l, d in items)
        body += (f"<h3>Servitudes et risques à instruire</h3>"
                 f"<table><tr><th>Nature</th><th>Élément</th><th>Détail</th></tr>{rows}</table>")
    else:
        body += ("<p class='note'>Aucun élément dans les couches numérisées — ce constat ne vaut "
                 "pas absence de contrainte (seul l'ingéré est vérifié).</p>")
    return body


def _sources(out: dict) -> str:
    rap = out.get("rapport") or {}
    rows = "".join(f"<tr><td>{esc(x.get('source'))}</td><td>{esc(x.get('millesime'))}</td></tr>"
                   for x in (rap.get("sources") or []))
    if not rows:
        return ""
    return (f"<h2>7 · Sources et millésimes</h2>"
            f"<table><tr><th>Source</th><th>Millésime / synchronisation</th></tr>{rows}</table>"
            f"<p class='note'>DVF : ventes publiées (Etalab/DGFiP) ; PLU : règlement calibré cité "
            f"dans la dérivation ; hypothèses économiques : saisies par l'utilisateur.</p>")


# ───────────────────────── endpoint ─────────────────────────

def _build_pdf(db: Session, idu: str, cout_m2: float, marge_pct: float,
               prix_demande: float | None) -> bytes:
    out = _collect(db, idu, cout_m2, marge_pct, prix_demande)
    # renumérotation visuelle des sections briques (2 et 3) via leurs titres d'origine
    marche = bq.comparables(out).replace("<h2>Marché de comparaison</h2>",
                                         "<h2>2 · Le marché réel (DVF)</h2>")
    permet = bq.faisabilite(out).replace("<h2>Faisabilité — dérivation détaillée</h2>",
                                         "<h2>3 · Ce que le terrain permet</h2>")
    # C9 — la bande de points DVF complète le tableau du marché (chaque vente = un point)
    strip = _svg_bande_points(out.get("prix_dvf") or {})
    if strip:
        marche += f"<h3>Les ventes retenues, une à une</h3>{strip}"
    sections = [_synthese(out), marche, permet, _reductions(out),
                _bilan_rebours(out), _vigilance(out), _sources(out)]
    # C7 : bandeau de contexte sur chaque page
    pdf = bq.render_pdf(sections, LIBELLE, produit="Argumentaire de négociation",
                        idu=idu, commune=out["parcelle"].get("commune") or "")
    log.info("argumentaire %s généré (%d ko)", idu, len(pdf) // 1024)
    return pdf


@router.get("/{idu}.pdf")
def argumentaire_pdf(idu: str,
                     prix_demande_eur: float | None = Query(None, ge=0, le=500_000_000),
                     cout_construction_m2: float = Query(2500.0, ge=500, le=8000),
                     marge_frais_pct: float = Query(21.0, ge=0, le=60),
                     db: Session = Depends(get_db)) -> Response:
    """Sert l'argumentaire de négociation (synchrone). Hypothèses = celles de la calculette."""
    pdf = _build_pdf(db, idu, cout_construction_m2, marge_frais_pct, prix_demande_eur)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="argumentaire_{idu}.pdf"'})
