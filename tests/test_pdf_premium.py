"""Régression audit UI (12/07) — export PDF de la fiche premium.

La bascule q_v2 → q_v3_datagap (0c9f335) avait mis un f-string `{RUN}` dans le footer
de pdf_premium.py SANS importer le symbole → NameError sur TOUTES les fiches (500).
Ce test rend un PDF avec une fiche minimale : il pète si l'import RUN redisparaît.
"""
from __future__ import annotations

from labuse.api.pdf_premium import RUN, render_fiche_pdf

FICHE_MIN = {
    "idu": "97415000AB0001", "commune": "Saint-Paul", "statut": "chaude",
    "surface_m2": 500, "q_score": 60, "a_score": 55, "completeness_score": 70,
    "lines": [], "flags": [], "evenement": None, "evenement_detail": None,
    "proprietaire_moral": None, "score_v": None,
    "contexte_commune": None, "rtaa": {},
}


def test_render_fiche_pdf_ne_crashe_plus():
    pdf = render_fiche_pdf(FICHE_MIN)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 2000


def test_footer_porte_le_run_de_reference():
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    assert RUN == Q_A_RUN_LABEL          # bascule centralisée : jamais un littéral local
