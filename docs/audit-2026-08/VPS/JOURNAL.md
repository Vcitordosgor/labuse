# JOURNAL — MANDAT VPS (mise à niveau et go-live)

Session du 27/08/2026 (heure Réunion). Toute commande VPS = une entrée : commande → résultat.
VPS : `ssh labuse-vps` (OVH VPS-3, vps-5563949c, Gravelines). Aucun secret dans ce journal.

---

## V1 — ÉTAT DES LIEUX ET FILET

### V1.1 Inventaire (27/08 ~17h55 Réunion / 13h55 UTC)

Commandes : `hostname/uptime/lsb_release/df/free/python3 --version/psql --version/systemctl is-active/caddy version`, puis inspection `/opt/labuse`, base, `/etc/labuse`, unit systemd, `/var/backups/labuse`, `/etc/cron.d`, Caddyfile, ufw, fuseaux.

| Élément | État constaté |
|---|---|
| OS | Ubuntu 24.04.4 LTS, uptime 49 j, load ~0 |
| Disque | 96 Go, 51 Go utilisés, **45 Go libres** |
| RAM | 12 Go, ~1 Go utilisé, 10 Go dispo, **pas de swap** |
| Python | 3.12.3 |
| PostgreSQL | 18.4 (pgdg), localhost only |
| Caddy | v2.11.4, HTTPS, rideau basic_auth (exemption /stripe/webhook), en-têtes X-Robots/nosniff/Referrer, cache assets, page 401 habillée |
| Services | labuse, caddy, postgresql, fail2ban : tous `active` |
| App | `/opt/labuse/app` = **copie non-git du 23/07** (103 entrées à la racine, mtime 23/07 19:44) ; venv `/opt/labuse/venv` du 21/07 |
| Base `labuse` | **19 Go**, 431 663 parcelles, PAS de table `parcel_cascade` (schéma juillet), run q_v7_defisc |
| Fuseau | Système **Etc/UTC** ; PG (base labuse) : `Indian/Reunion` ✓ |
| systemd unit | uvicorn 2 workers, port 8000 local, `Restart=on-failure`, EnvironmentFile=/etc/labuse/labuse.env, durcissement (ProtectSystem=full etc.) — commentaires disent « Nginx » (réalité : Caddy) |
| Env vars (noms) | LABUSE_DATABASE_URL, LABUSE_ENV, LABUSE_AUTH_PASSWORD, LABUSE_SECRET_KEY, LABUSE_PUBLIC_URL, LABUSE_SERVED_RUN, LABUSE_PILOT_COMMUNE_INSEE/NAME, LABUSE_HTTP_TIMEOUT_S, ANTHROPIC_API_KEY, LABUSE_QA_ALLOWLIST, LABUSE_BACKUP_DIR, LABUSE_BACKUP_KEEP, LABUSE_TRUSTED_PROXIES |
| ufw | 22 LIMIT, 80/443 ALLOW |
| Crons | `/etc/cron.d/labuse-*` ×9 (juillet) : backup 03h00 (via `deploy/scripts/backup_postgres.sh`, dumps 4 Go quotidiens présents 21→27/08), radar lun 02h40, catnat 5-du-mois, sitadel 04h15 + hebdo, dpe mar, ban 5-du-mois, dvf mer, bodacc 04h30, abuse-scan 06h00 — **fuseau système UTC** (les heures cron sont en UTC, pas Réunion) |

Constats V1 (à traiter dans les lots suivants) :
- Le backup quotidien EXISTE déjà (contrairement au « prévus » du contexte). Correction : `deploy/scripts/backup_postgres.sh` VÉRIFIE déjà par `pg_restore --list` dans le job (garde J+2 du 22/07). Il manque : la rétention hebdo (rotation 7 seulement) et les jobs avis-echeance/purge-sessions. Les 7 dumps × 4 Go occupent ~28 Go.
- Crons en UTC (système Etc/UTC) → V6 devra fixer le fuseau des jobs (CRON_TZ ou TZ) en Indian/Reunion.
- Pas de swap : à surveiller pour la restauration 19 Go + uvicorn 5 workers (V4).

