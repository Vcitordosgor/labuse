"""DEPLOY-GROUPE-3 (q_v23) — la vue `parcel_residuel` lit un run CANDIDAT par numéro, sans le servir.

Le Score LABUSE et les features du Signal lisent le résiduel par la VUE `parcel_residuel`, filtrée
sur le run SERVI. Pour calculer et contrôler un run candidat q_v23 sur SON propre résiduel AVANT la
promotion — sans toucher le run servi ni ce que voit le client —, la vue honore désormais un réglage
de session `labuse.residuel_run_seq` (défaut : run servi). Posé par l'env `LABUSE_RESIDUEL_RUN_SEQ`
au connect (db.make_engine) ou par `apply_residuel_run_seq`.

GARANTIE DE NON-RÉGRESSION (exigée par Vic) : viser le run SERVI par ce chemin paramétré rend un Score
IDENTIQUE au chemin actuel (vue par défaut). Les sessions client ne posent jamais le réglage → run
servi, service inchangé.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.residuel_runs import (apply_residuel_run_seq,
                                              ensure_runs_schema, served_run_seq,
                                              _view_sql)


def test_view_sql_contient_le_reglage_de_session():
    """Le SQL de la vue retombe sur le run servi via COALESCE du réglage de session (pur, sans DB)."""
    sql = _view_sql(or_replace=True)
    assert "current_setting('labuse.residuel_run_seq', true)" in sql
    assert "residuel_runs WHERE is_served" in sql
    assert "COALESCE" in sql


@pytest.mark.reel
def test_vue_defaut_egale_run_servi():
    """Sans réglage, la vue = le run servi (comportement historique, inchangé)."""
    with session_scope() as s:
        ensure_runs_schema(s.connection())
        servi = served_run_seq(s.connection())
        apply_residuel_run_seq(s, None)                       # réinitialise (lecture du servi)
        n_vue = s.execute(text("SELECT count(*) FROM parcel_residuel")).scalar()
        n_servi = s.execute(text("SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=:r"),
                            {"r": servi}).scalar()
        assert n_vue == n_servi


@pytest.mark.reel
def test_vue_vise_un_run_candidat_sans_servir():
    """Avec le réglage posé sur un run NON servi, la vue lit CE run — et `is_served` ne bouge pas."""
    with session_scope() as s:
        ensure_runs_schema(s.connection())
        apply_residuel_run_seq(s, None)                       # repart d'un état propre
        servi = served_run_seq(s.connection())
        seqs = [r[0] for r in s.execute(text(
            "SELECT run_seq FROM parcel_residuel_runs GROUP BY run_seq ORDER BY run_seq"))]
        cands = [x for x in seqs if x != servi]
        if not cands:
            pytest.skip("aucun run candidat en base pour ce test")
        cand = cands[-1]
        apply_residuel_run_seq(s, cand)
        n_vue = s.execute(text("SELECT count(*) FROM parcel_residuel")).scalar()
        n_cand = s.execute(text("SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=:r"),
                           {"r": cand}).scalar()
        assert n_vue == n_cand
        # is_served INTACT
        assert served_run_seq(s.connection()) == servi
        apply_residuel_run_seq(s, None)


@pytest.mark.reel
def test_score_sur_run_servi_identique_par_les_deux_chemins():
    """GARANTIE Vic : le Score calculé en VISANT le run servi (chemin paramétré) == Score par la vue
    par défaut, à l'identique, sur un échantillon de parcelles."""
    from labuse.scoring.score_labuse import score_batch
    with session_scope() as s:
        ensure_runs_schema(s.connection())
        servi = served_run_seq(s.connection())
        ids = [r[0] for r in s.execute(text(
            "SELECT id FROM parcels ORDER BY id LIMIT 400"))]

    def _scores(run_seq):
        with session_scope() as s:
            apply_residuel_run_seq(s, run_seq)
            lignes = score_batch(s, ids, "test_rseq", cascade_label=None)
            return {l.parcel_id: (l.bande, l.score, l.sdp_residuelle_m2) for l in lignes}

    defaut = _scores(None)          # vue par défaut (run servi)
    vise = _scores(servi)           # chemin paramétré, visant le run servi
    assert defaut == vise, "le Score en visant le run servi doit être identique à la vue par défaut"
