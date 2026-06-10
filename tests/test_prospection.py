"""Module prospection Niveau 1 — saisie manuelle, validation, RGPD/vocabulaire, API, export."""
from pathlib import Path

import pytest
from sqlalchemy import text

from labuse import prospection as P
from labuse.api.export import fiche_html, fiche_markdown

ROOT = Path(__file__).resolve().parents[1]


# ── Cœur pur (sans DB) ─────────────────────────────────────────────
def test_default_n_invente_aucun_nom():
    d = P.default_prospection()
    assert d["statut_proprietaire"] == "inconnu"
    assert "contact_nom" not in d and not P.has_manual_contact(d)


def test_merge_valide_et_borne():
    out = P.merge_prospection(P.default_prospection(),
                              {"statut_proprietaire": "identifie_manuellement",
                               "source_statut": "saisi_utilisateur", "contact_nom": "Mairie de Saint-Paul"})
    assert out["statut_proprietaire"] == "identifie_manuellement"
    assert out["contact_nom"] == "Mairie de Saint-Paul" and P.has_manual_contact(out)


def test_merge_refuse_enum_invalide():
    with pytest.raises(ValueError):
        P.merge_prospection({}, {"statut_proprietaire": "proprietaire_officiel"})
    with pytest.raises(ValueError):
        P.merge_prospection({}, {"niveau_confiance": "absolu"})


def test_merge_ignore_cles_inconnues():
    out = P.merge_prospection({}, {"hack": "x", "contact_nom": "ok"})
    assert "hack" not in out and out["contact_nom"] == "ok"


def test_merge_valide_les_dates():
    assert P.merge_prospection({}, {"date_prochaine_action": "2026-07-01"})["date_prochaine_action"] == "2026-07-01"
    with pytest.raises(ValueError):
        P.merge_prospection({}, {"date_prochaine_action": "pas-une-date"})


# ── Exports (synthétique, sans DB) ─────────────────────────────────
def _fiche(prospection):
    return {"parcel": {"idu": "97415000BN1351", "commune": "Saint-Paul", "surface_m2": 4552,
                       "section": "BN", "numero": "1351"},
            "verdict": {"status": "opportunite", "opportunity_score": 73, "completeness_score": 60, "reasons": []},
            "cascade": [], "sources_responded": [], "sources_silent": [],
            "disclaimer": "Pré-analyse.", "ai": None, "prospection": prospection}


def test_export_bloc_prospection_avec_contact():
    md = fiche_markdown(_fiche({"statut_label": "Identifié manuellement",
                                "data": {"statut_proprietaire": "identifie_manuellement", "contact_nom": "EPF Réunion"}}))
    assert "Prospection propriétaire" in md and "EPF Réunion" in md


def test_export_sans_contact_dit_a_identifier():
    md = fiche_markdown(_fiche({"statut_label": "Propriétaire inconnu", "data": {}}))
    assert "Propriétaire à identifier — aucune donnée nominative disponible dans LA BUSE" in md
    h = fiche_html(_fiche({"statut_label": "Propriétaire inconnu", "data": {}}))
    assert "Prospection propriétaire" in h and "aucune donnée nominative" in h


# ── Garde-fous RGPD / vocabulaire (assets user-facing) ─────────────
_FORBIDDEN = ["propriétaire officiel", "propriétaire garanti", "contact vérifié automatiquement",
              "donnée fiscale", "donnée majic", "donnée fichiers fonciers"]


@pytest.mark.parametrize("rel", ["src/labuse/api/web/app.js", "src/labuse/api/export.py", "src/labuse/prospection.py"])
def test_vocabulaire_interdit_absent(rel):
    txt = (ROOT / rel).read_text(encoding="utf-8").lower()
    for bad in _FORBIDDEN:
        assert bad not in txt, f"formulation interdite « {bad} » dans {rel}"


# ── API (DB) : pipeline + prospection manuelle ─────────────────────
pytestmark_db = pytest.mark.db


@pytest.fixture
def client_parcel(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.db import session_scope
    wkt = "POLYGON((55.30 -21.00,55.31 -21.00,55.31 -20.99,55.30 -20.99,55.30 -21.00))"
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
            "('99999000ZZ0001','Testville','Z','1', ST_GeomFromText(:w,4326), 1000, "
            "ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"w": wkt})
    try:
        yield TestClient(app), "99999000ZZ0001"
    finally:
        with session_scope() as s:
            s.execute(text("DELETE FROM parcels WHERE idu='99999000ZZ0001'"))


@pytest.mark.db
def test_api_pipeline_prospection(client_parcel):
    client, idu = client_parcel
    # ajout au pipeline → prospection par défaut, AUCUN nom pré-rempli
    r = client.post("/pipeline", json={"idu": idu})
    assert r.status_code == 200
    e = r.json()["entry"]
    assert e["prospection"].get("statut_proprietaire") == "inconnu"
    assert not e["prospection"].get("contact_nom") and e["has_manual_contact"] is False
    eid = e["id"]

    # passer « propriétaire à identifier » + saisir un contact manuel
    r = client.patch(f"/pipeline/{eid}", json={"status": "proprietaire_a_identifier",
                     "prospection": {"statut_proprietaire": "identifie_manuellement",
                                     "source_statut": "saisi_utilisateur", "contact_nom": "Commune de X",
                                     "prochaine_action": "Demander le relevé de propriété"}})
    assert r.status_code == 200
    e = r.json()["entry"]
    assert e["status"] == "proprietaire_a_identifier"
    assert e["prospection"]["contact_nom"] == "Commune de X" and e["has_manual_contact"] is True

    # valeur d'enum invalide → 422 (pas de stockage)
    assert client.patch(f"/pipeline/{eid}", json={"prospection": {"statut_proprietaire": "bidon"}}).status_code == 422

    # export markdown : le bloc prospection apparaît avec le contact saisi
    ex = client.get(f"/parcels/{idu}/export", params={"format": "md"})
    assert ex.status_code == 200 and "Prospection propriétaire" in ex.text and "Commune de X" in ex.text
