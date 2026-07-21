"""RELIQUATS FRONT (PJ2 · PJ4 · PJ5 · PJ6 + UI O2/O3) — tests d'affichage (pattern test_front_m2 :
marqueurs dans le source servi, garde-fous de régression sans framework JS).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASKBAR = (ROOT / "frontend/src/components/fiche/AskBar.tsx").read_text(encoding="utf-8")
FICHE = (ROOT / "frontend/src/components/fiche/Fiche.tsx").read_text(encoding="utf-8")


# ───────────────────────── R1 · PJ6 — le panneau IA ne cache plus la fiche ─────────────────────────

def test_r1_replie_par_defaut():
    assert "useState(false)" in ASKBAR and "data-askbar-open" in ASKBAR


def test_r1_lien_voir_fiche_present_avec_reponse():
    # lien permanent quand une réponse est affichée ; la réponse reste gardée (pas détruite)
    assert "data-askbar-voir-fiche" in ASKBAR
    assert "Voir l'entièreté de la fiche" in ASKBAR
    assert "réponse reste gardée" in ASKBAR         # title explicite


def test_r1_regle_dure_reponse_bornee_nav_jamais_masquee():
    # RÈGLE DURE : zone de réponse bornée + scroll interne → la nav des onglets ne sort jamais de l'écran
    assert "data-askbar-reponse" in ASKBAR
    assert "max-h-[36vh]" in ASKBAR and "overflow-y-auto" in ASKBAR


def test_r1_redeploiement_sans_perte():
    # replié : le bouton dit que la dernière réponse est gardée ; rouvrir = un clic, cache inchangé
    assert "dernière réponse gardée" in ASKBAR
    assert "aucun nouvel appel" in ASKBAR


def test_r1_nav_onglets_hors_du_panneau_ia():
    # la nav des onglets vit dans Fiche.tsx (hors AskBar), en bloc shrink-0 propre
    assert "TABS.map" in FICHE
    assert "AskBar" in FICHE                        # panneau injecté séparément, au-dessus
