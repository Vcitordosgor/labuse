"""Bilan promoteur (PARTIE 1) : potentiel ÉCONOMIQUE d'une parcelle.

À partir de la faisabilité (surface habitable vendable) et du DVF local (prix de vente
au m² réel, par rayon), estime en FOURCHETTES :
  - le CHIFFRE D'AFFAIRES potentiel (surface vendable × prix DVF) ;
  - la CHARGE FONCIÈRE acceptable (bilan promoteur À REBOURS simplifié : CA − coûts de
    construction − marge − frais annexes), càd ce que le terrain peut « supporter ».

Aucun chiffre présenté comme certain : prix SOURCÉ (DVF), reste en hypothèses signalées
et configurables. Si le DVF local est trop maigre → on le DIT, on n'invente pas de prix.
Aucune dépendance à la cascade/scoring.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from .engine import Hypotheses, Step

_BANDEAU = ("Estimation économique indicative (DVF public + hypothèses) — "
            "ne remplace pas un bilan promoteur professionnel.")


@dataclass
class Bilan:
    fiable: bool
    verdict: str
    prix_dvf: dict | None
    ca: dict | None
    charge_fonciere: dict | None
    steps: list[Step] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    bandeau: str = _BANDEAU


def _eur(x: float) -> str:
    """Format lisible : €, k€, M€."""
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x / 1_000_000:.1f} M€"
    if ax >= 1_000:
        return f"{x / 1_000:.0f} k€"
    return f"{x:.0f} €"


def sector_price(db: Session, parcel_id: int, hyp: Hypotheses) -> dict:
    """Prix de vente €/m² HABITABLE des ventes appart./maison DVF dans un rayon.
    fiable=False si trop peu de ventes (on ne fabrique pas de prix)."""
    rows = db.execute(text(
        "SELECT d.valeur_fonciere / d.surface_reelle_bati AS prix "
        "FROM dvf_mutations d, parcels p "
        "WHERE p.id = :pid AND d.surface_reelle_bati >= 20 AND d.valeur_fonciere > 20000 "
        "AND d.nature_mutation ILIKE '%vente%' "
        "AND d.type_local ILIKE ANY(ARRAY['%APPARTEMENT%','%MAISON%']) "
        "AND ST_DWithin(d.geom::geography, p.centroid::geography, :r)"),
        {"pid": parcel_id, "r": hyp.dvf_radius_m}).scalars().all()
    prices = sorted(float(x) for x in rows if x)
    n = len(prices)
    base = {"n": n, "radius_m": hyp.dvf_radius_m}
    if n < hyp.dvf_min_ventes:
        return {**base, "fiable": False}
    q1, _med, q3 = statistics.quantiles(prices, n=4)
    return {**base, "fiable": True, "q1": round(q1), "median": round(statistics.median(prices)),
            "q3": round(q3)}


def compute_bilan(shab_vendable_m2: float, surface_terrain_m2: float,
                  prix: dict, hyp: Hypotheses) -> Bilan:
    """Cœur pur du bilan (testable sans DB)."""
    steps: list[Step] = []
    hypotheses: list[str] = []
    avert: list[str] = []

    if not prix.get("fiable"):
        return Bilan(False,
                     f"DVF local trop maigre ({prix['n']} vente(s) dans {prix['radius_m']:.0f} m) "
                     "— prix de vente non fiable : bilan non chiffré (on n'invente pas de prix).",
                     prix, None, None, avertissements=[
                         f"Seulement {prix['n']} ventes comparables (< {hyp.dvf_min_ventes}) → "
                         "prix DVF jugé non fiable ici."])
    if shab_vendable_m2 <= 0:
        return Bilan(False, "Surface vendable nulle (parcelle non constructible) — pas de bilan.",
                     prix, None, None)

    q1, med, q3 = prix["q1"], prix["median"], prix["q3"]
    surf = shab_vendable_m2

    steps.append(Step("Surface habitable vendable", "issue de la faisabilité (post-rendement, plafond, modulation)",
                      f"~{surf:.0f} m²", "faisabilité"))
    steps.append(Step("Prix de vente (DVF secteur)",
                      f"{prix['n']} ventes appart./maison dans {prix['radius_m']:.0f} m",
                      f"{q1}–{q3} €/m² (médiane {med})", f"DVF Région ODS, rayon {prix['radius_m']:.0f} m"))

    ca_bas, ca_cen, ca_haut = surf * q1, surf * med, surf * q3
    steps.append(Step("Chiffre d'affaires potentiel", f"{surf:.0f} m² × {q1}–{q3} €/m²",
                      f"~{_eur(ca_bas)} – {_eur(ca_haut)} (médiane {_eur(ca_cen)})", "dérivé"))

    cc_bas, cc_haut = surf * hyp.cout_construction_m2_bas, surf * hyp.cout_construction_m2_haut
    steps.append(Step("Coût de construction",
                      f"{surf:.0f} m² × {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m²",
                      f"~{_eur(cc_bas)} – {_eur(cc_haut)}", "hypothèse coût"))
    coef = 1.0 - hyp.marge_promoteur_pct - hyp.frais_annexes_pct
    steps.append(Step("Marge promoteur + frais annexes",
                      f"marge {hyp.marge_promoteur_pct:.0%} + frais {hyp.frais_annexes_pct:.0%} du CA",
                      "déduits du CA", "hypothèse"))

    # Charge foncière à rebours : CA×(1−marge−frais) − coût construction
    cf_bas = ca_bas * coef - cc_haut          # prix bas + coût haut
    cf_cen = ca_cen * coef - (cc_bas + cc_haut) / 2
    cf_haut = ca_haut * coef - cc_bas         # prix haut + coût bas
    par_m2 = cf_cen / surface_terrain_m2 if surface_terrain_m2 else 0.0
    steps.append(Step("Charge foncière acceptable (bilan à rebours)",
                      f"CA×(1−{hyp.marge_promoteur_pct:.0%}−{hyp.frais_annexes_pct:.0%}) − coût construction",
                      f"~{_eur(cf_bas)} – {_eur(cf_haut)} (médiane {_eur(cf_cen)} ≈ {par_m2:.0f} €/m² de terrain)",
                      "dérivé"))

    hypotheses += [
        f"Coût de construction supposé {hyp.cout_construction_m2_bas:.0f}–{hyp.cout_construction_m2_haut:.0f} €/m² habitable.",
        f"Marge promoteur supposée {hyp.marge_promoteur_pct:.0%} du CA ; frais annexes {hyp.frais_annexes_pct:.0%}.",
        f"Prix de vente = ventes DVF réelles (appart./maison) dans {hyp.dvf_radius_m:.0f} m, fourchette Q1–Q3.",
    ]
    if cf_bas < 0:
        avert.append("Charge foncière NÉGATIVE en bas de fourchette : aux prix bas / coûts hauts, "
                     "l'opération ne dégage pas de valeur pour le terrain.")

    verdict = (f"CA ~{_eur(ca_bas)}–{_eur(ca_haut)} · "
               f"charge foncière ~{_eur(max(0, cf_bas))}–{_eur(cf_haut)} "
               f"(médiane ~{_eur(cf_cen)})")
    return Bilan(True, verdict, prix,
                 {"bas": round(ca_bas), "central": round(ca_cen), "haut": round(ca_haut)},
                 {"bas": round(cf_bas), "central": round(cf_cen), "haut": round(cf_haut),
                  "par_m2_terrain": round(par_m2)},
                 steps, hypotheses, avert)
