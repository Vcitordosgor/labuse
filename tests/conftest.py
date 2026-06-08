"""Fixtures de test — ISOLÉES de la base applicative (M4).

Les tests tournent sur une base DÉDIÉE (`labuse_test` par défaut, ou
`LABUSE_TEST_DATABASE_URL`) : ils ne touchent JAMAIS la base de l'app. On bascule
TOUT le code (app + tests) vers cette base AVANT tout accès aux settings, de sorte
qu'aucun test ne puisse `TRUNCATE` la base applicative (cf. demo_saint_paul.reset_demo).

Si la base est injoignable, les tests `db` sont SKIPPÉS (pas en échec).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("LABUSE_CONFIG_DIR", "config")
# Fiche « promoteur » : pas d'appels externes (RGE ALTI / GPU) en test → déterministe.
os.environ.setdefault("LABUSE_ENRICH_LIVE", "0")

# Redirige l'app ET les tests vers une base de test dédiée, AVANT le 1er get_settings().
_APP_URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://labuse:labuse@localhost:5432/labuse")
_TEST_URL = os.environ.get("LABUSE_TEST_DATABASE_URL") or (_APP_URL.rsplit("/", 1)[0] + "/labuse_test")
os.environ["LABUSE_DATABASE_URL"] = _TEST_URL


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy import create_engine, text

    from labuse import config, db, models

    config.get_settings.cache_clear()        # prend en compte la base de test
    db._engine = None                        # force la reconstruction de l'engine app
    db._Session = None

    # Crée la base de test si absente (connexion à la base de maintenance 'postgres').
    try:
        admin_url = _TEST_URL.rsplit("/", 1)[0] + "/postgres"
        dbname = _TEST_URL.rsplit("/", 1)[1]
        admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            if not c.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}).scalar():
                c.execute(text(f'CREATE DATABASE "{dbname}"'))
        admin.dispose()
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        pytest.skip(f"Base de test indisponible ({_TEST_URL}) : {exc}")

    eng = db.make_engine()
    try:
        with eng.connect():
            pass
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        pytest.skip(f"PostGIS injoignable, tests db skippés : {exc}")
    db._engine = eng                         # l'app (session_scope) utilise la MÊME base de test
    db._Session = None
    from labuse.db import ensure_postgis
    ensure_postgis(eng)
    models.create_all(eng)
    return eng


@pytest.fixture
def db_session(engine):
    """Session transactionnelle rollback-ée après chaque test (pas de pollution)."""
    connection = engine.connect()
    trans = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
