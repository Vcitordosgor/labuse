"""MOTEUR-VERITE-FIX-8 — le relecteur valide le décompte, reste sa liste fermée de trois points.

LOT 1 — le littoral se calcule sur la GÉOMÉTRIE DU SCÉNARIO (assiette découpée par la bande),
        pas en prorata du terrain entier (faux dans les deux sens).
LOT 2 — un refus exige une absence MESURÉE (mesure indisponible ≠ vide ; contact rouge significatif ;
        libellé ER « épuisent l'assiette après reculs »).
LOT 3 — une preuve fidèle au calcul (recul côté par côté ; sans-règle = retrait prudent de référence).

Base applicative réelle (marqueur `reel`) pour les cas parcelle.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.coherence]


def _res(app_session, idu: str):
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"{idu} absente de la base réelle")
    r = parcel_faisabilite(app_session, pid)
    assert r is not None
    _ctx, f = r
    return _ctx, f


# ─────────────── LOT 1 — littoral sur la géométrie du scénario ───────────────
@pytest.mark.reel
def test_lot1_littoral_sur_geometrie(app_session):
    """Le prorata du terrain entier était faux dans les deux sens. On découpe l'assiette du scénario
    (inset au recul servi, ici 6 m) par la bande et on recalcule sur ce qui reste :
      · BL0308 — l'assiette (398 m²) est ENTIÈREMENT dans la bande (intersection hors bande = 0 m²) :
        « capacité à vérifier » sans chiffre (le prorata servait 98 m² à tort) ;
      · BL0040 — l'assiette est ENTIÈREMENT hors bande : chiffre PLEIN, aucune réduction
        (le prorata réduisait à tort)."""
    _ctx, f = _res(app_session, "97408000BL0308")
    assert (f.fourchette or {}).get("surface_plancher_m2") is None, \
        "BL0308 : chiffre servi alors que l'assiette du scénario est entièrement dans la bande"
    assert f.constructible is True and (f.cause or "") != "terrain_exigu"
    assert "trait de côte" in (f.verdict or "").lower() and "bande" in (f.verdict or "").lower()

    _ctx, f2 = _res(app_session, "97408000BL0040")
    sdp2 = (f2.fourchette or {}).get("surface_plancher_m2")
    assert sdp2 is not None and sdp2 >= 1860, \
        f"BL0040 : assiette entièrement hors bande → chiffre plein attendu, obtenu {sdp2}"
    # pas de réserve « hors bande » quand rien n'est dans la bande de l'assiette
    assert not any("hors bande" in a.lower() for a in (f2.avertissements or [])), \
        "BL0040 : réserve hors bande posée alors que l'assiette est entièrement hors bande"
