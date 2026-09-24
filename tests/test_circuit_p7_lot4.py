"""CIRCUIT-P7 (lot 4) — L'INVARIANT de l'onglet « À faire ».

Le compteur « À faire » = le nombre de lignes = la somme EXACTE des pastilles non vertes
(Sources + Circuit) et des actions en attente = la tuile « tâches à effectuer » du Pilotage.
La fuite et l'écart du contrôle, qui n'avaient AUCUNE ligne, en ont une (le bug fermé) ;
« jamais vérifiée » (gris) n'en fait pas. Test construit : d'abord le cas qui casse si les
lignes fuite/écart manquent, puis l'égalité stricte compteur = lignes = formule = total_a_faire.
"""
from labuse import circuit_resume as R


def _res(nom, libelle):
    couleur = {"nouvelle version": "ambre", "échue": "ambre", "sonde en panne": "rouge",
               "jamais vérifiée": "gris", "à jour": "mint"}[libelle]
    return {"id": nom, "nom": nom, "etat": [couleur, libelle], "vanne": {}, "veille": {}}


RESERVOIRS = [
    _res("A", "nouvelle version"),   # → Injecter (ambre, compte)
    _res("B", "nouvelle version"),   # → Injecter
    _res("C", "échue"),              # → Déposer (ambre, compte)
    _res("D", "jamais vérifiée"),    # gris → PAS de ligne (appelle l'agent depuis Sources)
    _res("E", "à jour"),             # mint → rien
    _res("F", "sonde en panne"),     # rouge → Décider (compte)
]
FUITES_ROB = [{"id": "exports_recette", "nom": "Recette des exports"}]   # 1 robinet lit hors moteur
ECARTS = [{"chiffre_id": "parcelles_potentiel", "robinet_a": "table communes", "valeur_a": 1812,
           "robinet_b": "fiche commune", "valeur_b": 1790, "robinet_a_id": None}]              # 1 écart ouvert
VERROUS = {"casses": ["G8"]}         # 1 verrou cassé → Décider


def _compose(**kw):
    base = dict(residuel=None, candidat="q_v15", run_servi="q_v11",
                verrous=VERROUS, fuites_robinets=FUITES_ROB, ecarts=ECARTS,
                etats_compte={"nouvelle version": 2, "échue": 1, "sonde en panne": 1,
                              "jamais vérifiée": 1, "à jour": 1, "total": 6})
    base.update(kw)
    return R.composer_a_faire(RESERVOIRS, **base)


def test_fuite_et_ecart_ont_desormais_leur_ligne():
    """Le bug fermé : sans les lignes fuite/écart, le compte oublierait 2 pastilles rouges."""
    af = _compose()
    titres = [l["titre"] for l in af["lignes"]]
    assert any("fuite" in t and "hors moteur" in t for t in titres)     # la fuite a sa ligne
    assert any("écart" in t and "diffère" in t for t in titres)          # l'écart a sa ligne
    # sans ces deux lignes, on aurait raté 2 pastilles → l'invariant serait faux (le bug).
    sans_fuite_ecart = sum(1 for l in af["lignes"] if l["bouton"]["action"] != "decider"
                           or ("fuite" not in l["titre"] and "écart" not in l["titre"]))
    assert af["total"] - sans_fuite_ecart == 2


def test_invariant_compteur_egale_lignes_egale_formule():
    af = _compose()
    # 1) compteur = nombre de lignes
    assert af["total"] == len(af["lignes"])
    # 2) = pastilles non vertes (Sources : 2 nouvelle + 1 échue + 1 panne) + Circuit (1 fuite + 1
    #    écart + 1 verrou) + actions (Calculer 0 + Basculer 1) = 4 + 3 + 1 = 8
    attendu = (2 + 1 + 1) + (1 + 1 + 1) + (0 + 1)
    assert af["total"] == attendu
    # 3) = la fonction unique total_a_faire (celle que lit la tuile Pilotage) sur les MÊMES entrées
    assert af["total"] == R.total_a_faire(
        RESERVOIRS, fuites_robinets=FUITES_ROB, ecarts=ECARTS, verrous=VERROUS,
        candidat="q_v15", residuel=None)


def test_jamais_verifiee_ne_fait_pas_de_ligne_mais_va_au_calme():
    af = _compose()
    assert not any("jamais" in l["titre"].lower() for l in af["lignes"])   # pas de ligne
    assert af["calme"]["jamais"] == 1                                       # dit dans « Rien d'autre »


def test_ordre_rouge_puis_ambre():
    af = _compose()
    couleurs = [l["couleur"] for l in af["lignes"]]
    # tous les rouges viennent avant tous les ambres (pas d'alternance).
    premier_ambre = next((i for i, c in enumerate(couleurs) if c == "ambre"), len(couleurs))
    assert all(c == "rouge" for c in couleurs[:premier_ambre])
    assert all(c == "ambre" for c in couleurs[premier_ambre:])


def test_tout_coule_zero_ligne():
    af = R.composer_a_faire([_res("Z", "à jour")], residuel=None, candidat=None, run_servi="q",
                            verrous={}, fuites_robinets=[], ecarts=[],
                            etats_compte={"total": 1})
    assert af["total"] == 0 and af["lignes"] == []
