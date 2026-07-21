"""O3 — ANTI-FICHE : motifs hiérarchisés (RÉDHIBITOIRE puis VIGILANCE), sourcés, non inventés.

Lit la cascade déjà calculée. Une parcelle sans motif le dit ; jamais d'invention.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import anti_fiche as af


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
        "VALUES ('q_v7_defisc', :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"i": idu, "t": tier})
    for layer, result, detail in cascade:
        s.execute(text(
            "INSERT INTO cascade_results (parcel_id, layer_name, result, detail) VALUES (:p,:l,:r,:d)"),
            {"p": pid, "l": layer, "r": result, "d": detail})
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
