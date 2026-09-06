"""FICHE-1 lot 6 — les annonces Radar rattachées à la parcelle (Marché et secteur)."""
from __future__ import annotations

from labuse.registre import ROBINETS
from labuse.registre.donnees import DONNEES


def test_registre_radar_annonces_declare():
    d = DONNEES["radar_annonces_liste"]
    assert d.en_attente is None and d.type == "liste"
    assert set(d.reservoirs) == {"radar_pige", "dvf"}
    assert "radar_annonces_liste" in ROBINETS["fiche_parcelle_marche"].chiffres


def test_statut_libelle():
    from labuse.api.app import _RADAR_STATUT_LIBELLE
    assert _RADAR_STATUT_LIBELLE["active"] == "en cours"
    assert _RADAR_STATUT_LIBELLE["retiree"] == "retirée"
    assert _RADAR_STATUT_LIBELLE["vendue"] == "vendue"


def test_ecart_demande_acte_seulement_en_cours_avec_dvf(monkeypatch):
    """L'écart demandé/acté n'est servi que pour une annonce EN COURS avec mutation DVF ;
    calculé sur €/m² quand dispo (formule ecart_demande_acte_pct, maille parcelle)."""
    from labuse.api import app as _app

    class FakeRes:
        def __init__(self, data): self._data = data
        def mappings(self): return self
        def all(self): return self._data if isinstance(self._data, list) else []
        def first(self): return self._data if not isinstance(self._data, list) else None

    annonce = {"bien_id": 1, "statut": "active", "rattachement_niveau": "source",
               "date_annonce": None, "prix": 400000, "prix_m2": 5000, "type_bien": "maison",
               "surface_hab": 80, "vendue_valeur": None, "vendue_le": None, "retiree_le": None,
               "portail": "leboncoin", "url_sortante": "https://x"}
    dvf = {"valeur": 300000, "prix_m2_bati": 4000, "date_mutation": None}

    calls = {"n": 0}

    def fake_execute(sql, params=None):
        s = str(sql)
        if "pige_biens" in s:
            return FakeRes([annonce])
        if "v_parcel_dvf_last" in s:
            return FakeRes(dvf)
        return FakeRes([])

    class FakeSession:
        def execute(self, sql, params=None): return fake_execute(sql, params)

    b = _app._radar_annonces_block(FakeSession(), "97411000AA0001")
    assert b["n"] == 1
    item = b["liste"][0]
    assert item["statut"] == "en cours"
    # 5000 vs 4000 → +25 %
    assert item["ecart_demande_acte_pct"] == 25

    # retirée → pas d'écart même avec DVF
    annonce["statut"] = "retiree"
    b2 = _app._radar_annonces_block(FakeSession(), "97411000AA0001")
    assert b2["liste"][0]["statut"] == "retirée"
    assert b2["liste"][0]["ecart_demande_acte_pct"] is None
