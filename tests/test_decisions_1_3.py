"""Décisions 1-3 (directive post-1.A) — tests PURS (sans DB) des trois couches retouchées
et du bilan économique des prescriptions.

D1 : A/N sensible au recouvrement (HARD ≥ 90 %, mixte → flag + bonus réduit, liséré ignoré).
D2 : proxy SAR informatif (zéro exclusion/flag) + warning de divergence (⚠, AU renforcé).
D3 : ER ≥ 50 % → HARD « Emplacement réservé {num} : {libellé} ({pct} %) » ; mixité sociale
     → CA pondéré si calibré sinon PLACEHOLDER signalé ; eaux pluviales → majoration VRD.
"""
from __future__ import annotations

import pytest

from labuse.api.resume import build_resume
from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.phase1 import PrescriptionPluLayer, SarLayer, ZonagePluGpuLayer
from labuse.enums import CascadeVerdict, Severity
from labuse.faisabilite.bilan import compute_bilan
from labuse.faisabilite.engine import Hypotheses

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)

ZONAGE = {"spatial_kind": "plu_gpu_zone", "exclude_zones": [],
          "positive_prefixes": ["U", "AU"], "hard_exclude_prefixes": ["A", "N"],
          "an_hard_exclude_pct": 90, "an_mixte_min_pct": 5,
          "flag_fort_prefixes": [], "flag_prefixes": [], "positive_bonus_key": "zonage_u_au"}

SAR = {"spatial_kind": "sar", "plu_kind": "plu_gpu_zone", "uau_prefixes": ["U", "AU"],
       "divergent_subtypes": ["vocation_naturelle", "vocation_agricole", "vocation_continuite",
                              "vocation_coupure", "espace_naturel", "espace_agricole",
                              "coupure_urbanisation"],
       "info_subtypes": ["vocation_mixte", "vocation_rurale"]}

PRESC = {"spatial_kind": "plu_gpu_prescription", "emplacement_reserve_typepsc": ["05"],
         "boise_classe_typepsc": ["01"], "patrimoine_bati_typepsc": ["07"],
         "mixite_sociale_typepsc": ["16", "17"], "oap_typepsc": ["18"],
         "eaux_pluviales_typepsc": ["48"], "er_hard_exclude_pct": 50}


class _Ctx:
    """Stub minimal d'EvalContext : intersections par kind, sans PostGIS."""

    def __init__(self, by_kind: dict):
        self.by = by_kind

    def kind_present(self, kind):
        return kind in self.by

    def intersections(self, _pid, kind):
        return self.by.get(kind, [])


def _i(subtype, coverage, libelle=None):
    return Intersection(subtype, None, coverage, {"libelle": libelle} if libelle else {}, None)


def _as_list(out):
    return out if isinstance(out, list) else [out]


# ───────────────────────── D1 — zonage A/N sensible au recouvrement ─────────────────────────

def test_d1_an_total_hard_exclude_motif_directive():
    out = _as_list(ZonagePluGpuLayer().evaluate(P, _Ctx({"plu_gpu_zone": [_i("A", 1.0)]}), ZONAGE))
    assert len(out) == 1 and out[0].result == CascadeVerdict.HARD_EXCLUDE
    assert out[0].exclude_kind == "faux_positif"
    assert "Zone A PLU — inconstructible (recouvrement 100 %)" in out[0].detail


def test_d1_an_92_pct_avec_uau_reste_hard():
    ctx = _Ctx({"plu_gpu_zone": [_i("N", 0.92), _i("U1b", 0.08)]})
    out = _as_list(ZonagePluGpuLayer().evaluate(P, ctx, ZONAGE))
    assert out[0].result == CascadeVerdict.HARD_EXCLUDE
    assert "Zone N PLU — inconstructible (recouvrement 92 %)" in out[0].detail


