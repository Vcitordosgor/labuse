"""CHASSE-FIX-1 — verrous des corrections de CHASSE-1 (ECARTS.csv), un test par écart.

Chaque test rejoue la mécanique de l'écart corrigé sur la base de TEST (semis local,
nettoyé en fin de test) : si quelqu'un réintroduit le défaut, le test casse.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(engine):
    import os

    from labuse import config
    from labuse.api.app import app

    os.environ.pop("LABUSE_AUTH_PASSWORD", None)
    os.environ["LABUSE_ENV"] = "local"
    config.get_settings.cache_clear()
    return TestClient(app)


IDU = "97415000ZZ9906"   # parcelle semée par le test (jamais une fixture partagée)

#: petit carré ~30 m × 30 m à Saint-Paul (4326) — suffisant pour la fiche
_GEOM = ("SRID=4326;POLYGON((55.270 -21.010, 55.2703 -21.010, 55.2703 -21.0103, "
         "55.270 -21.0103, 55.270 -21.010))")


@pytest.fixture
def au_fermee_seed(engine):
    """Sème une parcelle + une zone AU fermée + une capacité servie > 0, nettoie après."""
    with engine.begin() as c:
        pid = c.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid) "
            "VALUES (:i, 'Saint-Paul', 'ZZ', '9906', ST_GeomFromEWKT(:g), 900, "
            "        ST_Centroid(ST_GeomFromEWKT(:g))) "
            "ON CONFLICT (idu) DO UPDATE SET commune = EXCLUDED.commune RETURNING id"),
            {"i": IDU, "g": _GEOM}).scalar()
        c.execute(text(
            "INSERT INTO parcel_au_statut (parcel_id, idu, classe, zone_lib, motif, computed_at) "
            "VALUES (:p, :i, 'declasse_au_fermee', 'AUtest', 'zone fermée (test)', now())"),
            {"p": pid, "i": IDU})
        served = c.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
        c.execute(text(
            "INSERT INTO parcel_residuel_runs (run_seq, parcel_id, taux_emprise_pct, pct_potentiel, "
            " sous_densite, sdp_residuelle_m2, computed_at) "
            "VALUES (:r, :p, 10, 20, true, 1234, now()) "
            "ON CONFLICT (run_seq, parcel_id) DO UPDATE SET sdp_residuelle_m2 = 1234, cause = NULL"),
            {"r": served, "p": pid})
        # zone PLU réelle de Saint-Paul (AU1b) → la Faisabilité résout la zone (pas de None)
        c.execute(text(
            "INSERT INTO parcel_zone_plu (idu, zone_lib, zone_fam, zone_libelle, zone_filtre) "
            "VALUES (:i, 'AU1b', 'AU', 'à urbaniser (test)', 'AU') "
            "ON CONFLICT (idu) DO UPDATE SET zone_lib = 'AU1b', zone_fam = 'AU'"),
            {"i": IDU})
        # la tête de fiche exige une évaluation du run courant (JOIN dryrun_parcel_evaluations)
        from labuse import runs as _runs
        c.execute(text(
            "INSERT INTO dryrun_parcel_evaluations (run_label, parcel_id, completeness_score, "
            " opportunity_score, opportunity_base, status, created_at) "
            "VALUES (:rl, :p, 50, 0, 0, 'ok', now())"),
            {"rl": _runs.current(), "p": pid})
    yield pid
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcel_au_statut WHERE parcel_id = :p"), {"p": pid})
        c.execute(text("DELETE FROM parcel_residuel_runs WHERE parcel_id = :p"), {"p": pid})
        c.execute(text("DELETE FROM dryrun_parcel_evaluations WHERE parcel_id = :p"), {"p": pid})
        c.execute(text("DELETE FROM parcel_zone_plu WHERE idu = :i"), {"i": IDU})
        c.execute(text("DELETE FROM parcels WHERE id = :p"), {"p": pid})


# ───────────────────────── C06 — AU fermée : capacité DIFFÉRÉE, jamais « disponible »

def test_c06_regle_unique_libelle():
    from labuse.faisabilite.au_differe import AU_CLASSES_DIFFEREES, libelle_differe
    assert "declasse_au_fermee" in AU_CLASSES_DIFFEREES
    assert "conditionnelle_operation" not in AU_CLASSES_DIFFEREES   # condition ≠ différé
    lib = libelle_differe(2852)
    assert "différé" in lib and "ouverture" in lib and "2 852" in lib and "après ouverture" in lib
    assert libelle_differe(None) == "Potentiel différé — ouverture de la zone requise"


def test_c06_fiche_potentiel_differe(client, au_fermee_seed):
    d = client.get(f"/parcels/{IDU}").json()
    pot = d.get("potentiel_transformation") or {}
    assert pot.get("capacite_differee") is True
    assert pot.get("niveau") == "differe"
    assert "Fort potentiel" not in (pot.get("libelle") or "")
    assert "après ouverture" in (pot.get("libelle") or "")
    # la SDP n'est PAS retirée (doctrine « différée, pas exclue ») : la valeur reste servie
    assert pot.get("sdp_residuelle_m2") == 1234


def test_c06_faisabilite_differe(client, au_fermee_seed):
    d = client.post(f"/modules/faisabilite/{IDU}/scenario", json={}).json()
    pan = d.get("scenario") or {}
    assert pan.get("capacite_differee") is True
    assert any("différé" in a for a in (pan.get("avertissements") or []))


def test_c06_gabarit_differe(client, au_fermee_seed):
    d = client.get(f"/outils/gabarit/{IDU}").json()
    au = (d.get("raccordement") or {}).get("au_differe")
    assert au is not None and "différé" in au["libelle"]


# ───────────────────────── Lot 3 — parcel_residuel est une VUE en base de test (comme en prod)

def test_lot3_parcel_residuel_est_une_vue(engine):
    with engine.connect() as c:
        relkind = c.execute(text(
            "SELECT relkind FROM pg_class WHERE relname = 'parcel_residuel'")).scalar()
    assert relkind == "v", "parcel_residuel doit être la VUE M135 (comme en prod), pas une table"


# ───────────────────────── C01 — « Autour, à moins de 100 m » : des MUTATIONS, pas des lignes

@pytest.fixture
def dvf_eclatee_seed(engine):
    """Deux parcelles voisines ; une mutation d'immeuble ÉCLATÉE en 60 lignes sur la seconde."""
    g1 = ("SRID=4326;POLYGON((55.280 -21.020, 55.2803 -21.020, 55.2803 -21.0203, "
          "55.280 -21.0203, 55.280 -21.020))")
    g2 = ("SRID=4326;POLYGON((55.2804 -21.020, 55.2807 -21.020, 55.2807 -21.0203, "
          "55.2804 -21.0203, 55.2804 -21.020))")
    i1, i2 = "97415000ZZ9907", "97415000ZZ9908"
    with engine.begin() as c:
        # aligne le schéma de test sur la prod (geom_2975 ajouté par migration en prod)
        c.execute(text("ALTER TABLE sitadel_permits ADD COLUMN IF NOT EXISTS "
                       "geom_2975 geometry(Geometry, 2975)"))
        pids = []
        for idu, g in ((i1, g1), (i2, g2)):
            pids.append(c.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid) "
                "VALUES (:i, 'Saint-Paul', 'ZZ', :num, ST_GeomFromEWKT(:g), "
                "        ST_Transform(ST_GeomFromEWKT(:g), 2975), 900, "
                "        ST_Centroid(ST_GeomFromEWKT(:g))) "
                "ON CONFLICT (idu) DO UPDATE SET commune = EXCLUDED.commune RETURNING id"),
                {"i": idu, "g": g, "num": idu[-4:]}).scalar())
        for _ in range(60):   # la vente d'immeuble : 60 lignes identiques (lots × nature_culture)
            c.execute(text(
                "INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, nature_mutation, "
                " valeur_fonciere, id_parcelle, type_local, surface_reelle_bati, surface_terrain, millesime) "
                "VALUES ('TESTC01-1', current_date - 30, 'Vente', 10000000, :i, 'Dépendance', 25, 500, 2026)"),
                {"i": i2})
        c.execute(text(
            "INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, nature_mutation, "
            " valeur_fonciere, id_parcelle, type_local, surface_reelle_bati, surface_terrain, millesime) "
            "VALUES ('TESTC01-2', current_date - 60, 'Vente', 200000, :i, 'Maison', 90, 500, 2026)"),
            {"i": i2})
    yield i1, i2
    with engine.begin() as c:
        c.execute(text("DELETE FROM dvf_mutations_parcelle WHERE id_mutation LIKE 'TESTC01-%'"))
        c.execute(text("DELETE FROM parcels WHERE idu IN (:a, :b)"), {"a": i1, "b": i2})


