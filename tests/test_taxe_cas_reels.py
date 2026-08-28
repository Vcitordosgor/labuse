"""RV2-V2 (retours visuels 2) — CONTRÔLE PAR CAS RÉELS de la taxe d'aménagement.

Cinq cas aux résultats calculables À LA MAIN, figés : toute divergence future (barème modifié,
régression du calcul) casse un test. Barème millésime 2026 (config/taxe_amenagement.yaml, vérifié le
28/08/2026 contre service-public A15416 ; base légale CGI art. 1635 quater) :
  · valeur forfaitaire hors-IdF (La Réunion, DOM) = 892 €/m²
  · abattement 50 % sur les 100 premiers m² de résidence principale ; sur TOUTE la surface d'un
    logement aidé (CGI 1635 quater H)
  · exonération de plein droit des surfaces < 5 m² (CGI 1635 quater D)
  · forfaits : piscine 251 €/m², stationnement extérieur 2 928 €/place (CGI 1635 quater J)
  · part départementale plafond 2,5 %
Calcul pur (pas de base ni de réseau).
"""
from __future__ import annotations

from labuse.taxe_amenagement import calculer

VF = 892  # €/m² hors-IdF


def test_cas1_maison_simple():
    """Maison RP 120 m², sans forfait, communal 3 %, départemental 2,5 %.
    Surface : 100 m² à −50 % + 20 m² pleins = 20×892 + 100×892×0,5 = 17 840 + 44 600 = 62 440 €.
    Communale 3 % = 1 873,20 ; départementale 2,5 % = 1 561,00 ; total = 3 434,20."""
    r = calculer(surface_taxable_m2=120, residence_principale=True,
                 taux_communal_pct=3, taux_departemental_pct=2.5)
    assert r["assiette_eur"] == 62440.0
    assert r["part_communale_eur"] == 1873.20
    assert r["part_departementale_eur"] == 1561.0
    assert r["total_eur"] == 3434.20


def test_cas2_maison_piscine_stationnement():
    """Maison RP 150 m² + piscine 30 m² + 2 places, communal 5 %, départemental 2,5 %.
    Surface : 50×892 + 100×892×0,5 = 44 600 + 44 600 = 89 200. Piscine 30×251 = 7 530.
    Stationnement 2×2 928 = 5 856. Assiette = 89 200 + 7 530 + 5 856 = 102 586.
    Communale 5 % = 5 129,30 ; départementale 2,5 % = 2 564,65 ; total = 7 693,95."""
    r = calculer(surface_taxable_m2=150, residence_principale=True, piscine_m2=30,
                 stationnement_ext_places=2, taux_communal_pct=5, taux_departemental_pct=2.5)
    assert r["assiette_eur"] == 102586.0
    assert r["part_communale_eur"] == 5129.30
    assert r["part_departementale_eur"] == 2564.65
    assert r["total_eur"] == 7693.95


def test_cas3_logement_aide():
    """Logement AIDÉ 80 m² (abattement sur toute la surface), communal 4 %, départemental 2,5 %.
    Surface : 80×892×0,5 = 35 680. Communale 4 % = 1 427,20 ; départementale 2,5 % = 892,00 ;
    total = 2 319,20."""
    r = calculer(surface_taxable_m2=80, logement_aide=True,
                 taux_communal_pct=4, taux_departemental_pct=2.5)
    assert r["assiette_eur"] == 35680.0
    assert r["part_communale_eur"] == 1427.20
    assert r["part_departementale_eur"] == 892.0
    assert r["total_eur"] == 2319.20


def test_cas4_projet_sous_seuil_5m2():
    """Projet 4 m² (< 5 m²) → surface EXONÉRÉE (CGI 1635 quater D). Assiette 0, total 0."""
    r = calculer(surface_taxable_m2=4, residence_principale=True,
                 taux_communal_pct=3, taux_departemental_pct=2.5)
    assert r["assiette_eur"] == 0.0
    assert r["total_eur"] == 0.0
    # la ligne dit l'exonération (jamais un zéro muet)
    assert any("exonérée" in l["detail"] for l in r["lignes"])


def test_cas5_taux_communal_manquant():
    """100 m² RP, taux communal NON saisi → pas de total (jamais inventé), mais assiette + part dép. calculées.
    Surface : 100×892×0,5 = 44 600. Départementale 2,5 % = 1 115,00 ; total = None."""
    r = calculer(surface_taxable_m2=100, residence_principale=True, taux_departemental_pct=2.5)
    assert r["assiette_eur"] == 44600.0
    assert r["part_communale_eur"] is None
    assert r["part_departementale_eur"] == 1115.0
    assert r["total_eur"] is None
    assert r["taux_communal_manquant"] is True
