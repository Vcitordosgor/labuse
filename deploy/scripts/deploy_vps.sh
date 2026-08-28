#!/usr/bin/env bash
# =============================================================================
# LA BUSE — déploiement VPS (git pull + install + build + restart) — MANDAT VPS V2
# -----------------------------------------------------------------------------
# S'exécute SUR LE VPS (avec sudo) : /opt/labuse/deploy.sh
# Pose :  install -o root -g root -m 755 deploy/scripts/deploy_vps.sh /opt/labuse/deploy.sh
#
# Ce que fait chaque déploiement, dans l'ordre, avec garde :
#   0. garde : le clone doit être PROPRE (aucune modif locale) — sinon on refuse, on ne déploie pas
#   1. HYGIÈNE H2 (28/08) — on se place explicitement sur `main` À JOUR (fetch + checkout main +
#      pull --ff-only). Avant, le script déployait la BRANCHE COURANTE : le VPS resté sur
#      feat/vps-golive pouvait « déployer » sans rien changer en affichant un succès (échec
#      silencieux). Désormais : main, toujours ; obstacle → arrêt explicite, jamais « au mieux ».
#      La branche et le commit déployés sont AFFICHÉS avant et après (Vic lit ce qui part en ligne).
#   2. backup automatique de la base (backup_postgres.sh — refuse un dump illisible)
#   3. pip install -e .[ai] dans le venv (dépendances suivent pyproject.toml) + VÉRIF de la version
#      anthropic figée (H1) : si le venv dérive du pin, on ARRÊTE (jamais le mode dégradé silencieux)
#   4. migrations : labuse init-db (schéma additif, CREATE TABLE IF NOT EXISTS — idempotent)
#   5. build front (npm ci + vite build --base=/) SI frontend/ a changé
#   6. restart systemd + healthcheck /readyz (ready=true exigé)
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

DEPLOY_BRANCH="main"   # HYGIÈNE H2 — on déploie TOUJOURS main (jamais la branche courante du clone)
BRANCHE_AVANT="$(sudo -u $RUN_AS git -C $APP branch --show-current)"; BRANCHE_AVANT="${BRANCHE_AVANT:-(HEAD détaché)}"
AVANT="$(sudo -u $RUN_AS git -C $APP rev-parse HEAD)"
echo "▶ [$(date '+%F %T')] deploy — état AVANT : branche $BRANCHE_AVANT @ ${AVANT:0:12}"
echo "  cible : $DEPLOY_BRANCH (origin) — rollback : sudo -u labuse git -C $APP reset --hard $AVANT ; voir en-tête"

# --- 0. garde : clone PROPRE (sinon checkout main échouerait/écraserait EN SILENCE) ---
if [ -n "$(sudo -u $RUN_AS git -C $APP status --porcelain)" ]; then
    echo "✗ le clone $APP est SALE (modifications locales non commitées) — on REFUSE de déployer." >&2
    sudo -u $RUN_AS git -C $APP status --short >&2
    echo "  résous à la main sur le VPS (git -C $APP stash | checkout -- .), puis relance /opt/labuse/deploy.sh." >&2
    exit 3
fi

# --- 1. se placer sur main À JOUR (fetch + checkout + pull --ff-only) ---
sudo -u $RUN_AS git -C $APP fetch origin --prune
if ! sudo -u $RUN_AS git -C $APP checkout "$DEPLOY_BRANCH" 2>/dev/null; then
    echo "✗ impossible de basculer sur $DEPLOY_BRANCH (branche absente en local ou obstacle) — on ARRÊTE." >&2
    echo "  vérifie : sudo -u labuse git -C $APP checkout $DEPLOY_BRANCH" >&2
    exit 3
fi
if ! sudo -u $RUN_AS git -C $APP pull --ff-only origin "$DEPLOY_BRANCH"; then
    echo "✗ pull --ff-only origin $DEPLOY_BRANCH IMPOSSIBLE (divergence, pas un fast-forward) — on ARRÊTE." >&2
    echo "  le clone a peut-être des commits locaux : inspecte sudo -u labuse git -C $APP log --oneline origin/$DEPLOY_BRANCH..HEAD" >&2
    exit 3
