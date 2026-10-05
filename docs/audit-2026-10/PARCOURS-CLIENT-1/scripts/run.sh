#!/usr/bin/env bash
# Lance un script Playwright du parcours. Usage : ./run.sh vicB.mjs
# Pré-requis : API sur 5995 (run-api.sh) + vite dev sur 8795 (voir RAPPORT §Environnement).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export PW_PKG="${PW_PKG:-/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.js}"
export LABUSE_AUTH_PASSWORD="${LABUSE_AUTH_PASSWORD:-parcours-vic-2026}"
export PARCOURS_BASE="${PARCOURS_BASE:-http://127.0.0.1:8795}"
exec node "$HERE/$1" "${@:2}"
