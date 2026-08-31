"""FICHE-COMMUNE-2 (C1) — la fiche commune est SERVIE depuis un cache précalculé (job nocturne
`fiche-commune-cache`), pour une ouverture < 500 ms (mesuré : 20–27 s → ~10 ms). Ces tests verrouillent
le contrat du cache : sur HIT on sert le payload stocké + la date de calcul, JAMAIS le recalcul ; sur
MISS on calcule en direct (honnête) avec `cache_calcule_le = null` ; le point d'écriture (`rafraichir`)
stocke bien le payload. Le calcul lourd lui-même est monkeypatché (déterministe, sans dépendre des
tables de scoring)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import app as A


@pytest.mark.db
def test_contexte_servi_depuis_cache_sans_recalcul(db_session, monkeypatch):
    A._ensure_contexte_cache(db_session)
    db_session.execute(text(
        "INSERT INTO commune_contexte_cache (commune, insee, payload, computed_at) "
        "VALUES ('Testville', '97999', CAST(:p AS jsonb), TIMESTAMPTZ '2026-08-31 10:00:00+04') "
        "ON CONFLICT (commune) DO UPDATE SET payload = EXCLUDED.payload, computed_at = EXCLUDED.computed_at"),
        {"p": '{"commune":"Testville","foncier":{"n_parcelles":42}}'})
    db_session.flush()

    def _boom(db, c):
        raise AssertionError("le calcul lourd ne doit PAS être appelé sur un hit de cache")
    monkeypatch.setattr(A, "_compute_commune_contexte", _boom)

    r = A.commune_contexte("Testville", db_session)
    assert r["foncier"]["n_parcelles"] == 42            # payload servi tel quel
    assert r["cache_calcule_le"].startswith("2026-08-31")   # date du calcul → pied de fiche


@pytest.mark.db
def test_cache_miss_calcule_en_direct(db_session, monkeypatch):
    A._ensure_contexte_cache(db_session)
    monkeypatch.setattr(A, "_compute_commune_contexte",
                        lambda db, c: {"commune": c, "foncier": None})
    r = A.commune_contexte("PasEnCache", db_session)
    assert r["commune"] == "PasEnCache"
    assert r["cache_calcule_le"] is None                # miss → calcul direct, dit tel quel (jamais un faux)


@pytest.mark.db
def test_rafraichir_ecrit_le_payload(db_session, monkeypatch):
    monkeypatch.setattr(A, "_compute_commune_contexte",
                        lambda db, c: {"commune": c, "insee": "97999", "foncier": {"n_parcelles": 7}})
    A.rafraichir_contexte_cache(db_session, "Testville")
    row = db_session.execute(text(
        "SELECT insee, payload, computed_at FROM commune_contexte_cache WHERE commune = 'Testville'")
    ).mappings().first()
    assert row is not None and row["insee"] == "97999"
    assert row["payload"]["foncier"]["n_parcelles"] == 7
    assert row["computed_at"] is not None
