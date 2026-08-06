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


def test_filtre_unifie_shape_et_source(client):
    # M45 (P1) : endpoint unifié /filtre — compte + tiers + page en un appel ; source requise.
    assert client.get("/filtre", params={"tiers": "brulante"}).status_code == 404  # sans source
    r = client.get("/filtre", params={"source": Q_A_RUN_LABEL, "commune": "Saint-Paul", "limit": 2})
    assert r.status_code == 200
    d = r.json()
    assert {"compte", "tiers", "opportunites", "page", "sort"} <= set(d)
    assert isinstance(d["compte"], int) and isinstance(d["page"], list) and len(d["page"]) <= 2
    # garde RGPD vaut aussi sur /filtre
    assert client.get("/filtre", params={"source": Q_A_RUN_LABEL, "flags": "age_dirigeant"}).status_code == 400


def test_p2a_facettes_composables(client):
    # M45 (P2a) : les nouvelles facettes (barre niveau 1 + tiroir droit) filtrent sans erreur,
    # sont composables, et le compteur reste un entier cohérent (<= total non filtré).
    total = client.get("/filtre", params={"source": Q_A_RUN_LABEL}).json()["compte"]
    for crit in [{"constructibilite": "constructible"}, {"constructibilite": "inconstructible,rnu"},
                 {"etat_sol": "nu,bati_sature"}, {"capacite_min": 3}, {"zone_plu": "UA,UB"},
                 {"sdp_max": 500}, {"surface_min": 300, "sdp_min": 100, "constructibilite": "constructible"}]:
        r = client.get("/filtre", params={"source": Q_A_RUN_LABEL, "limit": 0, **crit})
        assert r.status_code == 200, crit
        c = r.json()["compte"]
        assert isinstance(c, int) and 0 <= c <= total, (crit, c, total)


def test_p2d_facettes_tiroirs(client):
    # M45 (P2d) : facettes composables adossées à des tables PRÉSENTES dans labuse_test
    # (parcel_residuel, parcel_p_score_v2, parcelle_personne_morale). Les facettes sur tables
    # matérialisées hors modèle (renouvellement, division_or, NPNRU, état société, adresse BAN)
    # sont vérifiées sur la base réelle (comptes au commit [M45-P2d]) — non exercées ici.
    total = client.get("/filtre", params={"source": Q_A_RUN_LABEL}).json()["compte"]
    for crit in [{"sous_densite": "true"}, {"mult_min": 2}, {"rang_max": 100},
                 {"proprietaire_type": "bailleur"}, {"proprietaire_type": "pp"},
                 {"copro": "avec"}, {"copro": "sans"},
                 {"sous_densite": "true", "mult_min": 1.5, "proprietaire_type": "pm"}]:
        r = client.get("/filtre", params={"source": Q_A_RUN_LABEL, "limit": 0, **crit})
        assert r.status_code == 200, crit
        c = r.json()["compte"]
        assert isinstance(c, int) and 0 <= c <= total, (crit, c, total)


def test_params_morts_inertes(client):
    # Passés, `v_signal`/`statuts`/`brulantes` sont ignorés (params inconnus) : pas d'erreur,
    # et surtout ils ne filtrent plus rien (le total ne bouge pas vs la requête sans eux).
    base = client.get("/stats", params={"source": Q_A_RUN_LABEL, "commune": "Saint-Paul"}).json()
    avec = client.get("/stats", params={"source": Q_A_RUN_LABEL, "commune": "Saint-Paul",
                                        "v_signal": "pcl", "statuts": "chaude", "brulantes": "true"}).json()
    assert avec["total"] == base["total"]
