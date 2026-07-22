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
    assert "...TABS" in FICHE and ".map((t) => (" in FICHE
    assert "AskBar" in FICHE                        # panneau injecté séparément, au-dessus


# ───────────────────────── R2 · PJ2 — boutons du parcours de tri ─────────────────────────

TINDER = (ROOT / "frontend/src/components/projets/ParcoursTinder.tsx").read_text(encoding="utf-8")
KANBAN = (ROOT / "frontend/src/components/projets/ProjetKanban.tsx").read_text(encoding="utf-8")


def test_r2_trois_decisions_presentes():
    assert "data-decision-ecarter" in TINDER and "data-decision-retenir" in TINDER
    assert "data-decision-analyser" in TINDER       # la 3e décision manquait (PJ2)


def test_r2_couleurs_colonnes_kanban():
    # une décision = la couleur de sa colonne d'arrivée (M2) — revue UI/UX S13/S14 :
    # les hex locaux sont devenus les tokens de palette (mêmes couleurs, source unique)
    assert "st-ecartee" in TINDER and "st-ecartee" in KANBAN   # écartée (#E8695A token)
    assert "st-creuser" in TINDER and "st-creuser" in KANBAN   # à analyser (#E8B44C token)
    assert "bg-mint" in TINDER                                  # retenue (mint plein = la plus forte)


def test_r2_sortie_distincte_des_decisions():
    # Quitter : sobre (txt-mut), dans la barre haute — jamais confondu avec une décision
    assert "data-parcours-quitter" in TINDER and "✕ Quitter" in TINDER
    assert "text-txt-mut" in TINDER.split("data-parcours-quitter")[1][:300]


def test_r2_pas_de_raccourcis_inventes():
    # aucun raccourci clavier n'existe sur les décisions — on n'en affiche pas (règle du lot)
    assert "onKeyDown" not in TINDER.split("DecisionCard")[1]
    assert "on n'en invente pas" in TINDER


# ───────────── R3 · PJ5 — tooltips ×N + jauge, et wording « deux brûlantes » ─────────────

RESULTS = (ROOT / "frontend/src/components/panel/ResultsSection.tsx").read_text(encoding="utf-8")
STATUS = (ROOT / "frontend/src/lib/status.ts").read_text(encoding="utf-8")
LEGEND = (ROOT / "frontend/src/components/map/Legend.tsx").read_text(encoding="utf-8")
TIERBADGE = (ROOT / "frontend/src/components/outils/TierBadge.tsx").read_text(encoding="utf-8")
MAPVIEW = (ROOT / "frontend/src/components/map/MapView.tsx").read_text(encoding="utf-8")


def test_r3_tooltip_multiplicateur_de_rang():
    assert "data-mult-tip" in RESULTS
    assert "Multiplicateur de rang" in RESULTS
    assert "au-dessus de la moyenne de l'univers analysé" in RESULTS
    assert "RR" not in RESULTS                      # jamais un chiffre de perf in-sample en surface


def test_r3_tooltip_jauge_completude():
    assert "part des sources disponibles" in RESULTS
    assert "N'est PAS une note de qualité du terrain" in RESULTS


def test_r3_matrice_non_thermique():
    # échelle thermique RÉSERVÉE au tier P servi ; matrice Q×A = « Priorité dossier »
    assert "label: 'Priorité dossier'" in STATUS
    assert "label: 'Chaude'," not in STATUS         # plus de « Chaude » matrice
    assert "label: 'Brûlante v2'" in STATUS and "label: 'Chaude v2'" in STATUS   # thermique v2 conservé


def test_r3_desambiguisation_cote_a_cote():
    # TierBadge (les deux classements côte à côte) porte le tooltip d'explication
    assert "Deux classements distincts" in TIERBADGE
    # légende matrice contextualisée (jamais un « VERDICT » thermique ambigu) —
    # revue UI/UX S20 : libellé en casse mixte, les capitales viennent du token .label-caps
    assert "Verdict · Matrice Q×A" in LEGEND


def test_r3_marqueur_commune_non_thermique():
    # le compteur commune (matrice_statut='chaude' côté backend) s'affiche en vocabulaire dossier
    assert "en priorité dossier (matrice Q×A)" in MAPVIEW
    assert "chaude${c.chaudes" not in MAPVIEW       # l'ancien wording thermique a disparu


# ───────────── R5 — UI des outils O2 (scoreur d'adresse) et O3 (anti-fiche) ─────────────

HEADER = (ROOT / "frontend/src/components/header/Header.tsx").read_text(encoding="utf-8")
SCOREUR = (ROOT / "frontend/src/components/outils/ScoreurAdresse.tsx").read_text(encoding="utf-8")
POURQUOI = (ROOT / "frontend/src/components/fiche/PourquoiPas.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")


def test_r5_scoreur_trouvable_depuis_le_header():
    # entrée visible à côté de la recherche (< 5 s) — l'outil de démo « seconde opinion »
    assert "data-scoreur-open" in HEADER and "Scorer une adresse" in HEADER
    assert "ScoreurAdresse" in HEADER


def test_r5_scoreur_champs_et_prix_manuel():
    assert "data-scoreur-adresse" in SCOREUR and "Collez une adresse" in SCOREUR
    assert "data-scoreur-prix" in SCOREUR and "jamais scrapé" in SCOREUR   # prix saisi à la main
    assert "data-scoreur-resultat" in SCOREUR and "data-scoreur-fiche" in SCOREUR


def test_r5_scoreur_verdicts_prix():
    # confrontation prix demandé vs charge foncière : les 4 verdicts servis par l'API
    for v in ("opportunite", "dans_le_marche", "cher", "non_estimable"):
        assert v in SCOREUR
    assert "data-scoreur-prix-verdict" in SCOREUR


def test_r5_scoreur_hors_base_honnete():
    # ok:false → le message honnête de l'API est affiché, jamais un verdict inventé
    assert "!d.ok" in SCOREUR and "d.message" in SCOREUR


def test_r5_pourquoi_pas_onglet_conditionnel():
    # onglet ajouté SEULEMENT pour écartées/flaggées ; la nav reste la même barre (règle PJ6)
    assert "TAB_POURQUOI" in FICHE and "Pourquoi pas ?" in FICHE
    assert "verdictEcartee || f.lines.some((l) => l.result === 'SOFT_FLAG')" in FICHE
    assert "tab === 'pourquoi'" in FICHE and "PourquoiPasTab" in FICHE


def test_r5_pourquoi_pas_hierarchise_et_source():
    assert "RÉDHIBITOIRE" in POURQUOI and "VIGILANCE" in POURQUOI
    assert "data-pourquoi-pas" in POURQUOI
    assert "m.source" in POURQUOI                   # chaque motif porte sa source
    assert "Aucun motif" in POURQUOI                # sans motif : on le dit, rien d'inventé


def test_r5_api_helpers():
    assert "scoreurAdresse" in API and "/scoreur-adresse" in API and "prix_demande_eur" in API
    assert "getAntiFiche" in API and "/anti-fiche/" in API
