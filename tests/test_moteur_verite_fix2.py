"""MOTEUR-VERITE-FIX-2 LOT A — la RÈGLE gravée : un chiffre de capacité ne peut dépasser le
niveau prudent que si TOUTES les conditions de l'article qui l'ouvre sont APPLIQUÉES par le
moteur. Un jeton non modélisé, mal formé, disjonctif ou non mesurable FERME l'ouverture
(le verdict reste constructible, la mention « capacité supérieure possible » reste)."""
from labuse.gabarit.builder import analyser_condition_implantation, jeton_num_strict


LB = {"declaration": "toutes les conditions de l'article sont appliquées",
      "conditions": {k: "absente_du_texte" for k in (
          "nombre_de_limites", "lineaire_ou_profondeur_en_limite", "bande_depuis_voie",
          "hauteur_en_limite", "angle", "patio", "rupture_mitoyennete", "affectation_graphique")}}


def test_fix3_liste_blanche_obligatoire():
    """FIX-3 LOT 1 — tout est fermé par défaut : l'ouverture chiffrée exige la déclaration
    complète (8 conditions, chacune absente_du_texte ou mesuree). Une condition présente
    seulement dans le texte (clé manquante ou autre valeur) FERME."""
    imp = {"mode": "limite_ou_retrait", "article": "Uc 5", "liste_blanche": LB}
    assert analyser_condition_implantation(imp, None, None)["zero"] == "toutes"
    import copy
    imp2 = copy.deepcopy(imp)
    del imp2["liste_blanche"]["conditions"]["patio"]
    assert analyser_condition_implantation(imp2, None, None)["ouvre"] is False
    imp3 = copy.deepcopy(imp)
    imp3["liste_blanche"]["conditions"]["angle"] = "presente_dans_le_texte"
    assert analyser_condition_implantation(imp3, None, None)["ouvre"] is False
    imp4 = copy.deepcopy(imp)
    imp4["liste_blanche"]["declaration"] = "conditions appliquées"
    assert analyser_condition_implantation(imp4, None, None)["ouvre"] is False


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
           "condition_modelable": "largeur_terrain_max:14 m", "liste_blanche": LB}
    assert analyser_condition_implantation(imp, 12.0, 300.0)["zero"] == "toutes"
    # condition évaluée NON remplie → pas d'ouverture, pas de mention (la règle est appliquée)
    d = analyser_condition_implantation(imp, 18.0, 300.0)
    assert d["ouvre"] is False and d["mention"] is None
    # largeur NON mesurable → on ne peut pas appliquer la condition → ferme AVEC mention
    d2 = analyser_condition_implantation(imp, None, 300.0)
    assert d2["ouvre"] is False and d2["mention"]
    # bascule de surface : mesurée des deux côtés du seuil
    imp3 = {"mode": "limite_sous_conditions", "condition_modelable": "bascule_surface:400",
            "liste_blanche": LB}
    assert analyser_condition_implantation(imp3, None, 300.0)["zero"] == 2
    assert analyser_condition_implantation(imp3, None, 900.0)["zero"] == 1
    # FIX-3 : SANS déclaration de liste blanche, même le « libre choix » reste FERMÉ
    assert analyser_condition_implantation({"mode": "limite_ou_retrait"}, None, None)["ouvre"] is False


def test_retrait_obligatoire_n_ouvre_jamais():
    d = analyser_condition_implantation(
        {"mode": "retrait_obligatoire", "condition_texte": "retrait de fond non chiffré, à vérifier"},
        10.0, 500.0)
    assert d["ouvre"] is False and d["zero"] == 0 and d["mention"]


def test_lot_b_plafond_n_est_pas_une_capacite():
    """FIX-2 LOT B — les secteurs d'habitat A/N n'ont AUCUNE enveloppe calibrée : la capacité ne
    peut pas être établie → SDP ∅ (jamais le plafond servi comme chiffre) ; le plafond part en
    clé informative NON sommable ; tranche Arh (50 m²/600 m²) : complètes comptées, incomplète
    « à vérifier » ; « limite totale » = par unité foncière."""
    from labuse.faisabilite.engine import faisabilite_secteur_habitat
    f = faisabilite_secteur_habitat("Aba", "A", {
        "seuil_m2": 150, "article": "A2.2, 7.", "page_pdf": 42,
        "citation": "admises dans la limite totale de 150 m² de surface de plancher."})
    assert f.constructible and f.cause is None
    assert "surface_plancher_m2" not in (f.fourchette or {})
    assert (f.fourchette or {}).get("plafond_secteur_m2") == 150.0
    assert "capacité à vérifier" in f.verdict
    assert "unité foncière" in f.verdict or "limite TOTALE" in f.verdict
    # tranches complètes (Saint-Louis Arh)
    f2 = faisabilite_secteur_habitat("Arh", "A", {
        "seuil_m2": 50, "citation": "50 m² de surface de plancher par tranche de 600 m² de terrain."},
        surface_m2=1500)
    assert (f2.fourchette or {}).get("plafond_secteur_m2") == 100.0
    # tranche incomplète → aucun plafond chiffré, « à vérifier »
    f3 = faisabilite_secteur_habitat("Arh", "A", {
        "seuil_m2": 50, "citation": "par tranche de 600 m² de terrain."}, surface_m2=400)
    assert (f3.fourchette or {}).get("plafond_secteur_m2") is None
    assert "tranche incomplète" in f3.verdict


