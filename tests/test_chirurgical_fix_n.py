"""CHIRURGICAL-FIX-1 — LOT N (7ᵉ passage du relecteur). Liste fermée de trois points sur le Bilan.

  1. Aucune sortie sur une saisie rejetée : une case de saisie doit être VIDE ou un NOMBRE dans ses
     bornes ; dès qu'une case est fausse (texte, négatif, TVA hors [0,1]), TOUTES les cases calculées
     affichent « saisie invalide » — aucun nombre, aucune erreur Excel. Test de robustesse permanent.
  2. Les mêmes alertes dans le PDF et l'Excel : l'alerte « surface vendable > surface de plancher »
     apparaît dans le PDF ; une surface vendable positive avec une SDP nulle/vide alerte des deux ;
     le seuil se compare sur les décimales (595,1 > 595 alerte).
  3. La couverture : les hypothèses (scénario + prix) sont nommées (plus de « aucune Étude reliée ») ;
     sur une parcelle sans programme, le bandeau reprend la distinction du Dossier (bâti conservé /
     terrain libéré), jamais un faux « aucune capacité à bâtir ».
"""
from __future__ import annotations

import io
import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labuse.bilan.excel import classeur_bilan, classeur_bilan_bytes  # noqa: E402
from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste, SOURCE  # noqa: E402
from labuse.bilan.reperes import bandeau_sans_programme  # noqa: E402

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _bilan_complet() -> EntreesBilan:
    """Un bilan avec de VRAIES saisies partout : programme + produit (TVA) + achat + construction."""
    return EntreesBilan(
        programme=Programme(terrain=1703, sdp=795, surface_taxable=795),
        produits=[Produit("Log", lots=8, suv=572, prix_ttc_m2_suv=4318, tva=0.085)],
        postes={"achat": SaisiePoste(1000, "saisi"), "constr": SaisiePoste(2000, "saisi")},
    )


def _saisie_cells(ws):
    """Les cases de SAISIE, lues des validations Excel : coûts (≥ 0) vs TVA (entre 0 et 1)."""
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


# ── N1 — aucune sortie sur une saisie rejetée (robustesse, moteur de tableur indépendant) ─────
def test_n1_robustesse_toutes_les_cases(tmp_path):
    formulas = pytest.importorskip("formulas")
    import numpy as np
    wb = classeur_bilan(_bilan_complet())
    ws = wb.active
    cout_cells, tva_cells = _saisie_cells(ws)
    assert cout_cells and tva_cells
    R = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}
    # cases CALCULÉES représentatives : lignes (via sous-total), sous-totaux, totaux, CA TTC/HT, résultat.
    _bloc_tot = next(lbl for lbl in R if isinstance(lbl, str) and lbl.startswith("Total — "))
    sorties = [f"D{R['Dépenses totales']}", f"F{R['Dépenses totales']}",
               f"D{R['Chiffre d\'affaires']}", f"F{R['Chiffre d\'affaires']}",
               f"D{R['Résultat net']}", f"F{R['Total produits']}", f"D{R[_bloc_tot]}"]

    p = tmp_path / "rob.xlsx"
    p.write_bytes(classeur_bilan_bytes(_bilan_complet()))
    xl = formulas.ExcelModel().loads(str(p)).finish()
    sol0 = xl.calculate()
    pre = next(iter(sol0)).rsplit("!", 1)[0] + "!"   # '[ROB.XLSX]BILAN'!

    def _val(cell):
        return np.asarray(cell.value).ravel()[0]

    def calc(inputs):
        sol = xl.calculate(inputs={pre + k: v for k, v in inputs.items()})
        vus = {}
        for k, v in sol.items():
            ku = k.upper()
            for coord in sorties:
                if ku.endswith("!" + coord):
                    vus[coord] = _val(v)
        return vus

    MATRICE_COUT = [(-5, False), ("n/a", False), (0, True), (3.5, True), (1e9, True)]
    MATRICE_TVA = [(-0.1, False), ("n/a", False), (0, True), (0.085, True), (5, False)]  # 5 > 1 = hors bornes

    def _verifie(vus, valide):
        for coord, raw in vus.items():
            s = str(raw)
            assert "#" not in s, f"{coord} = {s!r} (erreur Excel interdite)"
            if valide:
                assert s != "saisie invalide", f"{coord} valide mais bloquée ({s!r})"
            else:
                # une saisie invalide ne laisse NI nombre NI erreur : seulement « saisie invalide ».
                assert s == "saisie invalide", f"{coord} = {s!r} (devrait être « saisie invalide »)"

    for cells, matrice in ((cout_cells, MATRICE_COUT), (tva_cells, MATRICE_TVA)):
        for cell in cells:
            for valeur, valide in matrice:
                _verifie(calc({cell: valeur}), valide)

    # « vide » = l'état blanc par défaut des cases non saisies : le bilan calcule, sans « saisie invalide ».
    base = calc({})
    assert all("#" not in str(v) and str(v) != "saisie invalide" for v in base.values())


