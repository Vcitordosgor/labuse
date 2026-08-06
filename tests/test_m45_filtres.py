"""M45 (P1) — verrous des corrections de filtres menteurs (P0 → P1).

Ces tests VERROUILLENT trois corrections actées au cadrage M45 :
  1. `/parcels` et `/stats` SANS `source` → 404 explicite (fin du repli sur la table morte
     `parcel_evaluations` qui ignorait tous les filtres) ;
  2. garde RGPD CODE : la couche `age_dirigeant` (personne physique) est refusée en critère
     de requête (`flags`/`flags_exclus`), y compris pour un partenaire API direct ;
  3. les params morts `statuts`/`v_signal`/`brulantes` ne filtrent plus (retirés) — passés,
     ils sont inertes (ignorés), jamais une source de filtrage.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from labuse.scoring.score_v_constants import Q_A_RUN_LABEL


@pytest.fixture(scope="module")
def client(engine):
    # Verrous de contrat (404 source, garde RGPD) : pas besoin de données semées — le 404 et le
    # 400 RGPD sont levés AVANT toute requête SQL. `engine` (conftest) garantit le schéma labuse_test.
    from labuse.api.app import app
    return TestClient(app)


def test_parcels_sans_source_404(client):
    r = client.get("/parcels", params={"commune": "Saint-Paul", "limit": 3})
    assert r.status_code == 404
    assert "source" in (r.json().get("detail", "").lower())


def test_stats_sans_source_404(client):
    r = client.get("/stats", params={"commune": "Saint-Paul"})
    assert r.status_code == 404
    assert "source" in (r.json().get("detail", "").lower())


def test_flags_age_dirigeant_refuse_rgpd(client):
    # Garde CODE (pas seulement UI) : un partenaire API ne peut pas requêter la couche PP.
    r = client.get("/parcels", params={"source": Q_A_RUN_LABEL, "flags": "age_dirigeant"})
    assert r.status_code == 400 and "rgpd" in r.json()["detail"].lower()
    # même verrou côté exclusion
    r2 = client.get("/parcels", params={"source": Q_A_RUN_LABEL, "flags_exclus": "age_dirigeant"})
    assert r2.status_code == 400
    # combiné à une couche licite : refus quand même (l'interdit prime)
    r3 = client.get("/stats", params={"source": Q_A_RUN_LABEL, "flags": "pente,age_dirigeant"})
    assert r3.status_code == 400


def test_params_morts_inertes(client):
    # Passés, `v_signal`/`statuts`/`brulantes` sont ignorés (params inconnus) : pas d'erreur,
    # et surtout ils ne filtrent plus rien (le total ne bouge pas vs la requête sans eux).
    base = client.get("/stats", params={"source": Q_A_RUN_LABEL, "commune": "Saint-Paul"}).json()
    avec = client.get("/stats", params={"source": Q_A_RUN_LABEL, "commune": "Saint-Paul",
                                        "v_signal": "pcl", "statuts": "chaude", "brulantes": "true"}).json()
    assert avec["total"] == base["total"]
