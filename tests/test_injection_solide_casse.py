"""INJECTION-SOLIDE-1 — les ESSAIS DE CASSE de la primitive d'injection sûre.

Sur une table JETABLE (`zzz_injsure_test`, créée/détruite par la fixture — jamais une table servie),
on provoque chaque panne du mandat et on PROUVE le comportement attendu : refus ou retour arrière
automatique, données servies INTACTES, jamais une table à moitié remplie.

Marqué `local` : exige une base PostGIS (la base applicative locale). Rejoué au banc de nuit.
"""
from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import text

from labuse import db as db_mod
from labuse.ingestion import injection_sure as ijs

pytestmark = pytest.mark.local

TABLE = "zzz_injsure_test"

# points WGS84 → la fixture les projette en 2975 : La Réunion (valide) et Paris (hors territoire).
_REUNION = (55.50, -21.10)
_PARIS = (2.35, 48.85)


def _pt_2975(lon, lat):
    return (f"ST_Transform(ST_SetSRID(ST_MakePoint({lon},{lat}),4326),2975)")


def _poly_valide_2975(lon, lat):
    return (f"ST_Transform(ST_Buffer(ST_SetSRID(ST_MakePoint({lon},{lat}),4326),0.002),2975)")


def _poly_bowtie_2975():
    """Un « nœud papillon » auto-intersectant → ST_IsValid faux, en 2975."""
    return ("ST_Transform(ST_SetSRID(ST_GeomFromText("
            "'POLYGON((55.5 -21.1, 55.6 -21.2, 55.5 -21.2, 55.6 -21.1, 55.5 -21.1))'),4326),2975)")


@pytest.fixture()
def engine():
    try:
        eng = db_mod.engine()
        with eng.connect() as c:
            if not c.execute(text("SELECT 1 FROM pg_extension WHERE extname='postgis'")).scalar():
                pytest.skip("PostGIS absent")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"base indisponible ({exc})")
    return eng


@pytest.fixture(autouse=True)
def table_jetable(engine):
    """Table servie JETABLE avec `n_served` lignes valides (La Réunion). Détruite en fin de test."""
    with engine.begin() as c:
        c.execute(text(f'DROP TABLE IF EXISTS "{TABLE}"'))
        c.execute(text(f'DROP TABLE IF EXISTS "{ijs._staging_nom(TABLE)}"'))
        c.execute(text(f'CREATE TABLE "{TABLE}" (id serial PRIMARY KEY, cle text, '
                       f'commune varchar(64), geom_2975 geometry(Geometry,2975))'))
    yield
    with engine.begin() as c:
        c.execute(text("SET lock_timeout = '10s'"))  # jamais un teardown qui pend sur un verrou
        c.execute(text(f'DROP TABLE IF EXISTS "{TABLE}"'))
        c.execute(text(f'DROP TABLE IF EXISTS "{ijs._staging_nom(TABLE)}"'))


def _seed(engine, n: int):
    """Pose `n` lignes servies valides (La Réunion)."""
    lon, lat = _REUNION
    with engine.begin() as c:
        for i in range(n):
            c.execute(text(f'INSERT INTO "{TABLE}" (cle, commune, geom_2975) '
                           f"VALUES (:k, 'Saint-Paul', {_poly_valide_2975(lon + i*0.001, lat)})"),
                      {"k": f"served-{i}"})


def _count(engine) -> int:
    with engine.connect() as c:
        return int(c.execute(text(f'SELECT count(*) FROM "{TABLE}"')).scalar() or 0)


def _rows(engine):
    with engine.connect() as c:
        return [r[0] for r in c.execute(text(f'SELECT cle FROM "{TABLE}" ORDER BY cle')).all()]


def _charger(lignes):
    """Fabrique un `charger_staging` qui insère `lignes` = [(cle, commune, geom_sql_2975), …]."""
    def _f(conn, staging):
        for cle, commune, geom_sql in lignes:
            conn.execute(text(f'INSERT INTO "{staging}" (cle, commune, geom_2975) '
                              f"VALUES (:k, :c, {geom_sql})"), {"k": cle, "c": commune})
    return _f


