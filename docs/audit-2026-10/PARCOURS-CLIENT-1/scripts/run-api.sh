#!/usr/bin/env bash
# PARCOURS-CLIENT-1 — lance l'API LABUSE en mode AUDIT JOUÉ, single-origin (sert le front buildé
# sous /socle + les pages serveur /login,/invitation,/reset,/moi + l'API JSON), port 5995.
#
# Garanties mandat :
#  - DRY-RUN mail : LABUSE_SMTP_* vidés (override du .env) → mail_configured()=False → rien ne part,
#    tout est journalisé dans mail_queue. BREVO_API_KEY non prefixé → jamais lu par Settings, absent
#    de os.environ (on NE source PAS .env).
#  - AUTH ACTIVE : LABUSE_AUTH_PASSWORD posé → enabled()=True ; login pilote = admin de fait (pas de
#    TOTP), login client = email+argon2id. env=local → cookies non-secure (http localhost OK).
#  - PAS de LABUSE_SECRET_KEY (env=local l'interdirait). PYTHONPATH force le src de CE worktree.
set -euo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
export LABUSE_ENV="local"
export LABUSE_AUTH_PASSWORD="parcours-vic-2026"
# DRY-RUN mail (override .env) — ⚠ config.py appelle load_dotenv(.env, override=False) : toute
# variable NON posée ici serait injectée depuis .env au runtime (invisible à `ps`). Il faut donc
# vider EXPLICITEMENT chaque canal d'envoi, y compris BREVO (mails templatisés du cycle de vie,
# indépendants du SMTP) et STRIPE, sinon les mails/paiements partent POUR DE VRAI.
export LABUSE_SMTP_HOST=""
export LABUSE_SMTP_USER=""
export LABUSE_SMTP_PASSWORD=""
export BREVO_API_KEY=""
export LABUSE_BREVO_API_KEY=""
export LABUSE_STRIPE_SECRET_KEY=""
export STRIPE_RESTRICTED_KEY=""
# éviter les 429 anti-scraping pendant l'audit (autorisé en env=local uniquement) :
export LABUSE_DEV_MODE="1"
# pyproj (dette connue) :
export PROJ_DATA="$HOME/miniforge3/envs/labusedb/share/proj"
# forcer le code de CE worktree :
export PYTHONPATH="$(pwd)/src"

exec /Users/openclaw/Desktop/labuse/.venv/bin/python -m uvicorn labuse.api.app:app \
  --host 127.0.0.1 --port 5995 --no-access-log
