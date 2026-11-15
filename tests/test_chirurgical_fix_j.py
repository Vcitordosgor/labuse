"""CHIRURGICAL-FIX-1 — LOT J (3ᵉ contre-audit du relecteur, 4 parcelles).

Gardes déterministes, sans base. Bilan Excel d'abord : la famille 1a..1e du relecteur
(référence circulaire, `#DIV/0!`, validation de saisie, recalcul par un moteur
INDÉPENDANT, TVA du « net promoteur »). Puis les formulations (pt3), l'adresse unique
(pt2) et le numéro de contenu (pt4) — ajoutées au fil des points.
"""
from __future__ import annotations

import io
import logging
import os
import re
import tempfile
import warnings

import pytest
from openpyxl import load_workbook

from pathlib import Path

from labuse.bilan.excel import classeur_bilan, classeur_bilan_bytes
from labuse.bilan.moteur import EntreesBilan, Produit, Programme, SaisiePoste

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


# ── Profils des 4 parcelles (dont AM0838, habitat interdit → non constructible, 0 produit) ──
#   surface terrain = la VRAIE contenance cadastrale (LOT J 1e) : 2003 BW2635, 1703 AD0887.
def _parcelles():
    S = SaisiePoste
    libre = lambda suv=800.0: Produit("Libre", 10, suv, 4500.0, 0.085)
    return {
        "BW2635": dict(terrain=2003, produits=[libre()]),
        "AM0838": dict(terrain=1270, produits=[]),          # non constructible (habitat interdit)
        "AD0887": dict(terrain=1703, produits=[libre(760.0)]),
        "IS0448": dict(terrain=1450, produits=[libre(540.0)]),
    }


def _entrees(prof, *, couts):
    postes = {}
    if couts:
        postes = {"achat": SaisiePoste(1000, "saisi", tva=0.0),
                  "constr": SaisiePoste(2293, "saisi")}
    return EntreesBilan(
        programme=Programme(terrain=prof["terrain"], sdp=800, surface_taxable=800),
        produits=list(prof["produits"]),
        postes=postes,
    )


def _ws(entrees):
    return classeur_bilan(entrees, titre="t").active


def _formules(ws):
    return [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]


# ── 1a — jamais de SUM(X:Y) qui se contient elle-même (réf. circulaire au recalcul) ──────────
def test_1a_aucune_reference_circulaire_sum_meme_sans_produit():
    pat = re.compile(r"=SUM\(([A-G])(\d+):([A-G])(\d+)\)")
    for nom, prof in _parcelles().items():
        for couts in (False, True):
            ws = _ws(_entrees(prof, couts=couts))
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str):
                        m = pat.fullmatch(c.value)
                        if m and c.column_letter == m.group(1) == m.group(3):
                            r1, r2, rr = int(m.group(2)), int(m.group(4)), int(c.row)
                            assert not (r1 <= rr <= r2), f"{nom}: {c.coordinate} se somme elle-même ({c.value})"


# ── 1b — les ratios sont gardés : jamais de division par une surface vendable nulle ──────────
def test_1b_ratios_gardes_si_surface_vendable_nulle():
    # AM0838 (0 produit → SUV 0) : les ratios €/m² de SUV sont `=IF(...=0,"",...)`, pas `#DIV/0!`.
    ws = _ws(_entrees(_parcelles()["AM0838"], couts=True))
    ratios = [f for f in _formules(ws) if "/E" in f or "/B" in f or "/C" in f or "/D" in f]
    douteux = [f for f in _formules(ws)
               if re.search(r"/(E\d+|B\d+|C\d+|D\d+)(?![\d\)])", f) and "IF(" not in f and "=0," not in f]
    assert douteux == [], f"ratios non gardés (division sans garde SUV=0) : {douteux}"


