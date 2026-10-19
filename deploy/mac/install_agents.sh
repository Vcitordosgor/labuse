#!/usr/bin/env bash
# =============================================================================
# LA BUSE — (ré)installation des 3 agents launchd du Mac HORS DU BUREAU.
# -----------------------------------------------------------------------------
# POURQUOI. macOS (TCC) interdit à launchd de LIRE un script rangé sous ~/Desktop :
# les agents échouent alors en code 126 « Operation not permitted ». On installe
# donc les scripts (et tout ce dont ils dépendent) dans ~/.labuse/ops, qui n'est pas
# protégé, puis on repointe les .plist vers ce dossier et on les recharge.
#
# CE QUE FAIT CE SCRIPT (idempotent, rejouable) :
#   1. crée ~/.labuse/ops et y COPIE les 3 scripts depuis le dépôt (cette copie-ci,
#      sur la branche courante — à lancer depuis un clone à jour de `main`) ;
#   2. vérifie qu'aucun script installé ne lit plus quoi que ce soit sous ~/Desktop ;
#   3. installe les 3 .plist dans ~/Library/LaunchAgents en substituant /Users/VIC → $HOME ;
#   4. décharge puis recharge chaque agent (bootout/bootstrap, repli load -w) ;
#   5. kickstart chacun (sauf --no-kickstart) et affiche la fin de chaque journal.
#
# Les 3 agents :
#   com.labuse.backup-offsite   copie vérifiée des dumps VPS → disque externe du Mac
#   immo.labuse.pull-backups    rapatriement quotidien des dumps VPS → ~/labuse-backups/vps
#   immo.labuse.watch-prod      sentinelle /healthz de la prod toutes les 10 min
#
# DÉPENDANCES EXTERNES (hors ~/Desktop, rien à copier) :
#   · bash/ssh/rsync/curl/shasum/python3/osascript : /usr/bin (PATH launchd minimal) ;
#   · pg_restore ≥ majeure du VPS : $HOME/miniforge3/envs/labusedb/bin (chemin absolu dans les plist) ;
#   · alias ssh `labuse-vps` dans ~/.ssh/config ; secrets watch-prod dans ~/labuse-backups/M7_SECRETS.txt.
#   Les 3 scripts sont du bash autonome : AUCUN venv de projet n'est requis ni lu.
#
# VPS : ce script n'y touche JAMAIS (il ne fait que LIRE les dumps par ssh).
# =============================================================================
set -euo pipefail

KICKSTART=1
[ "${1:-}" = "--no-kickstart" ] && KICKSTART=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPS="$HOME/.labuse/ops"
LA="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"
DOMAIN="gui/$UID_NUM"

# scripts à installer : (source relative au dépôt) → (nom dans ~/.labuse/ops)
SCRIPTS=(
  "deploy/mac/backup_offsite_disque.sh"
  "deploy/scripts/pull_backups.sh"
  "deploy/scripts/watch_prod.sh"
)
# plist (modèles /Users/VIC) → label launchd
PLISTS=(
  "com.labuse.backup-offsite"
  "immo.labuse.pull-backups"
  "immo.labuse.watch-prod"
)

