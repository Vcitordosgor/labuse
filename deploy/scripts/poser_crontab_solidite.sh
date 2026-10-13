#!/usr/bin/env bash
# =============================================================================
# SOLIDITE-1 — POSE CIBLÉE du crontab (JAMAIS deploy.sh, qui régénère tout et effacerait le
# gel DVF + les 6 jobs commentés). Ce script touche UNIQUEMENT :
#   · MAILTO=root → MAILTO=""   (fin du mail cron vers le vide) ;
#   · ajoute 3 lignes si absentes : recap-matin, backup-offsite, verite-sources.
# Tout le reste (PATH, jobs commentés, absence de ingest-dvf/ingest-ban = gel DVF) est PRÉSERVÉ.
# IDEMPOTENT : relançable sans dégât (n'ajoute pas deux fois, ne retire rien).
#
# ⚠ PRÉREQUIS : le CODE doit être déployé d'abord (jobs recap-matin/backup-offsite/verite-sources
#   doivent exister : `labuse jobs list | grep recap-matin`). Sinon ces crons échoueraient.
#
# À lancer SUR LE VPS :  sudo bash deploy/scripts/poser_crontab_solidite.sh [--apply]
#   sans --apply : DRY-RUN (montre le diff, ne touche rien).
# =============================================================================
set -euo pipefail
CRON=/etc/cron.d/labuse
APPLY=0; [ "${1:-}" = "--apply" ] && APPLY=1

[ -f "$CRON" ] || { echo "✗ $CRON introuvable"; exit 1; }
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
cp "$CRON" "$TMP"

# 1) MAILTO vide (idempotent)
sed -i 's/^MAILTO=root$/MAILTO=""/' "$TMP"

# 2) ajouter les 3 blocs SI recap-matin n'y est pas déjà
if ! grep -q "jobs run recap-matin'" "$TMP"; then
  cat >> "$TMP" <<'EOF'

# SOLIDITE-1 — ajouts ciblés (recap-matin, backup-offsite, verite-sources)
# quotidien · 07:30 Réunion · exploitation — Récapitulatif d'exploitation du matin (un seul mail : vert, ou la liste des soucis)
30 7 * * *   labuse  sh -c '. /etc/labuse/labuse.env; exec labuse jobs run recap-matin'

# hebdo (dim) · 14:30 dim Réunion · exploitation — Copie chiffrée de la dernière sauvegarde hors du VPS (stockage objet)
30 14 * * 0   labuse  sh -c '. /etc/labuse/labuse.env; exec labuse jobs run backup-offsite'

# mensuel (15) · 06:00 le 15 Réunion · exploitation — Vérité sources — 20 parcelles confrontées aux sources officielles
0 6 15 * *   labuse  sh -c '. /etc/labuse/labuse.env; exec labuse jobs run verite-sources'
EOF
fi

echo "── DIFF $CRON → proposé ──"
diff -u "$CRON" "$TMP" || true
if [ "$APPLY" = 0 ]; then
  echo; echo "DRY-RUN. Relancer avec --apply pour poser (après avoir déployé le code)."
  exit 0
fi

# garde prérequis : les 3 jobs doivent exister dans le code déployé
# (le CLI exige labuse.env + cwd app — sinon il échoue au chargement et la garde refuse à tort).
JOBS_LIST="$(sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env 2>/dev/null; set +a; cd /opt/labuse/app && /opt/labuse/venv/bin/labuse jobs list 2>/dev/null')"
for j in recap-matin backup-offsite verite-sources; do
  printf '%s\n' "$JOBS_LIST" | grep -q "^$j " \
    || { echo "✗ REFUS : le job « $j » n'existe pas dans le code déployé — déployer le code d'abord."; exit 1; }
done

install -o root -g root -m 644 "$TMP" "$CRON"
echo "✓ crontab posé. (cron relit /etc/cron.d automatiquement.)"
