"""Tests Lot 5 (wave-adresses) : pack pré-dossier PC (CERFA pré-rempli, libellé, gating)."""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db

_POLY = ("POLYGON((55.4495 -21.3005, 55.4505 -21.3005, 55.4505 -21.2995,"
         " 55.4495 -21.2995, 55.4495 -21.3005))")


@pytest.fixture
def client_parcelle(engine):
    from labuse.api.app import app
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE idu = '97416000PD0001'"))
        c.execute(text(
            f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
                VALUES ('97416000PD0001', 'Saint-Pierre', 'PD', '0001', 815,
                        ST_GeomFromText('{_POLY}', 4326),
                        ST_Transform(ST_GeomFromText('{_POLY}', 4326), 2975))"""))
    yield TestClient(app, base_url="https://testserver")
    with engine.begin() as c:
        c.execute(text("DELETE FROM parcels WHERE idu = '97416000PD0001'"))


def test_gating_integral(client_parcelle, monkeypatch):
    """Réservé Intégral : un plan Essentiel reçoit 403 + CTA upgrade (stub Phase 0)."""
    monkeypatch.setenv("LABUSE_PLAN_DEFAUT", "essentiel")
    from labuse import config
    config.get_settings.cache_clear()
    try:
        r = client_parcelle.get("/pre-dossier/97416000PD0001.zip")
        assert r.status_code == 403
        assert r.json()["detail"]["plan_requis"] == "integral"
    finally:
        config.get_settings.cache_clear()


def test_pack_cerfa_prerempli_et_libelle(client_parcelle):
    pytest.importorskip("labuse.flash")
    from labuse.api.pre_dossier import LIBELLE

    r = client_parcelle.get("/pre-dossier/97416000PD0001.zip")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms = z.namelist()
    cerfa = next(n for n in noms if n.startswith("cerfa_13406-17"))
    assert "regles_du_zonage_et_pieces.pdf" in noms and "LISEZMOI.txt" in noms
    assert LIBELLE in z.read("LISEZMOI.txt").decode("utf-8")

    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(z.read(cerfa)))
    f = rd.get_fields()
    # champs TERRAIN pré-remplis…
    assert f["T2S_section"].get("/V") == "PD"
    assert f["T2N_numero"].get("/V") == "0001"
    assert f["T2T_superficie"].get("/V") == "815"
    assert f["T2L_localite"].get("/V") == "Saint-Pierre"
    # …champs PROJET laissés VIDES (mandat) — le pack ne préjuge de rien
    assert not (f["H1N_nom"].get("/V") or "")
    # libellé préparatoire tamponné sur CHAQUE page
    assert all("préparatoire" in (p.extract_text() or "") for p in rd.pages)


def test_parcelle_inconnue(client_parcelle):
    assert client_parcelle.get("/pre-dossier/97499000ZZ9999.zip").status_code == 404