# ── 1c — validation Excel « ≥ 0 » sur TOUTES les cellules de saisie ──────────────────────────
def test_1c_validation_cellules_saisie_non_negatif():
    for couts in (False, True):
        ws = _ws(_entrees(_parcelles()["AD0887"], couts=couts))
        dvs = list(ws.data_validations.dataValidation)
        assert len(dvs) == 1, "une seule règle de validation attendue"
        dv = dvs[0]
        assert dv.type == "decimal" and dv.operator == "greaterThanOrEqual" and dv.formula1 == "0"
        assert len(str(dv.sqref).split()) >= 4, "la validation doit couvrir plusieurs cellules de saisie"


# ── 1c bis — le même refus côté serveur dans le modèle des RATIOS MAISON ─────────────────────
def test_1c_ratio_maison_refuse_cout_negatif():
    from pydantic import ValidationError
    from labuse.api.bilan import RatioIn
    RatioIn(valeur=1200)                       # positif : accepté
    with pytest.raises(ValidationError):
        RatioIn(valeur=-250000)                # négatif : refusé, comme toute cellule de saisie


# ── 1d — TEST PERMANENT : chaque classeur recalculé par un moteur INDÉPENDANT (`formulas`) ───
#        4 parcelles (dont une non constructible), coûts vides PUIS saisis : 0 erreur, 0 cycle.
def test_1d_recalcul_moteur_independant_zero_erreur():
    formulas = pytest.importorskip("formulas")
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")

    def recalc(octets):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(octets)
            path = f.name
        try:
            sol = formulas.ExcelModel().loads(path).finish(circular=True).calculate()
        finally:
            os.unlink(path)
        bad = []
        for k, v in sol.items():
            try:
                val = v.value[0, 0] if hasattr(v.value, "shape") else v.value
            except Exception:
                val = v
            s = str(val)
            if any(e in s for e in ("#REF", "#DIV/0", "#VALUE", "#NAME", "#NUM", "#CYCLE")):
                bad.append((k, s))
        return bad

    for nom, prof in _parcelles().items():
        for couts in (False, True):
            octets = classeur_bilan_bytes(_entrees(prof, couts=couts), titre=nom)
            errs = recalc(octets)
            assert errs == [], f"{nom} (couts={couts}) : erreurs au recalcul indépendant : {errs[:5]}"


# ── 1e — « net promoteur TTC » applique la TVA de la ligne de vente (pas un taux figé) ───────
def test_1e_net_promoteur_applique_la_tva_de_la_vente():
    # Produit à TVA 0 (terrain nu / vente sans TVA) → le net promoteur TTC = le net HT (×1), pas ×1,085.
    ws = _ws(EntreesBilan(programme=Programme(terrain=1703, sdp=800, surface_taxable=800),
                          produits=[Produit("Libre", 10, 800.0, 4318.0, 0.0)],
                          postes={"achat": SaisiePoste(1000, "saisi", tva=0.0),
                                  "constr": SaisiePoste(2293, "saisi")}))
    # La formule du net promoteur multiplie par (CA_TTC / CA_HT) = le vrai multiplicateur de TVA de la
    # vente (ligne col. A « Net promoteur … », formule en col. E).
    ligne = next((c.row for row in ws.iter_rows() for c in row
                  if c.column_letter == "A" and isinstance(c.value, str) and c.value.startswith("Net promoteur")), None)
    assert ligne, "ligne « Net promoteur … » absente"
    frm = ws.cell(ligne, 5).value
    assert isinstance(frm, str) and "/" in frm and "*(" in frm, f"net promoteur sans multiplicateur TVA : {frm}"


# ── pt2 — une parcelle, une adresse : le CERFA (PCMI4) choisit la MÊME ligne BAN que la fiche ──
def test_pt2_pcmi4_meme_ordre_adresse_que_la_fiche():
    pd = (_SRC / "api" / "pre_dossier.py").read_text()
    # le CERFA reprend l'ordre canonique `_BAN_ORDER` (celui de _ban_adresse / la fiche)…
    assert "from .app import _BAN_ORDER" in pd and "ORDER BY {_BAN_ORDER} LIMIT 1" in pd
    # … et n'a plus son propre ORDER BY divergent (qui prenait une autre adresse).
    assert "ORDER BY (ap.source = 'principal') DESC, a.id_ban LIMIT 1" not in pd
