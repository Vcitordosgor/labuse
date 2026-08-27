#!/usr/bin/env bash
# =============================================================================
# LA BUSE — sauvegarde PostgreSQL (pg_dump quotidien + rotation locale courte)
# -----------------------------------------------------------------------------
# - Dump format custom compressé (pg_dump -Fc), nommage daté.
# - Écrit HORS du dossier applicatif (/var/backups/labuse par défaut).
# - Rotation : ne garde que les N plus récents (défaut 7).
# - Recommandation : pousser ensuite vers OVH Object Storage (voir fin de script).
# - AUCUNE suppression autre que la rotation des dumps datés de CE script.
#
# Usage :   deploy/scripts/backup_postgres.sh
# Cron   :   0 3 * * *  (3h du matin) — voir docs/DEPLOYMENT_OVH_VPS.md §11
# Auth DB :  via ~/.pgpass (chmod 600) ou PGPASSWORD/LABUSE_DB_*.
# =============================================================================
set -euo pipefail

BACKUP_DIR="${LABUSE_BACKUP_DIR:-/var/backups/labuse}"   # JAMAIS dans /opt/labuse/app
KEEP="${LABUSE_BACKUP_KEEP:-7}"                          # nb de dumps conservés
DB="${LABUSE_DB_NAME:-labuse}"
DB_USER="${LABUSE_DB_USER:-labuse}"
DB_HOST="${LABUSE_DB_HOST:-localhost}"
DB_PORT="${LABUSE_DB_PORT:-5432}"

command -v pg_dump >/dev/null || { echo "✗ pg_dump introuvable (postgresql-client-18)"; exit 2; }

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/labuse-${DB}-${TS}.dump"

# VP-002 (mandat VPS 27/08) — dump LEAN : la DATA des tables reconstructibles (dryrun/
# entraînement, ~16 Go, jamais saisies par l'utilisateur) est EXCLUE — schéma conservé,
# données rebâties par ingestion/scoring. Liste = _BACKUP_RECONSTRUCTIBLES de src/labuse/cli.py
# (GB-054) : à faire évoluer ENSEMBLE. Sans ça, 7 dumps quotidiens FULL saturent le disque.
EXCLUDES=""
for t in dryrun_cascade_results cascade_results p_model_dataset p_model_dataset_v2 \
         p_model_dataset_v2bis p_model_ext_dataset p_model_candidates score_snapshot_parcelles; do
    EXCLUDES="$EXCLUDES --exclude-table-data=$t"
done

echo "▶ [$(date '+%F %T')] pg_dump $DB (lean) → $OUT"
# J+2 (incident 22/07 : un échec d'auth laissait un dump de 0 octet, silencieux jusqu'au pull) :
# le fichier raté est SUPPRIMÉ et le script échoue BRUYAMMENT ; un dump vide/illisible ne survit pas.
# shellcheck disable=SC2086 — $EXCLUDES est une liste d'options construite ci-dessus.
if ! pg_dump -Fc --no-owner $EXCLUDES -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB" -f "$OUT"; then
    rm -f -- "$OUT"
    echo "✗ pg_dump A ÉCHOUÉ — dump supprimé, rien de corrompu ne reste" >&2
    exit 1
fi
if [ ! -s "$OUT" ] || ! pg_restore --list "$OUT" >/dev/null 2>&1; then
    rm -f -- "$OUT"
    echo "✗ dump vide ou illisible (pg_restore --list) — supprimé, échec bruyant" >&2
    exit 1
fi
SIZE="$(du -h "$OUT" | cut -f1)"
echo "✓ Sauvegarde OK ($SIZE)"

# --- Rotation : supprime les dumps de CE script au-delà des KEEP plus récents ---
mapfile -t OLD < <(ls -1t "$BACKUP_DIR"/labuse-"${DB}"-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))")
if ((${#OLD[@]})); then
    printf '  rotation : suppression de %d ancien(s) dump(s)\n' "${#OLD[@]}"
    rm -f -- "${OLD[@]}"
fi
echo "  $(ls -1 "$BACKUP_DIR"/labuse-"${DB}"-*.dump 2>/dev/null | wc -l) dump(s) conservé(s) dans $BACKUP_DIR"

# --- Rétention HEBDO (mandat VPS V6) : le dump du dimanche est retenu 4 semaines ---
# Hardlink (zéro octet copié) sous un préfixe hors du glob de la rotation quotidienne ;
# rotation propre à 4 exemplaires. Restauration : mêmes gestes que pour un dump quotidien.
if [ "$(date +%u)" = "7" ]; then
    HEBDO="$BACKUP_DIR/hebdo-labuse-${DB}-${TS}.dump"
    ln "$OUT" "$HEBDO" && echo "  hebdo : $HEBDO retenu (4 semaines)"
    mapfile -t OLDH < <(ls -1t "$BACKUP_DIR"/hebdo-labuse-"${DB}"-*.dump 2>/dev/null | tail -n +5)
    ((${#OLDH[@]})) && rm -f -- "${OLDH[@]}"
fi

# --- Offload Object Storage (À ACTIVER quand le bucket OVH est prêt) ---
# Décommenter après avoir configuré rclone (remote "ovh") ou s3cmd :
#   rclone copy "$OUT" ovh:labuse-backups/ && echo "  ↑ copié vers OVH Object Storage"
# Conserver une rétention plus longue côté Object Storage que la rotation locale.

echo "✓ Restauration : labuse restore-db --file $OUT   (ou pg_restore --clean --no-owner -d $DB $OUT)"
