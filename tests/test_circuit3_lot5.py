"""CIRCUIT-3 lot 5 — LE FILTRE DE NUIT ET LA PAGE.

Job `filtres-sources` (registre), état du filtre par réservoir (mapping motif le plus long),
« servir quand même » qui lève la quarantaine, healthz (quarantaine > 7 j = avertissement).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import filtres, jobs
from labuse.filtres.cadre import Filtre

pytestmark = pytest.mark.db


def _pose_quarantaine(db, source, version, joue_le_sql="now()"):
    filtres._ensure_sur_session(db)
    db.execute(text(
        "INSERT INTO filtre_versions (source, version, verdict, bloquants_ko, avertissants_ko, joue_le) "
        f"VALUES (:s,:v,'quarantaine',1,0,{joue_le_sql})"), {"s": source, "v": version})
    db.execute(text(
        "INSERT INTO filtre_resultats (source,version,controle,nature,severite,valeur,seuil,verdict) "
        "VALUES (:s,:v,'d_bloc','distribution','bloquant','484','0','ko')"), {"s": source, "v": version})
    db.commit()


def test_job_filtres_sources_enregistre():
    assert "filtres-sources" in jobs.JOBS
    assert "filtres-sources" in jobs.TOUCHE_EAU
    # le nom se résout vers l'implémentation jobs_impl.filtres_sources
    from labuse import jobs_impl
    assert callable(getattr(jobs_impl, "filtres_sources"))


def test_servir_quand_meme_leve_quarantaine(db_session, monkeypatch):
    filtres._registre.cache_clear()
    reg = filtres._registre()
    reg["_c5_run"] = Filtre(source="_c5_run", libelle="r", source_motif=None, portee_run=True)
    monkeypatch.setattr(filtres, "sources_run", lambda: ["_c5_run"])
    try:
        _pose_quarantaine(db_session, "_c5_run", "courante")
        assert filtres.en_quarantaine(db_session, "_c5_run", "courante") is True
        assert len(filtres.garde_pompe(db_session)) == 1
        r = filtres.servir_quand_meme(db_session, "_c5_run", "vic@labuse", "source saine")
        db_session.commit()
        assert r["ok"] is True
        assert filtres.en_quarantaine(db_session, "_c5_run", "courante") is False
        assert filtres.garde_pompe(db_session) == []
    finally:
        db_session.execute(text("DELETE FROM filtre_versions WHERE source='_c5_run'"))
        db_session.execute(text("DELETE FROM filtre_resultats WHERE source='_c5_run'"))
        db_session.commit()
        filtres._registre.cache_clear()


def test_quarantaines_anciennes_seuil_7j(db_session):
    try:
        _pose_quarantaine(db_session, "_c5_vieux", "v1", "now() - interval '9 days'")
        _pose_quarantaine(db_session, "_c5_recent", "v1", "now()")
        vieux = {x["source"] for x in filtres.quarantaines_anciennes(db_session, jours=7)}
        assert "_c5_vieux" in vieux
        assert "_c5_recent" not in vieux
    finally:
        db_session.execute(text("DELETE FROM filtre_versions WHERE source IN ('_c5_vieux','_c5_recent')"))
        db_session.execute(text("DELETE FROM filtre_resultats WHERE source IN ('_c5_vieux','_c5_recent')"))
        db_session.commit()


def test_etat_pour_data_source_motif_le_plus_long(db_session):
    """« Géorisques — mouvements de terrain » doit matcher georisques_mvt, pas georisques_api."""
    e = filtres.etat_pour_data_source(db_session, "Géorisques — mouvements de terrain (DEAL/BRGM)")
    assert e["source"] == "georisques_mvt"
    e2 = filtres.etat_pour_data_source(db_session, "Géorisques")
    assert e2["source"] == "georisques_api"


def test_etats_servis_batch(db_session):
    try:
        _pose_quarantaine(db_session, "_c5_batch", "vb")
        etats = filtres.etats_servis(db_session)
        assert "_c5_batch" in etats
        assert etats["_c5_batch"]["verdict"] == "quarantaine"
        assert any(c["controle"] == "d_bloc" for c in etats["_c5_batch"]["controles"])
    finally:
        db_session.execute(text("DELETE FROM filtre_versions WHERE source='_c5_batch'"))
        db_session.execute(text("DELETE FROM filtre_resultats WHERE source='_c5_batch'"))
        db_session.commit()
