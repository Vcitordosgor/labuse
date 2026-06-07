#!/bin/bash
# LA BUSE — SessionStart hook (Claude Code on the web).
# Installe PostGIS + démarre le cluster + crée la base, puis le venv Python.
# Rend le dépôt immédiatement testable (le socle PostGIS est non négociable).
# Idempotent, non-interactif, web-only.
set -euo pipefail

# Web uniquement : en local, on suppose l'environnement déjà prêt.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"

LOG=/tmp/labuse_session_start.log

# 1) PostGIS : installation (si absente) + cluster + base + extension.
if ! bash scripts/dev_db.sh >"$LOG" 2>&1; then
  echo "‼️  Mise en place PostGIS échouée — voir $LOG"
  tail -n 20 "$LOG" || true
  exit 1
fi

# 2) Environnement Python (venv + dépendances + outils de dev).
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip >>"$LOG" 2>&1
.venv/bin/pip install --quiet -e ".[dev]" >>"$LOG" 2>&1

# 3) Variables d'environnement persistées pour la session.
{
  echo "export LABUSE_DATABASE_URL=postgresql+psycopg://labuse:labuse@localhost:5432/labuse"
  echo "export PATH=$PROJECT_DIR/.venv/bin:\$PATH"
} >> "$CLAUDE_ENV_FILE"

echo "✓ LA BUSE prêt : PostGIS démarré (base 'labuse'), venv installé. Tests : pytest"
