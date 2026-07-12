"""Socle V1 — dispatch des endpoints vers la SOURCE DE VÉRITÉ q_v2 (dryrun_parcel_evaluations).

Teste le BRANCHEMENT `?source=q_v2` (sans base : les helpers q_v2 sont mockés). Le contenu SQL des
helpers est vérifié par smoke test sur la base réelle (curl), la couche de test n'ayant pas les
données dryrun.
"""
from __future__ import annotations

from labuse.api import app as m


def test_stats_dispatch_q_v2(monkeypatch):
    monkeypatch.setattr(m, "_q_v2_stats", lambda db, commune, run_label="q_v2", **kw: {"chaude": 83, "run": run_label})
    monkeypatch.setattr(m, "_mem_cached", lambda key, ttl, fn: fn())
    out = m.stats(commune="Saint-Paul", source="q_v2", db=None)
    assert out["chaude"] == 83 and out["run"] == "q_v2"


def test_geojson_dispatch_q_v2(monkeypatch):
    monkeypatch.setattr(m, "_q_v2_geojson",
                        lambda db, commune, limit, run_label="q_v2": {"type": "FeatureCollection", "features": [], "run": run_label})
    out = m.parcels_geojson(commune="Saint-Paul", source="q_v2", db=None)
    assert out["type"] == "FeatureCollection" and out["run"] == "q_v2"


def test_list_dispatch_q_v2(monkeypatch):
    monkeypatch.setattr(m, "_q_v2_list",
                        lambda db, commune, limit, offset, run_label="q_v2", **kw: [{"idu": "97415000AC0253", "status": "chaude"}])
    out = m.list_parcels(commune="Saint-Paul", source="q_v2", db=None)
    assert out[0]["idu"] == "97415000AC0253" and out[0]["status"] == "chaude"


def test_statuts_matrice_v2_exposes():
    # la matrice premium expose bien les 4 statuts (dont « à surveiller » qui manquait à la maquette)
    assert set(m._Q_V2_STATUTS) >= {"chaude", "a_surveiller", "a_creuser", "ecartee"}


def test_fiche_dispatch_q_v2(monkeypatch):
    monkeypatch.setattr(m, "_q_v2_fiche", lambda db, idu, run_label="q_v2": {"idu": idu, "statut": "chaude", "run": run_label})
    out = m.parcel_fiche("97415000AC0253", source="q_v2", db=None)
    assert out["statut"] == "chaude" and out["run"] == "q_v2"


def test_fiche_axe_qa_et_onglets():
    # axe A = pur vendeur (proprietaire/age/bodacc/dpe) ; le reste = Q. Chaque couche a un onglet.
    assert m._A_LAYERS == {"proprietaire", "age_dirigeant", "bodacc", "dpe_passoire"}
    assert m._LAYER_ONGLET["residuel_socle"] == "regles"
    assert m._LAYER_ONGLET["dvf"] == "marche"
    assert m._LAYER_ONGLET["bodacc"] == "proprio"
    assert m._LAYER_ONGLET["icpe"] == "risques"


def test_layers_whitelist():
    # /map/layers.geojson n'expose que la whitelist (pas d'énumération libre de spatial_layers)
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        m.map_layers_geojson(kind="batiment", commune=None, limit=10, db=None)


def test_pdf_statut_couleurs_completes():
    # le PDF connaît les 5 statuts de la matrice (jamais de KeyError sur une écartée/exclue)
    from labuse.api.pdf_premium import STATUT
    assert set(STATUT) == {"chaude", "a_surveiller", "a_creuser", "ecartee", "exclue"}
