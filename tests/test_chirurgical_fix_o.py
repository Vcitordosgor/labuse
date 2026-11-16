"""CHIRURGICAL-FIX-1 — LOT O (8ᵉ passage du relecteur). Liste fermée de deux points sur le Bilan.

  1. Le rejet s'étend à TOUTE la feuille : une valeur d'ERREUR Excel (#N/A, #DIV/0!, #VALUE!) ou un
     booléen collé dans une case ne contamine PLUS la cellule de validité ni les sorties ; « Total
     produits » (0 produit) suit la règle ; les alertes de surface ne s'affichent que sur une saisie
     valide. Test de robustesse : chaque case × {négatif, texte, erreurs, booléen, zéro, décimal,
     énorme}, et AUCUNE cellule calculée n'y échappe (on parcourt toutes les formules).
  2. Les mêmes décimales dans le PDF et l'Excel : aucun arrondi avant comparaison au seuil du Dossier
     (595,1 > 595 alerte des deux côtés), avec assez de décimales pour voir le dépassement.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from openpyxl.utils import get_column_letter, range_boundaries

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labuse.bilan.excel import classeur_bilan, classeur_bilan_bytes, _dec_m2  # noqa: E402
from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste, SOURCE  # noqa: E402

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _bilan_complet() -> EntreesBilan:
    return EntreesBilan(
        programme=Programme(terrain=1703, sdp=795, surface_taxable=795),
        produits=[Produit("Log", lots=8, suv=572, prix_ttc_m2_suv=4318, tva=0.085)],
        postes={"achat": SaisiePoste(1000, "saisi"), "constr": SaisiePoste(2000, "saisi")},
    )


def _saisie_cells(ws):
    cout, tva = [], []
    for dv in ws.data_validations.dataValidation:
        cibles = cout if dv.operator == "greaterThanOrEqual" else (tva if dv.operator == "between" else None)
        if cibles is None:
            continue
        for part in str(dv.sqref).split():
            c0, r0, c1, r1 = range_boundaries(part)
            for rr in range(r0, r1 + 1):
                for cc in range(c0, c1 + 1):
                    cibles.append(f"{get_column_letter(cc)}{rr}")
    return cout, tva


def _modele(octets: bytes):
    formulas = pytest.importorskip("formulas")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(octets)
        path = f.name
    xl = formulas.ExcelModel().loads(path).finish()
    pre = next(iter(xl.calculate())).rsplit("!", 1)[0] + "!"
    return xl, pre


def _val(v):
    import numpy as np
    cell = np.asarray(v.value).ravel()[0]
    try:
        return float(cell)
    except (ValueError, TypeError):
        return str(cell)


# ── O1 — le rejet s'étend à toute la feuille (erreurs Excel + booléens) ──────────────────────
def test_o1_validite_resiste_aux_erreurs_structurel():
    """Chaque test de la cellule de validité est enveloppé d'un IFERROR(…, TRUE) : une case en ERREUR
    (#N/A, …) est invalide, elle ne CONTAMINE pas I1 (en vrai Excel `#N/A<0` propage l'erreur)."""
    exc = (_SRC / "bilan" / "excel.py").read_text()
    assert "IFERROR(AND(NOT(ISBLANK(" in exc and "),TRUE)" in exc


def test_o1_aucune_cellule_calculee_n_echappe():
    """On injecte une ERREUR (#N/A) dans un coût et on PARCOURT TOUTES les formules de la feuille :
    AUCUNE cellule calculée n'échappe à « saisie invalide » (ni nombre, ni erreur), sauf la validité."""
    wb = classeur_bilan(_bilan_complet())
    ws = wb.active
    achat = next(r for r in range(1, ws.max_row + 1)
                 if ws.cell(r, 1).value and "Achat" in str(ws.cell(r, 1).value))
    formules = [c.coordinate for row in ws.iter_rows() for c in row
                if isinstance(c.value, str) and c.value.startswith("=")]
    xl, pre = _modele(classeur_bilan_bytes(_bilan_complet()))
    sol = xl.calculate(inputs={pre + f"C{achat}": "#N/A"})
    vus = {}
    for k, v in sol.items():
        coord = k.rsplit("!", 1)[-1].upper()
        vus[coord] = _val(v)
    echappent = [c for c in formules if c != "I1" and vus.get(c.upper()) != "saisie invalide"]
    assert not echappent, f"cellules calculées qui échappent au rejet : {echappent[:8]}"
    assert vus.get("I1") == "saisie invalide"   # la validité elle-même résiste à l'erreur


def test_o1_robustesse_erreurs_et_booleens():
    """Chaque case de saisie × {négatif, texte, #N/A, #DIV/0!, #VALUE!, booléen, zéro, décimal, énorme} :
    une saisie invalide ne laisse ni nombre ni erreur (tout « saisie invalide ») ; une valide recalcule."""
    import numpy as np  # noqa: F401
    wb = classeur_bilan(_bilan_complet())
    ws = wb.active
    cout_cells, tva_cells = _saisie_cells(ws)
    assert cout_cells and tva_cells
    R = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}
    bloc_tot = next(lbl for lbl in R if isinstance(lbl, str) and lbl.startswith("Total — "))
    sorties = [f"D{R['Dépenses totales']}", f"F{R['Dépenses totales']}",
               f"D{R['Chiffre d\'affaires']}", f"F{R['Chiffre d\'affaires']}",
               f"D{R['Résultat net']}", f"F{R['Total produits']}", f"D{R[bloc_tot]}"]
    xl, pre = _modele(classeur_bilan_bytes(_bilan_complet()))

    def calc(cell, valeur):
        sol = xl.calculate(inputs={pre + cell: valeur})
        out = {}
        for k, v in sol.items():
            c = k.rsplit("!", 1)[-1].upper()
            if c in sorties:
                out[c] = _val(v)
        return out

    ERREURS = ["#N/A", "#DIV/0!", "#VALUE!"]
    COUT = [(-5, False), ("texte", False), (True, False), (0, True), (3.5, True), (1e9, True)] + \
           [(e, False) for e in ERREURS]
    TVA = [(-0.1, False), ("texte", False), (True, False), (0, True), (0.085, True), (5, False)] + \
          [(e, False) for e in ERREURS]

    def verifie(vus, valide):
        for coord, raw in vus.items():
            s = str(raw)
            assert "#" not in s, f"{coord} = {s!r} (erreur Excel interdite)"
            if valide:
                assert s != "saisie invalide", f"{coord} valide mais bloquée"
            else:
                assert s == "saisie invalide", f"{coord} = {s!r} devrait être « saisie invalide »"

    for cells, matrice in ((cout_cells, COUT), (tva_cells, TVA)):
        for cell in cells:
            for valeur, valide in matrice:
                verifie(calc(cell, valeur), valide)