def test_d1_zonage_mixte_flag_et_bonus_reduit():
    ctx = _Ctx({"plu_gpu_zone": [_i("N", 0.40), _i("U1b", 0.60)]})
    out = _as_list(ZonagePluGpuLayer().evaluate(P, ctx, ZONAGE))
    flags = [v for v in out if v.result == CascadeVerdict.SOFT_FLAG]
    pos = [v for v in out if v.result == CascadeVerdict.POSITIVE]
    assert len(flags) == 1 and flags[0].severity == Severity.MOYEN
    assert "Zonage mixte — constructibilité limitée à l'emprise U/AU" in flags[0].detail
    assert len(pos) == 1 and pos[0].magnitude == pytest.approx(0.60, abs=0.01)


def test_d1_lisere_an_sous_plancher_ignore():
    ctx = _Ctx({"plu_gpu_zone": [_i("N", 0.02), _i("U1b", 0.98)]})
    out = _as_list(ZonagePluGpuLayer().evaluate(P, ctx, ZONAGE))
    assert [v.result for v in out] == [CascadeVerdict.POSITIVE]
    assert out[0].magnitude == 1.0


def test_d1_au_pas_happe_par_prefixe_agricole():
    out = _as_list(ZonagePluGpuLayer().evaluate(P, _Ctx({"plu_gpu_zone": [_i("AU6c", 1.0)]}), ZONAGE))
    assert [v.result for v in out] == [CascadeVerdict.POSITIVE]


# ───────────────────────── D2 — proxy SAR informatif + divergence ─────────────────────────

def test_d2_divergence_sur_zone_u():
    ctx = _Ctx({"sar": [_i("vocation_naturelle", 0.98, "espace naturel (protection forte)")],
                "plu_gpu_zone": [_i("U1b", 1.0)]})
    v = SarLayer().evaluate(P, ctx, SAR)
    assert v.result == CascadeVerdict.PASS
    assert v.detail.startswith("⚠ proxy SAR divergent du PLU — vigilance en cas de révision")
    assert "zone AU" not in v.detail


def test_d2_divergence_zone_au_mention_renforcee():
    ctx = _Ctx({"sar": [_i("vocation_naturelle", 0.98, "espace naturel (protection forte)")],
                "plu_gpu_zone": [_i("AU6c", 1.0)]})
    v = SarLayer().evaluate(P, ctx, SAR)
    assert v.result == CascadeVerdict.PASS
    assert "zone AU : ouverture à l'urbanisation moins probable" in v.detail


def test_d2_proxy_coherent_avec_plu_information_simple():
    ctx = _Ctx({"sar": [_i("vocation_naturelle", 1.0, "espace naturel")],
                "plu_gpu_zone": [_i("N", 1.0)]})
    v = SarLayer().evaluate(P, ctx, SAR)
    assert v.result == CascadeVerdict.PASS and "⚠" not in v.detail
    assert "proxy" in v.detail.lower()


def test_d2_jamais_excluant_ni_penalisant():
    for st in ("vocation_naturelle", "vocation_agricole", "espace_naturel", "espace_agricole",
               "coupure_urbanisation", "vocation_mixte", "vocation_rurale", "vocation_urbaine"):
        v = SarLayer().evaluate(P, _Ctx({"sar": [_i(st, 1.0, st)]}), SAR)
        assert v.result in (CascadeVerdict.PASS, CascadeVerdict.UNKNOWN), st


def test_d2_divergence_au_remontee_en_vigilance():
    cascade = [{"layer_name": "sar", "result": "PASS", "severity": None,
                "detail": "⚠ proxy SAR divergent du PLU — vigilance en cas de révision : "
                          "SAR (proxy indicatif) « espace naturel » sur zone PLU « AU6c » "
                          "— zone AU : ouverture à l'urbanisation moins probable."}]
    r = build_resume({"status": "a_creuser"}, cascade, None, {"has_manual_contact": True})
    assert any("Proxy SAR divergent du PLU (zone AU)" in v for v in r["vigilance"])


