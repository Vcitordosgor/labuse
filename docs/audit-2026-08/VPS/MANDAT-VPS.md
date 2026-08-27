# MANDAT — VPS : MISE À NIVEAU ET GO-LIVE
Régime AUTONOME du début à la fin. Commits par lot (V1→V8) dans le repo local ; les actions VPS sont journalisées dans docs/audit-2026-08/VPS/JOURNAL.md (chaque commande + résultat). Findings VP-001→. RÈGLES COMMUNES côté local.

## Contexte (établi le 27/08, session SSH de Vic)
Le VPS existe et tourne : OVH VPS-3 (6 vCores, 12 Go RAM, 100 Go, Ubuntu 24.04, Gravelines), accessible en `ssh labuse-vps` (config ~/.ssh/config de Vic, multiplexage actif, ufw rate-limit 6/30s). Déjà en place : PostgreSQL 18.4 + PostGIS (localhost only), Caddy (HTTPS), fail2ban, service systemd `labuse.service` (uvicorn --workers 2, port 8000 local), utilisateur système `labuse`, code dans /opt/labuse/app (PAS un dépôt git — copie de fin juillet), venv /opt/labuse/venv, secrets /etc/labuse/, backups prévus /var/backups/labuse. Base : 431 663 parcelles mais run q_v7_defisc (4 générations de retard), pas de tables dashboard/audit. Rideau basic auth Caddy (décision 22/07) devant toute l'app. Docs de l'époque : DEPLOYMENT_OVH_VPS.md, DEPLOY_RUNBOOK.md (mentionnent Nginx/PG16 — la réalité est Caddy/PG18 : les mettre à jour en V8).

## Doctrine du mandat
- AUCUNE commande destructive sur le VPS sans backup préalable vérifié du même lot.
- La base LOCALE est la référence : le VPS reçoit, jamais l'inverse.
- Chaque étape VPS : commande → résultat → journal. Pas de commande « de mémoire » : celles des docs de juillet peuvent être périmées, vérifier avant d'exécuter.
- Le site ne bascule publiquement (rideau) qu'en toute fin, après recette complète.
- En cas de perte SSH ou d'état incompréhensible : STOP, état des lieux, rapport.

## V1 — ÉTAT DES LIEUX ET FILET
Sur le VPS : inventaire exact (versions, services, contenu /opt/labuse/app — identifier de quel commit la copie date en comparant quelques fichiers marqueurs), espace disque, RAM libre. Backup du VPS actuel : dump de sa base (pg_dump -Fc) + archive de /etc/labuse + Caddyfile → /var/backups/labuse/pre-maj-20260827/. Vérifier le dump (pg_restore --list). Rien ne se fait avant ce filet.

## V2 — LE CODE PASSE SOUS GIT
/opt/labuse/app devient un clone du repo (remote GitHub Vcitordosgor/labuse, main). Préserver ce qui n'est pas versionné (.env locaux, uploads éventuels) : inventorier AVANT (diff copie actuelle vs main), sauver les écarts précieux dans le backup V1, puis remplacer proprement (clone à côté + bascule atomique du chemin, pas de rm -rf aveugle). Le venv : recréé depuis requirements (Python 3.12 du VPS), pas réutilisé à l'aveugle. deploy = git pull + pip install + migrations + restart : écrire le script /opt/labuse/deploy.sh qui fait exactement ça, avec garde (backup auto avant, healthcheck après, rollback documenté).

## V3 — LA BASE MIGRE
Transférer le dump local le plus récent (labuse backup-db --full sur le Mac de Vic AVANT le transfert — nouveau dump du jour, pas celui du 26). scp vers le VPS (attention : gros fichier, connexion Réunion — reprendre avec rsync --partial si coupure). Restaurer dans une base NEUVE (labuse_new) : pg_restore, vérifier (431 663 parcelles, run q_v11_m137 présent en cascade ET p_score_v2_runs, tables dashboard présentes, comptes). Puis bascule atomique : renommer labuse→labuse_old, labuse_new→labuse, redémarrer le service, healthcheck. labuse_old reste 7 jours puis suppression (note au journal). Le fuseau PG session Indian/Reunion (R2) doit être actif — vérifier.

