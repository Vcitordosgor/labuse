#!/bin/sh
# CRON-1 (K1) — LE WRAPPER COMMUN. Point d'entrée UNIQUE de tout job planifié.
#   scripts/jobs/run-job.sh <nom>
#
# Fait, dans cet ordre :
#   1. VERROU par job : un second lancement pendant qu'un premier tourne est REFUSÉ proprement
#      (code 200 = « tour sauté », jamais confondu avec un échec du job) et le dit dans le log.
#      → `flock` sur le serveur (Linux, kernel, relâché à la mort du process) ;
#      → repli `mkdir` atomique quand flock est absent (macOS de dev) — testable partout.
#   2. LOG daté : toute la sortie va dans <LOG_DIR>/<nom>.log (logrotate 30 j fourni) ;
#   3. délègue à `labuse jobs exec <nom>` : timeout par job, fichier d'état JSON, alerte mail à l'échec,
#      règle dry-run (sans SMTP : calcule/logue, n'envoie rien), ping témoin externe.
#
# Le crontab n'appelle QUE `labuse jobs run <nom>` (K2) qui appelle CE script → un seul verrou, partagé
# par le cron ET le bouton « Lancer maintenant » de l'admin. Zéro logique dans le crontab.
#
# Variables : LABUSE_BIN (binaire labuse), LABUSE_JOBS_LOG_DIR (logs), LABUSE_LOCK_DIR (verrous).
set -eu

BIN="${LABUSE_BIN:-labuse}"
LOG_DIR="${LABUSE_JOBS_LOG_DIR:-/var/log/labuse}"
LOCK_DIR="${LABUSE_LOCK_DIR:-/run/lock}"

# Corps VERROUILLÉ : ré-invocation de ce script (évite tout enfer de quoting dans flock -c).
if [ "${1:-}" = "__locked" ]; then
  nom="$2"
  echo "$(date -u +%FT%TZ) [$nom] début"
  $BIN jobs exec "$nom"
  code=$?
  echo "$(date -u +%FT%TZ) [$nom] fin (code $code)"
  exit "$code"
fi

nom="${1:?usage: run-job.sh <nom-du-job>}"
mkdir -p "$LOG_DIR" "$LOCK_DIR" 2>/dev/null || true
log="$LOG_DIR/$nom.log"

if command -v flock >/dev/null 2>&1; then
  # flock -n (non bloquant), -E 200 : verrou déjà pris → code 200 (≠ échec du job).
  set +e
  flock -n -E 200 "$LOCK_DIR/labuse-job-$nom.lock" sh "$0" __locked "$nom" >> "$log" 2>&1
  code=$?
  set -e
else
  # repli portable : mkdir est atomique (échoue si le dossier existe → verrou déjà pris).
  lockdir="$LOCK_DIR/labuse-job-$nom.lock.d"
  if mkdir "$lockdir" 2>/dev/null; then
    trap 'rmdir "$lockdir" 2>/dev/null || true' EXIT
    set +e
    sh "$0" __locked "$nom" >> "$log" 2>&1
    code=$?
    set -e
  else
    code=200
  fi
fi

if [ "$code" -eq 200 ]; then
  echo "$(date -u +%FT%TZ) [$nom] passage SAUTÉ : une exécution précédente est encore en cours" >> "$log"
  echo "job $nom : déjà en cours (verrou tenu) — lancement refusé." >&2
  exit 200
fi
exit "$code"
