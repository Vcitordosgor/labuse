"""Lot D — one-pager (D1), comparateur (D2), filtres sauvegardés (D3)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api.export import fiche_onepager

# ── Fiche minimale réutilisable (forme du payload _build_fiche) ──
_FICHE = {
    "parcel": {"idu": "97415000BV0912", "commune": "Saint-Paul", "section": "BV", "numero": "912",
               "surface_m2": 3948, "centroid": {"lon": 55.285, "lat": -21.01}},
    "verdict": {"status": "opportunite", "opportunity_score": 67, "completeness_score": 84, "reasons": []},
    "resume": {"synthese": "Ressort comme opportunité.", "vigilance": ["Propriétaire à identifier"],
               "prochaine_action": "Vérifier le PLU."},
    "faisabilite": {"zone": "U6c", "constructible": True, "verdict": "R+1 · ~16-17 logts",
                    "fourchette": {"surface_plancher_m2": 2555},
                    "residuel": {"disponible": True, "taux_emprise_pct": 10, "sdp_residuelle_m2": 2259, "sous_densite": True},
                    "bilan": {"fiable": True, "ca": {"bas": 2200000, "haut": 3400000},
                              "charge_fonciere": {"central": 300000, "par_m2_terrain": 76}}},
    "cascade": [{"layer_name": "zonage_plu_gpu", "result": "POSITIVE", "severity": None, "detail": "Zone U", "source": "GPU"},
                {"layer_name": "ravine", "result": "SOFT_FLAG", "severity": "moyen", "detail": "Proximité ravine", "source": "BD TOPO"}],
    "disclaimer": "Pré-analyse.",
}


# ── D1 — one-pager ──

def test_onepager_contient_les_sections_cles():
    geo = {"type": "Polygon", "coordinates": [[[55.284, -21.011], [55.286, -21.011],
                                               [55.286, -21.009], [55.284, -21.009], [55.284, -21.011]]]}
    h = fiche_onepager(_FICHE, geo)
    assert "@page" in h and "size: A4" in h
    for s in ("97415000BV0912", "Capacité", "Potentiel résiduel", "Bilan", "Contraintes",
              "À vérifier", "Proximité ravine", "wms-r/ows", "polygon points"):
        assert s in h, s
    assert "2.2 M€" in h or "2.2 M" in h   # CA formaté en M€


def test_onepager_degrade_sans_faisabilite_ni_geom():
    fiche = {**_FICHE, "faisabilite": None}
    h = fiche_onepager(fiche, None)   # ne doit pas crasher
    assert "97415000BV0912" in h and "Contraintes" in h


# ── D2 — _compare_row ──

def test_compare_row_extrait_les_champs_alignes():
    from labuse.api.app import _compare_row
    r = _compare_row(_FICHE)
    assert r["idu"] == "97415000BV0912" and r["status"] == "opportunite"
    assert r["sdp_max_m2"] == 2555 and r["sdp_residuelle_m2"] == 2259 and r["sous_densite"] is True
    assert r["ca_bas"] == 2200000 and r["n_contraintes"] == 1   # 1 SOFT_FLAG (le POSITIVE ne compte pas)


# ── D3 — filtres sauvegardés (DB) ──

@pytest.mark.db
def test_saved_filters_roundtrip(db_session):
    from labuse.api.app import SavedFilterIn, delete_filter, list_filters, save_filter
    db_session.execute(text("CREATE TABLE IF NOT EXISTS saved_filters ("
                            " id serial PRIMARY KEY, name varchar(80) NOT NULL, params jsonb NOT NULL,"
                            " created_at timestamptz NOT NULL DEFAULT now())"))
    r = save_filter(SavedFilterIn(name="Mon filtre", params={"statuses": ["opportunite"], "taux": 40}), db=db_session)
    assert r["id"] and r["name"] == "Mon filtre"
    lst = list_filters(db=db_session)
    assert any(f["name"] == "Mon filtre" and f["params"]["taux"] == 40 for f in lst)
    delete_filter(r["id"], db=db_session)
    assert all(f["id"] != r["id"] for f in list_filters(db=db_session))
