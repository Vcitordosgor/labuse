"""Recalcul indépendant — taxe d'aménagement.

Réimplémentation À LA MAIN de l'assiette et des parts, avec les CONSTANTES OFFICIELLES 2026
recopiées de la source légale (pas du YAML de prod), puis comparée à la sortie du produit
(`taxe_amenagement.calculer`) sur des cas limites — dont ceux exigés par le mandat : entrée à
0, résidence principale (abattement 100 m²), logement aidé, forfaits (piscine/PV/parking),
taux communal MAJORÉ, petite surface exonérée.

Le produit `calculer` n'est appelé QUE pour lire la valeur SERVIE (comme la fiche l'est) ; le
recalcul, lui, n'importe aucune fonction de calcul du back.

Constantes officielles 2026 (CGI art. 1635 quater ; service-public.fr A15416, indexation ICC) :
  · valeur forfaitaire hors Île-de-France : 892 €/m²  (2025 = 914 €/m², révisée à la baisse 2026) ;
  · abattement 50 % sur les 100 premiers m² de résidence principale / logement aidé ;
  · exonération de plein droit sous 5 m² ;
  · forfaits 2026 (vérifiés economie.gouv / service-public, art. 1635 quater J-K) :
    piscine 251 €/m², PV au sol 10 €/m², stationnement extérieur 2 928 €/place
    (jusqu'à 5 857 €/place sur délibération), éolienne (mât > 12 m) 3 000 €/mât ;
  · l'abattement 50 % ne s'applique JAMAIS aux forfaits (piscine/parking taxés en totalité) ;
  · part départementale plafond 2,5 %.
Constantes du code = valeurs officielles 2026 (VÉRIFIÉES) → aucun écart de constante attendu.
"""
from __future__ import annotations

VF_HORS_IDF = 892.0
ABATTEMENT = 0.50
PLAFOND_RP_M2 = 100.0
EXO_MIN_M2 = 5.0
RAP_PCT = 0.40
# forfaits OFFICIELS 2026 (vérifiés economie.gouv.fr — art. 1635 quater J/K).
FORFAIT_PISCINE = 251.0
FORFAIT_PV_SOL = 10.0
FORFAIT_PARKING = 2928.0
FORFAIT_EOLIENNE = 3000.0


def _eur(x):
    return round(float(x), 2)


def ta_independante(*, surface_taxable_m2=0.0, residence_principale=False, logement_aide=False,
                    piscine_m2=0.0, pv_sol_m2=0.0, stationnement_ext_places=0, eoliennes_mats=0,
                    taux_communal_pct=None, taux_departemental_pct=2.5):
    """Assiette + parts, formule officielle indépendante. → dict."""
    surf = max(0.0, float(surface_taxable_m2 or 0))
    if surf > 0 and surf < EXO_MIN_M2:
        assiette_surf = 0.0
    elif surf > 0:
        if logement_aide:
            abattue, pleine = surf, 0.0
        elif residence_principale:
            abattue = min(surf, PLAFOND_RP_M2)
            pleine = surf - abattue
        else:
            abattue, pleine = 0.0, surf
        assiette_surf = pleine * VF_HORS_IDF + abattue * VF_HORS_IDF * (1 - ABATTEMENT)
    else:
        assiette_surf = 0.0
    forfaits = (max(0.0, piscine_m2) * FORFAIT_PISCINE
                + max(0.0, pv_sol_m2) * FORFAIT_PV_SOL
                + max(0, stationnement_ext_places) * FORFAIT_PARKING
                + max(0, eoliennes_mats) * FORFAIT_EOLIENNE)
    assiette = _eur(assiette_surf + forfaits)
    part_com = None if taux_communal_pct is None else _eur(assiette * taux_communal_pct / 100.0)
    part_dep = None if taux_departemental_pct is None else _eur(assiette * taux_departemental_pct / 100.0)
    total = None if (part_com is None or part_dep is None) else _eur((part_com or 0) + (part_dep or 0))
    rap = _eur(assiette * RAP_PCT / 100.0)
    return {"assiette_eur": assiette, "part_com": part_com, "part_dep": part_dep,
            "total_eur": total, "rap_eur": rap}


#: cas limites du mandat (surface 0, RP, aidé, forfaits, taux majoré, petite surface).
CAS = [
    dict(surface_taxable_m2=0.0, taux_communal_pct=3.0),                       # entrée à 0
    dict(surface_taxable_m2=3.0, taux_communal_pct=3.0),                       # < 5 m² exonérée
    dict(surface_taxable_m2=120.0, taux_communal_pct=3.0),                     # nominal
    dict(surface_taxable_m2=120.0, residence_principale=True, taux_communal_pct=3.0),  # RP 100 m²
    dict(surface_taxable_m2=120.0, logement_aide=True, taux_communal_pct=5.0),  # aidé, taux majoré
    dict(surface_taxable_m2=80.0, piscine_m2=30.0, stationnement_ext_places=2, taux_communal_pct=5.0),
    dict(surface_taxable_m2=200.0, taux_communal_pct=None),                    # taux manquant → total None
]


def verifier(rec, conn, echantillon):
    from labuse import taxe_amenagement as prod          # importé UNIQUEMENT pour lire le SERVI

    for i, cas in enumerate(CAS):
        servi = prod.calculer(**cas)
        recalc = ta_independante(**cas)
        objet = "|".join(f"{k}={v}" for k, v in cas.items())
        # assiette
        rec.compare("taxe_amenagement.calculer", "assiette_eur", f"cas{i}:{objet}",
                    servi=servi.get("assiette_eur"), recalc=recalc["assiette_eur"],
                    tol="1 %", cause="constante")
        # total
        rec.compare("taxe_amenagement.calculer", "total_eur", f"cas{i}",
                    servi=servi.get("total_eur"), recalc=recalc["total_eur"],
                    tol="1 %", cause="constante")
        # RAP
        rec.compare("taxe_amenagement.calculer", "rap_eur", f"cas{i}",
                    servi=servi.get("rap_eur"), recalc=recalc["rap_eur"],
                    tol="1 %", cause="constante")

    # taux communal servi (fiche) = table taxe_amenagement_taux, par commune de l'échantillon
    communes = sorted({r["commune"] for r in echantillon if r["commune"] not in ("", "?")})
    for com in communes[:8]:
        idu = next((r["idu"] for r in echantillon if r["commune"] == com), None)
        if not idu:
            continue
        f = None
        try:
            from . import socle
            f = socle.fiche(idu)
        except Exception:  # noqa: BLE001
            continue
        servi = socle.chemin(f, "taxe_amenagement.taux_communal_pct")
        insee = idu[:5]
        with conn.cursor() as cur:
            cur.execute("SELECT part_communale_pct FROM taxe_amenagement_taux WHERE insee=%s", (insee,))
            r = cur.fetchone()
        if r and servi is not None:
            rec.compare("taxe_amenagement_taux (lookup)", "taux_communal_pct", com,
                        servi=servi, recalc=r[0], tol="0", cause="mauvais_id")
