"""PLU-CALIBRAGE-6 — la BASE du calcul de SDP est VALIDÉES-ONLY (comme l'overlay).

Constat SCORING-5-RETOUR §2 : `_val` lisait la valeur numérique de TOUTE feuille, quel que soit
son statut — 95 feuilles `propose` numériques branchaient la SDP. « Un résiduel calculé sur du
non-validé casse la règle "chaque chiffre est sourcé". »

Garde : une feuille `propose` ne branche JAMAIS le calcul ; une feuille SDP-déterminante encore
`propose` rend la zone NON CALCULABLE (cause `regle_plu_non_validee`), jamais une valeur par
défaut. Le stationnement en est exclu (il ne détermine pas `surface_plancher_m2`).
"""
from __future__ import annotations

from labuse.faisabilite import zonage as Z
from labuse.faisabilite.engine import Hypotheses, estimate_capacity


def _leaf(val, cle, statut):
    return {cle: val, "statut": statut, "article": "U 10", "page_pdf": 1, "citation": "preuve"}


# ── fonctions pures ───────────────────────────────────────────────────────────────────────────
def test_val_propose_ne_branche_pas():
    """AVANT : `_val` renvoyait 12.0 (la valeur propose branchait). APRÈS : `a_verifier`
    (non numérique → n'entre pas dans la SDP)."""
    reg = {"hauteur": {"faitage": _leaf(12.0, "m", "propose")}}
    assert Z._val(reg, "hauteur", "faitage", "m") == Z.A_VERIFIER


def test_val_valide_branche_toujours():
    reg = {"hauteur": {"faitage": _leaf(12.0, "m", "valide")}}
    assert Z._val(reg, "hauteur", "faitage", "m") == 12.0


def test_stat_propose_ne_branche_pas():
    reg = {"stationnement": {"par_logement": {"places": 2, "statut": "propose"}}}
    assert Z._stat_from_regles(reg) == Z.A_VERIFIER
    reg2 = {"stationnement": {"par_logement": {"places": 2, "statut": "valide"}}}
    assert Z._stat_from_regles(reg2) == "2 places / logement"


def test_regles_sdp_non_validees_detecte_les_bonnes_feuilles():
    reg = {"hauteur": {"faitage": _leaf(12.0, "m", "propose"),
                       "egout": _leaf(9.0, "m", "valide")},
           "retraits": {"voie": _leaf(3.0, "min_m", "propose")}}
    assert Z._regles_sdp_non_validees(reg) == ["hauteur.faitage", "retraits.voie"]


def test_stationnement_propose_n_est_pas_declencheur():
    """Le stationnement ne détermine pas la SDP → une feuille stationnement `propose` ne rend PAS
    la zone non calculable (mais elle ne branche pas non plus, cf. test_stat_propose)."""
    reg = {"stationnement": {"par_logement": {"places": 2, "statut": "propose"}}}
    assert Z._regles_sdp_non_validees(reg) == []


def test_feuille_absente_ou_plage_n_est_pas_declencheur():
    reg = {"hauteur": {"faitage": {"absent": True, "statut": "propose"}},
           "emprise_sol": {"ces": {"plage": {"min": 30}, "statut": "propose"}}}
    assert Z._regles_sdp_non_validees(reg) == []


# ── garde moteur (pure, sans base) ──────────────────────────────────────────────────────────────
def test_engine_regle_non_validee_non_calculable():
    """`estimate_capacity` sort AVANT tout calcul : non constructible, cause dédiée, aucune valeur
    de niveaux/reculs dérivée d'un défaut."""
    rules = Z.ZoneRules(code="U1", regle_non_validee="hauteur.faitage, retraits.voie")
    f = estimate_capacity(rules, 2000.0, hyp=Hypotheses())
    assert f.constructible is False
    assert f.cause == "regle_plu_non_validee"
    assert f.fourchette["logements_au_sol"] == (0, 0)
    assert not f.steps          # aucun step de calcul émis (rien n'a été calculé)


# ── intégration : routage resolve_zone → non calculable (destinations stubée, sans DB) ───────────
def _stub_commune(monkeypatch, reg: dict, zone="Uz"):
    from labuse.plu import destinations as D
    monkeypatch.setattr(Z, "_insee", lambda c: "99999")
    monkeypatch.setattr(Z, "_zonage_commune", lambda c: {"mode": "progressif"})
    monkeypatch.setattr(D, "regles_commune", lambda ins: [{"zone": zone}])
    monkeypatch.setattr(D, "regles_zone", lambda ins, code: reg)
    Z._calibrage_overlay.cache_clear()


def test_resolve_zone_propose_route_vers_non_calculable(monkeypatch):
    """Une zone calibrée dont la hauteur reste `propose` : resolve_zone porte `regle_non_validee`
    et le moteur rend la capacité non calculable — SANS retomber sur l'estimation générique
    (jamais une valeur par défaut). C'est le test qui CASSE si la base relit une règle non validée."""
    reg = {"hauteur": {"faitage": _leaf(12.0, "m", "propose")},
           "emprise_sol": {"ces": {"pct": 50.0, "statut": "valide", "article": "U 9",
                                   "page_pdf": 1, "citation": "50 %"}}}
    _stub_commune(monkeypatch, reg)
    rules = Z.resolve_zone("Uz", "CommuneFictiveZZ")
    assert rules is not None and rules.regle_non_validee == "hauteur.faitage"
    assert rules.calibree is True                    # calibrée, mais non calculable ≠ générique
    f = estimate_capacity(rules, 2000.0, hyp=Hypotheses())
    assert f.constructible is False and f.cause == "regle_plu_non_validee"


def test_resolve_zone_validee_calcule_normalement(monkeypatch):
    """Contrôle positif : les mêmes feuilles en `valide` → la zone se calcule (garde spécifique
    au `propose`, ne casse pas le cas nominal)."""
    reg = {"hauteur": {"faitage": _leaf(12.0, "m", "valide"),
                       "egout": _leaf(9.0, "m", "valide")},
           "emprise_sol": {"ces": {"pct": 50.0, "statut": "valide", "article": "U 9",
                                   "page_pdf": 1, "citation": "50 %"}}}
    _stub_commune(monkeypatch, reg)
    rules = Z.resolve_zone("Uz", "CommuneFictiveZZ")
    assert rules.regle_non_validee is None
    assert rules.he_m == 9.0 and rules.emprise_sol_pct == 50.0
    f = estimate_capacity(rules, 2000.0, hyp=Hypotheses())
    assert f.constructible is True
