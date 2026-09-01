"""CONNEXIONS-3 V1 — le Copilote v1 (missions lourdes RECHERCHE/VERIFICATION, servi via
`CopiloteView` → `/api/copilote/runs`) lit la cascade RUN-SCOPÉE (`dryrun_cascade_results` du run
SERVI, `Q_A_RUN_LABEL`), plus JAMAIS la table LIVE non run-scopée `cascade_results`.

Ces tests échouent sur l'ancien code (qui lisait la LIVE) : un signal du run servi doit être vu,
un LEURRE (dans la table LIVE OU sous l'ancien run `q_v8_calibre`) doit être ignoré — même forme
que `test_served_cascade`. Le tier servi au Copilote est celui de la FICHE (même table + même run).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.copilote import moteurs
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"

# recherche SANS programme → aucun filtre géométrique (le test porte sur la SOURCE de la cascade).
BRIEF = {"communes": ["Saint-Paul"],
         "programme": {"logements": None, "sdp_cible_m2": None},
         "budget_max_eur": None,
         "contraintes": {"exclure_ppr_rouge": True, "exclure_abf": False, "zones": None},
         "surface_min_m2": None}


def _seed_parcelle(s, idu, *, tier="chaude", rang=1, run=Q_A_RUN_LABEL):
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        " centroid, bbox) VALUES (:i, 'Saint-Paul', 'AB', '1', ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) "
        "RETURNING id"), {"i": idu, "w": _WKT}).scalar()
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
        " rang, contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:run, :i, 0.5, 30.0, 90.0, :r, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"run": run, "i": idu, "r": rang, "t": tier})
    s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam) VALUES (:i,'U','U')"),
              {"i": idu})
    return pid


def _seed_dryrun(s, pid, run, layer, result, detail, severity=None):
    s.execute(text(
        "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, severity, detail) "
        "VALUES (:run,:p,:l,:r,:sev,:d)"),
        {"run": run, "p": pid, "l": layer, "r": result, "sev": severity, "d": detail})


def _seed_live(s, pid, layer, result, detail, severity=None):
    s.execute(text(
        "INSERT INTO cascade_results (parcel_id, layer_name, result, severity, detail) "
        "VALUES (:p,:l,:r,:sev,:d)"),
        {"p": pid, "l": layer, "r": result, "sev": severity, "d": detail})


# ── criblage : le signal PPR du run SERVI exclut ; le leurre (LIVE / ancien run) est ignoré ──

def test_criblage_ppr_rouge_du_run_servi_exclut(db_session):
    # Signal PPR UNIQUEMENT dans le run servi → l'ancien code (table LIVE) ne le voyait pas.
    pid = _seed_parcelle(db_session, "97415000V1001", tier="chaude")
    _seed_dryrun(db_session, pid, Q_A_RUN_LABEL, "risques", "HARD_EXCLUDE",
                 "Exclue : PPR zone rouge majoritaire.")
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, BRIEF, dossier)
    assert [c["idu"] for c in dossier.retenus()] == []          # exclue par exclure_ppr_rouge


def test_criblage_ignore_leurre_ppr_live_et_ancien_run(db_session):
    # Aucun signal dans le run servi ; un LEURRE PPR dans la table LIVE ET sous q_v8_calibre.
    # NEW : criblage lit le run servi → aucun signal → parcelle RETENUE (leurre ignoré).
    # OLD : lisait la LIVE → excluait à tort (ce test échoue sur l'ancien code).
    pid = _seed_parcelle(db_session, "97415000V1002", tier="chaude")
    _seed_live(db_session, pid, "risques", "HARD_EXCLUDE", "LEURRE LIVE ppr")
    _seed_dryrun(db_session, pid, "q_v8_calibre", "risques", "HARD_EXCLUDE", "LEURRE ancien run ppr")
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, BRIEF, dossier)
    assert [c["idu"] for c in dossier.retenus()] == ["97415000V1002"]   # leurre ignoré


def test_criblage_tier_est_celui_du_run_servi_pas_du_leurre(db_session):
    # Même tier que la FICHE (parcel_p_score_v2 du run servi) ; un score sous q_v8_calibre
    # avec un AUTRE tier est ignoré.
    _seed_parcelle(db_session, "97415000V1004", tier="brulante", rang=1)
    db_session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
        " rang, contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES ('q_v8_calibre', :i, 0.5, 30.0, 10.0, 99, 0.2, 1.5, '[]', false, 'a_creuser', 'test')"),
        {"i": "97415000V1004"})
    dossier = moteurs.Dossier()
    moteurs.criblage(db_session, BRIEF, dossier)
    assert dossier.candidats[0]["tier"] == "brulante"           # run servi, pas le leurre a_creuser


# ── risques : lit les signaux du run servi, ignore le leurre LIVE ──

def test_risques_lit_run_servi_ignore_live(db_session):
    pid = _seed_parcelle(db_session, "97415000V1003", tier="chaude")
    _seed_dryrun(db_session, pid, Q_A_RUN_LABEL, "pente", "SOFT_FLAG", "Pente forte", "faible")
    _seed_live(db_session, pid, "pente", "SOFT_FLAG", "LEURRE LIVE pente")
    dossier = moteurs.Dossier()
    dossier.candidats = [{"idu": "97415000V1003", "parcel_id": pid, "retenu": True}]
    moteurs.risques(db_session, BRIEF, dossier)
    signaux = dossier.candidats[0]["risques"]
    assert [s["detail"] for s in signaux] == ["Pente forte"]    # run servi seul, pas le leurre


# ── VERIFICATION (scoreur_unitaire) : le tier d'un IDU vérifié = celui du run servi = la fiche ──

def test_verifier_adresse_idu_tier_du_run_servi(db_session):
    _seed_parcelle(db_session, "97415000V1005", tier="chaude", rang=4)
    dossier = moteurs.Dossier()
    brief = {"refs": [{"type": "idu", "valeur": "97415000V1005"}]}
    moteurs.scoreur_unitaire(db_session, brief, dossier)
    v = dossier.verdicts[0]
    assert v["trouvee"] and v["tier"] == "chaude"               # tier = run servi = fiche
