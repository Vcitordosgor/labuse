"""RETOURS-16 V1 — la mer partout, sans marches (constat Vic 05/09, 4e recette).

Gardes du proxy ortho généralisé (api/ortho_proxy.py) : toutes les sources ortho du front y
passent, la mer photo est limitée à la bande côtière (fondu vers l'aplat unique), les tuiles
entièrement au large répondent 404 sans requête IGN, et l'aplat est LA MÊME couleur des deux
côtés (proxy MER_HEX == front MER_ORTHO).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]


def _tilexy(lat: float, lon: float, z: int) -> tuple[int, int]:
    x = int((lon + 180) / 360 * 2 ** z)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat)))
             / math.pi) / 2 * 2 ** z)
    return x, y


def test_toutes_les_sources_ortho_du_front_passent_par_le_proxy():
    """V1 pt 1 — plus aucune tuile ortho brute : chaque fond bm-ortho* et la sous-couche monde
    pointent /map/tiles/ortho/<couche>/ et chaque <couche> existe dans la whitelist du proxy."""
    from labuse.api.ortho_proxy import _COUCHES
    bm = (ROOT / "frontend/src/components/map/basemaps.ts").read_text(encoding="utf-8")
    couches_front = set(re.findall(r"ORTHO_PROXY\('([a-z0-9]+)'\)", bm))
    assert couches_front, "le front doit consommer ORTHO_PROXY(...)"
    assert couches_front <= set(_COUCHES), couches_front - set(_COUCHES)
    # aucune URL WMTS IGN directe sur une couche ORTHO (le Plan IGN, non-ortho, reste direct)
    for ligne in bm.splitlines():
        if "WMTS('ORTHOIMAGERY" in ligne:
            raise AssertionError(f"source ortho brute restée dans basemaps.ts : {ligne.strip()}")


def test_aplat_de_mer_meme_couleur_proxy_et_front():
    """V1 pt 2 — l'aplat est UNE seule couleur, définie une fois de chaque côté, identique."""
    from labuse.api.ortho_proxy import MER_HEX
    mv = (ROOT / "frontend/src/components/map/MapView.tsx").read_text(encoding="utf-8")
    m = re.search(r"const MER_ORTHO = '(#[0-9A-Fa-f]{6})'", mv)
    assert m, "MER_ORTHO doit exister dans MapView.tsx"
    assert m.group(1).lower() == MER_HEX.lower()
    # et le canvas la sert bien sous les fonds ortho
    assert "basemap === 'ortho' ? MER_ORTHO" in mv


def test_tuile_au_large_404_sans_requete_ign(tmp_path, monkeypatch):
    """V1 pt 4 (coût) — une tuile entièrement au large répond 404 SANS toucher l'IGN."""
    monkeypatch.setenv("LABUSE_ORTHO_PROXY_CACHE_DIR", str(tmp_path))
    from labuse.config import get_settings
    get_settings.cache_clear()
    from labuse.api import ortho_proxy as op
    import requests
    def _interdit(*a, **k):  # noqa: ANN001
        raise AssertionError("requête IGN partie pour une tuile au large")
    monkeypatch.setattr(requests, "get", _interdit)
    x, y = _tilexy(-21.13, 51.0, 10)   # 470 km à l'ouest de l'île : plein océan
    with pytest.raises(HTTPException) as exc:
        op.ortho_tile("monde", 10, x, y)
    assert exc.value.status_code == 404
    get_settings.cache_clear()


def test_alpha_cote_trois_regimes():
    """Le champ côtier distingue : au large (None) · pleine terre (« pleine ») · côte (champ)."""
    from labuse.api.ortho_proxy import _alpha_cote
    z = 13
    assert _alpha_cote(z, *_tilexy(-21.13, 51.0, z)) is None            # plein océan
    assert _alpha_cote(z, *_tilexy(-21.13, 55.53, z)) == "pleine"       # Plaine des Cafres
    champ = _alpha_cote(z, *_tilexy(-20.878, 55.448, z))                # front de mer St-Denis
    assert champ is not None and not isinstance(champ, str)
    assert float(champ.max()) == 1.0 and float(champ.min()) == 0.0      # terre pleine ET large


def test_couche_inconnue_404():
    from labuse.api import ortho_proxy as op
    with pytest.raises(HTTPException) as exc:
        op.ortho_tile("planignv2", 10, 0, 0)
    assert exc.value.status_code == 404
