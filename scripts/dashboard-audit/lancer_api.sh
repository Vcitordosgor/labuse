#!/usr/bin/env bash
# DASHBOARD-AUDIT-1 — lance l'API du worktree pour rejouer l'audit (LECTURE SEULE).
# L'env conda `labusedb` du poste n'a plus d'interpréteur Python : on emprunte le venv du
# worktree principal, mais on force le `src/` de CE worktree en tête de PYTHONPATH pour servir
# le code d'origin/main audité. LABUSE_JOBS_STATE_DIR pointe l'état réel des jobs (le worktree
# d'audit a un dossier d'état vide → sinon la page Horloge afficherait "jamais" partout).
set -euo pipefail
cd "$(dirname "$0")/../.."
PORT="${1:-5965}"
PYBIN="${PYBIN:-$HOME/Desktop/labuse/.venv/bin/python}"
exec env \
  PYTHONPATH="$PWD/src" \
  LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
  PROJ_DATA="$HOME/miniforge3/envs/labusedb/share/proj" \
  LABUSE_JOBS_STATE_DIR="$HOME/Desktop/labuse/.local/state/jobs" \
  "$PYBIN" -m uvicorn labuse.api.app:app --host 127.0.0.1 --port "$PORT"
