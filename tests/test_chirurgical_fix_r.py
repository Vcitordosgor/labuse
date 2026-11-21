"""CHIRURGICAL-FIX-1 — LOT R (11ᵉ passage du relecteur). Un seul point sur le Bilan.

RÈGLE UNIQUE (PDF, Excel, moteur) : la PRÉCISION d'une surface est le CENTIÈME de m². Les deux
contrôles de surface COMPARENT les valeurs arrondies au centième et les AFFICHENT à deux décimales au
plus. Un écart < 0,01 m² n'est pas un dépassement → aucune alerte, dans aucun format. Toute alerte
affichée montre donc deux valeurs DISTINCTES.

Cas (dans les deux formats) :
  · 595,002 contre 595,001 → PAS d'alerte          · 85,001 contre 85 → PAS d'alerte
  · 595,01 contre 595 → alerte, valeurs distinctes  · 595,006 contre 595 → alerte « 595,01 contre 595 »
  · égalité stricte PDF / Excel sur le déclenchement, pour une série autour du seuil.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labuse.bilan.excel import classeur_bilan_bytes  # noqa: E402
from labuse.bilan.moteur import (  # noqa: E402
    EntreesBilan, Moteur, Produit, Programme, SaisiePoste, SOURCE,
    fmt_surfaces_paire, surface_depasse,
)

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _excel_alertes(sdp, suv, sar):
    """(texte SDP>surface à retenir, texte surface vendable>plancher) ÉVALUÉS par le moteur de tableur
    indépendant `formulas`. Chaîne vide = alerte NON déclenchée."""
    formulas = pytest.importorskip("formulas")
    import numpy as np
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=sdp, surface_taxable=sdp),
                     produits=[Produit("Log", lots=8, suv=suv, prix_ttc_m2_suv=4318, tva=0.085)],
                     postes={"txLog": SaisiePoste(66.9, SOURCE)})
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(classeur_bilan_bytes(e, garde_fou={"surface_a_retenir": sar}))
        path = f.name
    sol = formulas.ExcelModel().loads(path).finish().calculate()
    sar_t = suv_t = ""
    for _k, v in sol.items():
        s = str(np.asarray(v.value).ravel()[0])
        if "dépasse la surface à retenir" in s:
            sar_t = s
        if "supérieure à la surface de plancher" in s:
            suv_t = s
    return sar_t, suv_t


def _moteur_suv_fire(suv, sdp):
    e = EntreesBilan(programme=Programme(sdp=sdp),
                     produits=[Produit("X", suv=suv, prix_ttc_m2_suv=4000, tva=0.085)])
    return any(a["cible"] == "suv_sdp" for a in Moteur().calculer(e).vraisemblance)


# ── La règle (code) ──────────────────────────────────────────────────────────────────────────
def test_r_regle_au_centieme_code():
    m = (_SRC / "bilan" / "moteur.py").read_text()
    assert "PRECISION_SURFACE_M2 = 0.01" in m
    # arrondi au centième moitié-vers-le-haut (comme Excel), pas `round()` de Python :
    assert "def surface_depasse(" in m and "_round2(a) > _round2(b)" in m and "ROUND_HALF_UP" in m
    exc = (_SRC / "bilan" / "excel.py").read_text()
    assert "ROUND({cell_sdp},2)>ROUND({cell_sar},2)" in exc        # Excel compare au centième
    assert "ROUND({cell_suv},2)>ROUND({cell_sdp},2)" in exc


# ── Écart < 0,01 m² : AUCUNE alerte, dans les deux formats ───────────────────────────────────
def test_r_ecart_sous_centieme_pas_d_alerte():
    # surface à retenir : 595,002 de plancher contre 595,001 ; vendable : idem
    assert not surface_depasse(595.002, 595.001)          # règle
    assert not _moteur_suv_fire(595.002, 595.001)         # PDF (moteur)
    sar_t, suv_t = _excel_alertes(sdp=595.002, suv=595.002, sar=595.001)
    assert sar_t == "" and suv_t == ""                    # Excel : aucune alerte
    # IS0448 : 85,001 contre 85
    assert not surface_depasse(85.001, 85)
    sar_t2, _ = _excel_alertes(sdp=85.001, suv=50, sar=85)
    assert sar_t2 == ""


# ── Écart ≥ 0,01 m² : alerte avec deux valeurs DISTINCTES, dans les deux formats ─────────────
def test_r_595_01_contre_595_alerte_distincte():
    assert surface_depasse(595.01, 595)
    assert fmt_surfaces_paire(595.01, 595) == ("595,01", "595")
    sar_t, _ = _excel_alertes(sdp=595.01, suv=400, sar=595)
    assert "595,01 m²" in sar_t and "595 m²" in sar_t
    # deux valeurs distinctes (pas « 595 contre 595 »)
    assert sar_t.count("595,01 m²") == 1 and "595 m²" in sar_t.replace("595,01 m²", "")


def test_r_595_006_arrondi_a_595_01():
    # 595,006 s'arrondit à 595,01 → alerte « 595,01 contre 595 » (affichage = valeur arrondie)
    assert surface_depasse(595.006, 595)
    assert fmt_surfaces_paire(595.006, 595) == ("595,01", "595")
    sar_t, _ = _excel_alertes(sdp=595.006, suv=400, sar=595)
    assert "595,01 m²" in sar_t and "595 m²" in sar_t
    # surface vendable 595,006 contre 595 de plancher
    assert _moteur_suv_fire(595.006, 595)
    _, suv_t = _excel_alertes(sdp=595, suv=595.006, sar=590)
    assert "595,01 m²" in suv_t and "595 m²" in suv_t


# ── Égalité stricte PDF / Excel sur le déclenchement, autour du seuil ────────────────────────
def test_r_egalite_pdf_excel_serie():
    seuil = 595.0
    for delta in (0.0, 0.001, 0.004, 0.005, 0.006, 0.009, 0.01, 0.011, 0.02, 0.5, 1.0):
        suv = round(seuil + delta, 3)
        pdf_fire = surface_depasse(suv, seuil)            # PDF / moteur / garde-fou (règle unique)
        _, suv_t = _excel_alertes(sdp=seuil, suv=suv, sar=1_000_000)   # sar immense → seul suv>sdp peut tirer
        excel_fire = bool(suv_t)
        assert pdf_fire == excel_fire, (delta, suv, pdf_fire, excel_fire)
        if excel_fire:                                     # toute alerte affichée = deux valeurs distinctes
            import re
            nums = re.findall(r"(\d+(?:,\d+)?) m²", suv_t)
            assert len(nums) >= 2 and nums[0] != nums[1], (suv, suv_t)