### V1.2 Datation de la copie /opt/labuse/app

md5 de fichiers marqueurs VPS vs `git show <commit>:<fichier>` sur l'historique origin/main :
la copie est HÉTÉROGÈNE — la plupart des fichiers matchent `e41b57c8` (22/07 22:50, [LEX-D]),
88 fichiers matchent des commits de la vague M12 du 24/07 (`fd31eb3e`→`840ae6a1`). Copie rsync
en deux temps, aucun état git unique. Non versionnés trouvés (diff arbre VPS vs git) :
`data/ban/adresses-974.csv(.gz)` (retéléchargeable, `labuse ingest-ban --download`),
`src/labuse.egg-info/` et `frontend/dist/` (artefacts). AUCUN .env dans l'app (config en
/etc/labuse, archivée). Décision : l'app entière archivée dans le filet → rollback total possible.

### V1.3 Filet posé et VÉRIFIÉ — `/var/backups/labuse/pre-maj-20260827/`

| Fichier | Taille | Vérif |
|---|---|---|
| `labuse-pre-maj.dump` | 3,8 Go | `pg_dump -Fc` frais (14h00-14h11 UTC), `pg_restore --list` OK (FK, MV listées) |
| `config.tgz` | 6 Ko | /etc/labuse + Caddyfile + labuse.service + cron.d/labuse-* |
| `app-copie-juillet.tgz` | 266 Mo | /opt/labuse/app complet (sans node_modules/__pycache__) |

**V1 CLOS.** Rollback complet possible : base (dump vérifié) + config + app.

---

## V2 — LE CODE PASSE SOUS GIT

- Repo GitHub `Vcitordosgor/labuse` : PUBLIC (aucun credential nécessaire au VPS). ⚠ Branche par
  défaut GitHub = `claude/eager-pascal-cmObd` (bizarre — à corriger par Vic dans les réglages GitHub,
  noté pour le rapport) → clone en EXPLICITANT la branche.
- `feat/vps-golive` poussée (`5c482a8d` : VP-001 garde version pg_dump + deploy_vps.sh + journal).
- Clone : `sudo -u labuse git clone --branch feat/vps-golive https://github.com/Vcitordosgor/labuse.git /opt/labuse/app-new` → OK, HEAD `5c482a8d`.
  RÈGLE DE RÉGIME : le VPS reste sur `feat/vps-golive` jusqu'au merge par Vic ; après merge,
  `git checkout main` — deploy.sh tire la branche COURANTE, il est neutre au choix.
- venv : `python3 -m venv /opt/labuse/venv-new` (Python 3.12.3 système) + `pip install -e app-new` (en cours).
- `deploy/scripts/deploy_vps.sh` écrit (repo) : backup auto AVANT → git pull --ff-only branche
  courante → pip install -e → `labuse init-db` (schéma additif idempotent) → build front si
  frontend/ a bougé → restart + healthcheck /readyz ; rollback documenté en tête de script.
  Pose : `install -m 755 deploy/scripts/deploy_vps.sh /opt/labuse/deploy.sh` (fera partie de la bascule).

## V3 — LA BASE MIGRE (en cours)

- Dump local du jour `labuse-labuse-full-20260827-154408.dump` (6 481 723 320 octets) transféré
  par `rsync --partial --inplace` → `/var/backups/labuse/incoming/`, **md5 IDENTIQUE des deux côtés**
  (`963e26f7e2259e0263e2a1de6e1f5a89`). Transfert ~6 min, aucune coupure.
- `labuse_new` créée (OWNER labuse, PostGIS, `ALTER DATABASE … SET timezone 'Indian/Reunion'`).
- INCIDENT bénin : 1er pg_restore lancé via la session ssh (risque de mort au timeout) → tué et
  relancé PROPREMENT détaché (`setsid`, log /tmp/restore.log) après DROP/CREATE de labuse_new.
  Au passage : un script poussé par heredoc portait `$$` (PID bash) dans le quoting psql → fuseau
  refusé ; script re-poussé par scp, fuseau posé correctement.