echo "▶ dépôt source : $REPO_ROOT"
case "$REPO_ROOT" in
  "$HOME/Desktop"/*|"$HOME/Desktop") echo "  (source sous ~/Desktop — OK pour l'installation interactive ; les agents, eux, liront ~/.labuse/ops)";;
esac

# ── 1) copie des scripts dans ~/.labuse/ops ─────────────────────────────────────────────────────────
mkdir -p "$OPS"
for rel in "${SCRIPTS[@]}"; do
  src="$REPO_ROOT/$rel"
  [ -f "$src" ] || { echo "✗ introuvable : $src" >&2; exit 1; }
  install -m 0755 "$src" "$OPS/$(basename "$rel")"
  echo "  copié : $OPS/$(basename "$rel")"
done

# ── 2) garde : plus aucune lecture sous ~/Desktop dans les scripts installés ─────────────────────────
if grep -nE '(/Users/[^/]+/Desktop|\$HOME/Desktop|~/Desktop)' "$OPS"/*.sh; then
  echo "✗ un script installé référence encore ~/Desktop (voir ci-dessus) — correction requise." >&2
  exit 1
fi
echo "  garde OK : aucun chemin ~/Desktop dans les scripts installés."

# ── 3) + 4) installation des plist (/Users/VIC → \$HOME) puis rechargement ───────────────────────────
mkdir -p "$LA"
reload_agent() {           # $1 = label ; $2 = plist installé
  local label="$1" plist="$2"
  launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
  if ! launchctl bootstrap "$DOMAIN" "$plist" 2>/dev/null; then
    # repli pour les macOS récalcitrants au bootstrap
    launchctl unload "$plist" 2>/dev/null || true
    launchctl load -w "$plist"
  fi
  launchctl enable "$DOMAIN/$label" 2>/dev/null || true
}

for label in "${PLISTS[@]}"; do
  tmpl="$REPO_ROOT/deploy/mac/$label.plist"
  [ -f "$tmpl" ] || { echo "✗ modèle plist introuvable : $tmpl" >&2; exit 1; }
  dst="$LA/$label.plist"
  sed "s#/Users/VIC#$HOME#g" "$tmpl" > "$dst"
  # garde : le modèle doit bien pointer vers ~/.labuse/ops (jamais ~/Desktop)
  if grep -q "/Desktop/" "$dst"; then
    echo "✗ le plist installé $dst pointe encore vers ~/Desktop." >&2; exit 1
  fi
  echo "  plist → $dst (script = $(/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:1' "$dst" 2>/dev/null))"
  reload_agent "$label" "$dst"
done
echo "✓ 3 agents (ré)installés dans ~/.labuse/ops et rechargés."

# ── 5) kickstart + journaux ──────────────────────────────────────────────────────────────────────────
if [ "$KICKSTART" = 1 ]; then
  echo; echo "▶ kickstart des 3 agents (exécution immédiate) :"
  for label in "${PLISTS[@]}"; do
    launchctl kickstart -k "$DOMAIN/$label" 2>/dev/null || true
    echo "  kickstart $label"
  done
  echo
  echo "Les journaux (la copie disque de 6,9 Go peut tourner plusieurs minutes en tâche de fond) :"
  echo "  tail -f ~/.labuse/backup_offsite_disque.log"
  echo "  tail -f ~/labuse-backups/pull.log"
  echo "  tail -f ~/labuse-backups/watch_prod.log"
fi

# ── Accès complet au disque (seconde garde TCC, propre à la copie sur disque externe) ────────────────
# Sortir les scripts de ~/Desktop lève le « 126 » de LECTURE du script. Mais ÉCRIRE sur un volume
# amovible (/Volumes/…) depuis un contexte launchd réclame en plus « Accès complet au disque » pour
# l'interpréteur /bin/bash — sinon rsync échoue en « mkstemp … Operation not permitted ». C'est un
# réglage macOS qui NE PEUT PAS être posé en ligne de commande (choix utilisateur, Réglages Système).
if [ -d "/Volumes/MUSIQUE-VIDEO" ]; then
  cat <<'FDA'

⚠ COPIE SUR DISQUE EXTERNE — une autorisation macOS à poser UNE fois (sinon rsync = « Operation not permitted ») :
   Réglages Système ▸ Confidentialité et sécurité ▸ Accès complet au disque ▸ +  →  ajouter  /bin/bash
   (afficher les fichiers cachés dans le sélecteur : ⌘⇧. ; puis ⌘⇧G et coller /bin/bash)
   Ouvrir le volet directement :
     open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
   Puis relancer la copie :  launchctl kickstart -k gui/$(id -u)/com.labuse.backup-offsite
   (pull-backups et watch-prod n'écrivent que dans ~/ : eux n'ont besoin de rien de plus.)
FDA
fi
