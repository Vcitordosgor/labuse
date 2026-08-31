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
    # SECTEUR-2 (mise à jour des marqueurs périmés M120 P4) — le « TriCard » a été REMPLACÉ par DEUX
    # anatomies de ligne selon la densité : LigneParcelle (« À trier », dense = pourquoi + signaux) et
    # MiniLigne (Retenues / Écartées, allégée). Plus de ProposeeRow / KanbanCard / TriCard.
    assert "function LigneParcelle" in KANBAN and "data-tri-ligne" in KANBAN
    assert "function MiniLigne" in KANBAN and "data-mini-ligne" in KANBAN
    assert "function ProposeeRow" not in KANBAN and "function KanbanCard" not in KANBAN and "function TriCard" not in KANBAN
    assert "pourquoi" in KANBAN   # le pourquoi reste servi (ligne dense)


def test_trois_colonnes_pas_de_colonne_a_analyser():
    # SECTEUR-2 (mise à jour) — le filtre « à analyser » (data-kanban-filtre-analyse) a été retiré ;
    # l'invariant qui TIENT toujours est « 3 colonnes, jamais une 4e colonne a_analyser ».
    assert "key: 'proposee'" in KANBAN and "key: 'retenue'" in KANBAN and "key: 'ecartee'" in KANBAN
    assert "key: 'a_analyser'" not in KANBAN


def test_carte_surface_adresse_pourquoi_pas_de_qscore():
    # SECTEUR-2 (mise à jour) — la ligne surface l'ADRESSE + le signal marché + le POURQUOI ; le
    # q_score interne (« qualité N/100 ») n'est toujours PAS servi. Les chips filtrants/indicatifs et le
    # signal `evenement` de la maquette M120 P4 ont été retirés de la ligne (marqueurs supprimés).
    assert "it.adresse" in KANBAN and "marche_eur_m2" in KANBAN and "pourquoi" in KANBAN
    assert "it.q_score" not in KANBAN and "qualité " not in KANBAN   # plus AUCUN q_score affiché


def test_fusion_doublons_ui():
    assert "DedupBanner" in PANEL and "data-dedup-fusionner" in PANEL and "groupesDoublons" in PANEL
    assert "conflit" in PANEL.lower()   # les conflits sont affichés, jamais silencieux


def test_api_fusionner():
    assert "fusionnerProjets" in API and "/projets/fusionner" in API
    assert "hors_criteres" in API and "defisc" in API and "caduc" in API   # champs enrichis
