"""K4 (rattrapage KelFoncier) — couleurs de MARQUE : source unique + verrou anti-hardcode.

Le vert de marque #4ADE80 (M83-D) n'a le droit d'exister EN LITTÉRAL qu'à UN endroit :
`config/brand_colors.json`, lu par le front (tailwind) ET par le back (brand.py). Ce test grave :
  1. l'égalité de la source (JSON == brand.py == référence tailwind) ;
  2. l'absence de tout hex de marque en dur dans les chaînes des modules serveur qui rendent du
     HTML/CSS (coffre_ui, partners, onboarding, cli) — l'ancien orphelin #5CE6A1 inclus ;
  3. que le bouton de /invitation calcule bien le vert de marque (via var(--mint)).
"""
from __future__ import annotations

import io
import json
import tokenize
from pathlib import Path

import pytest

from labuse import brand

_ROOT = Path(__file__).resolve().parents[1]

# hex/rgb de marque qui ne doivent JAMAIS être posés en dur dans une chaîne serveur.
_INTERDITS = ("#5CE6A1", "#4ADE80", "92,230,161")

# modules serveur qui rendent du HTML/CSS de marque.
_MODULES = (
    "src/labuse/api/coffre_ui.py",
    "src/labuse/api/partners.py",
    "src/labuse/api/onboarding.py",
    "src/labuse/cli.py",
)


def test_source_unique_json_egale_python():
    data = json.loads((_ROOT / "config" / "brand_colors.json").read_text(encoding="utf-8"))
    assert data["mint"] == brand.MINT == "#4ADE80"       # le vert de marque, une seule valeur
    assert data["mint_rgb"] == brand.MINT_RGB
    assert brand.mint_rgba(".16") == f"rgba({brand.MINT_RGB},.16)"


def test_front_lit_la_meme_source():
    """tailwind.config.js consomme le JSON partagé (pas un hex de marque en dur)."""
    tw = (_ROOT / "frontend" / "tailwind.config.js").read_text(encoding="utf-8")
    assert "config/brand_colors.json" in tw          # requiert bien la source partagée
    assert "mint: brand.mint" in tw                  # `mint` vient du JSON, pas d'un littéral
    # le SEUL #5CE6A1 encore permis côté front = st-chaude (couleur de STATUT, pas de marque)
    assert "'st-chaude': '#5CE6A1'" in tw


@pytest.mark.parametrize("rel", _MODULES)
def test_aucun_hex_de_marque_en_dur(rel: str):
    """Verrou anti-hardcode : aucun hex de marque dans une CHAÎNE (commentaires Python exclus)."""
    src = (_ROOT / rel).read_text(encoding="utf-8")
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.STRING:
            up = tok.string.upper()
            for bad in _INTERDITS:
                assert bad.upper() not in up, f"{rel} : « {bad} » posé en dur dans une chaîne"


def test_bouton_invitation_calcule_le_vert_de_marque(monkeypatch):
    """La page /invitation définit --mint depuis la source et peint le bouton avec var(--mint)."""
    from fastapi.testclient import TestClient

    from labuse import comptes
    from labuse.api import coffre_ui
    from labuse.api.app import app

    # invitation valide simulée (la base de test est vide) — tunnel CLIENT.
    monkeypatch.setattr(comptes, "valider_invitation",
                        lambda db, token: {"plan": "client", "email": "vic@example.re", "compte_id": 1})

    html = TestClient(app).get("/invitation?token=peu-importe").text
    assert f"--mint:{brand.MINT}" in html                 # --mint servi DEPUIS la source unique
    assert 'id="cta"' in html                             # le bouton d'action existe
    assert "background:var(--mint)" in coffre_ui.CSS      # le bouton se peint AVEC var(--mint)
    # aucun orphelin ne subsiste sur la surface servie
    assert "#5CE6A1" not in html and "92,230,161" not in html
