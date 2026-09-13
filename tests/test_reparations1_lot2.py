"""REPARATIONS-1 lot 2 — (a) les lectures fines : chaque arête source→lecteur porte son
chiffre + robinet (vérifiés contre le registre) ou sa raison de machinerie, et le graphe est
exact dans les deux sens (dette 0, périmées 0) ; (b) le palier « Priorité » n'est plus servi
(décision Vic, réversible) : la tête classée entière porte « À suivre », la phrase du modèle
affiche le ×6,7 en marche avant, jamais le ×13,3 contaminé."""
from __future__ import annotations


def test_lectures_fines_integres_au_registre():
    from labuse.registre.donnees import DONNEES
    from labuse.registre.lectures import LECTURES
    from labuse.registre.robinets import ROBINETS
    from labuse.registre.tables import reservoirs_de
    assert len(LECTURES) >= 213
    for x in LECTURES:
        if x.chiffre is None:
            assert x.robinet is None
            assert x.note.strip(), f"machinerie sans raison écrite : {x.table} / {x.fichier}"
            continue
        assert x.chiffre in DONNEES, f"chiffre inconnu : {x.chiffre}"
        assert x.robinet in ROBINETS, f"robinet inconnu : {x.robinet}"
        assert x.chiffre in ROBINETS[x.robinet].chiffres, \
            f"le robinet {x.robinet} ne porte pas {x.chiffre}"
        assert set(DONNEES[x.chiffre].reservoirs) & set(reservoirs_de(x.table)), \
            f"{x.chiffre} n'appartient pas au réservoir de {x.table}"


def test_graphe_exact_dans_les_deux_sens():
    from labuse.circuit_garanties import lecteurs_non_declares, lectures_perimees
    assert lecteurs_non_declares() == [], "toute arête du code doit être déclarée finement"
    assert lectures_perimees() == [], "toute déclaration doit correspondre à une lecture du code"


def test_priorite_non_servie_tete_classee_a_suivre():
    from labuse.scoring import tiers_client as tc
    assert tc.PRIORITE_SERVIE is False
    for code in ("priorite", "brulante"):
        assert tc.code_palier(code) == "a_suivre"
        assert tc.court(code) == "À suivre"
    assert tc.court("chaude") == "À suivre"
    assert tc.court("sans_signal") == "Sans signal"
    # le filtrage « À suivre » couvre la tête classée entière (codes stockés, jamais réécrits)
    assert set(tc.codes_stockes("a_suivre")) == {"brulante", "chaude", "priorite", "a_suivre"}
    # réversibilité prouvée : drapeau à True → le palier revient tel quel, aucun rescoring
    tc.PRIORITE_SERVIE = True
    try:
        assert tc.code_palier("brulante") == "priorite"
        assert tc.court("priorite") == "Priorité"
    finally:
        tc.PRIORITE_SERVIE = False


def test_phrase_modele_marche_avant():
    from labuse.scoring.backtest import phrase_client, rr_marche_avant
    rr = rr_marche_avant()
    assert rr is not None and 6.0 < rr < 7.5   # le ×6,7 du fold 2025 out-of-sample (config gelée)
    bt = {"fenetre_fin": "2026-08-10", "base_pct": 0.4,
          "paliers": [{"tier": "chaude", "label": "À suivre", "n": 1367, "mutees": 70,
                       "taux_pct": 5.3, "lift": 13.26}],
          "filtres": {"realiste": {"libelle": "réaliste", "n": 30516, "mutees": 374,
                                   "taux_pct": 1.27, "lift": 3.17}}}
    p = phrase_client(bt)
    assert p and "6,7" in p and "marche avant" in p
    assert "13,3" not in p, "le lift contaminé (2025 = cible de recalage ET mesure) ne sort jamais"
