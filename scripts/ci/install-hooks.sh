#!/usr/bin/env bash
# CI-1 (Lot 4) — COMMANDE UNIQUE d'installation du filet local avant envoi.
# Usage :  bash scripts/ci/install-hooks.sh
# Pose core.hooksPath=scripts/git-hooks (hook versionné, partagé par tous les worktrees).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath scripts/git-hooks
chmod +x scripts/git-hooks/pre-push scripts/ci/scan_secrets.sh 2>/dev/null || true
echo "✓ Hook pre-push installé (core.hooksPath=scripts/git-hooks)."
echo "  Avant chaque push : scan de secrets · front (tsc -b + vitest) · tests unitaires Python."
echo "  Objectif < 2 min, sans base. Urgence : git push --no-verify."
echo "  Désinstaller : git config --unset core.hooksPath"
