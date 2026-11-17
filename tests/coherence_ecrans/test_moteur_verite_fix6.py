"""MOTEUR-VERITE-FIX-6 — l'ordre des verdicts : un refus établi ne s'efface jamais.

Les refus réglementaires (habitat interdit, zone fermée, parcelle refusée par main faute
d'assiette utilisable) passent AVANT les gardes de taille / « capacité à vérifier ».
Base applicative réelle requise (marqueur `reel`).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.coherence, pytest.mark.reel]


def _res(app_session, idu: str):
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"{idu} absente de la base réelle")
    r = parcel_faisabilite(app_session, pid)
    assert r is not None
    _ctx, f = r
    return f


# LOT 1 — refus réglementaires/établis : la parcelle NE DOIT PAS ressortir « constructible ».
#   (idu, cause attendue approximative)
# NB CG0875 (Saint-Leu UC, 92 m²) n'est PLUS un refus : la zone admet l'implantation en limite
# (≤ 10 m), l'assiette tient à la limite — LOT 7 la requalifie « capacité à vérifier » (cf. ci-dessous).
REFUS = [
    ("97418000AC1634", "habitat_interdit"),   # Sainte-Marie UEm, 20 m² : habitat interdit AVANT micro-garde
]


@pytest.mark.parametrize("idu,cause", REFUS)
def test_lot1_refus_etabli_preserve(app_session, idu, cause):
    f = _res(app_session, idu)
    assert f.constructible is False, f"{idu} : refus établi devenu constructible"
    assert (f.cause or "").startswith(cause.split(":")[0]), f"{idu} : cause {f.cause}, attendu {cause}"


# LOT 2 — un seul jeu de règles pour le repli : niveau par niveau + test rouge∩PLU.
def test_lot2_repli_niveau_par_niveau(app_session):
    """AD0173 (Sainte-Marie UA, zone autorisée) servie par le REPLI : le retrait relatif se
    calcule niveau par niveau (R+1, 3,75 m) comme le gabarit, plus un retrait uniforme de 9 m
    qui vidait l'assiette à tort (363 → 0 « trop exigu »). Baisse, pas refus ferme."""
    f = _res(app_session, "97418000AD0173")
    sdp = (f.fourchette or {}).get("surface_plancher_m2")
    assert f.constructible is True and sdp is not None, "AD0173 : refus ferme injustifié"
    assert 60 <= sdp <= 363, f"AD0173 : {sdp} m² hors de la fourchette R+1 attendue"


def test_lot2_repli_rouge_et_plu(app_session):
    """AW1235/BM0158/BO0383 ne servent plus leur chiffre repli (la cascade l'excluait). Mais
    FIX-7 LOT 2 : leurs parties hors rouge en U/AU (~87, 144, 194 m²) sont SOUS le seuil interne
    de 200 m² — convention LABUSE, pas une règle. Ce n'est donc pas un refus mais « capacité à
    vérifier », avec la surface hors rouge mesurée (le chiffre n'est pas servi : non chiffré)."""
    for idu in ("97405000AW1235", "97410000BM0158", "97409000BO0383"):
        f = _res(app_session, idu)
        assert f.constructible is True, f"{idu} : refus alors que le rouge ne prive pas la partie constructible"
        assert (f.fourchette or {}).get("surface_plancher_m2") is None, f"{idu} : chiffre servi malgré l'exclusion cascade"
        assert any("hors" in a.lower() and "rouge" in a.lower() for a in (f.avertissements or [])), \
            f"{idu} : surface hors rouge non mentionnée"


# LOT 3 — réserves et libellés.
def test_lot3_reserve_au_suit_la_portion(app_session):
    """La réserve « zone AU » suit la portion servie, pas la zone dominante : AK0834 (A dominant,
    portion 1AUa) et AE0409 (N dominant, portion 1AUc) servent sur la portion AU."""
    for idu in ("97419000AK0834", "97419000AE0409"):
        f = _res(app_session, idu)
        sdp = (f.fourchette or {}).get("surface_plancher_m2")
        if sdp is None:
            pytest.skip(f"{idu} sans chiffre")
        assert any("conditions d'aménagement" in a for a in (f.avertissements or [])), \
            f"{idu} : capacité AU chiffrée sans réserve d'aménagement/OAP"


def test_lot3_hauteur_porte_son_vrai_nom(app_session):
    """AS0606 (La Possession AUB, zone AU) : le calcul prudent utilise le FAÎTAGE (12 m), pas
    l'égout (9 m) — le libellé doit dire « faîtage », jamais « égout 12 m »."""
    from labuse.gabarit.builder import build_gabarit_input
    gb = build_gabarit_input(app_session, "97408000AS0606")
    if gb is None:
        pytest.skip("AS0606 sans gabarit")
    rsf = (gb.raccordement.get("plu") or {}).get("recul_sep_formule") or ""
    assert "égout 12" not in rsf, f"AS0606 : hauteur mal nommée — {rsf}"
    assert "faîtage" in rsf


