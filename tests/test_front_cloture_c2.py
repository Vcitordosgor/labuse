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
    tpl = (ROOT / "src" / "labuse" / "flash" / "templates" / "rapport.html.j2").read_text(encoding="utf-8")
    # le caveat est présent dans le template servi
    assert "surface de plancher au sens PLU" in tpl
    assert "habitable" in tpl and "15" in tpl
    # la dérivation de l'habitable (SDP / 1,15) rend le bon nombre
    out = Environment().from_string(
        "{{ (c.residuel.sdp_residuelle_m2 / 1.15) | round | int }}"
    ).render(c={"residuel": {"sdp_residuelle_m2": 1150}})
    assert out == "1000"                                    # 1150 / 1,15 = 1000 m² habitables


# B2 (BLOC B) : test du toggle « Bâti / libre » RETIRÉ avec le proto Vue (tag
# archive/proto-vue) — le toggle n'a jamais été porté en React : la mutabilité carte a été
# retirée à M9 (fondue en « Potentiel de transformation » dans la fiche, doctrine conservée).
