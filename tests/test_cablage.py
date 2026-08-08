"""M-B — garde de câblage scoring (bloquante). Vérifie les 4 invariants + le comportement INFO→0.

Pas de DB pour les invariants statiques (config/registry) ; la vérif des kinds spatiaux est testée
via une session factice (sans seed lourd). Chaque refus doit NOMMER le fautif."""
from __future__ import annotations

import copy

import pytest

from labuse.cascade import cablage
from labuse.cascade.base import REGISTRY, soft_flag
from labuse.cascade.cablage import CablageError, check_cablage_scoring
from labuse.enums import Severity
from labuse.scoring.opportunity import compute_opportunity


def test_cablage_actuel_passe():
    """Validation #4 : le câblage ACTUEL passe la garde (statique)."""
    out = check_cablage_scoring()
    assert out["layers"] == "OK" and out["severites"] == "OK" and out["bonus_keys"] == "OK"


def test_couche_registry_retiree_refuse(monkeypatch):
    """Validation #1 : couche retirée du registry (pas du YAML) → refus, NOM dans le message."""
    monkeypatch.delitem(REGISTRY, "friche")   # restauré en fin de test
    with pytest.raises(CablageError) as e:
        check_cablage_scoring()
    msg = str(e.value)
    assert "friche" in msg and "ABSENTE du registry" in msg


def test_couche_yaml_manquante_refuse(monkeypatch):
    """Réciproque : couche implémentée mais absente du YAML → refus nommant la couche."""
    rules = copy.deepcopy(cablage.cascade_rules())
    rules["layers"] = [l for l in rules["layers"] if l.get("name") != "friche"]
    monkeypatch.setattr(cablage, "cascade_rules", lambda: rules)
    with pytest.raises(CablageError) as e:
        check_cablage_scoring()
    assert "friche" in str(e.value) and "NON déclarée" in str(e.value)


def test_severite_inconnue_refuse(monkeypatch):
    """Validation #2 : sévérité inconnue déclarée au YAML → refus, NOM dans le message."""
    rules = copy.deepcopy(cablage.cascade_rules())
    rules["layers"].append({"name": "eau", "phase": 1, "params": {"severity": "catastrophique"}})
    monkeypatch.setattr(cablage, "cascade_rules", lambda: rules)
    with pytest.raises(CablageError) as e:
        check_cablage_scoring()
    assert "catastrophique" in str(e.value)


def test_severite_enum_sans_multiplicateur_refuse(monkeypatch):
    """Une sévérité de l'enum sans multiplicateur en config → refus (vaudrait ×1 par défaut)."""
    w = copy.deepcopy(cablage.opportunity_weights())
    del w["severity_multipliers"]["moyen"]
    monkeypatch.setattr(cablage, "opportunity_weights", lambda: w)
    with pytest.raises(CablageError) as e:
        check_cablage_scoring()
    assert "moyen" in str(e.value)


def test_info_doit_valoir_zero(monkeypatch):
    """info != 0 en config → refus : une sévérité à zéro n'est pas une sévérité ignorée."""
    w = copy.deepcopy(cablage.opportunity_weights())
    w["severity_multipliers"]["info"] = 2
    monkeypatch.setattr(cablage, "opportunity_weights", lambda: w)
    with pytest.raises(CablageError) as e:
        check_cablage_scoring()
    assert "info" in str(e.value)


def test_bonus_key_inexistante_refuse(monkeypatch):
    """Clé de bonus utilisée mais absente de la config → refus, NOM dans le message."""
    rules = copy.deepcopy(cablage.cascade_rules())
    rules["layers"].append({"name": "eau", "phase": 1, "params": {"bonus_key": "bonus_fantome"}})
    monkeypatch.setattr(cablage, "cascade_rules", lambda: rules)
    with pytest.raises(CablageError) as e:
        check_cablage_scoring()
    assert "bonus_fantome" in str(e.value)


def test_info_contribue_exactement_zero():
    """Validation #3 : une couche de sévérité INFO contribue EXACTEMENT 0 (traitée, pas ignorée)."""
    base = compute_opportunity([]).score                              # 50
    r_info = compute_opportunity([soft_flag("mvt", "aléa déjà en PPR", Severity.INFO)])
    assert r_info.score == base                                       # 0 point
    assert r_info.weights == [0.0]                                    # traité (poids présent) = 0
    r_moyen = compute_opportunity([soft_flag("x", "y", Severity.MOYEN)])
    assert r_moyen.score < base and r_moyen.weights != [0.0]          # moyen pénalise (≠ info)


# ── kinds spatiaux (P2-30) — session factice, sans seed lourd ─────────────────────────────

class _FakeSession:
    def __init__(self, kinds):
        self._kinds = kinds

    def execute(self, *a, **k):
        return [(x,) for x in self._kinds]


def test_spatial_kind_absent_refuse():
    """Base peuplée (un kind présent) mais un kind référencé manque → refus nommant le kind."""
    with pytest.raises(CablageError) as e:
        check_cablage_scoring(session=_FakeSession({"water"}))   # seul 'water' présent
    assert "spatial_kind" in str(e.value)


def test_spatial_kind_base_vide_toleree():
    """Base sans aucune couche cascade → tolérée (pas un défaut de câblage, mais un non-ingéré)."""
    out = check_cablage_scoring(session=_FakeSession(set()))
    assert out["spatial_kinds"] == "OK"
