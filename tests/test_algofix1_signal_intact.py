"""ALGO-FIX-1 — preuve que le Signal de mutation est INTACT (décision Vic D6, spec §12).

Deux garde-fous :
  1. STRUCTUREL — aucun fichier de la chaîne du Signal (modèle gelé, prétraitement, calibration,
     seuils, politique de service) n'est modifié par cette branche. C'est la traduction directe du
     « Zéro changement sur les sorties du Signal » de la recette : on ne change pas ce qu'on ne
     touche pas. (Marqueur `local` : lit git, aucune base.)
  2. COMPORTEMENTAL — le cœur V2 RELAIE la probabilité et le niveau servis sans les recalculer, et
     ne fabrique jamais une probabilité (absence ≠ zéro, hors-bornes ≠ écrêté). (Marqueur `reel`
     pour la vérification sur parcelle réelle ; les invariants purs sont dans le contrat.)
"""
from __future__ import annotations

import os
import subprocess

import pytest

# Chaîne du Signal : variables, WoE, coefficients, intercept, calibration, seuils, politique de
# service, verrou Priorité. Modifier l'un d'eux exigerait une validation séparée (spec §12) — ce
# mandat ne le fait pas.
FICHIERS_SIGNAL = {
    "src/labuse/scoring/signal_mutation.py",
    "src/labuse/scoring/tiers_client.py",
    "src/labuse/scoring/status.py",
    "src/labuse/scoring/p_model/model.py",
    "src/labuse/scoring/p_model/features.py",
    "src/labuse/scoring/p_model/woe.py",
    "src/labuse/scoring/p_model/evaluate.py",
    "src/labuse/scoring/p_model/ext_sql.py",
    "src/labuse/scoring/p_model/sql.py",
    "src/labuse/scoring/p_v2/statuts.py",
    "src/labuse/scoring/p_v2/qv15.py",
    "config/scoring_client.yaml",
    "config/mutation_weights.yaml",
    "frontend/src/lib/status.ts",
}


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args) -> str:
    return subprocess.check_output(["git", *args], cwd=_repo_root(), text=True,
                                   stderr=subprocess.DEVNULL)


@pytest.mark.local
def test_aucun_fichier_du_signal_modifie():
    try:
        base = _git("merge-base", "main", "HEAD").strip()
    except Exception:
        pytest.skip("hors dépôt git ou branche main absente")
    # Tout ce que cette branche a touché : commité (base…working) + non commité + non suivi.
    touches = set()
    for ref in (base,):
        touches |= {l for l in _git("diff", "--name-only", ref).splitlines() if l}
    touches |= {l for l in _git("status", "--porcelain").splitlines()}
    touches = {l[3:] if len(l) > 3 and l[2] == " " else l for l in touches}
    touches = {l.strip() for l in touches if l.strip()}
    intrus = sorted(FICHIERS_SIGNAL & touches)
    assert not intrus, f"la branche modifie des fichiers du Signal (interdit D6) : {intrus}"


@pytest.mark.local
def test_cover_le_module_v2_n_importe_aucune_ecriture_signal():
    # Le cœur V2 et son adaptateur ne doivent contenir AUCUNE écriture SQL (INSERT/UPDATE/UPSERT)
    # ni aucun recalcul de probabilité : la V2 se calcule en parallèle, en lecture seule (spec §14).
    root = _repo_root()
    for rel in ("src/labuse/scoring/scenarios_v2.py", "src/labuse/scoring/scenarios_v2_build.py"):
        txt = open(os.path.join(root, rel), encoding="utf-8").read().upper()
        for mot in ("INSERT INTO", "UPDATE ", "UPSERT", "DELETE FROM", "DROP ", "ALTER "):
            assert mot not in txt, f"{rel} contient une écriture interdite : {mot}"


@pytest.mark.reel
def test_signal_relaye_a_l_identique(db_session_reel):
    """Sur parcelles réelles : la probabilité et le niveau exposés par la V2 sont EXACTEMENT ceux
    servis par `score_labuse` (relais, pas recalcul)."""
    from sqlalchemy import text
    from labuse.scoring import scenarios_v2 as v2, scenarios_v2_build as build
    rows = db_session_reel.execute(text(
        "SELECT parcel_id, idu, signal_p, signal_niveau FROM score_labuse "
        "WHERE run_label='q_v20' AND signal_p IS NOT NULL ORDER BY idu LIMIT 50")).fetchall()
    ids = [r[0] for r in rows]
    recs = {rec.id: rec for rec, _ in build.records_for_parcels(db_session_reel, ids)}
    for pid, idu, p, niveau in rows:
        rec = recs.get(idu)
        assert rec is not None
        r = v2.evaluate(rec, {"mode": "sale"})
        assert r.signal["p"] == float(p)
        assert r.signal["niveau"] == niveau            # niveau servi, inchangé


@pytest.fixture(scope="module")
def db_session_reel():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    url = os.environ.get("LABUSE_REEL_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_REEL_DATABASE_URL non défini")
    eng = create_engine(url)
    conn = eng.connect()
    trans = conn.begin()
    sess = Session(bind=conn)
    try:
        if sess.execute(text("SELECT count(*) FROM score_labuse WHERE run_label='q_v20'")).scalar() == 0:
            pytest.skip("run q_v20 absent")
        yield sess
    finally:
        sess.close()
        trans.rollback()
        conn.close()
        eng.dispose()
