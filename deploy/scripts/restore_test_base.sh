#!/usr/bin/env bash
# AUTONOMIE-1 — restauration de CONTRÔLE dans une BASE À PART (jamais la base servie).
# Restaure $LABUSE_RESTORE_DUMP dans une base jetable (labuse_restore_ctrl), compte ses tables,
# puis la DÉTRUIT. Appelé par jobs_impl.restore_test quand LABUSE_RESTORE_TEST_REEL=1 et que le disque
# le permet (garde 4× côté Python). Imprime `TABLES=<n>` sur stdout. Idempotent (drop-if-exists avant).
#
# Rôle de dump = labuse (SELECT) ; la création/suppression de base demande un rôle qui le peut
# (LABUSE_RESTORE_SUPERUSER, défaut postgres). Aucune écriture dans la base de prod.
set -euo pipefail

DUMP="${LABUSE_RESTORE_DUMP:?LABUSE_RESTORE_DUMP requis}"
BASE="${LABUSE_RESTORE_BASE:-labuse_restore_ctrl}"
SU="${LABUSE_RESTORE_SUPERUSER:-postgres}"
HOST="${PGHOST:-localhost}"
PORT="${PGPORT:-5432}"

[ -f "$DUMP" ] || { echo "dump introuvable : $DUMP" >&2; exit 2; }

psql_su() { psql -h "$HOST" -p "$PORT" -U "$SU" -v ON_ERROR_STOP=1 "$@"; }

# base jetable repartant de zéro (drop si un run précédent a laissé des restes)
psql_su -d postgres -c "DROP DATABASE IF EXISTS ${BASE};"
psql_su -d postgres -c "CREATE DATABASE ${BASE};"
# PostGIS d'abord (le dump suppose l'extension présente — spatial_ref_sys repeuplé par l'extension)
psql_su -d "${BASE}" -c "CREATE EXTENSION IF NOT EXISTS postgis;" >/dev/null 2>&1 || true

trap 'psql_su -d postgres -c "DROP DATABASE IF EXISTS ${BASE};" >/dev/null 2>&1 || true' EXIT

# restauration (jobs parallèles modérés ; on tolère les erreurs d'objets déjà fournis par l'extension)
pg_restore -h "$HOST" -p "$PORT" -U "$SU" -d "${BASE}" --no-owner --jobs=2 "$DUMP" \
  >/tmp/restore_test_base.out 2>&1 || {
    # pg_restore sort non-zéro sur de simples warnings (ex. extension déjà là) : on ne casse que si 0 table
    echo "pg_restore a signalé des erreurs (voir /tmp/restore_test_base.out) — on vérifie le résultat" >&2
  }

TABLES=$(psql_su -tA -d "${BASE}" -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
echo "TABLES=${TABLES}"
[ "${TABLES:-0}" -ge 100 ] || { echo "trop peu de tables restaurées (${TABLES})" >&2; exit 3; }
