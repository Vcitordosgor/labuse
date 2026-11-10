"""FONCIER-PUBLIC-1 — équipements publics et foncier public dans l'Analyse LABUSE par scénario.

Décision de Vic : un ÉQUIPEMENT PUBLIC en place (enseignement, santé, administration, sécurité,
sport, culture, loisirs) rend la parcelle « Hors de ce projet » dans les DEUX scénarios ; un TERRAIN
PUBLIC sans équipement garde sa bande et porte un drapeau ; le Signal n'est jamais touché ; les
commerces / services privés (BPE) ne comptent pas.

Contrôles PURS (classification + moteur) sans base ; contrôles sur la base RÉELLE locale gardés par
`LABUSE_REEL_DATABASE_URL`, sur les trois cas du mandat : 97411000DO0049 (campus de lycées → Hors
projet), une communale nue en zone U (bande gardée + drapeau), une privée portant un commerce
(inchangée).
"""
from __future__ import annotations

import os

import pytest

from labuse.scoring import equipement_public as eqp
from labuse.scoring import scenarios_v2 as v2

# Les contrôles de CLASSIFICATION et de MOTEUR sont PURS (aucune base) : ils tournent dans la famille
# unitaire du hook. Seuls les contrôles sur la base réelle (section 3) portent le marqueur `local`.


# ── (1) classification BPE : RETENUS vs EXCLUS (source unique, mandat) ────────
@pytest.mark.parametrize("sdom,typequ,attendu", [
    # retenus
    ("C1", "C108", "enseignement"), ("C3", "C301", "enseignement"), ("C5", "C501", "enseignement"),
    ("C7", "C701", "enseignement"),
    ("D1", "D101", "santé"),
    ("F1", "F111", "sport"), ("F2", "F201", "loisirs"), ("F3", "F301", "culture"),
    ("A1", "A122", "administration"), ("A1", "A133", "administration"),
    ("A1", "A104", "sécurité"), ("A1", "A140", "sécurité"),
    # exclus (commerces / services privés / hors périmètre)
    ("A2", "A203", None), ("A3", "A301", None), ("A4", "A401", None), ("A5", "A504", None),
    ("B1", "B103", None), ("B2", "B201", None), ("B3", "B302", None),
    ("C6", "C610", None),                                   # formation continue privée
    ("D2", "D279", None), ("D3", "D307", None),             # libéral, pharmacie
    ("D4", "D401", None), ("D5", "D502", None), ("D6", "D601", None), ("D7", "D701", None),
    ("E1", "E101", None), ("G1", "G101", None),
    (None, None, None),
])
def test_categorie_bpe(sdom, typequ, attendu):
    assert eqp.categorie(sdom, typequ) == attendu


def test_dominante_prend_la_priorite():
    # un campus avec lycée + plateau multisport → « enseignement » (prime sur « sport »).
    assert eqp.dominante(["sport", "enseignement"]) == "enseignement"
    assert eqp.dominante(["santé", "enseignement", "administration"]) == "santé"
    assert eqp.dominante([]) is None
    assert eqp.dominante([None]) is None


def test_categorie_sql_est_le_mirroir_du_python():
    # la liste RETENUE côté SQL couvre exactement les sous-domaines du mirroir Python.
    sql = eqp.categorie_sql("b")
    for sd in ("C1", "C2", "C3", "C4", "C5", "C7", "D1", "F1", "F2", "F3", "A1"):
        assert sd in sql
    assert "A104" in sql and "A140" in sql          # le raffinage sécurité


# ── (2) moteur : la règle d'équipement + le drapeau de terrain public ────────
def _rec(**kw):
    base = dict(id="97400000AA0001", area_m2=5000.0, perimeter_m=300.0,
                capacity_rebuild_m2=4000.0, existing_m2=500.0, residual_m2=3500.0,
                slope_deg=5.0, access="POSITIVE", eligibility="allowed", horizon="now",
                height_status="present", signal_status="AVAILABLE", signal_p=0.3, signal_niveau="moyen")
    base.update(kw)
    return v2.ScenarioRecord(**base)


@pytest.mark.parametrize("scenario", ["keep", "rebuild"])
def test_equipement_public_hors_projet_les_deux_scenarios(scenario):
    rec = _rec(public_facility="enseignement", public_land=True)
    res = v2.evaluate(rec, {"mode": "potential", "scenario": scenario})
    assert res.status == "OUTSIDE_OBJECTIVE"
    assert res.label == "Hors de ce projet"
    assert res.cause_codes == ["EQUIPEMENT_PUBLIC:enseignement"]
    assert res.band is None
    assert res.details.get("equipement_public") == "enseignement"
    assert res.details.get("foncier_public") is True


