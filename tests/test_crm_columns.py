"""M12 LOT H — CRM personnalisable : colonnes du kanban stockées PAR TENANT.

La boussole (ligne rouge) : on ne perd JAMAIS une carte. Ces tests attaquent H2 (suppression
d'une colonne peuplée) sous tous les angles : déplacement obligatoire, dernière colonne
inamovible, réinitialisation qui remappe. DB réelle (jeu de démo Saint-Paul), bucket pilote
(compte_id NULL, pas d'auth dans ce client).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import text as _t

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def client(engine):
    import os

    from labuse import config, models
    from labuse.ai import StubProvider
    from labuse.api.app import app
    from labuse.api.crm_columns import ensure_tables
    from labuse.cascade import evaluate_parcels
    from labuse.db import session_scope
    from labuse.ingestion import demo_saint_paul, seed_sources

    # Le CRM se teste hors auth (bucket pilote compte_id NULL). Une autre suite peut avoir
    # laissé un mot de passe d'auth actif via la config LRU-cachée → on la neutralise pour
    # ce module afin d'être robuste à l'ordre d'exécution (le 401 sinon = pollution inter-modules).
    os.environ.pop("LABUSE_AUTH_PASSWORD", None)
    os.environ["LABUSE_ENV"] = "local"
    config.get_settings.cache_clear()

    ensure_tables(engine)
    with session_scope() as s:
        seed_sources.seed(s)
        demo_saint_paul.seed_demo(s)
        ids = [r[0] for r in s.execute(select(models.Parcel.id)).all()]
        evaluate_parcels(ids, s, persist=True, ai_provider=StubProvider())
    try:
        yield TestClient(app)
    finally:
        with session_scope() as s:
            demo_saint_paul.reset_demo(s)


@pytest.fixture(autouse=True)
def _clean_columns(engine):
    """Repart d'un kanban vierge (bucket pilote) avant chaque test → semis par défaut reproductible.
    Retire aussi les entrées pipeline du bucket pour ne pas polluer les comptes de cartes."""
    from labuse.db import session_scope
    with session_scope() as s:
        s.execute(_t("DELETE FROM pipeline_entries WHERE compte_id IS NULL"))
        s.execute(_t("DELETE FROM crm_columns WHERE compte_id IS NULL"))
        s.commit()
    yield
    with session_scope() as s:
        s.execute(_t("DELETE FROM pipeline_entries WHERE compte_id IS NULL"))
        s.execute(_t("DELETE FROM crm_columns WHERE compte_id IS NULL"))
        s.commit()


def _labels(cols):
    return [c["label"] for c in cols]


# ─────────────────────────── H1 : colonnes personnalisables ───────────────────────────

def test_h1_seed_defaut_labuse(client):
    """Un tenant sans colonne est semé au kanban LABUSE par défaut (8 étapes, dans l'ordre)."""
    cols = client.get("/pipeline/columns").json()["columns"]
    assert _labels(cols)[:3] == ["Repérée", "Propriétaire à identifier", "Contact à préparer"]
    assert _labels(cols)[-1] == "À abandonner"
    assert all(c["is_default"] for c in cols)
    # /pipeline/meta sert les MÊMES colonnes (source de vérité unique)
    meta = client.get("/pipeline/meta").json()["columns"]
    assert _labels(meta) == _labels(cols)


def test_h1_rename_ne_touche_pas_les_cartes(client):
    """Renommer = changer le libellé ; la key stable ne bouge pas → la carte reste dans la colonne."""
    eid = client.post("/pipeline", json={"idu": "97415000AB0001"}).json()["entry"]["id"]
    cols = client.get("/pipeline/columns").json()["columns"]
    first = cols[0]
    r = client.patch(f"/pipeline/columns/{first['id']}", json={"label": "À prospecter"})
    assert r.status_code == 200
    assert _labels(r.json()["columns"])[0] == "À prospecter"
    # la carte est toujours suivie et visible (status = key inchangée)
    assert any(e["id"] == eid for e in client.get("/pipeline").json())


def test_h1_add_et_reorder(client):
    """Ajout d'une colonne (à la fin) puis réordonnancement complet."""
    r = client.post("/pipeline/columns", json={"label": "Signé"})
    assert r.status_code == 200
    cols = r.json()["columns"]
    assert _labels(cols)[-1] == "Signé"
    ids = [c["id"] for c in cols]
    reversed_ids = list(reversed(ids))
    rr = client.post("/pipeline/columns/reorder", json={"order": reversed_ids})
    assert rr.status_code == 200
    assert [c["id"] for c in rr.json()["columns"]] == reversed_ids
    # reorder partiel/incohérent → 422 (jamais un ordre à trous)
    assert client.post("/pipeline/columns/reorder", json={"order": ids[:2]}).status_code == 422


def test_h1_delete_colonne_vide(client):
    """Supprimer une colonne VIDE ne demande pas de cible."""
    cols = client.get("/pipeline/columns").json()["columns"]
    victim = cols[-1]  # « À abandonner », vide
    r = client.request("DELETE", f"/pipeline/columns/{victim['id']}", json={})
    assert r.status_code == 200 and r.json()["moved"] == 0
    assert victim["id"] not in [c["id"] for c in r.json()["columns"]]


# ─────────────────────────── H2 : on ne perd JAMAIS une carte ───────────────────────────

def test_h2_delete_colonne_peuplee_exige_move_to(client):
    """Supprimer une colonne PEUPLÉE sans move_to → 422, la colonne ET la carte restent."""
    eid = client.post("/pipeline", json={"idu": "97415000AB0001"}).json()["entry"]["id"]
    cols = client.get("/pipeline/columns").json()["columns"]
    first = cols[0]  # la carte y est (colonne d'entrée par défaut)
    r = client.request("DELETE", f"/pipeline/columns/{first['id']}", json={})
    assert r.status_code == 422
    # rien n'a bougé : colonne présente, carte toujours suivie
    assert first["id"] in [c["id"] for c in client.get("/pipeline/columns").json()["columns"]]
    assert any(e["id"] == eid for e in client.get("/pipeline").json())


def test_h2_delete_deplace_les_cartes_jamais_perdues(client):
    """Avec move_to : les cartes sont déplacées vers la cible, PUIS la colonne supprimée. Zéro perte."""
    eid = client.post("/pipeline", json={"idu": "97415000AB0001"}).json()["entry"]["id"]
    cols = client.get("/pipeline/columns").json()["columns"]
    src, dst = cols[0], cols[2]
    dst_key = dst["key"]
    r = client.request("DELETE", f"/pipeline/columns/{src['id']}", json={"move_to": dst["id"]})
    assert r.status_code == 200 and r.json()["moved"] == 1
    assert src["id"] not in [c["id"] for c in r.json()["columns"]]
    # la carte n'a PAS disparu : elle est dans la colonne cible
    entry = next(e for e in client.get("/pipeline").json() if e["id"] == eid)
    assert entry["status"] == dst_key


def test_h2_move_to_doit_appartenir_au_tenant_et_differer(client):
    """move_to vers soi-même ou vers une colonne inconnue → refus (422/404), carte préservée."""
    client.post("/pipeline", json={"idu": "97415000AB0001"})
    cols = client.get("/pipeline/columns").json()["columns"]
    src = cols[0]
    # cible = elle-même
    assert client.request("DELETE", f"/pipeline/columns/{src['id']}", json={"move_to": src["id"]}).status_code == 422
    # cible inexistante
    assert client.request("DELETE", f"/pipeline/columns/{src['id']}", json={"move_to": 999999}).status_code == 404
    # la colonne source et la carte sont intactes
    assert src["id"] in [c["id"] for c in client.get("/pipeline/columns").json()["columns"]]


def test_h2_derniere_colonne_indelebile(client):
    """On ne peut JAMAIS supprimer la dernière colonne (même vide) — le kanban ne peut être vidé."""
    from labuse.db import session_scope
    # ne garder qu'UNE colonne
    with session_scope() as s:
        ids = [r[0] for r in s.execute(_t("SELECT id FROM crm_columns WHERE compte_id IS NULL ORDER BY position"))]
        # semer d'abord si vide
    cols = client.get("/pipeline/columns").json()["columns"]
    ids = [c["id"] for c in cols]
    with session_scope() as s:
        s.execute(_t("DELETE FROM crm_columns WHERE compte_id IS NULL AND id <> :keep"), {"keep": ids[0]})
        s.commit()
    only = client.get("/pipeline/columns").json()["columns"]
    assert len(only) == 1
    r = client.request("DELETE", f"/pipeline/columns/{only[0]['id']}", json={"move_to": None})
    assert r.status_code == 422
    assert len(client.get("/pipeline/columns").json()["columns"]) == 1


# ─────────────────────────── H3 : réinitialiser ───────────────────────────

def test_h3_reset_restaure_defaut_et_remappe_les_cartes(client):
    """Réinitialiser : re-sème les défauts LABUSE et REPLACE les cartes dans la 1re colonne
    (aucune carte perdue même si elle était dans une colonne custom supprimée)."""
    # état custom : une colonne ajoutée, une carte déplacée dedans
    added = client.post("/pipeline/columns", json={"label": "Signé"}).json()["columns"]
    new_key = added[-1]["key"]
    eid = client.post("/pipeline", json={"idu": "97415000AB0001"}).json()["entry"]["id"]
    client.patch(f"/pipeline/{eid}", json={"status": new_key})
    assert next(e for e in client.get("/pipeline").json() if e["id"] == eid)["status"] == new_key
    # reset
    r = client.post("/pipeline/columns/reset")
    assert r.status_code == 200
    cols = r.json()["columns"]
    assert _labels(cols)[0] == "Repérée" and all(c["is_default"] for c in cols)
    assert "Signé" not in _labels(cols)
    # la carte n'a PAS disparu : elle est dans la 1re colonne par défaut
    entry = next(e for e in client.get("/pipeline").json() if e["id"] == eid)
    assert entry["status"] == cols[0]["key"]
