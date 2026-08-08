"""M-O — ingestion : fraîcheur amont (P1-14), idempotence DVF (P2-55), rebuild non bloquant +
isolation des dérivés (P2-59/60), garde BAN (P2-61), connecteurs (P2-56/57/58)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion import fraicheur, layers_ingest, pc_caducs, defisc_fenetres, surface_d

pytestmark = pytest.mark.db


# ── P1-14 — persist_millesime : noms EXACTS + horizon NULL pour les couches sans date amont ──
def test_persist_millesime_provenance(db_session):
    s = db_session
    # (a) écriture par noms EXACTS — plus AUCUN pattern % (fin du fan-out `Géorisques%` → 5 lignes)
    for names in fraicheur.DS_NAMES.values():
        assert all("%" not in n for n in names)
    # (b) gpu_plu / georisques : date_sql = created_at (ingestion) → « horizon non amont » forcé NULL
    assert fraicheur.HORIZON_NON_AMONT == frozenset({"gpu_plu", "georisques"})
    assert len(fraicheur.DS_NAMES["georisques"]) == 5
    # (c) runtime (si le catalogue data_sources est seedé en base de test) : persist FORCE NULL sur
    # les lignes Géorisques même si on y pose une date sentinelle (= l'ancien bug : date d'ingestion).
    from datetime import date
    geo = fraicheur.DS_NAMES["georisques"]
    n_exist = s.execute(text("SELECT count(*) FROM data_sources WHERE name = ANY(:n)"), {"n": geo}).scalar()
    rendu = {r["source"]: r for r in fraicheur.persist_millesime(s, only="georisques", commit=False)}
    assert rendu["georisques"]["horizon"] is None      # jamais une date servie comme horizon amont
    if n_exist:
        s.execute(text("UPDATE data_sources SET source_horizon_at = :d WHERE name = ANY(:n)"),
                  {"d": date(2020, 1, 1), "n": geo})
        fraicheur.persist_millesime(s, only="georisques", commit=False)
        n_null = s.execute(text(
            "SELECT count(*) FROM data_sources WHERE source_horizon_at IS NULL AND name = ANY(:n)"),
            {"n": geo}).scalar()
        assert n_null == n_exist                        # les lignes ciblées repassent toutes à NULL


# ── P2-59 — rebuild par swap : idempotent, index canonique, aucune shadow résiduelle ──
def test_rebuild_swap_idempotent_index_canonique(db_session):
    from labuse.ingestion._rebuild import rebuild_swap
    s = db_session
    ddl = "CREATE TABLE IF NOT EXISTS _mo_swap_t (id int PRIMARY KEY, v text)"

    def _pop(target):
        s.execute(text(f'INSERT INTO "{target}" (id, v) VALUES (1, \'a\'), (2, \'b\')'))
        return {"n": 2}

    r1 = rebuild_swap(s, "_mo_swap_t", ddl, _pop, commit=False)
    r2 = rebuild_swap(s, "_mo_swap_t", ddl, _pop, commit=False)   # 2e run : pas de collision d'index
    assert r1 == r2 == {"n": 2}
    idx = [x[0] for x in s.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename = '_mo_swap_t'")).all()]
    assert idx == ["_mo_swap_t_pkey"]                 # renommé au swap (nom shadow libéré)
    assert s.execute(text("SELECT to_regclass('_mo_swap_t__rebuild')")).scalar() is None
    assert s.execute(text("SELECT count(*) FROM _mo_swap_t")).scalar() == 2
    s.execute(text("DROP TABLE IF EXISTS _mo_swap_t"))            # propreté (la TX rollback de toute façon)


# ── P2-55 — ingest_dvf idempotent (DELETE commune en tête) ──
def test_ingest_dvf_idempotent(db_session, monkeypatch):
    s = db_session
    insee, commune = "97499", "ZZ-Commune-Test-MO"
    s.execute(text("DELETE FROM dvf_mutations WHERE commune = :c"), {"c": commune})
    fake = [{"insee": insee, "mid": f"MUT{i}", "dt": "2024-03-01", "val": 250000.0,
             "tl": "Appartement", "sb": 60.0, "st": 0.0, "nat": "Vente",
             "lon": 55.3, "lat": -21.0, "vefa": False} for i in range(5)]
    monkeypatch.setattr(layers_ingest, "_GEO_DVF_CACHE", fake)
    n1 = layers_ingest.ingest_dvf(s, insee, commune, run_id=None, sids=[])
    n2 = layers_ingest.ingest_dvf(s, insee, commune, run_id=None, sids=[])   # rejeu SANS purge externe
    total = s.execute(text("SELECT count(*) FROM dvf_mutations WHERE commune = :c"), {"c": commune}).scalar()
    assert n1 == n2 == 5
    assert total == 5                                 # PAS 10 : la purge en tête garantit l'idempotence


# ── P2-60 — run_derives : un dérivé qui échoue est ISOLÉ, les précédents sont conservés ──
class _FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_run_derives_isole_les_echecs(monkeypatch):
    fs = _FakeSession()
    monkeypatch.setattr(pc_caducs, "build_pc_caducs", lambda s, **k: {"total": 1})

    def _boom(s, **k):
        raise RuntimeError("defisc casse")

    monkeypatch.setattr(defisc_fenetres, "build_defisc_fenetres", _boom)
    monkeypatch.setattr(surface_d, "build_events", lambda s, **k: {"total": 2})
    monkeypatch.setattr(fraicheur, "compteur_reveil_dpe",
                        lambda s: {"n": 0, "seuil": 200, "franchi": False})

    out = fraicheur.run_derives(fs, commit=True, log_fn=lambda *a: None)
    assert out["pc_caducs"] == {"total": 1}           # AVANT l'échec : conservé (committé)
    assert "erreur" in out["defisc_fenetres"] and "casse" in out["defisc_fenetres"]["erreur"]
    assert out["surface_d"] == {"total": 2}           # APRÈS l'échec : l'île continue
    assert fs.rollbacks >= 1                           # l'échec a bien été isolé


# ── P2-61 — ingest_ban : garde de plausibilité (CSV tronqué → refus, référentiel préservé) ──
def test_ingest_ban_garde_plausibilite(db_session, tmp_path):
    from labuse.ingestion.ban_adresses import DDL_ADRESSES, ingest_ban
    s = db_session
    for stmt in DDL_ADRESSES.strip().split(";"):
        if stmt.strip():
            s.execute(text(stmt))
    # référentiel « existant » abondant
    s.execute(text(
        "INSERT INTO adresses (id_ban, voie, commune, insee, geom) "
        "SELECT 'x'||g, 'Rue', 'C', '97499', ST_SetSRID(ST_MakePoint(55.3,-21.0),4326) "
        "FROM generate_series(1,200) g ON CONFLICT (id_ban) DO NOTHING"))
    header = ("id;id_fantoir;numero;rep;nom_voie;code_postal;code_insee;nom_commune;"
              "code_insee_ancienne_commune;nom_ancienne_commune;x;y;lon;lat;type_position;"
              "alias;nom_ld;libelle_acheminement;nom_afnor;source_position;source_nom_voie;"
              "certification_commune;cad_parcelles")
    rows = [header] + [f"a{i};;{i};;Rue Test;97400;97499;C;;;0;0;55.3;-21.0;entrance;;;;;;;;"
                       for i in range(3)]              # 3 << 80% de 200
    csv = tmp_path / "ban_tronque.csv"
    csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tronqué|suspect|REFUSÉE"):
        ingest_ban(s, csv)                             # garde par défaut → refus bruyant


# ── P2-56/57/58 — connecteurs ──
def test_connecteurs_les_7_branches():
    from labuse.connectors import REGISTRY
    from labuse.connectors.merimee import MerimeeConnector
    attendus = ["BODACC (procédures collectives)", "Cartofriches (Cerema)",
                "DPE ADEME (logements existants)", "INPI RNE (dirigeants)",
                "ABF / Monuments historiques", "QPV 2024 (ANCT)",
                "Recherche d'entreprises (DINUM)"]
    for name in attendus:
        assert name in REGISTRY, f"connecteur non branché : {name}"
    # le doublon générique « ABF » est remplacé par le vrai connecteur Mérimée
    assert isinstance(REGISTRY["ABF / Monuments historiques"], MerimeeConnector)


def test_client_suit_les_redirections():
    from labuse.connectors.base import Connector
    with Connector()._client() as c:
        assert c.follow_redirects is True


def test_qpv_timeout_explicite_et_resolution():
    from labuse.connectors.qpv import QpvConnector, DOWNLOAD_TIMEOUT_S
    q = QpvConnector()
    assert DOWNLOAD_TIMEOUT_S >= 60                    # gros zip : timeout explicite, pas le défaut
    assert hasattr(q, "_resolve_zip_url")             # URL résolue par l'API dataset (repli figé)
