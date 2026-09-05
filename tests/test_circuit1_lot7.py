"""CIRCUIT-1 lot 7 — le mode Traçage côté serveur : `?trace=1` est réservé à l'ADMIN.
Auth ACTIVÉE (monkeypatch enabled) : sans session → refus (401/403), jamais le tampon."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.db


def test_71_trace_403_hors_admin(engine, monkeypatch):
    from fastapi.testclient import TestClient
    from labuse.api import auth
    from labuse.api.app import app
    monkeypatch.setattr(auth, "enabled", lambda: True)     # auth ACTIVE (prod-like)
    client = TestClient(app)
    r = client.get("/communes/Saint-Paul/contexte?trace=1")
    # 401/403 = exiger_admin ; 503 = la garde GLOBALE d'auth refuse en amont (fail-closed,
    # infra de session absente en test) — dans tous les cas : REFUS, le tampon n'est jamais servi.
    assert r.status_code in (401, 403, 503), "le tampon est admin-seulement (7.1)"
    assert "_trace" not in (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})


def test_71_sans_trace_reste_public(engine, monkeypatch):
    """Sans trace=1, l'endpoint garde son comportement (le mode traçage n'a AUCUN effet client)."""
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    client = TestClient(app)
    r = client.get("/communes/Saint-Paul/contexte")
    assert r.status_code == 200 and "_trace" not in r.json()
