"""CIRCUIT-3 lot 4 — LA QUARANTAINE POUR LES DONNÉES SERVIES EN DIRECT.

L'ingestion écrit `<table>__attente` ; le filtre s'y joue ; l'échange n'a lieu que sur verdict OK
(ou « servir quand même »). Une injection en quarantaine NE SE SERT PAS. Retour = version précédente.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import filtres
from labuse.filtres import quarantaine
from labuse.filtres.cadre import Filtre

pytestmark = pytest.mark.db


@pytest.fixture
def source_live(db_session, monkeypatch):
    """Une source live témoin `_c3_swap` : table servie + table d'attente, enregistrée au registre."""
    for t in ("_c3_swap", "_c3_swap__attente", "_c3_swap__precedente"):
        db_session.execute(text(f"DROP TABLE IF EXISTS {t}"))
    db_session.execute(text("CREATE TABLE _c3_swap (idu varchar, v int)"))
    db_session.execute(text("INSERT INTO _c3_swap VALUES ('A', 1), ('B', 2)"))  # ANCIENNE, servie
    db_session.commit()
    filtres._registre.cache_clear()
    reg = filtres._registre()
    reg["_c3_swap"] = Filtre(source="_c3_swap", libelle="swap", table="_c3_swap",
                             cle=("idu",), live=True)
    monkeypatch.setattr(filtres, "sources_live", lambda: ["_c3_swap"])
    yield db_session
    for t in ("_c3_swap", "_c3_swap__attente", "_c3_swap__precedente"):
        db_session.execute(text(f"DROP TABLE IF EXISTS {t}"))
    db_session.commit()
    filtres._registre.cache_clear()


def _attente(db, rows_sql: str):
    db.execute(text("DROP TABLE IF EXISTS _c3_swap__attente"))
    db.execute(text("CREATE TABLE _c3_swap__attente (idu varchar, v int)"))
    if rows_sql:
        db.execute(text(f"INSERT INTO _c3_swap__attente VALUES {rows_sql}"))
    db.commit()


def test_echange_sur_verdict_ok(source_live):
    db = source_live
    _attente(db, "('C', 3), ('D', 4), ('E', 5)")   # NOUVELLE version, non vide → OK
    r = quarantaine.echanger(db, "_c3_swap")
    db.commit()
    assert r["ok"] is True
    # la table servie porte MAINTENANT la nouvelle version, la précédente l'ancienne
    servie = {x for x, in db.execute(text("SELECT idu FROM _c3_swap"))}
    prec = {x for x, in db.execute(text("SELECT idu FROM _c3_swap__precedente"))}
    assert servie == {"C", "D", "E"} and prec == {"A", "B"}


def test_injection_en_quarantaine_ne_se_sert_pas(source_live):
    db = source_live
    _attente(db, "")   # NOUVELLE version VIDE → u_non_vide bloquant KO → quarantaine
    r = quarantaine.echanger(db, "_c3_swap")
    db.commit()
    assert r["ok"] is False and r["motif"] == "quarantaine"
    # la table servie reste l'ANCIENNE (l'attente ne s'est pas servie)
    servie = {x for x, in db.execute(text("SELECT idu FROM _c3_swap"))}
    assert servie == {"A", "B"}
    assert filtres.cadre._table_existe(db, "_c3_swap__attente")  # l'attente reste, mesurée


def test_servir_quand_meme_force_l_echange(source_live):
    db = source_live
    _attente(db, "")   # vide → quarantaine, mais Vic force
    r = quarantaine.echanger(db, "_c3_swap", force=True, motif="source réputée saine")
    db.commit()
    assert r["ok"] is True and r["force"] is True
    n = db.execute(text("SELECT count(*) FROM _c3_swap")).scalar()
    assert n == 0  # la version forcée (vide) est servie


def test_retour_version_precedente(source_live):
    db = source_live
    _attente(db, "('C', 3)")
    quarantaine.echanger(db, "_c3_swap")
    db.commit()
    assert {x for x, in db.execute(text("SELECT idu FROM _c3_swap"))} == {"C"}
    # retour arrière → l'ancienne revient
    r = quarantaine.revenir(db, "_c3_swap")
    db.commit()
    assert r["ok"] is True
    assert {x for x, in db.execute(text("SELECT idu FROM _c3_swap"))} == {"A", "B"}


def test_sources_live_derivees_du_registre():
    """Les sources live viennent du registre (donnée à portée `live`) — DVF, BAN, cadastre en sont."""
    live = set(filtres.sources_live())
    for attendu in ("dvf", "ban", "cadastre_etalab", "sitadel", "sirene_etablissements"):
        assert attendu in live
