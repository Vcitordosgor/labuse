"""CHIRURGICAL-FIX-1 (LOT F, E11) — la table « 8 comparables les plus proches » du Dossier montre la
MÊME population que le chiffre de tête (le médian servi `prix_ancien`, du BÂTI) : jamais des ventes de
TERRAIN sous une médiane de bâti (cas d'un terrain nu, où ESTIMER-3 compare à des ventes de terrain)."""
import labuse.pige.api as pige_api
from labuse.exports.robinet_fiche import _c_comparables, _CMP_MEMO


class _DB:  # jeton d'identité pour la mémoïsation (db) — aucune requête émise
    pass


def _patch_comparables(monkeypatch, comps):
    monkeypatch.setattr(pige_api, "rapport_parcelle",
                        lambda db, idu, f=None: {"estimation": {"comparables": comps}})


def test_terrain_sous_mediane_batie_retire(monkeypatch):
    _CMP_MEMO.clear()
    comps = [{"date": "2024", "type": "Terrain", "prix_m2": 400, "distance_m": 100},
             {"date": "2024", "type": "Terrain", "prix_m2": 350, "distance_m": 120}]
    _patch_comparables(monkeypatch, comps)
    # prix_ancien servi = BÂTI (appartement) → aucune vente de terrain ne doit figurer.
    out = _c_comparables(_DB(), "97416000HT0538", {"prix_ancien": {"type_prix": "appartement"}})
    assert out is None


def test_comparables_bati_conserves_sous_mediane_batie(monkeypatch):
    _CMP_MEMO.clear()
    comps = [{"date": "2025", "type": "Maison", "prix_m2": 2500, "distance_m": 50},
             {"date": "2025", "type": "Maison", "prix_m2": 2600, "distance_m": 80}]
    _patch_comparables(monkeypatch, comps)
    out = _c_comparables(_DB(), "97422000AD0887", {"prix_ancien": {"type_prix": "maison"}})
    assert out is not None and len(out) == 2 and all(c["type"] == "Maison" for c in out)


def test_mixte_garde_bati_retire_terrain(monkeypatch):
    _CMP_MEMO.clear()
    comps = [{"type": "Maison", "prix_m2": 2500}, {"type": "Terrain", "prix_m2": 400},
             {"type": "Appartement", "prix_m2": 2800}]
    _patch_comparables(monkeypatch, comps)
    out = _c_comparables(_DB(), "x", {"prix_ancien": {"type_prix": "mixte (appart+maison)"}})
    assert out is not None and {c["type"] for c in out} == {"Maison", "Appartement"}
