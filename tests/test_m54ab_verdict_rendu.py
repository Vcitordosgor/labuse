"""M54-AB Famille 1 (C1) — RÉ-ANCRÉ M124-A (2026-08, cf. docs/DETTE_SUITE.md §1).

Décision produit en vigueur : le PDF client est DATA-ONLY — il n'imprime PLUS de verdict
(ni tier, ni rang, ni score/complétude) ; « l'analyse LABUSE reste à l'écran »
(pdf_premium.py, docstring « M124-A : plus de verdict/rang/score »). Ce test GARDE cette
décision : le texte extrait du PDF ne contient NI code technique NI libellé de tier NI le rang.

Avant M124-A ce test exigeait le libellé court M137 imprimé au papier ; M124-A l'a retiré du
PDF (le verdict vit à l'écran). On teste donc désormais l'ABSENCE, pour qu'une réintroduction
accidentelle du verdict au PDF casse ce test."""
from __future__ import annotations

import pytest

from labuse.api.pdf_premium import render_fiche_pdf
from labuse.verdict_servi import TIER_LABELS

pypdf = pytest.importorskip("pypdf")

_BASE = {
    "idu": "97415000AB0001", "commune": "Saint-Paul", "statut": "chaude",
    "surface_m2": 500, "q_score": 60, "a_score": 55, "completeness_score": 70,
    "coords": [55.26, -21.05],
    "lines": [], "flags": [], "evenement": None, "evenement_detail": None,
    "proprietaire_moral": None, "score_v": None, "contexte_commune": None, "rtaa": {},
}

# codes techniques qui ne doivent JAMAIS apparaître au client
_CODES = list(TIER_LABELS) + ["_sature", "_revele", "_fermee", "_statut_inconnu", "_non_constructible"]


def _texte(pdf: bytes) -> str:
    r = pypdf.PdfReader(__import__("io").BytesIO(pdf))
    return "\n".join((pg.extract_text() or "") for pg in r.pages)


@pytest.mark.parametrize("tier", list(TIER_LABELS))
def test_pdf_data_only_ni_code_ni_verdict_par_tier(tier: str):
    """M124-A : le PDF n'imprime NI code technique NI libellé de tier, pour tous les tiers."""
    fiche = dict(_BASE)
    fiche["score_v2"] = {"tier": tier, "rang": 57643, "rang_total": 428239, "mult_base": 1.3,
                         "declasse": tier.startswith("declasse_"), "motif": None}
    txt = _texte(render_fiche_pdf(fiche))
    for code in _CODES:
        assert code not in txt, f"code technique « {code} » fuite au client pour le tier {tier}"
    # M124-A : le libellé de tier NE DOIT PLUS être imprimé (verdict retiré du PDF, reste à l'écran).
    assert TIER_LABELS[tier] not in txt, (
        f"M124-A : le libellé « {TIER_LABELS[tier]} » ne doit plus figurer au PDF (data-only)")


def test_pdf_data_only_pas_de_rang():
    """M124-A : le rang/dénominateur n'est plus imprimé au PDF (il vit à l'écran)."""
    fiche = dict(_BASE)
    fiche["score_v2"] = {"tier": "declasse_bati_sature", "rang": 57643, "rang_total": 428239,
                         "mult_base": 1.3, "declasse": True,
                         "motif": "bâtie saturée — ratio 43 % (emprise 140 m²)"}
    txt = _texte(render_fiche_pdf(fiche)).replace(" ", "").replace(" ", "").replace("\xa0", "")
    assert "57643/428239" not in txt   # M124-A : aucun rang au PDF
