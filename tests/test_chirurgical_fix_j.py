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
        # LOT K 2d — en plus de la validation « ≥ 0 », une validation TVA « entre 0 et 1 » peut exister.
        dv = next(d for d in dvs if d.operator == "greaterThanOrEqual")
        assert dv.type == "decimal" and dv.formula1 == "0"
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


# ── pt3b — zone rouge : le RESTE soumis au règlement du plan de prévention (plus « qu'en zone bleue ») ──
def test_pt3b_zone_rouge_reste_soumis_au_plan():
    from labuse.api.risques_arbitrage import libelle_client_detail
    ancien = ("PPR zone rouge sur 34 % de la surface — vigilance forte ; constructibilité à vérifier "
              "au règlement (pas d'exclusion automatique).")
    neuf = libelle_client_detail(ancien)
    assert "la partie en zone rouge est exclue de l'implantation" in neuf
    assert "le reste est soumis au règlement du plan de prévention" in neuf
    assert "qu'en zone bleue" not in neuf


# ── pt3a / pt3c — stationnement renvoi + sol combiné (Le Tampon), capacité inchangée ─────────
def test_pt3ac_stationnement_renvoi_et_sol_combine():
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.plu_reglement import _regles_valeurs
    for zc, pt, perm in (("Ud", 30.0, 40.0), ("Uav", 20.0, 30.0)):
        z = resolve_zone(zc, "Le Tampon")
        lignes = {r["cle"]: r for r in _regles_valeurs(z, None, 0)}
        stat = lignes["stationnement"]["valeur"]
        assert stat.startswith("barème selon le type de logement et la taille de l'opération")
        assert "1 place" not in stat
        assert lignes["pleine_terre"]["valeur"] == (
            f"{perm:g} % de la parcelle en surface perméable et {pt:g} % de la parcelle en pleine terre")
        assert "surface_permeable" not in lignes
        assert z.places_par_logement() == 1.0          # la capacité ne change pas


# ── pt3d — bâti mesuré : raison VRAIE de l'absence de marge (pas « hauteur du bâti non mesurée ») ──
def test_pt3d_hauteur_mesuree_raison_vraie():
    from labuse.exports.miroir import _absence_une_raison
    ph = "Marge de surélévation non calculable (hauteur de règle ou bâti non déterminés)."
    # hauteur réellement mesurée (IS0448 : 4,1 m à l'égout) → ce n'est PAS « non mesurée »
    r = _absence_une_raison(ph, "U", bati_connu=True, hauteur_mesuree=True)
    assert "hauteur du bâti non mesurée" not in r
    assert "non comparable à la hauteur mesurée" in r
    # sans mesure (emprise connue seulement) → on garde « hauteur du bâti non mesurée » (LOT I 3b)
    assert "hauteur du bâti non mesurée" in _absence_une_raison(ph, "U", bati_connu=True)


# ── pt3e — comparables : classés par RESSEMBLANCE + note qui les distingue de la médiane ─────
def test_pt3e_comparables_ressemblance_et_note():
    from labuse.exports.blocs.annonce import _comparables
    from labuse.exports.miroir import _r_comparables
    from labuse.registre.valeur import Valeur
    comp = {"date": "2025-01-01", "type": "Maison", "surface_m2": 80,
            "prix_eur": 200000, "prix_m2": 2500, "distance_m": 321}
    # Estimer (annonce)
    h = _comparables({"comparables": [comp]})
    assert "ressemblant" in h and "pas par distance" in h and "tout le secteur" in h
    assert "les plus proches" not in h
    # Dossier (miroir) — titre « ressemblants » + note médiane présente
    v = [comp]
    val = Valeur(valeur=v, chiffre_id="comparables_proches", version_def=None, run=None)
    hd = _r_comparables(v, val)
    assert "les plus ressemblants" in hd and "tout le secteur" in hd
    assert "les plus proches" not in hd


