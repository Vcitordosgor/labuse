"""POST-M7 · J+2 — chaîne de fraîcheur : garde-fou tables de run, détection DVF, matrice, réveil DPE.

L'idempotence réelle (double run = même empreinte) est prouvée sur base réelle au rapport J2_FRAICHEUR.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.ingestion import fraicheur as f

ROOT = Path(__file__).resolve().parents[1]


def test_garde_fou_tables_de_run_jamais_ecrites():
    """INTERDIT ABSOLU (statique) : aucun module de la chaîne de fraîcheur n'écrit dans les tables
    de run. On vérifie l'absence d'INSERT/UPDATE/DELETE/DROP sur ces tables dans les sources."""
    modules = ["fraicheur.py", "pc_caducs.py", "defisc_fenetres.py", "surface_d.py",
               "permit_delais_m10.py", "bodacc.py", "dpe.py"]
    ecritures = re.compile(
        r"(INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+TABLE(?:\s+IF\s+EXISTS)?|TRUNCATE)\s+(%s)"
        % "|".join(f.TABLES_RUN_INTERDITES), re.I)
    for m in modules:
        src = (ROOT / "src/labuse/ingestion" / m).read_text(encoding="utf-8")
        hit = ecritures.search(src)
        assert hit is None, f"{m} écrit dans une table de run : {hit.group(0)!r}"


def test_matrice_sources_couvre_le_mandat():
    # les 6 sources du mandat au minimum, chacune avec cadence + détection documentées
    for src in ("sitadel", "bodacc", "dvf", "dpe", "gpu_plu", "georisques"):
        assert src in f.SOURCES
        assert f.SOURCES[src]["cadence"] and f.SOURCES[src]["detection"]
    # les couches de la cascade gelée ne sont JAMAIS auto-ingérées
    assert f.SOURCES["gpu_plu"]["auto"] is False and f.SOURCES["georisques"]["auto"] is False


def test_seuil_reveil_dpe():
    assert f.SEUIL_REVEIL_DPE == 200      # F/G ∩ mono ∩ non-écarté ≥ 200 (cadrage cycle 3)


@pytest.mark.db
def test_etat_fraicheur_kv(db_session):
    s = db_session
    f._etat_set(s, "test:cle", "v1")
    assert f._etat_get(s, "test:cle") == "v1"
    f._etat_set(s, "test:cle", "v2")      # upsert idempotent
    assert f._etat_get(s, "test:cle") == "v2"


@pytest.mark.db
def test_dvf_detection_no_op_si_lastmod_connu(db_session, monkeypatch):
    """On ne retélécharge JAMAIS ce qu'on a : lastmod identique → no-op (aucun DELETE/reload)."""
    s = db_session

    class FakeResp:
        status_code = 200
        headers = {"last-modified": "Wed, 01 Apr 2026 10:00:00 GMT"}

    class FakeClient:
        def __init__(self, **kw): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def head(self, url): return FakeResp()

    monkeypatch.setattr(f.httpx, "Client", FakeClient)
    # 1er check : tout est « nouveau »
    c1 = f.check_dvf_livraison(s)
    assert c1["n"] >= 1
    # on enregistre l'état (comme le ferait refresh_dvf) puis re-check → no-op
    for m in c1["modifies"]:
        f._etat_set(s, f"dvf:lastmod:{m['annee']}", m["lastmod"])
    c2 = f.check_dvf_livraison(s)
    assert c2["n"] == 0


@pytest.mark.db
def test_compteur_reveil_dpe_vide(db_session):
    s = db_session
    s.execute(text("CREATE TABLE IF NOT EXISTS dpe_records (parcelle_idu varchar(14), etiquette_dpe varchar(2), date_etablissement date)"))
    r = f.compteur_reveil_dpe(s)
    assert r["n"] == 0 and r["franchi"] is False and r["seuil"] == 200
