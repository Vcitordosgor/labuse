#!/usr/bin/env python3
"""CIRCUIT-0 Lot 3 — les horloges. Lecture seule.

Produit :
  · docs/CIRCUIT/inventaire/jobs.csv — une ligne par job du wrapper (registre
    src/labuse/jobs.py:263-318, 19 jobs) + une ligne par cron encore posé HORS wrapper
    (deploy/cron.d/*, 13 lignes actives) ;
  · docs/CIRCUIT/inventaire/source_veille.csv — dump complet de la table (Q3.1).

CONVENTIONS D'HEURES (constatées) : deploy/cron.d-labuse est écrit en UTC (heure Réunion
en commentaire) ; deploy/cron.d/* a été converti en heure RÉUNION avant la pose
(docs/audit-2026-08/VPS/JOURNAL.md:139-140). `dernier_statut` : l'état JSON du wrapper
(.local/state/jobs/<nom>.json — src/labuse/jobs.py:62) n'existe pas en local → DOUTE.
"""
from __future__ import annotations

import csv
import subprocess
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_JOBS = REPO / "docs/CIRCUIT/inventaire/jobs.csv"
OUT_SV = REPO / "docs/CIRCUIT/inventaire/source_veille.csv"

HEADER = ["id", "horaire_utc", "horaire_reunion", "fait_vraiment", "touche_l_eau",
          "dernier_statut", "trace_base_coherente", "preuve"]

DOUTE_ETAT = "DOUTE — état JSON du wrapper absent en local (VPS seulement, jobs.py:62)"

#: les 19 jobs du registre (jobs.py:263-318). posé = présent dans deploy/cron.d-labuse (16/19).
WRAPPER = [
 ("backup-postgres", "45 1 * * *", "05:45", "dump PostgreSQL + rotation", "non",
  "non (log fichier seul)", "jobs.py:265-266 ; deploy/cron.d-labuse"),
 ("sources-fraicheur", "0 2 * * *", "06:00",
  "recalcule fraicheur_statut des sources (a_jour/en_retard/en_panne) dans data_sources", "oui",
  "oui (data_sources.fraicheur_* — jobs_impl.py:67-131)", "jobs.py:267-268"),
 ("radar-cycle", "30 2 * * *", "06:30",
  "traite les dépôts Radar de la veille : parse, rattache, événements, badges", "oui",
  "oui (pige_biens/pige_faits)", "jobs.py:269-270"),
 ("radar-digests", "0 14 * * *", "18:00", "digests + alertes de veille, un mail par client (Brevo)", "non",
  "oui (dédup event_log)", "jobs.py:271-272"),
 ("fiche-commune-cache", "0 23 * * *", "03:00", "précalcule le contexte des fiches communes", "oui",
  "oui (commune_contexte_cache)", "jobs.py:273-274"),
 ("copilote-purge", "30 23 * * *", "03:30 — NON POSÉ (absent de cron.d-labuse)",
  "purge conversations Copilote au-delà de la rétention", "non",
  "oui (suppression en base)", "jobs.py:276-277 ; absent de deploy/cron.d-labuse"),
 ("healthcheck", "*/15 * * * *", "toutes les 15 min", "sonde /health locale + espace disque", "non",
  "non (fichier)", "jobs.py:278-279"),
 ("sante-endpoints", "7,37 * * * *", "toutes les 30 min — NON POSÉ",
  "sonde endpoints métier avec DB (accueil/sources/fiche/radar/projets/ask)", "non",
  "oui (notification à la panne)", "jobs.py:282-284 ; absent de deploy/cron.d-labuse"),
 ("pg-maintenance", "0 0 * * 0", "04:00 dim", "VACUUM ANALYZE des tables chaudes", "non",
  "non", "jobs.py:286-287"),
 ("rapport-admin", "15 2 * * 1", "06:15 lun", "rapport hebdomadaire d'exploitation (mail)", "non",
  "non (mail)", "jobs.py:288-289"),
 ("ingest-sirene", "0 0 7 * *", "04:00 le 7",
  "SIRENE mensuel COMPLET : DELETE puis réinsertion DuckDB (974 actifs)", "oui",
  "oui (data_sources.last_sync_at + source_millesime — sirene_etablissements.py:171-173)",
  "jobs.py:290-291 ; sirene_etablissements.py:143"),
 ("ingest-sitadel", "30 0 10 * *", "04:30 le 10",
  "SITADEL delta 3 mois + upsert, puis veille foncière + RUN CANDIDAT (rapport mail, bascule manuelle)", "oui",
  "oui (ingestion_runs — permits_sdes.py:302-315)", "jobs.py:292-293 ; jobs_impl.py:360-370"),
 ("ingest-dpe", "0 0 12 * *", "04:00 le 12",
  "DPE ADEME mensuel — SAUTE toute commune déjà peuplée (sans --force)", "oui",
  "NON — last_sync_at écrit même à 0 commune traitée (dpe.py:243, aucun if) : healthz peut dire « ok » à vide",
  "jobs.py:294 ; ingestion/dpe.py:217-245,306-308"),
 ("sync-gpu", "0 0 15 * *", "04:00 le 15",
  "SUP GPU par commune (purge puis réinsertion), puis evaluer_toutes() (veille)", "oui",
  "partielle (événements créés, pas d'ingestion_runs)", "jobs.py:295-296 ; sup_gpu.py:55-56 ; jobs_impl.py:385-389"),
 ("ingest-bdnb", "0 1 1 1,4,7,10 *", "05:00 le 1er jan/avr/juil/oct — NON POSÉ",
  "BDNB trimestriel streamé filtré 974 (amont 974 absent : constat SCORING-3)", "oui",
  "oui (data_sources)", "jobs.py:300-303 ; absent de deploy/cron.d-labuse"),
 ("sentinelle-sources", "0 3 * * *", "07:00",
  "sonde les sources amont (api/page/entete/temoin), alerte cloche admin, N'INGÈRE RIEN", "oui",
  "oui (source_veille.dernier_* — sentinelle.py:308-313)", "jobs.py:307-308"),
 ("radar-releves", "0 13 * * *", "17:00", "relevé quotidien des compteurs Radar (courbe d'accumulation)", "oui",
  "oui (radar_releves)", "jobs.py:311-312"),
 ("coherence-run", "15 3 * * *", "07:15",
  "garde de cohérence : chaque surface lit le run courant ; notifie à la divergence", "oui",
  "oui (notification event_log)", "jobs.py:315-316 ; coherence_flux.py"),
 ("restore-test", "0 1 1 * *", "05:00 le 1er", "restaure le dernier dump dans une base jetable et vérifie", "non",
  "non (mail/log)", "jobs.py:317-318"),
]

