"""CHIRURGICAL-FIX-H — gardes unitaires du contre-audit documents (LOT H).

pt1 — Bilan Excel & PDF : coûts requis manquants → résultat/marge/cash-flow GELÉS (comme le PDF),
pas un résultat = CA + 100 % de marge recalculés par formule. Taxe à assiette non renseignée → « — »,
pas « 0 € ».
"""
from __future__ import annotations

from labuse.bilan.excel import classeur_bilan
from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste


def _ws_rows(wb):
    return {r[0].value: (r[3].value, r[4].value) for r in wb.active.iter_rows() if r[0].value}


def test_excel_gele_resultat_si_cout_requis_manquant():
    # Programme + produit (donc un CA), AUCUN coût → le moteur ne calcule pas de résultat.
    e = EntreesBilan(programme=Programme(terrain=2000),
                     produits=[Produit("P1", 10, 600, 4785, 0.20)], postes={})
    assert Moteur().calculer(e).resultat_net is None, "pré-condition : incomplet"
    rows = _ws_rows(classeur_bilan(e, titre="t"))
    # Résultat net & cash-flow : texte « non calculable », PAS une formule « =D..-D.. ».
    assert rows["Résultat net"][0] == "non calculable — saisissez vos coûts"
    assert not str(rows["Résultat net"][0]).startswith("=")
    assert rows["Cash flow"][0] == "non calculable — saisissez vos coûts"
    # Marge % (colonne E de la ligne Résultat) : vide, jamais « 100 % ».
    assert rows["Résultat net"][1] in (None, "")
    # Renta nette / CA HT : vide quand incomplet (pas de division sur un texte).
    assert rows["Renta nette / CA HT"][1] in (None, "")


def test_excel_garde_les_formules_quand_le_resultat_est_calculable():
    e = EntreesBilan(programme=Programme(terrain=2000), produits=[Produit("P1", 10, 600, 4785, 0.20)],
                     postes={"achat": SaisiePoste(valeur=1_000_000, etat="montant"),
                             "constr": SaisiePoste(valeur=1500, etat="ratio")})
    assert Moteur().calculer(e).resultat_net is not None, "pré-condition : calculable"
    rn = _ws_rows(classeur_bilan(e, titre="t"))["Résultat net"][0]
    assert str(rn).startswith("="), "un bilan calculable garde la formule Excel"
