"""PLU-CALIBRAGE-5 — les 81 exceptions `modifie_calcul=true` entrent (ou sont portées) au moteur.

Ce module complète `test_donnees_fix1_exceptions_calcul.py` avec les garde-fous propres au
mandat PLU-CALIBRAGE-5 :
  - Lot A/C : chaque exception porte son VERBATIM (`texte`, source A_CALIBRER.csv) ; une exception
    NON modélisée est portée par la parcelle avec son texte, jamais approximée ;
  - Lot B : témoin À LA VOLÉE (aucun run) d'une exception MODÉLISABLE — la majoration conditionnée
    à la surface (97402 Ub, ≥ 2 000 m²) fait passer le témoin de R+1 à R+2 (SDP mesurée avant/après) ;
  - « Déjà couverte » : un sous-secteur cité (97408 UBa/UBb/UBc, 97423 Uaa) se résout DÉJÀ comme sa
    propre zone calibrée → resolve_zone sert la bonne valeur, rien à réappliquer ;
  - Lot C : une parcelle qui PORTE une exception non modélisée a une capacité « Estimé » (jamais
    « Sourcé »), même en zone calibrée — sans que la SDP soit approximée.
"""
from __future__ import annotations

import json
import os

import pytest

from labuse.faisabilite import residuel
from labuse.faisabilite.engine import Faisabilite, estimate_capacity
from labuse.faisabilite.zonage import (ZoneRules, appliquer_exceptions_calcul,
                                       _exceptions_effet, resolve_zone)

CALIB = os.path.join(os.path.dirname(__file__), "..", "config", "plu_exceptions_effet.json")


def _entries():
    return json.load(open(CALIB, encoding="utf-8"))["entries"]


# ── Lot A / C — le verbatim est porté ─────────────────────────────────────────────────────────
def test_verbatim_present_sur_les_81():
    """Chaque exception porte son texte verbatim (PLU-CALIBRAGE-5) — pour l'affichage fiche."""
    entries = _entries()
    assert len(entries) == 81
    for k, e in entries.items():
        assert e.get("texte"), f"entrée {k} sans verbatim `texte`"
        assert len(e["texte"]) > 10


def test_non_modelisee_porte_le_verbatim():
    """97416 Uf : exception bande_limite non modélisable → portée AVEC texte + article + page."""
    r = ZoneRules(code="Uf", he_m=6.0, hf_m=11.0, emprise_sol_pct=50.0)
    r2, nm = appliquer_exceptions_calcul(r, "97416", "Uf", None)
    assert r2.he_m == 6.0, "valeur de zone altérée par une exception non modélisable"
    assert nm, "règle non modélisée non portée"
    for x in nm:
        assert x.get("article") and x.get("page_pdf")
        assert x.get("texte"), "le verbatim doit accompagner la règle non modélisée (affichage fiche)"


# ── Lot B — témoin À LA VOLÉE d'une exception MODÉLISABLE (aucun run) ────────────────────────────
def _sdp(rules, surface, emprise):
    f = estimate_capacity(rules, surface, emprise_geo=(emprise, 4.0))
    return f.fourchette.get("surface_plancher_m2"), f.fourchette.get("niveaux")


def test_temoin_majoration_modelisable_augmente_la_sdp():
    """97402 Ub — majoration ≥ 2 000 m² (he 8→10, hf 11→13) : le témoin passe R+1 → R+2.
    Calcul à la volée, aucune valeur en base recalculée."""
    base = ZoneRules(code="Ub", he_m=8.0, hf_m=11.0, emprise_sol_pct=60.0, calibree=True)
    surface, emprise = 2500.0, 1500.0
    r_sans, _ = appliquer_exceptions_calcul(base, "97402", "Ub", 1000.0)   # < seuil → pas de majoration
    r_avec, _ = appliquer_exceptions_calcul(base, "97402", "Ub", surface)  # ≥ seuil → majoration
    assert (r_sans.he_m, r_avec.he_m) == (8.0, 10.0)
    sdp_sans, niv_sans = _sdp(r_sans, surface, emprise)
    sdp_avec, niv_avec = _sdp(r_avec, surface, emprise)
    assert niv_sans == "R+1" and niv_avec == "R+2"
    assert sdp_sans == 1350 and sdp_avec == 2025          # +675 m² SDP sur le témoin
    assert sdp_avec > sdp_sans
    # la règle de base partagée n'est JAMAIS mutée
    assert base.he_m == 8.0


