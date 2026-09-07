"""EXPORTS-2 lot 5 — le Financier (moteur de bilan + document).

Recette : le bilan est refait À LA MAIN et retrouvé AU CENTIME (programme de la maquette :
635 m² vendables, 794 m² de plancher, 8 logements, prix de sortie 4 730 €/m² TTC, coût 2 550,
marge 9 %, régime 8,5 %). Sans un poste, le résultat est un « maximum » et jamais une valeur
inventée.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from labuse.exports import financier_bilan as fb
from labuse.exports.blocs import financier

MOTS = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml").read_text())["mots"]

PROG = {"surface_vendable": 635, "surface_plancher": 794, "surface_terrain": 742, "logements": 8}
HYP = {"prix_sortie": 4730, "cout": 2550, "part_sociale_pct": 0, "marge_pct": 9, "honoraires_pct": 12,
       "vrd_m2": 90, "cout_place": 15000, "aleas_pct": 4, "frais_acq_pct": 7, "prix_demande": 650000,
       "demolition": 60000, "depollution": 20000, "taxe": 39000, "duree_portage": 29,
       "taux_apport": 3, "taux": 0.085}


def _r2(x):
    return None if x is None else round(x, 2)


def test_bilan_ht_au_centime():
    """Le calcul refait à la main, retrouvé au centime (décision Vic 07/09 — bilan HT)."""
    b = fb.calculer(PROG, HYP)
    assert _r2(b["ca_ht"]) == 2768248.85                       # 635 × 4730 ÷ 1,085
    p = {k: _r2(v["montant"]) for k, v in b["postes"].items()}
    assert p["construction"] == 2024700.0                      # 794 × 2550
    assert p["honoraires_techniques"] == 242964.0              # 12 % × construction
    assert p["vrd"] == 66780.0                                 # 742 × 90
    assert p["stationnement"] == 120000.0                      # 8 × 15 000
    assert p["demolition"] == 60000.0 and p["depollution"] == 20000.0
    assert p["aleas"] == 80988.0                               # 4 % × construction
    assert p["taxe_amenagement"] == 39000.0
    assert p["redevance_archeologie"] == 539.92                # 794 × 0,68
    assert p["portage"] == 151632.3                            # (constr+VRD) × 3 % × 29/12
    assert p["frais_acquisition"] == 45500.0                   # 7 % × 650 000
    assert _r2(b["marge"]) == 249142.4                         # 9 % × CA HT
    assert _r2(b["charge"]["centrale"]) == -332997.77          # CA − Σ postes − marge
    assert b["maximum"] is False                               # tout chiffré


def test_conversion_ht_par_le_taux_du_regime():
    b085 = fb.calculer(PROG, HYP)
    b0 = fb.calculer(PROG, dict(HYP, taux=0.0))
    assert _r2(b0["ca_ht"]) == round(635 * 4730, 2)            # taux 0 → CA = TTC
    assert b085["ca_ht"] < b0["ca_ht"]                          # 8,5 % → CA HT plus bas


def test_maximum_si_un_poste_non_chiffre():
    """Un poste vide → None (jamais un défaut), et le résultat porte « maximum »."""
    b = fb.calculer(PROG, dict(HYP, cout_place=None, taxe=None))
    assert b["postes"]["stationnement"]["montant"] is None
    assert b["postes"]["taxe_amenagement"]["montant"] is None
    assert b["maximum"] is True


def test_bornes_et_sensibilite_coherentes():
    b = fb.calculer(PROG, HYP)
    assert b["charge"]["basse"] <= b["charge"]["centrale"] <= b["charge"]["haute"]
    grille = b["sensibilite"]
    assert len(grille) == 3 and all(len(r) == 3 for r in grille)
    # coin (coût haut, sortie bas) = borne basse ; coin (coût bas, sortie haut) = borne haute
    assert _r2(grille[2][0]["charge"]) == _r2(b["charge"]["basse"])
    assert _r2(grille[0][2]["charge"]) == _r2(b["charge"]["haute"])


def test_seuil_et_prix_de_revient():
    b = fb.calculer(PROG, HYP)
    assert b["seuil_rentabilite"] == b["charge"]["centrale"]    # prix d'achat à la marge visée
    # prix de revient = (foncier retenu + Σ postes) / vendable ; foncier retenu = prix demandé
    tot = sum(v["montant"] for v in b["postes"].values())
    assert _r2(b["prix_revient"]) == _r2((650000 + tot) / 635)
    assert _r2(b["ecart_prix_demande"]) == _r2(b["charge"]["centrale"] - 650000)


def _ctx(bilan, resolved):
    return {"bilan": bilan, "resolved": resolved, "program": PROG, "existe": True, "complet": True}


def test_document_rend_ht_verdict_regime():
    b = fb.calculer(PROG, HYP)
    resolved = {"prix_demande_saisi_eur": {"valeur": 650000, "origine": "saisi"},
                "regime_tva_saisi": {"valeur": "tva_marge", "origine": "saisi"},
                "cout_construction_saisi_eur_m2": {"valeur": 2550, "origine": "saisi"},
                "duree_portage_saisi_mois": {"valeur": 29, "origine": "prefill", "source": "x"}}
    html = financier.rendu({}, _ctx(b, resolved))
    assert "Bilan de l" in html and "opération" in html         # libellé échappé en HTML
    assert "bilan à rebours" in html.lower() and "HT" in html
    assert "Régime de TVA retenu" in html and "expert-comptable" in html
    assert "Sensibilité double" in html and "Calendrier" in html
    assert "◌" not in html
    assert [m for m in MOTS if m in html] == []


def test_document_maximum_sans_valeur_inventee():
    b = fb.calculer(PROG, dict(HYP, cout_place=None, taxe=None, demolition=None))
    html = financier.rendu({}, _ctx(b, {"regime_tva_saisi": {"valeur": "autre", "origine": "saisi"}}))
    assert "maximum" in html and "non chiffré" in html
    assert "◌" not in html
