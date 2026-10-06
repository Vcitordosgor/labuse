"""BILAN-1 Lot 7 — recette « écran = PDF = Excel au centime ».

L'écran n'affiche que le résultat du moteur (/bilan/{idu}/calcul) : écran = moteur
par construction. Le PDF est bâti à partir de ce même résultat. L'Excel est vivant
et évalué ici. On prouve que les TROIS portent les mêmes totaux, au centime, sur
le témoin de la promotrice.
"""

from __future__ import annotations

import re

import pytest

from labuse.bilan.excel import classeur_bilan
from labuse.bilan.moteur import Moteur
from labuse.bilan.pdf import construire_html
from test_bilan_excel import _evaluateur, _grille
from test_bilan_moteur import entrees_temoin_promotrice


def _eur_fr(x: float) -> str:
    return f"{round(x):,}".replace(",", " ") + " €"


def test_ecran_pdf_excel_au_centime():
    e = entrees_temoin_promotrice()
    r = Moteur().calculer(e)
    assert r.complet

    # ÉCRAN = MOTEUR (l'écran rend r ; valeur de référence)
    res_moteur = r.resultat_net
    ca_moteur = r.ca_ht

    # PDF : bâti depuis r → doit porter le résultat net formaté du moteur
    html, _ = construire_html(r, idu="97415000BZ1065", commune="Saint-Paul")
    assert _eur_fr(res_moteur) in html, "le PDF doit afficher le résultat net du moteur"
    assert _eur_fr(ca_moteur) in html

    # EXCEL : évalué → mêmes totaux au centime
    ws = classeur_bilan(e)["Bilan"]
    ev = _evaluateur(_grille(ws))
    lignes = {ws.cell(row, 1).value: row for row in range(1, ws.max_row + 1) if ws.cell(row, 1).value}
    res_row = lignes["Résultat net"]
    ca_row = lignes["Chiffre d'affaires"]
    res_excel = ev(f"D{res_row}")
    ca_excel = ev(f"D{ca_row}")

    assert res_excel == pytest.approx(res_moteur, abs=1.0)
    assert ca_excel == pytest.approx(ca_moteur, abs=1.0)
    # et la marge affichée (PDF) = celle du moteur
    assert f"{r.marge_pct * 100:.1f}".replace(".", ",") in html
