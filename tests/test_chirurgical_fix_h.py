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


def test_apporteur_liste_alertes_complete_et_filtree():
    """pt2 — `contraintes_parcelle_liste` = TOUTES les alertes SOFT/HARD de la fiche (aléas, zone
    humide, inondation TRI…), SAUF le marché (VEFA) / le scoring (déclassement, bâti, SDP résiduelle)
    / bassin versant. L'Apporteur n'omet plus la zone humide, et ne liste pas « Marché du neuf »."""
    from labuse.exports.robinet_fiche import EXTRACTEURS
    fiche = {"lines": [
        {"layer": "zone_humide", "result": "SOFT_FLAG", "libelle": "Zone humide inventoriée (100 %)"},
        {"layer": "tri_zone", "result": "SOFT_FLAG", "libelle": "Zone inondable TRI — extreme (85 %)"},
        {"layer": "risques", "result": "SOFT_FLAG", "libelle": "Aléa mouvement de terrain — faible"},
        {"layer": "vefa_neuf", "result": "SOFT_FLAG", "libelle": "Marché du logement neuf (VEFA)"},
        {"layer": "declassement", "result": "SOFT_FLAG", "libelle": "bâti significatif : 20 %"},
        {"layer": "residuel_socle", "result": "SOFT_FLAG", "libelle": "SDP résiduelle 0 m²"},
        {"layer": "bassin_versant", "result": "SOFT_FLAG", "libelle": "Bassin versant"},
        {"layer": "zone_plu", "result": "PASS", "libelle": "zone U"},  # PASS → ignoré
    ]}
    out = EXTRACTEURS["contraintes_parcelle_liste"](None, "x", fiche)
    layers = {x["nature"] for x in (out or [])}
    assert "zone_humide" in layers and "tri_zone" in layers and "risques" in layers
    assert not ({"vefa_neuf", "declassement", "residuel_socle", "bassin_versant"} & layers), \
        "marché/scoring/bassin versant ne sont pas des alertes"
    assert "zone_plu" not in layers  # une ligne PASS n'est pas une alerte


def test_apporteur_contraintes_sans_doublon_depuis_la_liste_complete():
    """pt2 — avec la liste complète, les prescriptions (DPU…) ne sont pas ajoutées une 2e fois."""
    from labuse.exports.blocs.apporteur import _contraintes

    class _V:
        def __init__(self, v): self.valeur = v
    valeurs = {"contraintes_parcelle_liste": _V([
        {"libelle": "Droit de préemption urbain renforcé — …", "nature": "dpu"},
        {"libelle": "Aléa mouvement de terrain — faible", "nature": "risques"},
    ]), "dpu_perimetre": _V(True)}
    out = _contraintes(valeurs)
    assert out.count("préemption") <= 1, "pas de doublon DPU quand la liste complète le porte"
    assert "Droit de préemption urbain" in out


def test_excel_garde_les_formules_quand_le_resultat_est_calculable():
    e = EntreesBilan(programme=Programme(terrain=2000), produits=[Produit("P1", 10, 600, 4785, 0.20)],
                     postes={"achat": SaisiePoste(valeur=1_000_000, etat="montant"),
                             "constr": SaisiePoste(valeur=1500, etat="ratio")})
    assert Moteur().calculer(e).resultat_net is not None, "pré-condition : calculable"
    rn = _ws_rows(classeur_bilan(e, titre="t"))["Résultat net"][0]
    assert str(rn).startswith("="), "un bilan calculable garde la formule Excel"
