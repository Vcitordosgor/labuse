"""CHIRURGICAL-FIX-1 — LOT P (9ᵉ passage du relecteur). Un seul point sur le Bilan.

Les DEUX alertes de surface affichent LEURS DEUX valeurs, avec assez de décimales pour qu'on voie le
dépassement, dans le PDF (garde-fou / vraisemblance) COMME dans le classeur (message cité + format).
Règle d'affichage UNIQUE partagée : autant de décimales que nécessaire pour distinguer les deux
valeurs, au moins deux quand elles diffèrent de moins d'un m². Trois cas, dans les deux formats :
  · AD0887 « surface à retenir » : 595,01 m² de plancher contre 595 m²        → « 595,01 » / « 595 »
  · AD0887 « surface vendable »  : 595,02 m² vendables contre 595,01 de plancher → « 595,02 » / « 595,01 »
  · IS0448                        : 85,01 m² contre 85 m²                       → « 85,01 » / « 85 »
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labuse.bilan.excel import classeur_bilan  # noqa: E402
from labuse.bilan.moteur import (  # noqa: E402
    EntreesBilan, Moteur, Produit, Programme, SaisiePoste, SOURCE,
    fmt_surface_seule, fmt_surfaces_paire,
)

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _garde_fou(monkeypatch, *, sdp, sar, suv=None):
    from labuse.bilan import reperes
    import labuse.faisabilite.surface_retenue as sr
    from labuse.exports import etude_faisabilite as ef
    monkeypatch.setattr(reperes, "sources_parcelle", lambda db, idu: {})
    monkeypatch.setattr(reperes, "_emprise_batie", lambda db, idu: 0)
    monkeypatch.setattr(sr, "estimation_rapide_m2", lambda db, idu: sar)
    monkeypatch.setattr(sr, "surface_a_retenir", lambda *a, **k: {"valeur_m2": sar, "phrase": ""})
    monkeypatch.setattr(ef, "scenario_etude_persiste", lambda db, idu: None)
    return reperes.garde_fou_bilan(db=None, idu="x", sdp_saisie=sdp, suv_saisie=suv, programme_saisi=True)


def _excel_alertes(sdp, sar, suv):
    """Les deux formules d'alerte de surface du classeur (texte brut, avec leurs valeurs citées)."""
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=sdp, surface_taxable=sdp),
                     produits=[Produit("Log", lots=8, suv=suv, prix_ttc_m2_suv=4318, tva=0.085)],
                     postes={"txLog": SaisiePoste(66.9, SOURCE)})
    ws = classeur_bilan(e, garde_fou={"surface_a_retenir": sar}).active
    sar_cell = next((c.value for row in ws.iter_rows() for c in row
                     if isinstance(c.value, str) and "dépasse la surface à retenir" in c.value), "")
    suv_cell = next((c.value for row in ws.iter_rows() for c in row
                     if isinstance(c.value, str) and "supérieure à la surface de plancher" in c.value), "")
    return sar_cell, suv_cell


# ── La règle d'affichage unique ──────────────────────────────────────────────────────────────
def test_p_regle_affichage_unique():
    assert fmt_surfaces_paire(595.01, 595) == ("595,01", "595")
    assert fmt_surfaces_paire(595.02, 595.01) == ("595,02", "595,01")
    assert fmt_surfaces_paire(85.01, 85) == ("85,01", "85")
    # entiers → pas de décimales ; au moins 2 décimales quand l'écart < 1 m² (ici 0,5 → distingue).
    assert fmt_surfaces_paire(364, 535) == ("364", "535")
    assert fmt_surfaces_paire(100.5, 100) == ("100,5", "100")
    assert fmt_surface_seule(595.02) == "595,02" and fmt_surface_seule(85) == "85"


# ── Cas 1 — AD0887, surface à retenir : 595,01 contre 595 ────────────────────────────────────
def test_p_cas1_surface_a_retenir_pdf(monkeypatch):
    gf = _garde_fou(monkeypatch, sdp=595.01, sar=595)
    al = next(a for a in gf["alertes"] if "dépasse la surface à retenir" in a)
    assert "595,01 m²" in al and "595 m²" in al      # les DEUX valeurs, pas « 595 m² contre 595 m² »


def test_p_cas1_surface_a_retenir_excel():
    sar_cell, _ = _excel_alertes(sdp=595.01, sar=595, suv=400)
    assert "595,01 m²" in sar_cell and "595 m²" in sar_cell


# ── Cas 2 — AD0887, surface vendable : 595,02 contre 595,01 ──────────────────────────────────
def test_p_cas2_surface_vendable_pdf(monkeypatch):
    gf = _garde_fou(monkeypatch, sdp=595.01, sar=595, suv=595.02)
    al = next(a for a in gf["alertes"] if "supérieure à la surface de plancher" in a)
    assert "595,02 m²" in al and "595,01 m²" in al          # les deux valeurs, distinctes


def test_p_cas2_surface_vendable_moteur():
    e = EntreesBilan(programme=Programme(sdp=595.01),
                     produits=[Produit("X", suv=595.02, prix_ttc_m2_suv=4000, tva=0.085)])
    msg = next(v["message"] for v in Moteur().calculer(e).vraisemblance if v["cible"] == "suv_sdp")
    assert "595,02 m²" in msg and "595,01 m²" in msg


def test_p_cas2_surface_vendable_excel():
    _, suv_cell = _excel_alertes(sdp=595.01, sar=595, suv=595.02)
    assert "595,02 m²" in suv_cell and "595,01 m²" in suv_cell   # l'alerte CITE les deux (plus « aucun chiffre »)


# ── Cas 3 — IS0448 : 85,01 contre 85 ─────────────────────────────────────────────────────────
def test_p_cas3_is0448_pdf(monkeypatch):
    gf = _garde_fou(monkeypatch, sdp=85.01, sar=85)
    al = next(a for a in gf["alertes"] if "dépasse la surface à retenir" in a)
    assert "85,01 m²" in al and "85 m²" in al


def test_p_cas3_is0448_excel():
    sar_cell, _ = _excel_alertes(sdp=85.01, sar=85, suv=50)
    assert "85,01 m²" in sar_cell and "85 m²" in sar_cell


# ── Le PDF et l'Excel citent les MÊMES valeurs (règle partagée) ──────────────────────────────
def test_p_pdf_et_excel_memes_valeurs(monkeypatch):
    gf = _garde_fou(monkeypatch, sdp=595.01, sar=595, suv=595.02)
    sar_cell, suv_cell = _excel_alertes(sdp=595.01, sar=595, suv=595.02)
    # mêmes valeurs citées des deux côtés
    assert "595,01 m²" in next(a for a in gf["alertes"] if "dépasse" in a) and "595,01 m²" in sar_cell
    assert "595,02 m²" in next(a for a in gf["alertes"] if "supérieure" in a) and "595,02 m²" in suv_cell


# ── Les surfaces de la synthèse ne s'affichent plus arrondies au m² ──────────────────────────
def test_p_excel_surfaces_montrent_les_decimales():
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=595.01, surface_taxable=595.01),
                     produits=[Produit("Log", lots=8, suv=595.02, prix_ttc_m2_suv=4318, tva=0.085)])
    ws = classeur_bilan(e).active
    L = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}
    fmt = ws.cell(L["Surface de plancher"], 5).number_format
    assert "0.##" in fmt, fmt      # « 595,01 m² », pas arrondi au m²
