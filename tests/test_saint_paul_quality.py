"""QA « gold standard » Saint-Paul — contrôles DATA-QUALITÉ en LECTURE SEULE sur la base applicative.

But : garantir que CHAQUE parcelle Saint-Paul peut produire une fiche propre (géométrie valide,
IDU propre, zonage trouvé, verdict évalué) et qu'aucune « fausse opportunité » évidente ne subsiste.

Particularité : ces tests interrogent la base APPLICATIVE (où vivent les vraies parcelles), pas la
base de test transactionnelle. Ils se connectent à `LABUSE_AUDIT_DATABASE_URL` (défaut : la base
`labuse` locale) et se SKIPENT proprement si les données Saint-Paul sont absentes (CI / base vide).
Aucune écriture — uniquement des SELECT.

Seuils : plancher actuel = 3 000 parcelles (zone urbaine pilote). CIBLE après import cadastre
complet = 51 129 (source : cadastre.data.gouv.fr Etalab, 98 sections). Voir
docs/SAINT_PAUL_QUALITY_AUDIT.md.
"""
from __future__ import annotations

import os
import time

import pytest
from sqlalchemy import create_engine, text

COMMUNE = "Saint-Paul"
MIN_PARCELS = 3000          # plancher actuel ; passera à ~51129 après le LOT 2 (import complet)
APP_URL = os.environ.get("LABUSE_AUDIT_DATABASE_URL") \
    or "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"


@pytest.fixture(scope="module")
def db():
    """Connexion lecture seule à la base applicative ; skip si Saint-Paul absent."""
    try:
        eng = create_engine(APP_URL)
        with eng.connect() as c:
            n = c.execute(text("SELECT count(*) FROM parcels WHERE commune ILIKE :c"),
                          {"c": COMMUNE}).scalar()
    except Exception as exc:  # noqa: BLE001 - base indisponible → skip, jamais d'échec rouge en CI
        pytest.skip(f"base applicative indisponible ({type(exc).__name__}) — QA Saint-Paul ignorée")
    if not n or n < 100:
        pytest.skip(f"données Saint-Paul absentes ({n}) — QA Saint-Paul ignorée")
    yield eng
    eng.dispose()


def _scalar(db, sql: str) -> int:
    with db.connect() as c:
        return c.execute(text(sql), {"c": COMMUNE}).scalar()


# ── Couverture & intégrité parcellaire ──────────────────────────────────────────────────────
def test_nombre_minimal_de_parcelles(db):
    n = _scalar(db, "SELECT count(*) FROM parcels WHERE commune ILIKE :c")
    assert n >= MIN_PARCELS, f"{n} parcelles Saint-Paul (< plancher {MIN_PARCELS})"


def test_aucun_doublon_idu(db):
    with db.connect() as c:
        tot, dist = c.execute(text(
            "SELECT count(*), count(DISTINCT idu) FROM parcels WHERE commune ILIKE :c"),
            {"c": COMMUNE}).one()
    assert tot == dist, f"{tot - dist} doublon(s) d'IDU détecté(s)"


def test_geometries_valides_et_projetees(db):
    with db.connect() as c:
        bad = c.execute(text(
            "SELECT count(*) FROM parcels WHERE commune ILIKE :c AND "
            "(geom IS NULL OR NOT ST_IsValid(geom) OR geom_2975 IS NULL)"),
            {"c": COMMUNE}).scalar()
    assert bad == 0, f"{bad} parcelle(s) à géométrie invalide / non projetée (2975)"


def test_idu_propre(db):
    """IDU 14 caractères, préfixe INSEE 97415."""
    with db.connect() as c:
        bad = c.execute(text(
            "SELECT count(*) FROM parcels WHERE commune ILIKE :c AND "
            "(length(idu) <> 14 OR idu !~ '^97415')"), {"c": COMMUNE}).scalar()
    assert bad == 0, f"{bad} IDU non conforme(s) (longueur 14 / préfixe 97415)"


