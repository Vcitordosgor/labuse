"""FIX-ORFEVRE-1 · Point 2 — les trois gênants ACTIFS des journaux de prod (ANGLE-F G1/G2/G3 + E-04).

ORF-01 — mail-queue-consommer échouait chaque jour à 13:35 : `mailfile.ensure_tables` rejouait des DDL
  (ALTER CONSTRAINT, verrou ACCESS EXCLUSIVE) à CHAQUE run, bloquées par le pg_dump 13:30-13:48 ; le
  SIGALRM du runner laissait ensuite la connexion sale dans le pool (« another command is already in
  progress » en cascade, jusqu'à « journal/alerte impossible »).
ORF-02 — healthcheck aveugle : (a) `ops_alertes.signaler` passait par des DDL à chaque appel → l'alerte
  disque ne s'écrivait jamais pendant le backup (le moment où le seuil est franchi) et rien n'existait
  ailleurs ; (b) le job relisait son propre fichier d'état APRÈS que le runner l'avait écrasé
  (« en_cours », compteurs {}) → `echecs_consecutifs` toujours 0, alerte « 2 échecs » = code mort.
ORF-03 — pg-maintenance : `raw.autocommit = True` posé sur le PROXY de pool SQLAlchemy (attribut
  fantôme) → VACUUM refusé chaque dimanche, échec avalé, job vert.

Tous ces tests ÉCHOUENT sur le code d'avant (prouvé au mandat par git stash) et passent après.
Famille « unitaires sans base » (hook pre-push) sauf le VACUUM réel, marqué `local`.
"""
from __future__ import annotations

import json
import time
import types
import urllib.request
from contextlib import contextmanager

import pytest

from labuse import config, jobs, jobs_impl, mailfile, ops_alertes
from labuse import db as db_module
from labuse.jobs import JobContext


# ─────────────────────────── outillage : connexion/engine factices ───────────────────────────

class _Res:
    """Résultat SQLAlchemy minimal : scalar(), first(), mappings(), itération."""
    def __init__(self, scalar=None, first=None, rows=()):
        self._scalar, self._first, self._rows = scalar, first, list(rows)

    def scalar(self):
        return self._scalar

    def first(self):
        return self._first

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self._rows)


class _ConnMailQueueConforme:
    """Une connexion qui répond aux lectures de catalogue « tout est en place » et ENREGISTRE tout
    le SQL exécuté : la preuve qu'aucune DDL ne part quand le schéma est conforme."""
    def __init__(self, contrainte_connait_a_rejouer: bool = True):
        self.sqls: list[str] = []
        self._ok_contrainte = contrainte_connait_a_rejouer

    def execute(self, stmt, params=None):
        sql = " ".join(str(stmt).split())
        self.sqls.append(sql)
        if "to_regclass('mail_queue')" in sql:
            return _Res(scalar="mail_queue")
        if "information_schema.columns" in sql:
            return _Res(first=(1,))
        if "pg_indexes" in sql:
            return _Res(rows=[("ix_mail_queue_etat_cree",), ("ix_mail_queue_compte",),
                              ("ix_mail_queue_dedup",)])
        if "pg_get_constraintdef" in sql:
            etats = mailfile.ETATS if self._ok_contrainte else ("en_attente", "parti", "recu",
                                                               "echec", "annule")
            return _Res(scalar="CHECK (etat IN (" + ",".join(f"'{e}'" for e in etats) + "))")
        return _Res()


class _FauxEngine:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def begin(self):
        yield self._conn


def _ddl(sqls: list[str]) -> list[str]:
    return [s for s in sqls if s.upper().startswith(("ALTER", "CREATE", "DROP"))]


# ═══════════════════════════ ORF-01 (a) — ensure_tables sans DDL en régime établi ═══════════════════════════

def test_orf01_ensure_tables_aucune_ddl_quand_schema_conforme():
    """G1 racine : le worker (toutes les 5 min) ne doit tenter AUCUNE DDL quand mail_queue est déjà
    conforme — sinon l'ALTER CONSTRAINT (ACCESS EXCLUSIVE) se fait bloquer par le pg_dump quotidien."""
    conn = _ConnMailQueueConforme()
    mailfile.ensure_tables(_FauxEngine(conn))
    assert conn.sqls, "la vérification lecture seule doit avoir eu lieu"
    assert _ddl(conn.sqls) == [], f"DDL rejouée sur schéma conforme : {_ddl(conn.sqls)}"


