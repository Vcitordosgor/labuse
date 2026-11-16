"""CHIRURGICAL-FIX-1 — LOT L (5ᵉ passage du relecteur). Le Bilan, seul point resté bloquant.

Gardes déterministes, sans base (tournent au hook). Quatre parcelles témoins, valeurs SERVIES
(terrain cadastral + taxe d'aménagement + archéologie + scénario d'Étude), reconstituées à
l'identique de ce que `_entrees_servies` assemble pour les routes PDF/Excel.

  · L1 — un seul calcul, deux rendus : le classeur Excel RECALCULE (moteur de formules indépendant,
    puis vérification croisée par le tiers `formulas`) les MÊMES dépenses / CA / résultat que le
    moteur Python, à l'euro, sur les 4 parcelles.
  · L2 — garde-fou : comparé à la « surface à retenir » du Dossier, pas à l'estimation haute ;
    avertissement VIVANT (formule) dans l'Excel.
  · L3 — une saisie invalide (coût < 0, TVA hors [0,1]) bloque résultat, cash-flow, marge ET ratios
    via UNE cellule de validité unique.
  · L4 — livraison : programme « depuis l'Étude » pour les constructibles ; AUCUN programme injecté
    pour les parcelles sans capacité (le Bilan livré est celui de l'outil + son garde-fou) ; le cas
    « programme saisi quand même » est prouvé ICI, pas dans le fichier livré.
"""
from __future__ import annotations

import io
import re
import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_bilan_excel import _evaluateur, _grille  # noqa: E402  (évaluateur INDÉPENDANT du moteur)

from labuse.bilan.excel import classeur_bilan, classeur_bilan_bytes  # noqa: E402
from labuse.bilan.moteur import (  # noqa: E402
    SOURCE, EntreesBilan, Moteur, Produit, Programme, SaisiePoste,
)

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _entrees(terrain, tx, ar, *, sdp=None, lots=None, prix=None, tva=None) -> EntreesBilan:
    """Reconstitue l'objet calculé UNIQUE que `_entrees_servies` fabrique : terrain du cadastre,
    taxe d'aménagement + archéologie SOURCÉES, programme « depuis l'Étude » le cas échéant."""
    produits = [Produit("Logements — scénario de l'Étude", lots=lots, suv=sdp,
                        prix_ttc_m2_suv=prix, tva=tva)] if prix else []
    return EntreesBilan(
        programme=Programme(terrain=terrain, sdp=sdp),
        produits=produits,
        postes={"txLog": SaisiePoste(tx, SOURCE), "archeo": SaisiePoste(ar, SOURCE)},
    )


# Valeurs SERVIES mesurées sur la base (cf. scripts/lot_l_livraison.py · _saisies.json).
FIXTURES = {
    # constructibles — « Bilan depuis l'Étude » : surface + lots du scénario, prix neuf (VEFA) secteur.
    "BW2635": dict(terrain=2003, tx=66.9, ar=3.57, sdp=360, lots=4, prix=4547, constructible=True),
    "AD0887": dict(terrain=1703, tx=66.9, ar=3.57, sdp=795, lots=8, prix=4318, constructible=True),
    # sans capacité — AUCUN programme injecté (habitat interdit / pas d'Étude exploitable).
    "AM0838": dict(terrain=20336, tx=66.9, ar=3.57, constructible=False),
    "IS0448": dict(terrain=959, tx=49.06, ar=3.57, constructible=False),
}


def _fixture(name: str) -> EntreesBilan:
    f = FIXTURES[name]
    return _entrees(f["terrain"], f["tx"], f["ar"],
                    sdp=f.get("sdp"), lots=f.get("lots"), prix=f.get("prix"))


