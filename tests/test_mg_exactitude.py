"""M-G — exactitude servie : échéance DPE DOM (source unique), source PPR = flux réel, libellé PM1
(assiette, jamais une exclusion). Tests PURS (sans DB)."""
from __future__ import annotations

import inspect
from pathlib import Path

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.phase1 import RisquesLayer, SRC_DEAL_PPR, SRC_SUP_GPU
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


def test_ppr_pm1_assiette_source_gpu_jamais_exclusion():
    """Validation #3 : l'assiette PM1 nomme le flux GPU, dit le zonage interne INCONNU, jamais d'exclusion."""
    v = [x for x in _run("i_mvt", {"suptype": "PM1", "statut": "reglementaire", "risque": "inondation"})
         if x.result == CascadeVerdict.SOFT_FLAG][0]
    assert v.data_source_name == SRC_SUP_GPU        # P4/P2 : assiette API Carto GPU
    assert v.result != CascadeVerdict.HARD_EXCLUDE   # jamais une exclusion
    assert "n'est pas connu" in v.detail.lower()
    assert "jamais une exclusion" in v.detail.lower()


def test_ppr_pm1_marginal_reste_faible():
    """La sévérité (score) est INCHANGÉE : une intersection PM1 marginale reste FAIBLE."""
    v = [x for x in _run("i_mvt", {"suptype": "PM1", "risque": "inondation"}, coverage=0.05)
         if x.result == CascadeVerdict.SOFT_FLAG][0]
    assert v.severity == Severity.FAIBLE and "marginale" in v.detail.lower()
