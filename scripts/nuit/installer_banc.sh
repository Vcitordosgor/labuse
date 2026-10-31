#!/usr/bin/env bash
# =============================================================================
# COHERENCE-HOOK-1 — installe l'agent launchd DU BANC DE NUIT (coherence) sur le Mac.
# -----------------------------------------------------------------------------
# Séparé de deploy/mac/install_agents.sh À DESSEIN : ce banc-là LIT le dépôt (tests) sous ~/Desktop,
# ce que la garde stricte d'install_agents.sh refuse (agents de sauvegarde = zéro accès ~/Desktop).
# Le SCRIPT, lui, est copié dans ~/.labuse/ops (hors TCC) ; seul l'ARGUMENT « dépôt » pointe ~/Desktop.
#
#   • copie scripts/nuit/banc_coherence.sh → ~/.labuse/ops/
#   • installe deploy/mac/immo.labuse.banc-coherence.plist → ~/Library/LaunchAgents (/Users/VIC → $HOME)
#   • (re)charge l'agent (bootout/bootstrap)
#
# ⚠ macOS/TCC : comme le job lit ~/Desktop, donner « Accès complet au disque » à /bin/bash (Réglages
#   Système ▸ Confidentialité et sécurité ▸ Accès complet au disque). Sinon « Operation not permitted ».
#
# Usage :   scripts/nuit/installer_banc.sh [REPO_POUR_LE_JOB]   # défaut = ce dépôt (worktree courant)
# =============================================================================
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
JOB_REPO="${1:-$REPO_ROOT}"
OPS="$HOME/.labuse/ops"
LA="$HOME/Library/LaunchAgents"
LABEL="immo.labuse.banc-coherence"
UID_NUM="$(id -u)"; DOMAIN="gui/$UID_NUM"

mkdir -p "$OPS" "$LA" "$HOME/labuse-nuit"
install -m 0755 "$REPO_ROOT/scripts/nuit/banc_coherence.sh" "$OPS/banc_coherence.sh"
echo "  copié : $OPS/banc_coherence.sh"

dst="$LA/$LABEL.plist"
# /Users/VIC → $HOME, puis repointe l'argument « dépôt » vers JOB_REPO (défaut = ce dépôt).
sed -e "s#/Users/VIC#$HOME#g" \
    -e "s#$HOME/Desktop/labuse-hook#$JOB_REPO#g" \
    "$REPO_ROOT/deploy/mac/$LABEL.plist" > "$dst"
echo "  plist → $dst (dépôt du job : $JOB_REPO)"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
if ! launchctl bootstrap "$DOMAIN" "$dst" 2>/dev/null; then
  launchctl unload "$dst" 2>/dev/null || true
  launchctl load -w "$dst"
fi
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true
echo "✓ agent $LABEL (ré)installé — amorçage 19:30 + 20:30 Paris, fenêtre 22:30 Réunion."
echo
echo "Vérifier / tester :"
echo "  launchctl print $DOMAIN/$LABEL | grep -iE 'state|runs'"
echo "  bash $OPS/banc_coherence.sh --force $JOB_REPO   # run immédiat (ignore fenêtre+verrou)"
echo "  tail -f ~/labuse-nuit/coherence-\$(TZ=Indian/Reunion date +%Y-%m-%d).log"
echo
echo "⚠ Donner « Accès complet au disque » à /bin/bash si « Operation not permitted » (lecture ~/Desktop) :"
echo "  open \"x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles\""
