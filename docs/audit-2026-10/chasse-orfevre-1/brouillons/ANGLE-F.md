# ANGLE F — Les journaux de prod (30 jours : 18/09 → 18/10/2026)

Collecte : 18/10/2026 ~18h15 Réunion, VPS `labuse-vps` (51.255.163.56), **lecture seule stricte**
(journalctl, cat/grep via ssh ; analyse locale sur les copies `/tmp/orfevre-logs/`).
Script rejouable : `scripts/angle_f_journaux.sh`. Code rapproché : worktree `~/Desktop/labuse-orfevre` (= main).

---

## 1. Topologie & couverture

### Services (systemd, pas de docker — `docker ps` vide)
| Service | Rôle | Logs |
|---|---|---|
| `labuse.service` | FastAPI/Uvicorn 127.0.0.1:8000, **5 workers**, user `labuse`, `MemoryMax=6G`, `Restart=always` | journald (`SyslogIdentifier=labuse`) |
| `caddy.service` | Reverse proxy TLS `app.labuse.immo` | `/var/log/caddy/access.log` (JSON) + journald |
| `postgresql@18-main` | PostgreSQL 18 | `/var/log/postgresql/postgresql-18-main.log*` |
| cron `/etc/cron.d/labuse` | GÉNÉRÉ par deploy.sh (registre `labuse.jobs`, CRON-1) | wrapper → `/var/log/labuse/jobs/*.log` |

### Historique des déploiements (restarts `labuse.service` dans la fenêtre)
22/09 06:19 · 25/09 06:47 · 01/10 06:42 · **06/10 18:03 → 07/10 04:29 (17 restarts : nuit de migration)** ·
09/10 06:26 · 13/10 15:40 / 21:07 · 14/10 00:57 / 16:01 / 16:23 / 16:50 / 17:02.
**Stable sans redémarrage depuis le 14/10 17:02** (4 jours au moment de la collecte).

### Couverture réelle des logs (à savoir avant de conclure)
- **journald** : un seul boot listé, entrées **du 19/09 00:08 au présent** (321 Mo) → le 18/09 manque
  presque entièrement côté app ; uptime machine 101 jours.
- **Caddy access.log** : UN SEUL fichier 81 Mo, **du 27/08 à aujourd'hui, AUCUNE rotation configurée** → couvre toute la fenêtre.
- **PostgreSQL** : rotation hebdo, 10 conservés → couvre depuis mi-août.
- **Logs de jobs** : le wrapper CRON-1 (`jobs run X` → `/var/log/labuse/jobs/X.log`) n'écrit à cet endroit
  que **depuis le 13/10 21:07** (et `/var/log/labuse/X.log` depuis le 13/10 12:55Z seulement).
  **Le schéma cron CRON-1 tourne depuis le 07/10 04:00 mais ses sorties 07→13/10 ne sont plus sur disque.**
  Avant le 07/10 : ancien cron `flock` → logs « thème » (`bodacc.log`, `dvf.log`, `notifications.log`…) depuis juillet.
- **Piège journald** : l'export `journalctl _COMM=cron` PERD des lignes (89 CMD healthcheck comptées le 17/10
  dans le journal contre **96 débuts réels dans le log du wrapper**). Les « trous » du journal ne sont PAS des
  jobs manqués — toujours recouper avec les logs wrapper.

---

## 2. Groupes d'erreurs (API + jobs + base), classés

### G1 — GÊNANT · ACTIF · mail-queue-consommer échoue TOUS LES JOURS à 13:35 Réunion (fenêtre pg_dump)
- **Compte / période** : 9 échecs « job mail-queue-consommer en échec », 1/jour à 09:35Z (=13:35 Réunion)
  du **14/10 au 18/10** inclus (+ le passage 13:40 « SAUTÉ : exécution précédente en cours »). Continue.
