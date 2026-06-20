"""Potentiel résiduel (Lot B) — cœur pur du calcul + garde-fous, sans réseau.

On teste la logique de croisement (bâti existant × capacité max) sur des entrées contrôlées,
en stubbant la faisabilité et le bâti — la faisabilité et bati.py ont leurs propres tests.
"""
from __future__ import annotations

import pytest

from labuse.faisabilite import residuel
from labuse.faisabilite.engine import Faisabilite


def _faisa(constructible=True, emprise=500, sdp_max=1000, niveaux_max=2):
    fr = {"emprise_constructible_m2": emprise, "emprise_batie_max_m2": round(emprise * 0.45),
          "surface_plancher_m2": sdp_max, "niveaux_max": niveaux_max, "niveaux": f"R+{niveaux_max-1}",
          "logements_au_sol": (0, 0), "logements_sous_sol": (0, 0), "stationnement_regime": "borne"}
    f = Faisabilite("U", None, constructible, "v", [], [], [], [], fr, "b")

    class _Ctx:  # ParcelContext-like
        surface_m2 = 1000.0
    return (_Ctx(), f)


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    # Couche bâtiment "présente", niveaux existants = défaut (pas de hauteur ingérée).
    monkeypatch.setattr("labuse.bati.layer_available", lambda s: True)
    monkeypatch.setattr("labuse.faisabilite.residuel._niveaux_existants",
                        lambda s, pid, defaut: (float(defaut), False))


def _ratio(monkeypatch, ratio):
    monkeypatch.setattr("labuse.bati.stats_batch",
                        lambda s, ids: {ids[0]: {"bati_ratio": ratio, "bati_count": 1, "bati_max_m2": 100.0}})


def test_terrain_nu_residuel_quasi_integral(monkeypatch):
    _ratio(monkeypatch, 0.0)
    r = residuel.compute_residuel(None, 1, faisa=_faisa(emprise=500, sdp_max=1000))
    assert r["disponible"] and r["taux_emprise_pct"] == 0 and r["sous_densite"] is True
    assert r["sdp_residuelle_m2"] == 1000 and "terrain nu" in r["libelle"]


def test_parcelle_dense_pas_sous_densite(monkeypatch):
    # ratio 0.45 → emprise bâtie 450 / emprise max 500 = 90 % > seuil 40 %.
    _ratio(monkeypatch, 0.45)
    r = residuel.compute_residuel(None, 1, faisa=_faisa(emprise=500, sdp_max=1000))
    assert r["taux_emprise_pct"] == 90 and r["sous_densite"] is False
    # SDP existante = 450 × 1 niveau (défaut) ; résiduelle = 1000 − 450 = 550.
    assert r["sdp_residuelle_m2"] == 550


def test_sdp_estimee_flaggee_quand_hauteur_absente(monkeypatch):
    _ratio(monkeypatch, 0.2)
    r = residuel.compute_residuel(None, 1, faisa=_faisa())
    assert r["estimation_sdp"] is True and r["niveaux_reels"] is False
    assert "estimée" in r["libelle"]


def test_non_constructible_pas_de_residuel(monkeypatch):
    _ratio(monkeypatch, 0.0)
    r = residuel.compute_residuel(None, 1, faisa=_faisa(constructible=False))
    assert r["disponible"] is False and "non constructible" in r["raison"].lower()


def test_couche_bati_absente(monkeypatch):
    monkeypatch.setattr("labuse.bati.layer_available", lambda s: False)
    r = residuel.compute_residuel(None, 1, faisa=_faisa())
    assert r["disponible"] is False and "bâtiments" in r["raison"].lower()


def test_seuil_sous_densite_borne(monkeypatch):
    """Au seuil exact (emprise bâtie/emprise max = 40 %), pas sous-densité (strictement <)."""
    _ratio(monkeypatch, 0.20)   # 0.20×1000 = 200 m² bâtis / 500 m² max = 40 % → pas < 40
    r = residuel.compute_residuel(None, 1, faisa=_faisa(emprise=500, sdp_max=1000))
    assert r["taux_emprise_pct"] == 40 and r["sous_densite"] is False
