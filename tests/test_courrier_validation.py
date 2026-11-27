import pytest
from fastapi import HTTPException
from starlette.requests import Request

from labuse import cadastre_disparue, courrier_adressage
from labuse.api import courrier


def test_disparue_adressage_relecture_et_pdf(monkeypatch):
    idu = "97411000BZ1065"
    monkeypatch.setattr(cadastre_disparue, "info_disparue", lambda db, idu: {"commune": "Saint-Denis"})
    request = Request({"type": "http", "headers": []})
    resolution = courrier_adressage.resoudre_destinataire(None, idu)
    assert resolution["bloque"] and resolution["code"] == "disparue"
    apercu = courrier.courrier_composer(courrier.ComposerIn(idu=idu), request, None)
    assert apercu["recto"] == resolution["motif"]
    with pytest.raises(HTTPException) as erreur:
        courrier.courrier_pdf(courrier.PdfIn(idu=idu), request, None)
    assert erreur.value.status_code == 422


def test_demande_refuse_le_lot_avant_enregistrement(monkeypatch):
    visites = []

    def resoudre(db, idu):
        visites.append(idu)
        return {"bloque": idu == "B", "motif": "Opposition enregistrée"}

    monkeypatch.setattr(courrier_adressage, "resoudre_destinataire", resoudre)
    monkeypatch.setattr("labuse.api.tenant.current_compte", lambda request: 1)
    body = courrier.DemandeIn(parcelles=["a", " A ", "B"], corps="Courrier de test")
    with pytest.raises(HTTPException) as erreur:
        courrier.courrier_demande(body, None, None)
    assert visites == ["A", "B"]
    assert erreur.value.status_code == 422
    assert "Opposition" in erreur.value.detail


def test_demande_exige_un_expediteur_identifiable(monkeypatch):
    monkeypatch.setattr(courrier_adressage, "resoudre_destinataire", lambda db, idu: {"bloque": False})
    monkeypatch.setattr("labuse.api.tenant.current_compte", lambda request: 1)
    monkeypatch.setattr(courrier, "_marque_du_compte", lambda db, request: {"raison_sociale": "a@b.fr"})
    body = courrier.DemandeIn(parcelles=["A"], corps="Courrier de test")
    with pytest.raises(HTTPException) as erreur:
        courrier.courrier_demande(body, None, None)
    assert erreur.value.status_code == 422
