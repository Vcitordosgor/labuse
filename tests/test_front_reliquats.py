"""RELIQUATS FRONT (PJ2 · PJ4 · PJ5 · PJ6 + UI O2/O3) — tests d'affichage (pattern test_front_m2 :
marqueurs dans le source servi, garde-fous de régression sans framework JS).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASKBAR = (ROOT / "frontend/src/components/fiche/AskBar.tsx").read_text(encoding="utf-8")
FICHE = (ROOT / "frontend/src/components/fiche/Fiche.tsx").read_text(encoding="utf-8")
# Libellés client centralisés depuis M12/M19 (« texte client centralisé ») → lib/strings.ts (CLIENT.*).
STRINGS = (ROOT / "frontend/src/lib/strings.ts").read_text(encoding="utf-8")


# ───────────────────────── R1 · PJ6 — le panneau IA ne cache plus la fiche ─────────────────────────

def test_r1_replie_par_defaut():
    # M19 : le repli est devenu CONTRÔLABLE (`useState(!!startOpen)`) — replié par défaut, la
    # carte IA (bas de pile) peut l'ouvrir ; l'affordance de réouverture reste présente.
    assert "useState(!!startOpen)" in ASKBAR and "data-askbar-open" in ASKBAR


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
    # replié : le bouton dit que la dernière réponse est gardée ; rouvrir = un clic, cache inchangé.
    # M12/M19 : le libellé « dernière réponse gardée » vit désormais dans lib/strings.ts (CLIENT.*),
    # AskBar le rend via `CLIENT.fiche.ia.gardee` — même texte servi, source unique.
    assert "dernière réponse gardée" in STRINGS
    assert "CLIENT.fiche.ia.gardee" in ASKBAR
    assert "aucun nouvel appel" in ASKBAR


def test_r1_nav_onglets_hors_du_panneau_ia():
    # La fiche est passée en pile scrollée (« plus de navigation par onglets ») ; l'AskBar reste
    # un panneau injecté SÉPARÉMENT et repliable (startOpen/onClose) — il ne masque jamais la fiche (R1).
    assert "<AskBar" in FICHE and "onClose={() => setAskOpen(false)}" in FICHE
    assert "plus de navigation par onglets" in FICHE


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
# B2/M12 : le mini-anneau de complétude a quitté la liste (ResultsSection) → carte Kanban CRM.
KANBAN_CRM = (ROOT / "frontend/src/components/crm/Kanban.tsx").read_text(encoding="utf-8")


# Wordings servis VALIDÉS par Vic (arbitrage 07/2026) — tests remis à jour dessus, xfail retirés.

def test_r3_tooltip_multiplicateur_de_rang():
    # Wording servi validé : « ×N vs moyenne du parc » (plus court/clair que la formulation longue).
    assert "data-mult-tip" in RESULTS
    assert "vs moyenne du parc" in RESULTS
    assert "RR" not in RESULTS                      # jamais un chiffre de perf in-sample en surface


def test_r3_tooltip_jauge_completude():
    # M36 Lot B : la jauge Complétude est RETIRÉE des cartes CRM (quasi-constante, M35 D3) —
    # le verrou garde désormais son ABSENCE.
    assert "part des sources disponibles" not in KANBAN_CRM
    assert "completeness_score" not in KANBAN_CRM


def test_r3_matrice_non_thermique():
    # Invariant DUR : le vocabulaire thermique est RÉSERVÉ au tier P ; la matrice Q×A ne l'emprunte jamais.
    # Le statut 'chaude' de la MATRICE rend « Priorité dossier » ; le tier P 'chaude' rend « Chaude » (thermique).
    # Retrait du « v2 » des libellés tier validé (un n° de version interne ne s'affiche pas côté client).
    assert "chaude: { label: 'Priorité dossier'" in STATUS   # matrice Q×A → vocab dossier, jamais thermique
    assert "chaude: { label: 'Chaude'" in STATUS             # tier P → thermique (réservé)
    assert "brulante: { label: 'Brûlante'" in STATUS         # tier P → thermique (réservé)


def test_r3_desambiguisation_cote_a_cote():
    # TierBadge (les deux classements côte à côte) porte le tooltip d'explication
    assert "Deux classements distincts" in TIERBADGE
    # M36 Lot A : étiquette de source VRAIE — cas nominal « Classement servi », repli
    # honnête « Classement historique » ; le jargon « Matrice Q×A » ne s'affiche plus.
    assert "Verdict · Classement servi" in LEGEND
    assert "Verdict · Classement historique" in LEGEND
    assert "Verdict · Matrice Q×A" not in LEGEND


def test_r3_marqueur_commune_etiquette_vraie():
    # M35/M36 : le compteur commune sert les TIERS du run servi — le vocabulaire thermique
    # est désormais LE BON (réservé au tier P, règle R3 respectée) et l'étiquette est vraie.
    assert "parcelles brûlantes ou chaudes au classement servi" in MAPVIEW
    assert "en priorité dossier (matrice Q×A)" not in MAPVIEW   # l'étiquette AFFICHÉE fausse a disparu


# ───────────── R5 — UI des outils O2 (scoreur d'adresse) et O3 (anti-fiche) ─────────────

HEADER = (ROOT / "frontend/src/components/header/Header.tsx").read_text(encoding="utf-8")
SCOREUR = (ROOT / "frontend/src/components/outils/ScoreurAdresse.tsx").read_text(encoding="utf-8")
POURQUOI = (ROOT / "frontend/src/components/fiche/PourquoiPas.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")
# M12-D4 : « Scorer une adresse » a quitté l'en-tête pour le tiroir Outils (registre des outils).
REGISTRY = (ROOT / "frontend/src/components/outils/registry.ts").read_text(encoding="utf-8")


def test_r5_scoreur_trouvable_depuis_les_outils():
    # M12-D4 : l'outil « seconde opinion » quitte l'en-tête et rejoint les Outils (registre) —
    # surfacé comme outil PHARE du groupe « analyser », donc trouvable rapidement.
    assert "'scoreur-adresse'" in REGISTRY and "Scorer une adresse" in REGISTRY
    assert "phare: true" in REGISTRY.split("scoreur-adresse")[1][:200]


def test_r5_scoreur_champs_et_prix_manuel():
    # adresse NORMALISÉE BAN (jamais libre → AddressAutocomplete) + prix saisi à la main (jamais scrapé)
    assert "data-scoreur-adresse" in SCOREUR and "AddressAutocomplete" in SCOREUR
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
    # tiroir « Pourquoi pas ? » ajouté SEULEMENT pour écartées/flaggées (conditionnel), rendu via
    # PourquoiPasTab ; l'onglet est un littéral d'union 'pourquoi' (refactor : plus de constante TAB_POURQUOI).
    assert "'pourquoi'" in FICHE and "Pourquoi pas ?" in FICHE
    assert "verdictEcartee" in FICHE and "SOFT_FLAG" in FICHE     # condition écartée / flaggée
    assert "<PourquoiPasTab" in FICHE and "PourquoiPasTab" in FICHE


def test_r5_pourquoi_pas_hierarchise_et_source():
    assert "RÉDHIBITOIRE" in POURQUOI and "VIGILANCE" in POURQUOI
    assert "data-pourquoi-pas" in POURQUOI
    assert "m.source" in POURQUOI                   # chaque motif porte sa source
    assert "Aucun motif" in POURQUOI                # sans motif : on le dit, rien d'inventé


def test_r5_api_helpers():
    assert "scoreurAdresse" in API and "/scoreur-adresse" in API and "prix_demande_eur" in API
    assert "getAntiFiche" in API and "/anti-fiche/" in API
