"""M11 · SOCLE 0 — tests du service IA central (`labuse.ai.core`).

Tests PURS (sans appel Anthropic) : liste blanche, validation de sortie hybride 1+3, cache,
routeur de modèle. La couche 2 (chiffres) et la couche 1 (sources) sont vérifiées mécaniquement.
"""
from __future__ import annotations

import pytest

from labuse.ai import core


# ───────────────────── Lot 2 — grounding / liste blanche ─────────────────────
def test_liste_blanche_refuse_champ_hors_liste():
    with pytest.raises(ValueError):
        core.build_context({"zone": core.Fact("U4c"), "secret": core.Fact("x")},
                           allowed_fields={"zone"})


def test_liste_blanche_accepte_et_etiquette_provenance():
    ctx = core.build_context(
        {"zone": core.Fact("U4c", "SOURCE"), "sdp_m2": core.Fact(183, "ESTIME")},
        allowed_fields={"zone", "sdp_m2"})
    assert ctx["zone"] == {"valeur": "U4c", "provenance": "SOURCE"}
    assert ctx["sdp_m2"] == {"valeur": 183, "provenance": "ESTIME"}


# ───────────────────── Lot 3 couche 1 — sources forcées ─────────────────────
def _ctx():
    return core.build_context(
        {"zone": core.Fact("U4c", "SOURCE"), "sdp_m2": core.Fact(183, "ESTIME"),
         "prix_median": core.Fact(1640, "SOURCE")},
        allowed_fields={"zone", "sdp_m2", "prix_median"})


def test_source_valide_acceptee():
    chk = core.validate_output("La zone est U4c ⟨src:zone⟩.", _ctx())
    assert chk.ok and "zone" in chk.sources
    assert "⟨src" not in chk.text   # marqueur retiré du texte affiché


def test_source_invalide_rejetee():
    chk = core.validate_output("Bien desservie ⟨src:reseau⟩.", _ctx())
    assert not chk.ok and "reseau" in (chk.reason or "")


def test_prose_sans_source_rejetee_si_requise():
    chk = core.validate_output("La parcelle est constructible.", _ctx(), require_sources=True)
    assert not chk.ok


# ───────────────────── Lot 3 couche 2 — vérif mécanique des chiffres ─────────────────────
def test_chiffre_source_accepte():
    chk = core.validate_output("Capacité ESTIMÉE 183 m² ⟨src:sdp_m2⟩.", _ctx())
    assert chk.ok


def test_chiffre_invente_rejete():
    # 999 n'existe nulle part dans le contexte → hallucination numérique → rejet net
    chk = core.validate_output("Capacité 999 m² ⟨src:sdp_m2⟩.", _ctx())
    assert not chk.ok and "999" in (chk.reason or "")


def test_chiffre_source_avec_format_fr_accepte():
    # « 1 640 » (séparateur milliers FR) == 1640 au contexte
    chk = core.validate_output("Prix médian 1 640 €/m² ⟨src:prix_median⟩.", _ctx())
    assert chk.ok


def test_arrondi_keur_tolere():
    ctx = core.build_context({"charge": core.Fact(241000, "ESTIME")}, allowed_fields={"charge"})
    chk = core.validate_output("Charge foncière ~241 k€ ⟨src:charge⟩.", ctx)
    assert chk.ok


# ───────────────────── Lot 1 — routeur de modèle / statut ─────────────────────
def test_modeles_distincts_factuel_raisonnement():
    assert core.MODEL_FACTUAL != core.MODEL_REASONING
    assert "haiku" in core.MODEL_FACTUAL and "sonnet" in core.MODEL_REASONING


def test_provider_status_shape():
    st = core.provider_status()
    assert set(st) >= {"provider", "raison", "modeles", "doctrine"}


# ───────────────────── Lot 4 — cache (idu, run, question) ─────────────────────
def test_normalisation_question():
    assert core.normalize_question("  C'est quoi  U4c ? ") == "c'est quoi u4c"
    assert core.normalize_question("RISQUE inondation") == "risque inondation"


def test_cache_roundtrip_et_normalisation():
    from sqlalchemy import text

    from labuse.db import session_scope
    with session_scope() as s:
        idu, run = "97400000ZZ9999", "test_run_m11"
        # 1er cache_get crée la table si absente + repart propre
        core.cache_get(s, idu, run, "warmup")
        s.execute(text("DELETE FROM ia_cache WHERE idu=:i AND run_label IN (:r,:a)"),
                  {"i": idu, "r": run, "a": "autre_run"})
        assert core.cache_get(s, idu, run, "C'est quoi U4c ?") is None
        core.cache_put(s, idu, run, "C'est quoi U4c ?", {"texte": "zone urbaine"}, kind="fiche")
        # même question à la casse/espaces près → hit
        assert core.cache_get(s, idu, run, "  c'est quoi u4c   ") == {"texte": "zone urbaine"}
        # run différent → miss (invalidation implicite au changement de run servi)
        assert core.cache_get(s, idu, "autre_run", "C'est quoi U4c ?") is None
        s.execute(text("DELETE FROM ia_cache WHERE idu=:i"), {"i": idu})