- **Mécanisme prouvé** (log 17/10) :
  ```
  2026-10-17T09:35:02Z [mail-queue-consommer] début
  2026-10-17T09:40:02Z [mail-queue-consommer] passage SAUTÉ : une exécution précédente est encore en cours
    File "/opt/labuse/app/src/labuse/mailfile.py", line 102, in ensure_tables
      c.execute(text("ALTER TABLE mail_queue DROP CONSTRAINT IF EXISTS mail_queue_etat_check"))
    File "/opt/labuse/app/src/labuse/jobs.py", line 163, in _sonne
      raise _Timeout(f"dépassement du timeout ({job.timeout_s}s)")
  labuse.jobs._Timeout: dépassement du timeout (300s)
  psycopg.OperationalError: sending query failed: another command is already in progress
  job mail-queue-consommer en échec
  ```
- **Cause** : `mailfile.ensure_tables()` rejoue à CHAQUE run (toutes les 5 min) des DDL
  (`ALTER TABLE mail_queue DROP/ADD CONSTRAINT`, verrou ACCESS EXCLUSIVE). Le backup `backup-postgres`
  tourne 13:30→13:48 (pg_dump tient des verrous ACCESS SHARE sur `mail_queue`) → l'ALTER bloque →
  SIGALRM `_Timeout` 300 s (`jobs.py:160-186`) interrompt psycopg EN PLEIN wait → la connexion du pool
  reste sale → « another command is already in progress » en cascade.
- **Code (main)** : `src/labuse/mailfile.py:95-104` (DDL par run — toujours là),
  `src/labuse/jobs.py:160-186` (timeout par signal qui salit la connexion). **NON corrigé dans main.**
- **Impact** : mails du créneau 13:35-13:45 décalés de ~10 min ; un incident `job-echec` rouge par jour ;
  parfois « journal/alerte impossible pour le job » (l'échec lui-même ne peut pas s'écrire).

### G2 — GÊNANT · ACTIF · healthcheck échoue tous les jours à 13:45 : l'ALERTE DISQUE ne peut pas s'écrire
- **Compte / période** : 1 traceback/jour à 09:45Z (=13:45 Réunion) du **14/10 au 18/10**. Continue.
- **Extrait (18/10)** :
  ```
  File "/opt/labuse/app/src/labuse/jobs_impl.py", line 364, in healthcheck
    ops_alertes.signaler(db, "disque", f"Disque à {pct}% (seuil {s.disque_seuil_pct}%)", ...
  File "/opt/labuse/app/src/labuse/ops_alertes.py", line 55, in ensure_table
    db.execute(text(DDL_INDEX))
  ...
  labuse.jobs._Timeout: dépassement du timeout (120s)
  ```
