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


def test_hybride_proposees_liste_retenues_cartes():
    # proposées = liste dense (ProposeeRow), retenues/écartées = cartes (KanbanCard)
    assert "function ProposeeRow" in KANBAN and "function KanbanCard" in KANBAN
    assert "data-proposee-row" in KANBAN and "data-kanban-card" in KANBAN


def test_a_analyser_badge_et_filtre_pas_de_colonne():
    # « à analyser » : pas de 4e colonne, un filtre rapide + remontée en tête
    assert "data-kanban-filtre-analyse" in KANBAN and "filtreAnalyse" in KANBAN
    # seulement 3 colonnes déclarées
    assert KANBAN.count("key: 'proposee'") == 1 and "key: 'retenue'" in KANBAN and "key: 'ecartee'" in KANBAN
    assert "key: 'a_analyser'" not in KANBAN


def test_hors_criteres_badge():
    assert "data-badge-hors" in KANBAN and "hors critères actuels" in KANBAN


def test_vignette_ign_lazy():
    assert "function Vignette" in KANBAN and 'loading="lazy"' in KANBAN and "ORTHOIMAGERY" in KANBAN


def test_fusion_doublons_ui():
    assert "DedupBanner" in PANEL and "data-dedup-fusionner" in PANEL and "groupesDoublons" in PANEL
    assert "conflit" in PANEL.lower()   # les conflits sont affichés, jamais silencieux


def test_api_fusionner():
    assert "fusionnerProjets" in API and "/projets/fusionner" in API
    assert "hors_criteres" in API and "defisc" in API and "caduc" in API   # champs enrichis
