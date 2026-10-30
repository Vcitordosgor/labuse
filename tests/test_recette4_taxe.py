"""RECETTE-4 (point « Taxe d'aménagement ») — VERROU DE RECETTE : un test par COMBINAISON DE FILTRES,
chaque résultat confronté à la formule OFFICIELLE 2026 (CGI art. 1635 quater) calculée à la main.

Barème officiel 2026 (La Réunion = DOM = HORS Île-de-France) — vérifié contre service-public A15416 :
  · valeur forfaitaire surface : 892 €/m²
  · piscine : 251 €/m² · stationnement extérieur : 2 928 €/place (→ 5 857 € sur délibération)
  · panneau PV au sol : 10 €/m² · éolienne (mât > 12 m) : 3 000 €
  · abattement 50 % sur les 100 premiers m² PAR LOGEMENT en résidence principale ; locaux aidés : 50 % partout
  · exonération de plein droit des surfaces < 5 m²
  · part départementale 974 : 2,5 % (confirmée DELTA) · part communale : votée (jamais inventée)
  · redevance d'archéologie préventive : 0,40 % de l'assiette

Conclusion de l'audit : AUCUN écart — le code est sur le bon millésime. Ces cas verrouillent chacun
une combinaison de filtres pour qu'un futur changement de barème (ou de logique) soit détecté.
"""
from labuse.taxe_amenagement import calculer, config

VF = 892.0
PISCINE = 251.0
STATION = 2928.0
STATION_MAX = 5857.0
DEP = 2.5


def _cent(x):
    return round(x + 1e-9, 2)


def test_config_valeurs_officielles_2026():
    cfg = config()
    assert cfg["meta"]["annee"] == 2026
    assert cfg["valeur_forfaitaire_m2"]["hors_idf"] == 892
    assert cfg["forfaits"]["piscine_m2"] == 251
    assert cfg["forfaits"]["stationnement_ext_place"] == 2928
    assert cfg["forfaits"]["stationnement_ext_place_max_delib"] == 5857
    assert cfg["forfaits"]["panneau_pv_sol_m2"] == 10
    assert cfg["forfaits"]["eolienne_mat"] == 3000
    assert cfg["abattement"]["taux_pct"] == 50
    assert cfg["abattement"]["plafond_m2_residence_principale"] == 100
    assert cfg["taux"]["part_departementale_defaut"] == 2.5
    assert cfg["exoneration_surface_min_m2"] == 5


def test_combo_surface_non_rp():
    # 200 m², non résidence principale, commune 3 %
    r = calculer(surface_taxable_m2=200, taux_communal_pct=3.0)
    assert _cent(r["assiette_eur"]) == _cent(200 * VF)             # 178 400
    assert _cent(r["part_communale_eur"]) == _cent(200 * VF * 0.03)   # 5 352
    assert _cent(r["part_departementale_eur"]) == _cent(200 * VF * DEP / 100)  # 4 460
    assert _cent(r["total_eur"]) == _cent(200 * VF * (0.03 + DEP / 100))        # 9 812
    assert _cent(r["rap_eur"]) == _cent(200 * VF * 0.004)          # 713,60


def test_combo_rp_maison_1_logement():
    # 200 m² RP, 1 logement : 100 m² à −50 % + 100 m² pleins
    r = calculer(surface_taxable_m2=200, residence_principale=True, nb_logements=1, taux_communal_pct=3.0)
    attendu = 100 * VF * 0.5 + 100 * VF                           # 133 800
    assert _cent(r["assiette_eur"]) == _cent(attendu)
    assert _cent(r["total_eur"]) == _cent(attendu * (0.03 + DEP / 100))  # 7 359


def test_combo_rp_collectif_3_logements():
    # 350 m² RP, 3 logements : abattement sur min(350, 3×100)=300 m², 50 m² pleins
    r = calculer(surface_taxable_m2=350, residence_principale=True, nb_logements=3, taux_communal_pct=3.0)
    attendu = 300 * VF * 0.5 + 50 * VF                           # 178 400
    assert _cent(r["assiette_eur"]) == _cent(attendu)


def test_combo_logement_aide():
    # 200 m² aidé : toute la surface à −50 %
    r = calculer(surface_taxable_m2=200, logement_aide=True, taux_communal_pct=3.0)
    attendu = 200 * VF * 0.5                                     # 89 200
    assert _cent(r["assiette_eur"]) == _cent(attendu)
    assert _cent(r["total_eur"]) == _cent(attendu * (0.03 + DEP / 100))  # 4 906


def test_combo_piscine():
    r = calculer(piscine_m2=50, taux_communal_pct=3.0)
    assert _cent(r["assiette_eur"]) == _cent(50 * PISCINE)        # 12 550
    assert _cent(r["total_eur"]) == _cent(50 * PISCINE * (0.03 + DEP / 100))  # 690,25


def test_combo_stationnement():
    r = calculer(stationnement_ext_places=5, taux_communal_pct=3.0)
    assert _cent(r["assiette_eur"]) == _cent(5 * STATION)         # 14 640
    assert _cent(r["total_eur"]) == _cent(5 * STATION * (0.03 + DEP / 100))  # 805,20


def test_combo_surface_sous_5m2_exoneree():
    r = calculer(surface_taxable_m2=3, taux_communal_pct=3.0)
    # < 5 m² : exonérée de la part surface → assiette surface nulle
    assert _cent(r["assiette_eur"]) == 0.0


def test_combo_mixte_rp_piscine_stationnement():
    # 150 m² RP (1 logt) + piscine 30 m² + 2 places, commune 4 %
    r = calculer(surface_taxable_m2=150, residence_principale=True, nb_logements=1,
                 piscine_m2=30, stationnement_ext_places=2, taux_communal_pct=4.0)
    surf = 100 * VF * 0.5 + 50 * VF                              # 89 200
    attendu = surf + 30 * PISCINE + 2 * STATION                 # 102 586
    assert _cent(r["assiette_eur"]) == _cent(attendu)
    assert _cent(r["part_communale_eur"]) == _cent(attendu * 0.04)        # 4 103,44
    assert _cent(r["part_departementale_eur"]) == _cent(attendu * DEP / 100)  # 2 564,65
    assert _cent(r["total_eur"]) == _cent(attendu * (0.04 + DEP / 100))  # 6 668,09


def test_combo_sans_taux_communal_pas_de_total_mais_departemental():
    # taux communal absent : total None, part départementale quand même calculée, drapeau levé
    r = calculer(surface_taxable_m2=200)
    assert r["total_eur"] is None
    assert r["part_communale_eur"] is None
    assert r["taux_communal_manquant"] is True
    assert _cent(r["part_departementale_eur"]) == _cent(200 * VF * DEP / 100)  # 4 460
