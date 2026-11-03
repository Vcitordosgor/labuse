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


# TABLEAU-1 — noms NON classés explicitement → classe B par défaut → font une ligne « Injecter ».
RESERVOIRS = [
    _res("A", "nouvelle version"),   # classe B (défaut) → Injecter (ambre, compte)
    _res("B", "nouvelle version"),   # classe B (défaut) → Injecter
    _res("C", "échue"),              # → Déposer (ambre, compte)
    _res("D", "jamais vérifiée"),    # gris → PAS de ligne (appelle l'agent depuis Sources)
    _res("E", "à jour"),             # mint → rien
    _res("F", "sonde en panne"),     # TABLEAU-1 : non bloquant → PLUS de ligne (va en « tout tourne »)
]
FUITES_ROB = [{"id": "exports_recette", "nom": "Recette des exports"}]   # 1 robinet lit hors moteur
ECARTS = [{"chiffre_id": "parcelles_potentiel", "robinet_a": "table communes", "valeur_a": 1812,
           "robinet_b": "fiche commune", "valeur_b": 1790, "robinet_a_id": None}]              # 1 écart ouvert
# 1 verrou BLOQUANT (V1c) → Décider ; G8 (avertissement) ne compte PAS (TABLEAU-1 → section santé).
VERROUS = {"casses": ["V1c", "G8"]}


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
    # 2) = pastilles non vertes (Sources : 2 nouvelle version CLASSE B + 1 échue ; la sonde en panne ne
    #    compte plus — TABLEAU-1) + Circuit (1 fuite + 1 écart + 1 verrou BLOQUANT ; G8 exclu)
    #    + actions (Calculer 0 + Basculer 1) = 3 + 3 + 1 = 7
    attendu = (2 + 1) + (1 + 1 + 1) + (0 + 1)
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


def test_tuiles_perimees_comptent_dans_invariant():
    """DASHBOARD-FIX-1 (point 5) — la ligne bloquante « Reconstruire les tuiles » (tuiles périmées vs
    run servi) compte dans l'onglet ET dans total_a_faire : la tuile Pilotage et l'onglet « À faire »
    ne peuvent plus diverger (5 vs 9) quand une bascule laisse les tuiles en arrière."""
    tuiles = {"perime": True, "motif": "run", "run_carte": "q_v11", "run_servi": "q_v16"}
    af = _compose(tuiles=tuiles)
    assert any("Reconstruire les tuiles" in l["titre"] for l in af["lignes"])
    assert af["total"] == len(af["lignes"])
    # la fonction unique (tuile Pilotage) sur les MÊMES entrées, tuiles comprises
    assert af["total"] == R.total_a_faire(
        RESERVOIRS, fuites_robinets=FUITES_ROB, ecarts=ECARTS, verrous=VERROUS,
        candidat="q_v15", residuel=None, tuiles=tuiles)
    # une ligne de plus que sans tuiles périmées
    assert af["total"] == _compose()["total"] + 1


def test_classe_a_en_nouvelle_version_ne_fait_pas_de_ligne_injecter():
    """TABLEAU-1 (point 1) — une source de CLASSE A (ex. « Population légale (INSEE via geo.api.gouv) »)
    en nouvelle version s'injecte SEULE la nuit : elle ne doit JAMAIS faire de ligne « Injecter »
    (décision de Vic) ni compter dans total_a_faire. Une source structurante (classe B) en fait une."""
    res_a = {"id": 1, "nom": "Population légale (INSEE via geo.api.gouv)",
             "etat": ["ambre", "nouvelle version"], "vanne": {}, "veille": {}}
    res_b = {"id": 2, "nom": "DVF / valeurs foncières", "categorie": "marche",
             "etat": ["ambre", "nouvelle version"], "vanne": {}, "veille": {}}
    af = R.composer_a_faire([res_a, res_b], residuel=None, candidat=None, run_servi="q",
                            verrous={}, fuites_robinets=[], ecarts=[], etats_compte={"total": 2})
    titres = [l["titre"] for l in af["lignes"]]
    assert "Injecter Population légale (INSEE via geo.api.gouv)" not in titres   # classe A : auto nuit
    assert any("Injecter DVF" in t for t in titres)                             # classe B : clic de Vic
    assert af["total"] == 1
    assert af["total"] == R.total_a_faire([res_a, res_b], residuel=None, candidat=None)


def test_sonde_en_panne_ne_fait_plus_de_ligne():
    """TABLEAU-1 (point 3+5) — une sonde en panne (signal non bloquant) ne fait plus de carte « décider » :
    elle vit dans « Est-ce que tout tourne ? ». Donc 0 ligne, 0 dans total_a_faire."""
    res_f = {"id": 9, "nom": "OCS GE", "etat": ["rouge", "sonde en panne"], "vanne": {}, "veille": {}}
    af = R.composer_a_faire([res_f], residuel=None, candidat=None, run_servi="q",
                            verrous={}, fuites_robinets=[], ecarts=[], etats_compte={"total": 1})
    assert af["total"] == 0 and af["lignes"] == []
    assert R.total_a_faire([res_f]) == 0


def test_tout_coule_zero_ligne():
    af = R.composer_a_faire([_res("Z", "à jour")], residuel=None, candidat=None, run_servi="q",
                            verrous={}, fuites_robinets=[], ecarts=[],
                            etats_compte={"total": 1})
    assert af["total"] == 0 and af["lignes"] == []
