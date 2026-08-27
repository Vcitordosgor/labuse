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


def sql_statements(ddl: str) -> list[str]:
    """FIX-GB-011 (extinction de la classe) — découpe un DDL multi-statements SANS jamais couper sur un
    `;` situé DANS un commentaire (`-- …`, `/* … */`), un bloc dollar-quoté (`$$ … $$`, fonctions/DO) ou
    un littéral (`'…'`, `"…"`). L'ancien `ddl.split(";")` cassait dès qu'un commentaire contenait un `;`
    (bug GB-011 sur courrier ; risque latent sur partners avec ses `$$`). Les statements retournés peuvent
    encore CONTENIR des commentaires (Postgres les ignore) ; les fragments vides sont écartés. Remplace
    tout `for s in DDL.split(";")` par `for s in sql_statements(DDL)`."""
    def _meaningful(stmt: str) -> bool:
        # écarte les fragments purement commentaire/blanc (exécuter un commentaire seul lève « empty query »)
        import re
        sans = re.sub(r"/\*.*?\*/", "", re.sub(r"--[^\n]*", "", stmt), flags=re.S)
        return bool(sans.strip())

    out: list[str] = []
    buf: list[str] = []
    i, n = 0, len(ddl)
    while i < n:
        ch, two = ddl[i], ddl[i:i + 2]
        if two == "--":                                   # commentaire de ligne → jusqu'au \n inclus
            j = ddl.find("\n", i)
            j = n if j == -1 else j + 1
            buf.append(ddl[i:j]); i = j; continue
        if two == "/*":                                   # commentaire bloc → jusqu'au */
            j = ddl.find("*/", i + 2)
            j = n if j == -1 else j + 2
            buf.append(ddl[i:j]); i = j; continue
        if ch == "$":                                     # dollar-quote $tag$ … $tag$ (fonctions/DO)
            end = ddl.find("$", i + 1)
            if end != -1:
                tag = ddl[i:end + 1]
                close = ddl.find(tag, end + 1)
                if close != -1:
                    j = close + len(tag)
                    buf.append(ddl[i:j]); i = j; continue
        if ch in ("'", '"'):                              # littéral chaîne / identifiant quoté
            q, j = ch, i + 1
            while j < n:
                if ddl[j] == q:
                    if j + 1 < n and ddl[j + 1] == q:     # guillemet doublé = échappé
                        j += 2; continue
                    j += 1; break
                j += 1
            buf.append(ddl[i:j]); i = j; continue
        if ch == ";":                                     # fin de statement AU NIVEAU TOP
            stmt = "".join(buf).strip()
            if _meaningful(stmt):
                out.append(stmt)
            buf = []; i += 1; continue
        buf.append(ch); i += 1
    tail = "".join(buf).strip()
    if _meaningful(tail):
        out.append(tail)
    return out


def make_engine(url: str | None = None, echo: bool = False) -> Engine:
    settings = get_settings()
    # idle_in_transaction_session_timeout (10 min) : un client tué en plein batch laissait sa transaction
    # serveur ouverte, verrous tenus des heures (incident O12, 21/07/2026 — CREATE TABLE bloqué 2h47).
    # Une transaction IDLE aussi longtemps est toujours un bug ; les requêtes ACTIVES ne sont pas concernées.
    # REVUE · R2 — fuseau de session forcé à Indian/Reunion : tout CURRENT_DATE/now() du SQL métier
    # est en heure Réunion, indépendamment du fuseau du serveur de prod (bug fuseau consigné). Le
    # pendant Python vit dans labuse.tz (today_reunion / now_reunion).
    return create_engine(url or settings.database_url, echo=echo, future=True, pool_pre_ping=True,
                         connect_args={"options": "-c idle_in_transaction_session_timeout=600000"
                                                  " -c timezone=Indian/Reunion"})


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