def test_orf01_ensure_tables_repare_une_contrainte_perimee():
    """Garde-fou inverse : si la contrainte CHECK ne connaît pas `a_rejouer`, la réparation (DROP/ADD)
    doit encore partir — l'ensure reste un vrai ensure, il n'est juste plus systématique."""
    conn = _ConnMailQueueConforme(contrainte_connait_a_rejouer=False)
    mailfile.ensure_tables(_FauxEngine(conn))
    assert any("ADD CONSTRAINT mail_queue_etat_check" in s for s in conn.sqls)


# ═══════════════════════════ ORF-01 (b) — timeout : la connexion sale ne ressert jamais ═══════════════════════════

@pytest.fixture
def etat_jobs_tmp(monkeypatch, tmp_path):
    """Répertoire d'état des jobs isolé (le runner écrit <nom>.json ; le repli d'alerte y va aussi)."""
    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path))
    config.get_settings.cache_clear()
    yield tmp_path
    config.get_settings.cache_clear()


def test_orf01_timeout_purge_le_pool_de_connexions(monkeypatch, etat_jobs_tmp):
    """Quand l'alarme du runner sonne (SIGALRM en plein travail), la connexion interrompue est
    potentiellement sale (« another command is already in progress ») : le runner doit jeter le pool
    AVANT la trace/alerte, pour que rien de sale ne ressorte. Avant le fix : aucune purge — la
    connexion sale repartait dans le pool (cascade vue en prod les 14-18/10 à 13:35)."""
    disposes: list[int] = []
    monkeypatch.setattr(db_module, "_engine",
                        types.SimpleNamespace(dispose=lambda: disposes.append(1)))
    monkeypatch.setattr(jobs, "_journaliser_et_alerter", lambda *a, **k: None)
    monkeypatch.setattr(jobs, "_ping_temoin", lambda *a, **k: None)

    def _dort(ctx):
        time.sleep(5)   # > timeout_s : l'alarme sonne pendant le sleep

    monkeypatch.setitem(jobs.JOBS, "orf01-test", jobs.Job(
        nom="orf01-test", titre="test timeout", cadence="test", cron_utc="* * * * *",
        heure_reunion="", fn=_dort, timeout_s=1, besoin_db=False))
    rc = jobs.exec_one("orf01-test")
    etat = json.loads((etat_jobs_tmp / "orf01-test.json").read_text(encoding="utf-8"))
    assert rc == 1 and etat["statut"] == "timeout"
    assert disposes, "le pool n'a pas été purgé après le timeout — la connexion sale resservirait"


# ═══════════════════════════ ORF-02 (a) — l'alerte n'a plus de DDL, et existe QUELQUE PART ═══════════════════════════

class _DbOpsConforme:
    """Session factice : ops_incidents existe déjà ; enregistre tout le SQL de `signaler()`."""
    def __init__(self):
        self.sqls: list[str] = []

    def execute(self, stmt, params=None):
        sql = " ".join(str(stmt).split())
        self.sqls.append(sql)
        if "to_regclass('ops_incidents')" in sql:
            return _Res(scalar=True)
        if sql.startswith("SELECT id, dernier_envoi_at"):
            return _Res(first=None)        # pas d'incident ouvert → INSERT + envoi
        return _Res()


def test_orf02_signaler_ne_contient_aucune_ddl(monkeypatch):
    """G2 racine (a) : le chemin d'alerte (`signaler`) ne doit plus passer par CREATE TABLE/INDEX à
    chaque appel — c'est exactement ce qui bloquait l'alerte disque pendant le pg_dump."""
    monkeypatch.setattr(ops_alertes, "_sink", lambda *a, **k: "ok")   # pas de mail/cloche ici
    db = _DbOpsConforme()
    assert ops_alertes.signaler(db, "disque", "Disque à 99%", "test") == "ouvert"
    assert _ddl(db.sqls) == [], f"DDL sur le chemin d'alerte : {_ddl(db.sqls)}"


