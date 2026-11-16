"""CHIRURGICAL-FIX-1 — LOT M (6ᵉ passage du relecteur). Le Bilan, liste fermée de 3 corrections.

  1. Les vraies valeurs de l'écran : la surface VENDABLE = la surface HABITABLE du scénario (≠ la
     surface de plancher). Contrôle de cohérence : surface vendable > surface de plancher → alerte.
  2. Une seule convention de TVA : net promoteur identique PDF/Excel (plus de 8,5 % forfaitaires) ;
     une TVA de vente VIDE n'est pas 0 % → CA HT / net promoteur / marge « non calculable » ; une
     saisie invalide bloque AUSSI les totaux (dépenses, CA), jamais un #VALUE!.
  3. Le terrain sans programme : pas de « surface à retenir » fantôme sur une parcelle non
     constructible ; seuil d'alerte identique PDF/Excel ; Bilan sans programme → « Aucun programme ».
"""
from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_bilan_excel import _evaluateur, _grille  # noqa: E402

from labuse.bilan.excel import classeur_bilan, classeur_bilan_bytes  # noqa: E402
from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste, SOURCE  # noqa: E402

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


def _ev_cell(ws, label, col):
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == label)
    return _evaluateur(_grille(ws))(f"{chr(64 + col)}{row}")


def _formulas_cells(octets: bytes, coords: list[str]) -> dict:
    """Résout des cellules avec le moteur de tableur TIERS `formulas` (court-circuite IF, comme Excel)."""
    formulas = pytest.importorskip("formulas")
    import numpy as np
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(octets)
        path = f.name
    sol = formulas.ExcelModel().loads(path).finish().calculate()
    out: dict[str, object] = {}
    for k, v in sol.items():
        for coord in coords:
            if k.upper().endswith(f"!{coord}"):
                cell = np.asarray(v.value).ravel()[0]
                try:
                    out[coord] = float(cell)
                except (ValueError, TypeError):
                    out[coord] = str(cell)
    return out


def _rows(ws):
    return {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}


# ── M1 — la surface vendable (SHAB) est distincte de la SDP + contrôle de cohérence ──────────
def test_m1_script_livraison_utilise_la_shab():
    s = (Path(__file__).resolve().parents[1] / "scripts" / "lot_m_livraison.py").read_text()
    # la surface VENDABLE livrée = la SHAB du scénario (comme l'écran), PAS la surface de plancher.
    assert 'prog.get("shab_estimee_m2")' in s and '"suv": prog["suv"]' in s
    assert '"sdp": round(float(sdp))' in s and '"suv": round(float(shab))' in s


def test_m1_coherence_suv_superieure_sdp_alerte():
    # surface vendable (900) > surface de plancher (795) → alerte de cohérence (CA surestimé).
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=795),
                     produits=[Produit("X", suv=900, prix_ttc_m2_suv=4000, tva=0.085)])
    msgs = [v["message"] for v in Moteur().calculer(e).vraisemblance if v["cible"] == "suv_sdp"]
    assert msgs and "supérieure à la surface de plancher" in msgs[0]
    # cas sain (SHAB < SDP) : pas d'alerte.
    e2 = EntreesBilan(programme=Programme(terrain=1703, sdp=795),
                      produits=[Produit("X", suv=572, prix_ttc_m2_suv=4000, tva=0.085)])
    assert not [v for v in Moteur().calculer(e2).vraisemblance if v["cible"] == "suv_sdp"]


def test_m1_excel_alerte_suv_sdp_est_vivante():
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=795),
                     produits=[Produit("X", suv=572, prix_ttc_m2_suv=4000, tva=0.085)])
    ws = classeur_bilan(e).active
    # LOT O 1 — l'alerte est désormais ENVELOPPÉE par la validité ; on la cherche par son contenu.
    formules = [c.value for row in ws.iter_rows() for c in row
                if isinstance(c.value, str) and "surface vendable > surface de plancher" in c.value
                and "AND(" in c.value]
    assert formules, "l'alerte surface vendable > surface de plancher doit être une FORMULE vivante"