## V4 — LE SERVICE SE MET À NIVEAU
uvicorn --workers 5 (6 vCores, 12 Go — laisser de la marge à PG). Vérifier la RAM sous charge (le dashboard Stripe/monitoring a tué l'uvicorn local 2 fois — surveiller). systemd : Restart=always, limites raisonnables. /readyz vert avec le nouveau code+base. Variables /etc/labuse/labuse.env : compléter avec TOUTES les vars nécessaires au code d'aujourd'hui — Brevo (BREVO_* — le code lit ce préfixe depuis RV-013), STRIPE_RESTRICTED_KEY, IDs templates, et le webhook secret Stripe PROD (whsec_ — Vic devra créer l'endpoint dans le dashboard Stripe : documenter la manip exacte au journal, avec l'URL à saisir). RV-011 : les clés live vs test — en prod, clés LIVE partout, et le noter.

## V5 — SÉCURITÉ D'EXPOSITION
Le rideau basic auth TOMBE (l'auth comptes existe). À la place : rate-limit /login côté Caddy (l'app a le sien — défense en profondeur), 2FA TOTP sur le compte admin (AC-025 : implémenter côté app — enrôlement par QR code au premier login admin, codes de secours, table dédiée, tests), compte admin NOMINATIF pour Vic (le login pilote partagé meurt — AC-020), en-têtes durcis déjà en place via CSP R4 (vérifier qu'ils passent Caddy), HSTS activé au Caddyfile. fail2ban : vérifier qu'il regarde les bons logs (Caddy + app).

## V6 — CRON S'INSTALLE
La table docs/EXPLOITATION-CRON.md (R2) devient réalité : backup quotidien (labuse backup-db vers /var/backups/labuse, rotation 7 j + 4 hebdo, VÉRIFIÉ par pg_restore --list dans le job même), avis-echeance quotidien, purge-sessions, et tout job listé comme « à installer VPS ». Chaque cron : timezone Indian/Reunion, log dans un fichier dédié, test d'exécution manuelle AVANT l'installation au crontab. Le backup DOIT avoir tourné une fois avec succès avant la fin du mandat.

## V7 — RECETTE COMPLÈTE
Derrière le rideau encore fermé (ou via tunnel SSH) : /readyz, login compte réel, carte (tuiles q_v11_m137, cartouche), fiche parcelle 200 avec scores, dashboard admin complet (LED, Stripe live en lecture, sources), export, PDF, Copilote (1 question réelle — ia_budget compte), courrier PDF. Puis LE RIDEAU TOMBE : app.labuse.immo public en HTTPS, certificat valide, la recette rejouée depuis l'extérieur (sans tunnel). Webhook Stripe : l'endpoint prod répond et vérifie la signature (test avec le CLI stripe si dispo, sinon documenter le test manuel à faire par Vic). favicon en place (créer un favicon simple aux couleurs LABUSE si absent du repo).

## V8 — DOCS ET TRANSMISSION
DEPLOYMENT_OVH_VPS.md et DEPLOY_RUNBOOK.md réécrits pour refléter la réalité (Caddy, PG18, workers 5, 2FA, crons, deploy.sh). Une page docs/EXPLOITATION.md : les 10 gestes du quotidien (déployer, backup manuel, restaurer, logs, redémarrer, vérifier les crons, monter un tunnel, gérer le certificat, ajouter une var d'env, que faire si ça tombe). Écrite pour Vic dans 6 mois, pas pour un devops.

## FIN
Critères : app.labuse.immo sert l'app complète en HTTPS avec le code du jour et le run q_v11_m137 · 2FA admin active et testée · backup cron exécuté et vérifié au moins une fois · suite locale toujours verte (aucune régression du code pendant le mandat) · JOURNAL.md complet · rollback documenté à chaque étape critique. Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/vps-golive). Tu ne merges pas. Les secrets ne transitent JAMAIS par le rapport ni par git.