def test_lot3_sous_prescriptions_seulement_si_bleue(app_session):
    """« Sous prescriptions » ne s'écrit que si une zone bleue touche la parcelle : AH0074
    (rouge seul, aucune bleue) ne porte pas la réserve bleue."""
    f = _res(app_session, "97421000AH0074")
    assert not any("prescriptions du plan de prévention" in a for a in (f.avertissements or [])), \
        "AH0074 : réserve bleue sans zone bleue"


# LOT 5 — gardes de doute : réserve au lieu de retrait du chiffre (sauf assiette nulle).
# NB FIX-8 LOT 1 calcule le littoral sur la GÉOMÉTRIE du scénario (assiette découpée par la bande) :
# BM0052, dont l'assiette du scénario est ENTIÈREMENT hors bande, garde donc son chiffre PLEIN sans
# réserve (la bande touche la parcelle mais pas l'assiette). Le cas « assiette dans la bande → à
# vérifier » est couvert par test_moteur_verite_fix8::test_lot1_littoral_sur_geometrie (BL0308).
def test_lot5_littoral_assiette_hors_bande_garde_le_chiffre(app_session):
    """BM0052 (La Possession) : la bande littorale touche la parcelle, mais l'assiette du scénario
    est entièrement hors bande → le chiffre est servi, non vidé par le recul prospectif."""
    f = _res(app_session, "97408000BM0052")
    assert f.constructible is True
    assert (f.fourchette or {}).get("surface_plancher_m2") is not None, \
        "BM0052 : chiffre vidé alors que l'assiette du scénario est hors bande"


# LOT 6 — « trop exigu » veut dire que rien ne tient dans le scénario le plus favorable.
def test_lot6_faux_exigu_devient_a_verifier(app_session):
    """Sainte-Marie UA sans façade établie : le recul PRUDENT (9 m) vide l'assiette, mais le
    scénario FAVORABLE (R+1, recul minimal 3 m) laisse une emprise → pas exigu. Le verdict est
    « constructible, capacité à vérifier », jamais un refus (AD0280, main chiffrait 168 m²)."""
    for idu in ("97418000AD0280", "97418000AT0539", "97418000AT0493"):
        f = _res(app_session, idu)
        assert f.constructible is True, f"{idu} : faux terrain exigu (refus) persiste"
        assert (f.cause or "") != "terrain_exigu"


def test_lot6_vrai_exigu_et_refus_reglementaire_restent(app_session):
    """Les refus qui demeurent : l'emprise rouge COUVRE la partie constructible (DR0615, Saint-Paul
    U6c, hors rouge ≈ 0 m² — FIX-7 LOT 2, seule situation rouge qui fonde un refus), et le refus
    réglementaire (AC1634, habitat interdit). La référence prudente ne crée ni ne lève le refus.
    NB AD0982 (72 % rouge) n'est PLUS un refus : sa partie hors rouge n'est pas négligeable."""
    f = _res(app_session, "97415000DR0615")   # ~100 % rouge : hors rouge négligeable → refus établi
    assert f.constructible is False and f.cause == "terrain_exigu"
    f = _res(app_session, "97418000AC1634")   # habitat interdit
    assert f.constructible is False and f.cause == "habitat_interdit"


# LOT 7 — implantation en limite / à l'alignement : une assiette vidée par le retrait prudent mais
# qui TIENT à la limite n'est jamais un refus ; c'est « capacité à vérifier » avec la mention limite.
def test_lot7_implantation_en_limite_devient_a_verifier(app_session):
    """AO0709 (Le Port Ud, 84 m²) et CG0875 (Saint-Leu UC, 92 m²) : le retrait séparatif vide
    l'assiette, mais le règlement admet l'implantation en limite / à l'alignement et l'assiette
    tient à la limite (recul 0). Verdict « constructible, capacité à vérifier », jamais exigu ;
    aucune capacité chiffrée (on ne surestime pas), mention d'implantation en limite portée."""
    for idu in ("97407000AO0709", "97413000CG0875"):
        f = _res(app_session, idu)
        assert f.constructible is True, f"{idu} : faux terrain exigu en zone à implantation en limite"
        assert (f.cause or "") != "terrain_exigu"
        assert (f.fourchette or {}).get("surface_plancher_m2") is None, \
            f"{idu} : capacité chiffrée alors que seule l'implantation en limite tient (surestimation)"
        assert any("limite" in a.lower() for a in (f.avertissements or [])) or "limite" in (f.verdict or "").lower(), \
            f"{idu} : mention d'implantation en limite absente"
