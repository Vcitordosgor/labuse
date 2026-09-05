# CIRCUIT-1 lot 8.1 — CE DOSSIER EST OBSOLÈTE

Les 11 fichiers `deploy/cron.d/*` (abuse, backup, ban, bodacc, dpe, dvf, fraicheur,
notifications, radar, sessions, sitadel) sont l'ANCIEN jeu de crons, celui qui tournait
seul sur le VPS jusqu'à CIRCUIT-1 (constat lot 0.1 : le wrapper n'avait jamais été posé —
`deploy.sh` refusait le fuseau Indian/Reunion).

LE SEUL JEU DÉPLOYÉ est le wrapper : `deploy/cron.d-labuse` (posé par `deploy.sh`, qui
REFUSE désormais de déployer tant qu'un fichier legacy `/etc/cron.d/labuse-*` subsiste —
retrait explicite : `deploy/scripts/retirer_crons_legacy.sh`).

Fichiers conservés en lecture seule pour l'archéologie (aucune table supprimée, aucun
fichier perdu — règle 4). NE PLUS LES POSER.
