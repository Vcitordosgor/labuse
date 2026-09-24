"""COMMUNE-FIX-1 — gardes de la fiche commune (recette Vic, témoin Saint-Paul).

Chaque test verrouille un correctif pour qu'il ne régresse pas. Les gardes sont surtout de LIGNAGE
(registre + code) donc robustes en base de test vide ; les vérifications de données réelles sont
gardées par l'existence de la table (la vraie valeur a été vérifiée en direct le 24/09/2026) :
A1 — Habitants = population LÉGALE INSEE (Sudocuh pop_mun), pas l'agrégat Filosofi.
A2 — prix demandé médian / écart demandé-acté servis seulement au seuil Radar (30 biens).
B6 — la carte Foncier lit le run résiduel SERVI (vue parcel_residuel), jamais un run codé en dur.
B7 — coordonnées mairie structurellement saines (e-mail ≠ site) — déjà conformes à l'annuaire.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from labuse.api import fiche_commune as fc

_ROOT = Path(__file__).resolve().parents[1]


def _table_existe(db, nom: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:n)"), {"n": nom}).scalar())


# ───────────────────────────── A1 — population légale ─────────────────────────────
def test_a1_registre_habitants_sur_population_legale():
    """Le registre déclare Habitants sur la population municipale légale (Sudocuh pop_mun),
    plus l'agrégat Filosofi."""
    from labuse.registre.donnees import DONNEES
    d = DONNEES["habitants_n"]
    assert "sudocuh" in d.reservoirs
    assert "pop_mun" in (d.table or "")
    assert "filosofi" not in (d.table or "").lower()


def test_a1_population_confine_filosofi_au_niveau_de_vie():
    """population() lit pop_mun légal et ne garde Filosofi que pour le niveau de vie."""
    src = (_ROOT / "src" / "labuse" / "api" / "fiche_commune.py").read_text()
    i = src.index("def population(")
    bloc = src[i:src.index("def _parc_ancien_pct")]
    assert "sudocuh_procedures" in bloc and "pop_mun" in bloc            # habitants = légal
    assert '"habitants": habitants' in bloc                              # servi depuis pop_mun légal
    assert "Filosofi (niveau de vie)" in bloc                            # source confine Filosofi
    # l'agrégat Filosofi ne calcule plus les habitants (plus de Σ ind → hab dans le SELECT)
    assert "round(sum(f.ind)) hab" not in bloc


# ───────────────────────────── A2 — seuil Radar (30) ─────────────────────────────
def test_a2_seuil_radar_30_sur_ecart_demande_acte():
    """Le seuil Radar (30) garde le prix demandé médian et l'écart demandé/acté."""
    from labuse.pige.signaux import SEUIL_REF_TYPE
    assert SEUIL_REF_TYPE == 30
    src = (_ROOT / "src" / "labuse" / "api" / "fiche_commune.py").read_text()
    i = src.index("def marche_annonces(")
    bloc = src[i:i + 2000]
    assert "SEUIL_REF_TYPE" in bloc            # l'écart est gardé par le seuil Radar (30)
    assert "demande_sous_seuil" in bloc


# ───────────────────────────── B6 — run résiduel servi ─────────────────────────────
def test_b6_gisement_lit_la_vue_residuelle_servie():
    """ligne7_gisement lit la VUE `parcel_residuel` (servie), jamais `parcel_residuel_runs` figé."""
    src = (_ROOT / "src" / "labuse" / "faisabilite" / "marche_commune.py").read_text()
    i = src.index("def ligne7_gisement")
    bloc = src[i:i + 900]
    assert "parcel_residuel" in bloc
    assert "FROM parcel_residuel_runs" not in bloc      # pas de lecture d'un run figé


def test_b6_vue_residuelle_suit_le_run_servi(db_session):
    """Donnée réelle si disponible : la vue filtre sur is_served == run du manifeste."""
    if not _table_existe(db_session, "parcel_residuel"):
        return
    viewdef = db_session.execute(text("SELECT pg_get_viewdef('parcel_residuel', true)")).scalar()
    if not viewdef:            # stub non-vue en base de test → le lignage code suffit
        return
    assert "is_served" in viewdef
    if _table_existe(db_session, "residuel_runs"):
        served = db_session.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
        if served is not None:
            manifest = json.loads((_ROOT / "config" / "served_manifest.json").read_text())
            assert int(served) == manifest["residuel_run_seq"]


# ───────────────────────────── B8 — FRR (garde de non-dérive) ─────────────────────────────
def test_b8_frr_classement_seed_verrouille():
    """B8/FRR (arbitrage Vic) — à La Réunion le FRR s'appuie sur la ZSAR (les Hauts, infra-communale) :
    le classement « en partie » PEUT être réel, le libellé est conservé. Cette garde verrouille la
    classification SOURCÉE du seed (ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017) pour qu'elle ne dérive
    pas en silence. La vérification LIGNE À LIGNE contre le fichier officiel « La Réunion par communes
    2025 » de l'Observatoire des territoires (arrêté modificatif 14/04/2025) reste à faire à la main :
    le jeu n'est pas exposé par une API — si l'Observatoire diffère, mettre à jour le seed ET cette garde."""
    import csv
    seed = _ROOT / "data" / "fiscal" / "territoire_fiscal.csv"
    rows = {r["commune"]: r["frr_classement"] for r in csv.DictReader(seed.open(encoding="utf-8"), delimiter=";")}
    assert len(rows) == 24
    assert all(v in ("totalite", "partie", "hors") for v in rows.values())
    totalite = {c for c, v in rows.items() if v == "totalite"}
    hors = {c for c, v in rows.items() if v == "hors"}
    assert totalite == {"Cilaos", "Salazie", "La Plaine-des-Palmistes"}   # classées en totalité (ZSAR)
    assert hors == {"Le Port"}                                            # seule commune hors zone
    assert sum(1 for v in rows.values() if v == "partie") == 20


# ───────────────────────────── B7 — coordonnées mairie saines ─────────────────────────────
def test_b7_coordonnees_mairie_structurellement_saines(db_session):
    """Vérifié le 24/09/2026 : les 24 communes = annuaire service-public à l'identique. Cette garde
    attrape une régression d'inversion (e-mail contenant une URL, site contenant un @)."""
    if not _table_existe(db_session, "mairies"):
        return
    for r in db_session.execute(text("SELECT commune, email, site_officiel FROM mairies")).mappings():
        if r["email"]:
            assert "@" in r["email"] and "http" not in r["email"].lower()
        if r["site_officiel"]:
            assert "@" not in r["site_officiel"]
