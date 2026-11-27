"""Connexion PostGIS — socle non négociable (PostgreSQL 15+/PostGIS 3+).

Toutes les intersections (parcelle × zonage, × risque, × Parc, × SAR…) sont des
opérations PostGIS. Voir models.py pour les colonnes géométriques (4326) et les
index GIST.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from psycopg import OperationalError as DriverOperationalError
from sqlalchemy.exc import DBAPIError, TimeoutError as PoolTimeout
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def connexions_saturees(exc: Exception) -> bool:
    """Pool local expiré ou refus PostgreSQL faute de connexions disponibles."""
    if isinstance(exc, PoolTimeout):
        return True
    erreur = exc.orig if isinstance(exc, DBAPIError) else exc
    if getattr(erreur, "sqlstate", None):
        return erreur.sqlstate == "53300"
    # Au démarrage de la connexion, libpq peut transmettre le FATAL sans SQLSTATE.
    if isinstance(erreur, DriverOperationalError):
        message = str(erreur).lower()
        return any(motif in message for motif in (
            "too many clients already", "too many connections for",
            "remaining connection slots are reserved",
        ))
    return False


def requete_bdd_indisponible(exc: Exception) -> bool:
    """À la frontière HTTP, un calcul SQL interrompu peut être retenté."""
    if connexions_saturees(exc):
        return True
    erreur = exc.orig if isinstance(exc, DBAPIError) else exc
    code = getattr(erreur, "sqlstate", None)
    # PostgreSQL signale une annulation en 57014. Si elle survient pendant une
    # intersection PostGIS, GEOS remonte parfois son propre diagnostic en XX000.
    return code == "57014" or (code == "XX000" and "GEOS Error: InterruptedException" in str(erreur))


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
    # VITESSE-FIX-1 lot A — pool EXPLICITE et réglable par l'env (défauts = comportement historique :
    # pool_size=5, max_overflow=10 ⇒ 15 connexions/worker, pression INCHANGÉE). `pool_recycle` ajouté
    # (robustesse connexions longues). AUCUN `statement_timeout` posé ici : le moteur est PARTAGÉ avec
    # les batchs CLI (ingestion/scoring/résiduel) qui tournent légitimement des heures — le plafond de
    # requête est appliqué par requête d'API (SET LOCAL dans get_db), jamais sur le moteur.
    # NU4-FIX-1 (E/R2) — hygiène du pool sous charge : `pool_use_lifo` réutilise la connexion la PLUS
    # récemment rendue (au lieu d'un round-robin FIFO) → sous rafale, moins de connexions distinctes
    # restent ouvertes en même temps (les surplus `overflow` se referment plus vite), ce qui soulage la
    # pression sur `max_connections`. `pool_timeout` borné et RÉGLABLE. La vraie cause d'épuisement
    # (connexions « idle in transaction » pendant l'appel modèle) est traitée à la source par R3
    # (ai.core.complete libère la connexion AVANT l'appel réseau).
    # DEPLOY-GROUPE-3 (q_v23) — un PROCESS de calcul peut faire lire à TOUTES ses connexions un run
    # résiduel CANDIDAT (par numéro) au lieu du run servi, en posant `LABUSE_RESIDUEL_RUN_SEQ`. La vue
    # `parcel_residuel` honore alors le réglage de session `labuse.residuel_run_seq` (cf.
    # residuel_runs._view_sql). Le service/les clients ne posent JAMAIS cet env → run servi, comportement
    # inchangé. `int()` valide l'entrée (jamais d'injection dans les options de connexion).
    opts = "-c idle_in_transaction_session_timeout=600000 -c timezone=Indian/Reunion"
    _rseq = os.environ.get("LABUSE_RESIDUEL_RUN_SEQ")
    if _rseq:
        opts += f" -c labuse.residuel_run_seq={int(_rseq)}"
    return create_engine(url or settings.database_url, echo=echo, future=True,
                         pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow,
                         pool_pre_ping=settings.db_pool_pre_ping, pool_recycle=settings.db_pool_recycle_s,
                         pool_timeout=settings.db_pool_timeout_s, pool_use_lifo=True,
                         connect_args={"options": opts})


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
