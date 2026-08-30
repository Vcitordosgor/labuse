#!/bin/sh
# CRON-1 (K8) — POSE de l'exploitation planifiée sur le serveur (déploiement groupé).
# À lancer SUR LE VPS (root). Pose le crontab versionné + le logrotate des logs de jobs, APRÈS avoir
# vérifié que l'horloge serveur est en UTC (le crontab est écrit en heure UTC — un serveur en heure
# Réunion décalerait TOUS les jobs de 4 h).
#
# Idempotent. N'installe RIEN d'autre (le code/venv/systemd passent par deploy/scripts/deploy_app.sh).
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"

echo "→ Vérification du fuseau serveur (doit être UTC)…"
tz="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo inconnu)"
if [ "$tz" != "UTC" ] && [ "$tz" != "Etc/UTC" ]; then
  cat >&2 <<MSG
✗ REFUS : le serveur est en fuseau « $tz », pas UTC.
  Le crontab deploy/cron.d-labuse est écrit en heure UTC (La Réunion = UTC+4, sans heure d'été) ;
  le poser sur un serveur en heure Réunion décalerait tous les jobs de 4 h.
  À adapter :  sudo timedatectl set-timezone UTC   puis relancer ./deploy.sh
  (Les fenêtres MÉTIER restent calculées en Indian/Reunion explicite dans le code — indépendant.)
MSG
  exit 1
fi
echo "  ✓ fuseau serveur = $tz"

echo "→ Pose du crontab /etc/cron.d/labuse…"
install -o root -g root -m 644 "$REPO/deploy/cron.d-labuse" /etc/cron.d/labuse
echo "  ✓ /etc/cron.d/labuse"

echo "→ Pose du logrotate des logs de jobs…"
install -o root -g root -m 644 "$REPO/deploy/logrotate.d/labuse-jobs" /etc/logrotate.d/labuse-jobs
echo "  ✓ /etc/logrotate.d/labuse-jobs (30 j)"

echo "→ Dossiers d'état et de logs…"
install -d -o labuse -g labuse -m 755 /opt/labuse/state/jobs /var/log/labuse
echo "  ✓ /opt/labuse/state/jobs · /var/log/labuse"

echo "✓ Exploitation planifiée posée. Vérifier :  labuse jobs list   et   tail -f /var/log/labuse/*.log"
