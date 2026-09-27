"""FAISABILITE-3 (Vic 27/09/2026) — LE moteur sert les deux scénarios (Lot A).

Cœur PUR : on exerce le vrai moteur (`estimate_capacity` + les champs de fourchette ajoutés) et
l'assemblage `faisabilite_scenario`, en stubbant les frontières base (parcel_faisabilite,
compute_residuel, resolve_zone, reglement_source, resolve_reglement). Aucun réseau.
"""
from __future__ import annotations

import pytest

from labuse.faisabilite import scenarios
from labuse.faisabilite.engine import Contraintes, Hypotheses, estimate_capacity
from labuse.faisabilite.zonage import ZoneRules


def _rules_uh():
    """Uh calibrée : hé 4,5 m, CES 30 %, reculs 3 m / 4 m, 1 place/logt — comme le témoin BZ1065."""
    return ZoneRules(
        code="Uh", he_m=4.5, emprise_sol_pct=30.0, recul_voirie_m=3.0, recul_limites_sep_m=4.0,
        stat_logement="1 place / logement", calibree=True,
        sources={"hauteur": "Art. Uh.10 · p.73", "emprise": "Art. Uh.9 · p.72",
                 "recul_voirie": "Art. Uh.6 · p.70", "recul_limites": "Art. Uh.7 · p.71",
                 "stationnement": "Art. XVII · p.120"})


def _faisa(rules=None, surface=1625.0, emprise_geo=(927.0, 4.0)):
    rules = rules or _rules_uh()
    return estimate_capacity(rules, surface, Contraintes(), hyp=Hypotheses(),
                             emprise_geo=emprise_geo,
                             extras={"assiette_source": "gabarit", "total_deduit_m2": 0})


class _Ctx:
    def __init__(self, zone="Uh", a_cheval=False, parts=None):
        self.parcel_id, self.idu, self.commune = 1, "97411000BZ1065", "Saint-Denis"
        self.surface_m2, self.zone = 1625.0, zone
        self.a_cheval, self.zone_parts = a_cheval, parts or []
        self.contraintes = Contraintes()


def _residuel(dispo=True, emprise_batie=193, sdp_existante=219, sdp_residuelle=26, taux=40,
              niveaux=3, source="lidar"):
    if not dispo:
        return {"disponible": False}
    return {"disponible": True, "emprise_batie_m2": emprise_batie, "sdp_existante_m2": sdp_existante,
            "sdp_residuelle_m2": sdp_residuelle, "taux_emprise_pct": taux,
            "niveaux_existants": niveaux, "hauteur_source": source, "sdp_max_m2": 245}


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    """Frontières base neutralisées ; par défaut : Uh constructible + bâti présent (26 m² résiduel)."""
    f = _faisa()
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda s, pid, hyp_overrides=None: (_Ctx(), f))
    monkeypatch.setattr("labuse.faisabilite.residuel.compute_residuel",
                        lambda s, pid, faisa=None, assiette_clippee=False: _residuel())
    monkeypatch.setattr("labuse.faisabilite.zonage.resolve_zone",
                        lambda code, commune=None: _rules_uh())
    monkeypatch.setattr("labuse.faisabilite.zonage.reglement_source",
                        lambda commune: {"approbation": "05/08/2026", "url": "plu.pdf"})
    monkeypatch.setattr("labuse.plu_reglement.resolve_reglement",
                        lambda commune, zone, idurba=None: {
                            "zone": zone, "calibree": True, "url": "plu.pdf#page=73",
                            "url_document": "plu.pdf", "approbation": "05/08/2026",
                            "regles_valeurs": [{"cle": "hauteur", "libelle": "Hauteur max",
                                                "valeur": "7 m au faîtage · 4.5 m à l'égout",
                                                "etat": "chiffre", "reference": "Art. Uh.10 · p.73",
                                                "url": "plu.pdf#page=73"}]})


# ── L'ENGINE : les deux champs de fourchette ajoutés (étapes 1 & 2 de la maquette) ──
def test_fourchette_expose_zone_implantation_et_emprise_max():
    fr = _faisa().fourchette
    assert fr["zone_implantation_m2"] == 927                 # assiette après reculs (avant CES)
    assert fr["emprise_sol_max_m2"] == round(1625 * 0.30)    # surface × CES 30 % = 488
    assert fr["surface_plancher_m2"] > 0


# ── LES DEUX SCÉNARIOS ──
def test_terrain_libere_enveloppe_pleine_et_demolition():
    r = scenarios.faisabilite_scenario(None, 1, "terrain_libere")
    assert r["scenario"] == "terrain_libere" and r["constructible"]
    assert r["sdp_possible_m2"] == _faisa().fourchette["surface_plancher_m2"]   # enveloppe pleine
    assert r["surface_a_demolir_m2"] == 219                  # emprise bâtie × niveaux LiDAR (sdp existante)
    e5 = next(e for e in r["etapes"] if e["n"] == 5)
    assert "démolition" in e5["valeur"] and "0 m²" in e5["valeur"]
    assert len(r["etapes"]) == 8


