"""O5 — SERVITUDES INVISIBLES : décodage des couches dormantes, sourcées + datées.

SUP décodée en effet concret ; dédup ; couches non ingérées dites « non couvertes » (jamais faux RAS).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import servitudes as sv


# ───────────────────────── décodage (pur) ─────────────────────────

def test_sup_decode_pm1_risques():
    d = sv._detail("sup", "pm1", "PM1_PPR_i_mvt", {"typeass": "Enveloppe des zonages réglementaires"})
    assert "Risques naturels (PPR)" in d and "Enveloppe" in d


def test_sup_i3_gaz():
    assert "gaz" in sv._detail("sup", "I3", None, None).lower()


def test_sol_pollue_sis():
    assert "SIS" in sv._detail("sol_pollue", "sis", None, None)


def test_bruit_categorie():
    assert "catégorie 3" in sv._detail("bruit_route", "cat3", None, None)


def test_sup_inconnu_ne_ment_pas():
    d = sv._detail("sup", "ZZ9", None, None)
    assert "ZZ9" in d          # code inconnu affiché tel quel, jamais inventé


def test_non_couvert_liste_les_manques():
    assert any("Canalisations" in x for x in sv._NON_COUVERT)


# ───────────────────────── flux DB ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


@pytest.mark.db
def test_flux_sup_sourcee_datee_et_dedup(db_session):
    s = db_session
    idu = "97499000SV0001"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    ds = s.execute(text("INSERT INTO data_sources (name, status, last_sync_at) "
                        "VALUES ('SUP test', 'ok', '2026-07-10') RETURNING id")).scalar()
    # deux enveloppes de la MÊME SUP → une seule ligne (dédup)
    for gen in ("gen1", "gen2"):
        s.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, attrs, data_source_id, geom, geom_2975) VALUES "
            "('sup','pm1',:n, '{\"typeass\":\"Enveloppe\"}', :ds, ST_GeomFromText(:w,4326), "
            " ST_Transform(ST_GeomFromText(:w,4326),2975))"),
            {"n": f"PM1_{gen}", "ds": ds, "w": _WKT})

    out = sv.servitudes_invisibles(idu, s)
    assert out["n"] == 1                                   # dédup : gen1+gen2 = 1 ligne
    it = out["servitudes"][0]
    assert "Risques naturels" in it["effet"] and it["source"] == "SUP test" and it["date"] == "2026-07-10"
    assert out["non_couvert"]                              # manques listés


@pytest.mark.db
def test_flux_ras_honnete(db_session):
    s = db_session
    idu = "97499000SV0002"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','2', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    out = sv.servitudes_invisibles(idu, s)
    assert out["n"] == 0 and "Aucune servitude" in out["synthese"]
    assert "ne vaut pas absence réelle" in out["avertissement"]   # jamais un faux RAS définitif