def test_fix3_largeur_est_une_porte_pas_un_nombre():
    """FIX-3 LOT 2 — Sainte-Rose Ud (AS0031, front 52,6 m) : « une seule limite pour une largeur
    sur voie au plus égale à 14 m ». La largeur est une PORTE : remplie, elle active le jeton de
    nombre (une seule) ; non remplie, le côté FERME (règle appliquée, pas une mention). Elle ne
    vaut jamais « toutes » quand un jeton de nombre l'accompagne."""
    lb = {"declaration": "toutes les conditions de l'article sont appliquées",
          "conditions": {k: ("mesuree" if k == "nombre_de_limites" else "absente_du_texte")
                         for k in ("nombre_de_limites", "lineaire_ou_profondeur_en_limite",
                                   "bande_depuis_voie", "hauteur_en_limite", "angle", "patio",
                                   "rupture_mitoyennete", "affectation_graphique")}}
    imp = {"mode": "limite_sous_conditions", "liste_blanche": lb,
           "condition_modelable": "largeur_terrain_max:14 m + une_seule_limite"}
    d = analyser_condition_implantation(imp, 12.0, None)
    assert d["ouvre"] is True and d["zero"] == 1          # jamais « toutes »
    d = analyser_condition_implantation(imp, 52.6, None)
    assert d["ouvre"] is False and d["zero"] == 0 and d["mention"] is None
    # largeur non mesurable → prudent, mention
    d = analyser_condition_implantation(imp, None, None)
    assert d["ouvre"] is False and d["mention"]
    # mode imposé : au-delà du seuil, « au moins une » reste imposée
    impi = {"mode": "limite_imposee", "liste_blanche": lb,
            "condition_modelable": "largeur_terrain_max:14 m"}
    d = analyser_condition_implantation(impi, 52.6, None)
    assert d["ouvre"] is True and d["zero"] == 1


def test_fix3_repli_regle_propre_jamais_generique():
    """FIX-3 LOT 2 — le repli générique applique les règles PROPRES de la zone quand elles
    existent (feuilles validées) : Saint-Denis Uicm = 5 m ET CES 40 % (Ui.9 p.56) ; Udo = 4 m
    (Ud.7 p.42) et sa hauteur (règle propre par rue, Ud.10 p.44) n'est JAMAIS remplacée par la
    hauteur générique → capacité à vérifier (constructible, SDP ∅)."""
    from labuse.faisabilite.engine import estimate_capacity
    from labuse.faisabilite.zonage import _zone_generique
    zr = _zone_generique("Uicm", "Saint-Denis")
    assert zr.calibree is False
    assert zr.recul_limites_sep_m == 5.0
    assert zr.emprise_sol_pct == 40.0
    assert zr.capacite_a_verifier is None
    zr2 = _zone_generique("Udo", "Saint-Denis")
    assert zr2.recul_limites_sep_m == 4.0
    assert zr2.capacite_a_verifier and "Ud.10" in zr2.capacite_a_verifier
    f = estimate_capacity(zr2, 800.0)
    assert f.constructible is True
    assert "capacité à vérifier" in f.verdict
    assert "surface_plancher_m2" not in (f.fourchette or {})
    # zone sans aucune feuille : le générique pur reste servi (rien ne casse)
    zr3 = _zone_generique("Uzz", "Cilaos")
    assert zr3.capacite_a_verifier is None and zr3.he_m is not None


def test_fix3_capacite_a_verifier_n_est_pas_zero(monkeypatch):
    """FIX-3 LOT 3 — une faisabilité constructible SANS `surface_plancher_m2` (SDP ∅ : capacité
    à vérifier) ne devient JAMAIS `capacite_nulle`/0 dans le résiduel : SDP écrite NULL + cause
    d'IGNORANCE (gate et score servent « Analyse incomplète », pas « rien à bâtir »).
    Témoins AS0256 (Salazie Aba), CY1293 (Saint-Leu, site classé)."""
    from labuse.faisabilite import residuel as R
    from labuse.faisabilite.engine import cause_certaine, cause_libelle

    monkeypatch.setattr(R.bati_mod, "layer_available", lambda s: True)

    class _F:
        constructible = True
        fourchette = {"logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)}  # SDP ∅
        cause = None
        zone = "Aba"
    out = R.compute_residuel(None, 0, faisa=(object(), _F()))
    assert out["disponible"] is False
    assert out["cause"] == "capacite_a_verifier"
    assert out["sdp_ecrite"] is None                      # l'inconnu RESTE inconnu, jamais 0
    assert cause_certaine("capacite_a_verifier") is False  # famille IGNORANCE (gate + score)
    assert "Analyse incomplète" in (cause_libelle("capacite_a_verifier") or "")
    # une vraie capacité nulle (clé présente, valeur 0) garde son verdict ferme
    class _F0(_F):
        fourchette = {"surface_plancher_m2": 0, "emprise_constructible_m2": 0,
                      "logements_au_sol": (0, 0), "logements_sous_sol": (0, 0)}
    out0 = R.compute_residuel(None, 0, faisa=(object(), _F0()))
    assert out0["cause"] == "capacite_nulle" and out0["sdp_ecrite"] == 0