def test_index_gist_presents(db):
    """Sans les index GIST spatiaux, les requêtes fiche/carte s'effondrent."""
    with db.connect() as c:
        idx = set(r[0] for r in c.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename IN ('parcels','spatial_layers')")).all())
    for needed in ("idx_parcels_geom_2975", "idx_spatial_layers_geom_2975"):
        assert needed in idx, f"index GIST manquant : {needed}"


# ── Aptitude à produire une fiche propre ────────────────────────────────────────────────────
def test_toutes_les_parcelles_sont_evaluees(db):
    """Une parcelle sans évaluation ne produit pas de verdict → fiche incomplète."""
    with db.connect() as c:
        tot, ev = c.execute(text(
            "SELECT count(*), count(e.parcel_id) FROM parcels p "
            "LEFT JOIN LATERAL (SELECT parcel_id FROM parcel_evaluations WHERE parcel_id=p.id LIMIT 1) e ON true "
            "WHERE p.commune ILIKE :c"), {"c": COMMUNE}).one()
    assert ev == tot, f"{tot - ev} parcelle(s) Saint-Paul sans évaluation (verdict absent)"


def test_couverture_zonage_plu(db):
    """Le zonage PLU doit être trouvé pour la quasi-totalité des parcelles (fiche urbanisme)."""
    with db.connect() as c:
        tot = c.execute(text("SELECT count(*) FROM parcels WHERE commune ILIKE :c"), {"c": COMMUNE}).scalar()
        zoned = c.execute(text(
            "SELECT count(*) FROM parcels p WHERE p.commune ILIKE :c AND EXISTS "
            "(SELECT 1 FROM spatial_layers s WHERE s.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975,s.geom_2975))"),
            {"c": COMMUNE}).scalar()
    pct = 100.0 * zoned / tot
    assert pct >= 95.0, f"zonage PLU couvert sur {pct:.1f}% seulement (< 95%)"


def test_echantillon_des_verdicts_presents(db):
    """Le gold standard doit exposer les 3 régimes de verdict (opportunité / à creuser / écartée)."""
    with db.connect() as c:
        statuses = set(r[0] for r in c.execute(text(
            "SELECT DISTINCT e.status FROM parcels p JOIN LATERAL "
            "(SELECT status FROM parcel_evaluations WHERE parcel_id=p.id ORDER BY evaluated_at DESC LIMIT 1) e ON true "
            "WHERE p.commune ILIKE :c"), {"c": COMMUNE}).all())
    for needed in ("opportunite", "a_creuser", "faux_positif_probable"):
        assert needed in statuses, f"aucune parcelle de verdict « {needed} » (échantillon incomplet)"


# ── Anti « fausse opportunité » (efficacité du correctif R1 bâti) ────────────────────────────
def test_aucune_opportunite_majoritairement_batie(db):
    """Une « opportunité » ne doit pas être couverte à > 50% de bâti (sinon R1 a laissé passer un faux positif)."""
    with db.connect() as c:
        n = c.execute(text(
            "WITH opp AS (SELECT p.id, p.geom_2975, ST_Area(p.geom_2975) a FROM parcels p "
            "  JOIN LATERAL (SELECT status FROM parcel_evaluations WHERE parcel_id=p.id ORDER BY evaluated_at DESC LIMIT 1) e ON true "
            "  WHERE p.commune ILIKE :c AND e.status='opportunite') "
            "SELECT count(*) FROM opp WHERE a > 0 AND ("
            "  SELECT COALESCE(SUM(ST_Area(ST_Intersection(opp.geom_2975, b.geom_2975))),0) "
            "  FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(opp.geom_2975,b.geom_2975)"
            ") > 0.5 * opp.a"), {"c": COMMUNE}).scalar()
    assert n == 0, f"{n} « opportunité(s) » bâtie(s) à > 50% — R1 a laissé passer un faux positif"


# ── Performance (la fiche doit rester réactive) ─────────────────────────────────────────────
def test_requete_fiche_sous_budget(db):
    """Requête spatiale représentative d'une fiche (parcelle + zonage) < 1 s."""
    with db.connect() as c:
        idu = c.execute(text(
            "SELECT idu FROM parcels WHERE commune ILIKE :c ORDER BY id LIMIT 1"), {"c": COMMUNE}).scalar()
        t0 = time.perf_counter()
        c.execute(text(
            "SELECT p.idu, string_agg(DISTINCT s.subtype, ', ') FROM parcels p "
            "LEFT JOIN spatial_layers s ON s.kind='plu_gpu_zone' AND ST_Intersects(p.geom_2975,s.geom_2975) "
            "WHERE p.idu=:idu GROUP BY p.idu"), {"idu": idu}).all()
        dt = time.perf_counter() - t0
    assert dt < 1.0, f"requête fiche {dt*1000:.0f} ms (> 1 s — index/tuning à vérifier)"
