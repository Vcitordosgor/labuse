"""CIRCUIT-6 lot 0 — la règle mère : rien hors registre (raccordements + gardes).

Chaque test garde UN raccordement de l'inventaire CONTOURNEMENTS.md :
  · les libellés de scénarios/fiabilité viennent de vocabulaires.py (plus de littéral local) ;
  · les arêtes réservoir→chiffre qui manquaient (taxe, CatNat, RTAA) sont présentes ;
  · chaque kind de couche servi par un robinet appartient, après alias déclaré, à la carte
    des réservoirs (registre/tables.py) — un kind inventé casse ;
  · le libellé de la couche occupation du sol dit SA source (BD CARTO), jamais « OCS GE » seul.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from labuse.registre import donnees, robinets, tables
from labuse import vocabulaires as V

pytestmark = pytest.mark.verrous

ROOT = Path(__file__).resolve().parents[2]

#: kinds LOGIQUES des routes de robinets → kind PHYSIQUE de spatial_layers (même doctrine que
#: les réservoirs logiques de tables.py : sis/casias = subtypes de sol_pollue, ebc/er = familles
#: de plu_gpu_prescription…). Un kind de route hors de cette carte ET hors des couches déclarées
#: est un kind INVENTÉ → casse.
KIND_ALIASES = {
    "casias": "sol_pollue", "sis": "sol_pollue",
    "ebc": "plu_gpu_prescription", "er": "plu_gpu_prescription",
    "plu_gpu": "plu_gpu_zone",
    "rpg": "safer",
    "enp": "ens",
    "tcsp_axe": "tcsp_troncon",
}


def _kinds_routes() -> set[str]:
    kinds = set()
    for r in robinets.ROBINETS.values():
        if r.categorie == "couche":
            kinds |= set(re.findall(r"kind=([a-z_0-9]+)", r.route))
    return kinds


def _couches_carte() -> set[str]:
    return {k for rt in tables.RESERVOIR_TABLES.values() for k in rt.couches}


# ── scénarios : un littéral, un endroit ────────────────────────────────────────────────
def test_scenarios_importes_du_vocabulaire():
    src = (ROOT / "src/labuse/exports/blocs/potentiel.py").read_text(encoding="utf-8")
    for lib in V.SCENARIOS_POTENTIEL:
        assert lib not in src, f"littéral de scénario en dur dans potentiel.py : {lib!r}"
    assert "SCENARIO_AU_SOL" in src and "SCENARIO_RECONSTRUCTION" in src


def test_scenarios_le_vocabulaire_est_ferme():
    assert V.SCENARIOS_POTENTIEL == (
        "Au sol, bâti conservé", "En hauteur, bâti conservé", "Reconstruction après démolition")


# ── fiabilité : le manifeste de fiche lit le vocabulaire ───────────────────────────────
def test_fiabilite_importee_du_vocabulaire():
    src = (ROOT / "src/labuse/api/app.py").read_text(encoding="utf-8")
    assert '"verifie": "surveillée"' not in src, "mapping _FIAB recodé en dur dans app.py"
    assert "FIABILITE_LIBELLES" in src


# ── arêtes raccordées (anti-régression : elles ont manqué, SOURCES-AUDIT-1) ────────────
def test_aretes_taxe_catnat_rtaa_presentes():
    assert donnees.CHIFFRES["taxe_amenagement_eur"].reservoirs == ("taxe_amenagement",)
    assert donnees.CHIFFRES["taxe_amenagement_estimee_eur"].reservoirs == ("taxe_amenagement",)
    assert donnees.CHIFFRES["catnat_n"].reservoirs == ("catnat_gaspar",)
    assert donnees.CHIFFRES["rtaa_exigences"].reservoirs == ("rtaa_dom",)
    assert "rtaa_exigences" in robinets.ROBINETS["outil_faisabilite"].chiffres


# ── couches : chaque kind de route appartient à la carte (après alias déclaré) ─────────
def test_kinds_de_routes_dans_la_carte():
    carte = _couches_carte()
    inconnus = sorted(
        k for k in _kinds_routes() if KIND_ALIASES.get(k, k) not in carte)
    assert inconnus == [], f"kinds de couches servis HORS carte des réservoirs : {inconnus}"


def test_kinds_de_routes_dans_la_carte_prouve_casse():
    """Un kind inventé (non déclaré) doit être attrapé — preuve que la garde mord."""
    carte = _couches_carte()
    kinds = _kinds_routes() | {"couche_inventee_xyz"}
    inconnus = [k for k in kinds if KIND_ALIASES.get(k, k) not in carte]
    assert "couche_inventee_xyz" in inconnus


# ── occupation du sol : le libellé dit SA source ───────────────────────────────────────
def test_ocs_ge_libelle_dit_bd_carto():
    lab = (ROOT / "frontend/src/lib/layers.ts").read_text(encoding="utf-8")
    m = re.search(r"ocs_ge:\s*'([^']+)'", lab)
    assert m, "couche ocs_ge absente de layers.ts"
    libelle = m.group(1)
    assert "BD CARTO" in libelle, f"le libellé occupation du sol ne dit plus sa source : {libelle!r}"
    assert not re.search(r"OCS\s*GE\s*\(IGN\)", libelle), \
        "le libellé re-prétend servir OCS GE (IGN) alors que la couche sert BD CARTO V5"
