"""M-T Volet 1 — validation couche 2 (ancrage des chiffres) sur les trois synthèses, repli STUB.

Règle : synthèse riche SI elle passe la validation ; au moindre doute (pas de clé, erreur, ou
chiffre non ancré au contexte) → STUB déterministe EXACT avec son flag. JAMAIS « indisponible »,
jamais un chiffre douteux, jamais un écran vide.
"""
from __future__ import annotations

from labuse.ai import core as ai_core
from labuse.ai.core import IAResult, validate_output
from labuse.api import assistant as assistant_mod
from labuse.api import ia as ia_mod


# ── Couche 2 (mécanique, hors IA) : un chiffre inventé est rejeté, une prose fidèle passe ────────
def test_couche2_rejette_chiffre_faux_accepte_le_vrai():
    ctx = {"q_score": 66, "surface_m2": 800}
    faux = validate_output("La parcelle fait 4200 m².", ctx, require_sources=False, strict_numbers=True)
    assert faux.ok is False and "4200" in (faux.reason or "")
    vrai = validate_output("Qualité 66 sur 800 m².", ctx, require_sources=False, strict_numbers=True)
    assert vrai.ok is True


# ── /ia/synthese & /ia/pourquoi : rejet / dégradation → stub servi, flag visible ────────────────
def _patch_complete(monkeypatch, result):
    monkeypatch.setattr(ia_mod.core, "complete", lambda *a, **k: result)
    monkeypatch.setattr(ia_mod, "_log", lambda *a, **k: None)


def test_synthese_chiffre_faux_sert_le_stub(monkeypatch):
    # le modèle a sorti un chiffre non ancré → complete renvoie rejected=True
    _patch_complete(monkeypatch, IAResult(text="", model="m", rejected=True,
                                          reason="chiffre non sourcé « 999 »", raw="… 999 …"))
    out = ia_mod._validee_ou_stub(None, "synthese", "SYS", {"idu": "x"},
                                  lambda f: "SYNTHÈSE STUB EXACTE", "MENTION_OK", "MENTION_STUB")
    assert out["stub"] is True
    assert out["texte"] == "SYNTHÈSE STUB EXACTE"          # le stub déterministe, pas la prose douteuse
    assert out["stub_motif"] == "chiffre non ancré"
    assert out["mention"] == "MENTION_STUB"


def test_synthese_sans_cle_sert_le_stub(monkeypatch):
    _patch_complete(monkeypatch, IAResult(text="", model="m", degraded=True, reason="no_key"))
    out = ia_mod._validee_ou_stub(None, "pourquoi", "SYS", {"idu": "x"},
                                  lambda f: "STUB POURQUOI", "MENTION_OK", "MENTION_STUB")
    assert out["stub"] is True and out["texte"] == "STUB POURQUOI" and out["stub_motif"] == "clé IA absente"


def test_synthese_validee_sert_la_prose(monkeypatch):
    _patch_complete(monkeypatch, IAResult(text="SYNTHÈSE RICHE VALIDÉE", model="m", sources=["q_score"]))
    out = ia_mod._validee_ou_stub(None, "synthese", "SYS", {"idu": "x"},
                                  lambda f: "STUB (non servi)", "MENTION_OK", "MENTION_STUB")
    assert out["stub"] is False and out["texte"] == "SYNTHÈSE RICHE VALIDÉE" and out["mention"] == "MENTION_OK"


# ── assistant.explain_parcel : rejet / dégradation → synthèse règles déterministe (stub) ────────
def test_explain_parcel_rejet_sert_rules_summary(monkeypatch):
    # assistant importe `core` DANS la fonction → on patche le module labuse.ai.core directement.
    monkeypatch.setattr(ai_core, "has_key", lambda: True)
    monkeypatch.setattr(ai_core, "complete",
                        lambda *a, **k: IAResult(text="Parcelle de 4200 m².", model="m",
                                                 rejected=True, reason="chiffre non sourcé « 4200 »"))
    out = assistant_mod.explain_parcel({"idu": "97415000AB0001", "surface_m2": 800})
    assert out["available"] is False and out.get("stub") is True
    assert out["rules_summary"] and "explanation" not in out    # jamais la prose douteuse
    assert out["reason"] == "chiffre non ancré"
