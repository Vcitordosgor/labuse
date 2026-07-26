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
    kpis.append(f"<div class='kpi'><span class='v'>{p['surface_m2']:.0f} m²</span>"
                f"<span class='l'>Terrain · Sourcé</span></div>")
    if calc.get("calculable"):
        cf = calc["prix_achat_max"]
        phrases.append(
            f"Au regard des règles applicables{f' (zone {zone})' if zone else ''} et du marché "
            f"observé ({prix.get('n', '?')} ventes DVF, fiabilité {prix.get('fiabilite', '?')}), "
            f"la charge foncière supportable — ce que l'opération peut payer le terrain — "
            f"s'établit entre {eur(cf['bas'])} et {eur(cf['haut'])} (médiane {eur(cf['central'])}, "
            f"selon les hypothèses de coût et de marge rappelées en partie 5).")
        kpis.append(f"<div class='kpi'><span class='v'>{eur(cf['central'])}</span>"
                    f"<span class='l'>Prix d'achat max (médiane) · Estimé</span></div>")
        e = calc.get("ecart_negociation")
        if e:
            kpis.append(f"<div class='kpi'><span class='v'>{eur(e['prix_demande_eur'])}</span>"
                        f"<span class='l'>Prix demandé · saisi</span></div>")
            if e["sens"] == "surcout":
                phrases.append(
                    f"Le prix demandé ({eur(e['prix_demande_eur'])}) excède ce maximum de "
                    f"{eur(e['demande_moins_max_eur'])} (+{e['demande_moins_max_pct']} %) : "
                    f"l'écart constitue la base factuelle d'une contre-proposition.")
                kpis.append(f"<div class='kpi'><span class='v'>+{eur(e['demande_moins_max_eur'])}</span>"
                            f"<span class='l'>Écart demandé − max · dérivé</span></div>")
            else:
                phrases.append(
                    f"Le prix demandé ({eur(e['prix_demande_eur'])}) s'inscrit sous ce maximum "
                    f"(marge {eur(abs(e['demande_moins_max_eur']))}) : l'opération reste "
                    f"finançable à ce prix selon ces hypothèses.")
    else:
        phrases.append("La charge foncière supportable n'est pas chiffrable sur cette parcelle "
                       f"({esc(calc.get('raison') or 'données insuffisantes')}) — l'argumentaire "
                       "se limite aux faits qualitatifs des parties suivantes.")
    return (f"<h1>Argumentaire de négociation foncière</h1>"
            f"<p class='cover-sub'>Parcelle {esc(p['idu'])} — {esc(p['commune'])} · "
            f"section {esc(p['section'])} n° {esc(p['numero'])}</p>"
            f"<div class='bandeau'>{LIBELLE}</div>"
            f"<h2>1 · Synthèse</h2>"
            f"<div class='exec'>{esc(' '.join(phrases))}</div>"
            f"<div style='margin-top:4mm;'>{''.join(kpis)}</div>"
            f"<h2>Situation</h2>{bq.map_html(p['geojson'], ign=True)}")


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
    body = ("<div class='pb'></div><h2>5 · Le bilan à rebours — du prix de sortie au foncier</h2>"
            f"<p class='note'>Hypothèses saisies (jamais estimées par LABUSE) : coût de construction "
            f"{hyp['cout_m2']:g} €/m² de plancher · marge & frais {hyp['marge_pct']:g} % du CA. "
            f"Les valeurs sourcées (surface vendable, prix DVF) viennent du moteur.</p>")
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
    sections = [_synthese(out), marche, permet, _reductions(out),
                _bilan_rebours(out), _vigilance(out), _sources(out)]
    pdf = bq.render_pdf(sections, LIBELLE)
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