def test_o1_total_produits_sans_produit_suit_la_regle():
    """AM0838 / IS0448 (0 produit) : la ligne « Total produits » est une FORMULE gatée (plus un 0 figé)
    → elle affiche « saisie invalide » comme les autres après un rejet."""
    ws = classeur_bilan(EntreesBilan(programme=Programme(terrain=20336), produits=[],
                                     postes={"txLog": SaisiePoste(66.9, SOURCE)})).active
    tp = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == "Total produits")
    for col in (2, 3, 6, 7):      # lots, surface vendable, CA TTC, CA HT
        v = ws.cell(tp, col).value
        assert isinstance(v, str) and v.startswith('=IF(I1<>"",'), (col, v)


def test_o1_alertes_surface_gatees():
    """Les alertes de surface sont ENVELOPPÉES par la validité : sur une saisie invalide → « saisie
    invalide », PAS l'alerte à tort ; sur une saisie valide → l'alerte vivante."""
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=795),
                     produits=[Produit("X", suv=572, prix_ttc_m2_suv=4000, tva=0.085)])
    ws = classeur_bilan(e, garde_fou={"surface_a_retenir": 795}).active
    for marqueur in ("supérieure à la surface de plancher", "dépasse la surface à retenir"):
        cells = [c.value for row in ws.iter_rows() for c in row
                 if isinstance(c.value, str) and marqueur in c.value]
        assert cells and all(v.startswith('=IF(I1<>"",') for v in cells), marqueur


# ── O2 — les mêmes décimales dans le PDF et l'Excel ──────────────────────────────────────────
def test_o2_seuil_sans_arrondi_les_deux_cotes():
    rep = (_SRC / "bilan" / "reperes.py").read_text()
    exc = (_SRC / "bilan" / "excel.py").read_text()
    # aucun arrondi avant comparaison, dans aucun des deux contrôles :
    assert "sdp_saisie > sar_val" in rep and "round(sdp_saisie)" not in rep and "round(sar_val)" not in rep
    assert "{cell_sdp}>{cell_sar}" in exc and "{round(_sar)}" not in exc


def test_o2_garde_fou_decimales_visibles(monkeypatch):
    from labuse.bilan import reperes
    import labuse.faisabilite.surface_retenue as sr
    from labuse.exports import etude_faisabilite as ef
    monkeypatch.setattr(reperes, "sources_parcelle", lambda db, idu: {})
    monkeypatch.setattr(reperes, "_emprise_batie", lambda db, idu: 0)
    monkeypatch.setattr(sr, "estimation_rapide_m2", lambda db, idu: 595)
    monkeypatch.setattr(sr, "surface_a_retenir", lambda *a, **k: {"valeur_m2": 595, "phrase": ""})
    monkeypatch.setattr(ef, "scenario_etude_persiste", lambda db, idu: None)
    gf = reperes.garde_fou_bilan(db=None, idu="x", sdp_saisie=595.1, programme_saisi=True)
    al = [a for a in gf["alertes"] if "dépasse la surface à retenir" in a]
    assert al and "595,1 m²" in al[0] and "595 m²" in al[0]        # 595,1 contre 595 (pas 595 contre 595)
    gf2 = reperes.garde_fou_bilan(db=None, idu="x", sdp_saisie=595.0, programme_saisi=True)
    assert not [a for a in gf2["alertes"] if "dépasse la surface à retenir" in a]   # 595,0 = pas de dépassement


def test_o2_moteur_suv_sdp_decimales():
    e = EntreesBilan(programme=Programme(sdp=595),
                     produits=[Produit("X", suv=595.1, prix_ttc_m2_suv=4000, tva=0.085)])
    msg = [v["message"] for v in Moteur().calculer(e).vraisemblance if v["cible"] == "suv_sdp"]
    assert msg and "595,1 m²" in msg[0] and "595 m²" in msg[0]


def test_o2_dec_m2_format():
    assert _dec_m2(595.0) == "595" and _dec_m2(595.1) == "595,1" and _dec_m2(85) == "85"
