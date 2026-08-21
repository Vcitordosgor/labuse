"""O2 — SCOREUR D'ADRESSE INVERSÉ : tests logique prix (pur) + flux adresse→parcelle→verdict (DB).

Le prix demandé est saisi À LA MAIN (jamais scrapé) ; confronté à la charge foncière supportable et
au prix probable (Score É V2). Une adresse hors base → réponse honnête, jamais un verdict inventé.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import scoreur
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL  # M31 : seed sous le run SERVI, pas un littéral


# ─────────── logique prix (pur) — M128-6-§1.3 : CONSTAT chiffré nu, AUCUN verdict ───────────
# La charge vient de la méthode DOCUMENTS (bilan à rebours). On sert des NOMBRES, jamais une conclusion.

def test_constat_marge_chiffree_sans_verdict():
    # charge 200 000 (méthode documents) − prix 80 000 = +120 000. Aucun mot de verdict.
    r = scoreur._prix_constat(80000, charge=200000, prix_probable=100000, surface=1000)
    assert r["marge_a_ce_prix_eur"] == 120000 and r["charge_fonciere_supportable_eur"] == 200000
    assert r["prix_saisi_m2_terrain"] == 80 and "Estimé" in r["avertissement"]
    assert r["prix_probable_foncier_eur"] == 100000 and r["ecart_vs_prix_probable_pct"] == -20
    # AUCUN verdict / conclusion servie au tiers
    assert "verdict" not in r and "synthese" not in r
    txt = " ".join(str(v) for v in r.values()).lower()
    for mot in ("rentable", "bonne affaire", "au-dessus du marché", "sous le marché", "validé", "opportunité"):
        assert mot not in txt


def test_constat_marge_negative_reste_un_nombre():
    r = scoreur._prix_constat(100000, charge=90000, prix_probable=100000, surface=1000)
    assert r["marge_a_ce_prix_eur"] == -10000 and r["ecart_vs_prix_probable_pct"] == 0
    assert "verdict" not in r and "synthese" not in r


def test_constat_prix_non_chiffrable_sans_charge():
    r = scoreur._prix_constat(80000, charge=None, prix_probable=None, surface=1000)
    assert "marge_a_ce_prix_eur" not in r and "non calculable" in r["message"].lower()
    assert "verdict" not in r


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
    # M128-5-§2 : la marge score_e (barème sectoriel, méthode divergente) n'est plus servie au tiers.
    assert "score_e" not in out
    # M128-6-§1 : le prix saisi est confronté à la charge DOCUMENTS (compute_bilan), servie seulement
    # si le bilan est calculable. Le prix probable (médiane terrain, NON divergent) reste servi ;
    # aucun verdict / conclusion (§1.3).
    assert "verdict" not in out["prix"] and "synthese" not in out["prix"]
    assert out["prix"]["prix_probable_foncier_eur"] == 100000
    assert out["prix"]["ecart_vs_prix_probable_pct"] == -20


@pytest.mark.db
def test_adresse_hors_base_reponse_honnete(db_session, monkeypatch):
    s = db_session
    monkeypatch.setattr(scoreur, "_geocode", lambda q: {"lon": 2.35, "lat": 48.85, "label": "Paris"})
    out = scoreur.scoreur_adresse(scoreur.ScoreurIn(q="paris"), s)
    assert out["ok"] is False and "Aucune parcelle" in out["message"]
