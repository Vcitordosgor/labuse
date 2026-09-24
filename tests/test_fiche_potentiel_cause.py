"""FICHE-500 — la fiche COMPLÈTE doit répondre 200 pour une parcelle AVEC ligne résiduelle.

Régression `1a39a90b` (FAISABILITE-clip) : le retrait de la garde « dominante A/N → 0 » a
supprimé l'affectation de `_cause_zone` mais laissé `"cause": _cause_zone` dans le payload de
`_potentiel_transformation_block` → NameError → GET /parcels/{idu} = 500 pour TOUTE parcelle
ayant une ligne `parcel_residuel` (constat FICHE-AUDIT-2 §0). Les tests du commit passaient car
aucun n'appelait l'endpoint fiche de bout en bout avec une ligne résiduelle servie — c'est ce
test-ci. Il seede BZ1065 (le témoin de l'audit) + sa ligne résiduelle du run servi et exige un
200 avec le bloc potentiel_transformation servi (cause = None, la cause-garde n'existe plus).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db

IDU = "97411000BZ1065"


@pytest.fixture
def client(engine):
    from labuse import config
    from labuse.api.app import app

    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


@pytest.fixture
def parcelle_avec_residuel(engine):
    """Sème BZ1065 + son évaluation du run servi + une ligne résiduelle SERVIE, puis nettoie.

    En prod `parcel_residuel` est une VUE sur `parcel_residuel_runs` filtrée au run
    `residuel_runs.is_served` ; en base de test c'est (héritage) une TABLE directe. On sert les
    deux formes : table → insertion directe ; vue → ligne `parcel_residuel_runs` au run servi
    (semé run_seq 9999 s'il n'y en a pas), en ne supprimant QUE ce qu'on a inséré."""
    from labuse import runs
    run = runs.current()
    poly = ("POLYGON((55.4495 -20.8905, 55.4505 -20.8905, 55.4505 -20.8895,"
            " 55.4495 -20.8895, 55.4495 -20.8905))")
    with engine.begin() as c:
        est_table = c.execute(text(
            "SELECT table_type = 'BASE TABLE' FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'parcel_residuel'")).scalar()
        c.execute(text("DELETE FROM dryrun_parcel_evaluations d USING parcels p "
                       "WHERE d.parcel_id = p.id AND p.idu = :i"), {"i": IDU})
        if est_table:
            c.execute(text("DELETE FROM parcel_residuel r USING parcels p "
                           "WHERE r.parcel_id = p.id AND p.idu = :i"), {"i": IDU})
        c.execute(text("DELETE FROM parcel_residuel_runs r USING parcels p "
                       "WHERE r.parcel_id = p.id AND p.idu = :i"), {"i": IDU})
        c.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": IDU})
        c.execute(text(
            f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
                VALUES (:i, 'Saint-Denis', 'BZ', '1065', 1625,
                        ST_GeomFromText('{poly}', 4326),
                        ST_Transform(ST_GeomFromText('{poly}', 4326), 2975))"""), {"i": IDU})
        c.execute(text(
            "INSERT INTO dryrun_parcel_evaluations "
            "(run_label, parcel_id, completeness_score, opportunity_score, status, created_at) "
            "SELECT :run, p.id, 50, 10, 'analysee', now() FROM parcels p WHERE p.idu = :i"),
            {"run": run, "i": IDU})
        run_seme = False
        if est_table:
            c.execute(text(
                "INSERT INTO parcel_residuel "
                "(parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2, "
                " capacite_estimee, cause, computed_at) "
                "SELECT p.id, 40, 88, false, 26, false, NULL, now() FROM parcels p WHERE p.idu = :i"),
                {"i": IDU})
        else:
            seq = c.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar()
            run_seme = seq is None
            if run_seme:
                seq = 9999
                c.execute(text(
                    "INSERT INTO residuel_runs (run_seq, label, is_served) "
                    "VALUES (9999, 'test-fiche-500', true)"))
            c.execute(text(
                "INSERT INTO parcel_residuel_runs "
                "(run_seq, parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2, "
                " capacite_estimee, cause, computed_at) "
                "SELECT :seq, p.id, 40, 88, false, 26, false, NULL, now() FROM parcels p WHERE p.idu = :i"),
                {"seq": seq, "i": IDU})
    yield
    with engine.begin() as c:
        if est_table:
            c.execute(text("DELETE FROM parcel_residuel r USING parcels p "
                           "WHERE r.parcel_id = p.id AND p.idu = :i"), {"i": IDU})
        c.execute(text("DELETE FROM parcel_residuel_runs r USING parcels p "
                       "WHERE r.parcel_id = p.id AND p.idu = :i"), {"i": IDU})
        if run_seme:
            c.execute(text("DELETE FROM residuel_runs WHERE run_seq = 9999 AND label = 'test-fiche-500'"))
        c.execute(text("DELETE FROM dryrun_parcel_evaluations d USING parcels p "
                       "WHERE d.parcel_id = p.id AND p.idu = :i"), {"i": IDU})
        c.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": IDU})


def test_fiche_complete_200_avec_ligne_residuelle(client, parcelle_avec_residuel):
    """L'endpoint fiche COMPLET (aucun bloc mocké) répond 200 quand la parcelle a une ligne
    résiduelle servie — le chemin exact qui produisait le NameError `_cause_zone`."""
    r = client.get(f"/parcels/{IDU}")
    assert r.status_code == 200, r.text[:300]
    f = r.json()
    pt = f.get("potentiel_transformation")
    assert pt is not None, "bloc potentiel_transformation absent alors qu'une ligne résiduelle est servie"
    # le bloc est SERVI (pas le repli « indisponible » de _bloc_indisponible)
    assert not pt.get("indisponible"), pt
    assert pt.get("sdp_residuelle_m2") == 26
    # la cause-garde n'existe plus : la clé reste (contrat front) mais vaut None
    assert "cause" in pt and pt["cause"] is None
