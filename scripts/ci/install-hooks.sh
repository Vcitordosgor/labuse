#!/usr/bin/env bash
# CI-1 (Lot 4) — COMMANDE UNIQUE d'installation du filet local avant envoi.
# Usage :  bash scripts/ci/install-hooks.sh
# Pose core.hooksPath=scripts/git-hooks (hook versionné, partagé par tous les worktrees).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath scripts/git-hooks
chmod +x scripts/git-hooks/pre-push scripts/git-hooks/pre-commit scripts/ci/scan_secrets.sh 2>/dev/null || true
echo "✓ Hooks installés (core.hooksPath=scripts/git-hooks)."
echo "  pre-commit : refuse tout fichier >2 Mio hors liste blanche (garde-fou bloat .git, MENAGE-1)."
echo "  pre-push   : scan de secrets · front (tsc -b + vitest) · tests unitaires Python."
echo "  Objectif < 2 min, sans base. Urgence : git commit/push --no-verify."
echo "  Désinstaller : git config --unset core.hooksPath"
