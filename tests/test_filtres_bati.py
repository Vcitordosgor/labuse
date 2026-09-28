"""KELFONCIER-FIX-1 (Lot D) — FILTRES BÂTI : hauteur LiDAR (batiment_hauteur_lidar, faîtage) et
emprise bâtie en % (parcel_residuel.taux_emprise_pct du run servi, la MÊME colonne qu'« État du sol »).

Deux verrous :
  1. WHERE-construction — les bons EXISTS + paramètres pour hauteur_min/max et emprise_min/max ;
  2. témoin end-to-end sur la HAUTEUR (table seedable) via l'endpoint /filtre : réglé DANS la
     fourchette → la parcelle ressort ; réglé à côté → elle disparaît.
L'emprise lit parcel_residuel (VUE du run servi, non seedable à l'unité) — couverte par le WHERE.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

_WKT = "POLYGON((55.31 -21.0,55.3103 -21.0,55.3103 -20.9997,55.31 -20.9997,55.31 -21.0))"


def test_where_bati_construit_hauteur_emprise():
    from labuse.api.app import _q_v2_where
    w, p = _q_v2_where("q_v11_m137", None, None, None, False, None,
                       hauteur_min=3.0, hauteur_max=10.0, emprise_min=5, emprise_max=80)
    assert "batiment_hauteur_lidar" in w
    assert "faitage_m >= :f_hmin" in w and "faitage_m <= :f_hmax" in w
    assert p["f_hmin"] == 3.0 and p["f_hmax"] == 10.0
    assert "taux_emprise_pct,0) >= :f_empmin" in w and "taux_emprise_pct,0) <= :f_empmax" in w
    assert p["f_empmin"] == 5 and p["f_empmax"] == 80


@pytest.mark.db
def test_temoin_hauteur_ressort_et_disparait(db_session):
    from labuse.api.app import FiltreCriteres, filtre
    idu = "97499000BH0001"
    pid = db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'BatiVille','S','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 900,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()
    # le compteur /filtre lit dryrun_parcel_evaluations (univers du run) puis joint le tier v2
    db_session.execute(text(
        "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, opportunity_score) "
        "VALUES (:r,:p,100,50)"), {"r": Q_A_RUN_LABEL, "p": pid})
    db_session.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:r,:i,0.5,30,90,1,0.2,1.5,'[]',false,'a_creuser','test')"), {"r": Q_A_RUN_LABEL, "i": idu})
    # faîtage LiDAR mesuré = 8,5 m
    db_session.execute(text(
        "INSERT INTO batiment_hauteur_lidar (idu, faitage_m, egout_m) VALUES (:i, 8.5, 5.0)"), {"i": idu})

    def compte(**kw) -> int:
        c = FiltreCriteres(source=Q_A_RUN_LABEL, communes="BatiVille", **kw)
        r = filtre(c=c, limit=0, offset=0, sort=None, idus=0, groupes=0,
                   segment=None, signal=None, bande=None, db=db_session)
        return r["compte"]

    assert compte() == 1                                   # la parcelle témoin, sans filtre bâti
    assert compte(hauteur_min=3.0, hauteur_max=10.0) == 1  # 8,5 m ∈ [3;10] → ressort
    assert compte(hauteur_max=6.0) == 0                    # 8,5 m > 6 → disparaît
    assert compte(hauteur_min=12.0) == 0                   # 8,5 m < 12 → disparaît
