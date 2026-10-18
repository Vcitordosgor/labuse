#!/usr/bin/env python
"""CHASSE-ORFEVRE-1 · Angle E — état réel des JOBS et des FILES (lecture seule, rejouable).

Joue une série de SELECT (aucune écriture, aucun job lancé) et imprime :
  1. mail_queue        — compte par état, âge de la plus vieille ligne non traitée, lignes DUES
                         (en_attente/a_rejouer échues) qu'un worker réel enverrait, orphelins compte ;
  2. job_runs          — volume, derniers passages, statuts non terminaux ;
  3. fichiers d'état   — <jobs_state_dir>/*.json : statut figé « en_cours » (kill au milieu) ;
  4. ops_incidents     — incidents ouverts et leur âge ;
  5. ingestion_runs    — compte par statut, lignes « running » anciennes (coincées) ;
  6. courrier          — demandes par statut (+ âge de la plus vieille « demande »), envois par statut ;
  7. event_log         — volume 7 j par kind, doublons de clé dedup le même jour (course possible) ;
  8. stripe_events     — dédup webhook (volume, dernier reçu) ;
  9. source_veille     — sondes en échec consécutif, lignes jamais repassées depuis > 7 j ;
 10. pige_biens        — statuts du cycle Radar (états sans consommateur ?).

Usage :
  PYTHONPATH=~/Desktop/labuse-orfevre/src ~/Desktop/labuse/.venv/bin/python \
      docs/audit-2026-10/chasse-orfevre-1/scripts/angle_e_jobs.py
Le DSN vient de LABUSE_DATABASE_URL (.env du worktree, chargé si présent).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]   # scripts → chasse-orfevre-1 → audit-2026-10 → docs → racine
# .env du worktree : LABUSE_DATABASE_URL (sans écraser un env déjà posé)
env = RACINE / ".env"
if env.is_file():
    for ligne in env.read_text().splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            k, _, v = ligne.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

DSN = os.environ.get("LABUSE_DATABASE_URL")
if not DSN:
    sys.exit("LABUSE_DATABASE_URL absent (.env)")

from sqlalchemy import create_engine, text  # noqa: E402

eng = create_engine(DSN, pool_pre_ping=True)


def q(c, sql, **p):
    try:
        return c.execute(text(sql), p).all()
    except Exception as e:  # noqa: BLE001 — table absente = dit, jamais un crash
        c.rollback()
        return [("(erreur : " + str(e).splitlines()[0][:120] + ")",)]


def titre(t):
    print(f"\n{'─' * 78}\n{t}\n{'─' * 78}")


with eng.connect() as c:
    titre("1. mail_queue — par état + âge")
    for r in q(c, "SELECT etat, count(*), min(cree_at)::date, max(cree_at)::date "
                  "FROM mail_queue GROUP BY etat ORDER BY etat"):
        print(f"  {r[0]:<12} n={r[1]:<5} de {r[2]} à {r[3]}")
    print("  DUES maintenant (qu'un worker RÉEL enverrait) :")
    for r in q(c, "SELECT id, etat, mail_key, compte_id, destinataire, tentatives, "
                  "  round(extract(epoch FROM now()-cree_at)/86400,1) AS age_j, prevu_at "
                  "FROM mail_queue WHERE etat IN ('en_attente','a_rejouer') "
                  "AND (prevu_at IS NULL OR prevu_at <= now()) ORDER BY id"):
        print(f"    #{r[0]} {r[1]} {r[2]} compte={r[3]} to={r[4]} tent={r[5]} age={r[6]}j")
    for r in q(c, "SELECT count(*) FROM mail_queue m WHERE m.compte_id IS NOT NULL "
                  "AND NOT EXISTS (SELECT 1 FROM comptes k WHERE k.id = m.compte_id)"):
        print(f"  orphelins (compte supprimé) : {r[0]}")

    titre("2. job_runs — historique durable")
    for r in q(c, "SELECT count(*), min(debut), max(debut) FROM job_runs"):
        print(f"  total={r[0]} de {r[1]} à {r[2]}")
    for r in q(c, "SELECT nom, statut, debut, duree_s, erreur FROM job_runs "
                  "ORDER BY debut DESC LIMIT 15"):
        print(f"  {str(r[2])[:16]} {r[0]:<24} {r[1]:<8} {r[3]}s {str(r[4] or '')[:60]}")
    for r in q(c, "SELECT count(*) FROM job_runs WHERE statut NOT IN "
                  "('ok','dry-run','echec','timeout')"):
        print(f"  statuts NON terminaux (en_cours figé ?) : {r[0]}")

    titre("3. fichiers d'état jobs (*.json) — « en_cours » figé")
    try:
        sys.path.insert(0, str(RACINE / "src"))
        from labuse.config import get_settings
        d = Path(get_settings().jobs_state_dir)
        if d.is_dir():
            import json
            for f in sorted(d.glob("*.json")):
                e = json.loads(f.read_text())
                marque = "  ⚠ EN_COURS FIGÉ" if e.get("statut") == "en_cours" else ""
                print(f"  {f.stem:<24} {e.get('statut', '?'):<8} fin={str(e.get('fin'))[:16]}{marque}")
        else:
            print(f"  (dossier d'état absent : {d})")
    except Exception as e:  # noqa: BLE001
        print(f"  (états illisibles : {e})")

    titre("4. ops_incidents — ouverts")
    for r in q(c, "SELECT cle, sujet, ouvert_at::date, rappels FROM ops_incidents "
                  "WHERE resolu_at IS NULL ORDER BY ouvert_at"):
        print(f"  [{r[0]}] {str(r[1])[:50]} depuis {r[2]} ({r[3]} rappels)")
    for r in q(c, "SELECT count(*) FROM ops_incidents WHERE resolu_at IS NULL"):
        print(f"  total ouverts : {r[0]}")

    titre("5. ingestion_runs — par statut + running anciens")
    for r in q(c, "SELECT COALESCE(status,'NULL'), count(*), max(started_at)::date "
                  "FROM ingestion_runs GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {r[0]:<12} n={r[1]:<6} dernier={r[2]}")
    for r in q(c, "SELECT id, commune, started_at FROM ingestion_runs "
                  "WHERE status IN ('running','en_cours','started') "
                  "AND started_at < now() - interval '1 day' ORDER BY started_at DESC LIMIT 10"):
        print(f"  ⚠ coincé running : #{r[0]} {r[1]} depuis {r[2]}")

    titre("6. courrier — demandes et envois")
    for r in q(c, "SELECT statut, count(*) FROM courrier_demandes WHERE corps IS NOT NULL "
                  "GROUP BY statut ORDER BY 2 DESC"):
        print(f"  demande   {r[0]:<16} n={r[1]}")
    for r in q(c, "SELECT min(ts)::date, count(*) FROM courrier_demandes "
                  "WHERE corps IS NOT NULL AND statut IN ('demande','tarif_confirme')"):
        print(f"  « à déposer » : {r[1]} (plus vieille {r[0]})")
    for r in q(c, "SELECT statut, count(*) FROM courrier_envois GROUP BY statut"):
        print(f"  envoi     {r[0]:<16} n={r[1]}")

    titre("7. event_log — 7 jours par kind + doublons dedup/jour")
    for r in q(c, "SELECT kind, count(*) FROM event_log WHERE ts >= now() - interval '7 days' "
                  "GROUP BY kind ORDER BY 2 DESC LIMIT 12"):
        print(f"  {r[0]:<22} n={r[1]}")
    for r in q(c, "SELECT dedup, compte_id, ts::date, count(*) FROM event_log "
                  "WHERE dedup IS NOT NULL GROUP BY 1,2,3 HAVING count(*) > 1 "
                  "ORDER BY 4 DESC LIMIT 8"):
        print(f"  ⚠ dedup doublé : {r[0]} compte={r[1]} {r[2]} ×{r[3]}")

    titre("8. stripe_events — dédup webhook")
    for r in q(c, "SELECT count(*), max(recu_at) FROM stripe_events"):
        print(f"  events dédupliqués : {r[0]} (dernier {r[1]})")

    titre("9. source_veille — sondes en échec / jamais repassées")
    for r in q(c, "SELECT count(*) FILTER (WHERE echecs_consecutifs >= 3), "
                  "count(*) FILTER (WHERE actif AND dernier_passage_at < now() - interval '7 days'), "
                  "count(*) FILTER (WHERE actif AND dernier_passage_at IS NULL), count(*) "
                  "FROM source_veille"):
        print(f"  ≥3 échecs consécutifs={r[0]} · actives sans passage depuis 7 j={r[1]} "
              f"· jamais passées={r[2]} · total={r[3]}")

    titre("10. pige_biens — statuts du cycle Radar")
    for r in q(c, "SELECT statut, count(*) FROM pige_biens GROUP BY statut ORDER BY 2 DESC"):
        print(f"  {r[0]:<20} n={r[1]}")

print("\n(fin — aucune écriture)")
