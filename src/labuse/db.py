"""Connexion PostGIS — socle non négociable (PostgreSQL 15+/PostGIS 3+).

Toutes les intersections (parcelle × zonage, × risque, × Parc, × SAR…) sont des
opérations PostGIS. Voir models.py pour les colonnes géométriques (4326) et les
index GIST.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def make_engine(url: str | None = None, echo: bool = False) -> Engine:
    settings = get_settings()
    # idle_in_transaction_session_timeout (10 min) : un client tué en plein batch laissait sa transaction
    # serveur ouverte, verrous tenus des heures (incident O12, 21/07/2026 — CREATE TABLE bloqué 2h47).
    # Une transaction IDLE aussi longtemps est toujours un bug ; les requêtes ACTIVES ne sont pas concernées.
    return create_engine(url or settings.database_url, echo=echo, future=True, pool_pre_ping=True,
                         connect_args={"options": "-c idle_in_transaction_session_timeout=600000"})


_engine: Engine | None = None
_Session: sessionmaker | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def session_factory() -> sessionmaker:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=engine(), expire_on_commit=False, future=True)
    return _Session


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session transactionnelle : commit si OK, rollback sinon."""
    session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_postgis(eng: Engine | None = None) -> None:
    """CREATE EXTENSION postgis si absent (idempotent)."""
    eng = eng or engine()
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
