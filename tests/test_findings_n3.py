"""NUIT N3 — findings F8 (libellé eau par branche), F10 (wording DGFiP groupe 9), F9 (non comparable).

Tests PURS (F8/F10 : couches avec ctx stub ; F9 : geo_recheck avec session stub). Aucune écriture ; les
verdicts déjà matérialisés dans les runs ne bougent pas (code seul).
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.etage0_ext import FoncierPublicLayer
from labuse.cascade.layers.phase1 import EauLayer
from labuse.enums import CascadeVerdict

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)


# ───────────────────────── F8 : deux libellés eau selon la branche ─────────────────────────

class _CtxEau:
    def __init__(self, inter, centroid):
        self._i, self._c = inter, centroid

    def intersections(self, _pid, _kind):
        return self._i

    def centroid_in(self, _pid, _kind):
        return self._c


def test_f8_branche_centroide():
    v = EauLayer().evaluate(P, _CtxEau([], True), {"spatial_kind": "eau"})
    assert v.result == CascadeVerdict.HARD_EXCLUDE
    assert "centroïde dans l'hydrographie" in v.detail
    assert "recouvrement" not in v.detail


def test_f8_branche_recouvrement():
    v = EauLayer().evaluate(P, _CtxEau([Intersection("water", None, 0.7, {}, None)], False), {"spatial_kind": "eau"})
    assert v.result == CascadeVerdict.HARD_EXCLUDE
    assert "majoritairement sur l'eau (70 % de recouvrement)" in v.detail


# ───────────────────────── F10 : wording DGFiP groupe 9 vs 1-4 ─────────────────────────

class _CtxOwn:
    def __init__(self, own):
        self._o = own

    def owner_pm(self, _pid):
        return self._o


def test_f10_groupe9_institutionnel_hors_marche():
    v = FoncierPublicLayer().evaluate(P, _CtxOwn({"groupe": 9, "denomination": "TERRACOOP", "groupe_label": "Étab public"}), {})
    assert v.result == CascadeVerdict.HARD_EXCLUDE                 # exclusion HARD inchangée
    assert "Propriétaire institutionnel" in v.detail and "acquisition improbable" in v.detail
    assert "Propriété publique" not in v.detail and "non acquérable" not in v.detail


def test_f10_groupe4_reste_propriete_publique():
    v = FoncierPublicLayer().evaluate(P, _CtxOwn({"groupe": 4, "denomination": "Commune X", "groupe_label": "Commune"}), {})
    assert v.result == CascadeVerdict.HARD_EXCLUDE
    assert "Propriété publique" in v.detail and "non acquérable" in v.detail


# ───────────────────────── F9 : « non comparable » (pente °/%, eau aire/centroïde) ─────────────────────────

def _load_revue():
    spec = importlib.util.spec_from_file_location(
        "j3_revue_dossier", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "j3_revue_dossier.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Sess:
    def execute(self, *_a, **_k):
        class _R:
            def first(self_inner):
                return None
        return _R()


@pytest.mark.parametrize("motif", ["pente", "eau"])
def test_f9_non_comparable(motif):
    mod = _load_revue()
    txt, concorde = mod.geo_recheck(_Sess(), 1, motif)
    assert concorde is None                                        # jamais un vert
    assert "non comparable" in txt and "métriques différentes" in txt
