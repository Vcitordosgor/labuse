"""ÉTAGE 0 — filtre dur (refonte scoring, session 1).

Verrouille la FUSION du déclassement franc dans la cascade phase 1 : les bloquants FRANCS
(micro-parcelle, pente non aménageable, équipement OSM dominant, déjà bâti franc) produisent
désormais un HARD_EXCLUDE `faux_positif` EN PHASE 1 — plus un statut corrigé en aval. Une
parcelle éliminée n'a donc plus de score fantôme (compute_opportunity renvoie 0).

Tests PURS (aucune DB) : les couches concernées ne lisent que `parcel`, `params` (YAML réel)
et un contexte spatial minimal simulé. Le comportement de bout en bout (promotion, invariant
« aucun HARD_EXCLUDE en aval ») est verrouillé côté DB dans test_cascade.py.
"""
from __future__ import annotations

import labuse.cascade  # noqa: F401  (effet de bord : enregistre les couches)
from labuse import config
from labuse.cascade.base import REGISTRY
from labuse.cascade.context import Intersection, ParcelRef
from labuse.enums import CascadeVerdict


def _params(name: str) -> dict:
    for lc in config.cascade_rules()["layers"]:
        if lc.get("name") == name:
            return lc.get("params", {}) or {}
    raise KeyError(name)


class FakeCtx:
    """Contexte spatial minimal — juste ce que lisent les couches phase 1 testées ici."""

    def __init__(self, inter=None, present=None, declass_signals=None):
        self._inter = inter or {}          # {(pid, kind): [Intersection]}
        self._present = set(present or ())
        self.declass_signals = declass_signals or {}

    def kind_present(self, kind):
        return kind in self._present

    def intersections(self, pid, kind):
        return self._inter.get((pid, kind), [])


def _parcel(surface_m2=2000.0, pid=1):
    return ParcelRef(id=pid, idu="97415000AA0001", commune="Saint-Paul", surface_m2=surface_m2)


def _inter(kind, coverage, subtype=None, attrs=None, pid=1):
    return {(pid, kind): [Intersection(subtype, None, coverage, attrs or {}, None)]}


# ───────────────────────── surface (micro-parcelle) ─────────────────────────

def test_surface_micro_parcelle_eliminee_phase1():
    v = REGISTRY["surface"].evaluate(_parcel(surface_m2=28), FakeCtx(), _params("surface"))
    assert v.is_hard_exclude() and v.exclude_kind == "faux_positif"
    assert "28" in v.detail and "micro" in v.detail.lower()


def test_surface_dans_la_bande_non_eliminee():
    # 180 m² (< seuil « à creuser » 250 mais > seuil franc 100) : NON éliminée en phase 1
    # (c'est un flag qualité du déclassement, étage 1) → jamais un HARD_EXCLUDE.
    v = REGISTRY["surface"].evaluate(_parcel(surface_m2=180), FakeCtx(), _params("surface"))
    assert not v.is_hard_exclude()


def test_surface_normale_non_eliminee():
    v = REGISTRY["surface"].evaluate(_parcel(surface_m2=2000), FakeCtx(), _params("surface"))
    assert not v.is_hard_exclude()


# ───────────────────────── pente ─────────────────────────

def test_pente_non_amenageable_eliminee_phase1():
    ctx = FakeCtx(inter=_inter("pente", 1.0, attrs={"slope_pct": 94}), present={"pente"})
    v = REGISTRY["pente"].evaluate(_parcel(), ctx, _params("pente"))
    assert v.is_hard_exclude() and v.exclude_kind == "faux_positif" and "94" in v.detail


def test_pente_forte_mais_amenageable_non_eliminee():
    # 45 % : au-dessus du seuil de flag (30) mais sous le seuil franc (60) → SOFT_FLAG, pas exclusion.
    ctx = FakeCtx(inter=_inter("pente", 1.0, attrs={"slope_pct": 45}), present={"pente"})
    v = REGISTRY["pente"].evaluate(_parcel(), ctx, _params("pente"))
    assert not v.is_hard_exclude() and v.result == CascadeVerdict.SOFT_FLAG


# ───────────────────────── OSM (équipement dominant) ─────────────────────────

def test_osm_equipement_dominant_elimine_phase1():
    ctx = FakeCtx(inter=_inter("osm_faux_positif", 0.82, subtype="parking"))
    v = REGISTRY["osm_faux_positif"].evaluate(_parcel(), ctx, _params("osm_faux_positif"))
    assert v.is_hard_exclude() and v.exclude_kind == "faux_positif"
    assert "parking" in v.detail and "82" in v.detail


def test_osm_recouvrement_partiel_non_elimine():
    # parking sur 40 % : au-dessus du seuil de flag (0.30) mais sous le seuil franc (0.50)
    # → SOFT_FLAG (le « à creuser » du déclassement est porté en aval), jamais une exclusion.
    ctx = FakeCtx(inter=_inter("osm_faux_positif", 0.40, subtype="parking"))
    v = REGISTRY["osm_faux_positif"].evaluate(_parcel(), ctx, _params("osm_faux_positif"))
    assert not v.is_hard_exclude()


def test_osm_effleurement_de_bord_passe():
    ctx = FakeCtx(inter=_inter("osm_faux_positif", 0.07, subtype="pitch"))
    v = REGISTRY["osm_faux_positif"].evaluate(_parcel(surface_m2=11420), ctx, _params("osm_faux_positif"))
    assert v.result == CascadeVerdict.PASS


# ───────────────────────── bâti franc (correctif R1) ─────────────────────────

def test_bati_ensemble_bati_elimine_phase1():
    # Cas BP0571 : 18 % / 4 bâtiments / max 418 m² → « ensemble bâti » (franc) → éliminé.
    sig = {1: {"bati_ratio": 0.18, "bati_count": 4, "bati_max_m2": 418.0, "surface_m2": 9222.0}}
    v = REGISTRY["bati"].evaluate(_parcel(surface_m2=9222.0), FakeCtx(declass_signals=sig), _params("bati"))
    assert v.is_hard_exclude() and v.exclude_kind == "faux_positif" and "ensemble bâti" in v.detail


def test_bati_deja_bati_elimine_phase1():
    sig = {1: {"bati_ratio": 0.55, "bati_count": 6, "bati_max_m2": 400.0, "surface_m2": 5000.0}}
    v = REGISTRY["bati"].evaluate(_parcel(surface_m2=5000.0), FakeCtx(declass_signals=sig), _params("bati"))
    assert v.is_hard_exclude() and "déjà bâtie" in v.detail


def test_bati_partiellement_bati_non_elimine():
    # 20 % : « à creuser » (non-franc) → PASS en phase 1 (le flag est porté par le déclassement).
    sig = {1: {"bati_ratio": 0.20, "bati_count": 1, "bati_max_m2": 150.0, "surface_m2": 1000.0}}
    v = REGISTRY["bati"].evaluate(_parcel(surface_m2=1000.0), FakeCtx(declass_signals=sig), _params("bati"))
    assert v.result == CascadeVerdict.PASS


def test_bati_couche_absente_unknown():
    # Aucun signal bâti (couche batiment non ingérée) → UNKNOWN, jamais un faux « vacant » éliminant.
    v = REGISTRY["bati"].evaluate(_parcel(), FakeCtx(declass_signals={}), _params("bati"))
    assert v.result == CascadeVerdict.UNKNOWN
