"""BOOT-VERROU-1 — le boot de l'API ne prend AUCUN verrou de table quand le schéma est posé.

Étend le test de LIENS-1 lot 0 (`test_boot_sans_verrou.py`, ensure_runs_schema) aux DDL de boot
RESTANTS qui touchaient une table CHAUDE sans tester le catalogue d'abord. Incident reproduit : le
06/10, un `ALTER TABLE parcel_zone_plu ADD COLUMN IF NOT EXISTS zone_filtre` *no-op* prenait quand
même un ACCESS EXCLUSIVE, se mettait en FILE derrière un lecteur et gelait tout le démarrage.

Deux familles de verrous, deux bloqueurs :
  • ADD COLUMN / ALTER TYPE / DROP CONSTRAINT → ACCESS EXCLUSIVE : entre en conflit avec un LECTEUR
    (ACCESS SHARE). Le bloqueur `lecteur` tient donc un ACCESS SHARE sur chaque table chaude.
  • CREATE INDEX (non concurrent) → SHARE : n'entre PAS en conflit avec un lecteur, mais AVEC un
    ÉCRIVAIN (ROW EXCLUSIVE — ex. un run de cascade en cours). Le bloqueur `ecrivain` tient donc un
    ROW EXCLUSIVE sur les tables où le boot crée un index.

Schéma posé (fixture) → chaque `ensure_*` doit n'émettre AUCUN DDL (tout existe déjà) → ne jamais se
mettre en file → finir vite. Le `lock_timeout` court transforme une RÉGRESSION (un DDL redevenu non
gardé) en ÉCHEC RAPIDE : le DDL buterait sur le verrou tenu et lèverait au lieu de geler 8 min.

`test_les_gardes_mordent` prouve que le filet fonctionne : les DDL NON gardés d'origine, rejoués sous
les mêmes verrous, lèvent bien — donc si une garde saute, le test au-dessus tombera.
"""
from __future__ import annotations

import time

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from labuse import comptes as comptes_mod
from labuse import models
from labuse.api import dashboard, projets, recherche, tenant

# Tables LUES en continu par l'app → un ADD COLUMN no-op (ACCESS EXCLUSIVE) s'y met en file.
_TABLES_LECTEUR = ("parcel_zone_plu", "data_sources", "parcels", "pipeline_entries",
                   "comptes", "sessions_auth", "adresses", "ia_log", "dryrun_cascade_results",
                   "watch_zones", "alertes")
# Tables où le boot CRÉE un index → un CREATE INDEX no-op (SHARE) se met en file derrière un écrivain.
_TABLES_ECRIVAIN = ("parcels", "adresses", "dryrun_cascade_results", "pipeline_entries", "ia_log")


def _boot_engine(engine):
    """Engine jumeau (même base de test) avec un `lock_timeout` court armé sur chaque connexion :
    un DDL non gardé bute vite au lieu de geler le test (et la prod)."""
    return create_engine(str(engine.url), connect_args={"options": "-c lock_timeout=4000"})


def _dsn(engine) -> str:
    """DSN libpq (psycopg) vers la MÊME base de test — pour tenir des verrous HORS du pool SQLAlchemy
    de l'app (sinon on épuise le QueuePool en ouvrant 16 bloqueurs)."""
    u = engine.url
    return f"postgresql://{u.username}@{u.host}:{u.port or 5432}/{u.database}"


def _tenir_verrou(dsn: str, table: str, mode: str):
    """Ouvre une connexion psycopg, tient `mode` sur `table` dans une transaction ouverte. À fermer."""
    conn = psycopg.connect(dsn)
    cur = conn.cursor()
    cur.execute("BEGIN")
    cur.execute(f"LOCK TABLE {table} IN {mode} MODE")
    return conn


