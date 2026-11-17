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


# ─────────────── LOT 2 — un refus exige une absence MESURÉE ───────────────
@pytest.mark.reel
def test_lot2a_mesure_indisponible_nest_pas_un_vide(app_session, monkeypatch):
    """Une mesure indisponible n'est pas une assiette vide. En simulant l'indisponibilité de la
    mesure hors rouge sur AT2046 (zone rouge significative), on obtenait un refus « terrain exigu »
    et un zéro ; on doit désormais servir « capacité à vérifier » avec le motif, jamais un refus."""
    from sqlalchemy import text as _t
    import labuse.faisabilite.db as _db
    monkeypatch.setattr(_db, "_HORS_ROUGE_FRAGMENT", _t("SELECT 1/0 AS m2, NULL AS wkt"))
    _ctx, f = _res(app_session, "97408000AT2046")
    assert f.constructible is True and f.cause != "terrain_exigu", \
        "AT2046 : refus prononcé sur une mesure indisponible (absence non mesurée)"
    assert "indisponible" in (f.verdict or "").lower()


@pytest.mark.reel
def test_lot2b_contact_rouge_negligeable_garde_le_chiffre(app_session):
    """La zone rouge ne fait perdre un chiffre que si elle TOUCHE réellement l'assiette. AM0577
    (contact rouge ~0,003 m², bien sous le seuil de 1 m²) ne doit pas perdre ses ~171 m² : le rouge
    négligeable est ignoré, le chiffre est servi."""
    _ctx, f = _res(app_session, "97406000AM0577")
    assert f.constructible is True, "AM0577 : chiffre perdu pour un contact rouge négligeable"
    assert (f.fourchette or {}).get("surface_plancher_m2") is not None, \
        "AM0577 : capacité non chiffrée alors que le rouge est un simple contact de bord"
    # un rouge SIGNIFICATIF reste traité (AT2046 : ~3 m² → « à vérifier » hors rouge)
    _ctx, f2 = _res(app_session, "97408000AT2046")
    assert (f2.fourchette or {}).get("surface_plancher_m2") is None and f2.constructible is True


@pytest.mark.reel
def test_lot2c_libelle_emplacement_reserve(app_session):
    """BO0312 : le libellé dit que l'emplacement réservé ÉPUISE l'assiette APRÈS RECULS, pas qu'il
    « couvre la parcelle »."""
    _ctx, f = _res(app_session, "97408000BO0312")
    assert f.constructible is False
    v = (f.verdict or "").lower()
    assert "après reculs" in v and "couvre la parcelle" not in v and "couvrant la parcelle" not in v, \
        f"BO0312 : libellé ER non conforme — {f.verdict}"


# ─────────────── LOT 3 — une preuve fidèle au calcul ───────────────
@pytest.mark.reel
def test_lot3a_recul_reellement_retenu_cote_par_cote(app_session):
    """Le recul exposé est celui RÉELLEMENT retenu par le gabarit, côté par côté — pas le recul
    d'entrée. AO0308 : le gabarit retient 6 m sur les séparatives (pas 3 m) ; AS1086 : 8,25 m
    (pas 9 m). La voie garde son propre recul."""
    _ctx, f = _res(app_session, "97408000AO0308")
    assert abs((_ctx.recul_servi_m or 0) - 6.0) < 0.2, f"AO0308 : recul retenu {_ctx.recul_servi_m} ≠ 6 m"
    assert "latérale 6" in (_ctx.recul_par_cote or ""), f"AO0308 : côté par côté — {_ctx.recul_par_cote}"
    _ctx, f = _res(app_session, "97418000AS1086")
    assert abs((_ctx.recul_servi_m or 0) - 8.25) < 0.2, f"AS1086 : recul retenu {_ctx.recul_servi_m} ≠ 8,25 m"


@pytest.mark.reel
def test_lot3b_sans_regle_retablit_le_retrait_prudent(app_session):
    """Le rejeu de contrôle « sans la règle » rétablit le retrait PRUDENT de référence (fraction ×
    faîtage, ce que fait main), pas le recul d'entrée. Sur AN1411 (La Possession, rule niveau-par-
    niveau), la capacité tombe au chiffre de main (~174 m²) avec le retrait prudent — ce qui isole
    l'effet de la règle (la branche sert 2 298 m²) des changements de géométrie (nuls ici)."""
    import labuse.gabarit.engine as _E
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu='97408000AN1411'")).scalar()
    if pid is None:
        pytest.skip("AN1411 absente")
    _ctx, f_regle = parcel_faisabilite(app_session, pid)
    sdp_regle = (f_regle.fourchette or {}).get("surface_plancher_m2")
    _E.RETRAIT_PRUDENT_REFERENCE = True
    try:
        _ctx, f_prud = parcel_faisabilite(app_session, pid)
    finally:
        _E.RETRAIT_PRUDENT_REFERENCE = False
    sdp_prud = (f_prud.fourchette or {}).get("surface_plancher_m2")
    assert sdp_regle and sdp_prud and sdp_prud < sdp_regle, \
        f"AN1411 : le retrait prudent ne réduit pas (règle {sdp_regle}, prudent {sdp_prud})"
    assert sdp_prud <= 200, f"AN1411 : retrait prudent {sdp_prud} m² loin du chiffre de main (~174)"
