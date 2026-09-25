"""FIX-CARTE — verrous du moteur de tuiles : bornes de zoom alignées sur la source (C2) et
fraîcheur exposée au runtime par /map/tiles/meta (T1).

Tests de CONTRAT (pas de données semées nécessaires) : la borne de zoom est vérifiée AVANT toute
requête SQL, et /map/tiles/meta répond même sans mvt_meta (valeurs nulles / perime=False).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


def test_zoom_borne_a_15_comme_la_source(client):
    """C2 — l'endpoint parcelles ne sert que z9-15 (la source front cape à z15) : z16/z22 → 204."""
    assert client.get("/map/tiles/16/1/1.pbf").status_code == 204
    assert client.get("/map/tiles/22/1/1.pbf").status_code == 204
    assert client.get("/map/tiles/8/1/1.pbf").status_code == 204   # sous la source (minzoom 9)



def test_meta_expose_la_fraicheur(client):
    """T1 — /map/tiles/meta annonce la date de ce que la carte peint + le drapeau de péremption,
    lisible au RUNTIME (et non plus seulement au build)."""
    r = client.get("/map/tiles/meta")
    assert r.status_code == 200
    body = r.json()
    for k in ("run_label", "zonage_parcelle", "carte_le", "amont_le", "perime"):
        assert k in body, f"clé de fraîcheur manquante : {k}"
    assert isinstance(body["perime"], bool)


def _req(if_none_match: str | None = None):
    """Requête starlette minimale pour tester le contrat ETag sans DB ni serveur."""
    from starlette.requests import Request

    headers = []
    if if_none_match is not None:
        headers.append((b"if-none-match", if_none_match.encode()))
    return Request({"type": "http", "method": "GET", "headers": headers})


def test_etag_revalidation_conditionnelle():
    """CARTE-VITESSE-2 lot C (R3) — la réponse tuile porte un ETag FORT (hash du contenu) + le
    Cache-Control ; un If-None-Match correspondant → 304 sans corps (0 octet réseau) ; sinon 200."""
    from labuse.api.tiles import _etag, _tile_response

    body = b"\x1a\x2b\x3c parcelle mvt octets"
    etag = _etag(body)

    # 1) Sans If-None-Match → 200, ETag entre guillemets, Cache-Control conservé.
    r = _tile_response(_req(), body, etag)
    assert r.status_code == 200
    assert r.headers["etag"] == f'"{etag}"'
    assert "max-age=3600" in r.headers["cache-control"]

    # 2) If-None-Match = le bon tag → 304, même ETag, pas de corps.
    r304 = _tile_response(_req(f'"{etag}"'), body, etag)
    assert r304.status_code == 304
    assert r304.headers["etag"] == f'"{etag}"'
    assert r304.body == b""

    # 3) Tag FAIBLE (W/"…") et LISTE de tags → toujours 304 (on matche la valeur).
    assert _tile_response(_req(f'W/"{etag}", "autre"'), body, etag).status_code == 304
    # 4) Joker "*" → 304.
    assert _tile_response(_req("*"), body, etag).status_code == 304
    # 5) Tag qui ne correspond pas → 200 (le contenu a changé, on renvoie la tuile).
    assert _tile_response(_req('"perime00000000000000000000000000"'), body, etag).status_code == 200