def test_n1_validite_rejette_le_texte():
    """La cellule de validité exige ISNUMBER (un texte collé n'est pas un nombre) + bornes (≥ 0, TVA 0..1)."""
    ws = classeur_bilan(_bilan_complet()).active
    i1 = ws["I1"].value
    assert isinstance(i1, str) and "ISNUMBER" in i1 and "ISBLANK" in i1 and "saisie invalide" in i1


def test_n1_toutes_les_cases_calculees_sont_enveloppees():
    """LOT O 1 — TOUTE formule de la feuille (y compris les alertes de surface) est enveloppée par la
    validité `=IF(I1<>"","saisie invalide",…)` ; SEULE la cellule de validité elle-même est épargnée."""
    ws = classeur_bilan(_bilan_complet()).active
    nues = []
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if not (isinstance(v, str) and v.startswith("=")):
                continue
            if c.coordinate == "I1":
                continue
            if not v.startswith('=IF(I1<>"",'):
                nues.append((c.coordinate, v[:40]))
    assert not nues, f"cases calculées NON enveloppées par la validité : {nues[:5]}"


# ── N2 — les mêmes alertes dans le PDF et l'Excel ────────────────────────────────────────────
def test_n2_suv_sdp_dans_le_pdf():
    """L'alerte « surface vendable > surface de plancher » apparaît dans le BANDEAU du PDF."""
    from labuse.bilan.pdf import construire_html
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=400),
                     produits=[Produit("X", suv=600, prix_ttc_m2_suv=4000, tva=0.085)])
    gf = {"alertes": ["Surface vendable (600 m²) supérieure à la surface de plancher (400 m²) — "
                      "incohérent (le chiffre d'affaires est surestimé)."], "programme_saisi": True}
    html, _ = construire_html(Moteur().calculer(e), idu="x", jour=date(2026, 11, 16), garde_fou=gf)
    assert "surface vendable" in html.lower() and "surface de plancher" in html.lower()


def test_n2_suv_positive_sdp_vide_et_decimales():
    e0 = EntreesBilan(programme=Programme(sdp=None),
                      produits=[Produit("X", suv=400, prix_ttc_m2_suv=4000, tva=0.085)])
    assert any(a["cible"] == "suv_sdp" for a in Moteur().calculer(e0).vraisemblance)   # SDP vide → alerte
    e1 = EntreesBilan(programme=Programme(sdp=595),
                      produits=[Produit("X", suv=595.1, prix_ttc_m2_suv=4000, tva=0.085)])
    assert any(a["cible"] == "suv_sdp" for a in Moteur().calculer(e1).vraisemblance)   # 595,1 > 595 (décimal)
    e2 = EntreesBilan(programme=Programme(sdp=595),
                      produits=[Produit("X", suv=594.9, prix_ttc_m2_suv=4000, tva=0.085)])
    assert not any(a["cible"] == "suv_sdp" for a in Moteur().calculer(e2).vraisemblance)  # 594,9 < 595