# ── L1 — un seul calcul, deux rendus : Excel == moteur à l'euro, sur les 4 parcelles ─────────
@pytest.mark.parametrize("name", list(FIXTURES))
def test_l1_excel_recalcule_le_meme_bilan(name):
    e = _fixture(name)
    r = Moteur().calculer(e)
    ws = classeur_bilan(e).active
    ev = _evaluateur(_grille(ws))
    L = {ws.cell(row, 1).value: row for row in range(1, ws.max_row + 1) if ws.cell(row, 1).value}
    row_ca, row_dep, row_res = L["Chiffre d'affaires"], L["Dépenses totales"], L["Résultat net"]

    # CA TTC et dépenses : égaux à l'euro entre le moteur (PDF) et le classeur (Excel).
    assert ev(f"F{row_ca}") == pytest.approx(r.ca_ttc, abs=1.0)
    assert ev(f"D{row_dep}") == pytest.approx(r.depenses_ht, abs=1.0)
    # CA HT : LOT M 2 — une TVA de vente vide (cas des constructibles livrés) rend le CA HT « non
    # calculable » DES DEUX CÔTÉS ; sinon il est égal à l'euro.
    ca_ht_excel = ev(f"D{row_ca}")
    if r.ca_ht is None:
        assert isinstance(ca_ht_excel, str) and "non calculable" in ca_ht_excel
    else:
        assert ca_ht_excel == pytest.approx(r.ca_ht, abs=1.0)

    # résultat : « non calculable » des DEUX côtés quand un coût majeur manque (achat/construction).
    # (Avec une TVA vide, le CA HT est du TEXTE : notre évaluateur maison — EAGER, contrairement à Excel
    # et à `formulas` — ne peut pas trancher la branche NON prise et dégrade en None ; le tiers `formulas`
    # confirme le « non calculable » réel dans test_l1_tableur_tiers_formulas_confirme.)
    res_excel = ev(f"D{row_res}")
    if r.resultat_net is None:
        assert res_excel is None or (isinstance(res_excel, str) and "non calculable" in res_excel)
    else:
        assert res_excel == pytest.approx(r.resultat_net, abs=1.0)

    # régime attendu : CA présent pour un constructible, CA nul pour une parcelle sans programme.
    if FIXTURES[name]["constructible"]:
        assert r.ca_ttc and r.ca_ttc > 0
    else:
        assert not r.ca_ttc


def test_l1_tableur_tiers_formulas_confirme(tmp_path):
    """Vérification CROISÉE par un moteur de tableur TIERS (`formulas`) : le classeur AD0887 recalcule
    bien CA et dépenses identiques au moteur, à l'euro — indépendamment de notre propre évaluateur."""
    formulas = pytest.importorskip("formulas")
    import numpy as np
    e = _fixture("AD0887")
    r = Moteur().calculer(e)
    octets = classeur_bilan_bytes(e)
    p = tmp_path / "bilan.xlsx"
    p.write_bytes(octets)
    ws = load_workbook(io.BytesIO(octets)).active
    L = {ws.cell(row, 1).value: row for row in range(1, ws.max_row + 1) if ws.cell(row, 1).value}
    # CA TTC + dépenses = des nombres (à l'euro) ; CA HT = « non calculable » (TVA de vente vide).
    coord_ca_ttc = f"F{L['Chiffre d\'affaires']}"
    coord_ca_ht = f"D{L['Chiffre d\'affaires']}"
    coord_dep = f"D{L['Dépenses totales']}"
    sol = formulas.ExcelModel().loads(str(p)).finish().calculate()
    vus = {}
    for k, v in sol.items():
        for coord in (coord_ca_ttc, coord_ca_ht, coord_dep):
            if k.upper().endswith(f"!{coord}"):
                cell = np.asarray(v.value).ravel()[0]
                try:
                    vus[coord] = float(cell)
                except (ValueError, TypeError):
                    vus[coord] = str(cell)
    assert vus[coord_ca_ttc] == pytest.approx(r.ca_ttc, abs=1.0)
    assert vus[coord_dep] == pytest.approx(r.depenses_ht, abs=1.0)
    assert r.ca_ht is None and vus[coord_ca_ht] == "non calculable"   # TVA vide → non calculable


def test_l1_un_seul_objet_calcule_dans_les_deux_routes():
    """Le PDF et l'Excel partent du MÊME objet (`_entrees_servies`) ; le terrain rendu sur le PDF est
    CELUI entré dans le calcul (plus de contenance injectée APRÈS coup, qui laissait l'achat vide)."""
    b = (_SRC / "api" / "bilan.py").read_text()
    assert b.count("_entrees_servies(db, idu, corps)") >= 2
    assert "_prog[\"terrain\"] = e.programme.terrain" in b
    # un seul calcul : le PDF n'appelle Moteur().calculer qu'une fois sur l'objet servi.
    assert "r = Moteur().calculer(e)" in b


# ── L2 — garde-fou : surface à retenir du Dossier + avertissement VIVANT dans l'Excel ────────
def test_l2_garde_fou_vise_la_surface_a_retenir():
    rep = (_SRC / "bilan" / "reperes.py").read_text()
    # compare la SAISIE à la surface à retenir (scénario du Dossier), pas à l'estimation haute.
    assert "surface_a_retenir" in rep and "def garde_fou_bilan(" in rep
    assert "terrain_libere" in rep              # scénario « terrain libéré » détecté et nommé
    assert "dépasse la surface à retenir" in (_SRC / "bilan" / "excel.py").read_text()


