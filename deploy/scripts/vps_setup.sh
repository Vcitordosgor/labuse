#!/usr/bin/env bash
# =============================================================================
# LA BUSE — M7 · préparation du VPS (Ubuntu 24.04) — IDEMPOTENT
# -----------------------------------------------------------------------------
# Exécuté par M7 (utilisateur sudo). Chaque section est relançable sans dégât.
# SSH déjà durci à part (00-labuse-hardening.conf : clés seules, root off).
# ufw N'EST PAS activé ici — protocole dédié (règle SSH d'abord, 2e session
# vérifiée) : deploy/scripts/ufw_setup.sh.
# =============================================================================
set -euo pipefail

echo "── 1. Système à jour + outils de base ──"
sudo DEBIAN_FRONTEND=noninteractive apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -q
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  fail2ban curl git rsync htop unattended-upgrades ca-certificates gnupg

echo "── 2. fail2ban (sshd, défauts sains) ──"
sudo tee /etc/fail2ban/jail.d/labuse.conf > /dev/null <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
sudo systemctl enable --now fail2ban

echo "── 3. Utilisateur applicatif `labuse` (sans shell de login interactif distant) ──"
id labuse >/dev/null 2>&1 || sudo useradd -m -s /bin/bash labuse
sudo mkdir -p /opt/labuse /var/log/labuse /var/backups/labuse /etc/labuse
sudo chown -R labuse:labuse /opt/labuse /var/log/labuse /var/backups/labuse

echo "── 4. PostgreSQL 18 + PostGIS (dépôt PGDG — le dump -Fc 18.x l'exige) ──"
if [ ! -f /etc/apt/sources.list.d/pgdg.list ]; then
  sudo install -d /usr/share/postgresql-common/pgdg
  sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    https://www.postgresql.org/media/keys/ACCC4CF8.asc
  echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    | sudo tee /etc/apt/sources.list.d/pgdg.list
  sudo apt-get update -q
fi
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  postgresql-18 postgresql-18-postgis-3 postgresql-client-18
sudo systemctl enable --now postgresql

echo "── 5. Python 3.12 (natif 24.04) + venv ──"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  python3.12 python3.12-venv python3-pip libpq-dev build-essential proj-data

echo "── 6. Node 22 (NodeSource — aligné sur le poste local) ──"
if ! command -v node >/dev/null || [ "$(node -v | cut -d. -f1)" != "v22" ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q nodejs
fi

echo "── 7. Caddy (TLS auto) — installé, NON activé (mise en service = dernière étape) ──"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
  sudo apt-get update -q
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q caddy
  sudo systemctl stop caddy || true      # pas de service public avant le golden
  sudo systemctl disable caddy || true
fi

echo "✓ VPS prêt : $(psql --version 2>/dev/null | head -1) · $(node -v) · $(python3.12 --version)"
