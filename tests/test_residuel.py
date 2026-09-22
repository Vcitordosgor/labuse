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
    # M32 (BASCULE PHASE C) — compute_residuel lit désormais le bâti RÉVÉLÉ CoSIA (parcel_bati_revele) :
    # point unique isolé en `_emprise_revelee`, qu'on stubbe (pas de bâti révélé par défaut) pour garder
    # ces tests PURS. Avant M32 le calcul n'accédait pas à la base — d'où l'ancien `session=None`.
    monkeypatch.setattr("labuse.faisabilite.residuel._emprise_revelee", lambda s, pid: None)


def _ratio(monkeypatch, ratio):
    monkeypatch.setattr("labuse.bati.stats_batch",
                        lambda s, ids: {ids[0]: {"bati_ratio": ratio, "bati_count": 1, "bati_max_m2": 100.0}})


def test_terrain_nu_residuel_quasi_integral(monkeypatch):
    _ratio(monkeypatch, 0.0)
    r = residuel.compute_residuel(None, 1, faisa=_faisa(emprise=500, sdp_max=1000))
    assert r["disponible"] and r["taux_emprise_pct"] == 0 and r["sous_densite"] is True
    assert r["sdp_residuelle_m2"] == 1000 and "terrain nu" in r["libelle"]


def test_bati_revele_cosia_prime_sur_bd_topo(monkeypatch):
    # M32 — CoSIA voit une emprise que BD TOPO rate (ratio 0) : la parcelle cesse d'être « terrain nu ».
    _ratio(monkeypatch, 0.0)                      # BD TOPO : 0 m² bâti
    monkeypatch.setattr("labuse.faisabilite.residuel._emprise_revelee", lambda s, pid: 300.0)
    r = residuel.compute_residuel(None, 1, faisa=_faisa(emprise=500, sdp_max=1000))
    # révélée 300 > BD TOPO 0 → retenue ; taux 300/500 = 60 % ; SDP existante 300×1 → résiduelle 700.
    assert r["emprise_batie_m2"] == 300 and r["taux_emprise_pct"] == 60
    assert r["sdp_residuelle_m2"] == 700 and r["sous_densite"] is False


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


def test_assiette_clippee_bati_mesure_sur_la_portion_uau(monkeypatch):
    """SCORING-6 lot A — sur une parcelle A/N à cheval clippée, le bâti retranché est celui de
    la SEULE portion U/AU, pas du contour entier : sinon le bâti debout sur la portion A/N
    inconstructible grève un plafond calculé sur la seule portion U/AU → résiduel toujours 0
    (le tout-ou-rien déguisé, cause du run 4 ≡ run 3)."""
    from labuse.faisabilite.db import ParcelContext
    from labuse.faisabilite.engine import Contraintes
    # stats_batch (contour entier) verrait 600 m² de bâti → ne DOIT PAS être utilisé sous clip.
    _ratio(monkeypatch, 0.60)   # 0.60 × 1000 = 600 m² sur toute la parcelle
    monkeypatch.setattr("labuse.faisabilite.residuel._emprise_batie_assiette",
                        lambda s, pid: 20.0)   # 20 m² seulement sur la portion U/AU
    ctx = ParcelContext(1, "x", "Bras-Panon", 1000.0, "N", Contraintes(),
                        zone_parts=[{"zone": "N", "fam": "N", "pct": 95.0},
                                    {"zone": "Uc", "fam": "U", "pct": 5.0}])
    faisa = _faisa(emprise=90, sdp_max=81, niveaux_max=1)
    faisa = (ctx, faisa[1])
    r = residuel.compute_residuel(None, 1, faisa=faisa, assiette_clippee=True)
    # bâti retenu = 20 m² (portion U/AU), niveaux 1 → SDP existante 20 → résiduelle 81 − 20 = 61.
    # (avec le bâti du contour entier : 81 − 600 = 0 → faux tout-ou-rien.)
    assert r["disponible"] and r["emprise_batie_m2"] == 20
    assert r["sdp_residuelle_m2"] == 61


def test_assiette_clippee_ignoree_hors_a_cheval(monkeypatch):
    """Parcelle mono-zone (parts vides) : le clip ne s'applique pas — bâti du contour entier,
    comportement servi identique même quand --assiette-clippee est demandé."""
    from labuse.faisabilite.db import ParcelContext
    from labuse.faisabilite.engine import Contraintes
    _ratio(monkeypatch, 0.20)
    called = {"n": 0}
    monkeypatch.setattr("labuse.faisabilite.residuel._emprise_batie_assiette",
                        lambda s, pid: called.__setitem__("n", called["n"] + 1) or 999.0)
    ctx = ParcelContext(1, "x", "Bras-Panon", 1000.0, "U", Contraintes(), zone_parts=[])
    r = residuel.compute_residuel(None, 1, faisa=(ctx, _faisa(emprise=500, sdp_max=1000)[1]),
                                  assiette_clippee=True)
    # parts vides → _pct_constructible None → clip ignoré → bâti = 0.20×1000 = 200, résiduelle 800.
    assert called["n"] == 0 and r["emprise_batie_m2"] == 200 and r["sdp_residuelle_m2"] == 800


def test_seuil_sous_densite_borne(monkeypatch):
    """Au seuil exact (emprise bâtie/emprise max = 40 %), pas sous-densité (strictement <)."""
    _ratio(monkeypatch, 0.20)   # 0.20×1000 = 200 m² bâtis / 500 m² max = 40 % → pas < 40
    r = residuel.compute_residuel(None, 1, faisa=_faisa(emprise=500, sdp_max=1000))
    assert r["taux_emprise_pct"] == 40 and r["sous_densite"] is False
