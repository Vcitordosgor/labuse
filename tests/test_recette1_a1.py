"""RECETTE-1 A1 — le verdict « assiette vide » dit la RAISON réelle.

Avant : toute parcelle dont l'emprise se vidait affichait « Terrain trop exigu compte tenu des
reculs (4 m) » — y compris une parcelle de 19 000 m² entièrement en PPR zone rouge, ou couverte
par un emplacement réservé, ou dont seule une portion U/AU réduite était constructible. La valeur
(0 m²) était juste ; le message était faux. Ici on verrouille le message par RAISON.

- Test 1 (sans base) : le mappage raison → verdict couvre les 5 raisons + le repli « reculs ».
- Test 2 (base applicative, skip si absente) : 4 témoins réels portent la bonne `exigu_raison`.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from labuse.faisabilite.engine import _verdict_assiette_vide
from labuse.faisabilite.db import parcel_faisabilite

APP_URL = os.environ.get("LABUSE_AUDIT_DATABASE_URL") \
    or "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"

# Témoins réels (île) — un par raison + un vrai « reculs ».
TEMOINS = {
    "97415000BN1169": "ppr_rouge",           # U1b 19 047 m², 100 % PPR INTERDICTION
    "97401000AI0016": "emplacement_reserve",  # Ud 5 345 m², 100 % ER « logements/mixité »
    "97415000AS0941": "portion_reduite",      # N 1 625 m², portion U = 86 m²
    "97407000AK1335": "reculs",              # Uc 167 m², réellement étroite
}


def test_verdict_par_raison_couvre_tous_les_cas():
    """Chaque raison a son message ; aucune ne retombe sur « reculs » par défaut, sauf None."""
    for raison in ("ppr_rouge", "emplacement_reserve", "ebc", "contraintes", "portion_reduite"):
        msg, _ = _verdict_assiette_vide(raison, 4.0)
        assert "compte tenu des reculs" not in msg, f"{raison} retombe à tort sur « reculs »"
    # repli : None / inconnu / 'reculs' → message reculs (parcelle réellement étroite)
    for r in (None, "reculs", "inconnu"):
        msg, _ = _verdict_assiette_vide(r, 4.0)
        assert "compte tenu des reculs (4 m)" in msg
    # chaque raison nommée cite sa contrainte
    assert "PPR" in _verdict_assiette_vide("ppr_rouge", 4)[0]
    assert "Emplacement réservé" in _verdict_assiette_vide("emplacement_reserve", 4)[0]
    assert "boisé" in _verdict_assiette_vide("ebc", 4)[0]
    assert "U/AU" in _verdict_assiette_vide("portion_reduite", 4)[0]


def test_temoins_reels_portent_la_bonne_raison():
    """Base applicative : 4 témoins réels → la raison attendue (et la capacité reste 0)."""
    try:
        eng = create_engine(APP_URL)
        Session = sessionmaker(bind=eng, future=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — base indisponible → skip, jamais rouge en CI
        pytest.skip(f"base applicative indisponible ({type(exc).__name__})")
    with Session() as s:
        for idu, attendu in TEMOINS.items():
            pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
            if pid is None:
                pytest.skip(f"témoin {idu} absent (base sans l'île)")
            res = parcel_faisabilite(s, pid)
            assert res is not None, f"{idu} : pas de faisabilité"
            f = res[1]
            assert f.cause == "terrain_exigu", f"{idu} : cause changée ({f.cause}) — run non neutre"
            assert f.exigu_raison == attendu, f"{idu} : raison {f.exigu_raison!r} ≠ {attendu!r}"
            assert f.fourchette["logements_au_sol"] == (0, 0), f"{idu} : capacité ≠ 0"
    eng.dispose()
