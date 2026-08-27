"""S3 (lisibilité des pages légales) — structure de lecture des 3 pages légales.

Le fond juridique ne change pas ; on gèle la PRÉSENTATION : sommaire cliquable + ancres pour la
CGV, colonne de lecture (mode legal), retour en haut.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def test_cgv_sommaire_cliquable_et_ancres(client):
    html = client.get("/cgv").text
    # sommaire présent
    assert 'class="toc"' in html and "Sommaire" in html
    # 11 ancres d'articles (1–10 + 4 bis) et autant de cibles href="#aN"
    ancres = set(re.findall(r'<h2 id="(a\w+)">', html))
    assert {"a1", "a4bis", "a5", "a9", "a10"} <= ancres and len(ancres) == 11
    for a in ancres:
        assert f'href="#{a}"' in html
    # retour en haut
    assert 'href="#haut"' in html and "Haut de page" in html


def test_pages_legales_en_mode_lecture(client):
    """Les 3 pages légales rendent en mode « legalpage » (colonne de lecture, pas bloc 400px)."""
    for url in ("/cgv", "/mentions-legales", "/confidentialite"):
        html = client.get(url).text
        assert 'class="legalpage"' in html, f"{url} pas en mode lecture"
        assert 'class="legal"' in html


def test_css_colonne_de_lecture_confortable():
    """La CSS légale impose une colonne ~68ch (ni bloc 400px étroit, ni pleine largeur)."""
    from labuse.api import coffre_ui
    assert ".legal{max-width:68ch" in coffre_ui.CSS.replace("\n", "")
    # O1 — le body n'est plus flex ; le mode lecture top-aligne via `.legalpage .top`.
    assert ".legalpage .top{justify-content:flex-start" in coffre_ui.CSS