def test_c01_voisinage_compte_des_mutations(engine, dvf_eclatee_seed):
    i1, _ = dvf_eclatee_seed
    from labuse.api.site_voisinage import voisinage_proche
    from labuse.db import session_factory
    db = session_factory()()
    try:
        v = voisinage_proche(db, i1)
    finally:
        db.close()
    assert v is not None
    # 61 lignes DVF mais DEUX mutations : le compteur dit 2, jamais 61
    assert v["ventes_dvf"] == 2, v


# ───────────────────────── C02 — prix/m² de la dernière mutation = totaux de la MUTATION

def test_c02_vue_prix_m2_sur_totaux_mutation(engine, dvf_eclatee_seed):
    from labuse.ingestion.dvf_marche import ensure_dvf_views
    ensure_dvf_views(engine)
    _, i2 = dvf_eclatee_seed
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, nature_mutation, "
            " valeur_fonciere, id_parcelle, type_local, surface_reelle_bati, surface_terrain, millesime) "
            "SELECT 'TESTC01-3', current_date - 10, 'Vente', 400000, idu, 'Maison', 80, 100, 2026 "
            "FROM (VALUES ('97415000ZZ9907'), ('97415000ZZ9907')) v(idu)"))   # ligne dupliquée ×2
        c.execute(text(
            "INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, nature_mutation, "
            " valeur_fonciere, id_parcelle, type_local, surface_reelle_bati, surface_terrain, millesime) "
            "VALUES ('TESTC01-3', current_date - 10, 'Vente', 400000, '97415000ZZ9908', NULL, NULL, 300, 2026)"))
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT valeur, prix_m2_bati, prix_m2_terrain, multi_parcelles, n_parcelles "
            "FROM v_parcel_dvf_last WHERE idu = '97415000ZZ9907'")).mappings().first()
    assert row is not None
    assert row["multi_parcelles"] is True and row["n_parcelles"] == 2
    # bâti : lignes dupliquées DÉDUPLIQUÉES (80, pas 160) → 400000/80 = 5000
    assert row["prix_m2_bati"] == 5000, dict(row)
    # terrain : somme des parcelles de la mutation (100 + 300) → 400000/400 = 1000
    assert row["prix_m2_terrain"] == 1000, dict(row)