def test_bati_garde_egale_le_residuel_servi():
    """Golden 55 (invariant) : bati_garde.sdp_possible == compute_residuel(clip).sdp_residuelle."""
    r = scenarios.faisabilite_scenario(None, 1, "bati_garde")
    assert r["scenario"] == "bati_garde"
    assert r["sdp_possible_m2"] == 26                        # == résiduel servi
    assert r["surface_a_demolir_m2"] is None                 # bâti conservé
    e5 = next(e for e in r["etapes"] if e["n"] == 5)
    assert "conservés" in e5["valeur"]


def test_bati_garde_jamais_plus_de_logements_que_terrain_libere():
    tl = scenarios.faisabilite_scenario(None, 1, "terrain_libere")
    bg = scenarios.faisabilite_scenario(None, 1, "bati_garde")
    assert max(bg["logements"]) <= max(tl["logements"])


# ── PARCELLE NUE : un seul scénario ──
def test_parcelle_nue_un_seul_scenario(monkeypatch):
    monkeypatch.setattr("labuse.faisabilite.residuel.compute_residuel",
                        lambda s, pid, faisa=None, assiette_clippee=False:
                        _residuel(emprise_batie=0, taux=0, sdp_residuelle=0))
    r = scenarios.faisabilite_scenario(None, 1, "bati_garde")   # demande bâti gardé…
    assert r["bati_present"] is False
    assert r["scenario"] == "terrain_libere"                    # …retombe sur l'unique scénario


# ── HABITAT INTERDIT : message + citation, jamais un chiffre ──
def test_habitat_interdit_message(monkeypatch):
    rules = ZoneRules(code="UE", he_m=9.0, habitat="interdit", calibree=True)
    f = estimate_capacity(rules, 1000.0, Contraintes(), hyp=Hypotheses(), emprise_geo=(600.0, 4.0))
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda s, pid, hyp_overrides=None: (_Ctx(zone="UE"), f))
    r = scenarios.faisabilite_scenario(None, 1, "terrain_libere",
                                       test={"n_logements": 2, "surface_par_logement": 90})
    assert r["logement_autorise"] is False and r["sdp_possible_m2"] == 0
    assert "interdit" in r["ce_qui_limite"].lower()
    assert r["test"]["statut"] == "non_autorise"


# ── AU NON OUVERTE : 0 partout, motif ──
def test_au_non_ouverte(monkeypatch):
    rules = ZoneRules(code="2AU", constructible_neuf=False, calibree=True)
    f = estimate_capacity(rules, 1000.0, Contraintes(), hyp=Hypotheses())
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda s, pid, hyp_overrides=None: (_Ctx(zone="2AU"), f))
    r = scenarios.faisabilite_scenario(None, 1, "terrain_libere")
    assert r["sdp_possible_m2"] == 0 and r["logements"] == [0, 0]
    assert "AU non ouverte" in r["ce_qui_limite"]


# ── À CHEVAL : la portion constructible est renvoyée ──
def test_a_cheval_portion(monkeypatch):
    parts = [{"zone": "U6c", "fam": "U", "pct": 72.0}, {"zone": "N", "fam": "N", "pct": 28.0}]
    f = _faisa()
    monkeypatch.setattr("labuse.faisabilite.db.parcel_faisabilite",
                        lambda s, pid, hyp_overrides=None: (_Ctx(zone="U6c", a_cheval=True, parts=parts), f))
    r = scenarios.faisabilite_scenario(None, 1, "terrain_libere")
    assert r["a_cheval"] and r["portion_zone"] == "U6c"
    assert r["portion_constructible_m2"] == round(1625 * 0.72)
    assert "U6c" in r["verdict"]


# ── TESTER UN PROJET : champs vides → à compléter ; tient / ne tient pas ──
def test_tester_champs_vides_a_completer():
    r = scenarios.faisabilite_scenario(None, 1, "terrain_libere",
                                       test={"n_logements": None, "surface_par_logement": None})
    assert r["test"]["statut"] == "a_completer"


def test_tester_tient_et_ne_tient_pas():
    tient = scenarios.faisabilite_scenario(None, 1, "terrain_libere",
                                           test={"n_logements": 1, "surface_par_logement": 50})
    assert tient["test"]["statut"] == "tient"
    # bâti gardé (26 m² possibles) : 2 × 90 = 180 m² ne tient pas
    ntp = scenarios.faisabilite_scenario(None, 1, "bati_garde",
                                         test={"n_logements": 2, "surface_par_logement": 90})
    assert ntp["test"]["statut"] == "ne_tient_pas" and ntp["test"]["manque_m2"] == 180 - 26


# ── GARDE « défaut ≠ PLU » : l'occupation par défaut ≤ 100 %, jamais 100 % ──
def test_garde_occupation_defaut_pas_100pct():
    h = Hypotheses()
    assert 0 < h.coef_occupation <= 1.0
    assert h.coef_occupation != 1.0            # ne remplit jamais 100 % de l'emprise max
    assert 0 < h.coef_rendement <= 1.0
