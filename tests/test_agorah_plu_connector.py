"""Connecteur PLU AGORAH (repli) — tests PURS (aucun réseau, aucune base).

Verrouille : mapping AGORAH → couche `plu_gpu_zone`, conservation typezones U/AU/A/N,
partition `DU_<INSEE>`, attrs (source/idurba/datappro…), et la règle de repli :
- repli SEULEMENT si le GPU n'a aucune zone propre ET commune allowlistée ;
- pas de repli si le GPU sert déjà du propre ;
- pas de repli pour une commune non allowlistée (dont Saint-Leu 97413, hors allowlist
  tant que la fraîcheur du PLU 2007 n'est pas validée).
"""
from __future__ import annotations

from labuse.ingestion import agorah_plu

_GEOM = {"type": "Polygon", "coordinates": [[[55.6, -20.9], [55.61, -20.9], [55.61, -20.91], [55.6, -20.91], [55.6, -20.9]]]}


def _rec(typezone="U", libelle="Ub", libelong="zone urbaine Ub",
         idurba="97409_20190228", datappro="2019-02-28T00:00:00+00:00", geom=None):
    return {"typezone": typezone, "libelle": libelle, "libelong": libelong, "idurba": idurba,
            "datappro": datappro, "geo_shape": {"type": "Feature", "geometry": geom or _GEOM}}


# ── Mapping AGORAH → plu_gpu_zone ──────────────────────────────────────────────
def test_agorah_zone_mapping_complet():
    m = agorah_plu.agorah_zone_mapping(_rec(), "97409")
    assert m["kind"] == "plu_gpu_zone"
    assert m["subtype"] == "U"                       # subtype = typezone
    assert m["name"] == "zone urbaine Ub"            # name = libelong prioritaire
    assert m["geometry"]["type"] == "Polygon"
    a = m["attrs"]
    assert a["source"] == "AGORAH_BASE_PERMANENTE_PLU_REUNION"
    assert a["insee"] == "97409"
    assert a["typezone"] == "U"
    assert a["libelle"] == "Ub"
    assert a["libelong"] == "zone urbaine Ub"
    assert a["idurba"] == "97409_20190228"
    assert a["datappro"].startswith("2019-02-28")
    assert a["partition"] == "DU_97409"
    assert "data.regionreunion.com" in a["dataset_url"]


def test_name_retombe_sur_libelle_si_pas_de_libelong():
    m = agorah_plu.agorah_zone_mapping(_rec(libelong=None, libelle="A"), "97409")
    assert m["name"] == "A"


def test_typezones_uau_a_n_preserves():
    for tz in ("U", "U1b", "AU", "AUc", "AUs", "A", "N", "Nh"):
        m = agorah_plu.agorah_zone_mapping(_rec(typezone=tz), "97409")
        assert m["subtype"] == tz and m["attrs"]["typezone"] == tz


def test_typezone_vide_devient_none():
    assert agorah_plu.agorah_zone_mapping(_rec(typezone="  "), "97409")["subtype"] is None


def test_partition_du_insee():
    assert agorah_plu.agorah_partition("97409") == "DU_97409"
    assert agorah_plu.agorah_partition("97413") == "DU_97413"
    assert agorah_plu.agorah_zone_mapping(_rec(), "97413")["attrs"]["partition"] == "DU_97413"


# ── geo_shape : Feature, geometry brute, ou rien ──────────────────────────────
def test_geo_shape_feature_geometry_brute_et_absente():
    geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
    multi = {"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]]}
    assert agorah_plu.agorah_zone_mapping({"typezone": "U", "geo_shape": {"type": "Feature", "geometry": geom}}, "97409")["geometry"] == geom
    assert agorah_plu.agorah_zone_mapping({"typezone": "U", "geo_shape": geom}, "97409")["geometry"] == geom
    assert agorah_plu.agorah_zone_mapping({"typezone": "U", "geo_shape": multi}, "97409")["geometry"] == multi
    assert agorah_plu.agorah_zone_mapping({"typezone": "U", "geo_shape": None}, "97409") is None
    assert agorah_plu.agorah_zone_mapping({"typezone": "U"}, "97409") is None


# ── Règle de repli (PURE) ─────────────────────────────────────────────────────
def test_repli_seulement_si_gpu_zero_propre_et_allowliste():
    assert agorah_plu.should_use_agorah_fallback("97409", 0) is True       # Saint-André allowlistée, GPU vide
    assert agorah_plu.should_use_agorah_fallback("97409", 3) is False      # GPU sert déjà du propre → pas de repli
    assert agorah_plu.should_use_agorah_fallback("97415", 0) is False      # Saint-Paul non allowlistée
    assert agorah_plu.should_use_agorah_fallback("97413", 0) is False      # Saint-Leu hors allowlist (fraîcheur 2007)


def test_allowlist_contenu():
    assert "97409" in agorah_plu.AGORAH_PLU_ALLOWLIST          # Saint-André activée
    assert "97413" not in agorah_plu.AGORAH_PLU_ALLOWLIST      # Saint-Leu pas (encore)


# ── Pré-vol lecture seule (réseau mocké, aucune base) ─────────────────────────
def test_preflight_resume_et_couverture(monkeypatch):
    recs = [
        _rec(typezone="U", geom={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}),
        _rec(typezone="A", geom={"type": "Polygon", "coordinates": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]]}),
    ]
    monkeypatch.setattr(agorah_plu, "fetch_agorah_zones", lambda insee, **k: recs)
    pts = [(0.5, 0.5), (1.5, 0.5), (5.0, 5.0)]          # 2 dans les zones, 1 dehors
    out = agorah_plu.agorah_plu_preflight("97409", pts)
    assert out["zones"] == 2
    assert out["typezones"] == {"U": 1, "A": 1}
    assert out["partition"] == "DU_97409"
    assert out["parcels"] == 3 and out["covered"] == 2
    assert out["coverage_pct"] == round(100.0 * 2 / 3, 2)


def test_preflight_ignore_zone_sans_geometrie(monkeypatch):
    recs = [_rec(typezone="U"), {"typezone": "N", "geo_shape": None}]
    monkeypatch.setattr(agorah_plu, "fetch_agorah_zones", lambda insee, **k: recs)
    out = agorah_plu.agorah_plu_preflight("97409")
    assert out["zones"] == 1 and out["invalid_repaired"] == 1
