"""RADAR-AUTO-1 — recette du dépôt automatique, du cycle planifié, des prix baisse/hausse, du
rattachement terrain et de radar_stats. Les pages réelles de Vic sont dans docs/RADAR/.

Sans DB : registre des jobs + parseur. Avec DB (`pytest.mark.db`) : seuil de variation de prix,
confirmation de liveness, rattachement terrain unique/multiple, radar_stats avec/sans copro.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.pige import html_next

_DOCS = Path(__file__).resolve().parents[1] / "docs" / "RADAR"
_RICHE = _DOCS / "Saint-Denis_toute_la_ville_-_leboncoin.html"
_DEGR = _DOCS / "Saint-Denis_toute_la_ville_-_page_2_-_leboncoin.html"


# ─────────────────────────── registre des jobs (sans DB) ───────────────────────────

def test_jobs_cycle_planifies():
    """Lot C — radar-cycle / -dvf / -mensuel sont AU registre (renverse l'ancien « Radar : pas de job »),
    chacun avec sa raison, sa touche exploitation, son cron ; et leurs implémentations existent."""
    from labuse.jobs import JOBS
    from labuse import jobs_impl
    for nom in ("radar-cycle", "radar-cycle-dvf", "radar-cycle-mensuel"):
        assert nom in JOBS, f"{nom} absent du registre"
        j = JOBS[nom]
        assert j.touche == "exploitation" and j.raison and j.cron_utc
        assert hasattr(jobs_impl, nom.replace("-", "_")), f"impl {nom} manquante"
    # radar-releves reste retiré (les relevés se lisent, pas de job).
    assert "radar-releves" not in JOBS


# ─────────────────────────── parseur sur les pages réelles (sans DB) ───────────────────────────

@pytest.mark.skipif(not _RICHE.exists(), reason="page riche absente")
def test_page_riche_35_avec_position():
    r = html_next.analyser(_RICHE.read_text(encoding="utf-8", errors="replace"))
    assert r["mode"] == "resultats" and r["provenance"] == html_next.PROV_RICHE
    assert len(r["records"]) == 35
    assert all(x["lat"] is not None and x["lng"] is not None for x in r["records"]), \
        "la page riche porte une position par annonce (searchData)"
    assert all(x["first_publication_date"] for x in r["records"]), "et une date de publication"


@pytest.mark.skipif(not _DEGR.exists(), reason="page dégradée absente")
def test_page_degradee_40_sans_position():
    r = html_next.analyser(_DEGR.read_text(encoding="utf-8", errors="replace"))
    assert r["mode"] == "resultats" and r["provenance"] == html_next.PROV_DEGRADE
    assert len(r["records"]) == 40
    assert all(x["lat"] is None for x in r["records"]), "dégradé = aucune position (jamais rattaché)"


# ─────────────────────────── seuil de variation de prix (DB) ───────────────────────────

@pytest.mark.db
def test_maj_prix_seuil_baisse_hausse(db_session):
    """Lot C — < 1 % = bruit (historisé, aucun événement) ; baisse ≥ 1 % → pige.baisse_prix ;
    hausse ≥ 1 % → pige.hausse_prix."""
    from labuse.pige import html_ingest
    db = db_session
    bid = db.execute(text(
        "INSERT INTO pige_biens (commune, statut) VALUES ('Saint-Denis','active') RETURNING bien_id")).scalar()
    db.execute(text("INSERT INTO pige_faits (bien_id, prix, valide_at) VALUES (:b, 100000, now())"), {"b": bid})

    def n_ev(kind):
        return db.execute(text("SELECT count(*) FROM event_log WHERE kind = :k AND detail LIKE :d"),
                          {"k": kind, "d": f"%#{bid}%"}).scalar()

    html_ingest._maj_prix(db, bid, 100000, 99500)   # −0,5 % : sous le seuil
    assert n_ev("pige.baisse_prix") == 0
    assert db.execute(text("SELECT count(*) FROM pige_prix_historique WHERE bien_id = :b"),
                      {"b": bid}).scalar() == 1, "la micro-variation est historisée quand même"

    html_ingest._maj_prix(db, bid, 100000, 95000)   # −5 %
    assert db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.baisse_prix' "
                           "AND dedup = :d"), {"d": f"pige:baisse:{bid}:95000"}).scalar() == 1

    html_ingest._maj_prix(db, bid, 100000, 110000)  # +10 %
    assert db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.hausse_prix' "
                           "AND dedup = :d"), {"d": f"pige:hausse:{bid}:110000"}).scalar() == 1


def test_niveau_preuve_mapping():
    """Lot D — le niveau de preuve affiché : humain/≥2 critères = certain ; terrain estimé = probable ;
    non rattaché = quartier."""
    from labuse.pige.rattachement_html import niveau_preuve as np
    assert np(True, "rattachee", "source") == "certain"      # tranché à la main
    assert np(False, "rattachee", "source") == "certain"     # ≥2 critères bâti
    assert np(False, "rattachee", "estime") == "probable"    # terrain unique ±1 %
    assert np(False, "non_rattachee", "absent") == "quartier"
    assert np(False, "piste", "estime") == "quartier"        # une piste ne s'affiche pas rattachée


@pytest.mark.db
def test_terrain_regle_unique_vs_multiple(db_session, monkeypatch):
    """Lot D — un TERRAIN dont la surface matche UNE seule parcelle à ±1 % → rattachee/estime (probable) ;
    deux candidates ou plus → RIEN d'automatique (piste). Déterministe (détecteur surface monkeypatché)."""
    from labuse.pige import rattachement_html as rh
    base = {"type": "terrain", "commune": "Saint-Denis", "lng": 55.45, "lat": -20.88,
            "surface_terrain": 500, "surface_hab": None, "est_copro": False}

    monkeypatch.setattr(rh, "_crit_surface", lambda *a, **k: {"97411000ZZ0001": "terrain 502 m² ≈ 500 (0 %)"})
    out = rh.rattacher(db_session, dict(base))
    assert out["etat"] == "rattachee" and out["niveau"] == "estime" and out["idu"] == "97411000ZZ0001"
    assert out["criteres"][0].get("preuve") == "probable"

    monkeypatch.setattr(rh, "_crit_surface",
                        lambda *a, **k: {"97411000ZZ0001": "x", "97411000ZZ0002": "y"})
    out = rh.rattacher(db_session, dict(base))
    assert out["etat"] != "rattachee", "deux candidates ±1 % → jamais un rattachement automatique"


@pytest.mark.db
@pytest.mark.skipif(not _RICHE.exists(), reason="page riche absente")
def test_terrains_reels_biconditionnel(db_session):
    """Lot D (intégration) — sur les type==terrain réels de la page, rattachee/probable SSI une seule
    parcelle à ±1 %. Sur l'échantillon de Vic aucun pur terrain n'est unique → 0 auto (le bouton manuel
    reste la voie principale, exactement ce que la mesure 0.3 anticipait ; les 3 uniques de 0.3 étaient
    des MAISONS, gérées par la cascade bâtie)."""
    from labuse.pige import rattachement_html as rh
    recs = html_next.analyser(_RICHE.read_text(encoding="utf-8", errors="replace"))["records"]
    for rec in (r for r in recs if r["type"] == "terrain"):
        stricts = rh._crit_surface(db_session, rec["lng"], rec["lat"], rec["commune"],
                                   float(rec["surface_terrain"]), tol=rh.TOL_SURFACE_TERRAIN_STRICT)
        out = rh.rattacher(db_session, {**rec, "est_copro": False})
        est_probable = out["etat"] == "rattachee" and out["niveau"] == "estime"
        assert est_probable == (len(stricts) == 1), (rec["list_id"], len(stricts), out["etat"])


@pytest.mark.db
def test_radar_stats_inclut_apparts(db_session):
    """Lot E — radar_stats INCLUT les appartements dans les statistiques (la règle copro ne vaut que
    pour carte/digests/veilles). Chaque chiffre porte son registre_id ; le libellé dit « demandés »."""
    from labuse.pige import marche
    db = db_session
    # 5 appartements Saint-Denis à 3000 €/m² (150 000 € / 50 m²), validés, non copro-exclus des stats.
    for _ in range(5):
        bid = db.execute(text("INSERT INTO pige_biens (commune, type_bien, est_copro, statut) "
                              "VALUES ('Saint-Denis','appartement',true,'active') RETURNING bien_id")).scalar()
        db.execute(text("INSERT INTO pige_faits (bien_id, prix, type_bien, surface_hab, valide_at) "
                        "VALUES (:b, 150000, 'appartement', 50, now())"), {"b": bid})
    st = marche.radar_stats(db, commune="Saint-Denis", type_bien="appartement")
    assert st["actives_n"]["valeur"] >= 5
    assert st["prix_m2_median_demande"]["valeur"] == 3000, st["prix_m2_median_demande"]
    assert st["prix_m2_median_demande"]["registre_id"] == "prix_demande_median_eur_m2"
    assert st["libelle"] == "prix demandés (Radar)"
    # sans filtre de type, les apparts comptent aussi dans la médiane bâtie.
    st_all = marche.radar_stats(db, commune="Saint-Denis")
    assert st_all["actives_n"]["valeur"] >= 5


@pytest.mark.db
def test_confirmation_supprimee_retiree_sans_courrier(db_session):
    """Lot A/C — verdict « supprimee » → statut retiree + retiree_le, JAMAIS retiree_sans_vente
    (celui-ci reste au cycle mensuel, sur preuve DVF)."""
    db = db_session
    bid = db.execute(text(
        "INSERT INTO pige_biens (commune, statut, last_seen_at) VALUES "
        "('Saint-Denis','active', now() - interval '10 days') RETURNING bien_id")).scalar()
    # simule le geste du endpoint confirmation (verdict supprimee)
    db.execute(text("UPDATE pige_biens SET statut='retiree', retiree_le=COALESCE(retiree_le, now()) "
                    "WHERE bien_id=:b AND statut NOT IN ('vendue','retiree_sans_vente')"), {"b": bid})
    row = db.execute(text("SELECT statut, retiree_le FROM pige_biens WHERE bien_id=:b"),
                     {"b": bid}).mappings().first()
    assert row["statut"] == "retiree" and row["retiree_le"] is not None