# ── M2 — une seule convention de TVA ─────────────────────────────────────────────────────────
def _entrees_tva(tva):
    return EntreesBilan(programme=Programme(terrain=1703, sdp=795),
                        produits=[Produit("Log", lots=8, suv=572, prix_ttc_m2_suv=4318, tva=tva)],
                        postes={"txLog": SaisiePoste(66.9, SOURCE), "archeo": SaisiePoste(3.57, SOURCE)})


def test_m2_tva_vide_rend_tout_non_calculable():
    r = Moteur().calculer(_entrees_tva(None))
    # CA TTC reste connu (surface vendable × prix) ; CA HT / marge / résultat « non calculable ».
    assert r.ca_ttc == pytest.approx(572 * 4318, abs=1.0)
    assert r.ca_ht is None and r.ca_tva is None and r.resultat_net is None and r.marge_pct is None
    ratios = dict(r.ratios)
    for k in ("Prix moyen au m² de surface vendable HT",
              "Net promoteur m² de surface vendable TTC", "Renta nette / CA HT"):
        assert ratios[k] == "non calculable", (k, ratios[k])


def test_m2_pdf_tete_renta_non_calculable_si_tva_vide():
    """Le bloc « Ratios & programme » du PDF dit « non calculable » pour la renta quand la TVA de vente
    est vide (cohérent avec le net promoteur / le prix moyen), pas « — »."""
    from labuse.bilan.pdf import construire_html
    html, _ = construire_html(Moteur().calculer(_entrees_tva(None)), idu="x", jour=date(2026, 11, 16))
    import re
    bloc = re.sub(r"<[^>]+>", " ", html)
    m = re.search(r"Renta nette / CA HT\s+([^\s].{0,20})", bloc)
    assert m and "non calculable" in m.group(1)


def test_m2_net_promoteur_identique_pdf_et_excel():
    """Le PDF (moteur) n'ajoute plus 8,5 % forfaitaires : net promoteur = la TVA RÉELLE, comme l'Excel."""
    e = _entrees_tva(0.085)
    r = Moteur().calculer(e)
    net_pdf = dict(r.ratios)["Net promoteur m² de surface vendable TTC"]
    # sans frais d'acte/pack/proc, le net promoteur TTC = le prix TTC/m² (4 318 €), PAS 4 318 × 1,085.
    assert net_pdf == "4 318 €", net_pdf
    octets = classeur_bilan_bytes(e)
    ws = load_workbook(io.BytesIO(octets)).active
    row = next(r2 for r2 in range(1, ws.max_row + 1)
               if ws.cell(r2, 1).value == "Net promoteur m² de surface vendable TTC")
    vals = _formulas_cells(octets, [f"E{row}"])
    assert round(vals[f"E{row}"]) == 4318, vals        # Excel = 4 318 € aussi (même convention)


def test_m2_tva_vide_ca_ht_non_calculable_excel_tiers():
    octets = classeur_bilan_bytes(_entrees_tva(None))
    ws = load_workbook(io.BytesIO(octets)).active
    R = _rows(ws)
    v = _formulas_cells(octets, [f"D{R['Chiffre d\'affaires']}", f"F{R['Chiffre d\'affaires']}"])
    assert v[f"F{R['Chiffre d\'affaires']}"] == pytest.approx(572 * 4318, abs=1.0)   # CA TTC connu
    assert v[f"D{R['Chiffre d\'affaires']}"] == "non calculable"                     # CA HT non calculable


def test_m2_saisie_invalide_bloque_les_totaux():
    """Une TVA à 101 % (hors [0,1]) → la synthèse (dépenses ET CA), pas seulement le résultat, dit
    « saisie invalide » ; le CA TTC (indépendant de la TVA) reste le seul chiffre affiché."""
    e = EntreesBilan(programme=Programme(terrain=1703, sdp=795),
                     produits=[Produit("Log", lots=8, suv=572, prix_ttc_m2_suv=4318, tva=1.01)],
                     postes={"achat": SaisiePoste(1000, "saisi"), "constr": SaisiePoste(2000, "saisi")})
    octets = classeur_bilan_bytes(e)
    ws = load_workbook(io.BytesIO(octets)).active
    R = _rows(ws)
    coords = [f"D{R['Dépenses totales']}", f"D{R['Chiffre d\'affaires']}", f"D{R['Résultat net']}", "I1"]
    v = _formulas_cells(octets, coords)
    assert v["I1"] == "saisie invalide"
    assert v[f"D{R['Dépenses totales']}"] == "saisie invalide"      # le TOTAL dépenses est bloqué
    assert v[f"D{R['Chiffre d\'affaires']}"] == "saisie invalide"   # le CA HT est bloqué
    assert v[f"D{R['Résultat net']}"] == "saisie invalide"