# ─────────────────────────────── 0. nominal : ça passe ───────────────────────────────

def test_nominal_injection_sert_la_nouvelle_version(engine):
    _seed(engine, 3)
    lon, lat = _REUNION
    res = ijs.injecter_table_sure(
        engine, table=TABLE, couverture_974_min=1, delta_max_pct=100.0,
        charger_staging=_charger([(f"neuf-{i}", "Saint-Paul", _poly_valide_2975(lon, lat))
                                  for i in range(3)]))
    assert res["injecte"] is True, res["resume"]
    assert sorted(_rows(engine)) == ["neuf-0", "neuf-1", "neuf-2"]


# ─────────────────────────────── 1. fichier vide ───────────────────────────────

def test_fichier_vide_refuse_et_table_intacte(engine):
    _seed(engine, 5)
    res = ijs.injecter_table_sure(engine, table=TABLE, charger_staging=_charger([]))
    assert res["injecte"] is False
    assert "injection vide" in res["verdict"].echecs[0]
    assert _count(engine) == 5  # servie INTACTE


# ─────────────────────── 2. fichier à moitié téléchargé (écart) ───────────────────────

def test_demi_fichier_ecart_suspect_refuse(engine):
    _seed(engine, 10)
    lon, lat = _REUNION
    res = ijs.injecter_table_sure(
        engine, table=TABLE, delta_max_pct=35.0, couverture_974_min=1,
        charger_staging=_charger([("x", "Saint-Paul", _poly_valide_2975(lon, lat))]))  # 10 → 1 = -90 %
    assert res["injecte"] is False
    assert any("écart avec la version précédente" in e for e in res["verdict"].echecs)
    assert _count(engine) == 10


# ─────────────────────────── 3. colonnes renommées par le producteur ───────────────────────────

def test_colonnes_renommees_rollback(engine):
    _seed(engine, 4)
    def charger(conn, staging):
        # le producteur a renommé `cle` en `code` : l'INSERT vise une colonne absente → erreur.
        conn.execute(text(f'INSERT INTO "{staging}" (code) VALUES (:v)'), {"v": "x"})
    res = ijs.injecter_table_sure(engine, table=TABLE, charger_staging=charger)
    assert res["injecte"] is False
    assert "erreur" in res
    assert _count(engine) == 4


# ─────────────────────────────── 4. doublons ───────────────────────────────

def test_doublons_refuses(engine):
    _seed(engine, 3)
    lon, lat = _REUNION
    res = ijs.injecter_table_sure(
        engine, table=TABLE, couverture_974_min=1, delta_max_pct=100.0, dedup_cols=["cle"],
        charger_staging=_charger([("dup", "Saint-Paul", _poly_valide_2975(lon, lat)),
                                  ("dup", "Saint-Paul", _poly_valide_2975(lon, lat))]))
    assert res["injecte"] is False
    assert any("doublon" in e for e in res["verdict"].echecs)
    assert _count(engine) == 3


# ─────────────────────────────── 5. géométries invalides ───────────────────────────────

def test_geometries_invalides_refusees(engine):
    _seed(engine, 3)
    res = ijs.injecter_table_sure(
        engine, table=TABLE, couverture_974_min=1, delta_max_pct=100.0,
        charger_staging=_charger([("bowtie", "Saint-Paul", _poly_bowtie_2975())]))
    assert res["injecte"] is False
    assert any("géométrie(s) invalide" in e for e in res["verdict"].echecs)
    assert _count(engine) == 3


# ─────────────────────────────── 6. données hors de La Réunion ───────────────────────────────

def test_hors_reunion_refuse(engine):
    _seed(engine, 3)
    lon, lat = _PARIS
    res = ijs.injecter_table_sure(
        engine, table=TABLE, couverture_974_min=0, delta_max_pct=100.0,
        charger_staging=_charger([("paris", "Paris", _poly_valide_2975(lon, lat))]))
    assert res["injecte"] is False
    assert any("hors de La Réunion" in e for e in res["verdict"].echecs)
    assert _count(engine) == 3


