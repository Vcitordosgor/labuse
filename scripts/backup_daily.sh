#!/usr/bin/env bash
# LA BUSE — sauvegarde quotidienne : dump horodaté + rotation + journal.
#
# Cron (serveur pilote, 3 h du matin) :
#   0 3 * * * cd /opt/labuse && ./scripts/backup_daily.sh
#
# Variables (optionnelles, via environnement ou .env chargé par cron wrapper) :
#   LABUSE_BACKUP_KEEP    nombre de dumps conservés (défaut 14)
#   LABUSE_BACKUP_DIR     dossier des dumps (défaut backups/)
#   LABUSE_BACKUP_EXTERN  dossier EXTERNE où copier le dernier dump (montage NFS,
#                         point rclone…) — vide = pas de copie externe (à configurer !)
#
# Le script utilise le conteneur compose s'il tourne, sinon le CLI local.
set -euo pipefail
cd "$(dirname "$0")/.."

KEEP="${LABUSE_BACKUP_KEEP:-14}"
DIR="${LABUSE_BACKUP_DIR:-backups}"
EXTERN="${LABUSE_BACKUP_EXTERN:-}"
LOG="$DIR/backup.log"
mkdir -p "$DIR"

run_backup() {
  if command -v docker >/dev/null 2>&1 \
     && docker compose -f docker-compose.pilot.yml ps --status running app >/dev/null 2>&1 \
     && [ -n "$(docker compose -f docker-compose.pilot.yml ps --status running -q app 2>/dev/null)" ]; then
    docker compose -f docker-compose.pilot.yml exec -T app labuse backup-db --dir backups
  else
    labuse backup-db --dir "$DIR"
  fi
}

{
  echo "[$(date -Is)] sauvegarde — début"
  run_backup
  # Rotation : ne garde que les KEEP dumps les plus récents.
  ls -1t "$DIR"/labuse-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f --
  latest="$(ls -1t "$DIR"/labuse-*.dump 2>/dev/null | head -1)"
  if [ -n "$EXTERN" ] && [ -n "$latest" ]; then
    cp -- "$latest" "$EXTERN/" && echo "copie externe : $EXTERN/$(basename "$latest")"
  fi
  echo "[$(date -Is)] sauvegarde — OK ($(ls -1 "$DIR"/labuse-*.dump 2>/dev/null | wc -l) dump(s) conservé(s))"
} >>"$LOG" 2>&1 || { echo "[$(date -Is)] sauvegarde — ÉCHEC (voir au-dessus)" >>"$LOG"; exit 1; }
