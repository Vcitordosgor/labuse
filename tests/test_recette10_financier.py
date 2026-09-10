"""RECETTE-10 T3/T4/T5 — le Financier au propre : natures justes des montants, charge foncière
négative dite en clair, garde de vraisemblance prix bailleur < prix libre."""
from __future__ import annotations

from labuse.exports import financier_bilan as fb
from labuse.exports.blocs import financier

# programme + hypothèses qui rendent une charge foncière NÉGATIVE (repris de lot5 : centrale = -332 997,77 €)
PROG = {"surface_vendable": 635, "surface_plancher": 794, "surface_terrain": 742, "logements": 8}
HYP = {"prix_sortie": 4730, "cout": 2550, "part_sociale_pct": 0, "marge_pct": 9, "honoraires_pct": 12,
       "vrd_m2": 90, "cout_place": 15000, "aleas_pct": 4, "frais_acq_pct": 7, "prix_demande": 650000,
       "demolition": 60000, "depollution": 20000, "taxe": 39000, "duree_portage": 29,
       "taux_apport": 3, "taux": 0.085}


def _ctx(bilan, resolved):
    return {"bilan": bilan, "resolved": resolved, "program": PROG, "existe": True, "complet": True}


# ── T3 — natures : un MONTANT produit d'une formule est ƒ dérivé, jamais sourcé ────────────────
def test_t3_natures_des_postes_produits_sont_derives():
    b = fb.calculer(PROG, HYP)
    n = {k: v["nature"] for k, v in b["postes"].items()}
    # produits d'une formule affichée par le bloc → dérivé
    for k in ("construction", "honoraires_techniques", "vrd", "stationnement", "aleas",
              "taxe_amenagement", "redevance_archeologie", "portage", "frais_acquisition"):
        assert n[k] == "derive", f"{k} devrait être ƒ dérivé, pas {n[k]}"
    # montants forfaitaires SAISIS directement par le porteur → projet
    assert n["demolition"] == "projet" and n["depollution"] == "projet"


def test_t3_le_montant_construction_nest_jamais_source_meme_si_le_taux_lest():
    """Le €/m² pré-rempli est SOURCÉ, mais le montant (plancher × €/m²) est ƒ DÉRIVÉ. L'ancien code
    tamponnait le montant « sourcé » dès que le taux l'était (le -717 k€ mensonger)."""
    b = fb.calculer(PROG, HYP)
    resolved = {"regime_tva_saisi": {"valeur": "tva_marge", "origine": "saisi"},
                # le coût de construction est un PRÉ-REMPLISSAGE sourcé
                "cout_construction_saisi_eur_m2": {"valeur": 2550, "origine": "prefill", "source": "médiane"}}
    html = financier.rendu({}, _ctx(b, resolved))
    # la ligne « Coût de construction » du BILAN À REBOURS porte la pastille ƒ dérivé, pas sourcé
    deb = html.find("bilan à rebours")
    i = html.find("Coût de construction", deb)
    fin = html.find("</tr>", i)
    segment = html[i:fin]
    assert "dérivé" in segment and "sourcé" not in segment
    # mais le TAUX, lui, reste montré comme sourcé dans l'encart « Hypothèses du porteur »
    assert "Hypothèses du porteur" in html and "sourcé" in html


# ── T4 — charge foncière négative dite en clair, jamais un euro négatif ────────────────────────
def test_t4_charge_negative_verdict_en_clair():
    b = fb.calculer(PROG, HYP)
    assert b["charge"]["centrale"] < 0                      # bien un cas négatif
    html = financier.rendu({}, _ctx(b, {"regime_tva_saisi": {"valeur": "autre", "origine": "saisi"}}))
    assert "aucun achat de terrain" in html
    assert "il lui manque" in html
    # le déficit est le |charge| arrondi (≈ 333 k€), pas un « -333 » brut dans le verdict
    verdict_zone = html[html.find("verdict"):html.find("Hypothèses du porteur")]
    assert "-333" not in verdict_zone and "-332" not in verdict_zone


def test_t4_seuil_et_marge_residuelle_negatifs_en_clair():
    b = fb.calculer(PROG, HYP)
    assert b["seuil_rentabilite"] < 0
    html = financier.rendu({}, _ctx(b, {"regime_tva_saisi": {"valeur": "autre", "origine": "saisi"}}))
    assert "aucun prix" in html and "viable" in html      # seuil de rentabilité négatif (apostrophe échappée)
    if b["marge_residuelle_pct"] is not None and b["marge_residuelle_pct"] < 0:
        assert "perd de l" in html and "argent" in html   # marge résiduelle négative


# ── T5 — garde : prix bailleur social > prix libre = hors marché ───────────────────────────────
def test_t5_prix_bailleur_superieur_au_libre_hors_marche():
    hm = fb._hors_marche(prix_sortie=4500, cout=2550, prix_bailleur=5500)
    assert hm is not None
    assert hm["champ"] == "Prix de vente au bailleur social"
    assert "toujours inférieure au prix du marché libre" in hm["raison"]


def test_t5_prix_bailleur_plausible_passe():
    assert fb._hors_marche(prix_sortie=4500, cout=2550, prix_bailleur=3200) is None
    # borne absolue toujours active en plus de la garde relationnelle
    assert fb._hors_marche(prix_sortie=4500, cout=2550, prix_bailleur=550000) is not None


def test_t5_bilan_bloque_avec_le_bon_conseil():
    b = fb.calculer(PROG, dict(HYP, prix_sortie=4500, prix_bailleur=5500, part_sociale_pct=30))
    assert b["hors_marche"] is not None
    html = financier.rendu({}, _ctx(b, {"regime_tva_saisi": {"valeur": "autre", "origine": "saisi"}}))
    assert "Hypothèse hors marché" in html
    assert "il doit rester sous le prix de vente libre" in html   # conseil dédié, pas « prix total »