def _executer_tous_les_ensure_de_boot(boot):
    """Rejoue, sur le `boot` engine, TOUS les `ensure_*` corrigés par BOOT-VERROU-1."""
    models.ensure_zone_filtre(boot)
    models.ensure_data_sources_millesime(boot)
    models.ensure_promesses_index(boot)
    models.ensure_flags_probe_index(boot)
    models.ensure_pipeline_projet(boot)
    models.ensure_pipeline_prospection(boot)
    models.ensure_pipeline_archived(boot)
    models.ensure_contact_etiquette(boot)
    models.ensure_watch_zones(boot)
    recherche.ensure_index(boot)
    dashboard.ensure_tables(boot)
    projets.ensure_tables(boot)
    Session = sessionmaker(bind=boot)
    with Session() as s:
        comptes_mod.ensure_tables(s)
        s.commit()
    with Session() as s:
        tenant.ensure_scoping(s)


def test_boot_sans_verrou_sur_tables_chaudes(engine):
    # Pré-requis : matérialiser les objets que la fixture ne pose pas encore (index de recherche,
    # ia_log + colonnes comptes de dashboard) pour TESTER LE CHEMIN NOMINAL (tout présent).
    recherche.ensure_index(engine)
    dashboard.ensure_tables(engine)

    with engine.connect() as c:
        # Le chemin nominal n'a de sens que si les objets existent VRAIMENT (sinon on testerait la
        # première pose, pas le no-op).
        assert c.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='parcel_zone_plu'"
                              " AND column_name='zone_filtre'")).scalar(), "pré-requis zone_filtre"
        assert c.execute(text("SELECT to_regclass('ix_parcels_section_numero')")).scalar(), "pré-requis index recherche"
        assert c.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='comptes'"
                              " AND column_name='copilote_quota_jour'")).scalar(), "pré-requis colonne comptes (dashboard)"

    boot = _boot_engine(engine)
    dsn = _dsn(engine)
    bloqueurs = []
    try:
        for tbl in _TABLES_LECTEUR:               # lecteurs : ACCESS SHARE (reproduit l'incident ALTER)
            bloqueurs.append(_tenir_verrou(dsn, tbl, "ACCESS SHARE"))
        for tbl in _TABLES_ECRIVAIN:              # écrivains : ROW EXCLUSIVE (met en file les CREATE INDEX)
            bloqueurs.append(_tenir_verrou(dsn, tbl, "ROW EXCLUSIVE"))

        t0 = time.perf_counter()
        _executer_tous_les_ensure_de_boot(boot)   # chemin nominal → zéro DDL → zéro attente
        dt = time.perf_counter() - t0
        assert dt < 10, (
            f"le boot a mis {dt:.1f}s avec des verrous tenus sur les tables chaudes → un DDL non "
            "gardé s'est remis en file (régression du correctif BOOT-VERROU-1).")
    finally:
        for b in bloqueurs:
            b.rollback()
            b.close()
        boot.dispose()


def test_les_gardes_mordent(engine):
    """Preuve que le test MORD : les DDL NON gardés d'origine, rejoués sous les mêmes verrous que
    ci-dessus, lèvent bien (lock_timeout). Si une garde disparaissait, le test nominal basculerait
    donc en échec."""
    boot = _boot_engine(engine)
    try:
        # (1) ALTER ADD COLUMN no-op sous un LECTEUR (ACCESS SHARE) → ACCESS EXCLUSIVE en file → lève.
        lecteur = engine.connect()
        lecteur.execute(text("LOCK TABLE parcel_zone_plu IN ACCESS SHARE MODE"))
        try:
            with pytest.raises(OperationalError):
                with boot.begin() as c:
                    c.execute(text("ALTER TABLE parcel_zone_plu ADD COLUMN IF NOT EXISTS zone_filtre varchar"))
        finally:
            lecteur.rollback()
            lecteur.close()

        # (2) CREATE INDEX no-op sous un ÉCRIVAIN (ROW EXCLUSIVE) → SHARE en file → lève.
        ecrivain = engine.connect()
        ecrivain.execute(text("LOCK TABLE dryrun_cascade_results IN ROW EXCLUSIVE MODE"))
        try:
            with pytest.raises(OperationalError):
                with boot.begin() as c:
                    c.execute(text("CREATE INDEX IF NOT EXISTS ix_dryrun_cascade_bati_exclude "
                                   "ON dryrun_cascade_results (run_label, parcel_id) "
                                   "WHERE layer_name = 'bati' AND result = 'HARD_EXCLUDE'"))
        finally:
            ecrivain.rollback()
            ecrivain.close()
    finally:
        boot.dispose()
