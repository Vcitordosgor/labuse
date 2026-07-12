"""Fix preset parc-piscines-entretien (12/07/2026) — proxy bâti indépendant des mutations.

type_bien=Maison (DVF) ne couvrait que les parcelles vendues récemment : 497/8 299 (6 %).
Remplacé par emprise bâtie BD TOPO 40-400 m² (gabarit maison individuelle) → 5 784 parcelles.
Limite mesurée et assumée : 12 des 22 « Appartement » DVF connus ont une emprise dans la
fenêtre (petits collectifs) — pollution résiduelle ≤ 0,2 % du segment.
"""
from __future__ import annotations

from labuse import config
from labuse.segments import presets as presets_mod
from labuse.segments.registry import FILTERS


def _preset():
    doc = config.load_yaml_config("segment_presets")
    return next(p for p in doc["presets"] if p["slug"] == "parc-piscines-entretien")


def test_le_preset_ne_depend_plus_des_mutations_dvf():
    p = _preset()
    cles = [f["cle"] for f in p["filtres"]]
    assert "type_bien" not in cles, "le proxy DVF (parcelles vendues seulement) est revenu"
    assert cles == ["piscine", "emprise_batie_m2", "jardin_m2"]
    emprise = next(f for f in p["filtres"] if f["cle"] == "emprise_batie_m2")
    assert (emprise["min"], emprise["max"]) == (40, 400)
    jardin = next(f for f in p["filtres"] if f["cle"] == "jardin_m2")
    assert jardin["min"] == 100          # inchangé (mandat)
    assert presets_mod.validate_preset(p) == []
    # l'export suit le proxy : l'emprise remplace le type DVF
    assert "emprise_batie_m2" in p["colonnes_export"] and "type_bien" not in p["colonnes_export"]


def test_le_proxy_emprise_est_independant_des_mutations():
    fd = FILTERS["emprise_batie_m2"]
    assert fd.requires_rows == "parcel_residuel_bati"     # BD TOPO, pas DVF
    assert "dvf" not in fd.joins and "tb" not in fd.joins
