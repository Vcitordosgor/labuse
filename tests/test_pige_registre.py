"""RADAR P456 · D4 — le Radar au registre des sources + fraîcheur = dernière COLLECTE (jamais un run)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion.seed_sources import seed
from labuse.pige.tables import enregistrer_fraicheur

pytestmark = pytest.mark.db

NOM = "Radar (pige d'annonces)"


def test_radar_au_registre_des_sources(engine):
    with session_scope() as db:
        seed(db)
        db.commit()
        row = db.execute(text("SELECT status, source_cadence, category FROM data_sources WHERE name = :n"),
                         {"n": NOM}).mappings().first()
    assert row is not None and row["status"] == "manuel" and row["source_cadence"] == "quotidien"


def test_fraicheur_est_la_derniere_collecte(engine):
    tag = uuid.uuid4().hex[:4]
    with session_scope() as db:
        seed(db)
        bid = db.execute(text("INSERT INTO pige_biens (commune,type_bien,est_copro,rattachement_niveau,statut) "
                              "VALUES ('Saint-Paul','maison',false,'absent','active') RETURNING bien_id")).scalar()
        db.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante,date_saisie) "
                        "VALUES (:b,'leboncoin',:u, now())"), {"b": bid, "u": f"https://www.leboncoin.fr/rt-{tag}"})
        pose = enregistrer_fraicheur(db)
        db.commit()
        last = db.execute(text("SELECT last_sync_at FROM data_sources WHERE name = :n"), {"n": NOM}).scalar()
        # la fraîcheur = max(date_saisie), et non une date de run
        maxsaisie = db.execute(text("SELECT max(date_saisie) FROM pige_annonces")).scalar()
        assert pose is not None and last == maxsaisie
        db.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": bid})
        db.commit()
