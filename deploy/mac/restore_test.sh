#!/bin/bash
# SOLIDITE-1 (Lot 3.3) + DONNEES-ETAT-FIX-2 (Lot A) — TEST DE RESTAURATION MENSUEL, SUR LE MAC
# (jamais sur le disque du VPS). Une sauvegarde jamais restaurée n'est pas une sauvegarde. Chaque mois
# (launchd) :
#   0. GARDE-FOU : refuse si < N Go libres (défaut 20) — une restauration qui remplit le disque est pire ;
#   1. rapatrie le dernier dump du VPS (rsync pull, sens tiré) ;
#   2. le restaure dans une base JETABLE locale (labuse_restore_test), puis la supprime (trap EXIT) ;
#   3. compare les comptages des tables clés à la PROD (via SSH, lecture seule) + compte le RUN SERVI ;
#   4. écrit un MARQUEUR .restore-test.json (date, OK/KO, comptages) LU PAR LE TABLEAU DE BORD ;
#   5. rapport dans ~/.labuse/restore_test.log + ALERTE (mail Brevo / notif macOS) si écart.
#
# Config (plist EnvironmentVariables) :
#   LABUSE_VPS_SSH        alias ssh du VPS (défaut labuse-vps)
#   LABUSE_REMOTE_BACKUP  dossier des dumps sur le VPS (défaut /var/backups/labuse)
#   LABUSE_LOCAL_BACKUP   dossier local de réception (défaut ~/labuse-backups)
#   LABUSE_BACKUP_DIR     où écrire le marqueur lu par le dashboard (défaut = LABUSE_LOCAL_BACKUP)
#   LABUSE_RESTORE_MIN_GO garde-fou espace libre en Go (défaut 20)
#   LABUSE_RESTORE_TABLES sous-ensemble de tables à restaurer (dev/petit disque) ; vide = dump COMPLET
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
MIN_GO="${LABUSE_RESTORE_MIN_GO:-20}"
MARQ_DIR="${LABUSE_BACKUP_DIR:-$LOCAL_DIR}"
MARQUEUR="$MARQ_DIR/.restore-test.json"
read -ra SUBSET <<< "${LABUSE_RESTORE_TABLES:-}"     # vide => () => dump complet
mkdir -p "$DIR" "$LOCAL_DIR" "$MARQ_DIR"
now="$(date -u +%FT%TZ)"

# tables clés STABLES (comptage identique dump↔prod ; on ne compare pas les tables vivantes comme
# event_log/sessions qui bougent entre l'heure du dump et maintenant).
TABLES=(parcels data_sources score_labuse veilles comptes)

# État accumulé pour le marqueur (rempli au fil de l'eau).
run_servi=""; run_lignes=""; comptes_json="{}"; DUMP=""

_json() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

# MARQUEUR lu par le Tableau de bord (ops_alertes.lire_restore_test) — statut ok|ko|refuse.
ecrire_marqueur() {   # $1=statut  $2=message
  python3 - "$MARQUEUR" "$1" "$2" "$DUMP" "$run_servi" "$run_lignes" "$comptes_json" "$MIN_GO" <<'PY'
import json, os, sys, datetime
chemin, statut, message, dump, run_servi, run_lignes, comptes, min_go = sys.argv[1:9]
json.dump({
  "test_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
  "statut": statut,                                   # ok | ko | refuse
  "message": message,
  "dump": os.path.basename(dump) if dump else None,
  "run_servi": run_servi or None,
  "run_servi_lignes": int(run_lignes) if str(run_lignes).isdigit() else None,
  "tables": json.loads(comptes) if comptes else {},
  "min_go": int(min_go) if str(min_go).isdigit() else None,
}, open(chemin, "w"), ensure_ascii=False, indent=1)
PY
  echo "$now    marqueur → $MARQUEUR ($1)" >> "$LOG"
}

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

echo "$now  ▶ test de restauration mensuel (garde ${MIN_GO} Go)" >> "$LOG"

# 0) GARDE-FOU espace libre (Go sur la partition du dossier local). macOS : df -g = GiB.
libre_go="$(df -g "$LOCAL_DIR" | awk 'NR==2{print $4}')"
if [ "${libre_go:-0}" -lt "$MIN_GO" ]; then
  echo "$now  ⚠ REFUS : ${libre_go} Go libres < ${MIN_GO} Go requis — restauration reportée" >> "$LOG"
  ecrire_marqueur "refuse" "Espace insuffisant (${libre_go} Go libres < ${MIN_GO} Go requis) — test reporté"
  alerter "[LABUSE] restore-test : reporté" "Espace insuffisant (${libre_go} Go < ${MIN_GO} Go) — test reporté, non bloquant"
  exit 0   # reporté proprement, pas un échec
fi

# 1) rapatrier le dernier dump
rsync -az --include="labuse-labuse-*.dump" --exclude="*" "${SSHV}:${REMOTE_DIR}/" "$LOCAL_DIR/" 2>>"$LOG"
DUMP="$(ls -1t "$LOCAL_DIR"/labuse-labuse-*.dump 2>/dev/null | head -1)"
if [ -z "$DUMP" ]; then
  ecrire_marqueur "ko" "Aucun dump rapatriable depuis $SSHV:$REMOTE_DIR"
  alerter "[LABUSE] restore-test : aucun dump" "Aucun dump rapatriable depuis $SSHV:$REMOTE_DIR"; exit 1
