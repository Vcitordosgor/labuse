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


# ── TAXE-FIX-1 point 1 — exonérations de plein droit (CGI 1635 quater D) ───────────────────────
def test_exoneration_agricole_zone_a_zero(  # CO0322 : hangar agricole en zone A → 0 €
):
    """Un local agricole (CGI 1635 quater D, 3°) : la surface est EXONÉRÉE, pas abattue → 0 €."""
    out = ta.calculer(surface_taxable_m2=0, surface_exoneree_m2=400, motif_exoneration="agricole",
                      taux_communal_pct=5.0, taux_departemental_pct=2.5)
    assert out["assiette_eur"] == 0.0
    assert out["total_eur"] == 0.0
    ligne = next(l for l in out["lignes"] if "exonérée" in l["poste"] or "exonérée" in l["detail"])
    assert ligne["assiette_eur"] == 0.0 and "3°" in ligne["detail"]


def test_plai_exonere_pas_abattu():
    """PLAI (2°) = EXONÉRATION (0 €), à ne pas confondre avec l'abattement 50 % du logement aidé."""
    exo = ta.calculer(surface_taxable_m2=0, surface_exoneree_m2=300, motif_exoneration="plai",
                      taux_communal_pct=5.0, taux_departemental_pct=2.5)
    abattu = ta.calculer(surface_taxable_m2=300, logement_aide=True,
                         taux_communal_pct=5.0, taux_departemental_pct=2.5)
    assert exo["total_eur"] == 0.0                       # exonéré : rien
    assert abattu["total_eur"] and abattu["total_eur"] > 0   # abattu : moitié, pas zéro


def test_programme_mixte_3_plai_sur_10():
    """« 10 logements dont 3 PLAI » : les 3 (≈180 m²) exonérés, les 7 (≈420 m²) au barème, un seul calcul."""
    out = ta.calculer(surface_taxable_m2=420, surface_exoneree_m2=180, motif_exoneration="plai",
                      taux_communal_pct=5.0, taux_departemental_pct=2.5)
    # assiette = 420 × 892 (les 180 PLAI ne comptent pas) ; la ligne exonérée est présente à 0 €.
    assert out["assiette_eur"] == round(420 * 892, 2)
    assert any(l["assiette_eur"] == 0.0 and "PLAI" in l["poste"] for l in out["lignes"])
    assert out["total_eur"] == round(420 * 892 * 0.075, 2)


def test_reconstruction_identique_exoneree():
    out = ta.calculer(surface_taxable_m2=0, surface_exoneree_m2=120, motif_exoneration="reconstruction",
                      taux_communal_pct=3.0, taux_departemental_pct=2.5)
    assert out["total_eur"] == 0.0
    assert any("9°" in l["detail"] for l in out["lignes"])