fi
APRES="$(sudo -u $RUN_AS git -C $APP rev-parse HEAD)"
echo "▶ [$(date '+%F %T')] déploiement de : branche $DEPLOY_BRANCH @ ${APRES:0:12}"
[ "$AVANT" = "$APRES" ] && echo "  (code déjà à jour — on continue quand même : venv/front/restart)"

# --- 2. filet : backup base AVANT toute migration (échec bruyant = on ne déploie pas) ---
echo "▶ backup pré-déploiement…"
set -a
# le fichier de secrets n'existe que sur le VPS — non suivi au lint (attendu)
# shellcheck disable=SC1091
. /etc/labuse/labuse.env
set +a
sudo -u $RUN_AS --preserve-env=LABUSE_BACKUP_DIR,LABUSE_BACKUP_KEEP,LABUSE_DB_NAME,LABUSE_DB_USER,LABUSE_DB_HOST,LABUSE_DB_PORT \
    "$APP/deploy/scripts/backup_postgres.sh"

# --- 3. dépendances Python (extra [ai] = anthropic : le Copilote en prod appelle le LLM ;
# sans lui, LABUSE_AI_PROVIDER=anthropic tombe en ModuleNotFoundError au 1er /ask) ---
sudo -u $RUN_AS "$VENV/bin/pip" install -q -e "${APP}[ai]"
# HYGIÈNE H1 — garde-fou BRUYANT : la version anthropic installée doit être EXACTEMENT le pin de
# pyproject.toml [ai]. C'est ici que le venv du VPS avait dérivé (1.1.0) → Copilote dégradé SILENCIEUX.
PIN_ANTHROPIC="$(sudo -u $RUN_AS "$VENV/bin/python" -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('$APP/pyproject.toml').read_text()); print(next(s.split('==')[1] for s in d['project']['optional-dependencies']['ai'] if s.startswith('anthropic') and '==' in s))" 2>/dev/null || true)"
VER_ANTHROPIC="$(sudo -u $RUN_AS "$VENV/bin/python" -c "from importlib.metadata import version; print(version('anthropic'))" 2>/dev/null || true)"
if [ -z "$PIN_ANTHROPIC" ]; then
    echo "✗ anthropic n'est pas figé (==) dans pyproject.toml [ai] — on ARRÊTE (le pin est le garde-fou)." >&2
    exit 4
fi
if [ "$VER_ANTHROPIC" != "$PIN_ANTHROPIC" ]; then
    echo "✗ VERSION ANTHROPIC INATTENDUE : installée=$VER_ANTHROPIC, attendue=$PIN_ANTHROPIC (pin pyproject [ai])." >&2
    echo "  C'est l'incident du 27/08 (venv en 1.1.0 → Copilote dégradé SILENCIEUX). On ARRÊTE avant de servir." >&2
    echo "  corrige : sudo -u labuse $VENV/bin/pip install -e '${APP}[ai]' --force-reinstall anthropic==$PIN_ANTHROPIC" >&2
    exit 4
fi
echo "✓ anthropic $VER_ANTHROPIC (== pin pyproject [ai])"

# --- 4. migrations (schéma additif idempotent) ---
sudo -u $RUN_AS --preserve-env=LABUSE_DATABASE_URL "$VENV/bin/labuse" init-db

# --- 5. front (seulement si frontend/ a bougé, ou si dist absent) ---
if [ ! -d "$APP/frontend/dist" ] || ! sudo -u $RUN_AS git -C $APP diff --quiet "$AVANT" "$APRES" -- frontend/; then
    echo "▶ build front…"
    ( cd "$APP/frontend" && sudo -u $RUN_AS npm ci --silent && sudo -u $RUN_AS npx vite build --base=/ )
else
    echo "  front inchangé — build sauté"
fi

# --- 6. restart + healthcheck ---
systemctl restart labuse
for _ in $(seq 1 30); do
    sleep 2
    if curl -fsS http://127.0.0.1:8000/readyz 2>/dev/null | grep -q '"ready": *true'; then
        echo "✓ [$(date '+%F %T')] deploy OK — $AVANT → $APRES, /readyz ready=true"
        exit 0
    fi
done
echo "✗ /readyz PAS vert 60 s après restart — service à inspecter : journalctl -u labuse -n 100" >&2
echo "  rollback : sudo -u labuse git -C $APP reset --hard $AVANT && sudo /opt/labuse/deploy.sh" >&2
exit 1
