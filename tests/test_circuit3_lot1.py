"""CIRCUIT-3 lot 1 — LE CADRE DES FILTRES.

Invariant 1.5 : toute source de sources_ingestion.yaml a un filtre (sinon test rouge).
Contrôles universels (1.2) sur une table témoin. Quarantaine + garde de la pompe (1.4).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import filtres
from labuse.filtres import cadre
from labuse.filtres.cadre import Controle, Filtre

pytestmark = pytest.mark.db


# ─────────────────────────── 1.5 : une source à job = un filtre ───────────────────────────

def test_toute_source_a_job_a_un_filtre():
    """Le garde-fou du mandat : une source de la vanne SANS filtre = test rouge."""
    reg = filtres.FILTRES()
    manquants = [c["label"] for c in filtres.sources_a_job() if c["label"] not in reg]
    assert manquants == [], f"sources à job sans filtre : {manquants}"


def test_filtre_par_defaut_porte_au_moins_le_millesime():
    f = filtres.get_filtre("bodacc")
    ids = [c.id for c in f.controles_effectifs()]
    assert "u_millesime" in ids


# ─────────────────────────── table témoin pour les universels ───────────────────────────

@pytest.fixture
def table_temoin(db_session):
    db_session.execute(text("DROP TABLE IF EXISTS _c3_temoin"))
    db_session.execute(text(
        "CREATE TABLE _c3_temoin (idu varchar(20), insee varchar(5), "
        "d date, geom geometry(Point,4326))"))
    # 3 communes seulement (sur 24), une clé dupliquée, une date future, un point hors emprise.
    db_session.execute(text("""
        INSERT INTO _c3_temoin (idu, insee, d, geom) VALUES
        ('A', '97411', DATE '2020-01-01', ST_SetSRID(ST_MakePoint(55.45,-20.9),4326)),
        ('A', '97411', DATE '2020-01-02', ST_SetSRID(ST_MakePoint(55.46,-20.9),4326)),
        ('B', '97415', DATE '2099-01-01', ST_SetSRID(ST_MakePoint(55.5,-21.0),4326)),
        ('C', '97402', DATE '2021-01-01', ST_SetSRID(ST_MakePoint(2.35,48.8),4326))
    """))
    db_session.commit()
    yield
    db_session.execute(text("DROP TABLE IF EXISTS _c3_temoin"))
    db_session.commit()


def _filtre_temoin(**kw) -> Filtre:
    base = dict(source="_c3_temoin", libelle="témoin", table="_c3_temoin",
                cle=("idu",), insee_col="insee", geom_col="geom", date_cols=("d",))
    base.update(kw)
    return Filtre(**base)


def test_universels_attrapent_les_defauts(db_session, table_temoin):
    f = _filtre_temoin()
    v = cadre.jouer(db_session, f, version="v1")
    db_session.commit()
    par_id = {r["controle"]: r for r in v.resultats}
    assert par_id["u_communes"]["verdict"] == "ko"      # 3/24 communes
    assert par_id["u_communes"]["details"]["presentes"] == 3
    assert par_id["u_non_vide"]["verdict"] == "ok"       # 4 lignes
    assert par_id["u_doublon_cle"]["verdict"] == "ko"    # idu 'A' en double
    assert par_id["u_dates_plausibles"]["verdict"] == "ko"  # 2099
    assert par_id["u_geom_emprise"]["verdict"] == "ko"   # Paris hors Réunion
    # aucun de ces universels n'est bloquant → pas de quarantaine, juste des avertissements
    assert v.verdict == "avertissements"
    assert v.bloquants_ko == 0


def test_couloir_lignes_pose_la_reference_puis_avertit(db_session, table_temoin):
    f = _filtre_temoin()
    v1 = cadre.jouer(db_session, f, version="v1")  # 4 lignes → référence posée, ok
    db_session.commit()
    r1 = {r["controle"]: r for r in v1.resultats}["u_couloir_lignes"]
    assert r1["verdict"] == "ok" and r1["details"]["reference"] is None
    # on vide la table → 0 ligne à v2 : hors couloir ±30 % ET non-vide bloquant KO
    db_session.execute(text("DELETE FROM _c3_temoin"))
    db_session.commit()
    v2 = cadre.jouer(db_session, f, version="v2")
    db_session.commit()
    r2 = {r["controle"]: r for r in v2.resultats}
    assert r2["u_couloir_lignes"]["verdict"] == "ko"     # 0 vs référence 4
    assert r2["u_non_vide"]["verdict"] == "ko"
    assert v2.verdict == "quarantaine"                   # non_vide est bloquant
    assert v2.bloquants_ko == 1


def test_bloquant_met_en_quarantaine_et_servir_quand_meme(db_session, table_temoin):
    """Un contrôle propre BLOQUANT KO → quarantaine ; « servir quand même » lève le blocage."""
    def toujours_ko(db, filtre, version):
        return cadre.ko("mauvais", {"raison": "test"})
    f = _filtre_temoin(propres=[Controle("p_test", "plage", "bloquant", "test", "jamais", toujours_ko)])
    v = cadre.jouer(db_session, f, version="q1")
    db_session.commit()
    assert v.verdict == "quarantaine" and v.bloquants_ko == 1
    assert cadre.en_quarantaine(db_session, "_c3_temoin", "q1") is True
    # Vic sert quand même : on marque la version, en_quarantaine redevient False
    db_session.execute(text(
        "UPDATE filtre_versions SET servir_quand_meme = true, servi_par = 'vic', "
        "servi_motif = 'source saine' WHERE source='_c3_temoin' AND version='q1'"))
    db_session.commit()
    assert cadre.en_quarantaine(db_session, "_c3_temoin", "q1") is False


# ─────────────────────────── garde de la pompe (1.4) ───────────────────────────

def test_garde_pompe_bloque_source_run_en_quarantaine(db_session, monkeypatch):
    """La garde nomme la source `run` en quarantaine ; sans quarantaine, la garde est vide."""
    filtres._registre.cache_clear()
    reg = filtres._registre()
    f = Filtre(source="_c3_run", libelle="run-témoin", source_motif=None, portee_run=True)
    reg["_c3_run"] = f
    monkeypatch.setattr(filtres, "sources_run", lambda: ["_c3_run"])
    try:
        version = cadre.version_servie(db_session, f)  # 'courante' (pas de motif)
        # pas encore de verdict → garde vide
        assert filtres.garde_pompe(db_session) == []
        # on pose une quarantaine avec un bloquant KO enregistré
        db_session.execute(text(
            "INSERT INTO filtre_resultats (source,version,controle,nature,severite,valeur,seuil,verdict) "
            "VALUES ('_c3_run',:v,'p_bloque','completude','bloquant','0','>0','ko')"), {"v": version})
        db_session.execute(text(
            "INSERT INTO filtre_versions (source,version,verdict,bloquants_ko,avertissants_ko) "
            "VALUES ('_c3_run',:v,'quarantaine',1,0)"), {"v": version})
        db_session.commit()
        blocages = filtres.garde_pompe(db_session)
        assert len(blocages) == 1
        assert blocages[0]["source"] == "_c3_run"
        assert "p_bloque" in blocages[0]["controles"]
        # servir quand même → garde vide
        db_session.execute(text(
            "UPDATE filtre_versions SET servir_quand_meme = true WHERE source='_c3_run'"))
        db_session.commit()
        assert filtres.garde_pompe(db_session) == []
    finally:
        db_session.execute(text("DELETE FROM filtre_versions WHERE source='_c3_run'"))
        db_session.execute(text("DELETE FROM filtre_resultats WHERE source='_c3_run'"))
        db_session.commit()
        filtres._registre.cache_clear()


def test_jouer_ecrit_les_deux_tables(db_session, table_temoin):
    cadre.jouer(db_session, _filtre_temoin(), version="w1")
    db_session.commit()
    n_res = db_session.execute(text(
        "SELECT count(*) FROM filtre_resultats WHERE source='_c3_temoin' AND version='w1'")).scalar()
    n_ver = db_session.execute(text(
        "SELECT count(*) FROM filtre_versions WHERE source='_c3_temoin' AND version='w1'")).scalar()
    assert n_res >= 5 and n_ver == 1