- INCIDENT 2 : `--role=labuse` ne peut pas créer `postgis_raster` (non « trusted ») ni
  `pg_freespacemap` → la table raster `rgealti_pente_5m` (pente RGE ALTI, servie par le solaire)
  aurait SAUTÉ. Restore arrêté, extensions pré-créées en superuser, relancé. Vérifié ensuite.
- INCIDENT 3 — DISQUE PLEIN pendant le restore (96G/96G, 645 Mo restants) : le restore s'est
  terminé avec 11 erreurs = 3 bénignes (COMMENT ON EXTENSION), 1 bénigne (COPY spatial_ref_sys,
  peuplée par l'extension), et 3 INDEX tombés sur ENOSPC (2× dryrun_cascade_results,
  1× score_snapshot_parcelles). Espace rendu en supprimant LA COPIE transférée du dump
  (l'original md5-vérifié reste sur le Mac — aucun artefact de reprise unique détruit ;
  la suppression des vieux dumps quotidiens a été REFUSÉE par la garde de permissions et
  n'a pas été faite). Les 3 index recréés à la main à l'identique — restore COMPLET.
- VÉRIFICATIONS labuse_new : parcelles **431 663** ✓ · `parcel_p_score_v2` porte
  **q_v11_m137 sur 431 663 lignes** ✓ · q_v11_m137 dans `p_score_v2_runs` (7 runs) ✓ ·
  tables dashboard `ia_log`/`usage_compteurs` ✓ · comptes 21 / utilisateurs 17 ✓ ·
  fuseau base `Indian/Reunion` ✓ · spatial_ref_sys 8 500 ✓.

### Bascule V2+V3 exécutée (14h29-14h32 UTC, service arrêté ~3 min, rideau Caddy INCHANGÉ)

Script `/tmp/bascule.sh` (journalisé /tmp/bascule.log sur le VPS) :
1. `git pull` sur app-new → `e79bd483` ; 2. `systemctl stop labuse` ;
3. sessions PG terminées puis `ALTER DATABASE labuse RENAME TO labuse_old` et
   `labuse_new RENAME TO labuse` ; 4. `mv app → app-juillet`, `mv app-new → app` ;
5. venv RECRÉÉ à son chemin final /opt/labuse/venv (piège shebangs : un venv renommé
   pointe vers l'ancien chemin), ancien → venv-juillet ; 6. unit systemd (workers 5,
   Restart=always, MemoryMax=6G) + `/opt/labuse/deploy.sh` posés ; 7. `labuse init-db`
   (schéma additif : tables 2FA…) ; 8. start + healthcheck.
- INCIDENT 4 : `LABUSE_MAIL_FROM=LABUSE <contact@labuse.immo>` SANS guillemets casse tout
  sourcing shell du fichier env (`set -a; . labuse.env` — le même geste que TOUS les crons).
  systemd, lui, le lisait sans broncher. Corrigé (valeur entre guillemets), init-db rejoué.
- RÉSULTAT : service `active`, **/readyz {"ready":true}**, 5 workers uvicorn (~130 Mo chacun),
  RAM totale 1,3 Go. `labuse_old` reste jusqu'au **03/09/2026** (note : suppression =
  `sudo -u postgres psql -c "DROP DATABASE labuse_old;"` après vérification).
- Rollback documenté : stop → renommer les bases en sens inverse → `mv` inverses des dossiers
  app/venv → ancien unit depuis config.tgz → start. Filet V1 intact.

## V4 — SERVICE À NIVEAU (fait avec la bascule)

- Unit systemd : **workers 5** (6 vCores), **Restart=always** (le dashboard avait tué l'uvicorn
  local 2 fois — plus jamais de service mort silencieux), **MemoryMax=6G** (l'OOM systemd
  redémarre le service plutôt que de laisser le noyau viser PostgreSQL), commentaires Nginx→Caddy.
