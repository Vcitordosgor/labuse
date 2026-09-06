"""CIRCUIT-4 lot 5 — la règle SUR le circuit : le miroir base porte la règle, l'endpoint sert les
badges, le Résumé porte les lignes « écarts à la règle » / « choix LABUSE à confirmer », et le job
regles-references existe mais reste DÉSACTIVÉ."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import regles


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


@pytest.mark.db
def test_sync_porte_la_regle(engine):
    from labuse.db import session_scope
    from labuse.registre.sync import sync
    with session_scope() as s:
        sync(s)
        row = s.execute(text(
            "SELECT classe_regle, verdict_regle, valide_par, reference_regle"
            " FROM registre_chiffres WHERE id = 'taxe_amenagement_eur'")).mappings().first()
        s.commit()
    assert row["classe_regle"] == "regle_externe" and row["verdict_regle"] == "conforme"
    assert row["valide_par"] == "cc"
    assert row["reference_regle"] and "1635 quater" in str(row["reference_regle"])


@pytest.mark.db
def test_endpoint_sert_les_regles(client, engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    circ = client.get("/admin/circuit").json()
    # chaque donnée moteur porte sa règle dans le payload (badges du tiroir de trace)
    rg = circ["chiffres"]["taxe_amenagement_eur"]["regle"]
    assert rg["verdict"] == "conforme" and rg["reference"]["url"].startswith("https://")
    # les lignes du Résumé : écarts (tant que E1 tient) et choix (fiches en_attente)
    lignes = {li["titre"]: li for g in circ["resume"]["groupes"] for li in g["lignes"]}
    regles.charger()
    a_ecart = any(f.verdict == "ecart" for f in regles.TOUTES)
    if a_ecart:
        assert "écarts à la règle" in lignes
        assert lignes["écarts à la règle"]["cible"]["type"] == "robinet"
    assert "choix LABUSE à confirmer" in lignes
    assert lignes["choix LABUSE à confirmer"]["cible"]["type"] == "robinet"
    assert lignes["choix LABUSE à confirmer"]["couleur"] == "gris"     # à décider, jamais bloquant


@pytest.mark.db
def test_detail_robinet_porte_badges(client, engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    from labuse.registre import ROBINETS
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    rid = next(r for r, rb in ROBINETS.items() if "taxe_amenagement_eur" in rb.chiffres)
    d = client.get(f"/admin/circuit/robinet/{rid}").json()
    ch = next(x for x in d["chiffres"] if x["id"] == "taxe_amenagement_eur")
    assert ch["regle"]["verdict"] == "conforme"
    assert "extrait" in ch["regle"]["reference"]


def test_job_regles_references_desactive():
    from labuse.jobs import JOBS
    j = JOBS["regles-references"]
    assert "DÉSACTIVÉ" in j.titre and "JAMAIS posé" in j.heure_reunion
    # jamais posé au crontab (même doctrine qu'agents-sources) — verrouillé par test_circuit1_lot8
    from pathlib import Path
    cron = Path("deploy/cron.d-labuse").read_text()
    assert "regles-references" not in cron


def test_robinets_par_verdict():
    out = regles.robinets_par_verdict({"rob_taxe": ["taxe_amenagement_eur"],
                                       "rob_dist": ["distance_arret_m"],
                                       "rob_choix": ["n_piscines"]})
    regles.charger()
    if regles.FICHES["distance_arret_m"].verdict == "ecart":
        assert "rob_dist" in out["ecart"]
    assert "rob_taxe" not in out["ecart"]
    assert "rob_choix" in out["choix"]         # n_piscines : choix en_attente
