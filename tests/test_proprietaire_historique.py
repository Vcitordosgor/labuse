"""L1 (rattrapage KelFoncier 2) — historique du propriétaire PM par millésime + diff annuel.

Base de test vide → on SEME un jeu [KF-TEST] : une parcelle qui change de SCI entre 2023 et 2024,
avec un millésime 2025 servi (table de prod). On gèle : la timeline unifie versionné + servi SANS
écraser le servi, le diff est un CONSTAT (avant→après), les acquisitions récentes comptent le vrai
total, et l'historique est PM-only (aucune personne physique).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.db import session_scope
from labuse.proprietaire_historique import acquisitions_recentes, historique

pytestmark = pytest.mark.db

INSEE = "97415"                       # Saint-Paul (pour les acquisitions par commune)
SIREN_A = "900000101"
SIREN_B = "900000102"


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


@pytest.fixture
def seed(engine):
    """Parcelle [KF-TEST] : SCI A en 2022-2023, SCI B en 2024 (changement), B servi en 2025."""
    tag = uuid.uuid4().hex[:4].upper()
    idu = f"{INSEE}000{tag}0001"[:14].ljust(14, "0")
    with session_scope() as s:
        # base de test parfois créée avec un schéma commune_insee_logement antérieur à la colonne
        # insee (CREATE TABLE IF NOT EXISTS ne rétro-remplit pas) — défensif, sans effet en prod.
        s.execute(text("ALTER TABLE commune_insee_logement ADD COLUMN IF NOT EXISTS insee varchar"))
        for m, siren, denom in [(2022, SIREN_A, "SCI KF-TEST ALPHA"),
                                (2023, SIREN_A, "SCI KF-TEST ALPHA"),
                                (2024, SIREN_B, "SCI KF-TEST BETA")]:
            s.execute(text(
                "INSERT INTO pm_proprietaires_millesimes (millesime, idu, groupe, groupe_label, "
                "forme_juridique, denomination, siren, url_source) "
                "VALUES (:m, :i, 0, 'PM', 'SCI', :d, :s, 'http://kf-test')"),
                {"m": m, "i": idu, "d": denom, "s": siren})
        # millésime SERVI 2025 (table de prod) — jamais écrasé, uni à la volée par la timeline
        s.execute(text(
            "INSERT INTO parcelle_personne_morale (idu, groupe, groupe_label, forme_juridique, "
            "denomination, siren, millesime, source) "
            "VALUES (:i, 0, 'PM', 'SCI', 'SCI KF-TEST BETA', :s, '2025', 'DGFiP')"),
            {"i": idu, "s": SIREN_B})
        s.execute(text("INSERT INTO commune_insee_logement (insee, commune) VALUES (:i, :c) "
                       "ON CONFLICT DO NOTHING"), {"i": INSEE, "c": "KF-Test-Ville"})
    yield {"idu": idu}
    with session_scope() as s:
        s.execute(text("DELETE FROM pm_proprietaires_millesimes WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM parcelle_personne_morale WHERE idu = :i"), {"i": idu})


def test_timeline_unifie_versionne_et_servi(seed):
    with session_scope() as db:
        h = historique(db, seed["idu"])
    assert h is not None
    # 2022, 2023, 2024 (versionné) + 2025 (servi) — le millésime servi est UNI, pas écrasé
    assert [m["millesime"] for m in h["millesimes"]] == [2022, 2023, 2024, 2025]
    assert h["n_millesimes"] == 4
    assert h["millesimes"][-1]["situation"] == "1ᵉʳ janvier 2025"


def test_diff_est_un_constat_avant_apres(seed):
    with session_scope() as db:
        h = historique(db, seed["idu"])
    # un seul changement CONSTATÉ : 2023 → 2024, SCI A → SCI B
    assert h["n_changements"] == 1
    c = h["changements"][0]
    assert (c["de_millesime"], c["a_millesime"]) == (2023, 2024)
    assert c["siren_avant"] == SIREN_A and c["siren_apres"] == SIREN_B
    assert c["denomination_avant"] == "SCI KF-TEST ALPHA" and c["denomination_apres"] == "SCI KF-TEST BETA"
    # aucune interprétation servie — juste le constat + le garde-fou de lecture
    assert "vente" in h["note"] and "scoring" in h["note"]


def test_acquisitions_recentes_compte_le_vrai_total(seed):
    with session_scope() as db:
        a = acquisitions_recentes(db, INSEE, depuis_millesime=2022, limit=8)
    assert a["n_total"] >= 1                       # au moins notre changement 2023→2024
    assert any(x["siren_avant"] == SIREN_A and x["siren_apres"] == SIREN_B for x in a["acquisitions"])


def test_parcelle_sans_pm_ne_rend_rien(seed):
    with session_scope() as db:
        assert historique(db, "00000000XX0000") is None


def test_endpoints(client, seed):
    r = client.get(f"/proprietaires/{seed['idu']}/historique").json()
    assert r["n_millesimes"] == 4 and r["n_changements"] == 1
    # parcelle inconnue → {} (jamais une erreur)
    assert client.get("/proprietaires/00000000XX0000/historique").json() == {}
    acq = client.get("/proprietaires/acquisitions", params={"commune": "KF-Test-Ville", "depuis": 2022}).json()
    assert acq["n_total"] >= 1
    # commune inconnue → non couvert, jamais un zéro muet inventé
    assert client.get("/proprietaires/acquisitions", params={"commune": "Nulle-Part"}).json()["non_couvert"] is True