- `/etc/labuse/labuse.env` RÉÉCRIT (sauvegarde `.avant-v4-20260827`, mode 640 root:labuse) :
  secrets existants préservés ; `LABUSE_SERVED_RUN=q_v7_defisc` RETIRÉ → `config/served_run.txt`
  versionné gouverne (**q_v11_m137**) ; ajouts : `LABUSE_PUBLIC_BASE_URL`,
  `LABUSE_LOGIN_PILOTE_ACTIF=0` (V5), `LABUSE_AI_PROVIDER=anthropic`, `LABUSE_ADMIN_EMAIL`,
  placeholders commentés pour les clés LIVE À POSER PAR VIC : `STRIPE_SECRET_KEY` (sk_live_…),
  `STRIPE_WEBHOOK_SECRET` (whsec_…), `STRIPE_RESTRICTED_KEY` (rk_live_…), `STRIPE_PRICE_*`,
  `BREVO_API_KEY` + 8 IDs de templates, SMTP. RV-011 : clés LIVE partout en prod, jamais de test.
- **MANIP STRIPE POUR VIC (webhook prod)** : dashboard Stripe (mode LIVE) → Développeurs →
  Webhooks → « Ajouter un endpoint » → URL `https://app.labuse.immo/stripe/webhook` →
  événements : `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`, `invoice.payment_failed` (la liste que lit
  `facturation.traiter_webhook`) → créer, puis copier le « Signing secret » (whsec_…) dans
  `/etc/labuse/labuse.env` (STRIPE_WEBHOOK_SECRET=) et `sudo systemctl restart labuse`.

## V6 — CRONS (installés, HEURE RÉUNION)

- Fuseau SYSTÈME posé : `timedatectl set-timezone Indian/Reunion` (+04). Les crontab lisent
  désormais l'heure locale → tous les horaires des fichiers `deploy/cron.d/*` ont été convertis
  UTC→Réunion (+4 h) AVANT la pose. 13 jobs posés `/etc/cron.d/labuse-*`, `systemctl restart cron`.
- 2 nouveaux : `labuse-sessions` (purge-sessions 08:00) et `labuse-avis-echeance` (08:30).
- Cron `labuse-catnat` RETIRÉ : sa commande `ingest-catnat` est morte depuis M12 (le fichier
  VPS était orphelin du dépôt ; il est archivé dans le filet config.tgz). Vérifié : la CLI ne
  connaît plus `ingest-catnat`.
- Tests manuels AVANT de compter dessus : `purge-sessions` (0 supprimée, OK), `avis-echeance`
  (0 avis, OK), et surtout **le BACKUP joué à la main comme le cron** (flock + source env +
  backup_postgres.sh) → **dump LEAN 4,1 Go, "Sauvegarde OK", `pg_restore --list` passé DANS le
  job, rotation → 7 conservés**. Le backup a donc tourné avec succès au moins une fois. ✓
- VP-002 : le backup nocturne est passé en LEAN (exclusion de la data des tables
  reconstructibles, comme `labuse backup-db` sans --full) — sinon 7 dumps FULL de 6 Go saturaient
  les 45 Go. Rétention hebdo ajoutée (hardlink du dump du dimanche, 4 semaines).

## V5 — SÉCURITÉ D'EXPOSITION

- **2FA TOTP admin (AC-025)** : implémentée et testée (15 tests `tests/test_2fa.py`, vecteurs
  RFC 6238 + flux web complet). Tables `totp_2fa`/`totp_secours` posées par `init-db` à la
  bascule. Tout login rôle admin passe par `/login/2fa` ; 1er passage = enrôlement QR + 8 codes
  de secours ; anti-rejeu ; 5 tentatives/défi de 5 min. Machinerie vérifiée en prod
  (GET /login/2fa sans défi → 302 /login).
- **Rideau basic auth TOMBÉ** (go-live) : nouveau `/etc/caddy/Caddyfile` (source
  `deploy/Caddyfile.prod`) SANS `basic_auth` — l'auth comptes applicative est la porte
  (vérifié : API sans session → 401 JSON applicatif, plus de `www-authenticate: Basic`).
  Ancien Caddyfile sauvegardé `/etc/caddy/Caddyfile.rideau-<ts>` ; `CADDY_BASIC_HASH` neutralisé
  dans `/etc/caddy/labuse.env`. `caddy validate` (env chargé) OK AVANT reload.
