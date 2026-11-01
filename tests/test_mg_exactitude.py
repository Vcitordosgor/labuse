"""M-G — exactitude servie : échéance DPE DOM (source unique), source PPR = flux réel, libellé PM1
(assiette, jamais une exclusion). Tests PURS (sans DB)."""
from __future__ import annotations

import inspect
from pathlib import Path

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.phase1 import RisquesLayer, SRC_DEAL_PPR
from labuse.enums import CascadeVerdict, Severity
from labuse.scoring import score_v_constants as C


# ── 1) DPE : calendrier DOM lu d'une SOURCE UNIQUE, jamais la métropole (2034) ──
def test_dpe_dom_source_unique():
    assert C.DPE_DOM_INTERDICTION_LOCATION == {"G": "01/01/2028", "F": "01/01/2031"}
    # les 3 libellés E lisent la constante (2028/2031), plus le 2034 métropole
    for code in ("DPE_G", "DPE_G_MULTI"):
        assert C.DPE_DOM_INTERDICTION_LOCATION["G"] in C.SIGNALS[code][2]
    assert C.DPE_DOM_INTERDICTION_LOCATION["F"] in C.SIGNALS["DPE_F"][2]
    assert "2034" not in C.SIGNALS["DPE_F"][2] and "2034" not in C.SIGNALS["DPE_G"][2]


def test_dpe_surfaces_lisent_la_constante():
    # M71 B1 : la couche DPE a quitté la cascade — il reste à garantir qu'AUCUN module
    # etage2 ne réintroduit le calendrier métropole 2034.
    et2 = inspect.getsource(__import__("labuse.cascade.layers.etage2", fromlist=["BodaccLayer"]))
    assert "2034" not in et2
    models = Path(C.__file__).resolve().parents[1].joinpath("models.py").read_text(encoding="utf-8")
    # la docstring de la vue passoire cite la source unique et l'échéance F correcte (2031, pas 2034)
    idx = models.find("Calendrier réglementaire DOM")
    bloc = models[idx:idx + 400]
    assert "01/01/2031" in bloc and "DPE_DOM_INTERDICTION_LOCATION" in bloc


# ── 2 & 4) PPR : source = flux réel ; assiette PM1 = périmètre, jamais une exclusion ──
_RISQUES = {"spatial_kind_ppr": "ppr", "spatial_kind_alea": "georisque_alea",
            "ppr_red_subtypes": ["INTERDICTION"],
            "alea_severity_map": {"fort": "fort", "moyen": "moyen", "faible": "faible"},
            "min_coverage_pct": 10}
_P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)


class _Ctx:
    def __init__(self, inters):
        self.inters = inters

    def kind_present(self, k):
        return k == "ppr"

    def intersections(self, _p, k):
        return self.inters if k == "ppr" else []


def _run(subtype, attrs, coverage=0.8):
    return RisquesLayer().evaluate(_P, _Ctx([Intersection(subtype, None, coverage, attrs, None)]), _RISQUES)


def test_ppr_deal_rouge_source_deal():
    v = [x for x in _run("INTERDICTION", {"statut": "zonage_reglementaire", "risque": "inondation"})
         if x.result == CascadeVerdict.HARD_EXCLUDE][0]
    assert v.data_source_name == SRC_DEAL_PPR       # P2 : zoné DEAL, pas « GPU »


def test_ppr_deal_bleu_source_deal_zone_connue():
    v = [x for x in _run("PRESCRIPTION", {"statut": "zonage_reglementaire", "risque": "inondation"})
         if x.result == CascadeVerdict.SOFT_FLAG][0]
    assert v.data_source_name == SRC_DEAL_PPR
    assert "bleue" in v.detail.lower()              # zonage connu, pas « périmètre inconnu »


def test_ppr_pm1_repli_code_inconnu_traite_rouge_d001():
    """SCORING-COPRO-1 (PPR-UNIQUE-1, NU-D-001) — DOCTRINE RÉVISÉE. Dans la couche `kind='ppr'`, un
    repli PM1 à CODE NON CLASSÉ (le code hérité `i` de Saint-Philippe : seul PM1 réellement présent en
    `ppr`) n'est plus « périmètre, zonage inconnu, jamais une exclusion » (c'était D-001 : 42 logements
    dessinés sur 100 % rouge). La couleur est lue par le module UNIQUE `labuse.ppr` : couleur incertaine
    → ROUGE par prudence. ≥ 50 % de surface → ÉCARTÉE, comme toute zone rouge. (Les VRAIES assiettes SUP
    GPU — enveloppes sans couleur des autres communes — vivent en `kind='sup'`, couche `sup`, en INFO :
    cette couche-ci ne les voit pas.)"""
    hx = [x for x in _run("i", {"suptype": "PM1", "statut": "reglementaire", "code_risque": "i"},
                          coverage=0.80) if x.result == CascadeVerdict.HARD_EXCLUDE]
    assert hx and hx[0].data_source_name == SRC_DEAL_PPR   # jugé par la lecture couleur unique
    assert "rouge" in hx[0].detail.lower() and "80 %" in hx[0].detail


def test_ppr_pm1_repli_marginal_rouge_vigilance_fort():
    """Un repli PM1 non classé (rouge par prudence) à faible couverture (2–50 %) → vigilance FORTE,
    jamais une exclusion (3 paliers rouges). Avant D-001 il restait FAIBLE (périmètre inconnu)."""
    out = _run("i", {"suptype": "PM1", "code_risque": "i"}, coverage=0.05)
    v = [x for x in out if x.result == CascadeVerdict.SOFT_FLAG][0]
    assert v.severity == Severity.FORT and "rouge" in v.detail.lower()
    assert not any(x.result == CascadeVerdict.HARD_EXCLUDE for x in out)
