"""NUIT N5 — filet de tests de CARACTÉRISATION pour 3 modules SERVIS encore nus.

Priorisation par criticité (tous servis sur chaque fiche/liste, tous purs, aucun test direct) :
  1. `scoring.opportunity.compute_opportunity` — le SCORE + STATUT d'opportunité servi (le cœur).
  2. `scoring.completeness.compute_completeness` — la COMPLÉTUDE servie (double-score).
  3. `scoring.declassement.apply_declassement` — le DÉCLASSEMENT non-franc du statut servi.

Ces tests PHOTOGRAPHIENT le comportement actuel (ils ne le corrigent pas). Un bug découvert →
finding numéroté dans le rapport de nuit, JAMAIS de fix dans ce lot.
"""
from __future__ import annotations

from labuse.cascade.base import hard_exclude, passed, soft_flag
from labuse.config import opportunity_weights
from labuse.enums import CascadeVerdict, EvaluationStatus as ES, Severity
from labuse.scoring.completeness import compute_completeness
from labuse.scoring.declassement import apply_declassement
from labuse.scoring.opportunity import compute_opportunity


# ───────────────────────── 1. compute_opportunity ─────────────────────────

def test_opportunity_vide_donne_le_base_score():
    r = compute_opportunity([passed("x", "ok")])
    assert r.hard_exclude is False
    assert r.score == opportunity_weights()["base_score"]        # aucun flag → score de base
    assert r.has_fort_flag is False


def test_opportunity_hard_exclude_score_zero():
    r = compute_opportunity([hard_exclude("eau", "sur l'eau", kind="exclue"), passed("y", "ok")])
    assert r.hard_exclude is True and r.score == 0
    assert r.exclude_kind == "exclue" and r.has_fort_flag is False


def test_opportunity_soft_flag_fort_marque_et_penalise():
    base = compute_opportunity([passed("x", "ok")]).score
    r = compute_opportunity([soft_flag("risques", "PPR fort", Severity.FORT)])
    assert r.has_fort_flag is True
    assert r.score < base                                        # un flag fort pénalise le score


def test_opportunity_faux_positif_prioritaire_sur_exclue_absent():
    # deux hard_exclude 'faux_positif' → exclude_kind reste 'faux_positif' (aucun 'exclue').
    r = compute_opportunity([hard_exclude("emprise_lineaire", "voirie", kind="faux_positif")])
    assert r.hard_exclude is True and r.exclude_kind == "faux_positif"


# ───────────────────────── 2. compute_completeness ─────────────────────────

def test_completeness_cadastre_suit_parcel_ingested():
    ok = compute_completeness([], parcel_ingested=True)
    ko = compute_completeness([], parcel_ingested=False)
    assert ok.by_family["cadastre"]["covered"] is True
    assert ko.by_family["cadastre"]["covered"] is False
    assert ok.score > ko.score                                  # cadastre pèse dans le score


def test_completeness_unknown_ne_couvre_pas():
    from labuse.cascade.base import unknown
    # une couche répondue (PASS) couvre sa famille ; UNKNOWN ne couvre pas.
    r_pass = compute_completeness([passed("risques", "ok")], parcel_ingested=True)
    r_unk = compute_completeness([unknown("risques", "inconnu")], parcel_ingested=True)
    assert r_pass.score >= r_unk.score


def test_completeness_score_borne_0_100():
    r = compute_completeness([], parcel_ingested=True)
    assert 0 <= r.score <= 100


# ───────────────────────── 3. apply_declassement ─────────────────────────

def test_declassement_aucun_signal_inchange():
    assert apply_declassement(ES.OPPORTUNITE, {}) == (ES.OPPORTUNITE, None)


def test_declassement_surface_reduite_vers_a_creuser():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 100.0})
    assert st == ES.A_CREUSER and "surface réduite" in motif


def test_declassement_ne_remonte_jamais():
    # statut déjà plus bas (EXCLUE) : un signal 'à creuser' ne le REMONTE pas.
    st, motif = apply_declassement(ES.EXCLUE, {"surface_m2": 100.0})
    assert st == ES.EXCLUE and motif is not None                # motif renseigné mais statut inchangé


def test_declassement_pente_forte():
    st, motif = apply_declassement(ES.OPPORTUNITE, {"pente_pct": 55.0})
    assert st == ES.A_CREUSER and "pente" in motif
