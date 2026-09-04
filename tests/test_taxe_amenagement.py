"""K3 (rattrapage KelFoncier) — calculette de taxe d'aménagement.

Formule publique, config datée et sourcée. On gèle : détail ligne par ligne, abattement 50 % sur les
100 premiers m² d'une résidence principale, forfaits d'installations, et surtout AUCUN taux communal
inventé (sans taux communal, pas de total).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from labuse.taxe_amenagement import calculer, config

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


def test_config_datee_et_sourcee():
    c = config()
    assert c["meta"]["annee"] and c["meta"]["url"].startswith("http") and "service-public" in c["meta"]["url"]
    assert c["valeur_forfaitaire_m2"]["hors_idf"] > 0        # La Réunion = hors IdF
    assert c["forfaits"]["piscine_m2"] > 0
    assert c["taux"]["part_communale_defaut"] is None        # aucun défaut communal


def test_valeurs_2026_conformes_arrete_officiel():
    """RETOURS-11F M8 — les valeurs forfaitaires de la config sont EXACTEMENT celles de l'arrêté 2026
    (vérifiées 04/09/2026 contre service-public / BOFiP). La « fausse alerte » du mandat : 892 €/m² est
    la valeur RÉELLE 2026 hors-IdF — elle a BAISSÉ (930→892, indice ICC en repli), ce n'est pas un bug ;
    et le forfait stationnement 2 928 € est la valeur 2026 indépendante, sans incohérence entre les deux.
    Ce test GÈLE les valeurs vérifiées : toute dérive silencieuse au prochain millésime rougira."""
    c = config()
    assert c["meta"]["annee"] == 2026
    assert c["valeur_forfaitaire_m2"]["hors_idf"] == 892     # La Réunion (DOM) — arrêté 2026
    assert c["valeur_forfaitaire_m2"]["idf"] == 1011
    assert c["forfaits"]["piscine_m2"] == 251                # CGI 1635 quater J, millésime 2026
    assert c["forfaits"]["panneau_pv_sol_m2"] == 10
    assert c["forfaits"]["stationnement_ext_place"] == 2928
    assert c["forfaits"]["eolienne_mat"] == 3000
    assert c["abattement"]["taux_pct"] == 50 and c["abattement"]["plafond_m2_residence_principale"] == 100
    assert c["exoneration_surface_min_m2"] == 5


def test_sans_taux_communal_pas_de_total():
    r = calculer(surface_taxable_m2=150, residence_principale=True)
    assert r["taux_communal_manquant"] is True
    assert r["total_eur"] is None and r["part_communale_eur"] is None
    assert r["message_taux_communal"] and "non renseigné" in r["message_taux_communal"]
    # l'assiette (indépendante du taux) est calculée et détaillée
    assert r["assiette_eur"] > 0 and r["lignes"]


def test_abattement_50pct_100_premiers_m2():
    """RP 150 m² : 100 m² à −50 % + 50 m² pleins → assiette = 100×vf×0,5 + 50×vf."""
    vf = config()["valeur_forfaitaire_m2"]["hors_idf"]
    r = calculer(surface_taxable_m2=150, residence_principale=True, taux_communal_pct=3.0)
    attendu = 100 * vf * 0.5 + 50 * vf
    assert abs(r["assiette_eur"] - attendu) < 1
    # sans le statut RP, pas d'abattement
    r2 = calculer(surface_taxable_m2=150, taux_communal_pct=3.0)
    assert abs(r2["assiette_eur"] - 150 * vf) < 1
    assert r2["assiette_eur"] > r["assiette_eur"]


def test_detail_ligne_par_ligne_et_forfaits():
    r = calculer(surface_taxable_m2=100, piscine_m2=30, stationnement_ext_places=2, taux_communal_pct=5.0)
    postes = {l["poste"] for l in r["lignes"]}
    assert "Surface de construction" in postes and "Piscine" in postes and "Stationnement extérieur" in postes
    # total = assiette × (com + dep), vérifiable ligne par ligne
    assert r["part_communale_eur"] == round(r["assiette_eur"] * 5.0 / 100, 2)
    assert r["total_eur"] == round((r["part_communale_eur"] or 0) + (r["part_departementale_eur"] or 0), 2)


def test_departemental_plafond_non_confirme():
    r = calculer(surface_taxable_m2=50, taux_communal_pct=2.0)
    assert r["taux_departemental_pct"] == 2.5            # plafond légal servi
    assert r["part_departementale_confirmee"] is False   # étiqueté « à confirmer », jamais un taux confirmé


def test_endpoint_calcule_et_config(client):
    cfg = client.get("/outils/taxe-amenagement/config").json()
    assert cfg["meta"]["annee"] and cfg["valeur_forfaitaire_m2"]["hors_idf"] > 0
    r = client.get("/outils/taxe-amenagement?surface_taxable_m2=200&taux_communal_pct=3").json()
    assert r["total_eur"] is not None and r["lignes"]
    r0 = client.get("/outils/taxe-amenagement?surface_taxable_m2=200").json()
    assert r0["total_eur"] is None and r0["taux_communal_manquant"] is True
