"""Témoin CIRCUIT-4 — taxe d'aménagement : recalcul ligne à ligne INDÉPENDANT (formule CGI
1635 quater H/I telle que citée dans la fiche), comparé au moteur. Aucune fonction du moteur
réutilisée pour le recalcul."""
from __future__ import annotations

from labuse import taxe_amenagement as ta


def _recalcul_independant(surface_m2, rp, piscine_m2, places_ext, tx_com, tx_dep, cfg):
    """La formule de la référence, réécrite ICI : assiette = surface × VF (abattement 50 % sur
    les 100 premiers m² d'une RP) + forfaits ; taxe = assiette × (taux com + taux dep)."""
    vf = float(cfg["valeur_forfaitaire_m2"]["hors_idf"])
    ab = cfg["abattement"]
    fo = cfg["forfaits"]
    abattue = min(surface_m2, float(ab["plafond_m2_residence_principale"])) if rp else 0.0
    pleine = surface_m2 - abattue
    assiette = (pleine * vf + abattue * vf * (1 - ab["taux_pct"] / 100.0)
                + piscine_m2 * fo["piscine_m2"]
                + places_ext * fo["stationnement_ext_place"])
    return assiette * (tx_com + tx_dep) / 100.0


def test_calcul_ligne_a_ligne_independant():
    cfg = ta.config()
    # valeurs 2026 vérifiées au lot 2 (CGI 1635 quater H + service-public A15416)
    assert cfg["valeur_forfaitaire_m2"]["hors_idf"] == 892
    assert cfg["abattement"]["taux_pct"] == 50 and cfg["abattement"]["plafond_m2_residence_principale"] == 100
    assert cfg["forfaits"]["piscine_m2"] == 251 and cfg["forfaits"]["stationnement_ext_place"] == 2928

    out = ta.calculer(surface_taxable_m2=150, residence_principale=True, piscine_m2=30,
                      stationnement_ext_places=2, taux_communal_pct=5.0,
                      taux_departemental_pct=2.5)
    attendu = _recalcul_independant(150.0, True, 30.0, 2, 5.0, 2.5, cfg)
    assert out["total_eur"] is not None
    assert abs(out["total_eur"] - attendu) < 1.0, (out["total_eur"], attendu)


def test_sans_taux_communal_pas_de_total():
    out = ta.calculer(surface_taxable_m2=150, residence_principale=True,
                      taux_communal_pct=None, taux_departemental_pct=None)
    assert out["total_eur"] is None       # doctrine : aucun taux inventé
