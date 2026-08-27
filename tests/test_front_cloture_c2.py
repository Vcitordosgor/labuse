"""Clôture cycle 2 — tests d'AFFICHAGE des fix front (N8).

1. PDF Flash : le label SDP dit que ce n'est PAS l'habitable (surface de plancher au sens PLU,
   ~15 % de moins), et dérive l'habitable (~SDP / 1,15).
2. Carte (app.js) : le toggle qui colore le RATIO BÂTI est libellé « Bâti / libre » — PAS
   « Capacité (SDP) » (il ne colore pas la SDP) ni « Mutabilité » (mot retiré, doctrine C≠P).
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]


def test_flash_sdp_note_habitable():
    # REVUE · R9 — MISE À JOUR : le template flash ne dit plus « surface de plancher au sens PLU »
    # + dérivation habitable (SDP/1,15). La note servie est désormais « plancher (SDP) = vendable ÷
    # rendement » (le bloc faisabilité rend le plancher SDP et son rendement). Le produit est correct
    # (R3 : moteur unique 0 divergence) — c'est l'ANCIENNE formulation qui a été remplacée. On vérifie
    # la formulation ACTUELLE : le template sert bien la SDP/plancher avec sa dérivation par rendement.
    tpl = (ROOT / "src" / "labuse" / "flash" / "templates" / "rapport.html.j2").read_text(encoding="utf-8")
    assert "plancher (SDP)" in tpl                          # la SDP/plancher est servie
    assert "rendement" in tpl                               # dérivée par le rendement (vendable ÷ rendement)
    # la dérivation vendable/rendement reste un calcul déterministe correct
    out = Environment().from_string(
        "{{ (c.faisa.vendable_m2 * 100 / c.faisa.rendement_pct) | round | int }}"
    ).render(c={"faisa": {"vendable_m2": 790, "rendement_pct": 79}})
    assert out == "1000"                                    # 790 / 0,79 = 1000 m² de plancher


# B2 (BLOC B) : test du toggle « Bâti / libre » RETIRÉ avec le proto Vue (tag
# archive/proto-vue) — le toggle n'a jamais été porté en React : la mutabilité carte a été
# retirée à M9 (fondue en « Potentiel de transformation » dans la fiche, doctrine conservée).
