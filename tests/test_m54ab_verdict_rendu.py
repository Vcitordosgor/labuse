"""M54-AB Famille 1 (C1) — le verdict imprimé au client n'est JAMAIS un code technique.

Rend la fiche premium pour TOUS les tiers (servables + 6 déclassements + écartée) et vérifie
dans le TEXTE EXTRAIT du PDF : zéro code technique (`declasse_*`, tier brut), le libellé client
présent, et — pour un tier classé — le rang AVEC son dénominateur. Source unique des libellés :
verdict_servi.TIER_LABELS (le même dictionnaire que l'écran)."""
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
def test_aucun_code_technique_par_tier(tier: str):
    fiche = dict(_BASE)
    # score_v2 SANS `label` : on prouve que le générateur retombe sur TIER_LABELS (pas le code brut).
    fiche["score_v2"] = {"tier": tier, "rang": 57643, "rang_total": 428239, "mult_base": 1.3,
                         "declasse": tier.startswith("declasse_"), "motif": None}
    txt = _texte(render_fiche_pdf(fiche))
    for code in _CODES:
        assert code not in txt, f"code technique « {code} » fuite au client pour le tier {tier}"
    assert TIER_LABELS[tier] in txt, f"libellé client absent pour {tier}"


def test_rang_avec_denominateur():
    fiche = dict(_BASE)
    fiche["score_v2"] = {"tier": "declasse_bati_sature", "rang": 57643, "rang_total": 428239,
                         "mult_base": 1.3, "declasse": True,
                         "motif": "bâtie saturée — ratio 43 % (emprise 140 m²)"}
    txt = _texte(render_fiche_pdf(fiche)).replace(" ", "").replace(" ", "").replace("\xa0", "")
    # rang ET dénominateur présents (un rang seul ne dit rien) — comparaison sans espaces
    assert "57643/428239" in txt
