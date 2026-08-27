"""Couleurs de MARQUE LABUSE — face Python de la source unique.

Lit `config/brand_colors.json` (le MÊME fichier que le front consomme via
`frontend/tailwind.config.js`). Le vert de marque `#4ADE80` (M83-D « nouvelle marque »,
aligné sur l'oiseau) n'existe en littéral qu'ici, dans le JSON. Tout module serveur qui
rend du HTML/CSS (coffre_ui, onboarding, partners, cli) doit passer par ces constantes —
verrou anti-hardcode dans `tests/test_brand_colors.py`.

Rappel doctrine : « une couleur de marque = un point de définition unique ». Les couleurs de
STATUT (tiers : chaude `#5CE6A1`, à surveiller, etc.) ne sont PAS de la marque et ne passent
pas par ce module.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# repo/config/brand_colors.json — remonte depuis src/labuse/brand.py
_JSON = Path(__file__).resolve().parents[2] / "config" / "brand_colors.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(_JSON.read_text(encoding="utf-8"))


MINT: str = _data()["mint"]            # #4ADE80 — accent / CTA / logo, LE vert de marque
MINT_RGB: str = _data()["mint_rgb"]    # "74,222,128" — pour les rgba(...) (ombres, halos, tints)
MINT_DIM: str = _data()["mint_dim"]    # #2E9E5B — liens & puces (vert sobre, ne porte pas de texte)
MINT_INK: str = _data()["mint_ink"]    # #04150A — encre lisible SUR le vert (texte de bouton)


def mint_rgba(alpha: float | str) -> str:
    """rgba() du vert de marque à l'opacité donnée — jamais un triple RGB en dur ailleurs."""
    return f"rgba({MINT_RGB},{alpha})"
