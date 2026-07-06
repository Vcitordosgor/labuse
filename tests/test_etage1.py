"""Couches ÉTAGE 1 (dry-run) — friche, sol_pollue/cavite/icpe/mvt, aménités.

Tests unitaires via ctx factice (sans géométrie/pyproj) : magnitude, sévérité graduée, mvt=0 point,
formule aménités, et source_table/source_id (cliquable) sur chaque verdict.
"""
from __future__ import annotations

from labuse.cascade.context import Intersection
from labuse.cascade.layers.etage1 import (
    AmenitesLayer,
    CaviteLayer,
    FricheLayer,
    IcpeLayer,
    MvtLayer,
    SolPollueLayer,
)
from labuse.enums import CascadeVerdict, Severity


class _Ctx:
    def __init__(self, present=True, inter=None, nearest=None, amenites=None):
        self._present, self._inter, self._nearest, self._am = present, inter or [], nearest, amenites

    def kind_present(self, kind):
        return self._present

    def intersections(self, pid, kind):
        return self._inter

    def nearest_point(self, pid, kind):
        return self._nearest

    def amenites(self, pid):
        return self._am


class _P:
    id = 7


P = {"spatial_kind": "friche", "bonus_key": "friche",
     "magnitude_avec_projet": 1.0, "magnitude_sans_projet": 0.6}


def test_friche_avec_projet():
    i = Intersection("friche avec projet", "FRICHE DE SAVANNA", 0.5, {}, "Cerema", id=42)
    v = FricheLayer().evaluate(_P(), _Ctx(inter=[i]), P)
    assert v.result == CascadeVerdict.POSITIVE and v.magnitude == 1.0
    assert v.extra == {"source_table": "spatial_layers", "source_id": 42}   # cliquable


def test_friche_sans_projet_magnitude_reduite():
    i = Intersection("friche sans projet", "X", 0.9, {}, "Cerema", id=43)
    v = FricheLayer().evaluate(_P(), _Ctx(inter=[i]), P)
    assert v.magnitude == 0.6


def test_icpe_severite_graduee():
    params = {"spatial_kind": "icpe", "bandes_m": {"fort": 50, "moyen": 150, "faible": 300},
              "detail": "ICPE"}
    for dist, sev in [(30, Severity.FORT), (100, Severity.MOYEN), (250, Severity.FAIBLE)]:
        v = IcpeLayer().evaluate(_P(), _Ctx(nearest={"dist": dist, "id": 9, "name": "Usine"}), params)
        assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == sev
        assert v.extra["source_id"] == 9


def test_mvt_est_info_zero_point():
    params = {"spatial_kind": "mvt", "proximite_m": 50, "severity": "info", "detail": "mvt"}
    v = MvtLayer().evaluate(_P(), _Ctx(nearest={"dist": 20, "id": 5, "name": "Coulée"}), params)
    assert v.severity == Severity.INFO       # multiplicateur ×0 → flag affiché, 0 point


def test_sol_pollue_flag_faible_avec_source():
    params = {"spatial_kind": "sol_pollue", "proximite_m": 50, "severity": "faible", "detail": "pollution"}
    v = SolPollueLayer().evaluate(_P(), _Ctx(nearest={"dist": 30, "id": 11, "name": "Sucrerie"}), params)
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.FAIBLE
    assert v.extra["source_table"] == "spatial_layers" and v.extra["source_id"] == 11


def test_cavite_absente_pass():
    params = {"spatial_kind": "cavite", "proximite_m": 50, "severity": "faible", "detail": "x"}
    v = CaviteLayer().evaluate(_P(), _Ctx(nearest=None), params)
    assert v.result == CascadeVerdict.PASS


AM_PARAMS = {"bonus_key": "amenites",
             "bandes_defaut_m": {"plein": 500, "demi": 1200}, "bandes_tcsp_m": {"plein": 300, "demi": 800},
             "ponderations": {"ecole": 0.30, "commerce": 0.30, "sante": 0.20, "tcsp": 0.20}}


def test_amenites_tout_proche_magnitude_1():
    am = {"dist_ecole_m": 100, "dist_commerce_m": 200, "dist_sante_m": 150, "dist_tcsp_m": 80}
    v = AmenitesLayer().evaluate(_P(), _Ctx(amenites=am), AM_PARAMS)
    assert abs(v.magnitude - 1.0) < 1e-9          # tout ≤ bande pleine → 11 pts
    assert v.extra == {"source_table": "parcel_amenites", "source_id": 7}


def test_amenites_bandes_intermediaires_et_manquant():
    # école 700m (0.5) · commerce 1500m (0) · santé None (0) · tcsp 500m (0.5, bande tcsp 300/800)
    am = {"dist_ecole_m": 700, "dist_commerce_m": 1500, "dist_sante_m": None, "dist_tcsp_m": 500}
    v = AmenitesLayer().evaluate(_P(), _Ctx(amenites=am), AM_PARAMS)
    assert abs(v.magnitude - (0.30 * 0.5 + 0.20 * 0.5)) < 1e-9   # 0.25


def test_amenites_non_calcule_unknown():
    v = AmenitesLayer().evaluate(_P(), _Ctx(amenites=None), AM_PARAMS)
    assert v.result == CascadeVerdict.UNKNOWN