# ─────────────── 7. coupure réseau / disque plein en cours (exception) → rollback ───────────────

def test_coupure_en_cours_rollback(engine):
    _seed(engine, 6)
    def charger(conn, staging):
        lon, lat = _REUNION
        conn.execute(text(f'INSERT INTO "{staging}" (cle, commune, geom_2975) '
                          f"VALUES ('a','Saint-Paul',{_poly_valide_2975(lon, lat)})"))
        raise ConnectionError("réseau coupé en plein téléchargement")  # ou disque plein
    res = ijs.injecter_table_sure(engine, table=TABLE, charger_staging=charger)
    assert res["injecte"] is False
    assert "ConnectionError" in res["erreur"]
    assert _count(engine) == 6  # rien de la staging n'a fui dans la servie


# ─────────────────────────── 8. deux injections en même temps ───────────────────────────

def test_deux_injections_concurrentes_la_seconde_refuse(engine):
    _seed(engine, 3)
    lon, lat = _REUNION
    # on TIENT le verrou consultatif de la table dans une transaction tierce, puis on injecte.
    tiers = engine.connect()
    ttx = tiers.begin()
    try:
        tiers.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ijs._cle_verrou(TABLE)})
        res = ijs.injecter_table_sure(
            engine, table=TABLE, couverture_974_min=1, delta_max_pct=100.0,
            charger_staging=_charger([("neuf", "Saint-Paul", _poly_valide_2975(lon, lat))]))
        assert res["injecte"] is False
        assert "déjà en cours" in res["verdict"].echecs[0]
        assert _count(engine) == 3
    finally:
        ttx.rollback()
        tiers.close()


# ─────── 9. lecture client pendant le remplacement : jamais une table à moitié remplie ───────

def test_lecture_pendant_remplacement_voit_une_version_coherente(engine):
    """Un lecteur ouvert en REPEATABLE READ avant le COMMIT voit l'ANCIENNE version entière ; un
    lecteur ouvert après voit la NOUVELLE entière. Jamais un décompte intermédiaire (moitié)."""
    _seed(engine, 4)
    lon, lat = _REUNION
    lecteur = engine.connect().execution_options(isolation_level="REPEATABLE READ")
    try:
        avant = int(lecteur.execute(text(f'SELECT count(*) FROM "{TABLE}"')).scalar())  # fige l'instantané
        assert avant == 4
        res = ijs.injecter_table_sure(
            engine, table=TABLE, couverture_974_min=1, delta_max_pct=1000.0,
            charger_staging=_charger([(f"neuf-{i}", "Saint-Paul", _poly_valide_2975(lon, lat))
                                      for i in range(9)]))
        assert res["injecte"] is True, res["resume"]
        # le lecteur, dans son instantané, voit TOUJOURS 4 (jamais 0, 9 partiel, ou autre) :
        pendant = int(lecteur.execute(text(f'SELECT count(*) FROM "{TABLE}"')).scalar())
        assert pendant == 4, f"le lecteur a vu une version à moitié remplie ({pendant}) !"
    finally:
        lecteur.rollback()
        lecteur.close()
    # un nouveau lecteur voit la version entière, neuve :
    assert _count(engine) == 9


# ─────────────────────────── 10. retour arrière réel après échec ───────────────────────────

def test_rollback_restaure_exactement_les_lignes(engine):
    _seed(engine, 3)
    avant = _rows(engine)
    # injection refusée (vide) : les lignes servies doivent être EXACTEMENT les mêmes après.
    ijs.injecter_table_sure(engine, table=TABLE, charger_staging=_charger([]))
    assert _rows(engine) == avant
    # et aucune table de travail ne traîne (nettoyée par le rollback).
    with engine.connect() as c:
        reste = c.execute(text("SELECT to_regclass(:s)"),
                          {"s": ijs._staging_nom(TABLE)}).scalar()
    assert reste is None, "la staging a survécu au rollback"
