"""O7 — CARNET DE SECTEUR : page de suivi par secteur (préfixe IDU 10), lecture sourcée.

Requêtes optionnelles guardées (une table absente → bloc null, jamais un crash). Abonnement = post-M7.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import carnet as k


_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def test_secteur_mauvaise_longueur_422():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        k.carnet("97401", db=None)          # 5 car → 422 avant tout accès DB
    assert e.value.status_code == 422


def test_post_m7_documente():
    assert "post-M7" in k.POST_M7 and "watch_zones" in k.POST_M7


def test_signal_labels():
    assert k._SIGNAL_LABELS["piscine_detectee"].startswith("Piscine")


@pytest.mark.db
def test_carnet_secteur_stock_et_robustesse(db_session):
    s = db_session
    idu = "97499000ZK0001"          # secteur 97499000ZK
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'Ville-Test','ZK','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 900, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES ('q_v7_defisc', :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, 'chaude', 'test')"), {"i": idu})

    out = k.carnet("97499000ZK", s)
    assert out["secteur"] == "97499000ZK" and out["section"] == "ZK" and out["insee"] == "97499"
    assert out["stock"]["opportunites"] == 1 and out["stock"]["par_tier"].get("chaude") == 1
    assert "post-M7" in out["note"]     # abonnement documenté


@pytest.mark.db
def test_liste_secteurs_triee(db_session):
    s = db_session
    for i, tier in enumerate(["chaude", "brulante"]):
        idu = f"97499000ZL000{i+1}"
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
            "(:i,'Ville-Test','ZL',:n, ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 900, "
            " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "n": str(i+1), "w": _WKT})
        s.execute(text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
            "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
            "VALUES ('q_v7_defisc', :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
            {"i": idu, "t": tier})
    out = k.liste_secteurs(s, commune="Ville-Test", limit=30)
    sect = next(r for r in out["secteurs"] if r["secteur"] == "97499000ZL")
    assert sect["opportunites"] == 2 and sect["brulantes"] == 1
