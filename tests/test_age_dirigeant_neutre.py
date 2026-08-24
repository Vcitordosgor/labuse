"""FIX-AGE-DIRIGEANT (décision Vic, I4) — l'âge du dirigeant N'ENTRE PLUS dans le score.

La cascade s'aligne sur le Score V : la couche `age_dirigeant` ne produit plus de `positive`
(0 point), mais garde une LIGNE de contexte visible et honnêtement étiquetée. Sans DB : on éprouve
la couche avec un contexte factice + la config, pas la cascade complète.
"""
from __future__ import annotations

from labuse.cascade.layers.etage2 import AgeDirigeantLayer
from labuse.config import load_yaml_config, opportunity_weights
from labuse.enums import CascadeVerdict

_PARAMS = {"bonus_key": "age_dirigeant", "courbe": {55: 0, 65: 0, 75: 0, 85: 0}, "age_min_valide": 18}


class _Parcel:
    id = 1


class _Ctx:
    def __init__(self, age):
        self._age = age
    def propension(self, _pid):
        return {"age_max_dirigeant": self._age, "siren": "123456789"} if self._age is not None else None


def _ev(age):
    return AgeDirigeantLayer().evaluate(_Parcel(), _Ctx(age), _PARAMS)


def test_dirigeant_age_ne_rapporte_aucun_point():
    """Le cas cœur : un dirigeant âgé produit une ligne de CONTEXTE (flag INFO), PAS un bonus."""
    v = _ev(72)
    assert v.result == CascadeVerdict.SOFT_FLAG      # flag de contexte, jamais POSITIVE
    assert v.bonus_key is None                        # aucune clé de bonus → aucun point
    assert v.magnitude in (0.0, 1.0)                  # pas de magnitude de bonus attribuée
    assert "score" in v.detail.lower()                # le libellé DIT qu'elle n'entre pas dans le score


def test_dirigeant_age_reste_visible_et_source():
    """L'information reste renseignée (ligne servie, source tracée) — pas effacée."""
    v = _ev(80)
    assert v.detail                                   # une ligne existe
    assert v.data_source_name                          # source INPI présente
    assert v.extra.get("source_table") == "v_foncier_propension_vendre"


def test_dirigeant_jeune_passe_zero_point():
    v = _ev(40)
    assert v.result == CascadeVerdict.PASS
    assert v.bonus_key is None


def test_age_absent_reste_unknown():
    """Absence = complétude (comme avant) : on n'invente rien, on ne score rien."""
    assert _ev(None).result == CascadeVerdict.UNKNOWN


def test_age_incoherent_reste_unknown():
    assert _ev(5).result == CascadeVerdict.UNKNOWN


def test_poids_config_age_dirigeant_est_zero():
    """Le poids ET la courbe sont à 0 : aucun point attribué à l'âge, nulle part."""
    assert opportunity_weights()["bonuses"]["age_dirigeant"] == 0
    rules = load_yaml_config("cascade_rules")["layers"]
    rule = next(r for r in rules if r["name"] == "age_dirigeant")
    assert all(int(v) == 0 for v in rule["params"]["courbe"].values())


def test_aucune_autre_porte_ne_score_l_age():
    """Point 4 du mandat : une SEULE règle porte bonus_key=age_dirigeant, et son poids config = 0 —
    aucune autre porte (dérivé, autre couche) ne peut réintroduire des points par l'âge."""
    rules = load_yaml_config("cascade_rules")["layers"]
    porteurs = [r["name"] for r in rules if (r.get("params") or {}).get("bonus_key") == "age_dirigeant"]
    assert porteurs == ["age_dirigeant"]                          # une seule règle
    assert opportunity_weights()["bonuses"]["age_dirigeant"] == 0  # et elle vaut 0
