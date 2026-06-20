"""2.B — vue mer (line-of-sight 1D) : classification + bonus prix du bilan."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def _parcel(db, idu, wkt):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Maria','S','1', ST_GeomFromText(:w,4326), 1000, ST_Centroid(ST_GeomFromText(:w,4326)),"
        " ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"), {"i": idu, "w": wkt}).scalar()


def _cote(db, wkt):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, geom) VALUES "
        "('trait_de_cote','stable','côte','Maria', ST_GeomFromText(:w,4326))"), {"w": wkt})


def test_front_de_mer_oui(db_session, monkeypatch):
    from labuse.api import enrichment as E
    monkeypatch.setattr(E, "_live_enabled", lambda: True)
    # côte à ~40 m → front de mer → oui (sans appel RGE)
    _cote(db_session, "LINESTRING(55.2900 -21.00, 55.2900 -21.01)")
    pid = _parcel(db_session, "MER00001",
                  "POLYGON((55.2905 -21.005,55.2906 -21.005,55.2906 -21.0045,55.2905 -21.0045,55.2905 -21.005))")
    r = E.vue_mer(db_session, pid)
    assert r["available"] and r["vue"] == "oui" and "front de mer" in r["label"]
    # mémoïsé en cache
    assert db_session.execute(text("SELECT vue FROM parcel_vue_mer WHERE parcel_id=:p"), {"p": pid}).scalar() == "oui"


def test_profil_degage_oui_et_relief_non(db_session, monkeypatch):
    from labuse.api import enrichment as E
    monkeypatch.setattr(E, "_live_enabled", lambda: True)
    _cote(db_session, "LINESTRING(55.300 -21.10, 55.300 -21.11)")
    pid = _parcel(db_session, "MER00002",
                  "POLYGON((55.3100 -21.105,55.3101 -21.105,55.3101 -21.1045,55.3100 -21.1045,55.3100 -21.105))")
    # profil DÉGAGÉ : descente régulière de l'observateur vers la mer → oui
    monkeypatch.setattr(E, "_alti_query", lambda pts, t: [50.0 * (1 - k / (len(pts) - 1)) for k in range(len(pts))])
    assert E.vue_mer(db_session, pid)["vue"] == "oui"
    # profil avec RELIEF masquant (colline au milieu, bien au-dessus de la ligne de vue) → non
    def relief(pts, t):
        n = len(pts)
        return [50.0 if k == 0 else (220.0 if 5 <= k <= 20 else 30.0) for k in range(n)]
    monkeypatch.setattr(E, "_alti_query", relief)
    assert E.vue_mer(db_session, pid)["vue"] in ("non", "partielle")


def test_bilan_bonus_vue_mer():
    from labuse.faisabilite.bilan import compute_bilan
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses()
    prix = {"fiable": True, "fiabilite": "fiable", "fiabilite_raisons": [], "type_prix": "appartement",
            "n": 40, "n_exclus": 0, "n_doublons": 0, "radius_m": 1500.0, "commune_fallback": False,
            "pct_appartement": 100, "periode": [2022, 2025], "q1": 2200, "median": 3000, "q3": 4300,
            "min": 2000, "max": 4700}
    bp = {"bonus_vue_mer_pct": 12}
    sans = compute_bilan(4600, 4500, prix, h, bilan_params=bp)              # pas de vue → pas de bonus
    avec = compute_bilan(4600, 4500, prix, h, contexte_eco={"vue_mer": "oui"}, bilan_params=bp)
    assert sans.ca["central"] == round(4600 * 3000)
    assert avec.ca["central"] == round(4600 * 3000 * 1.12)
    assert any("Bonus vue mer" in s.label for s in avec.steps)
