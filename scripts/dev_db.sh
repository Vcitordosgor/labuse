#!/usr/bin/env bash
# Démarre une PostGIS locale "bare-metal" (Debian/Ubuntu) sans Docker.
# Idempotent : peut être relancé. Nécessite les droits root (apt + cluster pg).
set -euo pipefail

DB_NAME="${DB_NAME:-labuse}"
DB_USER="${DB_USER:-labuse}"
DB_PASS="${DB_PASS:-labuse}"
PG_VER="${PG_VER:-16}"

echo "==> Installation PostGIS (si absent)"
# NB : dpkg-query (sortie minuscule) plutôt que `dpkg -l | grep -q` qui, sous
# `set -o pipefail`, renvoie non-zéro à cause d'un SIGPIPE sur dpkg (faux négatif).
if ! dpkg-query -W -f='${Status}' "postgresql-${PG_VER}-postgis-3" 2>/dev/null | grep -q "ok installed"; then
  export DEBIAN_FRONTEND=noninteractive
  # PPA tierces parfois bloquées (allowlist) : on tolère un update partiel,
  # le paquet PostGIS venant de l'archive principale Ubuntu.
  apt-get update -qq || echo "   (apt-get update partiel — dépôts tiers ignorés)"
  apt-get install -y --no-install-recommends \
    "postgresql-${PG_VER}-postgis-3" "postgresql-${PG_VER}-postgis-3-scripts"
fi

echo "==> Démarrage du cluster PostgreSQL ${PG_VER}"
pg_ctlcluster "${PG_VER}" main start 2>/dev/null || service postgresql start || true
sleep 2

echo "==> Rôle + base + extension PostGIS"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}' SUPERUSER;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "==> Prêt. EPSG métrique La Réunion :"
sudo -u postgres psql -d "${DB_NAME}" -tc \
  "SELECT srid || ' ' || left(srtext, 40) FROM spatial_ref_sys WHERE srid = 2975;"

echo
echo "export LABUSE_DATABASE_URL=postgresql+psycopg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"
