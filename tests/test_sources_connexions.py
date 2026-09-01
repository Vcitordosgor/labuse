"""CONNEXIONS-2 Lot 6 — Fraîcheur et sources (KO-11, KO-14, M2).

Tests de non-régression qui auraient attrapé les KO :
  · KO-11 — la ligne de fraîcheur de l'accueil est CALCULÉE (plus un texte figé) : /accueil/fraicheur.
  · KO-14 — un échec d'ingestion devient l'état « en erreur » (job sources_fraicheur + /sources).
  · M2   — désactiver une source depuis le dashboard (flag base) + propagation aux consommateurs.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db

_AFFICHEE = (
    "lower(status) IN ('connecte','manuel') "
    "AND COALESCE(technical_notes,'') NOT LIKE 'DOUBLON%' "
    "AND COALESCE(technical_notes,'') NOT LIKE 'RETIRÉ%' "
    "AND COALESCE(technical_notes,'') NOT LIKE 'DORMANT%' "
    "AND COALESCE(affichage_desactive,false)=false")


@pytest.fixture
def client(engine):
    from labuse import models
    from labuse.api.app import app
    models.ensure_data_sources_millesime(engine)   # garantit les colonnes fraicheur/erreur/desactive
    return TestClient(app, base_url="https://testserver")


def test_accueil_fraicheur_calculee(client, engine):
    """KO-11 — /accueil/fraicheur reflète l'état RÉEL des sources : à jour / en retard / en erreur.
    Échoue sur l'ancien front (chaîne littérale « Toutes les données sont à jour. »)."""
    from labuse.api import accueil
    with engine.begin() as c:
        c.execute(text("UPDATE data_sources SET fraicheur_statut='a_jour'"))
    accueil._fr_cache.update(at=0.0, data=None)
    r = client.get("/accueil/fraicheur").json()
    assert r["ton"] == "ok" and r["phrase"] == "Toutes les données sont à jour."

    with engine.begin() as c:
        sid = c.execute(text(f"SELECT id FROM data_sources WHERE {_AFFICHEE} LIMIT 1")).scalar()
        c.execute(text("UPDATE data_sources SET fraicheur_statut='en_retard' WHERE id=:i"), {"i": sid})
    accueil._fr_cache.update(at=0.0, data=None)
    r = client.get("/accueil/fraicheur").json()
    assert r["ton"] == "warn" and "retard" in r["phrase"] and r["en_retard"] >= 1

    # l'erreur PRIME le retard (une source cassée est plus grave qu'une source ancienne).
    with engine.begin() as c:
        c.execute(text("UPDATE data_sources SET fraicheur_statut='en_erreur' WHERE id=:i"), {"i": sid})
    accueil._fr_cache.update(at=0.0, data=None)
    r = client.get("/accueil/fraicheur").json()
    assert r["ton"] == "error" and "erreur" in r["phrase"]

    with engine.begin() as c:   # remise à plat
        c.execute(text("UPDATE data_sources SET fraicheur_statut='a_jour'"))
    accueil._fr_cache.update(at=0.0, data=None)


def test_job_sources_en_erreur(engine):
    """KO-14 — un run d'ingestion ÉCHOUÉ fait passer la source « en erreur » (distinct de l'ancienneté) ;
    un run redevenu bon efface l'erreur. Échoue sur l'ancien job (age-only, aucun état d'échec)."""
    from labuse.db import session_scope
    from labuse.jobs import JobContext
    from labuse import jobs_impl
    with session_scope() as s:
        sid = s.execute(text(
            "INSERT INTO data_sources (name, status, source_cadence) "
            "VALUES ('TEST Source Erreur', 'connecte', 'mensuelle') RETURNING id")).scalar()
        s.execute(text(
            "INSERT INTO ingestion_runs (data_source_id, started_at, finished_at, status) "
            "VALUES (:i, now() - interval '2 hours', now() - interval '1 hour', 'error')"), {"i": sid})
        s.commit()
        jobs_impl.sources_fraicheur(JobContext(db=s, dry_run=True))
        s.commit()
        row = s.execute(text("SELECT fraicheur_statut, fraicheur_erreur_message, fraicheur_erreur_at "
                             "FROM data_sources WHERE id=:i"), {"i": sid}).mappings().first()
        assert row["fraicheur_statut"] == "en_erreur"
        assert row["fraicheur_erreur_message"] and "error" in row["fraicheur_erreur_message"]
        assert row["fraicheur_erreur_at"] is not None

        # un run OK plus récent : l'erreur est effacée, plus jamais un « en erreur » qui colle.
        s.execute(text("INSERT INTO ingestion_runs (data_source_id, started_at, finished_at, status) "
                       "VALUES (:i, now(), now(), 'ok')"), {"i": sid})
        s.commit()
        jobs_impl.sources_fraicheur(JobContext(db=s, dry_run=True))
        s.commit()
        row = s.execute(text("SELECT fraicheur_statut, fraicheur_erreur_at FROM data_sources WHERE id=:i"),
                        {"i": sid}).mappings().first()
        assert row["fraicheur_statut"] != "en_erreur" and row["fraicheur_erreur_at"] is None

        s.execute(text("DELETE FROM ingestion_runs WHERE data_source_id=:i"), {"i": sid})
        s.execute(text("DELETE FROM data_sources WHERE id=:i"), {"i": sid})
        s.commit()


