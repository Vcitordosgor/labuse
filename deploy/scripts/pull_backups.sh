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
#
# Rotation locale (OPS-ROTATION-1) : on NE GARDE QUE les N=2 dumps les plus récents
# (6,4 Go/dump → 14 empilés = ~90 Go, c'est ce qui a saturé le disque du Mac).
# Deux garde-fous :
#   · la rotation ne tourne qu'APRÈS un rapatriement RÉUSSI ET un dump vérifié
#     intègre (sinon un pull raté + rotation = on jette les bons dumps) ;
#   · ALERTE si le volume local passe sous LABUSE_DISK_ALERT_GO (défaut 15 Go).
# =============================================================================
set -euo pipefail

REMOTE_DIR="${LABUSE_BACKUP_DIR:-/var/backups/labuse}"
KEEP_LOCAL="${LABUSE_BACKUP_KEEP_LOCAL:-2}"          # garder les 2 plus récents
SEUIL_DISQUE_GO="${LABUSE_DISK_ALERT_GO:-15}"        # alerte si < 15 Go libres

# --- Go libres sur le volume contenant $1 (POSIX, macOS + Linux : df -Pk → Ko) ---
disque_libre_go() {
  df -Pk "$1" | awk 'NR==2 {printf "%d", int($4/1024/1024)}'
}

# --- Alerte disque : stderr + code retour 1 si sous le seuil (ne bloque pas le pull) ---
alerter_disque() {
  local dir="$1" seuil="$2" libre
  libre=$(disque_libre_go "$dir")
  if [ "$libre" -lt "$seuil" ]; then
    echo "⚠ ALERTE DISQUE : ${libre} Go libres sur ${dir} (< ${seuil} Go) — libérer de la place." >&2
    return 1
  fi
  return 0
}

# --- Rotation : ne garde que les $keep dumps les plus récents, supprime le reste ---
#     (process substitution + '|| true' : robuste sous set -e/pipefail même à 0 fichier)
rotation() {
  local dir="$1" keep="$2" f
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    rm -f "$f" && echo "  rotation : supprimé $(basename "$f")"
  done < <(ls -1t "$dir"/labuse*.dump 2>/dev/null | tail -n +$((keep + 1)) || true)
}

main() {
  local REMOTE="${1:?usage: pull_backups.sh user@vps-host [dest]}"
  local DEST="${2:-$HOME/labuse-backups}"
  mkdir -p "$DEST"

  # 0) pré-vol disque — DEPLOY-1027 (OPS-ROTATION-1 durci) : sous le seuil on REFUSE de télécharger,
  #    et le refus S'ÉCRIT AU JOURNAL (stderr → pull.log). Leçon du 24/10 : un pull sur disque plein
  #    échoue en plein rsync (« No space left on device ») et la journée reste sans rapatriement.
  #    Les dumps déjà rapatriés restent intacts (la rotation ne tourne qu'après un pull vérifié).
  if ! alerter_disque "$DEST" "$SEUIL_DISQUE_GO"; then
    echo "✗ REFUS de télécharger : moins de ${SEUIL_DISQUE_GO} Go libres sur ${DEST} — libérer de la place puis relancer." >&2
    exit 1
  fi

  # 1) Rapatrier (rsync : delta seulement, préserve les horodatages)
  rsync -avz --include="labuse*.dump" --exclude="*" "${REMOTE}:${REMOTE_DIR}/" "$DEST/"

  # 2) Contrôle d'intégrité du plus récent AVANT toute suppression (pg_restore --list
  #    ne restaure rien). ⚠ pg_restore doit être >= la majeure du serveur source :
  #    surcharger via PG_RESTORE_BIN si le PATH est vieux.
  local PG_RESTORE LATEST
  PG_RESTORE="${PG_RESTORE_BIN:-pg_restore}"
  LATEST=$(ls -1t "$DEST"/labuse*.dump 2>/dev/null | head -1)
  if [ -z "$LATEST" ]; then
    echo "✗ aucun dump rapatrié" >&2
    exit 1
  fi
  if ! "$PG_RESTORE" --list "$LATEST" >/dev/null 2>&1; then
    echo "✗ ALERTE : $LATEST illisible par pg_restore — sauvegarde suspecte ; " \
         "ROTATION ANNULÉE (anciens dumps conservés)." >&2
    exit 1
  fi
  echo "✓ rapatrié + intègre : $LATEST ($(du -h "$LATEST" | cut -f1))"

  # 3) Rotation SEULEMENT après un rapatriement réussi ET vérifié (garde les N récents)
  rotation "$DEST" "$KEEP_LOCAL"

  # 4) Alerte disque finale (après ménage)
  alerter_disque "$DEST" "$SEUIL_DISQUE_GO" || true
}

# Exécuté uniquement si lancé directement ; `source` (tests unitaires) ne déclenche
# que les définitions de fonctions, pas le rapatriement.
if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  main "$@"
fi
