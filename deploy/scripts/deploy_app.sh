#!/usr/bin/env bash
# =============================================================================
# LA BUSE — M7 · déploiement applicatif — À LANCER DEPUIS LE MAC (idempotent)
# -----------------------------------------------------------------------------
# Le VPS ne détient AUCUN credential git : le code part du poste local en rsync
# (l'état de la branche déployée), sans .git ni artefacts. Relançable à volonté.
# Usage : deploy/scripts/deploy_app.sh [hôte-ssh=labuse-vps]
# =============================================================================
set -euo pipefail
HOST="${1:-labuse-vps}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"

echo "── 1. Code → ${HOST}:/opt/labuse/app (rsync, sans secrets ni artefacts) ──"
rsync -a --delete \
  --exclude .git --exclude .venv --exclude node_modules --exclude frontend/dist \
  --exclude qa/captures --exclude exports --exclude "__pycache__" --exclude "*.pyc" \
  --exclude .pytest_cache --exclude reports \
  "$REPO/" "$HOST":/tmp/labuse-app-sync/
ssh -o BatchMode=yes "$HOST" 'sudo rsync -a --delete /tmp/labuse-app-sync/ /opt/labuse/app/ && sudo chown -R labuse:labuse /opt/labuse/app'

echo "── 2. venv + dépendances (sur le VPS, en labuse) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "
  cd /opt/labuse
  [ -d venv ] || python3.12 -m venv venv
  ./venv/bin/pip install -q --upgrade pip
  ./venv/bin/pip install -q -e ./app
  ./venv/bin/python -c \"import labuse; print(\\\"labuse importable ✓\\\")\"
"'

echo "── 3. Front (dist se CONSTRUIT sur le VPS, ne se copie pas) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "
  cd /opt/labuse/app/frontend
  npm ci --silent
  VITE_RUN_LABEL=\${VITE_RUN_LABEL:-q_v7_defisc} npx vite build 2>&1 | tail -1
"'

echo "── 4. systemd (unit versionnée) ──"
ssh -o BatchMode=yes "$HOST" 'sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload'

echo "✓ déployé — reste : /etc/labuse/labuse.env (secrets), systemctl enable --now labuse"
