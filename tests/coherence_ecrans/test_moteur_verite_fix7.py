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


# ─────────────── LOT 2 — refus fondé sur une assiette réellement testée ───────────────
@pytest.mark.reel
def test_lot2_exiguite_limite_ou_alignement_a_verifier(app_session):
    """Zone admettant la limite ou l'alignement (même sous conditions) : une assiette vide avec
    les retraits n'établit pas un refus. AO0709 (Le Port Ud5) et CG0875 (Saint-Leu UC7 p.42) →
    « capacité à vérifier ». Le motif dit ce qui a été testé (retrait uniforme minimal / limite),
    sans promettre un R+1 réglementaire."""
    for idu in ("97407000AO0709", "97413000CG0875"):
        ctx, f = _res(app_session, idu)
        assert f.constructible is True and (f.cause or "") != "terrain_exigu", f"{idu} : refus exigu"
        assert (f.fourchette or {}).get("surface_plancher_m2") is None, f"{idu} : chiffre servi (surestimation)"
        v = (f.verdict or "").lower()
        assert "r+1" not in v, f"{idu} : le motif promet un R+1 réglementaire — {f.verdict}"
        assert "limite" in v or "alignement" in v, f"{idu} : implantation en limite non mentionnée"


@pytest.mark.reel
def test_lot2_ppr_rouge_trois_situations(app_session):
    """PPR rouge, trois situations, trois verdicts. Seule l'emprise rouge couvrant la partie
    constructible fonde un refus (DR0615, hors rouge ≈ 0). Les deux autres sont des doutes →
    « capacité à vérifier » avec la surface hors rouge mesurée :
      · AT2046 (rouge 1,7 %, 112 m² hors rouge < seuil interne 200 — convention LABUSE) ;
      · AM0577 (425 m² hors rouge, accès à établir) ;
      · AD0423 (318 m² d'un seul tenant au contact voie, assiette à confirmer).
    Le test ne refuse pas une parcelle que le rouge ne prive pas de sa partie constructible."""
    # refus : le rouge couvre la partie constructible
    _ctx, f = _res(app_session, "97415000DR0615")
    assert f.constructible is False and f.cause == "terrain_exigu", "DR0615 : rouge couvrant → doit refuser"
    # doutes → à vérifier, sans chiffre, surface hors rouge mesurée
    for idu in ("97408000AT2046", "97406000AM0577", "97418000AD0423"):
        _ctx, f = _res(app_session, idu)
        assert f.constructible is True, f"{idu} : refus alors que le rouge ne prive pas la partie constructible"
        assert f.cause != "terrain_exigu", f"{idu} : cause terrain_exigu persiste"
        assert (f.fourchette or {}).get("surface_plancher_m2") is None, f"{idu} : chiffre servi (non chiffré attendu)"
        v = (f.verdict or "").lower()
        assert "hors" in v and "rouge" in v, f"{idu} : surface/mention hors rouge absente — {f.verdict}"
