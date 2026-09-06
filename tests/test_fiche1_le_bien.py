"""FICHE-1 lot 1 — le tiroir « Le bien » (bâti existant + toit).

Garde-fous : le bloc est COHÉRENT (l'emprise servie est l'empreinte BD TOPO, jamais la
sur-détection CoSIA mêlée à un « 0 bâtiment »), il s'OMET quand rien n'est évaluable (couche
bâtiments non ingérée), et le toit se lit sur le CACHE seul (aucune requête WMS dans la fiche).
"""
from __future__ import annotations

from labuse import bati, solaire_toiture


def test_registre_le_bien_declare():
    """Les six données du tiroir sont déclarées, servies (plus en_attente), mono-robinet."""
    from labuse.registre import ROBINETS
    from labuse.registre.donnees import DONNEES
    ids = ("emprise_batie_m2", "hauteur_bati_m", "n_batiments", "surface_libre_sol_m2",
           "nature_toit", "pente_toit_deg")
    for cid in ids:
        assert cid in DONNEES, cid
        assert DONNEES[cid].en_attente is None, f"{cid} ne doit plus être en_attente"
    rob = ROBINETS["fiche_parcelle_le_bien"]
    assert set(ids) <= set(rob.chiffres)


def test_emprise_coherente_avec_le_bati(monkeypatch):
    """L'emprise servie = BD TOPO (cohérente avec le compte) ; la sur-détection CoSIA est servie
    À PART (cosia_detecte_m2), jamais confondue avec l'emprise sur une parcelle « 0 bâtiment »."""
    calls = {"topo": 4210.0, "cosia": 29000.0, "hauteur": None}

    class FakeScalarQ:
        def __init__(self, val): self.val = val
        def scalar(self): return self.val

    def fake_execute(sql, params=None):
        s = str(sql)
        if "SELECT id" in s and "parcels WHERE idu" in s:
            class M:
                def mappings(self): return self
                def first(self): return {"id": 1, "surface_m2": 100000}
            return M()
        if "emprise_cosia_m2" in s:
            return FakeScalarQ(calls["cosia"])
        if "ST_Intersection" in s and "SUM" in s:
            return FakeScalarQ(calls["topo"])
        return FakeScalarQ(0)

    class FakeSession:
        def execute(self, sql, params=None): return fake_execute(sql, params)

    sess = FakeSession()
    monkeypatch.setattr(bati, "layer_available", lambda s: True)
    monkeypatch.setattr(bati, "fiche_block", lambda s, pid, surf: {
        "disponible": True, "code": "vacant", "label": "Aucun bâti significatif détecté",
        "nb_batiments": 0, "ratio_pct": 4, "plus_grand_m2": 0})
    monkeypatch.setattr("labuse.faisabilite.potentiel._hauteur_bati_m", lambda s, pid: None)
    monkeypatch.setattr(solaire_toiture, "toiture_depuis_cache", lambda s, idu: None)
    b = bati.le_bien_block(sess, "97400000AA0001")
    assert b["emprise_batie_m2"] == 4210          # BD TOPO, PAS 29000 (CoSIA)
    assert b["nb_batiments"] == 0
    assert b["cosia_detecte_m2"] == 29000          # dit à part, honnête
    assert b["emprise_source"] == "BD TOPO IGN"


def test_omis_si_couche_batiment_absente(monkeypatch):
    """Couche bâtiments non ingérée → None → le front omet le tiroir (jamais un faux « nu »)."""
    class M:
        def mappings(self): return self
        def first(self): return {"id": 1, "surface_m2": 500}

    class FakeSession:
        def execute(self, sql, params=None): return M()
    monkeypatch.setattr(bati, "layer_available", lambda s: False)
    assert bati.le_bien_block(FakeSession(), "97400000AA0001") is None


def test_toit_cache_seul_jamais_de_wms(monkeypatch):
    """toiture_depuis_cache ne déclenche AUCUN fetch WMS : sur cache vide, renvoie None."""
    sentinel = {"fetched": False}
    monkeypatch.setattr(solaire_toiture, "_fetch_mnh",
                        lambda bbox: sentinel.__setitem__("fetched", True) or "boom")

    class Empty:
        def mappings(self): return self
        def first(self): return None

    class FakeSession:
        def execute(self, sql, params=None): return Empty()
    assert solaire_toiture.toiture_depuis_cache(FakeSession(), "x") is None
    assert sentinel["fetched"] is False
