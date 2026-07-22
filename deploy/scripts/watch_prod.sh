#!/usr/bin/env bash
# =============================================================================
# LA BUSE — sentinelle de PROD (J6, poste local) : healthz + état des crons.
# 2 échecs consécutifs → notification macOS + log ; jamais silencieux.
# Secrets lus depuis ~/labuse-backups/M7_SECRETS.txt (jamais en git).
# =============================================================================
set -u
S=~/labuse-backups/M7_SECRETS.txt ; . "$S"
BASE="${LABUSE_PROD_URL:-https://app.labuse.immo}"
STATE=~/labuse-backups/watch_prod.state
code=$(curl -s -m 15 -o /tmp/watch_h.json -w '%{http_code}' -u "labuse:${CADDY_BASIC_AUTH_PASSWORD}" "$BASE/healthz/crons")
ok=0
if [ "$code" = "200" ]; then
  grep -q '"ok": *true' /tmp/watch_h.json && ok=1 || ok=0   # un cron en retard = alerte aussi
fi
prev=$(cat "$STATE" 2>/dev/null || echo ok)
if [ "$ok" = 1 ]; then
  echo ok > "$STATE"
  exit 0
fi
if [ "$prev" = "fail" ]; then   # 2e échec consécutif → alerte
  msg="LABUSE prod : healthz KO ou cron en retard (HTTP $code) — $(date '+%H:%M')"
  echo "$(date -Iseconds) ALERTE $msg" >> ~/labuse-backups/watch_prod.log
  osascript -e "display notification \"$msg\" with title \"⚠ LABUSE PROD\"" 2>/dev/null || true
else
  echo fail > "$STATE"
  echo "$(date -Iseconds) 1er échec (HTTP $code) — confirmation au prochain passage" >> ~/labuse-backups/watch_prod.log
fi