def test_terrain_public_sans_equipement_garde_la_bande():
    rec = _rec(public_land=True)       # propriétaire public, aucun équipement
    res = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
    assert res.status == "ESTIMATED"               # la bande est GARDÉE
    assert res.band in ("A", "B", "C", "D")
    assert res.details.get("foncier_public") is True
    assert res.details.get("equipement_public") is None


def test_parcelle_privee_avec_commerce_inchangee():
    # un commerce (BPE exclu) n'est pas un équipement public : public_facility reste None.
    rec = _rec(public_land=False, public_facility=None)
    res = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
    assert res.status == "ESTIMATED"
    assert res.details.get("foncier_public") is False
    assert res.details.get("equipement_public") is None


def test_signal_jamais_touche_par_equipement_public():
    # en PROSPECTION (vente), un équipement public NE change PAS l'état de Signal (D6).
    rec = _rec(public_facility="santé", public_land=True)
    res = v2.evaluate(rec, {"mode": "sale", "scenario": "keep"})
    assert res.status == "SIGNAL_AVAILABLE"
    assert res.signal["p"] == 0.3
    # le drapeau reste informatif, même en vente.
    assert res.details.get("foncier_public") is True


# ── (3) base réelle : les trois cas du mandat + la case « Inclure le foncier public » ───────────
REEL = os.environ.get("LABUSE_REEL_DATABASE_URL")
# `local` (exclu de la famille unitaire du hook) + skip si la base réelle n'est pas fournie.
_reel = pytest.mark.local
_skip = pytest.mark.skipif(not REEL, reason="LABUSE_REEL_DATABASE_URL non défini")


@pytest.fixture()
def sess():
    from sqlalchemy.orm import Session
    from labuse.db import make_engine
    eng = make_engine(REEL)
    s = Session(eng)
    try:
        yield s
    finally:
        s.close()


#: toutes les cohortes cochées — le test veut VOIR la parcelle quel que soit son statut/bande.
_TOUT_BANDS = ["A", "B", "C", "D"]
_TOUT_STATUTS = ["OUTSIDE_OBJECTIVE", "TO_VERIFY", "DEFERRED", "NO_MARGIN", "COMPUTE_PENDING", "PRESTUDY"]


def _une(sess, idu, scenario="keep"):
    from labuse.scoring import scenarios_v2_persist as persist
    sel = "SELECT p.idu FROM parcels p WHERE p.idu = :fp"
    pay = persist.analyse_payload_filtre(
        sess, scn_run="q_v20", mode="potential", scenario=scenario, sort=None,
        sel_sql=sel, sel_params={"fp": idu}, bands=_TOUT_BANDS, statuts=_TOUT_STATUTS,
        inclure_foncier_public=True, limit=5)
    return pay["parcelles"][0] if pay["parcelles"] else None


@_reel
@_skip
@pytest.mark.parametrize("scenario", ["keep", "rebuild"])
def test_reel_DO0049_equipement_public_hors_projet(sess, scenario):
    p = _une(sess, "97411000DO0049", scenario)
    assert p is not None
    assert p["statut"] == "OUTSIDE_OBJECTIVE"
    assert p["equipement_public"] == "enseignement"
    assert p["cause"] == ["EQUIPEMENT_PUBLIC:enseignement"]
    assert p["foncier_public"] is True


@_reel
@_skip
def test_reel_communale_nue_zone_u_garde_bande_et_drapeau(sess):
    p = _une(sess, "97412000BM1251")
    assert p is not None
    assert p["statut"] == "ESTIMATED" and p["bande"] in ("A", "B", "C", "D")
    assert p["foncier_public"] is True
    assert p["equipement_public"] is None


@_reel
@_skip
def test_reel_privee_commerce_inchangee(sess):
    p = _une(sess, "97412000CI0056")
    assert p is not None
    assert p["foncier_public"] is False
    assert p["equipement_public"] is None


@_reel
@_skip
def test_reel_case_inclure_foncier_public_filtre_la_selection(sess):
    from labuse.scoring import scenarios_v2_persist as persist
    sel = ("SELECT p.idu FROM parcels p JOIN parcel_scenario_v2_runs z "
           "ON z.parcel_id = p.id AND z.run_label = 'q_v20' AND z.scenario = 'keep' "
           "WHERE p.commune = 'Saint-Denis'")
    kw = dict(scn_run="q_v20", mode="potential", scenario="keep", sel_sql=sel, sel_params={})
    eff_off = persist.effectifs_filtre(sess, **kw, inclure_foncier_public=False)
    eff_on = persist.effectifs_filtre(sess, **kw, inclure_foncier_public=True)
    # la case cochée fait ENTRER exactement le foncier public sans équipement.
    assert eff_on["n_selection"] == eff_off["n_selection"] + eff_off["n_foncier_public"]
    # le compte du drapeau ne dépend PAS de la case.
    assert eff_on["n_foncier_public"] == eff_off["n_foncier_public"] > 0
