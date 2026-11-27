"""OUTIL-PERMIS-FIX-15 — la table dérivée `pc_caducs` ne doit JAMAIS être vidée par une reconstruction
sur source transitoirement vide (cause des deux disparitions : avant FIX-9, et entre FIX-13 et FIX-14).

Mécanisme de la panne : `rebuild_swap` publiait ce que `_populate` produisait, même 0 ligne — une
reconstruction déclenchée pendant que `sitadel_permits` était vide/verrouillé (reload concurrent d'un
autre worktree, nightly `fraicheur-derives`) écrasait les 4 440 lignes servies par du vide.

Correctif : garde-fou VIDE dans `rebuild_swap` — refuse le swap si la shadow est vide alors que la
table servie a des lignes (`RebuildWouldEmptyError`), AVANT tout DROP → la table servie reste intacte.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text

from labuse.ingestion._rebuild import RebuildWouldEmptyError, rebuild_swap

_REF = dt.date(2026, 11, 25)
_WKT = "POLYGON((55.3 -21,55.301 -21,55.301 -21.001,55.3 -21.001,55.3 -21))"


def _seed_un_caduc(s, idu="97400000FIX15A"):
    s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": idu})
    s.execute(text(
        "INSERT INTO parcels (idu,commune,section,numero,geom,geom_2975,surface_m2,centroid,bbox) "
        "VALUES (:i,'T','AA','01',ST_GeomFromText(:w,4326),ST_Transform(ST_GeomFromText(:w,4326),2975),"
        "500,ST_Centroid(ST_GeomFromText(:w,4326)),ST_Envelope(ST_GeomFromText(:w,4326)))"),
        {"i": idu, "w": _WKT})
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id='PC-FIX15A'"))
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id,type,date,idu_codes,commune,raw) "
        "VALUES ('PC-FIX15A','PC','2020-02-26',CAST(:i AS jsonb),'T','{\"etat\":\"2\"}'::jsonb)"),
        {"i": '["%s"]' % idu})


@pytest.mark.db
def test_relance_sur_source_vide_ne_vide_pas_pc_caducs(db_session):
    """Relance simulée : 1re build → 1 caduc ; source vidée (reload concurrent) → 2e build REFUSÉE
    (RebuildWouldEmptyError) et la table GARDE sa ligne. Avant FIX-15, la 2e build mettait 0."""
    from labuse.ingestion import pc_caducs
    s = db_session
    _seed_un_caduc(s)
    pc_caducs.build_pc_caducs(s, ref_date=_REF, commit=False)
    assert s.execute(text("SELECT count(*) FROM pc_caducs")).scalar() == 1

    # source transitoirement VIDE (comme un reload de sitadel par un autre worktree) → reconstruction
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id='PC-FIX15A'"))
    with pytest.raises(RebuildWouldEmptyError):
        pc_caducs.build_pc_caducs(s, ref_date=_REF, commit=False)
    # la table servie est CONSERVÉE (pas de swap) — la ligne est toujours là
    assert s.execute(text("SELECT count(*) FROM pc_caducs")).scalar() == 1


@pytest.mark.db
def test_rebuild_swap_garde_fou_generique(db_session):
    """Garde-fou générique (protège aussi defisc_fenetres / score_e) : une shadow VIDE ne remplace
    pas une table peuplée ; `allow_empty=True` lève la garde pour un effacement volontaire."""
    s = db_session
    ddl = 'CREATE TABLE IF NOT EXISTS _fix15_t (x int)'
    rebuild_swap(s, "_fix15_t", ddl, lambda sh: s.execute(
        text(f'INSERT INTO "{sh}" (x) VALUES (1),(2),(3)')), commit=False)
    assert s.execute(text("SELECT count(*) FROM _fix15_t")).scalar() == 3

    # populate VIDE → refus, table conservée
    with pytest.raises(RebuildWouldEmptyError):
        rebuild_swap(s, "_fix15_t", ddl, lambda sh: None, commit=False)
    assert s.execute(text("SELECT count(*) FROM _fix15_t")).scalar() == 3

    # allow_empty=True → effacement VOLONTAIRE autorisé
    rebuild_swap(s, "_fix15_t", ddl, lambda sh: None, commit=False, allow_empty=True)
    assert s.execute(text("SELECT count(*) FROM _fix15_t")).scalar() == 0
    s.execute(text("DROP TABLE IF EXISTS _fix15_t"))
