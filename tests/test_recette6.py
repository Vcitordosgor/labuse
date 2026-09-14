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


# ── E2 : le garde de vraisemblance ────────────────────────────────────────────────────────────
def test_e2_hors_marche_detecte_le_prix_en_total():
    from labuse.exports.financier_bilan import _hors_marche
    # 700 000 saisi comme prix de sortie « €/m² » (en fait le prix TOTAL d'un logement) : hors borne.
    hm = _hors_marche(700_000, None, None)
    assert hm is not None
    assert hm["champ"]                      # le garde NOMME le champ fautif
    assert hm["valeur"] == 700_000
    assert hm["borne"] and hm["borne"] < 700_000


def test_e2_prix_plausible_passe():
    from labuse.exports.financier_bilan import _hors_marche
    assert _hors_marche(4200, 2800, None) is None     # 4 200 €/m² de sortie : dans le marché


# ── E5 : l'écran 0 ────────────────────────────────────────────────────────────────────────────
def test_e5_un_seul_usage_servi_les_autres_grises_avec_raison():
    # TESTS-1 lot 2 (B) — RECETTE-8 W13bis (8f84a994, 09/09/2026) a bâti et SERVI le parcours
    # « Revente en l'état » : les usages servis sont désormais DEUX, nommés — l'invariant reste
    # « rien de servi qui ne soit bâti, rien de grisé sans raison ».
    from labuse.financier_questionnaire import USAGES
    servis = [u for u in USAGES if u["servi"]]
    assert {u["key"] for u in servis} == {"construction", "revente"}
    for u in USAGES:
        if not u["servi"]:
            assert u.get("raison"), f"usage grisé sans raison : {u['key']}"


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