- **Cause** : le disque passe le seuil **85 %** (df : 84 % hors backup, davantage pendant l'écriture du dump)
  PENDANT la fenêtre pg_dump 13:30-13:48 → `signaler()` veut poser `ops_incidents` + `CREATE UNIQUE INDEX
  IF NOT EXISTS` (`ops_alertes.py:55`, DDL à chaque appel) → bloqué par pg_dump → timeout 120 s → le job
  échoue **et l'alerte disque n'est jamais enregistrée** : la sonde est aveugle exactement quand elle sonne.
- **Code (main)** : `src/labuse/jobs_impl.py:380-382` (seuil `config.py:214` = 85), `src/labuse/ops_alertes.py:45-56`.
  **NON corrigé dans main.** (En prod, la ligne est jobs_impl.py:364 — même code, offset de version.)
- **Pourquoi ça a commencé le 14/10** : c'est la date où le disque a atteint le seuil (84-85 %) — avant,
  `signaler` n'était pas appelé pendant le backup.

### G3 — GÊNANT · ACTIF · pg-maintenance : le VACUUM hebdo n'a JAMAIS fonctionné, job pourtant VERT
- **Compte / période** : « VACUUM cannot run inside a transaction block » chaque dimanche 04:00 Réunion :
  **13/09, 20/09, 27/09, 04/10, (11/10 absent du log pg conservé), 18/10** + un run manuel 13/10 14:07 UTC.
- **Preuve que RIEN n'est vacuumé et que le job est vert quand même** (`jobs/pg-maintenance.log`, 18/10) :
  ```
  2026-10-18T00:00:02Z [pg-maintenance] début
  VACUUM parcels ignoré (VACUUM cannot run inside a transaction block)
  VACUUM event_log ignoré (current transaction is aborted, commands ignored ...)
  ... (idem pige_biens, pige_faits, veilles, dvf_mutations)
  2026-10-18T00:00:04Z [pg-maintenance] fin (code 0)
  ```
- **Cause (code, main)** : `src/labuse/jobs_impl.py:495-512` — `raw = engine().raw_connection()` puis
  `raw.autocommit = True`. `raw` est le **proxy de pool SQLAlchemy** (`PoolProxiedConnection`) : l'affectation
  pose un attribut sur le proxy, PAS sur la connexion psycopg → psycopg ouvre un bloc de transaction →
  VACUUM refusé ; l'`except` par table (« une table absente ne casse pas la maintenance », ligne 508-509)
  avale tout → `fin (code 0)`. Fix attendu : `raw.driver_connection.autocommit = True` (ou connexion psycopg directe).
  **NON corrigé dans main** (le run du 18/10, post-déploiement 14/10, échoue encore).
- **Impact** : les 6 « tables chaudes » ne reçoivent jamais leur VACUUM ANALYZE hebdo (l'autovacuum reste
  le seul filet) ; faux vert permanent au tableau de bord des jobs.

### G4 — GÊNANT · RÉSOLU · nuit de migration 06/10 20:00 → 07/10 03:28 : la totalité des 500 et tracebacks API de la fenêtre
**TOUS les tracebacks API des 30 jours (378 lignes « Traceback », 46 réponses 500, 137 des 142 5xx Caddy)
sont dans cette unique fenêtre** — nuit de déploiement/migration (17 restarts, création/chargement de
`score_labuse`, `commune_zonage_abc`, `cout_construction_ref`, `batiment_hauteur_lidar`… vus dans le log pg),
trafic = IP opérateur 83.204.133.163. Sous-groupes :

| Sous-groupe | n | 1re → dernière | Endpoint | Cause / code |
|---|---|---|---|---|
| `FileNotFoundError: reports/m36-foncier/FREEZE-scoring2026.json` | 21 | 06/10 20:01 → 07/10 03:27 | `GET /v2/modele` → 500 | `src/labuse/api/score_v2.py:196` lit `MODEL_FREEZE` (`scoring/p_v2/__init__.py:20`) ; fichier pas encore déployé. Présent dans main → **200 OK dès le 07/10 08h+ (69×200 le 08/10), 0 récidive** |
| `UndefinedColumn: column d.mode_remplissage does not exist` | 20 | 06/10 20:34 → 07/10 01:37 | `GET /admin/circuit` → 500 | `src/labuse/circuit_garanties.py:404/687/698` lit `data_sources.mode_remplissage` avant la migration ; colonne posée dans la nuit → **200 OK ensuite, 0 récidive** |
| `TimeoutError: QueuePool limit of size 5 overflow 10 reached` | 77 | 06/10 20:06 → 06/10 23:43 | toutes routes (dep `get_db`, `api/app.py:408`, `couches_tuyau.py:49`) | pool épuisé pendant les migrations longues (requêtes 460-600 s observées côté Caddy) |
| `QueryCanceled: statement timeout` | 19 | 06/10 20:07 → 06/10 23:59 | fiches parcelles & co | statement_timeout pendant la charge ; 1 `deadlock detected` + 1 GEOS Interrupted dans le log pg |
| `UndefinedTable: commune_zonage_abc` (+ `cout_construction_ref` côté pg) | 3 | 06/10 20:07 → 20:09 | `GET /parcels/{idu}?source=q_v16` → 500 | tables créées plus tard dans la nuit |

**Classement : résolu en prod le 07/10 ; 11 jours sans récidive.** À retenir : déploiement « app ouverte »
pendant la migration — les 500 étaient visibles de l'extérieur (mais seul l'opérateur naviguait).

