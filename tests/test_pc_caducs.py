"""PHASE A cycle 2, volet 2 (badge) — tests « PC caducs ».

Couvre : (1) wording factuel NON accusatoire + Sourcé/Estimé (fonction pure) ; (2) construction DB
(caduc = octroyé jamais achevé ; réalisé et rejeté exclus) ; (3) idempotence ; (4) fragment de filtre SQL.
Le signal est la parcelle et ses dates — jamais le demandeur, jamais un jugement du propriétaire.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import pc_caducs as pcz


# ───────────────────────── wording (pur) ─────────────────────────

def test_row_wording_non_accusatoire():
    r = pcz._row("97411000AB0001", 2019, 2)
    assert r["caduc_depuis"] == 2022
    assert r["court"] == "PC autorisé 2019 · jamais commencé · caduc probable"
    assert "Sourcé" in r["detail"] and "Estimé" in r["detail"]
    assert "×1,6" in r["detail"]
    # JAMAIS un jugement du propriétaire, jamais une date de vente
    for mot in ("échec", "abandon", "renoncement", "faute", "vendra"):
        assert mot not in r["detail"].lower()


# ───────────────────────── construction DB ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _ensure_sources(s):
    s.execute(text("CREATE TABLE IF NOT EXISTS p_model_permits (permit_id varchar(64), idu text, type varchar(8), date_autorisation date)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS sitadel_permits (id bigserial, permit_id varchar(64), type varchar(8), raw jsonb)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS m10_permit_delais (permit_id varchar(64), date_achevement date)"))


def _seed_parcelle(s, idu):
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 500, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
        {"i": idu, "w": _WKT})


def _seed_pc(s, idu, annee, etat, daact=False):
    pid = f"P-{idu}-{annee}-{etat}"
    s.execute(text("INSERT INTO p_model_permits (permit_id, idu, type, date_autorisation) VALUES (:p,:i,'PC',:d)"),
              {"p": pid, "i": idu, "d": f"{annee}-05-01"})
    s.execute(text("INSERT INTO sitadel_permits (permit_id, type, raw) VALUES (:p,'PC',CAST(:r AS jsonb))"),
              {"p": pid, "r": f'{{"etat":"{etat}"}}'})
    s.execute(text("INSERT INTO m10_permit_delais (permit_id, date_achevement) VALUES (:p,:d)"),
              {"p": pid, "d": (f"{annee+2}-05-01" if daact else None)})


@pytest.mark.db
def test_build_caduc_vs_realise_vs_rejete(db_session):
    s = db_session
    _ensure_sources(s)
    A, B, C = "97499000ZA0001", "97499000ZB0002", "97499000ZC0003"
    _seed_parcelle(s, A); _seed_pc(s, A, 2018, "4")               # octroyé jamais achevé → CADUC
    _seed_parcelle(s, B); _seed_pc(s, B, 2018, "6", daact=True)   # achevé → réalisé (EXCLU)
    _seed_parcelle(s, C); _seed_pc(s, C, 2018, "5")               # rejeté (EXCLU)

    pcz.build_pc_caducs(s, ref_year=2026, commit=False)

    rows = {r["idu"]: r for r in s.execute(text(
        "SELECT idu, pc_annee, caduc_depuis, statut_autorisation, statut_caducite, libelle_court "
        "FROM pc_caducs WHERE idu = ANY(:ids)"), {"ids": [A, B, C]}).mappings().all()}
    assert set(rows) == {A}                                        # seul le caduc
    assert rows[A]["pc_annee"] == 2018 and rows[A]["caduc_depuis"] == 2021
    assert rows[A]["statut_autorisation"] == "Sourcé" and rows[A]["statut_caducite"] == "Estimé"
    assert "jamais commencé · caduc probable" in rows[A]["libelle_court"]


@pytest.mark.db
def test_build_idempotent(db_session):
    s = db_session
    _ensure_sources(s)
    A = "97499000ZD0004"
    _seed_parcelle(s, A); _seed_pc(s, A, 2017, "4")
    r1 = pcz.build_pc_caducs(s, ref_year=2026, commit=False)
    r2 = pcz.build_pc_caducs(s, ref_year=2026, commit=False)
    assert r1["total"] == r2["total"]
    assert s.execute(text("SELECT count(*) FROM pc_caducs WHERE idu=:i"), {"i": A}).scalar() == 1


@pytest.mark.db
def test_recent_pc_non_caduc(db_session):
    # PC 2024 : Y+4 non dépassé (ref 2026) → PAS caduc.
    s = db_session
    _ensure_sources(s)
    A = "97499000ZE0005"
    _seed_parcelle(s, A); _seed_pc(s, A, 2024, "4")
    pcz.build_pc_caducs(s, ref_year=2026, commit=False)
    assert s.execute(text("SELECT count(*) FROM pc_caducs WHERE idu=:i"), {"i": A}).scalar() == 0


# ───────────────────────── filtre SQL ─────────────────────────

def test_filtre_pc_caduc_fragment():
    from labuse.api.app import _q_v2_where
    where, _ = _q_v2_where("q_v7_defisc", None, None, None, None, None, False, False, None, pc_caduc=True)
    assert "pc_caducs" in where
    where0, _ = _q_v2_where("q_v7_defisc", None, None, None, None, None, False, False, None)
    assert "pc_caducs" not in where0
