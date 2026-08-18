"""M2 — tests d'AFFICHAGE (texte des composants) de la refonte « Projet ».

Vérifie que les marqueurs de la maquette validée sont présents dans le code servi (garde-fou de
régression sans framework JS). Le comportement DB est couvert par test_projet_m2.py.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KANBAN = (ROOT / "frontend/src/components/projets/ProjetKanban.tsx").read_text(encoding="utf-8")
PANEL = (ROOT / "frontend/src/components/projets/ProjetsPanel.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")


def test_carte_unifiee_deux_densites():
    # M120 · Phase 4 — UNE seule anatomie de carte (TriCard), DEUX densités : « À trier » garde tout
    # (dense = pourquoi + signaux), Retenues/Écartées s'allègent. Plus de ProposeeRow/KanbanCard.
    assert "function TriCard" in KANBAN and "data-tri-card" in KANBAN
    assert "function ProposeeRow" not in KANBAN and "function KanbanCard" not in KANBAN
    assert "dense" in KANBAN and "it.pourquoi" in KANBAN   # le pourquoi n'apparaît qu'en dense


def test_a_analyser_badge_et_filtre_pas_de_colonne():
    # « à analyser » : pas de 4e colonne, un filtre rapide + remontée en tête
    assert "data-kanban-filtre-analyse" in KANBAN and "filtreAnalyse" in KANBAN
    # seulement 3 colonnes déclarées
    assert KANBAN.count("key: 'proposee'") == 1 and "key: 'retenue'" in KANBAN and "key: 'ecartee'" in KANBAN
    assert "key: 'a_analyser'" not in KANBAN


def test_hors_criteres_badge():
    assert "data-badge-hors" in KANBAN and "hors critères actuels" in KANBAN


def test_carte_surface_adresse_pourquoi_signal_pas_de_qscore():
    # M120 · Phase 4 (ajustements Vic) : la carte surface l'ADRESSE + le POURQUOI + le signal
    # marché/événement ; le q_score interne (« qualité N/100 ») n'est PLUS servi ni affiché.
    assert "it.adresse" in KANBAN and "marche_eur_m2" in KANBAN and "it.evenement" in KANBAN
    assert "it.q_score" not in KANBAN and "qualité " not in KANBAN   # plus AUCUN q_score affiché
    # en-tête : chips FILTRANTS séparés des INDICATIFS (budget/type/livraison en retrait)
    assert "criteresFiltrants" in KANBAN and "criteresInformatifs" in KANBAN and "data-crit-indic" in KANBAN


def test_fusion_doublons_ui():
    assert "DedupBanner" in PANEL and "data-dedup-fusionner" in PANEL and "groupesDoublons" in PANEL
    assert "conflit" in PANEL.lower()   # les conflits sont affichés, jamais silencieux


def test_api_fusionner():
    assert "fusionnerProjets" in API and "/projets/fusionner" in API
    assert "hors_criteres" in API and "defisc" in API and "caduc" in API   # champs enrichis
