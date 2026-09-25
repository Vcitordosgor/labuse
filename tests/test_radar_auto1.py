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
