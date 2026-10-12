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

echo "── 1. Code → ${HOST}:/opt/labuse/app (rsync DIRECT via sudo distant, sans transit /tmp) ──"
# DISQUE-VPS-1 — on n'envoie QUE l'utile (cf. docs/audit-2026-10/DISQUE-VPS-1.md) :
#   · rsync écrit DIRECTEMENT dans /opt/labuse/app via --rsync-path="sudo rsync" (plus de
#     /tmp/labuse-app-sync : économise ~11 Go temporaires sous /tmp à chaque déploiement) ;
#   · exclusions ANCRÉES (préfixe / = racine du transfert) des SOURCES d'ingestion brutes (jamais
#     lues au runtime ni par un cron — ingérées une fois en base), de docs/ (barrière jouée côté Mac),
#     et des artefacts de dev (qa/captures/audit_shots/tests/reports) ;
#   · les exclusions PROTÈGENT AUSSI du --delete les caches/sorties écrits SUR le VPS
#     (data/plu_reglements, data/ortho_tiles, data/ban régénéré par cron, outputs/) — à ne pas écraser.
#   · ⛔ ÉTAT SERVI (config/served_manifest.json + served_run.txt) JAMAIS expédié : c'est le POINTEUR
#     de bascule, propre à la prod (écrit par la bascule seule). Incident 13/10 : le manifeste local
#     (q_v18) rsync'd ici a basculé prod sur un run sans données → /readyz=false. Exclu définitivement.
rsync -a --delete --rsync-path="sudo rsync" \
  --exclude .git --exclude .venv --exclude node_modules --exclude frontend/dist \
  --exclude "__pycache__" --exclude "*.pyc" --exclude .pytest_cache --exclude /exports \
  --exclude /reports --exclude /qa --exclude /captures --exclude /audit_shots \
  --exclude /tests --exclude /docs --exclude /outputs \
  --exclude /data/cosia --exclude /data/ortho_irc --exclude /data/ortho_tiles \
  --exclude /data/rgealti --exclude /data/dvf_histo --exclude /data/ml \
  --exclude /data/insee_rp --exclude /data/ban --exclude /data/edf_hta \
  --exclude /data/tcsp --exclude /data/dvf --exclude /data/plu_reglements \
  --exclude /config/served_manifest.json --exclude /config/served_run.txt \
  "$REPO/" "$HOST":/opt/labuse/app/
ssh -o BatchMode=yes "$HOST" 'sudo chown -R labuse:labuse /opt/labuse/app'

echo "── 2. venv + dépendances (sur le VPS, en labuse) ──"
# Import-smoke de la CHAÎNE DE DÉMARRAGE (pas juste `import labuse`) : app servie + comptes +
# tenant + events. Une dépendance cœur manquante (ex. argon2-cffi absent → comptes KO → cloison
# non matérialisée EN SILENCE) fait ÉCHOUER LE DÉPLOIEMENT ICI, avant tout restart. set -e propage.
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "
  set -e
  cd /opt/labuse
  [ -d venv ] || python3.12 -m venv venv
  ./venv/bin/pip install -q --upgrade pip
  # PROPRETE-FIX-0 — dépendances CŒUR depuis le VERROU (versions testées, CVE corrigées), puis
  # le paquet lui-même en éditable SANS re-résoudre (--no-deps : le closure vient du lock).
  ./venv/bin/pip install -q -r ./app/requirements.lock
  ./venv/bin/pip install -q -e ./app --no-deps
  ./venv/bin/python -c \"import labuse.api.app, labuse.comptes, labuse.api.tenant, labuse.api.events; print(\\\"chaîne de démarrage importable ✓\\\")\"
"'

echo "── 3. Front (dist se CONSTRUIT sur le VPS, ne se copie pas ; --base=/ : Caddy le sert à la RACINE) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u labuse bash -c "
  cd /opt/labuse/app/frontend
  npm ci --silent
  VITE_RUN_LABEL=\${VITE_RUN_LABEL:-q_v7_defisc} npx vite build --base=/ 2>&1 | tail -1
"'

echo "── 4. systemd (unit versionnée) ──"
ssh -o BatchMode=yes "$HOST" 'sudo install -o root -g root -m 644 /opt/labuse/app/deploy/systemd/labuse.service /etc/systemd/system/labuse.service
sudo systemctl daemon-reload'

echo "✓ déployé — reste : /etc/labuse/labuse.env (secrets), systemctl enable --now labuse"
