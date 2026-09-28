"""ALGO-FIX-1 (point 1) — LE RÉSIDUEL A UNE SEULE VÉRITÉ : `residuel_runs.is_served`.

Bug E6 : le manifeste portait `residuel_run_seq=8` alors que `is_served=10` ; `basculer()` rejouait
`set_served(db, 8)` → la bascule scoring suivante aurait fait RECULER le résiduel de 10 à 8, en silence.

Le correctif : la bascule scoring ne lit ni n'écrit JAMAIS le résiduel ; le manifeste ne fait que
RECOPIER `is_served`. Ce test reproduit E6 (manifeste périmé) et prouve qu'une bascule scoring laisse
le résiduel EXACTEMENT où il est, et réaligne le miroir du manifeste sur la vérité.

On ne bascule jamais pour de vrai (pointeurs redirigés sur un tmp, collaborateurs lourds neutralisés) ;
la base de test est transactionnelle (rollback par conftest).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import bascule_flux, circuit_journal, coherence_flux, golden_ops, manifeste, runs

pytestmark = pytest.mark.db

_JOURNAL_DDL = (
    "CREATE TABLE IF NOT EXISTS run_bascule_journal ("
    " id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),"
    " ancien varchar(64), nouveau varchar(64) NOT NULL,"
    " par varchar(120), sens varchar(12) NOT NULL DEFAULT 'avant',"
    " caches_purges jsonb NOT NULL DEFAULT '[]'::jsonb, coherence jsonb)")


def _table_existe(db, nom: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:n)"), {"n": nom}).scalar())


@pytest.fixture
def bascule_tmp(tmp_path, monkeypatch):
    """Redirige les pointeurs FICHIER sur un tmp et neutralise les collaborateurs lourds. Manifeste
    de départ PÉRIMÉ : residuel_run_seq=8 (repro E6). La cascade/journal/cohérence ne font rien."""
    monkeypatch.setattr(manifeste, "_FICHIER", tmp_path / "served_manifest.json")
    monkeypatch.setattr(runs, "_SERVED_FILE", tmp_path / "served_run.txt")
    monkeypatch.setattr(runs, "_PRECEDENT_FILE", tmp_path / "run_precedent.txt")
    monkeypatch.setattr(bascule_flux, "_RUN_PRECEDENT_FILE", tmp_path / "run_precedent.txt")
    monkeypatch.setattr(golden_ops, "_SERVED_FILE", tmp_path / "served_run.txt")
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    monkeypatch.setattr(bascule_flux, "_run_complet", lambda db, run: (True, "test : complet"))
    monkeypatch.setattr(bascule_flux, "resoudre_cascade_run", lambda db, run: (run, "test"))
    monkeypatch.setattr(bascule_flux, "purger_caches_run", lambda: [])
    monkeypatch.setattr(coherence_flux, "verifier", lambda db, run: {"ok": True})
    monkeypatch.setattr(circuit_journal, "journaliser", lambda *a, **k: None)

    def _fake_promote(run: str) -> dict:
        ancien = runs.current()
        (tmp_path / "served_run.txt").write_text(run + "\n", encoding="utf-8")
        runs.invalidate()
        return {"ok": True, "ancien": ancien, "nouveau": run}
    monkeypatch.setattr(golden_ops, "promote", _fake_promote)

    manifeste.ecrire({"scoring_run": "q_old", "cascade_run": "q_old", "residuel_run_seq": 8,
                      "mvt_run": "q_old", "division_run": "q_old", "promoted_at": None, "par": "test",
                      "precedent": {"scoring_run": "q_older", "cascade_run": "q_older",
                                    "residuel_run_seq": 8, "mvt_run": "q_older", "division_run": "q_older"}})
    (tmp_path / "served_run.txt").write_text("q_old\n", encoding="utf-8")
    (tmp_path / "run_precedent.txt").write_text("q_older\n", encoding="utf-8")
    runs.invalidate()
    yield tmp_path
    runs.invalidate()


def test_bascule_scoring_ne_recule_pas_le_residuel(db_session, bascule_tmp):
    """Le CŒUR d'E6 : is_served=10 en base, manifeste périmé=8 → une bascule scoring laisse is_served
    à 10 (ne rejoue plus set_served) et le manifeste recopie 10 (la vérité), pas 8."""
    if not _table_existe(db_session, "residuel_runs"):
        pytest.skip("chaîne résiduel absente de la base de test")
    db_session.execute(text(_JOURNAL_DDL))
    # état résiduel de test : seq 8 (non servi) et seq 10 (SERVI) — reproduit l'écart E6.
    db_session.execute(text("UPDATE residuel_runs SET is_served = false WHERE is_served"))
    for seq, served in ((8, False), (10, True)):
        db_session.execute(text(
            "INSERT INTO residuel_runs (run_seq, label, is_served) VALUES (:s, :l, :v) "
            "ON CONFLICT (run_seq) DO UPDATE SET is_served = EXCLUDED.is_served, label = EXCLUDED.label"),
            {"s": seq, "l": f"test-seq-{seq}", "v": served})

    avant = db_session.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    assert avant == 10

    res = bascule_flux.basculer(db_session, "q_new", par="test")
    assert res["ok"] is True and res["nouveau"] == "q_new"

    apres = db_session.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    assert apres == 10, "la bascule scoring ne touche PAS le résiduel (is_served reste 10)"

    m = manifeste.lire()
    assert m["residuel_run_seq"] == 10, "le manifeste RECOPIE is_served (10), pas la valeur périmée (8)"
    assert m["precedent"]["residuel_run_seq"] == 10, "le précédent aussi recopie la vérité (pas de recul au retour arrière)"
    assert m["scoring_run"] == "q_new", "le scoring a bien basculé"


def test_retour_arriere_ne_recule_pas_le_residuel(db_session, bascule_tmp):
    """Retour arrière (q_new → q_old) : même garantie — le résiduel ne bouge pas, is_served reste 10."""
    if not _table_existe(db_session, "residuel_runs"):
        pytest.skip("chaîne résiduel absente de la base de test")
    db_session.execute(text(_JOURNAL_DDL))
    db_session.execute(text("UPDATE residuel_runs SET is_served = false WHERE is_served"))
    for seq, served in ((8, False), (10, True)):
        db_session.execute(text(
            "INSERT INTO residuel_runs (run_seq, label, is_served) VALUES (:s, :l, :v) "
            "ON CONFLICT (run_seq) DO UPDATE SET is_served = EXCLUDED.is_served, label = EXCLUDED.label"),
            {"s": seq, "l": f"test-seq-{seq}", "v": served})
    # bascule vers le précédent q_older (retour arrière)
    res = bascule_flux.basculer(db_session, "q_older", par="test")
    assert res["ok"] is True and res.get("sens") == "arriere"
    apres = db_session.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
    assert apres == 10, "retour arrière : le résiduel reste seq 10"
    assert manifeste.lire()["residuel_run_seq"] == 10