# ── pt3f — plans de prévention : couvre la parcelle ≠ existe dans la commune ─────────────────
def test_pt3f_ppr_couvre_vs_commune():
    from labuse.exports.miroir import _r_aleas
    from labuse.registre.valeur import Valeur
    v = [{"nature": "PPR — zone bleue", "libelle": "PPR inondation — zone bleue sur 56 %",
          "ppr": [{"document": "PPR", "approbation": "2016-01-26"}],
          "ppr_commune_autres": [{"document": "PPRL", "approbation": "2017-03-16"}]}]
    val = Valeur(valeur=v, chiffre_id="aleas_parcelle_liste", version_def=None, run=None)
    html = _r_aleas(v, val)
    assert "approuvé le 26/01/2016" in html and "couvre la parcelle" in html
    assert "PPR littoral approuvé le 16/03/2017" in html and "ne couvrent pas la parcelle" in html


# ── pt3g — PLU : UNE SEULE date porte « version servie » ──────────────────────────────────────
def test_pt3g_plu_une_seule_version_servie():
    from labuse.exports.miroir import _r_statut_plu
    html = _r_statut_plu({"approbation_sudocuh": "2023-08-11", "horizon": "2024-01-01"})
    assert "Version du PLU servie, approuvée le 11/08/2023" in html
    assert "version servie par LABUSE, dernière approbation" not in html
    # la 2e date est un REPÈRE, pas une seconde « version servie »
    assert "approbation enregistrée au GPU le 01/01/2024" in html
    assert html.count("ersion du PLU servie") == 1


# ── pt4 — le numéro porte TOUT le contenu rendu : contenu affiché différent ⇒ numéro différent ──
class _FakeDB:
    def execute(self, *a, **k):
        raise RuntimeError("pas de base en test unitaire")


def test_pt4_numero_depend_du_contenu_rendu():
    from datetime import date
    from labuse.exports import builder
    j = date(2026, 9, 5)
    base = {"surface_m2": 742, "adresse": "103 Chaussée Royale, Saint-Paul",
            "commune": "Saint-Paul", "proprietaire_moral": True}
    r1 = builder.construire(_FakeDB(), "97415000BO0852", "dossier", fiche=dict(base), jour=j)
    r1b = builder.construire(_FakeDB(), "97415000BO0852", "dossier", fiche=dict(base), jour=j)
    # une adresse DIFFÉRENTE est AFFICHÉE mais n'est pas dans les `valeurs` : l'ancienne clé (valeurs
    # seules) aurait collisionné ; la clé de CONTENU les sépare.
    r2 = builder.construire(_FakeDB(), "97415000BO0852", "dossier",
                            fiche=dict(base, adresse="1 Rue Autre, Saint-Paul"), jour=j)
    assert r1.numero == r1b.numero                      # même contenu → même numéro (idempotent)
    assert r1.numero != r2.numero                       # contenu affiché différent → numéro différent
    assert r1.numero.startswith("DP-20260905-97415000BO0852-")
    assert r1.cartouche.doc_ref.endswith(r1.numero)
    assert "\x00" not in r1.html                        # le jeton de numéro ne fuit jamais


# ── Complément dvf — garde STATIQUE (hook) : les 3 lecteurs de prix dédoublonnent par couple ──
def test_dvf_lecteurs_prix_dedoublonnent_par_couple():
    bilan = (_SRC / "faisabilite" / "bilan.py").read_text()
    pmodel = (_SRC / "scoring" / "p_model" / "sql.py").read_text()
    marche = (_SRC / "faisabilite" / "marche_commune.py").read_text()
    # _surface_terrain_sujet : somme sur des lignes DISTINCT (plus un sum brut)
    assert "SELECT DISTINCT id_mutation, type_local, surface_reelle_bati" in bilan
    # p_model_mut_l2 : s_bati sommé sur la CTE dédoublonnée `ded`
    assert "WITH ded AS (" in pmodel and "FROM ded" in pmodel
    # _median_terrain_commune : une surface de terrain par couple (max OVER PARTITION) avant somme
    assert "OVER (PARTITION BY dm.id_mutation, dm.id_parcelle)" in marche
