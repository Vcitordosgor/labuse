#!/usr/bin/env bash
# =============================================================================
# LA BUSE — OBSOLÈTE (DONNEES-ETAT-FIX-2, Lot 0). NE PLUS UTILISER.
# -----------------------------------------------------------------------------
# Ce script supposait un CLONE GIT sur le VPS (`git pull` dans /opt/labuse/app).
# La prod N'A PAS de clone git : le code part du Mac en rsync. Ce script ne
# tournait donc JAMAIS (il sortait en « n'est pas un clone git »). FIX-1 y avait
# mis par erreur la repose du crontab — déplacée dans le SEUL vrai déploiement :
#
#            deploy/scripts/deploy_app.sh   (à lancer DEPUIS LE MAC)
#
# qui, à chaque passage : rsync code → VPS · venv · front · systemd · REPOSE +
# VÉRIFIE le crontab depuis le registre · met à jour config/deploiement.json.
#
# On garde ce fichier comme PANNEAU : un seul script de déploiement désormais.
# =============================================================================
set -euo pipefail
cat >&2 <<'MSG'
✗ deploy_vps.sh est OBSOLÈTE et ne déploie RIEN (la prod n'a pas de clone git).
  Déploie depuis le Mac :  deploy/scripts/deploy_app.sh labuse-vps
  (rsync + venv + front + systemd + crontab reposé/vérifié + deploiement.json)
MSG
exit 2