fi

# 2) restaurer dans une base jetable (puis DROP, quoi qu'il arrive)
"$PSQL" -d postgres -c "DROP DATABASE IF EXISTS ${BASE}" >>"$LOG" 2>&1
"$PSQL" -d postgres -c "CREATE DATABASE ${BASE}" >>"$LOG" 2>&1 || {
  ecrire_marqueur "ko" "CREATE DATABASE jetable a échoué"
  alerter "[LABUSE] restore-test : base jetable KO" "CREATE DATABASE a échoué"; exit 1; }
trap '"$PSQL" -d postgres -c "DROP DATABASE IF EXISTS '"${BASE}"'" >>"'"$LOG"'" 2>&1' EXIT

# Restauration : dump COMPLET par défaut ; sous-ensemble -t si LABUSE_RESTORE_TABLES est posé (dev).
RESTORE_ARGS=(--no-owner --no-acl -d "$BASE")
if [ "${#SUBSET[@]}" -gt 0 ]; then
  for t in "${SUBSET[@]}"; do RESTORE_ARGS+=(-t "$t"); done
  echo "$now  (restauration SOUS-ENSEMBLE : ${SUBSET[*]})" >> "$LOG"
fi
if ! "$PG_RESTORE" "${RESTORE_ARGS[@]}" "$DUMP" >>"$LOG" 2>&1; then
  echo "$now  (pg_restore a signalé des erreurs — on compare quand même les tables clés)" >> "$LOG"
fi

# run servi (lecture seule depuis la prod) — pour compter ses lignes dans la base restaurée.
run_servi="$(ssh -o ConnectTimeout=15 "$SSHV" "grep -vE '^[[:space:]]*#|^[[:space:]]*\$' /opt/labuse/app/config/served_run.txt 2>/dev/null | head -1" 2>/dev/null)"

# 3) comparer les comptages des tables clés à la prod (sauf si sous-ensemble : on ne compare que celles-là)
CHECK=("${TABLES[@]}"); [ "${#SUBSET[@]}" -gt 0 ] && CHECK=("${SUBSET[@]}")
ecarts=""; comptes_json="{"
for t in "${CHECK[@]}"; do
  loc="$("$PSQL" -At -d "$BASE" -c "SELECT count(*) FROM ${t}" 2>/dev/null)"
  prod="$(ssh -o ConnectTimeout=15 "$SSHV" "sudo -u postgres psql -At -d labuse -c 'SELECT count(*) FROM ${t}'" 2>/dev/null)"
  loc="${loc:-ABSENTE}"; prod="${prod:-?}"
  echo "$now    $t : restauré=$loc  prod=$prod" >> "$LOG"
  comptes_json="$comptes_json\"$t\":{\"restaure\":\"$loc\",\"prod\":\"$prod\"},"
  if [ "$loc" = "ABSENTE" ] || { [ "$loc" != "$prod" ] && [ "$prod" != "?" ]; }; then
    ecarts="$ecarts ${t}(restauré=$loc,prod=$prod)"
  fi
done
comptes_json="${comptes_json%,}}"

# run servi : nombre de lignes score_labuse pour le run servi (dans la base restaurée).
# Sauté si un SOUS-ENSEMBLE est demandé sans score_labuse (restauration partielle de dev/petit disque).
_score_restaure=1
if [ "${#SUBSET[@]}" -gt 0 ] && ! printf '%s\n' "${SUBSET[@]}" | grep -qx score_labuse; then
  _score_restaure=0
  echo "$now    (run servi non compté : score_labuse hors sous-ensemble)" >> "$LOG"
fi
if [ -n "$run_servi" ] && [ "$_score_restaure" = 1 ]; then
  run_lignes="$("$PSQL" -At -d "$BASE" -c "SELECT count(*) FROM score_labuse WHERE run_label='${run_servi}'" 2>/dev/null)"
  echo "$now    run servi $run_servi : $run_lignes lignes score_labuse" >> "$LOG"
  if [ -z "${run_lignes}" ] || [ "${run_lignes:-0}" -lt 1 ]; then
    ecarts="$ecarts run_servi:$run_servi(0 ligne)"
  fi
fi

if [ -n "$ecarts" ]; then
  ecrire_marqueur "ko" "Restauration OK mais comptages divergents :$ecarts"
  alerter "[LABUSE] restore-test : ÉCART" "Restauration $(basename "$DUMP") OK mais comptages divergents :$ecarts"
  echo "$now  ✗ ÉCART :$ecarts" >> "$LOG"
  exit 1
fi
ecrire_marqueur "ok" "Restauration vérifiée (tables clés = prod, run servi $run_servi = $run_lignes lignes)"
echo "$now  ✓ restauration vérifiée (tables clés = prod) à partir de $(basename "$DUMP")" >> "$LOG"