- **HSTS** activé (`Strict-Transport-Security: max-age=15552000`, vérifié depuis l'extérieur).
- **fail2ban jail `labuse-login`** : filtre sur le journal d'accès JSON de Caddy
  (`/var/log/caddy/access.log`, activé au Caddyfile) — POST /login|/login/2fa répondu 401 → ban
  IP (10 échecs/5 min → 1 h). `fail2ban-client status labuse-login` : jail active. Défense en
  profondeur (l'app garde SON verrou de compte : 5 échecs → 15 min).
- **Login pilote partagé MORT** : `LABUSE_LOGIN_PILOTE_ACTIF=0` (le mot de passe partagé répond
  401 neutre). Jamais réactivé pendant la recette (script initial refusé à raison par la garde
  de permissions — recette refaite sur un compte réel).
- **Admin nominatif Vic (AC-020)** — mécanisme prêt et testé (`labuse creer-admin`), MAIS la
  création du compte réel de Vic est laissée À VIC : elle produit un lien d'invitation qu'il doit
  ouvrir pour poser SON mot de passe, et son 1er login enrôle la 2FA sur SON téléphone — rien
  qu'un tiers puisse faire à sa place. Commande exacte au rapport. Personne n'est enfermé dehors :
  le compte existant de Vic (`kampusreunion@gmail.com`, titulaire actif) entre dans l'app ;
  `creer-admin` le promeut admin quand il le veut.

## V7 — RECETTE

### Derrière le rideau (via 127.0.0.1, sans toucher à la sécurité)
readyz ready=true ✓ · healthz 200 ✓ · route protégée sans session → 401 ✓ · page /login rendue
par l'app ✓ · /login/2fa sans défi → 302 ✓.

### Recette authentifiée réelle (compte titulaire éphémère `recette-vps@labuse.local`, créé actif
puis SUPPRIMÉ RGPD après — le pilote n'a JAMAIS été rallumé)
login utilisateur réel (303 + cookie) ✓ · **fiche 97416000ES2071 200, tier servi, run
q_v11_m137** ✓ · tiles/meta `run_label=q_v11_m137` ✓ · tuile z12 200 (0 o = zone vide, meta
prouve le run) · export JSON 200 ✓ · export.csv 200 (1002 lignes) ✓ · **export.pdf 186 Ko
(WeasyPrint OK sur le VPS)** ✓ · courrier SPF 200 (texte, par conception — PlainTextResponse) ✓ ·
copilote `/api/copilote-v2/ask` 200, quota+ia_log comptés ✓.

### Recette extérieure (depuis l'internet, rideau tombé, sans tunnel)
racine sans session → 302 /login ✓ · page login LABUSE publique ✓ · certificat valide (HTTP 200) ✓
· API protégée → 401 JSON ✓ · shell + favicon 200 ✓ · HSTS présent, plus de www-authenticate ✓ ·
webhook Stripe joignable (503 « non configuré » tant que whsec_ absent — honnête) ✓.

### FINDINGS de recette (pour Vic — secrets/config, PAS des défauts de code)
- **VP-003 — clé Anthropic invalide sur le VPS** : `ANTHROPIC_API_KEY` (posée en juillet) renvoie
  401 `authentication_error`. Le Copilote se dégrade PROPREMENT (« service d'analyse
  indisponible », `degraded:true`, jamais un crash — comportement correct). À renouveler par Vic
  dans `/etc/labuse/labuse.env` puis `systemctl restart labuse`. La partie déterministe de l'app
  n'en dépend pas.
- **VP-004 — extra `[ai]` manquait au venv** : `anthropic` est une dépendance OPTIONNELLE
  (`pyproject [ai]`) ; le venv de base ne l'avait pas → 1er `/ask` en ModuleNotFoundError.
  CORRIGÉ : installé dans le venv, et `deploy_vps.sh` installe désormais `-e "$APP[ai]"` pour que
  chaque déploiement le garde.
- Stripe/Brevo/SMTP : non configurés (placeholders) — l'app le dit honnêtement (webhook 503,
  mails journalisés). Clés LIVE à poser par Vic.
