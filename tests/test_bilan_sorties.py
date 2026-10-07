"""BILAN-1 Lot 5 — sorties : génération, PDF, Excel, round-trip des saisies.

Un bilan s'enregistre (saisies en JSON), puis PDF et Excel se régénèrent depuis
ces mêmes saisies. BILAN-2 : un bilan À MOITIÉ rempli se génère et s'exporte aussi
(calcul en continu, case vide = 0) ; plus de porte « bilan complet » (422).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse import comptes
from labuse.db import session_scope
from test_bilan_moteur import entrees_temoin_promotrice

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _corps_temoin() -> dict:
    """entrees_temoin_promotrice() → le corps JSON attendu par la route calcul/generer."""
    e = entrees_temoin_promotrice()
    return {
        "programme": {
            "terrain": e.programme.terrain,
            "surface_taxable": e.programme.surface_taxable,
            "loyer": e.programme.loyer,
        },
        "produits": [
            {
                "libelle": p.libelle,
                "lots": p.lots,
                "suv": p.suv,
                "prix_ttc_m2_suv": p.prix_ttc_m2_suv,
                "tva": p.tva,
            }
            for p in e.produits
        ],
        "postes": {
            pid: {
                "valeur": s.valeur,
                "etat": s.etat,
                "tva": s.tva,
                "assiette_valeur": s.assiette_valeur,
            }
            for pid, s in e.postes.items()
        },
        "mode": "marge",
    }


@pytest.fixture
def app_client(engine, monkeypatch):
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "pilote-bilan-sorties")
    monkeypatch.setenv("LABUSE_SECRET_KEY", "secret-bilan-sorties-00000000000000000")
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
            s, inv["lien"].split("token=")[1], "motdepasse-bilan-sorties", "2026-09-28"
        )
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def _login(client, email):
    r = client.post(
        "/login",
        data={"identifiant": email, "password": "motdepasse-bilan-sorties"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    return client


@pytest.fixture
def client_parc(app_client):
    email = f"bso-{uuid.uuid4().hex[:8]}@x.test"
    idu = f"97415000BZ{uuid.uuid4().int % 10000:04d}"
    _compte_actif(email)
    with session_scope() as s:
        s.execute(
            text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
                " VALUES (:i,'Saint-Paul','BZ','1065', ST_GeomFromText(:w,4326),"
                " ST_Transform(ST_GeomFromText(:w,4326),2975), 1746,"
                " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"
            ),
            {"i": idu, "w": _WKT},
        )
        s.commit()
    c = TestClient(app_client.app, base_url="https://testserver")
    _login(c, email)
    try:
        yield c, idu
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM parcels WHERE idu=:i"), {"i": idu})
            try:
                comptes.supprimer_utilisateur(s, email)
            except Exception:
                pass
            s.commit()


def test_generer_moitie_rempli_puis_exports(client_parc):
    """BILAN-2 : un bilan à moitié rempli se génère ET s'exporte (PDF + Excel)."""
    c, idu = client_parc
    corps = {
        "programme": {"terrain": 1746},
        "produits": [{"libelle": "Libre", "lots": 46, "suv": 2560, "prix_ttc_m2_suv": 4800, "tva": 0.085}],
        "postes": {"achat": {"valeur": 1000, "etat": "saisi", "tva": 0.0}},
        "mode": "marge",
    }
    g = c.post(f"/bilan/{idu}/generer", json=corps)
    assert g.status_code == 200, g.text
    body = g.json()
    doc_id = body["doc_id"]
    assert body["complet"] is False and body["lignes_vides"] > 0  # non bloquant
    # PDF et Excel se régénèrent malgré les lignes vides
    pdf = c.get(f"/bilan/{idu}.pdf", params={"doc_id": doc_id})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    xlsx = c.get(f"/bilan/{idu}.xlsx", params={"doc_id": doc_id})
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


def test_generer_puis_pdf_et_excel(client_parc):
    c, idu = client_parc
    g = c.post(f"/bilan/{idu}/generer", json=_corps_temoin())
    assert g.status_code == 200, g.text
    doc_id = g.json()["doc_id"]

    # le bilan est inscrit dans « Mes documents » avec la colonne Excel servie
    docs = c.get("/documents").json()
    ligne = next(d for d in docs["documents"] if d["id"] == doc_id) if isinstance(docs, dict) else next(
        d for d in docs if d["id"] == doc_id
    )
    assert ligne["doc_type"] == "bilan"
    assert ligne["excel"] is True

    # PDF régénéré depuis les saisies stockées
    p = c.get(f"/bilan/{idu}.pdf?doc_id={doc_id}")
    assert p.status_code == 200, p.text
    assert p.content[:5] == b"%PDF-"

    # Excel régénéré depuis les mêmes saisies
    x = c.get(f"/bilan/{idu}.xlsx?doc_id={doc_id}")
    assert x.status_code == 200, x.text
    assert x.content[:2] == b"PK"  # zip (xlsx)

    # un autre doc_id inexistant → 404
    assert c.get(f"/bilan/{idu}.pdf?doc_id=999999").status_code == 404
