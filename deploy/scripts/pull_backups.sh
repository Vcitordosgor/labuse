#!/usr/bin/env bash
# =============================================================================
# LA BUSE — rapatriement des sauvegardes VPS → poste local (pré-vol M7 · P4)
# -----------------------------------------------------------------------------
# À lancer DEPUIS LE POSTE LOCAL (cron/launchd local) — le VPS ne détient aucun
# credential vers chez nous (sens pull, jamais push). Complète backup_postgres.sh
# (dump quotidien + rotation côté VPS) : sans rapatriement, un VPS perdu = tout perdu.
#
# Usage :  deploy/scripts/pull_backups.sh user@vps-host [DEST_LOCALE]
# Cron local suggéré :  30 7 * * *  (après le backup VPS de 3h)
# Idempotent : rsync ne re-télécharge que le nouveau ; rotation locale N=14.
# =============================================================================
set -euo pipefail

REMOTE="${1:?usage: pull_backups.sh user@vps-host [dest]}"
REMOTE_DIR="${LABUSE_BACKUP_DIR:-/var/backups/labuse}"
DEST="${2:-$HOME/labuse-backups}"
KEEP_LOCAL="${LABUSE_BACKUP_KEEP_LOCAL:-14}"

mkdir -p "$DEST"

# 1) Rapatrier (rsync : delta seulement, préserve les horodatages)
rsync -avz --include="labuse_*.dump" --exclude="*" "${REMOTE}:${REMOTE_DIR}/" "$DEST/"

# 2) Rotation locale (ne touche QUE les dumps datés de ce pipeline)
ls -1t "$DEST"/labuse_*.dump 2>/dev/null | tail -n +$((KEEP_LOCAL + 1)) | xargs -I{} rm -f {}

# 3) Contrôle d'intégrité du plus récent (pg_restore --list ne restaure rien)
LATEST=$(ls -1t "$DEST"/labuse_*.dump 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  if pg_restore --list "$LATEST" >/dev/null 2>&1; then
    echo "✓ rapatrié + intègre : $LATEST ($(du -h "$LATEST" | cut -f1))"
  else
    echo "✗ ALERTE : $LATEST illisible par pg_restore — sauvegarde suspecte." >&2
    exit 1
  fi
else
  echo "✗ aucun dump rapatrié" >&2
  exit 1
fi
