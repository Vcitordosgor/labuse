#!/usr/bin/env bash
# =============================================================================
# SOLIDITE-1 (Lot 3.2) — COPIE DES SAUVEGARDES HORS DU VPS, CHIFFRÉE.
# -----------------------------------------------------------------------------
# Un VPS perdu (feu, suppression, rançongiciel) ne doit pas emporter les sauvegardes.
# Ce script prend le dernier dump local, le CHIFFRE (clé détenue par Vic — le VPS ne peut
# PAS déchiffrer ce qu'il envoie), et le POUSSE vers un stockage objet (rclone). Rétention
# distante : 8 hebdomadaires (en plus des 4 quotidiennes locales de backup_postgres.sh).
#
# Tant que le stockage objet N'EXISTE PAS (compte non fourni par Vic) ou que la clé de
# chiffrement manque : le script S'ARRÊTE PROPREMENT (code 3) et le dit — le job
# `backup-offsite` transforme ce code 3 en une alerte « sauvegarde distante non configurée »
# (rappel, pas une panne). On ne pousse JAMAIS un dump en clair.
#
# Config (dans /etc/labuse/labuse.env) :
#   LABUSE_OFFSITE_REMOTE          remote rclone + bucket, ex. "ovh:labuse-backups"
#   LABUSE_OFFSITE_AGE_RECIPIENT   clé publique age (recommandé)   — OU
#   LABUSE_OFFSITE_GPG_RECIPIENT   destinataire gpg (clé publique importée)
#   LABUSE_OFFSITE_KEEP            nb d'archives distantes gardées (défaut 8)
#   LABUSE_BACKUP_DIR              dossier des dumps (défaut /var/backups/labuse)
# =============================================================================
set -euo pipefail

BACKUP_DIR="${LABUSE_BACKUP_DIR:-/var/backups/labuse}"
DB="${LABUSE_DB_NAME:-labuse}"
REMOTE="${LABUSE_OFFSITE_REMOTE:-}"
AGE_TO="${LABUSE_OFFSITE_AGE_RECIPIENT:-}"
GPG_TO="${LABUSE_OFFSITE_GPG_RECIPIENT:-}"
KEEP="${LABUSE_OFFSITE_KEEP:-8}"

# ── garde « non configuré » : on s'arrête PROPREMENT (code 3), jamais d'envoi en clair ──
if [ -z "$REMOTE" ]; then
    echo "⏸ copie hors-VPS NON configurée : LABUSE_OFFSITE_REMOTE vide (compte stockage objet à fournir par Vic)."
    exit 3
fi
if [ -z "$AGE_TO" ] && [ -z "$GPG_TO" ]; then
    echo "⏸ copie hors-VPS NON configurée : aucune clé de chiffrement (LABUSE_OFFSITE_AGE_RECIPIENT ou _GPG_). On ne pousse pas en clair."
    exit 3
fi
command -v rclone >/dev/null || { echo "✗ rclone absent — à installer sur le VPS (copie hors-VPS)"; exit 2; }

LATEST="$(ls -1t "$BACKUP_DIR"/labuse-"${DB}"-*.dump 2>/dev/null | head -1 || true)"
[ -n "$LATEST" ] || { echo "✗ aucun dump local à copier dans $BACKUP_DIR"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ENC="$TMP/$(basename "$LATEST").enc"

echo "▶ chiffrement de $(basename "$LATEST") …"
if [ -n "$AGE_TO" ]; then
    command -v age >/dev/null || { echo "✗ age absent (chiffrement)"; exit 2; }
    age -r "$AGE_TO" -o "$ENC" "$LATEST"
else
    command -v gpg >/dev/null || { echo "✗ gpg absent (chiffrement)"; exit 2; }
    gpg --batch --yes --trust-model always -r "$GPG_TO" -o "$ENC" --encrypt "$LATEST"
fi
[ -s "$ENC" ] || { echo "✗ chiffrement vide — abandon"; exit 1; }

echo "▶ envoi vers $REMOTE …"
rclone copyto "$ENC" "$REMOTE/$(basename "$ENC")"
echo "✓ copié hors-VPS (chiffré) : $REMOTE/$(basename "$ENC") ($(du -h "$ENC" | cut -f1))"

# ── rétention distante : garder les KEEP archives .enc les plus récentes ──
mapfile -t DISTANTES < <(rclone lsf "$REMOTE" --include "labuse-${DB}-*.dump.enc" 2>/dev/null | sort)
SURPLUS=$(( ${#DISTANTES[@]} - KEEP ))
if (( SURPLUS > 0 )); then
    for i in $(seq 0 $((SURPLUS - 1))); do
        echo "  rétention distante : suppression ${DISTANTES[$i]}"
        rclone deletefile "$REMOTE/${DISTANTES[$i]}" || true
    done
fi
echo "  $(( ${#DISTANTES[@]} > KEEP ? KEEP : ${#DISTANTES[@]} )) archive(s) distante(s) conservée(s)."
