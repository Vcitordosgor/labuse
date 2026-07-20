"""PHASE 0 « Le Juge » — J1.a : couches PHASE 2 (SITADEL, propriétaire, DVF).

Tests PURS (ctx stubé). SITADEL : la distinction « RATTACHÉ par IDU » vs « SIGNAL DE ZONE »
(le marqueur lu ensuite par `dryrun.compute_matrice`) produit bien DEUX verdicts distincts.
Propriétaire & DVF : cas nominal + cas données absentes.
"""
from __future__ import annotations

from labuse.cascade.context import ParcelRef
from labuse.cascade.layers.phase2 import DvfLayer, ProprietaireLayer, SitadelLayer
from labuse.enums import CascadeVerdict, Severity

P = ParcelRef(id=1, idu="97415000AB0001", commune="Saint-Paul")


class _Ctx:
    def __init__(self, **v):
        self._v = v

    def table_has_commune(self, table, commune):
        return self._v.get("has_commune", True)

    def sitadel_near(self, pid, radius, months, types=None):
        return self._v.get("sitadel", {"matched_idu": 0, "nearby": 0})

    def dvf_stats(self, pid, radius, years):
        return self._v.get("dvf", {"count": 0, "median_eur_m2": None})

    def latest_source_result(self, pid, src):
        return self._v.get("owner")


# ───────────────────── SITADEL : rattaché IDU vs signal de zone ─────────────────────

def test_sitadel_rattache_par_idu():
    v = SitadelLayer().evaluate(P, _Ctx(sitadel={"matched_idu": 2, "nearby": 5}), {})
    assert v.result == CascadeVerdict.POSITIVE
    assert "RATTACHÉ" in v.detail.upper()
    assert "SIGNAL DE ZONE" not in v.detail          # le rattaché prime, jamais un signal de zone


def test_sitadel_signal_de_zone():
    v = SitadelLayer().evaluate(P, _Ctx(sitadel={"matched_idu": 0, "nearby": 5}), {})
    assert v.result == CascadeVerdict.POSITIVE
    assert "SIGNAL DE ZONE" in v.detail              # CONTRAT lu par dryrun.compute_matrice
    assert "RATTACHÉ" not in v.detail.upper()


def test_sitadel_deux_verdicts_distincts():
    rattache = SitadelLayer().evaluate(P, _Ctx(sitadel={"matched_idu": 1, "nearby": 0}), {})
    zone = SitadelLayer().evaluate(P, _Ctx(sitadel={"matched_idu": 0, "nearby": 3}), {})
    assert rattache.detail != zone.detail
    assert "RATTACHÉ" in rattache.detail.upper() and "SIGNAL DE ZONE" not in rattache.detail
    assert "SIGNAL DE ZONE" in zone.detail and "RATTACHÉ" not in zone.detail.upper()


def test_sitadel_aucun_permis_pass():
    v = SitadelLayer().evaluate(P, _Ctx(sitadel={"matched_idu": 0, "nearby": 0}), {})
    assert v.result == CascadeVerdict.PASS


def test_sitadel_commune_non_ingeree_unknown():
    v = SitadelLayer().evaluate(P, _Ctx(has_commune=False), {})
    assert v.result == CascadeVerdict.UNKNOWN


# ───────────────────── ProprietaireLayer : nominal + absent ─────────────────────

def test_proprietaire_morale_positive():
    vs = ProprietaireLayer().evaluate(
        P, _Ctx(owner={"raw_payload": {"personne_morale": True, "categorie": "SCI"}}), {})
    assert any(v.result == CascadeVerdict.POSITIVE for v in vs)


def test_proprietaire_indivision_soft_flag_fort():
    vs = ProprietaireLayer().evaluate(
        P, _Ctx(owner={"raw_payload": {"nb_droits_propriete": 7}}), {})
    flag = next((v for v in vs if v.result == CascadeVerdict.SOFT_FLAG), None)
    assert flag is not None and flag.severity == Severity.FORT
    assert "indivision" in flag.detail.lower()


def test_proprietaire_absent_unknown():
    vs = ProprietaireLayer().evaluate(P, _Ctx(owner=None), {})
    assert len(vs) == 1 and vs[0].result == CascadeVerdict.UNKNOWN


# ───────────────────── DvfLayer : nominal + absent ─────────────────────

def test_dvf_mutations_contexte_positif():
    v = DvfLayer().evaluate(P, _Ctx(dvf={"count": 6, "median_eur_m2": 600}), {})
    assert v.result == CascadeVerdict.POSITIVE
    assert "mutation" in v.detail.lower()


def test_dvf_aucune_mutation_pass():
    v = DvfLayer().evaluate(P, _Ctx(dvf={"count": 0, "median_eur_m2": None}), {})
    assert v.result == CascadeVerdict.PASS


def test_dvf_commune_non_ingeree_unknown():
    v = DvfLayer().evaluate(P, _Ctx(has_commune=False), {})
    assert v.result == CascadeVerdict.UNKNOWN
