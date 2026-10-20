"""CHASSE-APP-FIX-1 (pt 2) — l'écran de validation /flash (juste avant le paiement) affiche la
CONTENANCE cadastrale comme surface PRINCIPALE, pas l'aire du dessin (ST_Area). Le dessin passe
en mention secondaire « Dessin du plan » — même traitement que la fiche (CONTENANCE-1).

La chasse du 19/10 a relevé « 27 156 m² » (dessin) là où le cadastre dit « 25 633 m² »
(contenance) sur la parcelle Saint-Paul CW 658.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_POLY = ("ST_SetSRID(ST_GeomFromText('POLYGON((55.27 -21.01,55.2705 -21.01,"
         "55.2705 -21.0105,55.27 -21.0105,55.27 -21.01))'),4326)")


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with engine.begin() as c:
        # dessin (surface_m2) 27156 ≠ contenance 25633 (écart +6 % > 1 % → « Dessin du plan » montré).
        c.execute(text(
            f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, contenance_m2, geom, created_at, updated_at)
                VALUES ('97415000CW9658', 'Saint-Paul', 'CW', '9658', 27156, 25633, {_POLY}, now(), now())
                ON CONFLICT (idu) DO UPDATE SET surface_m2 = EXCLUDED.surface_m2,
                    contenance_m2 = EXCLUDED.contenance_m2, geom = EXCLUDED.geom"""))
    try:
        yield TestClient(app)
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM parcels WHERE idu = '97415000CW9658'"))


def test_flash_affiche_la_contenance_pas_le_dessin(client):
    html = client.get("/flash", params={"idu": "97415000CW9658"}).text
    # la contenance cadastrale (chiffre de l'acte) est la valeur PRINCIPALE de la légende
    assert "· 25 633 m² · Vue aérienne IGN" in html
    # le dessin (ST_Area) n'est plus la surface principale — il passe en mention secondaire
    assert "· 27 156 m² · Vue aérienne IGN" not in html
    assert "Dessin du plan : 27 156 m²" in html


def test_flash_repli_sans_contenance_dit_mesuree_sur_le_plan(client, engine):
    with engine.begin() as c:
        c.execute(text("UPDATE parcels SET contenance_m2 = NULL WHERE idu = '97415000CW9658'"))
    html = client.get("/flash", params={"idu": "97415000CW9658"}).text
    # sans contenance : le dessin sert de repli, dit « mesurée sur le plan », pas de ligne « Dessin du plan »
    assert "· 27 156 m² · Vue aérienne IGN" in html
    assert "Surface mesurée sur le plan cadastral." in html
    assert "Dessin du plan :" not in html
