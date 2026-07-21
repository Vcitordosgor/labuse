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


# ───────────────────────── R2 · PJ2 — boutons du parcours de tri ─────────────────────────

TINDER = (ROOT / "frontend/src/components/projets/ParcoursTinder.tsx").read_text(encoding="utf-8")
KANBAN = (ROOT / "frontend/src/components/projets/ProjetKanban.tsx").read_text(encoding="utf-8")


def test_r2_trois_decisions_presentes():
    assert "data-decision-ecarter" in TINDER and "data-decision-retenir" in TINDER
    assert "data-decision-analyser" in TINDER       # la 3e décision manquait (PJ2)


def test_r2_couleurs_colonnes_kanban():
    # une décision = la couleur de sa colonne d'arrivée (M2)
    assert "#E8695A" in TINDER and "#E8695A" in KANBAN     # écartée
    assert "#E8B44C" in TINDER and "#E8B44C" in KANBAN     # à analyser
    assert "bg-mint" in TINDER                              # retenue (mint plein = la plus forte)


def test_r2_sortie_distincte_des_decisions():
    # Quitter : sobre (txt-mut), dans la barre haute — jamais confondu avec une décision
    assert "data-parcours-quitter" in TINDER and "✕ Quitter" in TINDER
    assert "text-txt-mut" in TINDER.split("data-parcours-quitter")[1][:300]


def test_r2_pas_de_raccourcis_inventes():
    # aucun raccourci clavier n'existe sur les décisions — on n'en affiche pas (règle du lot)
    assert "onKeyDown" not in TINDER.split("DecisionCard")[1]
    assert "on n'en invente pas" in TINDER