#: crons HORS wrapper encore versionnés dans deploy/cron.d/* (heures RÉUNION, JOURNAL.md:139-140).
#: Lesquels sont posés sur le VPS aujourd'hui : DOUTE (indécidable en local ; les deux jeux coexistent).
HORS = [
 ("cron.d/abuse (abuse-scan)", "06:00", "0 10 * * *", "labuse abuse-scan (détection d'abus d'accès)", "non",
  "DOUTE (table de trace à confirmer)", "deploy/cron.d/abuse"),
 ("cron.d/backup (backup_postgres.sh)", "05:30", "30 9 * * *", "dump direct par script shell", "non",
  "non (fichier)", "deploy/cron.d/backup"),
 ("cron.d/backup (db_maintenance.sh)", "04:00 dim", "0 8 * * 0", "maintenance DB par script shell", "non",
  "non", "deploy/cron.d/backup"),
 ("cron.d/ban (ingest-ban)", "03:30 le 5", "30 7 5 * *", "labuse ingest-ban --download (mensuel le 5)", "oui",
  "oui (data_sources.last_sync_at)", "deploy/cron.d/ban"),
 ("cron.d/bodacc (ingest-bodacc)", "02:30", "30 6 * * *", "labuse ingest-bodacc + fraicheur-derives (QUOTIDIEN)", "oui",
  "oui (data_sources)", "deploy/cron.d/bodacc — c'est CE cron que /healthz/crons attend (2 j, ops.py:23-41)"),
 ("cron.d/dpe (ingest-dpe hebdo)", "05:20 mar", "20 9 * * 2", "labuse ingest-dpe + fraicheur-derives (HEBDO mardi)", "oui",
  "NON (même défaut last_sync_at)", "deploy/cron.d/dpe — explique la note « hebdo » de healthz (ops.py:39-40) vs wrapper mensuel le 12"),
 ("cron.d/dvf (refresh-dvf)", "05:00 mer", "0 9 * * 3", "labuse refresh-dvf + fraicheur-derives (HEBDO mercredi)", "oui",
  "oui (data_sources)", "deploy/cron.d/dvf"),
 ("cron.d/fraicheur (check-fraicheur)", "06:30", "30 10 * * *", "labuse check-fraicheur", "oui",
  "oui (data_sources.fraicheur_*)", "deploy/cron.d/fraicheur — redondant avec le job wrapper sources-fraicheur"),
 ("cron.d/notifications", "03:00", "0 7 * * *",
  "evaluer-suivis + evaluer-veilles + notifier-fraicheur + purge-notifications + digest quotidien", "oui",
  "oui (event_log)", "deploy/cron.d/notifications"),
 ("cron.d/radar (radar-sources)", "02:00 lun", "0 6 * * 1", "labuse radar-sources (hebdo lundi) → /var/log/labuse/radar.log", "oui",
  "oui (source_radar)", "deploy/cron.d/radar — l'objet de la contradiction healthz vs log radar (Q3.5)"),
 ("cron.d/sessions (purge-sessions)", "04:00", "0 8 * * *", "labuse purge-sessions", "non",
  "oui (sessions_auth)", "deploy/cron.d/sessions"),
 ("cron.d/sitadel (refresh)", "02:15", "15 6 * * *", "python -m labuse.ingestion.permits_sdes --refresh + fraicheur-derives (QUOTIDIEN)", "oui",
  "oui (ingestion_runs)", "deploy/cron.d/sitadel — redondant avec le job wrapper mensuel le 10"),
 ("cron.d/sitadel (fraicheur hebdo)", "03:45 lun", "45 7 * * 1", "labuse fraicheur-derives --hebdo", "oui",
  "oui (data_sources)", "deploy/cron.d/sitadel"),
]


