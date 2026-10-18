#!/usr/bin/env python
"""CHASSE-ORFEVRE-1 · Angle D (le temps) — script REJOUABLE, LECTURE SEULE.

Que fait-il ?
  1. Fuseau de session PostgreSQL (forcé par db.py ?) vs fuseau par défaut du serveur.
  2. `now()` SQL vs horloge Python (UTC) — dérive éventuelle.
  3. Inventaire de TOUTES les colonnes temporelles (timestamptz / timestamp naïf / date / time)
     du schéma public → le point clé : reste-t-il des `timestamp without time zone` ?
  4. Échantillons de valeurs réelles sur les colonnes « événements connus » (job_runs,
     ops_incidents, mail_queue, parcel_residuel.computed_at, sessions, comptes…) :
     valeur servie (session Réunion) + la même AT TIME ZONE 'UTC' + âge — pour vérifier que
     l'instant stocké est plausible (piège documenté : computed_at « Réunion » écrit depuis
     un shell CEST).

Usage :
  PYTHONPATH=~/Desktop/labuse-orfevre/src ~/Desktop/labuse/.venv/bin/python \
      docs/audit-2026-10/chasse-orfevre-1/scripts/angle_d_temps.py

Aucune écriture : uniquement des SELECT / SHOW.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text


def _dsn() -> str:
    url = os.environ.get("LABUSE_DATABASE_URL")
    if url:
        return url
    env = Path(__file__).resolve().parents[4] / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("LABUSE_DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("LABUSE_DATABASE_URL introuvable (.env)")


def main() -> None:
    os.environ.setdefault("LABUSE_DATABASE_URL", _dsn())
    # le moteur APPLICATIF (db.py) → on observe exactement la session que l'app obtient
    from labuse.db import engine

    eng = engine()
    with eng.connect() as c:
        print("══ 1. Fuseaux ══")
        print("  session TimeZone (celle de l'app, forcée db.py) :",
              c.execute(text("SHOW timezone")).scalar())
        row = c.execute(text(
            "SELECT boot_val, reset_val, source FROM pg_settings WHERE name='TimeZone'")).one()
        print(f"  serveur TimeZone (défaut hors app)             : reset_val={row[1]} "
              f"(boot={row[0]}, source session={row[2]})")

        print("\n══ 2. now() SQL vs horloge Python ══")
        sql_now, sql_utc, cur_date = c.execute(text(
            "SELECT now(), now() AT TIME ZONE 'UTC', CURRENT_DATE")).one()
        py_utc = datetime.now(timezone.utc)
        print("  now() servi (session)      :", sql_now)
        print("  now() AT TIME ZONE 'UTC'   :", sql_utc)
        print("  Python now(timezone.utc)   :", py_utc)
        print("  dérive SQL-Python (s)      :", round((sql_now - py_utc).total_seconds(), 3))
        print("  CURRENT_DATE (session)     :", cur_date,
              "— doit être la date RÉUNION, pas celle du serveur CEST")

        print("\n══ 3. Inventaire des colonnes temporelles (schéma public) ══")
        rows = c.execute(text("""
            SELECT data_type, count(*) AS n
            FROM information_schema.columns
            WHERE table_schema='public'
              AND data_type IN ('timestamp with time zone','timestamp without time zone',
                                'date','time without time zone','time with time zone')
            GROUP BY 1 ORDER BY 2 DESC""")).all()
        for dt, n in rows:
            print(f"  {n:4d} colonnes  {dt}")
        naifs = c.execute(text("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND data_type='timestamp without time zone'
            ORDER BY 1,2""")).all()
        print(f"\n  → colonnes TIMESTAMP NAÏF (sans fuseau) : {len(naifs)}")
        for t, col in naifs:
            print(f"      {t}.{col}")

        print("\n══ 4. Échantillons de valeurs réelles (3 plus récentes) ══")
        cibles = [
            ("job_runs", "debut"), ("job_runs", "fin"),
            ("ops_incidents", "ouvert_at"), ("ops_incidents", "dernier_envoi_at"),
            ("mail_queue", "cree_at"), ("mail_queue", "parti_at"), ("mail_queue", "prevu_at"),
            ("parcel_residuel", "computed_at"), ("residuel_runs", "created_at"),
            ("sessions_auth", "created_at"), ("sessions_auth", "expire_at"),
            ("comptes", "essai_expire_at"), ("comptes", "created_at"),
            ("pipeline_entries", "created_at"), ("consultation_log", "ts"),
            ("usage_compteurs", "jour"), ("api_keys", "jour"),
            ("circuit_journal", "ts"), ("share_links", "created_at"),
            ("coherence_runs", "ts"), ("data_sources", "last_sync_at"),
            ("data_sources", "prochain_millesime_at"),
        ]
        for table, col in cibles:
            ok = c.execute(text(
                "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name=:t AND column_name=:c"), {"t": table, "c": col}).scalar()
            if not ok:
                print(f"  {table}.{col} : (colonne absente)")
                continue
            dtyp = c.execute(text(
                "SELECT data_type FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name=:t AND column_name=:c"), {"t": table, "c": col}).scalar()
            try:
                if dtyp == "date":
                    vals = c.execute(text(
                        f"SELECT {col}::text FROM {table} WHERE {col} IS NOT NULL "
                        f"ORDER BY {col} DESC LIMIT 3")).scalars().all()
                    print(f"  {table}.{col} [{dtyp}] : {vals}")
                else:
                    vals = c.execute(text(
                        f"SELECT {col}, ({col} AT TIME ZONE 'UTC')::text, "
                        f"round(extract(epoch FROM now() - {col})/3600, 1) "
                        f"FROM {table} WHERE {col} IS NOT NULL "
                        f"ORDER BY {col} DESC LIMIT 3")).all()
                    print(f"  {table}.{col} [{dtyp}] :")
                    for v, vu, age_h in vals:
                        print(f"      servi={v}  ·  UTC={vu}  ·  âge={age_h} h")
            except Exception as e:  # noqa: BLE001 — table vide/absente : on le dit, on continue
                print(f"  {table}.{col} : erreur {type(e).__name__}: {str(e)[:120]}")

        print("\n══ 5. Garde-fou cron : jobs hebdo/mensuels dont la conversion +4 h "
              "franchirait minuit ══")
        from labuse.jobs import JOBS
        risques = []
        for nom, j in JOBS.items():
            champs = j.cron_utc.split()
            h, dom, dow = champs[1], champs[2], champs[4]
            if h.isdigit() and int(h) >= 20 and (dom != "*" or dow != "*"):
                risques.append((nom, j.cron_utc, j.heure_reunion))
        if risques:
            print("  ⚠ ces jobs changeraient de JOUR à la conversion --tz reunion "
                  "(+4 mod 24 SANS décaler dom/dow) :")
            for r in risques:
                print("   ", r)
        else:
            print("  ✓ aucun job hebdo/mensuel avec heure UTC ≥ 20 h : la conversion "
                  "+4 mod 24 (cli._crontab_du_registre) est sûre AUJOURD'HUI — garde à rejouer "
                  "à chaque nouveau job.")


if __name__ == "__main__":
    main()
