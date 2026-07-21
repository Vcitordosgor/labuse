#!/usr/bin/env bash
# =============================================================================
# LA BUSE — pare-feu ufw : procédure SÛRE et idempotente (pré-vol M7 · P4)
# -----------------------------------------------------------------------------
# ÉCRIT ici, EXÉCUTÉ le jour J sur le VPS (jamais depuis le poste local).
# Règle d'or anti-lock-out : SSH est autorisé AVANT d'activer quoi que ce soit,
# et `ufw --force enable` n'arrive qu'en DERNIER, après vérification des règles.
#
# Usage (root, sur le VPS) : bash deploy/scripts/ufw_setup.sh [PORT_SSH]
# Idempotent : ufw ignore les règles déjà présentes ; relançable sans risque.
# =============================================================================
set -euo pipefail

SSH_PORT="${1:-22}"

command -v ufw >/dev/null || { echo "✗ ufw absent — apt install ufw"; exit 1; }

# 1) SSH D'ABORD (avec rate-limit anti-bruteforce : 6 conn/30 s max par IP)
ufw limit "${SSH_PORT}/tcp" comment "SSH (rate-limited)"

# 2) HTTP/HTTPS (Caddy/nginx en frontal — l'API 8010 n'est JAMAIS exposée directement)
ufw allow 80/tcp  comment "HTTP (redirect HTTPS)"
ufw allow 443/tcp comment "HTTPS"

# 3) Politique par défaut : tout entrant refusé, tout sortant permis
ufw default deny incoming
ufw default allow outgoing

# 4) Vérification AVANT activation — la liste doit contenir la règle SSH
echo "── Règles en attente ──"
ufw show added
if ! ufw show added | grep -q "${SSH_PORT}/tcp"; then
  echo "✗ ABANDON : la règle SSH ${SSH_PORT}/tcp est absente — activer ufw sans elle = lock-out."
  exit 1
fi

# 5) Activation (le --force évite le prompt interactif ; on a vérifié SSH au-dessus)
ufw --force enable
ufw status verbose
echo "✓ ufw actif — SSH ${SSH_PORT} (limité), 80, 443. L'API/PostgreSQL restent internes."
