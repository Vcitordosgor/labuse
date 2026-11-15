"""MOTEUR-VERITE-FIX-2 LOT A — la RÈGLE gravée : un chiffre de capacité ne peut dépasser le
niveau prudent que si TOUTES les conditions de l'article qui l'ouvre sont APPLIQUÉES par le
moteur. Un jeton non modélisé, mal formé, disjonctif ou non mesurable FERME l'ouverture
(le verdict reste constructible, la mention « capacité supérieure possible » reste)."""
from labuse.gabarit.builder import analyser_condition_implantation, jeton_num_strict


def test_parseur_strict_jamais_141414():
    # FIX-2 LOT A — « 14 m » annoté était lu 141 414 m (concaténation des chiffres) et ouvrait
    # deux limites à toute largeur (Sainte-Rose Ua/Ub/Uc) ; « 20 m (…) » était lu 2 014 m de
    # bande (Bras-Panon). La forme stricte refuse toute annotation.
    assert jeton_num_strict("largeur_terrain_max:14 m") == ("largeur_terrain_max", 14.0)
    assert jeton_num_strict("profondeur_bande:20 m") == ("profondeur_bande", 20.0)
    assert jeton_num_strict("bascule_surface:400 m²") == ("bascule_surface", 400.0)
    assert jeton_num_strict("hauteur_bande:4 m sur bande de 3 m") is None
    assert jeton_num_strict("largeur_terrain_max:14 m (≤ 14 m : deux limites ; > 14 m : une_seule_limite)") is None
    assert jeton_num_strict("profondeur_bande:20 m (deux limites si largeur_terrain_max:14 m)") is None
    assert jeton_num_strict("profondeur_bande:20 m OU largeur_terrain_max:15 m") is None


def test_condition_non_modelisee_ferme_l_ouverture():
    # Avant FIX-2 : « deux_limites_max + non » ouvrait deux limites ET ajoutait une mention —
    # la capacité dépassait sans que la condition (hauteur en limite, rupture…) soit appliquée.
    imp = {"mode": "limite_sous_conditions", "article": "U 7.2",
           "condition_texte": "hauteur ≤ 6 m sur la bande de 3 m",
           "condition_modelable": "deux_limites_max + non"}
    d = analyser_condition_implantation(imp, largeur_m=10.0, surface_m2=500.0)
    assert d["ouvre"] is False and d["zero"] == 0
    assert d["mention"] and "hauteur" in d["mention"]
    # idem pour un flag ANNOTÉ (condition supplémentaire écrite dans le jeton)
    imp2 = dict(imp, condition_modelable="une_seule_limite (au-delà)")
    d2 = analyser_condition_implantation(imp2, 10.0, 500.0)
    assert d2["ouvre"] is False and d2["mention"]
    # et pour un jeton numérique annoté (le bug 141 414)
    imp3 = dict(imp, condition_modelable="largeur_terrain_max:14 m (≤ 14 m : deux limites)")
    d3 = analyser_condition_implantation(imp3, 10.0, 500.0)
    assert d3["ouvre"] is False


def test_conditions_toutes_appliquees_ouvrent():
    imp = {"mode": "limite_sous_conditions", "article": "UA 7",
           "condition_modelable": "largeur_terrain_max:14 m"}
    assert analyser_condition_implantation(imp, 12.0, 300.0)["zero"] == "toutes"
    # condition évaluée NON remplie → pas d'ouverture, pas de mention (la règle est appliquée)
    d = analyser_condition_implantation(imp, 18.0, 300.0)
    assert d["ouvre"] is False and d["mention"] is None
    # largeur NON mesurable → on ne peut pas appliquer la condition → ferme AVEC mention
    d2 = analyser_condition_implantation(imp, None, 300.0)
    assert d2["ouvre"] is False and d2["mention"]
    # bascule de surface : mesurée des deux côtés du seuil
    imp3 = {"mode": "limite_sous_conditions", "condition_modelable": "bascule_surface:400"}
    assert analyser_condition_implantation(imp3, None, 300.0)["zero"] == 2
    assert analyser_condition_implantation(imp3, None, 900.0)["zero"] == 1
    # sans condition écrite, le libre choix reste ouvert
    assert analyser_condition_implantation({"mode": "limite_ou_retrait"}, None, None)["zero"] == "toutes"


def test_retrait_obligatoire_n_ouvre_jamais():
    d = analyser_condition_implantation(
        {"mode": "retrait_obligatoire", "condition_texte": "retrait de fond non chiffré, à vérifier"},
        10.0, 500.0)
    assert d["ouvre"] is False and d["zero"] == 0 and d["mention"]