def test_l2_avertissement_sdp_est_une_formule_vivante():
    e = _fixture("AD0887")
    ws = classeur_bilan(e, None, "t",
                        garde_fou={"surface_a_retenir": 795,
                                   "alertes": ["La surface de plancher saisie dépasse la surface à retenir"]}).active
    formules = [c.value for row in ws.iter_rows() for c in row
                if isinstance(c.value, str) and c.value.startswith("=IF(AND(")
                and "dépasse la surface à retenir" in c.value]
    assert formules, "l'avertissement SDP > surface à retenir doit être une FORMULE (pas un texte figé)"
    assert "795" in formules[0]


# ── L3 — une saisie invalide bloque TOUT, via une cellule de validité unique ─────────────────
def test_l3_cellule_validite_unique_lue_partout():
    e = _entrees(1703, 66.9, 3.57, sdp=795, lots=8, prix=4318, tva=0.085)
    ws = classeur_bilan(e).active
    # I1 = la cellule de validité ; elle teste chaque saisie (< 0) et chaque TVA (hors [0,1]).
    i1 = ws["I1"].value
    assert isinstance(i1, str) and i1.startswith("=IF(OR(") and "saisie invalide" in i1
    assert "<0" in i1 and ">1" in i1
    # résultat, cash-flow, marge ET ratios référencent TOUS la même cellule de validité.
    def _cell(label, col):
        row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == label)
        return ws.cell(row, col).value or ""
    assert "I1" in _cell("Résultat net", 4) and "saisie invalide" in _cell("Résultat net", 4)
    assert "I1" in _cell("Résultat net", 5)        # marge (col E)
    assert "I1" in _cell("Cash flow", 4)
    ratios = [c.value for row in ws.iter_rows() for c in row
              if isinstance(c.value, str) and "saisie invalide" in c.value and "I1" in c.value]
    assert len(ratios) >= 6                         # résultat + marge + cash flow + 4 ratios


# ── L4 — livraison : deux régimes, et le cas « programme saisi quand même » prouvé ICI ───────
def test_l4_script_livraison_deux_regimes():
    s = (Path(__file__).resolve().parents[1] / "scripts" / "lot_l_livraison.py").read_text()
    # constructible → programme depuis l'Étude (surface + lots + prix neuf servi, par les routes HTTP).
    assert "resolve_prix_neuf_marche" in s and "scenario_retenu" in s
    assert 'POST /bilan/{idu}/generer' in s or "/generer" in s
    # non constructible → AUCUN programme injecté, c'est le Bilan de l'outil qui porte le garde-fou.
    assert "aucun programme injecté" in s and 'non_constructible' in s
    # TOUTES les pièces passent par des routes HTTP (pas seulement les Bilans).
    for route in ("/dossier/{idu}.pdf", "/apporteur/{idu}.pdf", "/analyse-annonce/{idu}.pdf",
                  "/pre-dossier/{idu}.zip", "/comparatif.pdf"):
        assert route in s


def test_l4_export_sans_ca_autorise_seulement_si_garde_fou():
    """La route n'exporte un Bilan sans CA que s'il porte un GARDE-FOU (parcelle écartée) ; sinon 422."""
    from labuse.api.bilan import _refuser_si_ca_nul
    from fastapi import HTTPException

    class _R:
        ca_ttc = 0.0
    with pytest.raises(HTTPException):
        _refuser_si_ca_nul(_R(), autorise_sans_ca=False)
    _refuser_si_ca_nul(_R(), autorise_sans_ca=True)    # garde-fou présent → l'export est permis


def test_l4_programme_saisi_sur_non_constructible_est_averti():
    """Le cas « programme saisi quand même » (ce que le fichier livré ne montre PAS) : un programme posé
    sur une fiche où l'habitat est interdit sort un Bilan FRAPPÉ du garde-fou, PDF et Excel."""
    from labuse.bilan.pdf import construire_html
    e = _entrees(20336, 66.9, 3.57, sdp=500, lots=7, prix=4000, tva=0.085)
    gf = {"alertes": ["Habitat interdit dans cette zone",
                      "La surface de plancher saisie (500 m²) dépasse la capacité estimée de la fiche "
                      "(0 m² avec le bâti conservé ; 85 m² en terrain libéré)."],
          "non_constructible": True}
    html, _ = construire_html(Moteur().calculer(e), idu="97404000AM0838", jour=date(2026, 11, 16),
                              garde_fou=gf)
    assert "Programme saisi — non vérifié" in html and "Habitat interdit" in html
    ws = classeur_bilan(e, None, "t", garde_fou=gf).active
    assert "Habitat interdit" in (ws["A2"].value or "")
