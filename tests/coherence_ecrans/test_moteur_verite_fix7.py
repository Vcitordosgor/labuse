"""MOTEUR-VERITE-FIX-7 — le relecteur refuse d278c9202, liste fermée de trois points.

LOT 1 — le repli respecte les MÊMES plafonds de hauteur que le gabarit (une seule fonction).
LOT 2 — un refus se fonde sur une assiette réellement testée (exiguïté limite/alignement ; PPR rouge).
LOT 3 — la SDP littorale correspond à l'assiette annoncée (calculée hors bande).

Chaque cas du rapport devient un test. Base applicative réelle (marqueur `reel`) pour les cas parcelle.
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


# ─────────────────────────── LOT 1 — plafonds de hauteur ───────────────────────────
def test_lot1_niveaux_max_plafond_egout_dabord():
    """La fonction partagée borne les niveaux par l'égout D'ABORD (le défaut du repli était de
    partir du faîtage). UBc La Possession : égout 7 m, faîtage ~11 m, étage 3,5 m → 2 niveaux
    (et non 3). Quand l'article fixe un nombre de niveaux, il a la priorité ; la hauteur totale
    de façade cape aussi par le faîtage moins la marge toiture."""
    from labuse.gabarit.builder import niveaux_max_plafond as nmp
    # égout 7 m, faîtage 11 m, étage 3,5 → 2 niveaux (7//3,5), pas 3 (11//3,5)
    assert nmp(7.0, 11.0, 3.5) == 2
    # faîtage seul (égout non fixé) : (11-3,5)//3,5 = 2
    assert nmp(None, 11.0, 3.5) == 2
    # nombre de niveaux explicite de l'article : priorité (2 niveaux déclarés → R+1 = 2)
    assert nmp(20.0, 30.0, 3.5, niveaux_max_zone=1) == 2
    # hauteur totale de façade : cape par faîtage - marge (1,5 m) → (11-1,5)//3,5 = 2
    assert nmp(None, 11.0, 3.5, h_reference="hauteur_totale_facade") == 2
    # rien de fixé → None (aucune borne de hauteur dérivable)
    assert nmp(None, None, 3.5) is None


@pytest.mark.reel
def test_lot1_repli_ne_depasse_pas_le_plafond_egout(app_session):
    """AC1866 (La Possession UBc) servait 887 m² sur 3 niveaux (9 m à l'égout pour 7 m admis).
    Borné au plafond à l'égout → 2 niveaux. AN1434 (UBpsfr2) et AW0571 (UBb) retombent
    exactement au chiffre de main en appliquant ce plafond au calcul de repli."""
    for idu, sdp_max, exp in (("97408000AC1866", 887, None),
                              ("97408000AN1434", 27166, 20375),
                              ("97408000AW0571", 11132, 7421)):
        ctx, f = _res(app_session, idu)
        fr = f.fourchette or {}
        sdp, niv = fr.get("surface_plancher_m2"), fr.get("niveaux_max")
        assert sdp is not None and niv is not None, f"{idu} : pas de chiffre"
        assert sdp < sdp_max, f"{idu} : {sdp} m² non borné (était {sdp_max})"
        if exp is not None:
            assert abs(sdp - exp) <= 2, f"{idu} : {sdp} m² ≠ chiffre de main attendu {exp}"
