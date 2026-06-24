"""Étape A (quick-win PPR v2) — tests PURS (sans DB) du seuil de couverture marginale du périmètre PM1.

Une intersection MARGINALE du périmètre PPR (couverture < `min_coverage_pct` % de la parcelle) ne doit plus
produire un SOFT_FLAG **fort** (bloquant l'opportunité) mais une note informative **faible**. À partir du
seuil, le comportement actuel (FORT prudent) est conservé. Le rouge/bleu réglementaire n'est PAS géré ici
(Étape B) ; le seuil de scoring (65) reste inchangé ; aucune neutralisation globale du PPR.
"""
from __future__ import annotations

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.phase1 import RisquesLayer
from labuse.config import opportunity_weights
from labuse.enums import CascadeVerdict, Severity
from labuse.scoring.opportunity import compute_opportunity

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)

# Params 'risques' alignés sur config/cascade_rules.yaml + le nouveau seuil quick-win.
RISQUES = {"spatial_kind_ppr": "ppr", "spatial_kind_alea": "georisque_alea",
           "ppr_red_subtypes": ["rouge", "R"],
           "alea_severity_map": {"fort": "fort", "moyen": "moyen", "faible": "faible"},
           "min_coverage_pct": 10}


class _Ctx:
    """Stub minimal d'EvalContext : intersections par kind, sans PostGIS."""

    def __init__(self, by_kind: dict):
        self.by = by_kind

    def kind_present(self, kind):
        return kind in self.by

    def intersections(self, _pid, kind):
        return self.by.get(kind, [])


def _i(subtype, coverage):
    return Intersection(subtype, None, coverage, {"risque": "inondation"}, None)


def _ppr(coverage, subtype="i_mvt"):
    return RisquesLayer().evaluate(P, _Ctx({"ppr": [_i(subtype, coverage)]}), RISQUES)


def _flag(verdicts):
    flags = [v for v in verdicts if v.result == CascadeVerdict.SOFT_FLAG]
    return flags[0] if flags else verdicts[0]


# ── Intersection marginale (< seuil) → FAIBLE, jamais FORT ────────────────────────────────────
def test_pm1_couverture_5pct_pas_de_flag_fort():
    v = _flag(_ppr(0.05))
    assert v.result == CascadeVerdict.SOFT_FLAG
    assert v.severity == Severity.FAIBLE
    assert "marginale" in v.detail


def test_pm1_couverture_9_9pct_pas_de_flag_fort():
    assert _flag(_ppr(0.099)).severity == Severity.FAIBLE


# ── Au seuil et au-delà : comportement actuel (FORT prudent) conservé ─────────────────────────
def test_pm1_couverture_10pct_flag_fort_conserve():
    assert _flag(_ppr(0.10)).severity == Severity.FORT


def test_pm1_couverture_20pct_flag_fort_conserve():
    assert _flag(_ppr(0.20)).severity == Severity.FORT


def test_pm1_couverture_50pct_pas_de_neutralisation_globale():
    # une forte couverture reste un flag fort prudent : aucune neutralisation globale du PPR.
    assert _flag(_ppr(0.50)).severity == Severity.FORT


# ── Parcelle sans PPR : inchangée (aucun flag fort) ──────────────────────────────────────────
def test_parcelle_sans_ppr_inchangee():
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": []}), RISQUES)
    assert all(v.severity != Severity.FORT for v in out if v.result == CascadeVerdict.SOFT_FLAG)
    assert any(v.result == CascadeVerdict.PASS for v in out)


# ── Rouge réglementaire : logique inchangée (HARD_EXCLUDE), non touchée par l'Étape A ─────────
def test_rouge_reglementaire_reste_exclu_meme_marginal():
    # même à couverture marginale, le rouge reste une exclusion dure (l'Étape A ne touche que le périmètre).
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": [_i("rouge", 0.05)]}), RISQUES)
    assert any(v.result == CascadeVerdict.HARD_EXCLUDE for v in out)


# ── « Ne bloque plus fort » de bout en bout (compute_opportunity) ─────────────────────────────
def test_marginal_ne_bloque_plus_opportunite():
    assert compute_opportunity([_flag(_ppr(0.05))]).has_fort_flag is False   # marginal → ne bloque plus
    assert compute_opportunity([_flag(_ppr(0.20))]).has_fort_flag is True    # ≥ seuil → bloque encore (prudent)


# ── Garde-fou : le seuil d'opportunité reste 65 (le PPR n'y touche pas) ───────────────────────
def test_seuil_opportunite_inchange_65():
    assert opportunity_weights()["status_rules"]["opportunity_threshold"] == 65
