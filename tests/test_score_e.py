"""NUIT N1 — tests SCORE É (marge estimée €).

Couvre : (1) bornes pures (marge positive, NÉGATIVE affichée telle quelle, non estimable) ; (2) build DB
(non-écartée estimable ; écartée exclue ; secteur sans médiane → non estimable) ; (3) fragment de filtre.
Jamais un prix ni une promesse ; jamais de marge sur une écartée.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import score_e as se


# ───────────────────────── bornes (pur) ─────────────────────────

def test_row_marge_positive():
    r = se._row("idu", 500, 1000, 200, 5000, "secteur")   # prix de sortie neuf élevé → charge > prix
    assert r["estimable"] is True and r["marge"] > 0
    assert r["court"].startswith("Marge estimée : +")
    assert "Estimé" in r["court"] and "Estimé" in r["detail"]
    assert r["niveau"] == "secteur"


def test_row_marge_negative_affichee():
    r = se._row("idu", 500, 1000, 200, 3000, "commune")   # prix modeste → charge < prix → marge négative
    assert r["estimable"] is True and r["marge"] < 0
    assert "−" in r["court"]                                # signe moins explicite (U+2212)
    assert "repli" in r["detail"]                           # niveau commune tracé comme repli


def test_row_non_estimable_sans_donnee():
    for args in ((500, 0, 200, 5000, "secteur"), (500, 1000, None, 5000, "secteur"), (500, 1000, 200, None, None)):
        r = se._row("idu", *args)
        assert r["estimable"] is False and r["marge"] is None
        assert "non estimable" in r["court"].lower()


# ───────────────────────── build DB ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _ensure_sources(s):
    s.execute(text("CREATE TABLE IF NOT EXISTS parcel_residuel (parcel_id int, sdp_residuelle_m2 int)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS dvf_secteur_medianes (secteur varchar(10), type_bien varchar(16), n_ventes int, mediane_prix_m2 int)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS dvf_prix_sortie_neuf (cle varchar(10), niveau text, prix_m2_neuf int, n int)"))


def _seed_score(s, idu, tier):
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES ('q_v7_defisc', :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"i": idu, "t": tier})


def _seed_parcelle(s, idu, surface):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), :su, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT, "su": surface}).scalar()


def _seed_medianes(s, secteur, terrain=200, neuf=5000):
    s.execute(text("INSERT INTO dvf_secteur_medianes (secteur, type_bien, n_ventes, mediane_prix_m2, fenetre) VALUES (:s,'terrain',10,:t,'test')"),
              {"s": secteur, "t": terrain})
    # V2 : prix de sortie NEUF au niveau secteur (repli commune non seedé ici)
    s.execute(text("INSERT INTO dvf_prix_sortie_neuf (cle, niveau, prix_m2_neuf, n) VALUES (:s,'secteur',:a,10)"),
              {"s": secteur, "a": neuf})


@pytest.mark.db
def test_build_ecartee_exclue_et_non_estimable(db_session):
    s = db_session
    _ensure_sources(s)
    A, B, C = "97499000ZA0001", "97499000ZB0002", "97499000ZC0003"
    pa = _seed_parcelle(s, A, 500); _seed_score(s, A, "a_creuser")
    s.execute(text("INSERT INTO parcel_residuel (parcel_id,sdp_residuelle_m2) VALUES (:p, 1000)"), {"p": pa}); _seed_medianes(s, "97499000ZA")
    _seed_parcelle(s, B, 500); _seed_score(s, B, "ecartee")
    pc = _seed_parcelle(s, C, 500); _seed_score(s, C, "a_creuser")
    s.execute(text("INSERT INTO parcel_residuel (parcel_id,sdp_residuelle_m2) VALUES (:p, 1000)"), {"p": pc})   # C : pas de médiane secteur

    se.build_score_e(s, run="q_v7_defisc", commit=False)

    rows = {r["idu"]: r for r in s.execute(text(
        "SELECT idu, estimable, marge_estimee FROM score_e WHERE idu = ANY(:ids)"), {"ids": [A, B, C]}).mappings().all()}
    assert A in rows and rows[A]["estimable"] is True and rows[A]["marge_estimee"] is not None
    assert B not in rows                                       # écartée : jamais de marge
    assert C in rows and rows[C]["estimable"] is False         # sans médiane : non estimable


# ───────────────────────── filtre ─────────────────────────

def test_filtre_marge_min_fragment():
    from labuse.api.app import _q_v2_where
    where, params = _q_v2_where("q_v7_defisc", None, None, None, None, None, False, False, None, marge_min=100000)
    assert "score_e" in where and "marge_estimee >=" in where and params["f_marge"] == 100000
    where0, _ = _q_v2_where("q_v7_defisc", None, None, None, None, None, False, False, None)
    assert "score_e" not in where0