# ── « Déjà couverte » — le sous-secteur se résout comme sa propre zone calibrée ──────────────────
def test_deja_couverte_sous_secteur_resolu():
    """97408 : UB = 9/12 m mais UBa/UBb/UBc = 7/10 m se résolvent seuls (resolve_zone) ; 97423 Uaa
    = 12/16 vs Ua = 10/14. La valeur du sous-secteur est DÉJÀ servie, rien à réappliquer."""
    ub = resolve_zone("UB", "La Possession")
    assert (ub.he_m, ub.hf_m) == (9.0, 12.0)
    for code in ("UBa", "UBb", "UBc"):
        r = resolve_zone(code, "La Possession")
        assert (r.he_m, r.hf_m) == (7.0, 10.0), f"{code} ne sert pas sa propre valeur calibrée"
    assert resolve_zone("Uaa", "Les Trois-Bassins").he_m == 12.0
    assert resolve_zone("Ua", "Les Trois-Bassins").he_m == 10.0


# ── Lot C — la capacité passe « Estimé » dès qu'une exception n'est pas modélisée ────────────────
def _faisa(regles_non_modelisees, calibree=True):
    fr = {"emprise_constructible_m2": 500, "emprise_batie_max_m2": 225,
          "surface_plancher_m2": 1000, "niveaux_max": 2, "niveaux": "R+1",
          "logements_au_sol": (0, 0), "logements_sous_sol": (0, 0), "stationnement_regime": "borne"}
    f = Faisabilite("U", None, True, "v", [], [], [], [], fr, "b", calibree=calibree)

    class _Ctx:
        surface_m2 = 1000.0
    ctx = _Ctx()
    ctx.regles_non_modelisees = regles_non_modelisees
    return (ctx, f)


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    monkeypatch.setattr("labuse.bati.layer_available", lambda s: True)
    monkeypatch.setattr("labuse.faisabilite.residuel._niveaux_existants",
                        lambda s, pid, defaut: (float(defaut), False, "sans"))
    monkeypatch.setattr("labuse.faisabilite.residuel._emprise_revelee", lambda s, pid: None)
    monkeypatch.setattr("labuse.bati.stats_batch",
                        lambda s, ids: {ids[0]: {"bati_ratio": 0.2, "bati_count": 1, "bati_max_m2": 100.0}})


def test_capacite_estimee_quand_exception_non_modelisee():
    """Zone calibrée MAIS l'exception n'est pas modélisée → capacité « Estimé » (jamais « Sourcé »).
    La SDP résiduelle n'est PAS approximée pour autant (même valeur qu'avant)."""
    nm = [{"regle": "hauteur.egout", "porte": "bande_limite", "article": "Ue3.5",
           "page_pdf": 193, "texte": "…"}]
    r_estime = residuel.compute_residuel(None, 1, faisa=_faisa(nm, calibree=True))
    r_source = residuel.compute_residuel(None, 1, faisa=_faisa([], calibree=True))
    assert r_estime["capacite_estimee"] is True, "une exception non modélisée doit forcer Estimé"
    assert r_source["capacite_estimee"] is False, "sans exception, zone calibrée reste Sourcé"
    # la valeur de SDP résiduelle est IDENTIQUE : le badge change, jamais le chiffre.
    assert r_estime["sdp_residuelle_m2"] == r_source["sdp_residuelle_m2"]
    assert r_estime["regles_non_modelisees"] == nm
