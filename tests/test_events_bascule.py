"""M137-M — la bascule de TIER V2 (parcel_p_score_v2.tier) déclenche l'alerte.

Casse si la détection retombe sur la matrice morte (matrice_statut/q_score, NULL depuis M129) :
avant le correctif, aucune bascule ▲ n'était émise (le check portait sur `status == 'chaude'`,
valeur que `status` n'a jamais) → la veille « bascule vers chaude » ne partait plus.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import events as ev

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.90, 55.451 -20.90, 55.451 -20.901, 55.45 -20.901, 55.45 -20.90))"


def _parcel(s, idu: str) -> int:
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i, 'Testville', 'AS', '1', ST_GeomFromText(:w, 4326), "
        "        ST_Transform(ST_GeomFromText(:w, 4326), 2975), 800, "
        "        ST_Centroid(ST_GeomFromText(:w, 4326)), ST_Envelope(ST_GeomFromText(:w, 4326))) "
        "RETURNING id"), {"i": idu, "w": _WKT}).scalar()


def _score(s, run: str, idu: str, tier: str) -> None:
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "  contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES (:r, :i, 0.3, 5.0, 90, 10, 0, 0, '[]', false, :t, 'm137-test')"),
        {"r": run, "i": idu, "t": tier})


def test_bascule_tier_declenche_alerte_parcelle_suivie(db_session):
    s = db_session
    idu = "97499000ZZ0001"
    _parcel(s, idu)
    _score(s, "run_from", idu, "a_creuser")   # avant
    _score(s, "run_to", idu, "chaude")        # après : MONTÉE en tier prioritaire
    s.execute(text("INSERT INTO watched_parcels (idu) VALUES (:i)"), {"i": idu})  # parcelle SUIVIE
    s.flush()

    ev.detect_events(s, "run_from", "run_to", demo=False)

    titre = s.execute(text("SELECT titre FROM event_log WHERE kind='bascule' AND idu=:i"),
                      {"i": idu}).scalar()
    assert titre and titre.startswith("▲"), f"attendu une bascule ▲ (montée de tier), obtenu {titre!r}"
    n = s.execute(text("SELECT count(*) FROM event_log WHERE kind='parcelle_suivie' AND idu=:i"),
                  {"i": idu}).scalar()
    assert n >= 1, "une parcelle SUIVIE qui monte de tier doit déclencher une alerte"


def test_veille_saved_search_matche_la_bascule(db_session):
    """Une veille (recherche sauvegardée) filtrée sur le tier 'chaude' matche la bascule ▲ vers chaude."""
    s = db_session
    idu = "97499000ZZ0002"
    _parcel(s, idu)
    _score(s, "run_from", idu, "a_creuser")
    _score(s, "run_to", idu, "chaude")
    # hash front (filtersToHash) : tv=chaude → veille sur le tier 'chaude'
    s.execute(text("INSERT INTO saved_searches (nom, hash, compte_id) VALUES ('Chaudes','#f=1&tv=chaude', NULL)"))
    s.flush()

    ev.detect_events(s, "run_from", "run_to", demo=False)

    n = s.execute(text("SELECT count(*) FROM event_log WHERE kind='veille' AND idu=:i"),
                  {"i": idu}).scalar()
    assert n >= 1, "la veille sur le tier 'chaude' doit matcher la bascule ▲ vers chaude"
