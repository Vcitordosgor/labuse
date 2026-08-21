"""O2 — SCOREUR D'ADRESSE INVERSÉ : tests logique prix (pur) + flux adresse→parcelle→verdict (DB).

Le prix demandé est saisi À LA MAIN (jamais scrapé) ; confronté à la charge foncière supportable et
au prix probable (Score É V2). Une adresse hors base → réponse honnête, jamais un verdict inventé.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import scoreur
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL  # M31 : seed sous le run SERVI, pas un littéral


# ───────────────────────── logique prix (pur) — M137-S : deux repères NOMMÉS ─────────────────────────
# Le badge juge UN SEUL repère (marché du foncier) ; la marge juge l'opération de promotion, à part.

def test_badge_sous_marche_marge_operation_separee():
    # 80 000 € sous le prix probable du foncier (100 000) → badge « en dessous du marché » ;
    # la marge (charge 200 000 − 80 000 = +120 000) juge l'OPÉRATION, séparément.
    r = scoreur._prix_verdict(80000, charge=200000, prix_probable=100000, surface=1000)
    assert r["verdict"] == "sous_marche" and r["marge_a_ce_prix_eur"] == 120000
    assert r["prix_demande_m2_terrain"] == 80 and "Estimé" in r["avertissement"]
    assert "rentable" in r["synthese"]                       # marge positive → opération rentable


def test_badge_dans_marche_marge_negative_reconciliee():
    # LE cas majoritaire (~69 %) : prix au niveau du marché MAIS marge négative
    # (charge 90 000 − prix 100 000 = −10 000). Badge « dans le marché » + synthèse qui réconcilie.
    r = scoreur._prix_verdict(100000, charge=90000, prix_probable=100000, surface=1000)
    assert r["verdict"] == "dans_marche" and r["marge_a_ce_prix_eur"] == -10000
    assert "se vend à son prix" in r["synthese"] and "pas rentable" in r["synthese"]


def test_badge_sur_marche():
    r = scoreur._prix_verdict(500000, 200000, 100000, 1000)
    assert r["verdict"] == "sur_marche" and r["marge_a_ce_prix_eur"] == -300000


def test_badge_ne_juge_jamais_l_operation():
    # garde anti-régression : le badge ne sort JAMAIS un verdict d'opération (« opportunité » retiré) —
    # ses trois états sont sur le seul repère marché, quel que soit le rapport prix/charge.
    for prix in (10000, 80000, 100000, 500000):
        assert scoreur._prix_verdict(prix, 200000, 100000, 1000)["verdict"] in (
            "sous_marche", "dans_marche", "sur_marche")


def test_prix_non_estimable_sans_charge():
    r = scoreur._prix_verdict(80000, charge=None, prix_probable=None, surface=1000)
    assert r["verdict"] == "non_estimable" and "non estimable" in r["message"].lower()
    assert "marge_a_ce_prix_eur" not in r                    # pas de marge sans charge/prix probable


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
        "VALUES (:run, :i, 0.5, 30.0, 90.0, 1, 0.2, 1.5, '[]', false, :t, 'test')"),
        {"i": idu, "t": tier, "run": Q_A_RUN_LABEL})
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
    assert out["verdict"]["tier"] == "a_creuser" and out["verdict"]["libelle"] == "Neutre"  # M137 chip court
    assert out["score_e"]["estimable"] is True
    # 80 000 € sous le prix probable du foncier (100 000) → badge « en dessous du marché » ;
    # la marge d'opération (charge 300 000 − 80 000 = +220 000) reste un repère distinct.
    assert out["prix"]["verdict"] == "sous_marche" and out["prix"]["marge_a_ce_prix_eur"] == 220000
    assert "rentable" in out["prix"]["synthese"]


@pytest.mark.db
def test_adresse_hors_base_reponse_honnete(db_session, monkeypatch):
    s = db_session
    monkeypatch.setattr(scoreur, "_geocode", lambda q: {"lon": 2.35, "lat": 48.85, "label": "Paris"})
    out = scoreur.scoreur_adresse(scoreur.ScoreurIn(q="paris"), s)
    assert out["ok"] is False and "Aucune parcelle" in out["message"]
