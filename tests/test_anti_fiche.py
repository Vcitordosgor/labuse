"""O3 — ANTI-FICHE : motifs hiérarchisés (RÉDHIBITOIRE puis VIGILANCE), sourcés, non inventés.

CONNEXIONS-2 Lot 1 (KO-2) : la cascade lue est la SERVIE run-scopée (`dryrun_cascade_results`
du run épinglé), plus la table LIVE `cascade_results`. Les seeds passent donc par la table
run-scopée ; un test-témoin prouve qu'une ligne de la table LIVE n'est PLUS surfacée.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import anti_fiche as af
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL  # M31 : seed sous le run SERVI, pas un littéral


_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _seed(s, idu, tier, cascade):
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:run, :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"i": idu, "t": tier, "run": Q_A_RUN_LABEL})
    # KO-2 : on seed la cascade SERVIE run-scopée — la MÊME table que la fiche écran.
    for layer, result, detail in cascade:
        s.execute(text(
            "INSERT INTO dryrun_cascade_results (run_label, parcel_id, layer_name, result, detail) "
            "VALUES (:run,:p,:l,:r,:d)"),
            {"run": Q_A_RUN_LABEL, "p": pid, "l": layer, "r": result, "d": detail})
    return pid


@pytest.mark.db
def test_ecartee_motifs_redhibitoires_puis_vigilance(db_session):
    s = db_session
    idu = "97499000AF0001"
    _seed(s, idu, "ecartee", [
        ("risques", "HARD_EXCLUDE", "Exclue : PPR zone rouge (inconstructible)."),
        ("pente", "HARD_EXCLUDE", "pente 74 % — non aménageable"),
        ("abf", "SOFT_FLAG", "Abords Monument historique — avis ABF probable."),
        ("zonage", "PASS", "Zone U"),   # ne doit PAS apparaître
    ])
    out = af.anti_fiche(idu, s)
    assert out["tier"] == "ecartee" and out["n_redhibitoire"] == 2 and out["n_vigilance"] == 1
    assert "rédhibitoire" in out["synthese"]
    motifs = [m["motif"] for m in out["redhibitoire"]]
    assert any("PPR" in m for m in motifs) and "Zone U" not in str(out)   # PASS exclu


@pytest.mark.db
def test_bien_classee_pas_d_invention(db_session):
    s = db_session
    idu = "97499000AF0002"
    _seed(s, idu, "brulante", [("zonage", "PASS", "Zone U"), ("dvf", "POSITIVE", "marché actif")])
    out = af.anti_fiche(idu, s)
    assert out["n_redhibitoire"] == 0 and out["n_vigilance"] == 0
    assert "Aucun motif" in out["synthese"] and "brulante" == out["tier"]


@pytest.mark.db
def test_dedup_par_couche(db_session):
    s = db_session
    idu = "97499000AF0003"
    _seed(s, idu, "ecartee", [
        ("risques", "HARD_EXCLUDE", "Exclue : PPR zone rouge."),
        ("risques", "SOFT_FLAG", "aléa faible"),   # même couche → une seule entrée (HARD gagne)
    ])
    out = af.anti_fiche(idu, s)
    assert out["n_redhibitoire"] == 1 and out["n_vigilance"] == 0


@pytest.mark.db
def test_ne_lit_plus_la_table_live_cascade_results(db_session):
    """KO-2 : une ligne présente UNIQUEMENT dans la table LIVE non run-scopée `cascade_results`
    ne doit PLUS être surfacée — l'anti-fiche lit exclusivement la cascade servie run-scopée.
    Ce test échoue sur l'ancien code (qui lisait `cascade_results`)."""
    s = db_session
    idu = "97499000AF0004"
    pid = _seed(s, idu, "brulante", [])   # cascade servie VIDE pour cette parcelle
    # décor : un motif rédhibitoire écrit SEULEMENT dans la table LIVE (rail legacy)
    s.execute(text(
        "INSERT INTO cascade_results (parcel_id, layer_name, result, detail) VALUES "
        "(:p,'risques','HARD_EXCLUDE','FANTÔME legacy — ne doit pas apparaître')"), {"p": pid})
    out = af.anti_fiche(idu, s)
    assert out["n_redhibitoire"] == 0 and out["n_vigilance"] == 0
    assert "FANTÔME" not in str(out)
