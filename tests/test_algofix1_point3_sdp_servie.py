"""ALGO-FIX-1 (point 3) — la SDP résiduelle montrée au client HORS SAISIE vient du RUN SERVI
(vue `parcel_residuel`), pas du moteur live. Le moteur live ne recalcule QUE sur des chiffres saisis
(overrides d'hypothèses ou test d'un projet).

E1/E2 : le panneau Faisabilité affichait la SDP recalculée live (ex. EO0796 187) alors que la fiche
et le Dossier servent 179 (parcel_residuel) → deux SDP pour la même parcelle. Ici le résiduel servi
fait foi hors saisie ; on prouve aussi que la saisie repasse bien sur le moteur live.
"""
from __future__ import annotations

import pytest

from labuse.faisabilite import scenarios
from labuse.faisabilite.engine import Contraintes, Hypotheses, estimate_capacity
from labuse.faisabilite.zonage import ZoneRules


def _rules():
    return ZoneRules(code="Uh", he_m=4.5, emprise_sol_pct=30.0, recul_voirie_m=3.0,
                     recul_limites_sep_m=4.0, stat_logement="1 place / logement", calibree=True,
                     sources={"hauteur": "Art.10", "emprise": "Art.9", "stationnement": "Art.12"})


def _faisa():
    return estimate_capacity(_rules(), 1625.0, Contraintes(), hyp=Hypotheses(),
                             emprise_geo=(927.0, 4.0),
                             extras={"assiette_source": "gabarit", "total_deduit_m2": 0})


class _Ctx:
    def __init__(self):
        self.parcel_id, self.idu, self.commune = 1, "97411000BZ1065", "Saint-Denis"
        self.surface_m2, self.zone = 1625.0, "Uh"
        self.a_cheval, self.zone_parts = False, []
        self.contraintes = Contraintes()


def _residuel(bati=True):
    if not bati:
        return {"disponible": True, "emprise_batie_m2": 0, "sdp_existante_m2": 0,
                "sdp_residuelle_m2": 245, "taux_emprise_pct": 0, "niveaux_existants": 0,
                "hauteur_source": "sans", "sdp_max_m2": 245}
    # LIVE : 26 m² résiduel — DIFFÉRENT du servi (179) pour bien distinguer les deux sources.
    return {"disponible": True, "emprise_batie_m2": 193, "sdp_existante_m2": 219,
            "sdp_residuelle_m2": 26, "taux_emprise_pct": 40, "niveaux_existants": 3,
            "hauteur_source": "lidar", "sdp_max_m2": 245}


class _FakeSession:
    """Rend la SDP SERVIE pour la requête parcel_residuel ; le reste des frontières est monkeypatché."""
    def __init__(self, servie):
        self._servie = servie

    def execute(self, *a, **k):
        servie = self._servie

        class _R:
            def scalar(self):
                return servie
        return _R()


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    f = _faisa()
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda s, pid, hyp_overrides=None: (_Ctx(), f))
    monkeypatch.setattr("labuse.faisabilite.zonage.resolve_zone", lambda code, commune=None: _rules())
    monkeypatch.setattr("labuse.faisabilite.zonage.reglement_source",
                        lambda commune: {"approbation": "05/08/2026", "url": "plu.pdf"})
    monkeypatch.setattr("labuse.plu_reglement.resolve_reglement",
                        lambda commune, zone, idurba=None: {
                            "zone": zone, "calibree": True, "url": "plu.pdf",
                            "url_document": "plu.pdf", "regles_valeurs": []})


def test_bati_garde_hors_saisie_lit_le_servi(monkeypatch):
    """Bâti présent, aucune saisie : bati_garde.sdp_possible == SERVI (179), PAS le live (26)."""
    monkeypatch.setattr("labuse.faisabilite.residuel.compute_residuel",
                        lambda s, pid, faisa=None, assiette_clippee=False: _residuel(bati=True))
    r = scenarios.faisabilite_scenario(_FakeSession(179), 1, "bati_garde")
    assert r["sdp_possible_m2"] == 179, "hors saisie, la SDP résiduelle vient du run servi (parcel_residuel)"


def test_bati_garde_avec_saisie_repasse_au_live(monkeypatch):
    """Avec un override (chiffre saisi) : le moteur LIVE reprend la main → 26, pas le servi 179."""
    monkeypatch.setattr("labuse.faisabilite.residuel.compute_residuel",
                        lambda s, pid, faisa=None, assiette_clippee=False: _residuel(bati=True))
    r = scenarios.faisabilite_scenario(_FakeSession(179), 1, "bati_garde",
                                       hyp_overrides={"coef_occupation": 0.9})
    assert r["sdp_possible_m2"] == 26, "avec saisie, le moteur live recalcule (pas le servi)"


def test_terrain_nu_hors_saisie_lit_le_servi(monkeypatch):
    """Terrain NU, aucune saisie : terrain_libere EST le résiduel → SDP SERVIE (1619), pas l'enveloppe live."""
    monkeypatch.setattr("labuse.faisabilite.residuel.compute_residuel",
                        lambda s, pid, faisa=None, assiette_clippee=False: _residuel(bati=False))
    r = scenarios.faisabilite_scenario(_FakeSession(1619), 1, "terrain_libere")
    assert r["sdp_possible_m2"] == 1619, "terrain nu hors saisie : la SDP servie fait foi"


def test_repli_live_quand_pas_de_residuel_servi(monkeypatch):
    """Chaîne résiduel absente (SDP servie None) : on garde le calcul live (aucune régression base test)."""
    monkeypatch.setattr("labuse.faisabilite.residuel.compute_residuel",
                        lambda s, pid, faisa=None, assiette_clippee=False: _residuel(bati=True))
    r = scenarios.faisabilite_scenario(_FakeSession(None), 1, "bati_garde")
    assert r["sdp_possible_m2"] == 26, "sans SDP servie, repli sur le live"
