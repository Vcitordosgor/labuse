"""M55-D stage 6 — Signaux de vie pré-calculés (parcel_signaux_vie) : build + IDEMPOTENCE.

Le builder reconstruit chaque signal par DELETE+INSERT — rejouer le build ne doit RIEN
changer (exigence du mandat : pré-calcul au build, avec test d'idempotence).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.signaux_vie import (
    ASSEMBLAGE_MIN_PARCELLES,
    SIGNAUX_PRECALCULES,
    build_signaux_vie,
)


# ───────────────────────── pur ─────────────────────────

def test_liste_fermee():
    # la liste des signaux pré-calculés est FERMÉE (le reste vit en direct dans /filtre)
    assert SIGNAUX_PRECALCULES == ("permis_actif", "friche", "assemblage_pm")
    assert ASSEMBLAGE_MIN_PARCELLES == 3   # arbitrage Vic (phase 1) : privé ≥ 3 parcelles


# ───────────────────────── DB : build + idempotence ─────────────────────────

_SQ = "POLYGON((55.27{i}0 -21.0100, 55.27{i}1 -21.0100, 55.27{i}1 -21.0099, 55.27{i}0 -21.0099, 55.27{i}0 -21.0100))"


def _parcel(db, idu, i):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i, 'Saint-Paul', ST_SetSRID(ST_GeomFromText(:w),4326), "
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) ON CONFLICT (idu) DO NOTHING"),
        {"i": idu, "w": _SQ.format(i=i)})


def _sources(db):
    """Tables sources absentes du schéma modélisé (labuse_test) — minimales, colonnes utiles."""
    db.execute(text("CREATE TABLE IF NOT EXISTS pc_caducs (idu varchar(14) PRIMARY KEY)"))
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS parcelle_personne_morale "
        "(idu varchar(14), siren varchar(9), groupe int)"))


@pytest.mark.db
def test_build_et_idempotence(db_session):
    db = db_session
    _sources(db)
    for n, idu in enumerate(["97415000ZZ0001", "97415000ZZ0002", "97415000ZZ0003", "97415000ZZ0004"]):
        _parcel(db, idu, n)
    # permis récent sur ZZ0001 (gardé) et ZZ0002 (exclu : caduc)
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes) VALUES "
        "('T1','PC', now() - interval '1 year', '[\"97415000ZZ0001\"]'), "
        "('T2','PC', now() - interval '1 year', '[\"97415000ZZ0002\"]'), "
        "('T3','PC', now() - interval '5 years', '[\"97415000ZZ0004\"]')"))   # trop vieux → hors fenêtre
    db.execute(text("INSERT INTO pc_caducs (idu) VALUES ('97415000ZZ0002') ON CONFLICT DO NOTHING"))
    # friche intersectant ZZ0003 (geom_2975 posé explicitement : pas de trigger en base de test)
    db.execute(text(
        "INSERT INTO spatial_layers (kind, name, geom, geom_2975) VALUES "
        "('friche', 'Friche T', ST_SetSRID(ST_GeomFromText(:w),4326), "
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975))"), {"w": _SQ.format(i=2)})
    # société privée (groupe 0) détenant 3 parcelles → assemblage ; ZZ0004 hors tout
    for idu in ["97415000ZZ0001", "97415000ZZ0002", "97415000ZZ0003"]:
        db.execute(text(
            "INSERT INTO parcelle_personne_morale (idu, siren, groupe) VALUES (:i, '111222333', 0)"),
            {"i": idu})
    db.flush()

    counts1 = build_signaux_vie(db)
    assert counts1["permis_actif"] >= 1   # ZZ0001 (ZZ0002 caduc exclu, ZZ0004 hors fenêtre)
    assert counts1["friche"] >= 1         # ZZ0003
    assert counts1["assemblage_pm"] >= 3  # les 3 parcelles du siren privé

    def rows():
        return sorted(db.execute(text(
            "SELECT idu, signal FROM parcel_signaux_vie WHERE idu LIKE '97415000ZZ%' ORDER BY 1,2"
        )).all())

    r1 = rows()
    assert ("97415000ZZ0001", "permis_actif") in r1
    assert ("97415000ZZ0002", "permis_actif") not in r1    # caduc → exclu
    assert ("97415000ZZ0004", "permis_actif") not in r1    # > 3 ans → hors fenêtre
    assert ("97415000ZZ0003", "friche") in r1
    assert {(f"97415000ZZ000{k}", "assemblage_pm") for k in (1, 2, 3)} <= set(r1)

    # IDEMPOTENCE : rejouer le build ne change RIEN (mêmes lignes, mêmes comptes)
    counts2 = build_signaux_vie(db)
    assert counts2 == counts1
    assert rows() == r1
