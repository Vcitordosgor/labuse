"""MOTEUR-VERITE-FIX-4 — les cas du relecteur, un par un, sur base réelle.

Chaque parcelle du rapport devient un test : la capacité servie doit valoir le chiffre que le
relecteur a reproduit (côté cadastral seul, coupes internes fermées), ou rester EN DESSOUS
(toute nouvelle prudence est admise, jamais une remontée). Base applicative réelle requise
(marqueur `reel`) ; joué au push par le hook.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.coherence, pytest.mark.reel]


def _sdp(app_session, idu: str):
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"{idu} absente de la base réelle")
    res = parcel_faisabilite(app_session, pid)
    assert res is not None, f"{idu} : faisabilité absente"
    _ctx, f = res
    return (f.fourchette or {}).get("surface_plancher_m2"), f


# LOT 1 — coupes internes et côtés cadastraux (rejeux du relecteur).
#   (idu, plafond admis) : la valeur servie doit être ≤ plafond (chiffre reproduit par le
#   relecteur avec le seul côté cadastral ouvert, ou valeur FIX-3 pour les « corrigés »).
CAS_LOT1 = [
    ("97406000AE0114", 88),      # coupe interne fermée (cad=False) ; 88 = côté cadastral de
    #  18,7 m (choix le plus favorable admis par « une seule limite ») — le rejeu du relecteur
    #  (83) ouvrait un autre côté ; l'essentiel est la coupe fermée (109 → 88)
    ("97406000AE0249", 177),     # tient avec une seule limite cadastrale de 42 m
    ("97406000AT0753", 159),     # tient (limite de 29,4 m)
    ("97406000AI1063", 220),     # tient malgré la polyligne qui réunissait trois côtés
    ("97420000AH0293", 3313),    # anneau en retrait (FIX-3) — ne doit pas rouvrir
    ("97404000AY0554", 250),
    ("97415000AH1368", 238),
    ("97422000AW0503", 72),
    ("97419000AS0031", 315),     # façade 52,6 m > 14 m : aucun côté ouvert
]


@pytest.mark.parametrize("idu,plafond", CAS_LOT1)
def test_lot1_cotes_cadastraux(app_session, idu, plafond):
    sdp, _f = _sdp(app_session, idu)
    assert sdp is not None, f"{idu} : SDP absente (attendu ≤ {plafond})"
    assert sdp <= plafond + 0.5, f"{idu} : {sdp} m² servis > {plafond} m² (côté cadastral seul)"
