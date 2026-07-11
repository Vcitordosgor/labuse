"""Tests Lot 6 (wave-adresses) : validation registry (garde-fou), stub, quota — sans réseau."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


def test_valider_filtres_rejette_hors_registry(db_session):
    from labuse.ai.nl_segments import valider_filtres
    from labuse.segments.registry import compute_availability

    avail = compute_availability(db_session, use_cache=False)
    data = {"filtres": [
        {"cle": "jardin_m2", "min": 300},                     # valide
        {"cle": "DROP TABLE parcels", "min": 1},              # clé hors registry → rejetée
        {"cle": "type_bien", "values": ["Chateau"]},          # valeur hors énum → rejetée
        {"cle": "communes", "values": ["Paris"]},             # commune hors liste → rejetée
        {"cle": "communes", "values": ["Le Tampon", "Paris"]},  # partiellement valide → borné
    ]}
    v = valider_filtres(data, avail)
    cles = [f["cle"] for f in v["filtres"]]
    assert cles == ["jardin_m2", "communes"]
    assert v["filtres"][1]["values"] == ["Le Tampon"]
    assert len(v["rejetes"]) == 3
    assert any("hors registry" in r["raison"] for r in v["rejetes"])


def test_stub_local_deterministe():
    from labuse.ai.nl_segments import stub_nl_segments

    r = stub_nl_segments("villas mutées récemment avec grand jardin sans piscine au Tampon")
    cles = {f["cle"] for f in r["filtres"]}
    assert {"communes", "jardin_m2", "anciennete_mutation_mois",
            "type_bien", "piscine"} <= cles
    assert stub_nl_segments("écris-moi un poème")["out_of_scope"]


def test_endpoint_quota_nl(engine, monkeypatch):
    """Quota 30/jour/sujet (réduit à 1) → refus honnête, sans appel réseau (clé retirée)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LABUSE_NL_QUOTA_JOUR", "1")
    from labuse import config
    from labuse.api import ia, protection
    from labuse.api.app import app
    config.get_settings.cache_clear()
    protection.ensure_tables(engine)
    ia.ensure_tables(engine)
    protection.reset_etat_memoire()
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_compteurs WHERE kind = 'nl'"))
        c.execute(text("DELETE FROM nl_query_log"))
        c.execute(text("DELETE FROM acces_gels"))   # gel résiduel d'une suite précédente
    client = TestClient(app, base_url="https://testserver")
    try:
        r1 = client.post("/ia/segments-search", json={"text": "grand jardin au Tampon"})
        assert r1.status_code == 200 and r1.json()["stub"] is True
        assert {f["cle"] for f in r1.json()["filtres"]} == {"communes", "jardin_m2"}
        r2 = client.post("/ia/segments-search", json={"text": "encore une question"})
        assert r2.json().get("quota") is True
        # log ANONYMISÉ : la question est là, aucun identifiant utilisateur
        with engine.connect() as c:
            row = c.execute(text("SELECT question, statut FROM nl_query_log")).first()
        assert row is not None and "jardin" in row[0]
    finally:
        config.get_settings.cache_clear()
