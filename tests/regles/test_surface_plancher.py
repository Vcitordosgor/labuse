"""Témoin CIRCUIT-4 — capacité « table rase » : recalcul INDÉPENDANT de la chaîne de l'enveloppe
(modèle carré) posée dans l'ordre du règlement, comparé à estimate_capacity (fonction PURE)."""
from __future__ import annotations

import math

from labuse.faisabilite.engine import Hypotheses, estimate_capacity
from labuse.faisabilite.plu_rules import ZoneRules


def _regles(he=9.0, ces=None, pt=None):
    return ZoneRules(code="Utest", constructible_neuf=True, habitat="autorise",
                     he_m=he, hf_m=None, emprise_sol_pct=ces, pleine_terre_pct=pt,
                     recul_voirie_m=5.0, recul_limites_sep_m=3.0,
                     sources={}, calibree=True, via_renvoi=None)


def test_enveloppe_ordre_du_reglement():
    S = 1000.0
    hyp = Hypotheses()
    f = estimate_capacity(_regles(he=9.0, ces=40.0, pt=30.0), S, hyp=hyp, emprise_geo=None)
    # ── recalcul indépendant, étape par étape (formule de la fiche) ──
    cote = math.sqrt(S)
    emprise = max(0.0, cote - 5.0 - 3.0) * max(0.0, cote - 2 * 3.0)     # reculs (modèle carré)
    emprise = min(emprise, S * 40.0 / 100)                               # Art. 9 (CES)
    emprise = min(emprise, S * (1 - 30.0 / 100))                         # Art. 13 (pleine terre)
    niveaux = int(9.0 // hyp.etage_m)                                    # Art. 10 (hé)
    sdp = emprise * hyp.coef_occupation * niveaux                        # gabarit 0,45 × niveaux
    fr = f.fourchette
    assert f.constructible
    assert fr["surface_plancher_m2"] == round(sdp), (fr["surface_plancher_m2"], sdp)
    assert fr["niveaux_max"] == niveaux


def test_zone_fermee_rend_zero_avec_cause():
    r = ZoneRules(code="Ntest", constructible_neuf=False, habitat="autorise", he_m=None,
                  hf_m=None, emprise_sol_pct=None, pleine_terre_pct=None, recul_voirie_m=None,
                  recul_limites_sep_m=None, sources={}, calibree=True, via_renvoi=None)
    f = estimate_capacity(r, 1000.0)
    assert not f.constructible and f.fourchette["logements_au_sol"] == (0, 0)
    assert f.cause == "zone_transition"
