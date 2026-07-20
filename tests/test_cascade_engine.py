"""PHASE 0 « Le Juge » — J1.a : le MOTEUR de cascade (`run_cascade` / `is_promoted`).

Test PUR (aucune base) : couches RÉELLES enregistrées — `foncier_public` (phase 1, exclusion dure)
et `potentiel_foncier_region` (phase 2) — pilotées par un `EvalContext` factice. On verrouille la
règle §4 : seule une SURVIVANTE de l'étage 0 (aucun HARD_EXCLUDE en phase 1) est promue en phase 2.
"""
from __future__ import annotations

from labuse.cascade.base import hard_exclude, passed
from labuse.cascade.context import ParcelRef
from labuse.cascade.engine import is_promoted, run_cascade
from labuse.enums import CascadeVerdict

_RULES = {"layers": [
    {"name": "foncier_public", "phase": 1, "enabled": True, "params": {}},
    {"name": "potentiel_foncier_region", "phase": 2, "enabled": True,
     "params": {"spatial_kind": "potentiel_foncier"}},
]}


class _Ctx:
    """EvalContext factice : `owner_pm` public pour les ids listés (→ HARD_EXCLUDE foncier_public),
    `kind_present` False → potentiel_foncier_region PASS (pas d'exclusion, juste un verdict phase 2)."""

    def __init__(self, public_ids):
        self.rules = _RULES
        self._public = set(public_ids)

    def owner_pm(self, pid):
        return ({"groupe": 4, "denomination": "COMMUNE", "groupe_label": "Commune"}
                if pid in self._public else None)

    def kind_present(self, kind):
        return False

    def intersections(self, pid, kind):
        return []


def _v(verdicts, layer):
    return next((x for x in verdicts if x.layer_name == layer), None)


def test_hard_exclude_phase1_coupe_la_phase2():
    p_excl = ParcelRef(id=1, idu="A", commune="X")
    p_surv = ParcelRef(id=2, idu="B", commune="X")
    res = run_cascade([p_excl, p_surv], _Ctx(public_ids={1}))
    # EXCLUE : HARD_EXCLUDE en phase 1, AUCUNE couche phase 2 évaluée, non promue.
    assert _v(res[1], "foncier_public").result == CascadeVerdict.HARD_EXCLUDE
    assert _v(res[1], "potentiel_foncier_region") is None
    assert is_promoted(res[1]) is False
    # SURVIVANTE : phase 1 PASS, phase 2 (potentiel) bien évaluée, promue.
    assert _v(res[2], "foncier_public").result == CascadeVerdict.PASS
    assert _v(res[2], "potentiel_foncier_region") is not None
    assert is_promoted(res[2]) is True


def test_is_promoted_sur_verdicts_mixtes():
    assert is_promoted([passed("a"), passed("b")]) is True
    assert is_promoted([passed("a"), hard_exclude("b", "motif")]) is False
    assert is_promoted([]) is True   # aucun verdict = aucune exclusion → promue


def test_phases_1_seule_ne_lance_jamais_la_phase2():
    p = ParcelRef(id=3, idu="C", commune="X")
    res = run_cascade([p], _Ctx(public_ids=set()), phases=(1,))
    assert _v(res[3], "foncier_public").result == CascadeVerdict.PASS
    assert _v(res[3], "potentiel_foncier_region") is None   # phase 2 non demandée
