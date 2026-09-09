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
    from labuse.financier_questionnaire import USAGES
    servis = [u for u in USAGES if u["servi"]]
    assert len(servis) == 1 and servis[0]["key"] == "construction"
    for u in USAGES:
        if not u["servi"]:
            assert u.get("raison"), f"usage grisé sans raison : {u['key']}"


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
