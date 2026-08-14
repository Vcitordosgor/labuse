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


def test_m84_seuil_derive_de_la_cadence():
    """M84 — le seuil est 2× la cadence normée, jamais un chiffre arbitraire. Les sources sans
    cadence bornable n'ont PAS de seuil (elles ne peuvent pas être « en retard »)."""
    assert f.seuil_jours("sitadel") == 60      # mensuel  → 2×30
    assert f.seuil_jours("dpe") == 14          # hebdo    → 2×7
    assert f.seuil_jours("dvf") == 364         # semestriel → 2×182
    assert f.seuil_jours("ban") == 60
    for k in ("bodacc", "catnat", "gpu_plu", "georisques", "sudocuh", "ortho_piscine"):
        assert f.seuil_jours(k) is None        # event-driven / annuel / révisions → pas de seuil


def test_m84_statut_anti_faux_positif():
    """M84 — le piège du faux positif ne revient PAS dans le mécanisme : DVF semestriel à 226 j et
    SITADEL à 45 j sont À JOUR pour leur cadence ; les cadences libres ne sont jamais un retard ;
    un vrai décrochage (delta > seuil) est bien déclaré. Aucun accès base (fonction pure)."""
    assert f.statut_fraicheur("dvf", 226) == "a_jour"       # mesuré M84 : 226 < 364, pas un retard
    assert f.statut_fraicheur("sitadel", 45) == "a_jour"    # mesuré M84 : 45 < 60, cadence SDES
    assert f.statut_fraicheur("sitadel", 61) == "en_retard"  # au-delà du seuil → décrochage réel
    assert f.statut_fraicheur("dpe", 30) == "en_retard"
    assert f.statut_fraicheur("sitadel", None) == "sans_donnee"
    for k in ("bodacc", "sudocuh", "ortho_piscine", "gpu_plu", "georisques", "catnat"):
        assert f.statut_fraicheur(k, 9999) == "cadence_libre"   # jamais une alerte, quel que soit l'âge


@pytest.mark.db
def test_etat_fraicheur_kv(db_session):
    s = db_session
    f._etat_set(s, "test:cle", "v1")
    assert f._etat_get(s, "test:cle") == "v1"
    f._etat_set(s, "test:cle", "v2")      # upsert idempotent
    assert f._etat_get(s, "test:cle") == "v2"


def _ensure_millesime_cols(s):
    # M32 : en prod, ensure_data_sources_millesime (boot) pose ces colonnes ; la table pré-existante
    # de la base de TEST ne les a pas (create_all saute les tables existantes) → on les pose ici.
    for col, typ in (("source_millesime", "varchar(64)"), ("source_horizon_at", "date"),
                     ("source_cadence", "varchar(32)"), ("prochain_millesime_at", "date")):
        s.execute(text(f"ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS {col} {typ}"))


@pytest.mark.db
def test_persist_millesime_dvf_horizon_calcule(db_session):
    """M32 Phase B §2 : persist_millesime écrit l'HORIZON amont (max date_mutation) + cadence +
    millésime dans data_sources, découpable par couche (only='dvf'). Horizon CALCULÉ, jamais figé."""
    s = db_session
    _ensure_millesime_cols(s)
    s.execute(text("INSERT INTO data_sources (name, category, status) VALUES "
                   "('DVF / valeurs foncières', 'marche', 'ok') ON CONFLICT (name) DO NOTHING"))
    s.execute(text("CREATE TABLE IF NOT EXISTS dvf_mutations_parcelle "
                   "(id_mutation text NOT NULL, date_mutation date, id_parcelle varchar(14), millesime smallint)"))
    s.execute(text("INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, id_parcelle, millesime) "
                   "VALUES ('m1','2025-12-31','97400000AA0001',2025),('m2','2024-06-01','97400000AA0002',2024)"))
    rendu = f.persist_millesime(s, only="dvf", commit=False)
    assert len(rendu) == 1 and rendu[0]["source"] == "dvf"
    row = s.execute(text("SELECT source_horizon_at, source_cadence, source_millesime, prochain_millesime_at "
                         "FROM data_sources WHERE name = 'DVF / valeurs foncières'")).one()
    assert str(row[0]) == "2025-12-31"          # horizon = max(date_mutation), calculé
    assert row[1] == "semestriel" and "géo-DVF" in row[2] and str(row[3]) == "2026-10-01"


@pytest.mark.db
def test_check_fraicheur_non_bloquant(db_session):
    """M32 Phase B §2 : la garde de fraîcheur AVERTIT mais ne bloque JAMAIS (retard source ≠ faute
    de bascule). Horizon très ancien → retard listé ; horizon récent → aucun retard. Zéro exception."""
    from labuse import bascule_gardes as bg
    from labuse.ingestion.fraicheur import DS_NAMES
    s = db_session
    _ensure_millesime_cols(s)
    # M-R : la garde parcourt l'UNIVERS des couches fraîcheur (fraicheur.SOURCES) — on donne à une
    # couche RÉELLE et bornable (dvf, semestriel) un horizon très ancien → retard listé, non bloquant.
    name = DS_NAMES["dvf"][0]
    s.execute(text("INSERT INTO data_sources (name, category, status, source_horizon_at) "
                   "VALUES (:n, 'x', 'ok', '2020-01-01') "
                   "ON CONFLICT (name) DO UPDATE SET source_horizon_at='2020-01-01'"), {"n": name})
    r = bg.check_fraicheur(session=s)             # session de test (rollback) ; ne lève jamais
    assert any(x["source"] == "dvf" for x in r["retards"])  # retard vu, non bloquant
    assert r["total"] == 10 and r["evaluees"] >= 1          # M-R : dénominateur honnête (N/total)


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


def test_plu_fraicheur_statuts():
    """M32 Phase B §2 : l'étiquette de fraîcheur du zonage (GPU-vs-mairie) expose le bon statut par
    commune, jamais silencieuse — à jour, opposabilité en attente (Saint-André), annulation partielle
    (Le Port), RNU (Saint-Philippe). Horizon = date d'approbation mairie. Lecture config, sans DB."""
    from labuse.api.app import _plu_fraicheur
    assert _plu_fraicheur("97411000AA0001")["statut"] == "a_jour"                  # Saint-Denis
    sa = _plu_fraicheur("97409000AA0001")                                          # Saint-André
    assert sa["statut"] == "opposabilite_en_attente" and sa["horizon"] == "2019-02-28"
    assert _plu_fraicheur("97407000AA0001")["statut"] == "annule_partiel"          # Le Port
    assert _plu_fraicheur("97417000AA0001")["statut"] == "rnu"                     # Saint-Philippe
    assert all(_plu_fraicheur(f"9740{c}000AA0001")["libelle"] for c in "1234")     # jamais vide
