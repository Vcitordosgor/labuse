"""Étape A (quick-win PPR v2) — tests PURS (sans DB) du seuil de couverture marginale d'une zone PPR
NON INTERDITE (bleue / prescription).

Une intersection MARGINALE (couverture < `min_coverage_pct` % de la parcelle) d'une zone NON interdite
ne doit pas produire un SOFT_FLAG **fort** (bloquant l'opportunité) mais une note informative **faible**.
À partir du seuil, le comportement prudent (FORT) est conservé. Le seuil de scoring (65) reste inchangé.

SCORING-COPRO-1 (31/10/2026) — DOCTRINE PPR-UNIQUE-1 adoptée par la cascade : la couleur est désormais
lue par le module UNIQUE `labuse.ppr` (`labuse_ppr_couleur`). « Couleur INCERTAINE → ROUGE par prudence »
(on ne construit jamais dans une zone PPR dont la couleur n'est pas certaine) REMPLACE l'ancien « le doute
PM1 ne classe pas ». Conséquence testée ici : un code NON classé (ex. le code hérité `i` de Saint-Philippe,
NU-D-001) est ROUGE — et suit les 3 paliers rouges (marginal <2 % / vigilance / exclusion ≥50 %), plus la
graduation PM1. La graduation `min_coverage_pct` ne concerne donc plus que les zones non interdites (bleues).
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


def _ppr(coverage, subtype="PRESCRIPTION"):
    # SCORING-COPRO-1 — défaut PRESCRIPTION (zone BLEUE, non interdite) : c'est désormais le seul cas
    # où la graduation `min_coverage_pct` s'applique (un code non classé est rouge, cf. doctrine ci-dessus).
    return RisquesLayer().evaluate(P, _Ctx({"ppr": [_i(subtype, coverage)]}), RISQUES)


def _flag(verdicts):
    flags = [v for v in verdicts if v.result == CascadeVerdict.SOFT_FLAG]
    return flags[0] if flags else verdicts[0]


# ── Zone NON interdite (bleue), intersection marginale (< seuil) → FAIBLE, jamais FORT ─────────
def test_bleue_couverture_5pct_pas_de_flag_fort():
    v = _flag(_ppr(0.05))
    assert v.result == CascadeVerdict.SOFT_FLAG
    assert v.severity == Severity.FAIBLE
    assert "marginale" in v.detail


def test_bleue_couverture_9_9pct_pas_de_flag_fort():
    assert _flag(_ppr(0.099)).severity == Severity.FAIBLE


# ── Au seuil et au-delà : comportement prudent (FORT) conservé ────────────────────────────────
def test_bleue_couverture_10pct_flag_fort_conserve():
    assert _flag(_ppr(0.10)).severity == Severity.FORT


def test_bleue_couverture_20pct_flag_fort_conserve():
    assert _flag(_ppr(0.20)).severity == Severity.FORT


def test_bleue_couverture_50pct_pas_de_neutralisation_globale():
    # une zone bleue, même à forte couverture, reste un flag fort prudent — JAMAIS une exclusion.
    f = _flag(_ppr(0.50))
    assert f.severity == Severity.FORT
    assert f.result == CascadeVerdict.SOFT_FLAG   # bleu ne s'exclut jamais


# ── Code NON classé (ex. `i` de Saint-Philippe, NU-D-001) → ROUGE par prudence ────────────────
def test_code_inconnu_i_ge_50pct_exclu():
    """Le code hérité `i` (non classé) est traité ROUGE : ≥ 50 % de la surface → ÉCARTÉE (D-001).
    Avant SCORING-COPRO-1 il tombait en « périmètre, zonage inconnu, jamais d'exclusion »."""
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": [_i("i", 0.80)]}), RISQUES)
    hx = [v for v in out if v.result == CascadeVerdict.HARD_EXCLUDE]
    assert hx and "rouge" in hx[0].detail.lower() and "80 %" in hx[0].detail


def test_code_inconnu_i_2_50pct_flag_fort_pas_exclusion():
    """`i` entre 2 et 50 % → vigilance FORTE (rouge), jamais une exclusion."""
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": [_i("i", 0.05)]}), RISQUES)
    assert not any(v.result == CascadeVerdict.HARD_EXCLUDE for v in out)
    f = [v for v in out if v.result == CascadeVerdict.SOFT_FLAG]
    assert f and f[0].severity == Severity.FORT and "rouge" in f[0].detail.lower()


# ── Parcelle sans PPR : inchangée (aucun flag fort) ──────────────────────────────────────────
def test_parcelle_sans_ppr_inchangee():
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": []}), RISQUES)
    assert all(v.severity != Severity.FORT for v in out if v.result == CascadeVerdict.SOFT_FLAG)
    assert any(v.result == CascadeVerdict.PASS for v in out)


# ── Rouge réglementaire GRADUÉ (M-I, arbitrage Vic 08/08) : 3 paliers selon la part de surface ─
def test_rouge_ge_50pct_reste_exclu():
    # >= 50 % de surface rouge → écartée, comme avant, avec le % au motif.
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": [_i("rouge", 0.60)]}), RISQUES)
    hx = [v for v in out if v.result == CascadeVerdict.HARD_EXCLUDE]
    assert hx and "60 %" in hx[0].detail and "surface" in hx[0].detail


def test_rouge_2_50pct_flag_fort_pas_exclusion():
    # 2–50 % → SERVI avec flag FORT (vigilance), JAMAIS une exclusion.
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": [_i("rouge", 0.05)]}), RISQUES)
    assert not any(v.result == CascadeVerdict.HARD_EXCLUDE for v in out)
    f = [v for v in out if v.result == CascadeVerdict.SOFT_FLAG]
    assert f and f[0].severity == Severity.FORT and "5 %" in f[0].detail


def test_rouge_marginal_lt_2pct_mention_info_hors_score():
    # < 2 % → servi normalement, mention INFO (×0, hors score), m² + % affichés, jamais d'exclusion.
    out = RisquesLayer().evaluate(P, _Ctx({"ppr": [_i("rouge", 0.01)]}), RISQUES)
    assert not any(v.result == CascadeVerdict.HARD_EXCLUDE for v in out)
    f = [v for v in out if v.result == CascadeVerdict.SOFT_FLAG]
    assert f and f[0].severity == Severity.INFO
    assert "marginal" in f[0].detail and "10 m²" in f[0].detail   # 1000 m² × 1 %
    # INFO → 0 point : le rouge marginal n'entre pas dans le score.
    assert compute_opportunity([f[0]]).has_fort_flag is False


# ── « Ne bloque plus fort » de bout en bout (compute_opportunity) ─────────────────────────────
def test_marginal_ne_bloque_plus_opportunite():
    assert compute_opportunity([_flag(_ppr(0.05))]).has_fort_flag is False   # marginal → ne bloque plus
    assert compute_opportunity([_flag(_ppr(0.20))]).has_fort_flag is True    # ≥ seuil → bloque encore (prudent)


# ── Garde-fou : le seuil d'opportunité reste 65 (le PPR n'y touche pas) ───────────────────────
def test_seuil_opportunite_inchange_65():
    assert opportunity_weights()["status_rules"]["opportunity_threshold"] == 65
