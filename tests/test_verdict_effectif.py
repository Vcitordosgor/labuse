"""Correctif M5 — verdict d'en-tête effectif (fiche/listes) : le tier v2 pilote
quand un run v2 existe ; l'exclusion dure étage 0 du run SERVI prime toujours ;
le statut matrice legacy reste exposé (historique), jamais verdict principal.

Cas Vic (97410000AS1425) : matrice « écartée » Q 44 + Brûlante v2 rang 16 sur le
même écran → l'en-tête doit suivre le v2 (aucune exclusion dure).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api.app import _q_v2_fiche, _q_v2_list, _score_v2_run_id

pytestmark = pytest.mark.db

RUN = "q_test_verdict"          # run matrice servi
V2RUN = "test-verdict-v2"

_WKT = ("POLYGON((55.45 -20.90, 55.451 -20.90, 55.451 -20.901, "
        "55.45 -20.901, 55.45 -20.90))")


def _parcel(session, idu: str) -> int:
    return session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        "                     centroid, bbox) "
        "VALUES (:i, 'Testville', 'AS', '1', ST_GeomFromText(:w, 4326), "
        "        ST_Transform(ST_GeomFromText(:w, 4326), 2975), 800, "
        "        ST_Centroid(ST_GeomFromText(:w, 4326)), ST_Envelope(ST_GeomFromText(:w, 4326))) "
        "RETURNING id"), {"i": idu, "w": _WKT}).scalar()


def _seed(session):
    # cas 1 : écartée matrice (Q < 50, AUCUNE exclusion dure) mais Brûlante v2 → v2 pilote
    # cas 2 : exclue étage 0 au run servi ET chaude v2 (divergence de runs) → écartée prime
    # cas 3 : écartée matrice, pas de ligne v2 → repli legacy (statut matrice)
    ids = {}
    for idu, cascade, matrice in [("97499000ZZ0001", "a_creuser", "ecartee"),
                                  ("97499000ZZ0002", "exclue", "ecartee"),
                                  ("97499000ZZ0003", "a_creuser", "ecartee")]:
        pid = _parcel(session, idu)
        ids[idu] = pid
        session.execute(text(
            "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
            "opportunity_score, status, q_score, a_score, matrice_statut) "
            "VALUES (:r, :p, 70, 10, :st, 44, 30, :m)"),
            {"r": RUN, "p": pid, "st": cascade, "m": matrice})
    session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles) "
        "VALUES (:r, 'm36-test', 'abc', '{}', 2)"), {"r": V2RUN})
    for idu, tier, rang in [("97499000ZZ0001", "brulante", 16), ("97499000ZZ0002", "chaude", 40)]:
        session.execute(text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
            "rang, contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
            "VALUES (:r, :i, 0.5, 21.99, 99.9, :rg, 0.2, 1.5, '[]', false, :t, 'm36-test')"),
            {"r": V2RUN, "i": idu, "rg": rang, "t": tier})
    session.flush()
    return ids


def test_fiche_expose_score_v2_et_etage0(db_session):
    _seed(db_session)
    f = _q_v2_fiche(db_session, "97499000ZZ0001", run_label=RUN)
    # le statut matrice reste servi (section Qualité, « historique »)…
    assert f["statut"] == "ecartee" and f["etage0"] is False
    # …et le tier v2 pilote l'en-tête côté front (rang + ×N)
    assert f["score_v2"]["tier"] == "brulante"
    assert f["score_v2"]["rang"] == 16 and f["score_v2"]["mult_base"] == 21.99


def test_etage0_du_run_servi_prime(db_session):
    """Divergence de runs (le pipeline v2 peut lire un autre run cascade) : une
    exclusion dure au run SERVI garde l'en-tête « écartée » même si tier v2 chaud."""
    _seed(db_session)
    f = _q_v2_fiche(db_session, "97499000ZZ0002", run_label=RUN)
    assert f["etage0"] is True                    # règle 1 : l'étage 0 prime
    assert f["score_v2"]["tier"] == "chaude"      # exposé, mais pas verdict d'en-tête


def test_repli_legacy_sans_ligne_v2(db_session):
    _seed(db_session)
    f = _q_v2_fiche(db_session, "97499000ZZ0003", run_label=RUN)
    assert f["score_v2"] is None and f["statut"] == "ecartee"


def test_liste_porte_le_verdict_effectif(db_session):
    _seed(db_session)
    assert _score_v2_run_id(db_session) == V2RUN
    items = _q_v2_list(db_session, "Testville", 10, 0, run_label=RUN,
                       extra_where="", extra_params={"f_statuts": ["ecartee"]})
    by_idu = {i["idu"]: i for i in items}
    assert by_idu["97499000ZZ0001"]["tier_v2"] == "brulante"
    assert by_idu["97499000ZZ0001"]["rang_v2"] == 16
    assert by_idu["97499000ZZ0001"]["etage0"] is False
    assert by_idu["97499000ZZ0002"]["etage0"] is True
    assert by_idu["97499000ZZ0003"]["tier_v2"] is None
