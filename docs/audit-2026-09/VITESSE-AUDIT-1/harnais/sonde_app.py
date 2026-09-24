"""VITESSE-AUDIT-1 — sonde de timing JETABLE (hors src/, jamais mergée).

Enveloppe ASGI autour de labuse.api.app:app qui mesure, par requête HTTP :
  - le temps mur total (ms)
  - le temps SQL cumulé (ms) + le nombre de requêtes SQL (détection N+1)
  - le temps Python résiduel = total - SQL

Écrit deux CSV dans $SONDE_DIR :
  - sonde_requests.csv : une ligne par requête HTTP
  - sonde_sql.csv      : une ligne par exécution SQL (statement normalisé + ms)

Lancement (worktree d'audit, venv activé) :
  SONDE_DIR=docs/audit-2026-09/VITESSE-AUDIT-1/MESURES/run1 \
  uvicorn sonde_app:sonde --app-dir docs/audit-2026-09/VITESSE-AUDIT-1/harnais \
    --host 127.0.0.1 --port 8305 --workers 1

Ne modifie AUCUN fichier de src/. Se branche sur l'Engine réel via les events
SQLAlchemy before/after_cursor_execute. À supprimer après l'audit (aucun merge).
"""
from __future__ import annotations

import contextvars
import csv
import os
import threading
import time
from pathlib import Path

from sqlalchemy import event

from labuse.api.app import app as _labuse_app
from labuse.db import engine as _engine

_DIR = Path(os.environ.get("SONDE_DIR", "sonde_out"))
_DIR.mkdir(parents=True, exist_ok=True)
_REQ = _DIR / "sonde_requests.csv"
_SQL = _DIR / "sonde_sql.csv"

_lock = threading.Lock()
# accumulateur par requête (dict mutable), propagé au threadpool via copie de contexte
_current: contextvars.ContextVar[dict | None] = contextvars.ContextVar("sonde_current", default=None)

# En-têtes CSV (écrits une fois si le fichier est neuf)
for _p, _hdr in ((_REQ, ["ts", "method", "path", "query", "status", "total_ms", "sql_ms", "py_ms", "sql_n", "resp_bytes"]),
                 (_SQL, ["ts", "path", "sql_ms", "rows", "stmt"])):
    if not _p.exists():
        with _p.open("w", newline="") as f:
            csv.writer(f).writerow(_hdr)


def _norm(stmt: str) -> str:
    return " ".join(stmt.split())


@event.listens_for(_engine(), "connect")
def _set_session_guards(dbapi_conn, _rec):  # noqa: ANN001
    """Sur CHAQUE connexion de l'instance d'audit uniquement (jamais commité) :
    - lock_timeout court : le heal DDL du démarrage (ALTER/CREATE INDEX en IF NOT EXISTS, no-op sur
      un schéma déjà à jour) échoue vite au lieu de faire la file d'attente ACCESS EXCLUSIVE derrière
      un run résiduel — l'instance ne bloque JAMAIS la base partagée en tête de file.
    - statement_timeout de sécurité (mandat §0) : plafonne une requête pathologique.
    Les LECTURES de service prennent un AccessShareLock, compatible avec le run résiduel (lecture ≠
    blocage lecture) → elles ne rencontrent jamais ce lock_timeout. Aucun effet sur le résultat servi."""
    cur = dbapi_conn.cursor()
    cur.execute("SET lock_timeout = '5s'")
    cur.execute("SET statement_timeout = '120s'")
    cur.close()


@event.listens_for(_engine(), "before_cursor_execute")
def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
    context._sonde_t0 = time.perf_counter()


@event.listens_for(_engine(), "after_cursor_execute")
def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
    t0 = getattr(context, "_sonde_t0", None)
    if t0 is None:
        return
    dt = (time.perf_counter() - t0) * 1000.0
    acc = _current.get()
    if acc is None:
        return
    acc["sql_ms"] += dt
    acc["sql_n"] += 1
    try:
        rows = cursor.rowcount
    except Exception:
        rows = -1
    acc["stmts"].append((dt, rows, _norm(statement)[:2000]))


class Sonde:
    """Middleware ASGI pur : ouvre un accumulateur par requête, l'expose via contextvar
    (copié dans le threadpool Starlette où tournent les handlers sync + SQLAlchemy)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        acc = {"sql_ms": 0.0, "sql_n": 0, "stmts": [], "bytes": 0}
        token = _current.set(acc)
        t0 = time.perf_counter()
        status = {"code": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            elif message["type"] == "http.response.body":
                acc["bytes"] += len(message.get("body", b"") or b"")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            total = (time.perf_counter() - t0) * 1000.0
            _current.reset(token)
            path = scope.get("path", "")
            query = scope.get("query_string", b"").decode("latin-1")
            method = scope.get("method", "")
            ts = time.time()
            sql_ms = acc["sql_ms"]
            with _lock:
                with _REQ.open("a", newline="") as f:
                    csv.writer(f).writerow([f"{ts:.3f}", method, path, query, status["code"],
                                            f"{total:.1f}", f"{sql_ms:.1f}", f"{total - sql_ms:.1f}",
                                            acc["sql_n"], acc["bytes"]])
                if acc["stmts"]:
                    with _SQL.open("a", newline="") as f:
                        w = csv.writer(f)
                        for dt, rows, stmt in acc["stmts"]:
                            w.writerow([f"{ts:.3f}", path, f"{dt:.1f}", rows, stmt])


sonde = Sonde(_labuse_app)
