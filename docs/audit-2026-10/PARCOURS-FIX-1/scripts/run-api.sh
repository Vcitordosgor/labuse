#!/usr/bin/env bash
# PARCOURS-FIX-1 — lance l'API LABUSE sur le BUILD DE PRODUCTION (front buildé servi sous /socle),
# single-origin, port 6005. C'est la chaîne qu'un client voit : on teste le BUILD, pas le dev vite.
#
# ÉTANCHÉITÉ (Lot 1.2, la correction du mandat) : on laisse une FAUSSE BREVO_API_KEY DANS l'env
# EXPRÈS — pour PROUVER que la garde `envoi_reel_autorise` tient : env=local + pas de LABUSE_MAIL_REEL
# → 0 appel réseau, les mails partent en .eml (outputs/mails_dryrun). AUCUN mail réel ne peut partir.
set -euo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
export LABUSE_ENV="local"
export LABUSE_AUTH_PASSWORD="parcours-vic-2026"
# PREUVE d'étanchéité : une clé Brevo bidon est présente ; la garde doit l'ignorer en local.
export BREVO_API_KEY="xkeysib-FAUSSE-CLE-NE-DOIT-JAMAIS-SERVIR-parcoursfix"
# PAS de LABUSE_MAIL_REEL → dry-run étanche. PAS de Stripe.
export LABUSE_STRIPE_SECRET_KEY=""
export STRIPE_RESTRICTED_KEY=""
export LABUSE_MAIL_DRYRUN_DIR="$(pwd)/docs/audit-2026-10/PARCOURS-FIX-1/mails/eml"
export LABUSE_DEV_MODE="1"
export PROJ_DATA="$HOME/miniforge3/envs/labusedb/share/proj"
export PYTHONPATH="$(pwd)/src"

mkdir -p "$LABUSE_MAIL_DRYRUN_DIR"
exec /Users/openclaw/Desktop/labuse/.venv/bin/python -m uvicorn labuse.api.app:app \
  --host 127.0.0.1 --port 6005 --no-access-log
