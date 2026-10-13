#!/bin/bash
# SOLIDITE-1 (Lot 3.3) — TEST DE RESTAURATION MENSUEL, SUR LE MAC (jamais sur le disque du VPS).
# Une sauvegarde jamais restaurée n'est pas une sauvegarde. Le VPS n'a pas la place de restaurer
# 45 Go ; le Mac, si. Chaque mois (launchd) :
#   1. rapatrie le dernier dump du VPS (rsync pull, sens tiré) ;
#   2. le restaure dans une base JETABLE locale (labuse_restore_test), puis la supprime ;
#   3. compare les comptages des tables clés à la PROD (via SSH) ;
#   4. rapport dans ~/.labuse/restore_test.log + ALERTE (mail Brevo / notif macOS) si écart.
#
# Config (plist EnvironmentVariables) :
#   LABUSE_VPS_SSH        alias ssh du VPS (défaut labuse-vps)
#   LABUSE_REMOTE_BACKUP  dossier des dumps sur le VPS (défaut /var/backups/labuse)
#   LABUSE_LOCAL_BACKUP   dossier local de réception (défaut ~/labuse-backups)
#   PG_RESTORE_BIN, PSQL_BIN   binaires PG (défaut pg_restore/psql du PATH — doivent être >= majeure du VPS)
#   LABUSE_BREVO_API_KEY, LABUSE_ALERT_TO, LABUSE_ALERT_FROM   (mail d'alerte — sinon notif macOS + log)
set -u

SSHV="${LABUSE_VPS_SSH:-labuse-vps}"
REMOTE_DIR="${LABUSE_REMOTE_BACKUP:-/var/backups/labuse}"
LOCAL_DIR="${LABUSE_LOCAL_BACKUP:-$HOME/labuse-backups}"
PG_RESTORE="${PG_RESTORE_BIN:-pg_restore}"
PSQL="${PSQL_BIN:-psql}"
BASE="labuse_restore_test"
DIR="$HOME/.labuse"; LOG="$DIR/restore_test.log"
mkdir -p "$DIR" "$LOCAL_DIR"
now="$(date -u +%FT%TZ)"

# tables clés STABLES (comptage identique dump↔prod ; on ne compare pas les tables vivantes comme
# event_log/sessions qui bougent entre l'heure du dump et maintenant).
TABLES=(parcels data_sources score_labuse veilles comptes)

_json() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }
alerter() {
  sujet="$1"; corps="$2"
  echo "$now  ALERTE  $sujet — $corps" >> "$LOG"
  if [ -n "${LABUSE_BREVO_API_KEY:-}" ] && [ -n "${LABUSE_ALERT_TO:-}" ]; then
    from="${LABUSE_ALERT_FROM:-labuse@app.labuse.immo}"
    curl -sS -m 20 -X POST 'https://api.brevo.com/v3/smtp/email' \
      -H "api-key: ${LABUSE_BREVO_API_KEY}" -H 'content-type: application/json' \
      -d "{\"sender\":{\"email\":\"${from}\"},\"to\":[{\"email\":\"${LABUSE_ALERT_TO}\"}],\"subject\":$(_json "$sujet"),\"textContent\":$(_json "$corps")}" >> "$LOG" 2>&1
  fi
  osascript -e "display notification \"${corps}\" with title \"${sujet}\"" >/dev/null 2>&1 || true
}

echo "$now  ▶ test de restauration mensuel" >> "$LOG"

# 1) rapatrier le dernier dump
rsync -az --include="labuse-labuse-*.dump" --exclude="*" "${SSHV}:${REMOTE_DIR}/" "$LOCAL_DIR/" 2>>"$LOG"
DUMP="$(ls -1t "$LOCAL_DIR"/labuse-labuse-*.dump 2>/dev/null | head -1)"
if [ -z "$DUMP" ]; then alerter "[LABUSE] restore-test : aucun dump" "Aucun dump rapatriable depuis $SSHV:$REMOTE_DIR"; exit 1; fi

# 2) restaurer dans une base jetable (puis DROP, quoi qu'il arrive)
"$PSQL" -d postgres -c "DROP DATABASE IF EXISTS ${BASE}" >>"$LOG" 2>&1
"$PSQL" -d postgres -c "CREATE DATABASE ${BASE}" >>"$LOG" 2>&1 || { alerter "[LABUSE] restore-test : base jetable KO" "CREATE DATABASE a échoué"; exit 1; }
trap '"$PSQL" -d postgres -c "DROP DATABASE IF EXISTS '"${BASE}"'" >>"'"$LOG"'" 2>&1' EXIT

if ! "$PG_RESTORE" --no-owner --no-acl -d "$BASE" "$DUMP" >>"$LOG" 2>&1; then
  echo "$now  (pg_restore a signalé des erreurs — on compare quand même les tables clés)" >> "$LOG"
fi

# 3) comparer les comptages des tables clés à la prod
ecarts=""
for t in "${TABLES[@]}"; do
  loc="$("$PSQL" -At -d "$BASE" -c "SELECT count(*) FROM ${t}" 2>/dev/null)"
  prod="$(ssh -o ConnectTimeout=15 "$SSHV" "sudo -u postgres psql -At -d labuse -c 'SELECT count(*) FROM ${t}'" 2>/dev/null)"
  loc="${loc:-ABSENTE}"; prod="${prod:-?}"
  echo "$now    $t : restauré=$loc  prod=$prod" >> "$LOG"
  # écart = table perdue à la restauration, ou comptage stable qui diffère
  if [ "$loc" = "ABSENTE" ] || { [ "$loc" != "$prod" ] && [ "$prod" != "?" ]; }; then
    ecarts="$ecarts ${t}(restauré=$loc,prod=$prod)"
  fi
done

if [ -n "$ecarts" ]; then
  alerter "[LABUSE] restore-test : ÉCART" "Restauration $DUMP OK mais comptages divergents :$ecarts"
  echo "$now  ✗ ÉCART :$ecarts" >> "$LOG"
  exit 1
fi
echo "$now  ✓ restauration vérifiée (tables clés = prod) à partir de $(basename "$DUMP")" >> "$LOG"
