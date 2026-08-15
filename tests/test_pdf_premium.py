"""Régression audit UI (12/07) — export PDF de la fiche premium.

À l'origine : la bascule q_v2 → q_v3_datagap (0c9f335) avait mis un f-string `{RUN}` dans le
footer de pdf_premium.py SANS importer le symbole → NameError sur TOUTES les fiches (500). Ce
test rendait un PDF minimal et vérifiait aussi que `RUN` restait importable.

M90 — le footer a depuis migré vers `export_commun.pied_de_page_pdf` (M6 2a) : il ne porte plus
de f-string `{RUN}`, et le symbole `RUN` a été retiré du module. La régression d'origine est donc
STRUCTURELLEMENT éteinte (évolution voulue, pas un bug). On retire l'`import RUN` qui, resté en
tête de module, faisait échouer la COLLECTE de TOUTE la suite (ImportError) — une panne de test
qui masquait 1500+ autres tests. Le test de rendu ci-dessous exerce le PDF footer compris : un
NameError de pied de page y crasherait encore, donc la protection utile est conservée.
"""
from __future__ import annotations

from labuse.api.pdf_premium import render_fiche_pdf

FICHE_MIN = {
    "idu": "97415000AB0001", "commune": "Saint-Paul", "statut": "chaude",
    "surface_m2": 500, "q_score": 60, "a_score": 55, "completeness_score": 70,
    "lines": [], "flags": [], "evenement": None, "evenement_detail": None,
    "proprietaire_moral": None, "score_v": None,
    "contexte_commune": None, "rtaa": {},
}


def test_render_fiche_pdf_ne_crashe_plus():
    # Rend le PDF ENTIER, pied de page compris (auto_page_break) : capture tout NameError de footer.
    pdf = render_fiche_pdf(FICHE_MIN)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 2000