### G5 — GÊNANT · RÉSOLU le 14/10 · chemin Mac en prod : captures Radar/pige inécrivables
- **95 occurrences** ERROR au démarrage de chaque worker, du **06/10 19:55 au 14/10 16:24** :
  ```
  ERROR: labuse — RADAR — répertoire de captures INACCESSIBLE EN ÉCRITURE :
  /Users/openclaw/labuse-pige/captures — inaccessible en écriture (PermissionError: ... '/Users').
  Le dépôt de captures ÉCHOUERA en ligne — créer/chown le répertoire (voir docs/PIGE/EXPLOITATION.md § captures).
  ```
- **Cause** : `LABUSE_PIGE_CAPTURES_DIR` (ou `pige_captures_dir`) posé avec un chemin **du Mac de dev** dans
  l'env prod au déploiement du 06/10. Garde-fou = `src/labuse/api/app.py:247` ; défaut prod sain =
  `/srv/labuse/pige/captures` (`src/labuse/pige/tables.py:41-44`).
- **Résolution** : plus aucune occurrence aux démarrages 14/10 16:50 et 17:02 → env corrigé le 14/10. Radar/pige
  étant GELÉ (Phase 8), l'impact réel était nul, mais 8 jours de config prod pointant sur un Mac méritent le rapport.

### G6 — GÊNANT · CORRIGÉ dans main (job gelé) · refresh DVF hebdo cassé : `mutation_id` inexistante
- **Occurrences** : log pg **23/09 et 30/09** (`ERROR: column "mutation_id" of relation "dvf_mutations_parcelle"
  does not exist`), 11 tracebacks dans `dvf.log` (mardis 05:00, remonte avant la fenêtre).
- **Cause** : l'ancien `refresh_dvf` insérait les colonnes de `load_dvf_geo` (`mutation_id, …`,
  `ingestion/layers_ingest.py:1001`) dans `dvf_mutations_parcelle` dont le schéma est `id_mutation, …`
  (`models.py:973+`) → la table servie n'était jamais rafraîchie.
- **État** : corrigé dans main — `ingestion/fraicheur.py:372-376` (commentaire CORRECTIFS-1 E1 : recharge
  `dvf_mutations`) ; le cron DVF est de toute façon **GELÉ Phase 8** depuis le cron CRON-1 du 07/10.
  Conséquence assumée : `dvf_mutations_parcelle` vieillit (connu des audits VERITE-TERRAIN).

### G7 — À SURVEILLER · plus AUCUNE copie hors-site planifiée depuis le 14/10
- `/etc/cron.d/labuse.bak-offsite-20261014-162648` (cron ignoré car nom à points) contient l'entrée
  `backup-offsite` hebdo (dim 14:30) ; le cron ACTIF ne l'a plus. `restore-test` mensuel est GELÉ Phase 8.
- Donc : dump quotidien local 13:30 (OK, 5/5 `fin (code 0)`, ~18 min) mais **ni copie hors du VPS ni test de
  restauration planifiés**. Le remplacement (`feat(sauvegarde-disque)` : disque externe Mac) est un WIP hors main
  (vu dans `git log jobs_impl.py` : « WIP déplacé hors de main »). Sur un disque à 84 %, c'est le point de risque n°1.

### G8 — À SURVEILLER · disque à 84 % (seuil d'alerte 85) + logs sans rotation
- `df /` : **81G/96G = 84 %**, 16G libres. Le seuil `disque_seuil_pct=85` est franchi pendant chaque backup → G2.
- `/var/log/caddy/access.log` : 81 Mo, un seul fichier depuis le 27/08, aucune rotation ; journald 321 Mo.

### G9 — À SURVEILLER · mort silencieuse d'un worker uvicorn (unique)
- **17/10 20:17:50** : `Child process [1406849] died` (juste après un login 2FA opérateur), **sans OOM**
  (rien dans kern.log, MemoryPeak service ~1,07 G sur 6 G) → 4 × 502 Caddy (`EOF`, tuiles
  `/map/tiles/limites_parcelles/15/...`, durées ~11 s) ; worker relancé en 13 s. Un seul cas en 30 jours ;
  profil « crash natif pendant la génération de tuiles » — à garder à l'œil si récidive.

