"""INJECTION-SOLIDE-1 — l'EFFET d'une source + le résumé « Où en est la mise à jour ? » (purs)."""
from labuse import circuit_maj as m


def test_effet_classement_vs_direct():
    assert m.effet(True)["code"] == "classement"
    assert m.effet(True)["phrase"] == "entre dans le classement, déclenche un nouveau calcul"
    assert m.effet(False)["code"] == "direct"
    assert m.effet(False)["phrase"] == "lue directement, visible le lendemain matin"


def test_resume_toujours_trois_phrases():
    r = m.resume_mise_a_jour(run_servi="q_v20", run_date="2026-10-31T18:46:50+04:00",
                             sources_changees=[], prochain_calcul="cette nuit 01:00")
    assert len(r) == 3
    assert r[0] == "Les clients sont servis en q_v20, calculé le 2026-10-31."
    assert r[1] == "Aucune source n'a changé depuis — la version servie est à jour."
    assert r[2] == "Rien à recalculer."


def test_resume_source_du_score_reclame_recalcul():
    r = m.resume_mise_a_jour(
        run_servi="q_v20", run_date="2026-10-31",
        sources_changees=[{"nom": "DVF / valeurs foncières", "dans_le_score": True},
                          {"nom": "Base Adresse Nationale", "dans_le_score": False}],
        prochain_calcul="cette nuit 01:00")
    assert "2 sources ont changé" in r[1]
    assert "1 entre dans le classement" in r[1]
    assert "nouveau calcul est nécessaire" in r[1]
    assert r[2] == "Prochain calcul prévu : cette nuit 01:00."


def test_resume_changes_mais_toutes_directes_pas_de_recalcul():
    r = m.resume_mise_a_jour(
        run_servi="q_v20", run_date="2026-10-31",
        sources_changees=[{"nom": "Base Adresse Nationale", "dans_le_score": False}],
        prochain_calcul=None)
    assert "toutes lues directement" in r[1]
    assert "visibles sans recalcul" in r[1]
    assert r[2] == "Rien à recalculer."


def test_resume_calcul_en_cours_prime():
    r = m.resume_mise_a_jour(
        run_servi="q_v20", run_date="2026-10-31",
        sources_changees=[{"nom": "DVF / valeurs foncières", "dans_le_score": True}],
        prochain_calcul="cette nuit 01:00", calcul_en_cours=True)
    assert r[2] == "Un calcul tourne en ce moment sur le serveur."


def test_resume_singulier_une_source():
    r = m.resume_mise_a_jour(
        run_servi="q_v20", run_date=None,
        sources_changees=[{"nom": "DVF / valeurs foncières", "dans_le_score": True}],
        prochain_calcul="cette nuit")
    assert r[0] == "Les clients sont servis en q_v20 (date de calcul inconnue)."
    assert "1 source a changé" in r[1]
    assert "1 entre dans le classement" in r[1]


def test_apercu_borne():
    assert m._apercu(["a", "b", "c", "d", "e"]) == "a, b, c et 2 autres"
    assert m._apercu(["a", "b", "c", "d"]) == "a, b, c et 1 autre"
    assert m._apercu(["a"]) == "a"
    assert m._apercu([]) == ""
