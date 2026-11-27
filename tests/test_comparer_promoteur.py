from labuse.exports.blocs.comparatif import rendu
from labuse.exports.builder import _resume_comparatif


def test_plancher_non_chiffre_et_plancher_nul_restent_distincts():
    lignes = [
        {"idu": "97415000BI0648", "sdp_residuelle_m2": None},
        {"idu": "97416000EK0559", "sdp_residuelle_m2": 0},
    ]
    assert "non chiffré" in _resume_comparatif(lignes)
    assert "aucune surface" in _resume_comparatif(lignes[1:])


def test_export_restitue_la_condition_et_la_source_de_la_surface():
    ligne = {"idu": "97416000EK0559", "emprise_ces_detail": "Selon l’unité foncière",
                "surface_a_retenir": {"valeur_m2": 35, "source": "estimation rapide",
                                       "phrase": "Terrain libéré (démolition) : 35 m²."}}
    html = rendu([ligne])
    assert "Selon l’unité foncière" in html
    assert "Terrain libéré (démolition) : 35 m²." in html


def test_au3st_fermee_sans_etendre_la_regle_aux_autres_zones():
    from labuse.faisabilite.au_ouverture import zone_regime
    assert zone_regime("97415", "au3ST")["ouverture"] == "fermee"
    assert zone_regime("97415", "AU3e")["ouverture"] == "conditionnelle_operation"
    assert zone_regime("97415", "AU3st2")["ouverture"] == "conditionnelle_operation"
