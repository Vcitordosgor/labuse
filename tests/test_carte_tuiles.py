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


def test_overlay_zoom_borne_a_15(client):
    """C2 — même borne haute pour les overlays MVT (ovmvt-* maxzoom 15)."""
    assert client.get("/map/tiles/ov/plu_gpu_zone/16/1/1.pbf").status_code == 204
    assert client.get("/map/tiles/ov/ppr/22/1/1.pbf").status_code == 204


def test_meta_expose_la_fraicheur(client):
    """T1 — /map/tiles/meta annonce la date de ce que la carte peint + le drapeau de péremption,
    lisible au RUNTIME (et non plus seulement au build)."""
    r = client.get("/map/tiles/meta")
    assert r.status_code == 200
    body = r.json()
    for k in ("run_label", "zonage_parcelle", "carte_le", "amont_le", "perime"):
        assert k in body, f"clé de fraîcheur manquante : {k}"
    assert isinstance(body["perime"], bool)
