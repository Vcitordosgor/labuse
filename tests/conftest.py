"""Fixtures de test. Les tests marqués `db` nécessitent une base PostGIS.

Si la base est injoignable, ces tests sont SKIPPÉS (pas en échec) — utile en CI
sandbox. Lancer une PostGIS locale puis :
    export LABUSE_DATABASE_URL=postgresql+psycopg://labuse:labuse@localhost:5432/labuse
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import sessionmaker

# Le répertoire config par défaut du dépôt (les tests lisent les YAML réels).
os.environ.setdefault("LABUSE_CONFIG_DIR", "config")


@pytest.fixture(scope="session")
def engine():
    from labuse.db import ensure_postgis, make_engine
    from labuse import models

    eng = make_engine()
    try:
        with eng.connect():
            pass
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        pytest.skip(f"PostGIS injoignable, tests db skippés : {exc}")
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