### G10 — COSMÉTIQUE · 404 en rafale sur `/map/tiles/ortho/monde/...`
- **483 des 724 404** de la fenêtre = tuiles ortho « monde » à z10-11 : c'est le **by design** du proxy
  (`src/labuse/api/ortho_proxy.py:228-256` : « Tuile mer (aplat) » → 404) quand l'utilisateur dézoome au large.
  Pas un lien mort, mais du bruit de log et des requêtes IGN évitables (elles sont bien court-circuitées cache/mer).

### G11 — COSMÉTIQUE (contexte sécurité) · scans et 401 en rafale
- **9 823 × 401** depuis le 18/09, dominés par les scanners (`/.env` 76, `/.git/config` 56, familles
  `wp/wordpress` ~280, GrokBot/KimiBot…). `garde_protection` renvoie 401 — sain. fail2ban : 350 bans sshd.
- Burst singulier : **11/10, 599 × 401 sur `/admin/*`** (dont 149 `/admin/circuit`, 299 cumulés `/admin/pilotage`)
  **depuis l'IP opérateur** : un dashboard admin resté ouvert avec session expirée qui re-polle sans redirection
  login. Gênant léger côté UX admin, rien côté sécurité.
- 11 739 requêtes « status 0 » (client parti : suggest, tuiles pendant pan de carte) = normal.

### G12 — COSMÉTIQUE · divers répétés
- **weasyprint** : 85 warnings « HarfBuzz-Subset » (fonts Inter/IBM Plex/DejaVu) + sélecteurs `::note-*` — PDF
  fonctionnels, dette de dépendance.
- **geopf.fr** : 3 × 502 et 1 × 400 WMS exposition, 2 WMTS timeouts contour — amont IGN, gérés en warning.
- **Stripe** : 1 webhook « REJETÉ (signature) : SignatureVerificationError » le 09/10 02:46 — unique, garde OK.
- **SITADEL/DiDo 400** (`DATE_REELLE_AUTORISATION=gte:...`) : occurrences anciennes dans `sitadel_refresh.log` ;
  le run mensuel CRON-1 du 13/10 s'est terminé `fin (code 0)` — plus d'échec dans la fenêtre récente.
- 1 × 502 `GET /.git/config` le 09/10 06:27 = scan tombé pile pendant le restart de déploiement.

### G13 — RÉSOLU · churn du déploiement du 13/10 (sans impact client durable)
- 13/10 12:55Z : **replay de TOUS les jobs** avec `PermissionError: '.local/state/jobs'` (chemin d'état RELATIF
  exécuté depuis un cwd non inscriptible — `jobs.py:71-78` + `settings.jobs_state_dir`) ; repassés verts 13:37Z.
  Même erreur relancée 14/10 12:03-12:06Z (4 runs manuels). Piège à noter : `jobs_state_dir` doit être absolu.
- 13/10 15:30→17:25 Réunion : **51 échecs mail-queue** `fe_sendauth: no password supplied` + « the database
  system is shutting down » (bascule env/postgres pendant le déploiement) ; plus rien après 17:25.
- 22/09 06:19 : au restart, 15 modules « heal schéma ÉCHOUÉ » (postgres en cours de redémarrage, cert
  `~/.postgresql/postgresql.crt` Permission denied) — une seule salve, app repartie ensuite.

---

## 3. Jobs : régularité, manqués, durées
- **Aucun job planifié manqué détecté** : les « trous » apparents dans `journalctl _COMM=cron` sont des pertes
  de lignes journald (preuve : 17/10 = 96 débuts réels dans le wrapper vs 89 lignes CMD au journal).
  Vérifié sur les wrapper-logs 13→18/10 : tous les `début` ont leur `fin (code 0)` SAUF les échecs G1/G2
  (qui se terminent sans ligne `fin` : 13 débuts sans fin sur mail-queue, 3 sur healthcheck).
