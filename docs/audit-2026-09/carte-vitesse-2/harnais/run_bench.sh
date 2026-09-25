#!/usr/bin/env bash
# CARTE-VITESSE-2 — orchestre la mesure avant/après. Redémarre l'API pour un vrai froid (LRU vide).
# Usage : run_bench.sh <label>        # ex: avant | apresA | apresB | final
set -u
LABEL="${1:?label requis}"
ROOT="/Users/openclaw/Desktop/labuse-carte2"
VENV="/Users/openclaw/Desktop/labuse/.venv"
PORT=8495
export CHROME_BIN="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
export BASE="http://127.0.0.1:$PORT"
BENCH="$ROOT/docs/audit-2026-09/carte-vitesse-2/harnais/bench.mjs"

start_api() {
  lsof -ti :$PORT 2>/dev/null | xargs kill 2>/dev/null; sleep 1
  ( cd "$ROOT" && source "$VENV/bin/activate" && PYTHONPATH="$ROOT/src" LABUSE_ENV=local \
    LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
    uvicorn labuse.api.app:app --host 127.0.0.1 --port $PORT --workers 1 >/tmp/cv2_api.log 2>&1 & )
  for i in $(seq 1 40); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/socle/" 2>/dev/null)
    [ "$code" = "200" ] && { echo "API prête ($i)"; return 0; }
    sleep 0.5
  done
  echo "API PAS PRÊTE"; tail -5 /tmp/cv2_api.log; return 1
}
stop_api() { lsof -ti :$PORT 2>/dev/null | xargs kill 2>/dev/null; sleep 1; }

# FROID : 3 redémarrages (LRU serveur vide + contexte navigateur neuf) → médiane
for run in 1 2 3; do
  start_api || exit 1
  LABEL="$LABEL" MODE=cold node "$BENCH"
  stop_api
done
# CHAUD : 1 démarrage, échauffement + 3 passes réutilisant le cache
start_api || exit 1
LABEL="$LABEL" MODE=warm PASSES=3 node "$BENCH"
stop_api
echo "=== bench '$LABEL' fini ==="
