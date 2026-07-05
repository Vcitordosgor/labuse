"""BODACC — Vague A1 : parsing, connecteur (batch/pagination), croisement & flag.

Schéma d'annonce figé sur un enregistrement RÉEL vérifié le 05/07/2026 (id A200902491993).
Les tests DB verrouillent le flag « foncier sous pression » et l'ABSENCE de faux flag.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text

from labuse.connectors.bodacc import BodaccConnector, extract_siren, parse_record
from labuse.ingestion.bodacc import (
    SOURCE_NAME,
    distinct_sirens,
    ingest_bodacc,
    parcelles_sous_pression,
)

# Enregistrement RÉEL (schéma vérifié) — procédure collective, SIREN dans `registre`.
REC = {
    "id": "A200902491993", "publicationavis": "A", "parution": "20090249",
    "dateparution": "2009-12-27", "numeroannonce": 1993, "typeavis": "annonce",
    "familleavis": "collective", "familleavis_lib": "Procédures collectives",
    "tribunal": "TRIBUNAL DE COMMERCE DE BOULOGNE-SUR-MER",
    "commercant": "LE SAGITTAIRE, HEMBERT, Lionel, Yvon, André",
    "registre": ["482 309 382", "482309382"],
    "jugement": {"famille": "Jugement prononçant",
                 "nature": "Jugement de conversion en liquidation judiciaire",
                 "date": "10 décembre 2009", "type": "initial"},
}


# ───────────────────────── parsing (pur) ─────────────────────────

def test_extract_siren():
    assert extract_siren(["482 309 382", "482309382"]) == "482309382"
    assert extract_siren("123456789") == "123456789"
    assert extract_siren(["pas un siren"]) is None
    assert extract_siren([]) is None
    assert extract_siren(None) is None


def test_parse_record_reel():
    p = parse_record(REC)
    assert p["annonce_id"] == "A200902491993"
    assert p["siren"] == "482309382"
    assert "liquidation" in p["type_procedure"].lower()
    assert p["famille_jugement"] == "Jugement prononçant"
    assert p["date_annonce"] == date(2009, 12, 27)
    assert p["date_jugement_txt"] == "10 décembre 2009"   # texte FR brut, non parsé
    assert p["numero_annonce"] == 1993 and p["publication"] == "A"
    assert "A200902491993" in p["url_source"]


def test_parse_record_sans_siren_est_ignore():
    assert parse_record({"id": "X", "registre": ["pas un siren"], "familleavis": "collective"}) is None
    assert parse_record({"id": "X", "familleavis": "collective"}) is None


def test_parse_record_jugement_string_json():
    # L'API ODS renvoie `jugement` comme une CHAÎNE JSON (vérifié live) — doit être décodée,
    # sinon type_procedure/date_jugement seraient toujours perdus (bug attrapé au sample).
    rec = {"id": "A202500995044", "registre": ["383755949", "383 755 949"],
           "dateparution": "2025-05-23", "familleavis": "collective",
           "jugement": '{"famille": "Jugement pronon\\u00e7ant", "nature": '
                       '"Jugement de conversion en redressement judiciaire", "date": "2025-04-16"}'}
    p = parse_record(rec)
    assert p["siren"] == "383755949"
    assert p["type_procedure"] == "Jugement de conversion en redressement judiciaire"
    assert p["date_jugement_txt"] == "2025-04-16"


def test_parse_record_jugement_absent():
    p = parse_record({"id": "A1", "registre": ["552100554"], "dateparution": "2024-02-03"})
    assert p["siren"] == "552100554" and p["type_procedure"] is None
    assert p["date_annonce"] == date(2024, 2, 3)


def test_source_name_coherent():
    assert BodaccConnector.name == SOURCE_NAME


# ───────────────────────── connecteur : batch + pagination (stub, sans réseau) ─────────────

def _rec(i: int, siren: str = "482309382") -> dict:
    return {"id": f"A{i:013d}", "publicationavis": "A", "dateparution": "2020-01-01",
            "numeroannonce": i, "familleavis": "collective", "tribunal": "TC X",
            "registre": [siren], "jugement": {"famille": "F", "nature": "Liquidation judiciaire",
                                              "date": "1 janvier 2020"}}


def test_connecteur_pagine(monkeypatch):
    conn = BodaccConnector()

    def fake_page(where, offset, max_retries=4):
        if offset == 0:
            return {"results": [_rec(i) for i in range(100)], "total_count": 150}
        return {"results": [_rec(i) for i in range(100, 150)], "total_count": 150}

    monkeypatch.setattr(conn, "_get_page", fake_page)
    out = list(conn.fetch_collective_by_sirens(["482309382"], throttle_s=0))
    assert len(out) == 150   # a suivi la 2e page


def test_connecteur_plusieurs_batches(monkeypatch):
    conn = BodaccConnector()
    wheres: list[str] = []

    def fake_page(where, offset, max_retries=4):
        wheres.append(where)
        return {"results": [_rec(0)], "total_count": 1}

    monkeypatch.setattr(conn, "_get_page", fake_page)
    out = list(conn.fetch_collective_by_sirens(["482309382", "111111118"], batch_size=1, throttle_s=0))
    assert len(out) == 2 and len(wheres) == 2   # 2 SIREN, batch_size=1 → 2 requêtes


# ───────────────────────── croisement / flag (DB) ─────────────────────────

pytestmark_db = pytest.mark.db


def _pm(db, idu, siren, denom="SCI TEST"):
    db.execute(text(
        "INSERT INTO parcelle_personne_morale (idu, siren, denomination, source, date_import) "
        "VALUES (:i,:s,:d,'test',now()) ON CONFLICT (idu) DO NOTHING"),
        {"i": idu, "s": siren, "d": denom})


def _proc(siren, aid, nature="Liquidation judiciaire", da=date(2020, 1, 1)):
    return {"annonce_id": aid, "siren": siren, "type_procedure": nature,
            "famille_jugement": "Jugement prononçant", "date_annonce": da,
            "date_jugement_txt": "1 janvier 2020", "tribunal": "TC SAINT-DENIS",
            "numero_annonce": 1, "publication": "A", "url_source": "http://x/" + aid,
            "raw": {"id": aid}}


class _StubConn:
    """Connecteur factice : rejoue des procédures pré-parsées, sans réseau."""

    def __init__(self, procs):
        self._procs = procs

    def fetch_collective_by_sirens(self, sirens, batch_size=40):
        s = set(sirens)
        for p in self._procs:
            if p["siren"] in s:
                yield p


@pytest.mark.db
def test_distinct_sirens_filtre_et_commune(db_session):
    _pm(db_session, "97415000AA0001", "482309382")
    _pm(db_session, "97415000AA0002", "")            # vide → exclu
    _pm(db_session, "97415000AA0003", "12345")       # mal formé → exclu
    _pm(db_session, "97411000AA0001", "999999999")   # autre commune
    db_session.flush()
    sp = distinct_sirens(db_session, "97415")
    assert "482309382" in sp and "999999999" not in sp
    assert all(len(s) == 9 and s.isdigit() for s in sp)
    ile = distinct_sirens(db_session)
    assert "999999999" in ile


@pytest.mark.db
def test_ingest_flag_et_pas_de_faux_flag(db_session):
    _pm(db_session, "97415000AA0001", "482309382", "SCI SOUS PRESSION")
    _pm(db_session, "97415000AA0002", "111111118", "SCI SAINE")   # aucune procédure
    db_session.flush()
    conn = _StubConn([_proc("482309382", "A0001"),
                      _proc("482309382", "A0002", da=date(2021, 5, 1))])  # plus récente
    res = ingest_bodacc(db_session, ["482309382", "111111118"], connector=conn)
    assert res["procedures"] == 2 and res["sirens_with_procedure"] == 1

    flags = parcelles_sous_pression(db_session, "97415")
    idus = {f["idu"] for f in flags}
    assert "97415000AA0001" in idus          # propriétaire sous procédure → flaggé
    assert "97415000AA0002" not in idus      # pas de procédure → PAS de faux flag
    f = next(f for f in flags if f["idu"] == "97415000AA0001")
    assert f["source"] == "BODACC" and f["date_annonce"] == date(2021, 5, 1)  # la plus récente


@pytest.mark.db
def test_ingest_idempotent(db_session):
    _pm(db_session, "97415000AA0001", "482309382")
    db_session.flush()
    conn = _StubConn([_proc("482309382", "A0001"), _proc("482309382", "A0002")])
    ingest_bodacc(db_session, ["482309382"], connector=conn)
    ingest_bodacc(db_session, ["482309382"], connector=conn)   # re-run
    n = db_session.execute(text("SELECT count(*) FROM bodacc_procedures")).scalar()
    assert n == 2   # ON CONFLICT (annonce_id) → aucun doublon
