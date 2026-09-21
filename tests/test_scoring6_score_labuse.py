"""SCORING-6 lot B — Score LABUSE V1 (tests PURS, sans base).

Verrouillent le contrat de sortie et les garde-fous du mandat (déterminisme, NC ≠ 0, pénalité
jamais exclusion, monotonicité, versionnement). La reproduction des 30 témoins bout-en-bout
(TEMOINS.csv, base `labuse`) est dans `captures/scoring6/lot_b_temoins.py` et le dry-run (lot G).
"""
import tempfile
from pathlib import Path

import pytest

from labuse.scoring.score_labuse import (ScoreEntrees, bande_de_score,
                                         charger_bareme, score_parcelle)

BAREME, VERSION = charger_bareme()


def _e(**kw) -> ScoreEntrees:
    base = dict(parcel_id=1, idu="x", commune="Saint-Paul", residuel_present=True,
                sdp_residuelle_m2=1000.0, taux_emprise_pct=0.0, cause=None,
                capacite_estimee=False, pente_moy_deg=3.0, aire_m2=1000.0,
                perimetre_m=130.0, faitage_m=None, au_classe=None, acces="POSITIVE")
    base.update(kw)
    return ScoreEntrees(**base)


def _s(**kw):
    return score_parcelle(_e(**kw), BAREME, VERSION, "test")


def test_deterministe():
    e = _e(sdp_residuelle_m2=4953.0, taux_emprise_pct=10.0, faitage_m=10.0,
           aire_m2=1000.0, perimetre_m=400.0)
    a = score_parcelle(e, BAREME, VERSION, "test")
    b = score_parcelle(e, BAREME, VERSION, "test")
    assert a.score == b.score and a.score is not None


def test_golden_lame_batie_donne_64():
    # Reproduit 97411000AB0798 (SCORING-5-RETOUR §3, cas d'école) : capacité pleine (100) mais
    # lame (f_forme 0,8) portant un bâtiment ≥ R+2 (f_bati 0,8) → coef 0,64 → 64.
    r = _s(sdp_residuelle_m2=4953.0, taux_emprise_pct=10.0, faitage_m=10.0,
           aire_m2=1000.0, perimetre_m=400.0)   # w=5 m, allongement 40 → lame
    assert r.details["f_forme"] == 0.8 and r.details["f_bati"] == 0.8
    assert r.details["coef"] == 0.64 and r.score == 64


def test_nc_ne_vaut_jamais_zero():
    r = _s(cause="zone_non_resolue:Uzz")
    assert r.non_calculable and r.score is None and r.bande == "NC"
    assert r.cause == "zone non résolue"
    r2 = _s(residuel_present=False)
    assert r2.non_calculable and r2.score is None and r2.cause == "donnée critique absente"


def test_penalite_jamais_exclusion():
    # Assiette > 0 et zone résolue ⇒ score strictement > 0, même très contraint (plancher 0,4).
    r = _s(sdp_residuelle_m2=36.0, pente_moy_deg=40.0, taux_emprise_pct=60.0, faitage_m=12.0)
    assert not r.non_calculable and r.score is not None and r.score > 0


def test_vrai_zero_n_est_pas_nc():
    # SDP nulle (terrain exigu, cause non-NC) → score 0 CALCULÉ, jamais « non calculable ».
    r = _s(sdp_residuelle_m2=0.0, cause="terrain_exigu", pente_moy_deg=40.0)
    assert not r.non_calculable and r.score == 0


def test_monotonicite_sdp_croissante():
    petit = _s(sdp_residuelle_m2=100.0)
    grand = _s(sdp_residuelle_m2=5000.0)
    assert grand.score >= petit.score


def test_monotonicite_emprise_batie():
    # Emprise bâtie ↑ à capacité égale ⇒ score ≤ (facteur de démolition).
    nu = _s(sdp_residuelle_m2=2000.0, taux_emprise_pct=0.0)
    bati = _s(sdp_residuelle_m2=2000.0, taux_emprise_pct=60.0)
    assert bati.score <= nu.score


def test_absence_donnee_baisse_couverture_pas_le_score():
    plein = _s(pente_moy_deg=3.0, acces="POSITIVE")
    creux = _s(pente_moy_deg=None, acces=None)
    assert creux.couverture["pct"] < plein.couverture["pct"]
    assert "pente" in creux.couverture["manquantes"]
    # pente absente = facteur neutre → le score ne baisse pas du fait de l'absence.
    assert creux.score == plein.score


def test_zone_au_fermee_capacite_differee():
    ouverte = _s(sdp_residuelle_m2=1500.0, au_classe=None)
    fermee = _s(sdp_residuelle_m2=1500.0, au_classe="declasse_au_fermee")
    assert fermee.details["au_mult"] == 0.5 and fermee.score < ouverte.score


def test_versionnement_obligatoire_et_lie_au_hash():
    r = _s()
    assert r.score_version.startswith("labuse_v1+") and len(r.score_version) == len("labuse_v1+") + 8
    # Un barème modifié → une version différente (changer le barème sans bump = impossible).
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "score_labuse.yaml"
        p.write_text("score_labuse:\n  version_base: labuse_v1\n  capacite: {au_dela_points: 42}\n")
        _, v2 = charger_bareme(str(p))
    assert v2 != VERSION


def test_bandes():
    assert bande_de_score(85, BAREME) == "A"
    assert bande_de_score(60, BAREME) == "B"
    assert bande_de_score(40, BAREME) == "C"
    assert bande_de_score(10, BAREME) == "D"
    assert bande_de_score(None, BAREME) == "NC"


def test_contributions_lisibles():
    r = _s(sdp_residuelle_m2=400.0, pente_moy_deg=40.0, taux_emprise_pct=60.0, faitage_m=12.0,
           acces="PASS")
    libs = " ".join(c["libelle"] for c in r.contributions)
    assert "droits à construire" in libs and "pente forte" in libs
    assert "accès à la voie non identifié" in libs and "démolition" in libs
