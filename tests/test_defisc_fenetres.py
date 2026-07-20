"""PHASE A-1 étape 2, volet 2 — tests du badge « fenêtre de sortie de défiscalisation ».

Couvre : (1) wording factuel + bornes + drapeau actif (fonction pure `_row`) ; (2) construction DB
réelle restreinte MONO (copro exclue, non-neuf exclu) ; (3) idempotence ; (4) le fragment de filtre SQL.
Aucune date de vente promise, aucune personne physique — le badge est un timing par parcelle.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import defisc_fenetres as dfz


# ───────────────────────── wording + bornes + actif (pur) ─────────────────────────

def test_row_vefa_wording_et_bornes():
    r = dfz._row("97411000AB0001", 2016, "vefa", None, ref_year=2026)
    assert r["deb"] == 2022 and r["fin"] == 2027          # bande [Y+6, Y+11]
    assert r["active"] is True                            # [2022,2027] ∩ [2026,2028] ≠ ∅
    assert r["src"] == "DVF VEFA 2016"
    assert r["badge"] == "achat neuf 2016 — DVF · fenêtre de sortie d'engagement 2022-2027 · Estimé"
    # chip court servi + survol
    assert r["court"] == "Sortie de défisc. probable · 2022-2027 · Estimé"
    assert "×2,4" in r["detail"] and "walk-forward" in r["detail"]
    assert "PAS une prédiction" in r["detail"]
    # JAMAIS une date de vente promise, JAMAIS le dispositif affirmé
    for txt in (r["badge"], r["court"], r["detail"]):
        assert "vendra" not in txt.lower()
    for dispositif in ("Pinel", "Girardin", "Scellier", "Duflot"):
        assert dispositif not in r["detail"]


def test_row_permis_source_trace_achevement():
    r = dfz._row("97411000AB0002", 2017, "permis_achevement", 2015, ref_year=2026)
    assert r["src"] == "DVF vente 2017 + achèvement PC 2015"
    assert r["badge"].startswith("achat neuf 2017 — DVF · fenêtre de sortie d'engagement 2023-2028")


def test_row_active_flag_borne():
    # achat 2011 → bande [2017,2022] : hors [2026,2028] → inactive
    assert dfz._row("x", 2011, "vefa", None, ref_year=2026)["active"] is False
    # achat 2020 → bande [2026,2031] : active
    assert dfz._row("x", 2020, "vefa", None, ref_year=2026)["active"] is True


# ───────────────────────── construction DB : MONO uniquement ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _ensure_sources(s):
    """Tables sources d'ingestion (hors models.py) — CREATE IF NOT EXISTS pour rendre le test
    hermétique quelle que soit la base ; no-op si elles existent déjà (prod). Rollback en fin de test."""
    s.execute(text(
        "CREATE TABLE IF NOT EXISTS p_model_ext_copro "
        "(idu varchar(14) PRIMARY KEY, copro_rnic boolean, copro_dvf boolean)"))
    for tbl in ("dvf_mutations_histo", "dvf_mutations_parcelle"):
        s.execute(text(
            f"CREATE TABLE IF NOT EXISTS {tbl} (id bigserial, id_mutation text, id_parcelle varchar(14), "
            "date_mutation date, nature_mutation text, type_local text, millesime smallint, "
            "source_archive text, millesime_source int)"))
    s.execute(text("CREATE TABLE IF NOT EXISTS p_model_permits (idu text, permit_id varchar(64), type varchar(8))"))
    s.execute(text("CREATE TABLE IF NOT EXISTS m10_permit_delais (permit_id varchar(64), date_achevement date)"))


def _seed_parcelle(s, idu):
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 500, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
        {"i": idu, "w": _WKT})


def _seed_copro(s, idu, copro):
    s.execute(text("INSERT INTO p_model_ext_copro (idu, copro_rnic, copro_dvf) VALUES (:i, false, :d)"),
              {"i": idu, "d": copro})


def _seed_mut(s, idu, annee, nature, tl="Maison"):
    s.execute(text(
        "INSERT INTO dvf_mutations_histo (id_mutation, id_parcelle, date_mutation, nature_mutation, "
        "type_local, millesime, source_archive, millesime_source) "
        "VALUES (:m, :i, :d, :n, :tl, :y, 'test', :y)"),
        {"m": f"MUT-{idu}-{annee}", "i": idu, "d": f"{annee}-06-15", "n": nature, "tl": tl, "y": annee})


@pytest.mark.db
def test_build_mono_uniquement(db_session):
    s = db_session
    _ensure_sources(s)
    A, B, C = "97499000ZA0001", "97499000ZB0002", "97499000ZC0003"
    _seed_parcelle(s, A); _seed_copro(s, A, False)                  # mono, VEFA neuf → RETENU
    _seed_mut(s, A, 2016, dfz.VEFA)
    _seed_parcelle(s, B); _seed_copro(s, B, True)                   # copro, VEFA → EXCLU
    _seed_mut(s, B, 2016, dfz.VEFA, tl="Appartement")
    _seed_parcelle(s, C); _seed_copro(s, C, False)                  # mono mais ancien (pas neuf) → EXCLU
    _seed_mut(s, C, 2015, "Vente")

    res = dfz.build_defisc_fenetres(s, ref_year=2026, commit=False)

    rows = {r["idu"]: r for r in s.execute(text(
        "SELECT idu, achat_neuf_annee, fenetre_debut, fenetre_fin, fenetre_active, statut, libelle_badge "
        "FROM defisc_fenetres WHERE idu = ANY(:ids)"), {"ids": [A, B, C]}).mappings().all()}
    assert set(rows) == {A}                                         # seule la mono neuf
    assert rows[A]["achat_neuf_annee"] == 2016
    assert rows[A]["fenetre_debut"] == 2022 and rows[A]["fenetre_fin"] == 2027
    assert rows[A]["fenetre_active"] is True
    assert rows[A]["statut"] == "Estimé"
    assert "fenêtre de sortie d'engagement 2022-2027" in rows[A]["libelle_badge"]
    # jamais de ligne copro dans la table
    assert res["total"] >= 1


@pytest.mark.db
def test_build_idempotent(db_session):
    s = db_session
    _ensure_sources(s)
    A = "97499000ZD0004"
    _seed_parcelle(s, A); _seed_copro(s, A, False); _seed_mut(s, A, 2018, dfz.VEFA)
    r1 = dfz.build_defisc_fenetres(s, ref_year=2026, commit=False)
    r2 = dfz.build_defisc_fenetres(s, ref_year=2026, commit=False)   # rebuild complet
    assert r1["total"] == r2["total"]                                # pas de doublon
    n = s.execute(text("SELECT count(*) FROM defisc_fenetres WHERE idu = :i"), {"i": A}).scalar()
    assert n == 1


# ───────────────────────── filtre SQL ─────────────────────────

def test_filtre_defisc_active_fragment():
    from labuse.api.app import _q_v2_where
    where, params = _q_v2_where("q_v6_m8", None, None, None, None, None, False, False, None,
                                defisc_active=True)
    assert "defisc_fenetres" in where and "fenetre_active" in where

    where0, _ = _q_v2_where("q_v6_m8", None, None, None, None, None, False, False, None)
    assert "defisc_fenetres" not in where0                           # off par défaut