def test_source_active_helper(engine):
    """M2 (propagation) — `source_active` : False si la source est désactivée, True sinon / si inconnue."""
    from labuse import sources_catalog
    from labuse.db import session_scope
    with session_scope() as s:
        sid = s.execute(text("INSERT INTO data_sources (name, status) "
                             "VALUES ('TEST Ortho Prop', 'connecte') RETURNING id")).scalar()
        s.commit()
        assert sources_catalog.source_active(s, "%TEST Ortho Prop%") is True
        assert sources_catalog.source_active(s, "%source qui n existe pas%") is True   # inconnue : prudence
        s.execute(text("UPDATE data_sources SET affichage_desactive=true WHERE id=:i"), {"i": sid})
        s.commit()
        assert sources_catalog.source_active(s, "%TEST Ortho Prop%") is False
        s.execute(text("DELETE FROM data_sources WHERE id=:i"), {"i": sid})
        s.commit()


def test_admin_desactiver_source_exclut_la_vitrine(client, engine):
    """M2 — désactiver une source au dashboard (flag base) la retire de /sources ; réactiver la rétablit.
    Échoue sur l'ancien code (SOURCES_MASQUEES en dur, aucune action dashboard)."""
    admin = client.get("/admin/sources").json()["sources"]
    assert admin, "pas de source affichée en base de test"
    cible = admin[0]
    sid, name0 = cible["id"], cible["name"]
    assert cible["affichage_desactive"] is False

    r = client.post(f"/admin/sources/{sid}/affichage", json={"actif": False}).json()
    assert r["ok"] and r["affichage_desactive"] is True
    apres = {x["name"] for x in client.get("/sources").json()}
    assert name0 not in apres

    client.post(f"/admin/sources/{sid}/affichage", json={"actif": True})
    encore = {x["name"] for x in client.get("/sources").json()}
    assert name0 in encore


def test_couche_source_desactivee_sert_vide(client, engine):
    """M2 (propagation, couche) — une couche dont la source est désactivée sert un FeatureCollection
    VIDE marqué « source désactivée », jamais des objets d'une source coupée."""
    kind = "parc_national"   # kind carte valide
    with engine.begin() as c:
        sid = c.execute(text("INSERT INTO data_sources (name, status) "
                             "VALUES ('TEST Couche desac', 'connecte') RETURNING id")).scalar()
        c.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, geom, data_source_id) "
            "VALUES (:k, 'test', 'zone test', "
            "  ST_SetSRID(ST_GeomFromText('POLYGON((55 -21,55.01 -21,55.01 -21.01,55 -21.01,55 -21))'), 4326), :i)"),
            {"k": kind, "i": sid})
        c.execute(text("UPDATE data_sources SET affichage_desactive=true WHERE id=:i"), {"i": sid})
    try:
        r = client.get(f"/map/layers.geojson?kind={kind}").json()
        assert r.get("source_desactivee") is True and r["features"] == []
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM spatial_layers WHERE data_source_id=:i"), {"i": sid})
            c.execute(text("DELETE FROM data_sources WHERE id=:i"), {"i": sid})


def test_outil_ortho_source_desactivee(client, engine):
    """M2 (propagation, outil) — /ortho/equipements sert « source désactivée » plutôt qu'un chiffre
    quand la source ortho est coupée au dashboard."""
    idu = "TESTORTHO0001"
    with engine.begin() as c:
        existe = c.execute(text("SELECT idu FROM parcels LIMIT 1")).scalar()
        cree = None
        if not existe:
            c.execute(text(
                "INSERT INTO parcels (idu, commune, geom) VALUES (:idu, 'TEST', "
                "  ST_SetSRID(ST_GeomFromText('POINT(55 -21)'), 4326))"), {"idu": idu})
            cree = idu
        else:
            idu = existe
        sid = c.execute(text("INSERT INTO data_sources (name, status) "
                             "VALUES ('TEST BD ORTHO desac', 'connecte') RETURNING id")).scalar()
        c.execute(text("UPDATE data_sources SET affichage_desactive=true WHERE id=:i"), {"i": sid})
    try:
        r = client.get(f"/ortho/equipements/{idu}").json()
        assert r.get("desactivee") is True and "désactiv" in r["source"].lower()
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM data_sources WHERE id=:i"), {"i": sid})
            if cree:
                c.execute(text("DELETE FROM parcels WHERE idu=:idu"), {"idu": cree})


def test_ortho_millesime_lu_de_la_table(engine):
    """Lot 6.4 — le millésime ortho SERVI est lu dans data_sources.source_millesime (centralisé),
    plus la constante en dur."""
    from labuse.db import session_scope
    from labuse.ingestion import ortho_tiles
    with session_scope() as s:
        # neutralise les autres lignes ortho millésimées le temps du test (déterminisme).
        autres = s.execute(text("SELECT id, source_millesime FROM data_sources "
                                "WHERE name ILIKE '%ortho%' AND source_millesime IS NOT NULL")).all()
        for oid, _ in autres:
            s.execute(text("UPDATE data_sources SET source_millesime=NULL WHERE id=:i"), {"i": oid})
        sid = s.execute(text(
            "INSERT INTO data_sources (name, status, source_millesime) "
            "VALUES ('TEST BD ORTHO millesime', 'connecte', '2099') RETURNING id")).scalar()
        s.commit()
        try:
            assert ortho_tiles.millesime_servi(s) == "2099"
        finally:
            s.execute(text("DELETE FROM data_sources WHERE id=:i"), {"i": sid})
            for oid, mil in autres:
                s.execute(text("UPDATE data_sources SET source_millesime=:m WHERE id=:i"),
                          {"m": mil, "i": oid})
            s.commit()