- Jobs rares exécutés à l'heure : ingest-sirene 07/10, ingest-sitadel 10/10 04:30, ingest-dpe 12/10 04:00,
  sync-gpu 15/10 04:00, verite-sources 15/10 06:00-06:04, pg-maintenance dimanches, backup quotidien 13:30.
- **GELÉS volontairement (Phase 8 Stéphanie, commentés dans le cron)** : ingest-dvf, radar-cloche, radar-cycle,
  radar-cycle-dvf, radar-cycle-mensuel, digest, restore-test. Retiré (non commenté, disparu) : backup-offsite (G7).
- Durées : backup 18 min (stable 5/5) ; coherence-banc 03:45→03:57 (12 min) ; fiche-commune-cache 03:00→03:12 ;
  rien d'anormal hors fenêtre backup.

## 4. Caddy (synthèse chiffrée, 18/09→18/10)
- 51 028 requêtes : 2xx 25 875 · 3xx 2 711 · 4xx 10 561 · **5xx 142** · « 0 » (abandon client) 11 739.
- 5xx par jour : 06/10 = 49, 07/10 = 88 (G4) ; 09/10 = 1 (scan pendant restart) ; 17/10 = 4 (G9). **Rien d'autre.**
- Latences > 30 s : 82, toutes les 06-08/10 (nuit G4 + 3 le 08/10 02:35 ≈ fenêtre batch) ; max 598 s (`/modules/permis`).
- Pas un seul warning/erreur TLS-certificats au journal caddy sur la fenêtre.

## 5. Système
- **OOM : aucun** (kern.log vide sur oom/killed). RAM service : pic 1,07 G / 6 G autorisés.
- **Disque : 84 %** → G2/G8. PostgreSQL : pas de PANIC ; 1 deadlock (nuit G4) ; erreurs récurrentes = G3 ;
  FATAL « password authentication failed » ×4 le 28/09 (bref, non répété) ; « VACUUM cannot run… » hebdo (G3).
- Brevo : **0 échec d'envoi** dans les logs mail-queue (les échecs du job sont AVANT l'envoi, cf. G1).
- fail2ban actif (350 bans sshd sur la fenêtre).

## 6. Croisements avec les audits précédents
- G4 recoupe la bascule q_v16/scoring servie début octobre (tables score_labuse/commune_zonage_abc de SCORING-7,
  LiDAR de CHASSE-INVARIANTS) — c'est la mise en prod de ces mandats, avec app restée exposée pendant la migration.
- G6 était précisément le bug décrit/corrigé par CORRECTIFS-1 E1 (commentaire in situ) — les logs prod datent les
  dernières morsures réelles (23 et 30/09).
- Le gel Phase 8 (radar/digest/DVF) vu en mémoire d'audit est confirmé par le cron ; l'angle neuf est G7
  (offsite RETIRÉ, pas seulement gelé).
- La « QueryCanceled → rollback silencieux » de SCORING-6 ne réapparaît pas dans la fenêtre hors nuit G4.

## 7. Récapitulatif par gravité
| Gravité | Groupes |
|---|---|
| Bloquant | — (aucun actif) |
| Gênant actif | **G1** (mail-queue échec quotidien 13:35), **G2** (healthcheck 13:45 + alerte disque muette), **G3** (VACUUM hebdo jamais fait, job vert) |
| Gênant résolu | G4 (nuit 06-07/10), G5 (chemin Mac captures), G6 (DVF mutation_id, corrigé+gelé), G13 (churn 13/10) |
| À surveiller | **G7** (plus d'offsite ni restore-test), G8 (disque 84 %, logs sans rotation), G9 (worker mort 17/10) |
| Cosmétique | G10 (404 tuiles mer), G11 (scans/401, burst admin 11/10), G12 (weasyprint, geopf, Stripe 1×, sitadel ancien) |

Fil rouge des trois gênants actifs : **la fenêtre pg_dump quotidienne 13:30-13:48 + des DDL « ensure » rejouées
à chaque run + un timeout par SIGALRM qui laisse la connexion sale** ; et un disque à un point du seuil d'alerte,
alerte qui ne peut justement pas s'écrire pendant la fenêtre.