# ───────────────────────── D3.a — emplacements réservés ─────────────────────────

def test_d3a_er_majoritaire_hard_exclude_format_directive():
    ctx = _Ctx({"plu_gpu_prescription": [_i("05", 0.62, "ER 12 - Voie nouvelle à 8 m")]})
    out = _as_list(PrescriptionPluLayer().evaluate(P, ctx, PRESC))
    he = [v for v in out if v.result == CascadeVerdict.HARD_EXCLUDE]
    assert len(he) == 1 and he[0].exclude_kind == "faux_positif"
    assert "Emplacement réservé 12 : Voie nouvelle à 8 m (62 %)" in he[0].detail


def test_d3a_er_minoritaire_flag_moyen_et_deduction_annoncee():
    ctx = _Ctx({"plu_gpu_prescription": [_i("05", 0.09, "ER 81 - Aménagement du chemin de la Cigale")]})
    out = _as_list(PrescriptionPluLayer().evaluate(P, ctx, PRESC))
    assert [v.result for v in out] == [CascadeVerdict.SOFT_FLAG]
    assert out[0].severity == Severity.MOYEN
    assert "déduite de l'emprise constructible" in out[0].detail


# ───────────────────────── D3.b / D3.c — bilan (mixité, pluvial) ─────────────────────────

def _prix(q1, med, q3, n=40):
    return {"fiable": True, "fiabilite": "fiable", "fiabilite_raisons": [], "type_prix": "appartement",
            "n": n, "n_exclus": 0, "n_doublons": 0, "radius_m": 1500.0, "commune_fallback": False,
            "pct_appartement": 100, "periode": [2022, 2025], "q1": q1, "median": med, "q3": q3,
            "min": round(q1 * 0.9), "max": round(q3 * 1.1)}


def test_d3b_mixite_placeholder_ca_non_pondere_et_averti():
    h = Hypotheses()  # pct_lls = prix_m2_lls = 0 (PLACEHOLDER)
    eco = {"mixite": True, "mixite_libelle": "Clause logements aidés"}
    b = compute_bilan(4600, 4500, _prix(2200, 3000, 4300), h, contexte_eco=eco)
    assert b.ca["central"] == round(4600 * 3000)          # CA inchangé
    assert any("PLACEHOLDER" in a for a in b.avertissements)
    assert b.calc and b.calc["mixite"] is True and b.calc["pondere"] is False


def test_d3b_mixite_calibree_ca_pondere_formule_directive():
    h = Hypotheses()
    h.pct_lls, h.prix_m2_lls = 30.0, 2600.0
    b = compute_bilan(4600, 4500, _prix(2200, 3000, 4300), h,
                      contexte_eco={"mixite": True})
    attendu = 4600 * (0.70 * 3000 + 0.30 * 2600)          # CA = SDP×[(1−p)×neuf + p×LLS]
    assert b.ca["central"] == round(attendu)
    assert any("CA pondéré" in s.label for s in b.steps)
    assert b.calc["pondere"] is True


def test_d3c_pluvial_neutre_puis_majoration():
    h = Hypotheses()
    eco = {"pluvial": True, "pluvial_libelle": "zone reglt Forte"}
    b0 = compute_bilan(4600, 4500, _prix(2200, 3000, 4300), h, contexte_eco=eco)
    assert any("majoration_vrd_pluvial = 0" in x for x in b0.hypotheses)  # visible mais neutre
    h.majoration_vrd_pluvial = 10.0
    b1 = compute_bilan(4600, 4500, _prix(2200, 3000, 4300), h, contexte_eco=eco)
    assert b1.calc["cc_bas"] == pytest.approx(b0.calc["cc_bas"] * 1.10, rel=1e-6)
    # charge foncière dégradée par le surcoût VRD
    assert b1.charge_fonciere["central"] < b0.charge_fonciere["central"]
