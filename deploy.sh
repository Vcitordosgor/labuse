#!/bin/sh
# CRON-1 (K8) → CIRCUIT-1 (lot 8.1) — POSE de l'exploitation planifiée sur le serveur.
# À lancer SUR LE VPS (root). Pose le crontab versionné + le logrotate, avec DEUX gardes :
#
#   1. FUSEAU — le crontab deploy/cron.d-labuse est écrit en UTC (heure Réunion en commentaire).
#      · serveur en UTC            → posé tel quel ;
#      · serveur en Indian/Reunion → CONVERTI automatiquement (+4 h, modulo 24 — sûr ici : seuls
#        des jobs QUOTIDIENS franchissent minuit, aucun décalage de date ni de jour de semaine).
#        C'est LE piège qui a empêché la pose du wrapper (constat CIRCUIT-1 lot 0.1 : le VPS est
#        passé en Indian/Reunion au mandat VPS du 27/08, l'ancien deploy.sh REFUSAIT → seuls les
#        crons LEGACY tournaient) ;
#      · tout autre fuseau         → refus.
#   2. LEGACY — refuse de déployer si /etc/cron.d/ contient encore un fichier labuse-* (l'ancien
#      jeu, 13 lignes) : DEUX jeux de crons = doubles ingestions et un healthz qui ment.
#      Retrait : deploy/scripts/retirer_crons_legacy.sh (geste explicite, jamais automatique).
#
# Idempotent. N'installe RIEN d'autre (code/venv/systemd : deploy/scripts/deploy_app.sh).
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"

echo "→ Garde legacy : /etc/cron.d/labuse-* doit être vide…"
legacy="$(ls /etc/cron.d/labuse-* 2>/dev/null || true)"
if [ -n "$legacy" ]; then
  cat >&2 <<MSG
✗ REFUS : d'anciens crons legacy sont encore posés :
$legacy
  Deux jeux de crons = doubles ingestions (bodacc/dpe/dvf/sitadel) et un healthz incohérent.
  Retirez-les d'abord (geste explicite) :  sudo sh deploy/scripts/retirer_crons_legacy.sh
MSG
  exit 1
fi
echo "  ✓ aucun cron legacy"

echo "→ Fuseau serveur…"
tz="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo inconnu)"
CRONSRC="$REPO/deploy/cron.d-labuse"
case "$tz" in
  UTC|Etc/UTC)
    echo "  ✓ UTC — crontab posé tel quel" ;;
  Indian/Reunion)
    echo "  ✓ Indian/Reunion — conversion +4 h (modulo 24) du crontab UTC"
    CRONSRC="/tmp/cron.d-labuse.reunion"
    awk '
      /^[0-9*]/ {
        h = $2
        if (h ~ /^[0-9]+$/) { h = (h + 4) % 24; $2 = h }
        print; next
      }
      { print }
    ' "$REPO/deploy/cron.d-labuse" > "$CRONSRC"
    ;;
  *)
    cat >&2 <<MSG
✗ REFUS : fuseau serveur « $tz » ni UTC ni Indian/Reunion.
  Le crontab est écrit en UTC ; seul le décalage Réunion (+4 h, sans heure d'été) est converti.
MSG
    exit 1 ;;
esac

echo "→ Pose du crontab /etc/cron.d/labuse…"
install -o root -g root -m 644 "$CRONSRC" /etc/cron.d/labuse
echo "  ✓ /etc/cron.d/labuse (source : $(basename "$CRONSRC"))"

echo "→ Pose du logrotate des logs de jobs…"
install -o root -g root -m 644 "$REPO/deploy/logrotate.d/labuse-jobs" /etc/logrotate.d/labuse-jobs
echo "  ✓ /etc/logrotate.d/labuse-jobs (30 j)"

echo "→ Dossiers d'état et de logs…"
install -d -o labuse -g labuse -m 755 /opt/labuse/state/jobs /var/log/labuse
echo "  ✓ /opt/labuse/state/jobs · /var/log/labuse"

echo "✓ Exploitation planifiée posée. Vérifier :  labuse jobs list   et   tail -f /var/log/labuse/*.log"
