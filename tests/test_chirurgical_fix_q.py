"""CHIRURGICAL-FIX-1 — LOT Q (10ᵉ passage du relecteur). Un seul point sur le Bilan.

Dans le classeur, le texte des DEUX alertes de surface n'est PLUS figé à l'export : il se construit
DANS la formule à partir des cellules (surface de plancher, surface vendable, surface à retenir), avec
la même règle d'affichage que le PDF. Donc si on MODIFIE une cellule sans régénérer le classeur, le
texte cité SUIT la nouvelle valeur.

Test (exigé par le relecteur) : exporter le classeur, modifier les cellules SANS régénérer, recalculer
avec le moteur de tableur INDÉPENDANT (`formulas`), vérifier que l'alerte cite les valeurs modifiées,
et que le texte change ENCORE à une seconde modification. Trois cas : 595,01/595 ; 595,02/595,01 ;
85,01/85.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labuse.bilan.excel import classeur_bilan, classeur_bilan_bytes  # noqa: E402
from labuse.bilan.moteur import EntreesBilan, Produit, Programme, SaisiePoste, SOURCE  # noqa: E402

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _coords():
    """Coordonnées des cellules d'alerte + des cellules d'entrée (SDP, surface vendable, surface à
    retenir) dans le classeur type."""
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=600, surface_taxable=600),
                     produits=[Produit("Log", lots=8, suv=500, prix_ttc_m2_suv=4318, tva=0.085)],
                     postes={"txLog": SaisiePoste(66.9, SOURCE)})
    ws = classeur_bilan(e, garde_fou={"surface_a_retenir": 590}).active
    sar_alert = next(c.coordinate for row in ws.iter_rows() for c in row
                     if isinstance(c.value, str) and "dépasse la surface à retenir" in c.value)
    suv_alert = next(c.coordinate for row in ws.iter_rows() for c in row
                     if isinstance(c.value, str) and "supérieure à la surface de plancher" in c.value)
    cell_sdp = "B" + str(next(r for r in range(1, ws.max_row + 1)
                              if ws.cell(r, 1).value == "Surface de plancher (m²)"))
    cell_suv = "C" + str(next(r for r in range(1, ws.max_row + 1)
                              if ws.cell(r, 1).value == "Total produits"))
    return e, sar_alert, suv_alert, cell_sdp, cell_suv, "I2"   # I2 = surface à retenir (LOT Q)


def _modele():
    formulas = pytest.importorskip("formulas")
    e, sar_alert, suv_alert, cell_sdp, cell_suv, cell_sar = _coords()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(classeur_bilan_bytes(e, garde_fou={"surface_a_retenir": 590}))
        path = f.name
    xl = formulas.ExcelModel().loads(path).finish()
    pre = next(iter(xl.calculate())).rsplit("!", 1)[0] + "!"
    return xl, pre, sar_alert, suv_alert, cell_sdp, cell_suv, cell_sar


def _texte(xl, pre, coord, inputs):
    import numpy as np
    sol = xl.calculate(inputs={pre + k: v for k, v in inputs.items()})
    for k, v in sol.items():
        if k.upper().endswith("!" + coord):
            return str(np.asarray(v.value).ravel()[0])
    return ""


# ── Le texte des alertes se construit des cellules et SUIT la saisie (sans régénérer) ────────
def test_q_sdp_sar_suit_les_cellules_modifiees():
    xl, pre, sar_alert, _suv, cell_sdp, _cs, cell_sar = _modele()
    # cas 1 — 595,01 m² de plancher contre 595 m²
    t1 = _texte(xl, pre, sar_alert, {cell_sdp: 595.01, cell_sar: 595})
    assert "595,01 m²" in t1 and "595 m²" in t1, t1
    # cas 3 — IS0448 : 85,01 contre 85 (SECONDE modification : le texte change encore)
    t2 = _texte(xl, pre, sar_alert, {cell_sdp: 85.01, cell_sar: 85})
    assert "85,01 m²" in t2 and "85 m²" in t2, t2
    assert t1 != t2   # le texte a CHANGÉ à la seconde modification


def test_q_surface_vendable_suit_les_cellules_modifiees():
    xl, pre, _sar, suv_alert, cell_sdp, cell_suv, _cs = _modele()
    # cas 2 — 595,02 m² vendables contre 595,01 de plancher
    t1 = _texte(xl, pre, suv_alert, {cell_suv: 595.02, cell_sdp: 595.01})
    assert "595,02 m²" in t1 and "595,01 m²" in t1, t1
    # seconde modification : 700,25 contre 700,1 → le texte change encore
    t2 = _texte(xl, pre, suv_alert, {cell_suv: 700.25, cell_sdp: 700.1})
    assert "700,25 m²" in t2 and "700,1 m²" in t2, t2
    assert t1 != t2


def test_q_messages_construits_dans_la_formule_pas_figes():
    """Aucune valeur de surface n'est écrite EN DUR dans les formules d'alerte : elles référencent les
    cellules (TEXT/INT/SUBSTITUTE) — c'est ce qui permet au texte de suivre la saisie."""
    e, sar_alert, suv_alert, cell_sdp, cell_suv, cell_sar = _coords()
    ws = classeur_bilan(e, garde_fou={"surface_a_retenir": 590}).active
    f_sar = ws[sar_alert].value
    f_suv = ws[suv_alert].value
    # les formules se construisent des cellules…
    for f, refs in ((f_sar, (cell_sdp, cell_sar)), (f_suv, (cell_suv, cell_sdp))):
        assert "TEXT(" in f and all(ref in f for ref in refs), f
    # …et ne figent AUCUNE des valeurs d'entrée du classeur type (600 / 500 / 590).
    assert "600" not in f_sar and "590" not in f_sar
    assert "500" not in f_suv and "600" not in f_suv


# ── La règle d'affichage (dans la formule) : décimales quand il faut, virgule française ──────
def test_q_regle_affichage_dans_la_formule(monkeypatch):
    """Écart ≥ 1 m² → pas de décimale (« 412 » / « 555 ») ; écart < 1 m² → décimales visibles."""
    xl, pre, sar_alert, suv_alert, cell_sdp, cell_suv, cell_sar = _modele()
    # écart large : entiers, pas de décimales parasites
    t = _texte(xl, pre, suv_alert, {cell_suv: 555, cell_sdp: 412})
    assert "555 m²" in t and "412 m²" in t and "555,00" not in t and "412,00" not in t
    # écart fin : au moins deux décimales pour voir le dépassement
    t2 = _texte(xl, pre, sar_alert, {cell_sdp: 555.01, cell_sar: 555})
    assert "555,01 m²" in t2 and "555 m²" in t2