def test_m2_ca_ht_total_additionne_jamais_sum():
    """Le CA HT total ADDITIONNE les produits avec « + » (jamais SUM, qui IGNORE le texte et rendrait 0
    sur une TVA vide — le bug « CA HT à zéro »)."""
    ex = (_SRC / "bilan" / "excel.py").read_text()
    assert '"+".join(prod_ht_cells)' in ex and "IFERROR" in ex


# ── M3 — le terrain sans programme ───────────────────────────────────────────────────────────
def test_m3_non_constructible_pas_de_surface_a_retenir(monkeypatch):
    """Sur une parcelle non constructible (habitat interdit), le garde-fou ne cite AUCUNE « surface à
    retenir » (plus de 8 125 m² venus d'une ancienne simulation) : seul le motif reste."""
    from labuse.bilan import reperes
    monkeypatch.setattr(reperes, "sources_parcelle",
                        lambda db, idu: {"non_constructible_motif": "Habitat interdit dans cette zone"})
    monkeypatch.setattr(reperes, "_emprise_batie", lambda db, idu: 500.0)

    def _sar(*a, **k):   # une ancienne simulation renverrait une grande surface
        return {"valeur_m2": 8125.0, "phrase": "terrain libéré"}
    import labuse.faisabilite.surface_retenue as sr
    monkeypatch.setattr(sr, "surface_a_retenir", _sar)
    monkeypatch.setattr(sr, "estimation_rapide_m2", lambda db, idu: 8000.0)
    gf = reperes.garde_fou_bilan(db=None, idu="97404000AM0838", sdp_saisie=500, programme_saisi=False)
    assert gf["surface_a_retenir"] is None and gf["non_constructible"] is True
    assert not any("surface à retenir" in a for a in gf["alertes"])
    assert any("Habitat interdit" in a for a in gf["alertes"])


def test_m3_seuil_identique_pdf_et_excel():
    """Le seuil « SDP > surface à retenir » est le MÊME côté Python (garde-fou/PDF) et Excel. LOT O 2 :
    comparaison SUR LES DÉCIMALES (plus d'arrondi avant comparaison, dans aucun des deux)."""
    rep = (_SRC / "bilan" / "reperes.py").read_text()
    exc = (_SRC / "bilan" / "excel.py").read_text()
    assert "sdp_saisie > sar_val" in rep and "round(sdp_saisie)" not in rep
    assert "{cell_sdp}>{_sar}" in exc and "{round(_sar)}" not in exc   # Excel : seuil brut (décimales)


def test_m3_bandeau_aucun_programme():
    """Un Bilan livré SANS programme (garde-fou `programme_saisi=False`) affiche « Aucun programme »,
    pas « Programme saisi par l'utilisateur » — PDF et Excel."""
    from labuse.bilan.pdf import construire_html
    e = EntreesBilan(programme=Programme(terrain=20336), produits=[],
                     postes={"txLog": SaisiePoste(66.9, SOURCE)})
    gf = {"alertes": ["Habitat interdit dans cette zone"], "non_constructible": True,
          "programme_saisi": False}
    html, _ = construire_html(Moteur().calculer(e), idu="97404000AM0838", jour=date(2026, 11, 16),
                              garde_fou=gf)
    assert "Aucun programme" in html and "Programme saisi — non vérifié" not in html
    ws = classeur_bilan(e, None, "t", garde_fou=gf).active
    assert "Aucun programme" in (ws["A2"].value or "") and "Programme saisi" not in (ws["A2"].value or "")

    # avec un programme saisi, on garde bien « Programme saisi ».
    gf2 = {"alertes": ["Scénario « terrain libéré »."], "programme_saisi": True}
    html2, _ = construire_html(Moteur().calculer(e), idu="x", jour=date(2026, 11, 16), garde_fou=gf2)
    assert "Programme saisi — non vérifié" in html2 and "Aucun programme" not in html2
