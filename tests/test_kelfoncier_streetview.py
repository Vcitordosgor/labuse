"""KELFONCIER-FIX-1 (Lot G) — Street View de la fiche §1.

Trois verrous, tous SANS clé réelle (jamais de secret en test) :
  1. clé ABSENTE → `_street_view_block` renvoie None → le front masque le bouton (aucune erreur) ;
  2. clé PRÉSENTE → URL d'embed Google (mode panorama) centrée sur le CENTROÏDE de la parcelle ;
  3. le CSP de l'app autorise `frame-src https://www.google.com` (sans quoi l'iframe serait bloqué).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_street_view_bloc_absent_sans_cle(monkeypatch):
    from labuse.api.app import _street_view_block
    monkeypatch.delenv("GOOGLE_MAPS_EMBED_KEY", raising=False)
    assert _street_view_block(-20.9738, 55.2975) is None
    # coords manquantes → None aussi (jamais une URL sans point)
    monkeypatch.setenv("GOOGLE_MAPS_EMBED_KEY", "K")
    assert _street_view_block(None, 55.2975) is None
    assert _street_view_block(-20.9738, None) is None


def test_street_view_url_centree_sur_le_centroide(monkeypatch):
    from labuse.api.app import _street_view_block
    monkeypatch.setenv("GOOGLE_MAPS_EMBED_KEY", "DEMO_KEY_XYZ")
    b = _street_view_block(-20.973806, 55.297496)
    assert b is not None
    url = b["embed_url"]
    assert url.startswith("https://www.google.com/maps/embed/v1/streetview?")
    assert "key=DEMO_KEY_XYZ" in url
    # le point EST le centroïde servi (6 décimales), jamais une adresse recalculée
    assert "location=-20.973806%2C55.297496" in url


def test_csp_autorise_frame_google():
    from labuse.api.app import app
    c = TestClient(app)
    r = c.get("/healthz")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "frame-src https://www.google.com" in csp
    # la garde anti-embed du site reste posée (on n'ouvre QUE l'enfant Google)
    assert "frame-ancestors 'none'" in csp