def _urlopen_ko(*a, **k):
    raise OSError("connexion refusée (service HS)")


def test_orf02_repli_local_quand_la_base_est_indisponible(monkeypatch, etat_jobs_tmp):
    """G2 : disque au-dessus du seuil PENDANT que la base est inécrivable (fenêtre pg_dump) — l'alerte
    doit exister QUELQUE PART : fichier de repli local + journald. Avant le fix : un simple log.error
    générique, l'alerte disque n'existait nulle part."""
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ko)
    du = types.SimpleNamespace(total=100, used=99, free=1)            # 99 % ≥ seuil (85)
    monkeypatch.setattr(jobs_impl.shutil, "disk_usage", lambda p: du)

    def _scope_ko():
        raise RuntimeError("base verrouillée (pg_dump en cours)")

    monkeypatch.setattr(db_module, "session_scope", _scope_ko)
    jobs_impl.healthcheck(JobContext(db=None, dry_run=True))          # 1er échec /health : ne lève pas
    repli = etat_jobs_tmp / ops_alertes.FICHIER_REPLI
    assert repli.exists(), "aucun repli local : l'alerte disque n'existe nulle part"
    contenu = repli.read_text(encoding="utf-8")
    assert '"disque"' in contenu and "99" in contenu and '"readyz"' in contenu


# ═══════════════════════════ ORF-02 (b) — 2 échecs consécutifs → le job lève, le témoin passe rouge ═══════════════════════════

def test_orf02_healthcheck_2_echecs_consecutifs_alerte(monkeypatch, etat_jobs_tmp):
    """E-04 : /health HS deux passages de suite → le 2ᵉ passage DOIT lever (incident job-echec ouvert
    par le runner, ping témoin /fail). Avant le fix : le job relisait l'état « en_cours, compteurs {} »
    que le runner venait d'écrire → echecs toujours ≤ 1, jamais d'alerte, témoin toujours vert."""
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ko)       # /health ET /readyz injoignables
    du = types.SimpleNamespace(total=100, used=10, free=90)           # disque sain : pas de bruit
    monkeypatch.setattr(jobs_impl.shutil, "disk_usage", lambda p: du)

    def _scope_ko():
        raise RuntimeError("pas de base dans ce test")

    monkeypatch.setattr(db_module, "session_scope", _scope_ko)
    monkeypatch.setattr(jobs, "_journaliser_et_alerter", lambda *a, **k: None)
    pings: list[bool] = []
    monkeypatch.setattr(jobs, "_ping_temoin", lambda nom, ok: pings.append(ok))

    rc1 = jobs.exec_one("healthcheck")                                # 1er échec : amorti (anti faux positif)
    rc2 = jobs.exec_one("healthcheck")                                # 2ᵉ échec consécutif : ALERTE
    etat = json.loads((etat_jobs_tmp / "healthcheck.json").read_text(encoding="utf-8"))
    assert rc1 == 0 and etat["compteurs"]["echecs_consecutifs"] >= 2
    assert rc2 == 1 and etat["statut"] == "echec" and "échec(s) consécutif(s)" in (etat["erreur"] or "")
    assert pings == [True, False], "le ping témoin doit passer ROUGE au 2ᵉ échec consécutif"


# ═══════════════════════════ ORF-03 — VACUUM réel (autocommit psycopg) + échec non avalé ═══════════════════════════

class _FauxCurseurPg:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def close(self):
        pass

    def execute(self, sql):
        self._conn.executes.append((sql, self._conn.autocommit))
        if not self._conn.autocommit:
            # le comportement réel de PostgreSQL quand l'autocommit n'est PAS posé sur psycopg
            raise Exception("VACUUM cannot run inside a transaction block")
        if "table_absente" in sql:
            from psycopg.errors import UndefinedTable
            raise UndefinedTable("relation n'existe pas")
        if "qui_casse" in sql:
            raise Exception("could not resize shared memory (disque plein)")


