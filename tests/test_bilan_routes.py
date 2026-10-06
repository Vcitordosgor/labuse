"""BILAN-1 Lot 3 (porte) — routes modèle + calcul.

Le front n'envoie que des saisies ; le moteur calcule. On vérifie que :
  · /bilan/{idu}/modele sert la structure (4 blocs, 45 postes), le Sourcé
    pré-rempli (terrain du cadastre, TVA légales) et les ratios du compte ;
  · /bilan/{idu}/calcul rend un bilan incomplet SANS marge quand un poste manque,
    et un résultat quand tout est posé — jamais le front ne calcule.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


@pytest.fixture
def app_client(engine, monkeypatch):
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-bilan-routes")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-bilan-routes-0000000000000000000")
    monkeypatch.setenv("LABUSE_SMTP_HOST", "")
    monkeypatch.setenv("BREVO_API_KEY", "")
    from labuse import config

    config.get_settings.cache_clear()
    from labuse.api.app import app

    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def _compte_actif(email: str) -> int:
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:
            pass
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(
            s, inv["lien"].split("token=")[1], "motdepasse-bilan-routes", "2026-09-28"
        )
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client, email):
    r = client.post(
        "/login",
        data={"identifiant": email, "password": "motdepasse-bilan-routes"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    return client


def _seed(idu: str, surface: float) -> None:
    with session_scope() as s:
        if not s.execute(text("SELECT 1 FROM parcels WHERE idu=:i"), {"i": idu}).scalar():
            s.execute(
                text(
                    "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
                    " VALUES (:i,'Saint-Paul','BW','102', ST_GeomFromText(:w,4326),"
                    " ST_Transform(ST_GeomFromText(:w,4326),2975), :s,"
                    " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"
                ),
                {"i": idu, "w": _WKT, "s": surface},
            )
        s.commit()


@pytest.fixture
def client_parc(app_client):
    email = f"bru-{uuid.uuid4().hex[:8]}@x.test"
    idu = f"97415000BW{uuid.uuid4().int % 10000:04d}"
    _compte_actif(email)
    _seed(idu, 1746.0)
    c = TestClient(app_client.app, base_url="https://testserver")
    _login(c, email)
    try:
        yield c, idu
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": idu})
            s.commit()
        with session_scope() as s:
            try:
                comptes.supprimer_utilisateur(s, email)
            except Exception:
                pass
            s.commit()


def test_modele_sert_structure_et_source(client_parc):
    c, idu = client_parc
    # un ratio maison existe déjà
    assert c.put("/bilan-ratios/moe", json={"valeur": 3.8}).status_code == 200

    m = c.get(f"/bilan/{idu}/modele")
    assert m.status_code == 200, m.text
    j = m.json()
    assert [b["id"] for b in j["blocs"]] == ["T", "C", "G", "V"]
    assert sum(len(b["postes"]) for b in j["blocs"]) == 45
    assert j["tva_legales"]["dom_standard"] == 0.085
    # Sourcé : surface terrain du cadastre
    assert j["sourcee"]["terrain"] == pytest.approx(1746.0)
    assert j["sourcee"]["commune"] == "Saint-Paul"
    # ratio maison remonté
    assert j["ratios_compte"]["moe"]["valeur"] == 3.8
    # repères publics : clé présente (contenu best-effort, jamais un 500)
    assert "reperes_publics" in j


def test_calcul_incomplet_sans_marge(client_parc):
    c, idu = client_parc
    corps = {
        "programme": {"terrain": 1746},
        "produits": [{"libelle": "Libre", "lots": 46, "suv": 2560, "prix_ttc_m2_suv": 4800, "tva": 0.085}],
        "postes": {"achat": {"valeur": 1000, "etat": "saisi", "tva": 0.0}},
        "mode": "marge",
    }
    r = c.post(f"/bilan/{idu}/calcul", json=corps)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["complet"] is False
    assert j["resultat_net"] is None and j["marge_pct"] is None
    assert j["manquants"]  # beaucoup de postes à renseigner
