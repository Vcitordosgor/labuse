#!/bin/sh
# CIRCUIT-1 (lot 8.1) — RETRAIT des crons legacy /etc/cron.d/labuse-* (geste EXPLICITE, jamais
# automatique). Le wrapper (deploy.sh → /etc/cron.d/labuse) reprend TOUT : bodacc quotidien,
# dpe/dvf aux cadences du registre, sitadel mensuel + candidat, sentinelle, sonde du circuit…
# Chaque fichier retiré est listé ; une SAUVEGARDE part dans /root/crons-legacy-<date>/.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "✗ à lancer en root" >&2; exit 1; }
sauve="/root/crons-legacy-$(date +%Y%m%d-%H%M)"
fichiers="$(ls /etc/cron.d/labuse-* 2>/dev/null || true)"
if [ -z "$fichiers" ]; then
  echo "✓ aucun cron legacy à retirer."
  exit 0
fi
mkdir -p "$sauve"
for f in $fichiers; do
  cp "$f" "$sauve/"
  rm "$f"
  echo "  − $f (sauvé dans $sauve/)"
done
systemctl restart cron 2>/dev/null || service cron restart 2>/dev/null || true
echo "✓ legacy retiré ($(echo "$fichiers" | wc -w | tr -d ' ') fichiers). Poser le wrapper :  sudo sh deploy.sh"