def main() -> None:
    OUT_JOBS.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for nom, utc, reunion, fait, eau, trace, preuve in WRAPPER:
        rows.append(dict(id=nom, horaire_utc=utc, horaire_reunion=reunion, fait_vraiment=fait,
                         touche_l_eau=eau, dernier_statut=DOUTE_ETAT, trace_base_coherente=trace,
                         preuve=preuve))
    for nom, reunion, brut, fait, eau, trace, preuve in HORS:
        rows.append(dict(id=nom, horaire_utc=f"(fichier en h. Réunion : {brut})", horaire_reunion=reunion,
                         fait_vraiment=fait, touche_l_eau=eau,
                         dernier_statut="DOUTE — pose VPS actuelle indécidable en local",
                         trace_base_coherente=trace, preuve=preuve))
    with OUT_JOBS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    sql = ("SELECT v.id, d.name AS source, v.methode, v.actif, v.cadence_heures,"
           " v.cadence_attendue_jours, v.url_version, v.selecteur, v.dernier_passage_at,"
           " v.dernier_vu, v.dernier_statut, v.dernier_message, v.echecs_consecutifs,"
           " v.dernier_notifie_vu, v.injection_lancee_at, v.injection_vu, v.mail_alerte,"
           " v.convention_echeance, v.url_temoin_2, v.created_at, v.updated_at"
           " FROM source_veille v JOIN data_sources d ON d.id = v.source_id ORDER BY v.id")
    out = subprocess.run(["psql", "-d", "labuse", "--csv", "-c", sql],
                         capture_output=True, text=True, check=True)
    # ';' pour l'homogénéité des livrables (le mandat impose le séparateur ;).
    lignes = list(csv.reader(out.stdout.splitlines()))
    with OUT_SV.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL).writerows(lignes)

    eau = Counter(r["touche_l_eau"] for r in rows)
    print(f"jobs.csv: {len(rows)} lignes ({len(WRAPPER)} wrapper + {len(HORS)} hors wrapper)")
    print(f"touche l'eau: oui={eau['oui']} non={eau['non']}")
    print(f"trace base cohérente NON/partielle: "
          f"{sum(1 for r in rows if r['trace_base_coherente'].startswith(('NON', 'partielle')))}")
    print(f"source_veille.csv: {len(lignes) - 1} lignes")


if __name__ == "__main__":
    main()
