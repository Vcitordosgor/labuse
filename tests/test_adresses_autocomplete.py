"""M13-B1 — autocomplétion d'adresse INTERNE (/adresses/autocomplete).

Adossée à la table `adresses` (BAN rattachée aux parcelles). On vérifie : match
insensible à la casse ET aux accents (le serveur n'a pas l'extension unaccent), priorité
au préfixe, et que chaque suggestion porte son idu + ses coordonnées (landing direct).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as _t

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def client(engine):
    import os

    from labuse import config
    from labuse.api.app import app

    os.environ.pop("LABUSE_AUTH_PASSWORD", None)
    os.environ["LABUSE_ENV"] = "local"
    config.get_settings.cache_clear()
    return TestClient(app)


@pytest.fixture
def adresses(engine):
    """Sème quelques adresses de test (idu + geom) puis nettoie."""
    from labuse.db import session_scope

    rows = [
        ("BAN_T1", "12", "Rue du General Bigeard", "97430", "Le Tampon", "97422000BY0162", 55.5178, -21.2787),
        ("BAN_T2", "3", "Allée des Ficus", "97410", "Saint-Pierre", "97416000HP0172", 55.4700, -21.3100),
        ("BAN_T3", "7", "Rue Leperlier", "97414", "Entre-Deux", "97403000AM0687", 55.4824, -21.2402),
    ]
    with session_scope() as s:
        for idb, num, voie, cp, com, idu, lon, lat in rows:
            s.execute(_t(
                "INSERT INTO adresses (id_ban, numero, voie, code_postal, commune, idu, geom) "
                "VALUES (:i, :n, :v, :cp, :c, :idu, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) "
                "ON CONFLICT (id_ban) DO NOTHING"),
                {"i": idb, "n": num, "v": voie, "cp": cp, "c": com, "idu": idu, "lon": lon, "lat": lat})
        s.commit()
    yield
    with session_scope() as s:
        s.execute(_t("DELETE FROM adresses WHERE id_ban IN ('BAN_T1','BAN_T2','BAN_T3')"))
        s.commit()


def test_autocomplete_match_casse(client, adresses):
    r = client.get("/adresses/autocomplete", params={"q": "general bigeard"})
    assert r.status_code == 200
    feats = r.json()["features"]
    assert feats, "au moins une suggestion attendue"
    top = feats[0]
    assert "General Bigeard" in top["label"]
    assert top["idu"] == "97422000BY0162"        # landing direct : l'idu accompagne la suggestion
    assert abs(top["lon"] - 55.5178) < 1e-3 and abs(top["lat"] + 21.2787) < 1e-3


def test_autocomplete_accents_insensibles(client, adresses):
    """« allee » (sans accent) doit retrouver « Allée des Ficus » (le serveur n'a pas unaccent)."""
    r = client.get("/adresses/autocomplete", params={"q": "allee des ficus"})
    feats = r.json()["features"]
    assert any(f["idu"] == "97416000HP0172" for f in feats)


def test_autocomplete_min_length(client):
    """< 3 caractères → aucune suggestion (validation FastAPI 422 côté query min_length)."""
    r = client.get("/adresses/autocomplete", params={"q": "ru"})
    assert r.status_code == 422


def test_autocomplete_label_contient_commune(client, adresses):
    r = client.get("/adresses/autocomplete", params={"q": "leperlier"})
    feats = r.json()["features"]
    assert feats
    assert "Entre-Deux" in feats[0]["label"]
