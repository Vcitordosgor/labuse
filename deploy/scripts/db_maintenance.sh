#!/usr/bin/env bash
# =============================================================================
# LA BUSE — maintenance base (NON destructive)
# -----------------------------------------------------------------------------
# VACUUM ANALYZE (récupère l'espace mort + rafraîchit les stats du planner) puis
# AUDIT en lecture seule : taille base, tables les plus lourdes, index GIST.
# AUCUNE suppression, AUCUN VACUUM FULL (pas de verrou exclusif).
#
# Usage :   deploy/scripts/db_maintenance.sh
# Cron   :   0 4 * * 0  (dimanche 4h) — voir docs/DEPLOYMENT_OVH_VPS.md §11
# Auth DB :  via ~/.pgpass (chmod 600) ou variables PG* / LABUSE_DB_*.
# =============================================================================
set -euo pipefail

DB="${LABUSE_DB_NAME:-labuse}"
DB_USER="${LABUSE_DB_USER:-labuse}"
DB_HOST="${LABUSE_DB_HOST:-localhost}"
DB_PORT="${LABUSE_DB_PORT:-5432}"

PSQL=(psql -X -q -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB")

echo "== [$(date '+%F %T')] Maintenance LA BUSE — base '$DB' =="

echo "-- VACUUM ANALYZE (non bloquant : ni VACUUM FULL, ni suppression) --"
# La maintenance ne doit pas être coupée par statement_timeout.
"${PSQL[@]}" -c "SET statement_timeout = 0; VACUUM (ANALYZE, VERBOSE);" >/dev/null
echo "   ✓ stats rafraîchies, espace mort récupéré."

echo "-- Taille totale de la base --"
"${PSQL[@]}" -c "SELECT pg_size_pretty(pg_database_size('$DB')) AS taille_base;"

echo "-- Tables les plus lourdes (heap + index + toast) --"
"${PSQL[@]}" -c "
  SELECT relname AS table,
         pg_size_pretty(pg_total_relation_size(relid)) AS total,
         pg_size_pretty(pg_relation_size(relid))       AS heap,
         pg_size_pretty(pg_indexes_size(relid))        AS index,
         n_live_tup                                    AS lignes
    FROM pg_stat_user_tables
   ORDER BY pg_total_relation_size(relid) DESC
   LIMIT 12;"

echo "-- Index GIST spatiaux (geom / geom_2975) --"
"${PSQL[@]}" -c "
  SELECT indexrelname AS index,
         pg_size_pretty(pg_relation_size(indexrelid)) AS taille,
         idx_scan AS scans
    FROM pg_stat_user_indexes
   WHERE indexrelname ILIKE '%geom%'
   ORDER BY pg_relation_size(indexrelid) DESC;"

echo "== Maintenance terminée — aucune donnée supprimée. =="
