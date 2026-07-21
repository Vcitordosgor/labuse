"""O2 — SCOREUR D'ADRESSE INVERSÉ : tests logique prix (pur) + flux adresse→parcelle→verdict (DB).

Le prix demandé est saisi À LA MAIN (jamais scrapé) ; confronté à la charge foncière supportable et
au prix probable (Score É V2). Une adresse hors base → réponse honnête, jamais un verdict inventé.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import scoreur


# ───────────────────────── logique prix (pur) ─────────────────────────

def test_prix_opportunite_sous_charge():
    r = scoreur._prix_verdict(80000, charge=200000, prix_probable=100000, surface=1000)
    assert r["verdict"] == "opportunite" and r["marge_a_ce_prix_eur"] == 120000
    assert r["prix_demande_m2_terrain"] == 80 and "Estimé" in r["avertissement"]


def test_prix_dans_le_marche():
    assert scoreur._prix_verdict(105000, 100000, 100000, 1000)["verdict"] == "dans_le_marche"


def test_prix_cher():
    assert scoreur._prix_verdict(500000, 200000, 100000, 1000)["verdict"] == "cher"


def test_prix_non_estimable_sans_charge():
    r = scoreur._prix_verdict(80000, charge=None, prix_probable=None, surface=1000)
    assert r["verdict"] == "non_estimable" and "non estimable" in r["message"].lower()


# ───────────────────────── flux DB (adresse simulée → parcelle) ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


def _seed(s, idu, tier="a_creuser", marge=250000):
    pid = s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": _WKT}).scalar()
    s.execute(text(
        "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, rang, "
        "contrib_z, contrib_d, top5_contributions, copro, tier, model_version) "
        "VALUES ('q_v7_defisc', :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"i": idu, "t": tier})
    s.execute(text("CREATE TABLE IF NOT EXISTS score_e (idu varchar(14) PRIMARY KEY, estimable boolean, "
                   "marge_estimee int, charge_supportable int, prix_probable int, niveau_prix text, "
                   "libelle_court text, detail text)"))
    s.execute(text("INSERT INTO score_e (idu, estimable, marge_estimee, charge_supportable, prix_probable, "
                   "niveau_prix, libelle_court, detail) VALUES (:i, true, :m, 300000, 100000, 'secteur', 'x', 'y')"),
              {"i": idu, "m": marge})
    return pid


@pytest.mark.db
def test_flux_adresse_verdict_et_prix(db_session, monkeypatch):
    s = db_session
    idu = "97499000ZS0001"
    _seed(s, idu)
    # centroïde de la parcelle seedée sert de résultat de géocodage
    lon, lat = s.execute(text("SELECT ST_X(centroid), ST_Y(centroid) FROM parcels WHERE idu=:i"),
                         {"i": idu}).first()
    monkeypatch.setattr(scoreur, "_geocode", lambda q: {"lon": lon, "lat": lat, "label": "1 rue Test"})

    out = scoreur.scoreur_adresse(scoreur.ScoreurIn(q="1 rue test", prix_demande_eur=80000), s)
    assert out["ok"] and out["idu"] == idu
    assert out["verdict"]["tier"] == "a_creuser" and "creuser" in out["verdict"]["libelle"].lower()
    assert out["score_e"]["estimable"] is True
    # 80 000 € < charge supportable 300 000 € → opportunité
    assert out["prix"]["verdict"] == "opportunite" and out["prix"]["marge_a_ce_prix_eur"] == 220000


@pytest.mark.db
def test_adresse_hors_base_reponse_honnete(db_session, monkeypatch):
    s = db_session
    monkeypatch.setattr(scoreur, "_geocode", lambda q: {"lon": 2.35, "lat": 48.85, "label": "Paris"})
    out = scoreur.scoreur_adresse(scoreur.ScoreurIn(q="paris"), s)
    assert out["ok"] is False and "Aucune parcelle" in out["message"]
