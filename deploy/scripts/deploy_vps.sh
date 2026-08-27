#!/usr/bin/env bash
# =============================================================================
# LA BUSE — déploiement VPS (git pull + install + build + restart) — MANDAT VPS V2
# -----------------------------------------------------------------------------
# S'exécute SUR LE VPS (avec sudo) : /opt/labuse/deploy.sh
# Pose :  install -o root -g root -m 755 deploy/scripts/deploy_vps.sh /opt/labuse/deploy.sh
#
# Ce que fait chaque déploiement, dans l'ordre, avec garde :
#   0. backup automatique de la base (backup_postgres.sh — refuse un dump illisible)
#   1. git fetch + pull --ff-only sur la BRANCHE COURANTE du clone /opt/labuse/app
#      (main en régime normal ; une branche de mandat si une bascule est en cours)
#   2. pip install -e . dans le venv (dépendances suivent pyproject.toml)
#   3. migrations : labuse init-db (schéma additif, CREATE TABLE IF NOT EXISTS — idempotent)
#   4. build front (npm ci + vite build --base=/) SI frontend/ a changé
#   5. restart systemd + healthcheck /readyz (ready=true exigé)
#
# ROLLBACK (documenté, manuel — jamais automatique pour ne rien masquer) :
#   sudo -u labuse git -C /opt/labuse/app reset --hard "$COMMIT_AVANT"   # affiché en début de run
#   sudo -u labuse /opt/labuse/venv/bin/pip install -e /opt/labuse/app
#   sudo systemctl restart labuse && curl -fsS localhost:8000/readyz
#   (la base : restaurer le dump pris à l'étape 0 — labuse restore-db --file <dump>)
# =============================================================================
set -euo pipefail

APP=/opt/labuse/app
VENV=/opt/labuse/venv
RUN_AS=labuse

[ "$(id -u)" -eq 0 ] || { echo "✗ lancer avec sudo (systemctl + su labuse)"; exit 2; }
[ -d "$APP/.git" ] || { echo "✗ $APP n'est pas un clone git"; exit 2; }

BRANCHE="$(sudo -u $RUN_AS git -C $APP branch --show-current)"
AVANT="$(sudo -u $RUN_AS git -C $APP rev-parse HEAD)"
echo "▶ [$(date '+%F %T')] deploy — branche $BRANCHE, commit avant : $AVANT"
echo "  (rollback : sudo -u labuse git -C $APP reset --hard $AVANT ; voir en-tête du script)"

# --- 0. filet : backup base AVANT tout (échec bruyant = on ne déploie pas) ---
echo "▶ backup pré-déploiement…"
set -a; . /etc/labuse/labuse.env; set +a
sudo -u $RUN_AS --preserve-env=LABUSE_BACKUP_DIR,LABUSE_BACKUP_KEEP,LABUSE_DB_NAME,LABUSE_DB_USER,LABUSE_DB_HOST,LABUSE_DB_PORT \
    "$APP/deploy/scripts/backup_postgres.sh"

# --- 1. code ---
sudo -u $RUN_AS git -C $APP fetch origin
sudo -u $RUN_AS git -C $APP pull --ff-only origin "$BRANCHE"
APRES="$(sudo -u $RUN_AS git -C $APP rev-parse HEAD)"
if [ "$AVANT" = "$APRES" ]; then echo "  (code déjà à jour — on continue quand même : venv/front/restart)"; fi

# --- 2. dépendances Python (extra [ai] = anthropic : le Copilote en prod appelle le LLM ;
# sans lui, LABUSE_AI_PROVIDER=anthropic tombe en ModuleNotFoundError au 1er /ask) ---
sudo -u $RUN_AS "$VENV/bin/pip" install -q -e "$APP[ai]"

# --- 3. migrations (schéma additif idempotent) ---
sudo -u $RUN_AS --preserve-env=LABUSE_DATABASE_URL "$VENV/bin/labuse" init-db

# --- 4. front (seulement si frontend/ a bougé, ou si dist absent) ---
if [ ! -d "$APP/frontend/dist" ] || ! sudo -u $RUN_AS git -C $APP diff --quiet "$AVANT" "$APRES" -- frontend/; then
    echo "▶ build front…"
    ( cd "$APP/frontend" && sudo -u $RUN_AS npm ci --silent && sudo -u $RUN_AS npx vite build --base=/ )
else
    echo "  front inchangé — build sauté"
fi

# --- 5. restart + healthcheck ---
systemctl restart labuse
for i in $(seq 1 30); do
    sleep 2
    if curl -fsS http://127.0.0.1:8000/readyz 2>/dev/null | grep -q '"ready": *true'; then
        echo "✓ [$(date '+%F %T')] deploy OK — $AVANT → $APRES, /readyz ready=true"
        exit 0
    fi
done
echo "✗ /readyz PAS vert 60 s après restart — service à inspecter : journalctl -u labuse -n 100" >&2
echo "  rollback : sudo -u labuse git -C $APP reset --hard $AVANT && sudo /opt/labuse/deploy.sh" >&2
exit 1
