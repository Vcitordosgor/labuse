"""CIRCUIT-1 lot 3 — la pompe unifiée : le MANIFESTE de service, le journal des gestes,
la note de version, la garde résiduel.

On NE bascule JAMAIS pour de vrai (ça réécrirait config/served_manifest.json et
served_run.txt — même règle que test_flux) : le manifeste est testé sur un fichier
TEMPORAIRE (monkeypatch de manifeste._FICHIER), la bascule par ses briques.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse import circuit_journal, manifeste

pytestmark = pytest.mark.db


@pytest.fixture
def manifeste_tmp(tmp_path, monkeypatch):
    f = tmp_path / "served_manifest.json"
    monkeypatch.setattr(manifeste, "_FICHIER", f)
    manifeste.invalidate()
    yield f
    manifeste.invalidate()


def test_31_ecrire_atomique_et_lire(manifeste_tmp):
    m = {"scoring_run": "q_x", "residuel_run_seq": 2, "mvt_run": "q_x", "division_run": "q_x",
         "promoted_at": "2026-09-05T12:00:00+00:00", "par": "test",
         "precedent": {"scoring_run": "q_w", "residuel_run_seq": 1, "mvt_run": "q_w", "division_run": "q_w"}}
    manifeste.ecrire(m)
    assert manifeste_tmp.exists()
    assert not manifeste_tmp.with_suffix(".json.tmp").exists(), "écrit par tmp + os.replace"
    manifeste.invalidate()
    lu = manifeste.lire()
    assert lu == m
    assert json.loads(manifeste_tmp.read_text())["scoring_run"] == "q_x"


def test_31_manifeste_incomplet_refuse(manifeste_tmp):
    with pytest.raises(ValueError, match="incomplet"):
        manifeste.ecrire({"scoring_run": "q_x", "mvt_run": None, "division_run": "q_x"})
    assert not manifeste_tmp.exists(), "un pointeur partiel ne s'écrit JAMAIS"


def test_31_runs_current_lit_le_manifeste(manifeste_tmp, monkeypatch):
    from labuse import runs
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    # la garde tests de runs.current() exige que manifeste et served_run.txt vivent dans le
    # MÊME dossier : on aligne les deux sur le tmp.
    monkeypatch.setattr(runs, "_SERVED_FILE", manifeste_tmp.parent / "served_run.txt")
    monkeypatch.setattr(runs, "_PRECEDENT_FILE", manifeste_tmp.parent / "run_precedent.txt")
    manifeste.ecrire({"scoring_run": "q_manifeste", "residuel_run_seq": None,
                      "mvt_run": "q_manifeste", "division_run": "q_manifeste",
                      "promoted_at": None, "par": "test", "precedent": {"scoring_run": "q_avant"}})
    runs.invalidate()
    assert runs.current() == "q_manifeste", "le manifeste fait foi quand il existe"
    assert runs.precedent() == "q_avant"
    runs.invalidate()   # ne pas polluer les autres tests


def test_31_division_run_repli_scoring(manifeste_tmp, monkeypatch):
    """Tant que le manifeste n'est pas posé : division_run() = run courant (aucun changement
    de comportement avant la première pose)."""
    monkeypatch.setenv("LABUSE_SERVED_RUN", "q_repli")
    assert not manifeste.existe()
    assert manifeste.division_run() == "q_repli"


def test_31_bootstrap_depuis_pointeurs(db_session, manifeste_tmp, monkeypatch):
    monkeypatch.setenv("LABUSE_SERVED_RUN", "q_boot")
    m = manifeste.construire_depuis_pointeurs(db_session)
    assert m["scoring_run"] == "q_boot" and m["mvt_run"] == "q_boot" and m["division_run"] == "q_boot"
    manifeste.ecrire(m)          # le bootstrap produit un manifeste complet, écrivable
    assert manifeste.lire()["par"].startswith("bootstrap")


def test_36_circuit_journal_qui_quand_quoi(db_session):
    circuit_journal.journaliser(db_session, "injecter", "SITADEL (test)", "vic@labuse.re",
                                "lance", {"job": "sitadel"})
    row = db_session.execute(text(
        "SELECT geste, cible, par, resultat, details FROM circuit_journal "
        "WHERE cible = 'SITADEL (test)' ORDER BY id DESC LIMIT 1")).mappings().first()
    assert row and row["par"] == "vic@labuse.re" and row["resultat"] == "lance"
    assert row["details"]["job"] == "sitadel"


def test_33_note_version_registre(db_session, monkeypatch):
    """La note de version vient du REGISTRE : chiffres à portée run + réservoirs (photo ou état
    courant). Sur un candidat inconnu, la note reste honnête (écart None, jamais un crash)."""
    from labuse import bascule_flux
    monkeypatch.setenv("LABUSE_SERVED_RUN", "q_servi_test")
    note = bascule_flux.note_version(db_session, "q_candidat_inconnu")
    assert note["candidat"] == "q_candidat_inconnu" and note["servi"] == "q_servi_test"
    assert "tier_opportunite" in note["chiffres_recalcules"], "les chiffres portée run du registre"
    assert isinstance(note["reservoirs"], list)
    ecart = note["ecart_classement"]
    assert ecart is None or ecart.get("ok") is False, \
        "candidat non scoré : la note le DIT (motif), jamais un écart inventé"


def test_32_residuel_entrees_changees_honnete(db_session):
    """Sans chaîne résiduel servie : « aucun run résiduel servi » (jamais un crash ni un faux oui)."""
    from labuse import bascule_flux
    d = bascule_flux.residuel_entrees_changees(db_session)
    assert d["changees"] is False
    assert "résiduel" in d["detail"] or "servi" in d["detail"]