def test_n2_excel_formule_suv_sdp_gere_sdp_vide():
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=400),
                     produits=[Produit("X", suv=600, prix_ttc_m2_suv=4000, tva=0.085)])
    ws = classeur_bilan(e).active
    f = [c.value for row in ws.iter_rows() for c in row
         if isinstance(c.value, str) and "supérieure à la surface de plancher" in c.value]
    assert f and "ISBLANK" in f[0] and "=0" in f[0]      # alerte aussi si SDP nulle / vide


def test_n2_garde_fou_porte_suv_sdp_sur_les_decimales():
    from labuse.bilan import reperes
    import labuse.faisabilite.surface_retenue as sr
    from labuse.exports import etude_faisabilite as ef
    reperes.sources_parcelle = lambda db, idu: {}
    reperes._emprise_batie = lambda db, idu: 0
    sr.estimation_rapide_m2 = lambda db, idu: None
    ef.scenario_etude_persiste = lambda db, idu: None
    gf = reperes.garde_fou_bilan(db=None, idu="x", sdp_saisie=595, suv_saisie=595.1, programme_saisi=True)
    assert any("surface de plancher" in a for a in gf["alertes"])


# ── N3 — la couverture ───────────────────────────────────────────────────────────────────────
def test_n3_entete_nomme_les_hypotheses_est_cable():
    """La route dérive `etude_reliee` / `prix_demande` (`_hypotheses_bilan`) et les passe au rendu : la
    couverture ne reste plus bloquée sur « aucune Étude reliée · non renseigné »."""
    b = (_SRC / "api" / "bilan.py").read_text()
    assert "def _hypotheses_bilan(" in b
    assert "etude_reliee=_etude_reliee" in b and "prix_demande=_prix_demande" in b
    from labuse.bilan.pdf import construire_html
    e = _bilan_complet()
    html, _ = construire_html(Moteur().calculer(e), idu="x", jour=date(2026, 11, 16),
                              etude_reliee="scénario de l'Étude (8 lots, 795 m²) · prix de vente = neuf VEFA commune",
                              prix_demande=4318)
    assert "neuf VEFA" in html and "aucune Étude reliée" not in html


def test_n3_bandeau_reprend_la_distinction_du_dossier():
    # IS0448-like : constructible mais 0 m² en l'état, 85 m² en terrain libéré → la distinction, pas un
    # faux « aucune capacité à bâtir ».
    gf = {"programme_saisi": False, "non_constructible": False,
          "capacite_batie_conservee_m2": 0, "capacite_terrain_libere_m2": 85}
    _titre, bas = bandeau_sans_programme(gf)
    assert "0 m² en l'état (bâti conservé)" in bas and "85 m² estimés en terrain libéré" in bas
    assert "aucune capacité à bâtir" not in bas
    # AM0838-like : habitat interdit → là, « aucune capacité résidentielle » est juste.
    gf2 = {"programme_saisi": False, "non_constructible": True,
           "capacite_batie_conservee_m2": None, "capacite_terrain_libere_m2": None}
    _t2, bas2 = bandeau_sans_programme(gf2)
    assert "aucune capacité résidentielle" in bas2


def test_n3_bandeau_pdf_et_excel_identiques():
    """Le bandeau « sans programme » est le MÊME texte en PDF et en Excel (source partagée)."""
    from labuse.bilan.pdf import construire_html
    e = EntreesBilan(programme=Programme(terrain=959), produits=[], postes={"txLog": SaisiePoste(49.06, SOURCE)})
    gf = {"alertes": ["Scénario « terrain libéré »."], "programme_saisi": False,
          "non_constructible": False, "capacite_batie_conservee_m2": 0, "capacite_terrain_libere_m2": 85}
    html, _ = construire_html(Moteur().calculer(e), idu="x", jour=date(2026, 11, 16), garde_fou=gf)
    ws = classeur_bilan(e, None, "t", garde_fou=gf).active
    for frag in ("Aucun programme", "bâti conservé", "terrain libéré"):
        assert frag in html and frag in (ws["A2"].value or "")
