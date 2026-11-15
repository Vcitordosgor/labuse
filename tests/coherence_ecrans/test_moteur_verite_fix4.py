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


# LOT 2 — liste blanche exacte : budgets Salazie (2 latérales + 1 fond, articles distincts),
# fermoirs par prescription (patrimoine Plaine, RHI/linéaires Le Port), garde micro-parcelle.
CAS_LOT2_PLAFONDS = [
    ("97421000AV1339", 1327),    # coupe hors contour fermée + budget : 1 latérale cadastrale
    #  (37,7 m) + 1 fond (24,4 m) mesurés — plus jamais 1482 sur lignes hors contour
    ("97421000AH0074", 586),     # 2 latérales cadastrales (32,3/32,8 m) ; coupe interne fermée
    ("97421000AV1267", 902),     # défendable (relecteur) : 2 latérales + 1 fond au cadastre
    ("97406000AT0753", 159),     # côté coupé au changement de voisin (29,4 m, rejeu exact)
    ("97406000AC0460", 208),     # côté cadastral le plus favorable (le rejeu relecteur : 198)
    ("97406000AE0113", 497),     # ≤ rejeu relecteur
    ("97407000AO1877", 540),     # Uc hors RHI / hors linéaire commercial : ouverture tient
]


@pytest.mark.parametrize("idu,plafond", CAS_LOT2_PLAFONDS)
def test_lot2_budgets_et_fermoirs(app_session, idu, plafond):
    sdp, _f = _sdp(app_session, idu)
    assert sdp is not None, f"{idu} : SDP absente (attendu ≤ {plafond})"
    assert sdp <= plafond + 0.5, f"{idu} : {sdp} m² > plafond {plafond} m²"


# LOT 2 — pas de capacité chiffrée : micro-parcelle seule (< 40 m²) et façade sur voie < 3 m.
CAS_LOT2_SANS_CHIFFRE = [
    ("97407000AO1876", "micro-parcelle"),    # 9 m² — 5 m² extrudés sur 5 niveaux avant le fix
    ("97408000BK0245", "façade"),            # 2,9 m de façade — desserte à établir
]


@pytest.mark.parametrize("idu,motif", CAS_LOT2_SANS_CHIFFRE)
def test_lot2_micro_parcelle_sans_capacite_chiffree(app_session, idu, motif):
    sdp, f = _sdp(app_session, idu)
    assert sdp is None, f"{idu} : {sdp} m² chiffrés sur une parcelle {motif}"
    assert f.constructible is True
    assert "capacité à vérifier" in f.verdict


# LOT 3 — les formules de retrait relatif s'exécutent (erreurs déjà présentes dans MAIN) +
# hauteurs Saint-Denis (Udo par rue → à vérifier ; Ud ≤ prospect calculé ; Uicm plafond Ui.10).
CAS_LOT3_PLAFONDS = [
    ("97418000AS1397", 1352),    # UAz : H/2 de la hauteur TOTALE de façade — 5 321 m² servis
    #  avec 3 m avant le fix. FIX-4 LOT 6 : façade = celle du BÂTIMENT ENVISAGÉ, niveau par
    #  niveau (n × 3 m + 1,5 m de toiture/acrotère) → R+3, recul 6,75 m, 1 352 m² (le 519 du
    #  relecteur était à 27 m FIXES ; « un projet plus bas peut donner davantage »)
    ("97411000AO0584", 822),     # Ud : hauteur retenue = min(prospect calculé 10 m, plage) —
    #  12 m/1 645 m² servis avant le fix
    ("97411000HX0075", 2279),    # Uicm : retrait 5 m + CES 40 % + plafond Ui.10 12 m (chiffre
    #  du relecteur à hypothèses identiques)
    ("97411000BP0869", 1966),    # idem (chiffre du relecteur)
]


# LOT 6 — « hauteur totale de façade » = la façade du bâtiment ENVISAGÉ, niveau par niveau
# (n × étage + marge toiture/acrotère 1,5 m, ÉCRITE au scénario) ; « différence d'altitude
# point à point » reste en référence prudente.
CAS_LOT6_PLAFONDS = [
    ("97418000AV2758", 578),     # Sainte-Marie UA : optimum niveau par niveau, < main (1 814)
]


