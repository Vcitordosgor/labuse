"""CIRCUIT-P4 (lot 4) — la règle injection → recalcul, testée SANS base (fonction pure).

Le mandat exige un test qui construit les deux cas : injecter une source qui nourrit le scoring →
la ligne « Calculer » apparaît ; une source qui ne nourrit rien → rien. On ajoute les cas résiduel,
règles PLU, et le repli sur le signal résiduel existant.
"""
from labuse import circuit_dependance as D

RUN = "2026-09-10T00:00:00+00:00"
APRES = "2026-09-20T00:00:00+00:00"
AVANT = "2026-09-01T00:00:00+00:00"


def test_moteurs_lus_du_registre():
    """Le mapping source → moteur vient de moteurs.csv (le registre), pas d'un dur."""
    par = D.sources_par_famille()
    # résiduel lit CoSIA / BD TOPO / cadastre ; le scoring lit en plus Sitadel, DVF, BODACC…
    assert "cosia" in par["residuel"] and "bd_topo" in par["residuel"]
    assert "sitadel" in par["scoring"] and "dvf" in par["scoring"]
    assert D.nourrit("sitadel") == {"residuel": False, "scoring": True}
    assert D.nourrit("cosia")["residuel"] is True
    assert D.nourrit("ban") == {"residuel": False, "scoring": False}


def test_source_scoring_injectee_fait_apparaitre_calculer():
    """Injecter une source qui nourrit le scoring APRÈS le run servi → la ligne apparaît."""
    res = [{"nom": "SITADEL", "slug": "sitadel", "ingere_le": APRES}]
    ligne = D.calculer_ligne(res, run_servi_date=RUN)
    assert ligne["actif"] is True
    assert ligne["titre"] == "Calculer le score"
    assert "score" in ligne["touche"]
    assert any("SITADEL" in c for c in ligne["changements"])


def test_source_residuel_injectee_touche_le_score_aussi():
    """Une source du résiduel (CoSIA) → « Calculer le résiduel » ET le score suit (Touche)."""
    res = [{"nom": "CoSIA", "slug": "cosia", "ingere_le": APRES}]
    ligne = D.calculer_ligne(res, run_servi_date=RUN)
    assert ligne["actif"] and ligne["titre"] == "Calculer le résiduel"
    assert "capacité" in ligne["touche"] and "score" in ligne["touche"]


def test_source_neutre_ne_declenche_rien():
    """Une source qui ne nourrit ni le résiduel ni le scoring (BAN) → RIEN."""
    res = [{"nom": "BAN", "slug": "ban", "ingere_le": APRES}]
    assert D.calculer_ligne(res, run_servi_date=RUN) == {"actif": False}


def test_source_scoring_injectee_avant_le_run_ne_declenche_rien():
    """Injectée AVANT le run servi : le run la connaît déjà → rien à recalculer."""
    res = [{"nom": "SITADEL", "slug": "sitadel", "ingere_le": AVANT}]
    assert D.calculer_ligne(res, run_servi_date=RUN) == {"actif": False}


def test_regles_plu_changees_declenchent_calculer():
    """Un commit qui change les règles PLU → « Calculer le résiduel », communes listées."""
    ligne = D.calculer_ligne([], run_servi_date=RUN, plu_changees=["97411", "97415"])
    assert ligne["actif"] and ligne["titre"] == "Calculer le résiduel"
    assert any("97411" in c for c in ligne["changements"])
    assert "capacité" in ligne["touche"]


def test_repli_signal_residuel_existant():
    """Sans injection ni PLU, le signal résiduel existant (entrées PLU/GPU/cadastre) suffit."""
    ligne = D.calculer_ligne([], run_servi_date=RUN,
                             residuel={"changees": True, "detail": "Urbanisme PLU/GPU"})
    assert ligne["actif"] and "Urbanisme PLU/GPU" in " ".join(ligne["changements"])


def test_rien_du_tout():
    """Aucun déclencheur → aucune ligne."""
    assert D.calculer_ligne([], run_servi_date=RUN, residuel={"changees": False}) == {"actif": False}