class _FauxPsycopg:
    """La « vraie » connexion DBAPI : c'est ELLE qui doit recevoir autocommit=True."""
    def __init__(self):
        self.autocommit = False
        self.executes: list[tuple[str, bool]] = []

    def cursor(self):
        return _FauxCurseurPg(self)


class _FauxProxyPool:
    """Le proxy de pool SQLAlchemy : accepter un attribut `autocommit` fantôme (comme le vrai
    PoolProxiedConnection) sans le propager à la connexion psycopg — le piège du code d'avant."""
    def __init__(self):
        self.driver_connection = _FauxPsycopg()

    def cursor(self):
        return self.driver_connection.cursor()

    def close(self):
        pass


def _engine_factice(monkeypatch, proxy):
    monkeypatch.setattr(db_module, "engine",
                        lambda: types.SimpleNamespace(raw_connection=lambda: proxy))


def test_orf03_vacuum_pose_autocommit_sur_la_connexion_psycopg(monkeypatch):
    """G3 racine : l'autocommit doit être posé sur la connexion psycopg réelle (driver_connection,
    même porte que scoring/score_v.py) — sinon chaque VACUUM répond « cannot run inside a transaction
    block » et le job restait vert. Et la connexion doit retourner PROPRE au pool (autocommit remis)."""
    proxy = _FauxProxyPool()
    _engine_factice(monkeypatch, proxy)
    monkeypatch.setattr(jobs_impl, "TABLES_CHAUDES", ["t_une", "t_deux"], raising=False)
    ctx = JobContext(db=None, dry_run=True)
    jobs_impl.pg_maintenance(ctx)
    assert ctx.compteurs["tables"] == ["t_une", "t_deux"]
    assert all(autocommit for _, autocommit in proxy.driver_connection.executes)
    assert proxy.driver_connection.autocommit is False, "autocommit non restauré avant retour au pool"


def test_orf03_un_echec_de_vacuum_fait_le_job_rouge(monkeypatch):
    """G3 : un VACUUM qui casse (autre chose qu'une table absente) ne doit PLUS être avalé — le job
    doit être ROUGE. Avant le fix : except générique par table → `fin (code 0)` mensonger."""
    proxy = _FauxProxyPool()
    _engine_factice(monkeypatch, proxy)
    monkeypatch.setattr(jobs_impl, "TABLES_CHAUDES", ["t_une", "t_qui_casse"], raising=False)
    with pytest.raises(Exception, match="disque plein"):
        jobs_impl.pg_maintenance(JobContext(db=None, dry_run=True))


def test_orf03_table_absente_toleree_mais_jamais_vert_par_vacuite(monkeypatch):
    """Une table absente reste tolérée (poste de dev) — mais ZÉRO table vacuumée = job rouge, jamais
    un vert par vacuité."""
    proxy = _FauxProxyPool()
    _engine_factice(monkeypatch, proxy)
    monkeypatch.setattr(jobs_impl, "TABLES_CHAUDES", ["table_absente"], raising=False)
    ctx = JobContext(db=None, dry_run=True)
    with pytest.raises(RuntimeError, match="AUCUNE table"):
        jobs_impl.pg_maintenance(ctx)
    assert ctx.compteurs["absentes"] == ["table_absente"]


@pytest.mark.local
def test_orf03_vacuum_reel_sur_la_base_locale(monkeypatch):
    """Preuve de bout en bout sur la base locale : un VACUUM ANALYZE réel passe (plus de « cannot run
    inside a transaction block ») et une table absente est comptée sans casser."""
    from sqlalchemy import text
    eng = db_module.engine()
    with eng.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS orfevre3_vacuum_test (id int)"))
    try:
        monkeypatch.setattr(jobs_impl, "TABLES_CHAUDES",
                            ["orfevre3_vacuum_test", "orfevre3_table_inexistante"])
        ctx = JobContext(db=None, dry_run=True)
        jobs_impl.pg_maintenance(ctx)
        assert ctx.compteurs["tables"] == ["orfevre3_vacuum_test"]
        assert ctx.compteurs["absentes"] == ["orfevre3_table_inexistante"]
    finally:
        with eng.begin() as c:
            c.execute(text("DROP TABLE IF EXISTS orfevre3_vacuum_test"))
