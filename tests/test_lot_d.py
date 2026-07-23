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
                            " created_at timestamptz NOT NULL DEFAULT now(), compte_id integer)"))
    # request=None → compte pilote (NULL) : current_compte() tolère l'appel direct hors HTTP.
    r = save_filter(SavedFilterIn(name="Mon filtre", params={"statuses": ["opportunite"], "taux": 40}), None, db=db_session)
    assert r["id"] and r["name"] == "Mon filtre"
    lst = list_filters(None, db=db_session)
    assert any(f["name"] == "Mon filtre" and f["params"]["taux"] == 40 for f in lst)
    delete_filter(r["id"], None, db=db_session)
    assert all(f["id"] != r["id"] for f in list_filters(None, db=db_session))


# ── 1.C — paramètres de bilan par secteur ──

def test_1c_compute_bilan_params_pilotent(monkeypatch):
    from labuse.faisabilite.bilan import compute_bilan
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses()
    prix = {"fiable": True, "fiabilite": "fiable", "fiabilite_raisons": [], "type_prix": "appartement",
            "n": 40, "n_exclus": 0, "n_doublons": 0, "radius_m": 1500.0, "commune_fallback": False,
            "pct_appartement": 100, "periode": [2022, 2025], "q1": 2200, "median": 3000, "q3": 4300,
            "min": 2000, "max": 4700}
    base = compute_bilan(4600, 4500, prix, h)
    # override prix neuf + coût construction secteur → CA et coût changent
    bp = {"prix_m2_neuf": 3500, "cout_construction_m2_sdp": 3200, "cout_vrd_base": 50,
          "majoration_vrd_pente_pct": 20, "marge_cible_pct": 18, "honoraires_pct": 12, "frais_financiers_pct": 3}
    sect = compute_bilan(4600, 4500, prix, h, contexte_eco={"pente_pct": 35}, bilan_params=bp)
    assert sect.ca["central"] == round(4600 * 3500)              # prix override appliqué (flat)
    assert sect.calc["cout_vrd"] == round(50 * 1.20 * 4500)      # VRD base × (1+20% pente≥15) × terrain
    assert sect.charge_fonciere["central"] != base.charge_fonciere["central"]  # piloté par secteur


@pytest.mark.db
def test_1c_resolution_par_secteur(db_session):
    from sqlalchemy import text as _t

    from labuse.faisabilite import bilan_params as bp
    db_session.execute(_t("CREATE TABLE IF NOT EXISTS bilan_params (secteur varchar(64), param varchar(48),"
                          " value double precision, is_placeholder boolean DEFAULT false,"
                          " updated_at timestamptz DEFAULT now(), PRIMARY KEY (secteur, param))"))
    bp.save(db_session, "Le Guillaume", "cout_construction_m2_sdp", 3200.0)
    bp.save(db_session, "*", "prix_m2_lls", 2600.0)
    a = bp.resolve(db_session, "Saint-Paul Centre")
    b = bp.resolve(db_session, "Le Guillaume")
    # Le secteur « Guillaume » (3200) ne fuit PAS vers un autre secteur — qui retombe sur le
    # socle global/défaut (le socle web sourcé peut peupler '*', d'où source 'défaut' OU 'global').
    assert a["cout_construction_m2_sdp"]["value"] != 3200.0
    assert a["cout_construction_m2_sdp"]["source"] in ("défaut", "global")
    assert b["cout_construction_m2_sdp"]["value"] == 3200.0 and b["cout_construction_m2_sdp"]["source"] == "secteur"
    assert a["prix_m2_lls"]["source"] == "global" and a["prix_m2_lls"]["value"] == 2600.0
    assert "Coût de construction" in " ".join(bp.uncalibrated_critical({"cout_construction_m2_sdp": {"is_placeholder": True}}))
