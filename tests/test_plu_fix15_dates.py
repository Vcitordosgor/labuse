import pytest
from labuse.api import modules
from labuse.registre.moteurs import commune


@pytest.fixture
def annuaire(monkeypatch):
    codes = ["97407", "97408", "97410", "97414", "97423"]
    def etat(db, mil):
        return {"n_communes": len(codes), "n_rnu": 0, "communes": [
            {"insee": c, "commune": mil[c]["commune"], "idurba": mil[c]["idurba"], "statut": "servable"} for c in codes]}
    monkeypatch.setattr(commune, "etat_corpus_plu", etat)
    return {r["insee"]: r for r in modules.plu_annuaire_communes(None)["communes"]}


@pytest.mark.parametrize("code,approbation,modification,lot", [
    ("97407", "2018-10-02", "2024-01-30", "2024-12-09"),
    ("97408", "2019-06-12", "2025-12-17", "2026-06-25"),
    ("97414", "2014-03-11", "2025-07-09", "2025-12-18"),
    ("97423", "2017-02-21", "2022-06-02", "2022-06-02"),
    ("97410", None, None, "2020-02-06"),
])
def test_dates_couverture_et_depot(annuaire, code, approbation, modification, lot):
    c = annuaire[code]
    assert c["date_approbation"] == approbation
    assert c.get("derniere_modification_couverture") == modification
    assert c["millesime_lot"] == lot


@pytest.mark.parametrize("code,libelle", [
    ("97416", "Approbation en couverture · 06/2024"),
    ("97407", "Approbation en couverture · 02/10/2018"),
    ("97410", "Dépôt GPU 97410_PLU_20200206"),
])
def test_date_du_document_sur_la_fiche(code, libelle):
    from labuse.api.app import _plu_fraicheur
    assert _plu_fraicheur(code + "000AA0001")["document_servi"] == libelle
