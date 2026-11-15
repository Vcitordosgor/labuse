"""MOTEUR-VERITE-FIX-5 — la règle de NON-HAUSSE et les lectures, cas du relecteur en tests.

Le chiffre servi ne dépasse JAMAIS celui de main (référence : origin/main 049dbcf7f rejoué,
cache-main5), sauf cas approuvés. Base applicative réelle requise (marqueur `reel`).
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
    assert res is not None
    return (res[1].fourchette or {}).get("surface_plancher_m2"), res[1]


# LOT 1 — hausses APPROUVÉES (le chiffre tient) : (idu, plafond admis)
HAUSSES_APPROUVEES = [
    ("97421000AV1267", 752),     # Salazie UA, un seul front établi
    ("97408000AC3589", 207),     # La Possession UBc, H/2 égout hors AU
    ("97408000AP0762", 1089),    # La Possession UAm, H/2 égout hors AU
    ("97418000AS1397", 1352),    # Sainte-Marie UAz, façade du projet sous plafonds
    ("97418000AV2758", 578),     # Sainte-Marie UA
    ("97402000AH1916", 184),     # Bras-Panon Ub
    ("97406000AE0249", 177),     # La Plaine Ub, un seul côté partagé
]


@pytest.mark.parametrize("idu,plafond", HAUSSES_APPROUVEES)
def test_lot1_hausse_approuvee(app_session, idu, plafond):
    sdp, f = _sdp(app_session, idu)
    if sdp is None:
        assert "capacité à vérifier" in f.verdict
        return
    assert sdp <= plafond + 0.5, f"{idu} : {sdp} m² > {plafond} m²"


# LOT 1 — JAMAIS de hausse : le chiffre servi est ≤ main (cache-main5), ou « à vérifier ».
#   (idu, chiffre de main)
NON_HAUSSES = [
    ("97421000AV1339", 1044),    # Salazie : deux emprises sur voie (terrain entier)
    ("97421000AH0074", 301),     # Salazie : 51 % de rouge
    ("97407000AO1877", 204),     # Le Port Uc : RHI (délib. 2025-149, lot 220) non traitée
    ("97408000AS0606", 74),      # La Possession AUB : zone AU
    ("97408000AC3540", 85),      # 0 m de façade qualifiée → à vérifier
    ("97402000AD0323", 452),     # Bras-Panon 1AUc : AU + 40 % rouge → à vérifier/≤ main
    ("97419000AK0024", 5894),    # Sainte-Rose 1AUa : jamais de hausse à Sainte-Rose
    ("97419000AS0724", 201),     # Sainte-Rose 1AUc
]


@pytest.mark.parametrize("idu,main_sdp", NON_HAUSSES)
def test_lot1_jamais_de_hausse(app_session, idu, main_sdp):
    sdp, f = _sdp(app_session, idu)
    if sdp is None:
        assert "capacité à vérifier" in f.verdict   # l'inconnu n'est jamais une hausse
        return
    assert sdp <= main_sdp + 0.5, f"{idu} : {sdp} m² > main {main_sdp} m² (règle de non-hausse)"


# LOT 2 — zone rouge partielle : les 200 m² et l'accès se vérifient sur le morceau
# HORS ROUGE ∩ U/AU (les quatre cas du relecteur ne passent plus).
CAS_ROUGE_UAU = ["97405000AW1235", "97410000BM0158", "97413000DB0325", "97409000BO0383"]


@pytest.mark.parametrize("idu", CAS_ROUGE_UAU)
def test_lot2_rouge_et_plu_meme_morceau(app_session, idu):
    from labuse.faisabilite.db import _hors_rouge_fragment_servable
    pid = app_session.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"{idu} absente")
    servable, motif = _hors_rouge_fragment_servable(app_session, pid)
    assert servable is False, f"{idu} : hors-rouge ∩ U/AU < 200 m², ne doit pas passer"
    assert motif == "hors_rouge_trop_petit"


def test_lot2_micro_parcelle_au_repli(app_session):
    """La garde des 40 m² s'applique AUSSI au calcul de repli (AB1185 12 m², AE0736 37 m²)."""
    for idu in ("97410000AB1185", "97410000AE0736"):
        sdp, f = _sdp(app_session, idu)
        assert sdp is None, f"{idu} : {sdp} m² chiffrés sur une micro-parcelle (repli)"
        assert "capacité à vérifier" in f.verdict


def test_lot2_gabarit_lit_cascade_rejouee(app_session):
    """AH0074/BC1134 : le gabarit affiche le verdict de la cascade REJOUÉE (« capacité
    réduite, sous prescriptions »), plus le classement épinglé (« Exclue »)."""
    from labuse.gabarit.builder import build_gabarit_input
    for idu in ("97421000AH0074", "97420000BC1134"):
        gb = build_gabarit_input(app_session, idu)
        if gb is None:
            pytest.skip(f"{idu} sans gabarit")
        det = str((gb.raccordement.get("ppr") or {}).get("detail") or "")
        assert "Exclue" not in det, f"{idu} : le gabarit lit encore le classement épinglé"
        assert "PRESCRIPTIONS" in det or "prescriptions" in det


# LOT 3 — toute capacité chiffrée porte ses réserves, ÉCRITES par le moteur.
RESERVES = [
    ("97402000AD1041", "conditions d'aménagement"),          # zone AU
    ("97420000BC1134", "prescriptions du plan de prévention"),  # zone bleue PPR
    ("97418000AS1397", "hauteur de façade SUPPOSÉE"),        # scénario par niveau
]


@pytest.mark.parametrize("idu,attendu", RESERVES)
def test_lot3_reserves_ecrites(app_session, idu, attendu):
    sdp, f = _sdp(app_session, idu)
    if sdp is None:
        pytest.skip(f"{idu} : capacité à vérifier (pas de chiffre, pas de réserve attendue)")
    assert any(attendu in a for a in (f.avertissements or [])), \
        f"{idu} : capacité chiffrée ({sdp} m²) sans la réserve « {attendu} »"
