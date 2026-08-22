"""Tests Lot 2B (wave-adresses) : courrier — stub, responsabilité, plafond, tarif."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import config, courrier
    from labuse.api.app import app
    courrier.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM courrier_envois"))
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_statut_stub_sans_compte(client):
    """Sans compte prestataire : disponible=false — le front N'AFFICHE PAS le bouton."""
    r = client.get("/courrier/statut").json()
    assert r["disponible"] is False and r["provider"] == "stub"
    # M82 #fuite : la raison est SERVIE au client — jamais le prestataire ni les variables d'env.
    assert r["raison"] and "Merci Facteur" not in r["raison"] and "MERCIFACTEUR" not in r["raison"]
    assert "envoi postal" in r["raison"].lower()
    # tarif = coût prestataire × marge (défauts : 2,69 × 1,5)
    assert r["tarif"]["prix_client_eur"] == round(2.69 * 1.5, 2)


def test_envoi_exige_responsabilite(client):
    r = client.post("/courrier/envois", json={
        "destinataires": [{"idu": "97416000AA0001", "adresse": "12 Rue X, 97410 Saint-Pierre"}],
        "assume_contenu": False})
    assert r.status_code == 422 and "responsabilité" in r.json()["detail"]


def test_envoi_stub_et_plafond(client, monkeypatch, engine):
    monkeypatch.setenv("LABUSE_COURRIER_MAX_JOUR", "2")
    from labuse import config
    config.get_settings.cache_clear()

    r = client.post("/courrier/envois", json={
        "destinataires": [
            {"idu": "97416000AA0001", "adresse": "12 Rue X, 97410 Saint-Pierre"},
            {"idu": "97416000AA0002", "adresse": "14 Rue X, 97410 Saint-Pierre"}],
        "modele": "renovation", "assume_contenu": True})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "stub"
    assert all(e["statut"] == "simule" for e in body["envois"])   # RIEN ne part en stub
    assert body["total_eur"] == round(2 * body["prix_unitaire_eur"], 2)

    # plafond/jour atteint → refus
    r2 = client.post("/courrier/envois", json={
        "destinataires": [{"idu": "97416000AA0003", "adresse": "16 Rue X, 97410 Saint-Pierre"}],
        "assume_contenu": True})
    assert r2.status_code == 422 and "Plafond" in r2.json()["detail"]

    # suivi
    suivi = client.get("/courrier/envois").json()
    assert suivi["n"] == 2 and suivi["envois"][0]["modele"] == "renovation"

def test_courrier_pdf_ne_leve_pas_sur_les_3_modeles(client):
    """Patron test_m136_exports_ne_crashent_pas : POST /courrier/pdf rend un PDF VALIDE (jamais de
    FPDFException) sur les 3 modèles réels ; contenu fidèle au texte affiché (ponctuation → pas de
    « ? », lignes vides des \\n\\n gérées). Le bug d'origine : multi_cell(w=0) sur une ligne vide."""
    import io
    from labuse.api.modules import _COURRIER
    pypdf = pytest.importorskip("pypdf")
    assert set(_COURRIER) == {"standard", "indivision", "succession"}   # les 3, pas un seul
    for motif, tpl in _COURRIER.items():
        texte = tpl.format(ref="BV 912", commune="Saint-Paul", surface=3948,
                           signature="LABUSE — prospection foncière")
        r = client.post("/courrier/pdf", json={"idu": "97415000BV0912", "motif": motif, "texte": texte})
        assert r.status_code == 200, f"{motif}: HTTP {r.status_code}"
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-", f"{motif}: pas un PDF"
        txt = "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(io.BytesIO(r.content)).pages).replace("\n", " ")
        assert "Saint-Paul" in txt and "BV 912" in txt, f"{motif}: contenu absent du PDF"
        assert "?" not in txt, f"{motif}: ponctuation dégradée en « ? »"