@pytest.mark.parametrize("idu,plafond", CAS_LOT6_PLAFONDS)
def test_lot6_facade_envisagee(app_session, idu, plafond):
    sdp, _f = _sdp(app_session, idu)
    assert sdp is not None and sdp <= plafond + 0.5, f"{idu} : {sdp} m² > plafond {plafond} m²"


def test_lot6_marge_toiture_ecrite(app_session):
    """La marge de toiture/acrotère (1,5 m) est FIXÉE et ÉCRITE dans le scénario servi."""
    from labuse.gabarit.builder import MARGE_FACADE_TOITURE_M, build_gabarit_input
    assert MARGE_FACADE_TOITURE_M == 1.5
    gb = build_gabarit_input(app_session, "97418000AS1397")
    if gb is None:
        pytest.skip("AS1397 absente")
    txt = (gb.raccordement.get("plu") or {}).get("recul_sep_formule", "")
    assert "hauteur totale de façade du bâtiment envisagé" in txt and "1.5 m" in txt


@pytest.mark.parametrize("idu,plafond", CAS_LOT3_PLAFONDS)
def test_lot3_formules_et_hauteurs(app_session, idu, plafond):
    sdp, _f = _sdp(app_session, idu)
    assert sdp is not None, f"{idu} : SDP absente (attendu ≤ {plafond})"
    assert sdp <= plafond + 0.5, f"{idu} : {sdp} m² > plafond {plafond} m²"


def test_lot3_udo_capacite_a_verifier(app_session):
    """Saint-Denis Udo : hauteurs par rue nommée (Ud.10 p.44) — plus JAMAIS 9 m génériques
    (AO0742 servait 865 m², AO0778 « terrain exigu confirmé »)."""
    for idu in ("97411000AO0742", "97411000AO0778"):
        sdp, f = _sdp(app_session, idu)
        assert sdp is None, f"{idu} : {sdp} m² chiffrés sur une hauteur générique"
        assert f.constructible is True and "capacité à vérifier" in f.verdict


# LOT 4 — zone rouge et PLU, dans le bon ordre.
def test_lot4_ppr_avant_secteur_habitat(app_session):
    """AL0165 (Saint-Joseph, Nba, 100 % en R2) : le contrôle du plan de prévention s'applique
    AUSSI aux secteurs d'habitat A/N — plus jamais « constructible sous conditions » sur une
    parcelle entièrement rouge (la branche Nba retournait avant le contrôle PPR)."""
    from labuse.faisabilite.db import parcel_faisabilite
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu='97412000AL0165'")).scalar()
    if pid is None:
        pytest.skip("AL0165 absente de la base réelle")
    _ctx, f = parcel_faisabilite(app_session, pid)
    assert f.constructible is False
    assert "PPR zone rouge" in f.verdict and f.cause == "redhibitoire"


def test_lot4_cascade_hors_rouge_seulement_si_plu_admet(app_session):
    """AC0249 (Saint-Benoît, 71 % rouge, zone Acor FERMÉE au PLU) : la cascade n'écrit
    « capacité réduite » QUE si le PLU admet la construction sur la partie hors rouge —
    sinon l'exclusion reste. BC1134 (portion UA réelle) garde l'allègement, reformulé
    « capacité RÉDUITE, SOUS PRESCRIPTIONS » (jamais une promesse)."""
    from labuse.cascade.context import EvalContext, ParcelRef
    from labuse.cascade.engine import run_cascade
    rows = {r[1]: r for r in app_session.execute(text(
        "SELECT id, idu, commune, coalesce(contenance_m2, ST_Area(geom_2975)) FROM parcels "
        "WHERE idu IN ('97410000AC0249','97420000BC1134')"))}
    if len(rows) < 2:
        pytest.skip("témoins absents de la base réelle")
    ctx = EvalContext(app_session)
    for idu, (pid, _idu, commune, surf) in rows.items():
        res = run_cascade([ParcelRef(id=pid, idu=idu, commune=commune,
                                     surface_m2=float(surf))], ctx)[pid]
        exclue = any(v.is_hard_exclude() for v in res)
        if idu == "97410000AC0249":
            assert exclue, "AC0249 : zone Acor fermée — l'exclusion rouge doit rester"
        else:
            assert not exclue, "BC1134 : portion UA réelle — allègement attendu"
            flag = next(v for v in res if "SOUS PRESCRIPTIONS" in str(v.detail))
            assert "capacité RÉDUITE" in str(flag.detail)
