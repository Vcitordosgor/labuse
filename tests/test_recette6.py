"""RECETTE-6 — gardes des correctifs (unitaires, sans base).

On garde ici ce qui se teste sans I/O :
  · E2 (🔴) — le garde de vraisemblance du bilan (une saisie en TOTAL au lieu d'un €/m² ne produit
    plus un bilan absurde × 160, mais un « hors marché » qui NOMME le champ) ;
  · E5 — l'écran 0 « Que voulez-vous chiffrer ? » : un seul usage servi, les autres grisés AVEC raison ;
  · G2 — les lecteurs d'emprise bâtie posent tous ST_Union (plus de SUM qui double-compte les
    polygones BD TOPO qui se chevauchent).
"""
from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parents[1] / "src" / "labuse"


# ── F1 : le titre de l'apporteur suit le contenu (bâti / nu) ────────────────────────────────────
def test_f1_titre_apporteur_suit_le_contenu():
    from labuse.exports.blocs import apporteur
    nu = apporteur.rendu({}, {"idu": "X", "is_bati": False})
    bati = apporteur.rendu({}, {"idu": "X", "is_bati": True})
    assert "<h1>Un terrain à sonder</h1>" in nu
    assert "<h1>Un bien bâti à sonder</h1>" in bati


# ── F2 (🔴) : la feuille des documents ne réactive plus les substitutions qui cassent le ToUnicode ──
def test_f2_pas_de_ligatures_ni_chiffres_tabulaires():
    css = (RACINE / "exports" / "theme.css").read_text(encoding="utf-8")
    assert "font-variant-ligatures: none" in css
    # plus AUCUN `tabular-nums` (c'est lui qui rendait dates et prix inextractibles).
    assert "tabular-nums" not in css


# ── G2 : ST_Union partout (plus de double-compte de l'emprise bâtie) ────────────────────────────
def test_g2_lecteurs_emprise_posent_st_union():
    fichiers = [
        RACINE / "scoring" / "p_model" / "sql.py",
        RACINE / "faisabilite" / "bati_revele.py",
        RACINE / "faisabilite" / "au_ouverture.py",
    ]
    for f in fichiers:
        src = f.read_text(encoding="utf-8")
        if "ST_Intersection" in src:
            # là où on mesure l'emprise bâtie, l'union doit envelopper les intersections
            # (sinon deux polygones BD TOPO qui se chevauchent sont comptés deux fois).
            assert "ST_Union(" in src, f"{f.name} : emprise avec ST_Intersection mais sans ST_Union"
