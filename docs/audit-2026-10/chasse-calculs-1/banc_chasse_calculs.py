"""CHASSE-CALCULS-1 — banc, rejouable en une commande.

    PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/banc_chasse_calculs.py

Lecture seule. Recalcule À LA MAIN les 10 cas de taxe d'aménagement du mandat (constantes
OFFICIELLES 2026 recopiées des textes, PAS du YAML de prod) et les confronte à la sortie du
produit `taxe_amenagement.calculer` — la calculette telle que la fiche/l'outil la servent.

Une garde par écart trouvé (CHASSE-CALCULS-1/ECARTS.md) :
  · 9 cas doivent être IDENTIQUES au centime (constantes + formule justes) ;
  · le cas « collectif 20 logements » DOIT diverger (E-A1) : le produit ne modélise pas
    l'abattement « 100 m² par logement » → il sur-taxe. La garde ÉCHOUE le jour où le produit
    se met à l'exprimer (paramètre nb_logements) OU, au contraire, où un des 9 cas justes casse.

Aucune fonction de calcul de prod n'est importée pour RECALCULER ; `calculer` n'est appelé que
pour LIRE le servi. Sortie : code retour 0 si l'état est CELUI ATTENDU par l'audit, 1 sinon.
"""
from __future__ import annotations

import sys

# ── constantes OFFICIELLES 2026 (CGI art. 1635 quater H/I/J ; arrêté 22/12/2025) ──
VF = 892.0                 # hors Île-de-France = La Réunion (DOM)
AB = 0.50                  # abattement
PLAFOND_RP = 100.0         # 100 premiers m² PAR LOGEMENT (RP)
PISCINE = 251.0
PARKING = 2928.0
DEP = 2.5                  # part départementale 974
RAP = 0.40


def _r(x):
    return round(float(x), 2)


def manuel(*, surf=0.0, rp=False, aide=False, nb_logements=1, piscine_m2=0.0,
           places=0, com_pct=0.0):
    """Assiette + total, formule officielle indépendante — avec abattement PAR LOGEMENT."""
    if surf and surf < 5:            # exonération de plein droit (< 5 m²)
        a_surf = 0.0
    elif aide:                        # logement aidé : 50 % sur TOUTE la surface
        a_surf = surf * VF * (1 - AB)
    elif rp:                          # RP : 100 m² PAR LOGEMENT à −50 %, reste plein
        abattue = min(surf, PLAFOND_RP * max(1, nb_logements))
        a_surf = (surf - abattue) * VF + abattue * VF * (1 - AB)
    else:
        a_surf = surf * VF
    assiette = _r(a_surf + piscine_m2 * PISCINE + places * PARKING)
    total = _r(assiette * (com_pct + DEP) / 100.0)
    return {"assiette": assiette, "total": total, "rap": _r(assiette * RAP / 100.0)}


# (nom, kwargs produit, kwargs manuel, doit_diverger)
CAS = [
    ("1 maison 120 RP com3", dict(surface_taxable_m2=120, residence_principale=True, taux_communal_pct=3),
     dict(surf=120, rp=True, nb_logements=1, com_pct=3), False),
    ("2 maison 250 com5", dict(surface_taxable_m2=250, taux_communal_pct=5),
     dict(surf=250, com_pct=5), False),
    # CHASSE-CALCULS-FIX-1 Lot 1 (E-A1) — collectif 20 logements RP : l'outil reçoit maintenant
    # nb_logements et applique l'abattement 100 m² PAR logement → doit ÉGALER le recalcul manuel.
    ("3 collectif 20lgt=1400 RP com3", dict(surface_taxable_m2=1400, residence_principale=True, nb_logements=20, taux_communal_pct=3),
     dict(surf=1400, rp=True, nb_logements=20, com_pct=3), False),
    ("4 piscine 30 com5", dict(surface_taxable_m2=0, piscine_m2=30, taux_communal_pct=5),
     dict(piscine_m2=30, com_pct=5), False),
    ("5 abri 15 com3", dict(surface_taxable_m2=15, taux_communal_pct=3),
     dict(surf=15, com_pct=3), False),
    ("6 social 120 aide com5", dict(surface_taxable_m2=120, logement_aide=True, taux_communal_pct=5),
     dict(surf=120, aide=True, com_pct=5), False),
    ("7 extension 40 com3", dict(surface_taxable_m2=40, taux_communal_pct=3),
     dict(surf=40, com_pct=3), False),
    ("8 bureaux 300 com3", dict(surface_taxable_m2=300, taux_communal_pct=3),
     dict(surf=300, com_pct=3), False),
    ("9 parking 10 com5", dict(surface_taxable_m2=0, stationnement_ext_places=10, taux_communal_pct=5),
     dict(places=10, com_pct=5), False),
    ("10 mixte 200+pisc40+4pk com5", dict(surface_taxable_m2=200, piscine_m2=40, stationnement_ext_places=4, taux_communal_pct=5),
     dict(surf=200, piscine_m2=40, places=4, com_pct=5), False),
]


def run() -> int:
    from labuse import taxe_amenagement as prod   # importé UNIQUEMENT pour lire le SERVI
    anomalies = []
    print("CHASSE-CALCULS-1 — taxe d'aménagement : recalcul manuel vs produit\n")
    for nom, kw_prod, kw_man, doit_diverger in CAS:
        p = prod.calculer(**kw_prod)
        m = manuel(**kw_man)
        egal = (p["total_eur"] == m["total"] and p["assiette_eur"] == m["assiette"])
        etat = "OK"
        if doit_diverger and egal:
            etat = "ANOMALIE (devait diverger — E-A1 corrigé ? mettre à jour l'audit)"
            anomalies.append(nom)
        elif doit_diverger and not egal:
            etat = f"DIVERGENCE ATTENDUE E-A1 (produit {p['total_eur']} vs manuel {m['total']})"
        elif not doit_diverger and not egal:
            etat = f"ANOMALIE (produit {p['total_eur']} ≠ manuel {m['total']})"
            anomalies.append(nom)
        print(f"  [{etat.split()[0]:10}] {nom:34} produit={p['total_eur']:>12} manuel={m['total']:>12}  {etat if 'OK'!=etat else ''}")
    print()
    # CHASSE-CALCULS-FIX-1 Lot 1 (E-A1) — garde « ne suppose rien » : RP sans nb_logements →
    # abattement pour 1 logement ET message d'invite à saisir (jamais un collectif supposé).
    sans_nb = prod.calculer(surface_taxable_m2=1400, residence_principale=True, taux_communal_pct=3)
    ok_msg = (sans_nb.get("nb_logements") == 1 and not sans_nb.get("nb_logements_precise")
              and bool(sans_nb.get("message_nb_logements")) and sans_nb["total_eur"] == 66231.0)
    print(f"  [{'OK' if ok_msg else 'ANOMALIE':10}] RP sans nb_logements → 1 logement + message d'invite "
          f"(total {sans_nb['total_eur']}, msg={'oui' if sans_nb.get('message_nb_logements') else 'NON'})")
    if not ok_msg:
        anomalies.append("message_nb_logements")
    if anomalies:
        print(f"✗ {len(anomalies)} anomalie(s) : {anomalies} — l'état ne correspond plus à ECARTS.md")
        return 1
    print("✓ état conforme (E-A1 fermé : 10 cas exacts dont collectif, et RP sans nb = 1 logt + message)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
