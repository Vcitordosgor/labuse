# DEPLOY-1027 — mise en prod de main (f28550160)

Lancé le 27/10/2026 depuis `~/Desktop/labuse-main`, prod `labuse-vps`.
Périmètre : quatre recettes d'outils, Étude de faisabilité V6, DOCS-COHERENCE-1 — tout main depuis le 13/10.

---

## Phase 0 — état des lieux (lecture seule)

### 0.1 Mac
- `git status -sb` : `## main...origin/main` à jour, HEAD `f28550160` (« Merge branch 'feat/docs-coherence-1' »). ✓
- Seul intrus : `logs/` non suivi (sans effet, exclu du rsync de toute façon).

### 0.2 VPS
- Disque : `/dev/sda1` 96 G, **87 G utilisés, 9,0 G libres (91 %)** ← point dur, voir 0.7.
- Mémoire : 11 Gi total, 6,8 Gi disponibles. ✓
- Service `labuse` : `active` ; `/readyz` → 200. ✓
- Run servi (`/opt/labuse/app/config/served_manifest.json`) : `scoring=q_v18 · cascade=q_v18_sources · mvt=q_v18 · division=q_v18 · residuel_run_seq=15`, promu le 13/10 (précédent q_v16/q_v13_sources1/seq 13).
- Commit du code prod : inconnu (le déploiement rsync n'expédie pas `.git` — attendu). L'état correspond au déploiement du 13/10.
- Base prod : 38 Go. `/var/backups/labuse` : 33 Go (dumps 6,5 Go pièce : quotidiens 1024/1025/1026/1027 + hebdo 1018 + hebdo 1025 en lien dur sur 1025).

### 0.3 Écart de schéma (information_schema Mac ⟷ prod, diffé)
Ce que le nouveau code attend et que la prod n'a pas :

| Objet | Type | Geste phase 2 |
|---|---|---|
| `parcel_couche_intersection_build` | table neuve (6 col., geom) | `CREATE TABLE IF NOT EXISTS` (DDL extraite du Mac) |
| `parcel_residuel_runs.surface_terrain_m2` | colonne (integer) | `ADD COLUMN IF NOT EXISTS` — **obligatoire AVANT la phase 3** (sync-run COPY la liste de colonnes du VPS) |
| `parcel_zone_plu.zone_filtre` | colonne (text) | `ADD COLUMN IF NOT EXISTS` (le builder la réécrit nativement) |
| `parcel_zone_plu_version.built_at`, `.sig` | colonnes | `ADD COLUMN IF NOT EXISTS` |
| `v_parcelle_contact_compte` | vue neuve | phase 4, `labuse doctor` (ensure_schema du nouveau code) |
| `parcel_residuel` (+`surface_terrain_m2`) | vue à recréer | phase 4, `labuse doctor` (`ensure_residuel_cache`), service arrêté |

Tables en prod absentes du Mac (agent_runs/agent_events, `_cad_sm1_*`, backups `m6_*`/`sauvegarde_*`…) : données prod ou reliquats — **on n'y touche pas** (jamais de DROP).

### 0.4 Écart de données

**Runs (sync-run) :**

| Table | Mac | prod | à envoyer |
|---|---|---|---|
| `score_labuse` (q_v20) | 433 229 | 0 (prod : q_v16, q_v18) | OUI (filtré run_label=q_v20) |
| `score_labuse_runs` (q_v20) | 1 | 0 | OUI |
| `parcel_p_score_v2` / `p_score_v2_runs` (q_v20) | 433 229 / 1 | 0 | OUI |
| `dryrun_cascade_results` (q_v19_sources) | 21 097 100 | 0 (prod : q_v11_m137, q_v13_sources1, q_v18_sources) | OUI |
| `dryrun_parcel_evaluations` (q_v19_sources) | 433 229 | 0 | OUI |
| `parcel_residuel_runs` (seq 17) / `residuel_runs` | 433 229 / 1 | 0 (prod sert seq 15) | OUI |
| dérivés entiers (parcel_evaluations 1 444 861 · pc_caducs 4 822 · defisc_fenetres 1 166 · score_e 279 946 · dvf_prix_sortie_neuf 12 · surface_d_events 11 918) | — | — | OUI (routine) |

**Fond (`labuse parite`, recompté table par table — le premier passage avait un artefact : la 1ʳᵉ table absente en local aborte la transaction et toutes les suivantes sortent « — ») :**

| Table | Mac | prod | verdict |
|---|---|---|---|
| parcels | 434 582 | 434 582 | = |
| adresses / adresse_parcelles | 339 915 / 418 346 | idem | = |
| spatial_layers | 1 931 174 | 1 931 174 | = (BPE/amenite incluses) |
| parcel_couche_intersection | 1 607 877 | 1 607 877 | = → **pas de build-intersections nécessaire** |
| parcel_zone_plu | 430 320 | 427 419 | ≠ — table MATÉRIALISÉE à signature (`tiles.build_parcel_zone_plu`, DROP+CREATE AS depuis spatial_layers, identiques) → se régénère en prod au premier build-mvt/périmption de signature, **rien à transférer** |
| parcel_cadastre_remplacement | absente du Mac (drop staging SM1) | 3 007 | le nouveau code la LIT (garde « parcelle disparue »), la prod l'A → rien à faire, données prod conservées |

Quotidien (BODACC, Sitadel, DPE, SIRENE, DVF) : prod fait foi, non touché. `gabarit_zone_libere_m2` : valeur calculée au read (regles/gabarit_implantation_m2.py), pas une colonne — part avec le code. Implantation (Étude V6) : calcul live, pas de table dédiée.

### 0.5 Écart de config serveur
- Proxy actif : **Caddy** (nginx `inactive` → `deploy/nginx/labuse.conf` sans objet).
- `/etc/caddy/Caddyfile` vs `deploy/Caddyfile.prod` : 2 écarts = commentaire compression G1 + **`reverse_proxy { transport http { read_timeout 75s } }`** (Étude V6-2). → copier + `caddy validate` + reload en phase 4.
- `/etc/systemd/system/labuse.service` vs dépôt : 1 écart = **`--timeout-keep-alive 75`**. Installé par `deploy_app.sh` (étape 4) + `daemon-reload`.
- Rien d'autre ne diverge. Conforme à `docs/deploiement/etude-v6-2-timeouts.md`.

### 0.6 Écart de crontab (registre ⟷ /etc/cron.d/labuse)
Diff par ENSEMBLE de jobs (le générateur Mac sort les heures en UTC, la prod est en heure Réunion : écarts d'heures uniformes −4 h = artefact, ignorés) :

| Geste | Job | Détail |
|---|---|---|
| RETIRER (ciblé) | `recap-matin` (actif, 07:30) | retiré du registre (COCKPIT-1 Lot C, décision Vic) ; le job n'existe plus dans le nouveau code → la ligne échouerait chaque matin |
| AJOUTER (ciblé) | `signal-instantane` | nouveau (Signal lot 4) : mensuel, 06:00 Réunion le 1ᵉʳ (`0 6 1 * *`) |
| NE PAS TOUCHER | `agents-sources` | au registre mais hors crontab prod = décision historique, maintenue |
| NE PAS TOUCHER | 6 gelés `# GELÉ (Phase 8 Stéphanie)` | radar-cloche/-cycle/-cycle-dvf/-cycle-mensuel, digest, restore-test — restent gelés (restore-test n'est plus au registre : commentaire inerte, laissé) |
| RAS | `mail-queue-consommer` | reste `*/5` ; le « cède à la sauvegarde » est dans le code |
| RAS | `ingest-dvf` | déjà dégelé en prod (20/10) |

### 0.7 Go / no-go

**Point dur disque.** 9,0 Go libres ; il faut : dump phase 1 (6,5) + dump garde 1 de `deploy_donnees.sh` (6,5) + garde 2 « ≥ 12 Go libres » + ~5 Go de CSV en clair dans /tmp (sync-run) + ~7 Go de croissance base (q_v20 + q_v19_sources 21 M lignes + résiduel seq 17 ; rien d'ancien n'est supprimé, q_v18 reste en secours).

**Ménage décidé (phase 1), tout est redondant ou mort :**
1. Mac : rotation `~/labuse-backups/vps` à 2 dumps (politique OPS-ROTATION-1 — le Mac est à 97 %, 7,6 Go libres) → +19,5 Go Mac.
2. Rapatrier `hebdo-labuse-labuse-20261018` sur le Mac (vérifié `pg_restore --list`), puis le supprimer du VPS → +6,5 Go VPS.
3. VPS : supprimer `labuse-labuse-20261024.dump` et `…-20261026.dump` (copies Mac vérifiées — pull.log du 26/10 « rapatrié + intègre ») → +13 Go.
4. VPS : supprimer les reliquats dev de `/opt/labuse/app` jamais lus au runtime (preuve : DISQUE-VPS-1 §1) : `docs/` 1,7 G + `qa/` 803 M + `captures/` 270 M + `audit_shots/` 59 M (`outputs/` et `data/*` conservés — écrits au runtime) → +2,8 Go.

Bilan prévisionnel : ~31 Go libres avant phase 2 ; ≥ 18 Go au moment de la garde 2 ; ~6 Go en fin de restore, ~11 Go après purge des CSV /tmp. Fin de déploiement serré mais sain ; recommandation à Vic en fin de rapport (ménage des runs morts q_v16/q_v13_sources1 via `menage_disque.sh`).

**Ce que les phases 2–5 vont toucher, exhaustivement :**
- Phase 2 (schéma) : 1 `CREATE TABLE IF NOT EXISTS` + 4 `ADD COLUMN IF NOT EXISTS` (0.3). Aucun DROP.
- Phase 3 (données) : les tables du tableau 0.4 « runs », via `deploy_donnees.sh --no-bascule` (dump garde 1 inclus). Aucune table client, aucun flux quotidien.
- Phase 4 (code+config) : `/opt/labuse/app` (rsync, exclusions protégées), venv (requirements.lock + `-e .`), front (rebuild VPS), unité systemd, Caddyfile, crontab ciblée (0.6).
- Phase 5 (bascule) : manifeste prod → q_v20/q_v19_sources/seq 17 (`golden promote` + `residuel-serve 17`), rebuild front (repli VITE_RUN_LABEL lu de `served_run.txt` post-bascule), purge `mvt_tile_cache` (parcels a minima), réchauffage en fond.

**GO** (sous le ménage ci-dessus). Ménage complet **validé par Vic en session** (question posée, réponse « Ménage complet »).

---

## Phase 1 — filet de sécurité

### Ménage disque préalable (autorisé par Vic)
- Mac : rotation `~/labuse-backups/vps` → suppression des dumps 22/23/24-10 (politique 2 conservés), 24 Gi libres après (était 7,6 à 97 %).
- `hebdo-labuse-labuse-20261018.dump` **rapatrié sur le Mac et vérifié** (`pg_restore --list` OK) AVANT sa suppression du VPS.
- VPS supprimés : `labuse-labuse-20261024.dump`, `…-20261026.dump` (copies Mac vérifiées, pull.log 26/10), `hebdo-…-20261018.dump` (copie Mac fraîche), et `/opt/labuse/app/{docs,qa,captures,audit_shots,.playwright-mcp}` (reliquats dev, preuve DISQUE-VPS-1 §1 : jamais lus au runtime ; `outputs/`, `data/*`, `.local` conservés).
- Résultat : **/dev/sda1 65 G utilisés, 32 G libres (68 %)**. Dumps restants : 1025 (+hebdo lien dur), 1027 midi, + celui de la phase 1.

### Sauvegarde + copies
- Dump phase 1 : `backup_postgres.sh` (env `/etc/labuse/labuse.env` chargé, user labuse, nohup → `/tmp/backup_phase1_1027.log`) → `labuse-labuse-20261027-173056.dump` ; contrôle `pg_restore --list` intégré au script (échec = dump supprimé, bruyant).
- Code : `cp -al /opt/labuse/app → /opt/labuse/app-avant-1027` et `cp -al /opt/labuse/venv → /opt/labuse/venv-avant-1027` (liens durs : instantané sans espace ; rsync/npm/pip remplacent par unlink+create → l'instantané reste intact).
- Config : `/etc/caddy/Caddyfile → Caddyfile.avant-1027` ; unité systemd → `/root/labuse.service.avant-1027` (hors `/etc/systemd/system` pour ne pas polluer systemd) ; `served_manifest.json` + `served_run.txt` + `/etc/cron.d/labuse` → `/root/*.avant-1027`.
- Tests de la routine côté Mac : `pytest tests/test_solidite1_lot4.py` → **5 passed** (gardes dans l'ordre, syntaxe des scripts, garde manifeste).

### Phase R — commandes exactes de retour arrière
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app && sudo mv /opt/labuse/app-avant-1027 /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-1027 /opt/labuse/venv
sudo cp -a /etc/caddy/Caddyfile.avant-1027 /etc/caddy/Caddyfile && sudo systemctl reload caddy
sudo install -o root -g root -m 644 /root/labuse.service.avant-1027 /etc/systemd/system/labuse.service && sudo systemctl daemon-reload
sudo cp -a /root/served_manifest.json.avant-1027 /opt/labuse/app/config/served_manifest.json
sudo cp -a /root/served_run.txt.avant-1027 /opt/labuse/app/config/served_run.txt
sudo chown -R labuse:labuse /opt/labuse/app
sudo install -o root -g root -m 644 /root/cron.labuse.avant-1027 /etc/cron.d/labuse
sudo systemctl start labuse && curl -fsS http://127.0.0.1:8000/readyz
# Le schéma ajouté (colonnes/table en plus) RESTE — sans effet sur l'ancien code.
# Données : restaurer labuse-labuse-20261027-173056.dump SEULEMENT si l'ancien code ne fonctionne plus.
```

Verdict phase 1 : **VERT** (`✓ Sauvegarde OK (6.5G)` à 17:30→17:4x, contrôle `pg_restore --list` intégré passé).

---

## Phase 2 — schéma

Appliqué via `psql -f /tmp/phase2_schema.sql` (transaction unique, `ON_ERROR_STOP`) :
- `CREATE TABLE IF NOT EXISTS parcel_couche_intersection_build` (6 col., OWNER labuse) ;
- `ALTER TABLE parcel_residuel_runs ADD COLUMN IF NOT EXISTS surface_terrain_m2 integer` ;
- `CREATE TABLE IF NOT EXISTS parcel_zone_plu_version (sig text, built_at timestamptz DEFAULT now() NOT NULL)` (OWNER labuse).

Péripétie instructive : le premier passage a échoué proprement (transaction annulée) — `parcel_zone_plu_version` est une **table neuve à 2 colonnes** (pas 2 colonnes à ajouter), et `parcel_zone_plu.zone_filtre` existait déjà en prod en `varchar` (le diff la signalait à cause du type `text` côté Mac — équivalent, aucun geste).

Contrôle (re-diff information_schema) : résidu = `parcel_residuel.surface_terrain_m2` (vue, recréée par `labuse doctor` en phase 4), `v_parcelle_contact_compte` (vue, idem), `zone_filtre` varchar/text (inoffensif). **Zéro écart de schéma restant à la charge de la phase 2. VERT.**

---

## Phase 3 — données de fond

Tests de la routine joués côté Mac d'abord : `pytest tests/test_solidite1_lot4.py` → 5 passed (phase 1).

Commande (depuis le Mac, nohup → `/tmp/deploy_donnees_1027.log`) :
```
deploy/scripts/deploy_donnees.sh --run-label q_v20 --residuel-seq 17 --cascade-label q_v19_sources --no-bascule
```
`--no-bascule` : données posées, pointeurs INCHANGÉS — la bascule est en phase 5. Gardes de la routine : 1 sauvegarde fraîche (2ᵉ dump du jour — voulu par la routine), 2 disque ≥ 12 Go, 3 sync-run (checksum + comptages Mac==prod par table). Tables client et flux quotidiens non touchés (périmètre sync-run uniquement).

Déroulé :
- Garde 1 : dump `labuse-labuse-20261027-175225.dump` (6,5 G, `pg_restore --list` OK).
- Garde 2 : 19 Go libres (≥ 12). ✓
- Garde 3 (sync-run filtré) : charge utile 639 Mo (dump dérivés 15 Mo + CSV gz 624 Mo), checksum OK. Restore : COPY 433 229 ×4 (p_score_v2, dryrun_evals, score_labuse, residuel) + COPY **21 097 100** (cascade q_v19_sources) + runs/manifeste. `residuel_runs` seq 17 chargé `is_served=false` (bascule différée). ANALYZE joué.
- **Anomalie de script consignée** : la boucle de comptage « 5a » de `sync-run.sh` n'a vérifié QUE la première table — le `ssh` dans le `while read` avale le stdin (correctif suggéré : `ssh -n`). **Vérification refaite à la main sur les 14 tables : Mac == prod partout**, y compris `surface_terrain_m2` (265 123 non-NULL des deux côtés).
- Transit purgé après vérification : `/tmp/labuse_runsync*` VPS (7,4 G dont CSV en clair) + dumps/CSV Mac. Disque VPS après : 13 G libres.

**Phase 3 VERTE.**

---

## Phase 4 — code et config

1. `sudo systemctl stop labuse` → inactive.
2. `deploy/scripts/deploy_app.sh labuse-vps` (nohup → `/tmp/deploy_app_1027.log`) : garde manifeste (q_v20 présent en prod : 433 229) ✓ ; rsync (exclusions d'usage, ni manifeste ni .env) ; venv = `requirements.lock` + `-e . --no-deps`, **chaîne de démarrage importable ✓** ; front construit sur le VPS (dist 18:31, repli `q_v18` à ce stade — normal avant bascule) ; unité systemd installée (`--timeout-keep-alive 75` vérifié) + daemon-reload ; contrôle manifeste prod (q_v18, 433 229 lignes) ✓.
3. Note dépendances : `pandas` est déclaré en extras `[ml]`/`[ci]` (choix assumé du dépôt : la prod sert des scores précalculés) et déjà présent dans la venv prod (3.0.3, posé le 06/10) — la venv n'étant pas purgée, rien ne casse. `anthropic` épinglé 0.116.0 ✓.
4. Caddy : `deploy/Caddyfile.prod` → `/etc/caddy/Caddyfile`, **validé avec l'env du service** (`LABUSE_DOMAIN` vient de `/etc/caddy/labuse.env` — un `caddy validate` nu échoue faussement sur « encode », piège consigné), reload OK, **`read_timeout 75s` confirmé chargé** via l'API admin Caddy.
5. Crontab CIBLÉE (jamais régénérée) : retrait du bloc actif `recap-matin` (job retiré du registre COCKPIT-1 — la ligne aurait échoué chaque matin), ajout `signal-instantane` (`0 6 1 * *`, job vérifié présent dans le code déployé), **6 gelés « Phase 8 Stéphanie » intacts**, `agents-sources` toujours hors crontab (décision historique maintenue).
6. `labuse doctor` (service arrêté) : « Schéma réconcilié » ✓ — vue `parcel_residuel` recréée avec `surface_terrain_m2`. La vue `v_parcelle_contact_compte` n'est posée que par le backfill scoring (jamais joué en prod) → créée à la main (DDL exacte du code, OWNER labuse, 47 lignes). Le « NON PRÊT » restant de doctor = fiches de démo pré-chauffées/healthcheck-service-arrêté, hors mandat.
7. `sudo systemctl start labuse` → **readyz 200**, boot « env=production · auth=active · schéma=ok ».

**Phase 4 VERTE.**

---

## Phase 5 — bascule et caches

1. Premier `golden promote q_v20` : **REFUSÉ par la garde de pompe** — source `enp_complements` en quarantaine (contrôle bloquant `d_enp_reserve_marine` : la Réserve Nationale Marine absente de `spatial_layers`). Diagnostic : la version ENP ingérée le 13/09 a perdu la réserve marine ; la prod rejoue le filtre chaque matin (quarantaine depuis le 13/10 17:12, 15 rejeux KO) ; le Mac n'a jamais rejoué le filtre sur cette version (dernier verdict « ok » du 13/09) — d'où la bascule locale de Vic sans accroc le 21/10. Données STRICTEMENT identiques Mac/prod (0 entité marine des deux côtés). **Préexistant, non causé par le déploiement.**
   → **Décision Vic en session : « servir quand même »** — dérogation auditée posée (`servir_quand_meme=true`, servi_par « Vic (via DEPLOY-1027) », motif écrit). ⚠ Reste à faire hors mandat : ré-ingérer `enp_complements` pour retrouver la Réserve Marine.
2. `golden promote q_v20` ✓ (manifeste : scoring/mvt q_v20 · cascade q_v19_sources · précédent q_v18 = retour arrière) + `residuel-serve 17` ✓ (15 → 17, rebuild caches détaché).
3. **Division d'or** (oubli de ma phase 0, rattrapé) : le Mac sert `division_run=q_v19` (24 candidats — décision Vic 21/10) ; la prod n'avait AUCUN candidat q_v19/q_v20 (33 × q_v10_m129). **Décision Vic en session : copier + q_v19.** Copie des 33 candidats (PK=idu → upsert toutes-colonnes, la note de revue 97420000BH1036 suivait déjà côté Mac), **tables identiques vérifiées au md5** (15 q_v10 + 24 q_v19 + 9 q_v20 des deux côtés) ; manifeste `division_run` → `q_v19` via `manifeste.ecrire` ; restart ; readyz 200.
4. Front reconstruit post-bascule : repli `VITE_RUN_LABEL` = **q_v20** (lu de `served_run.txt`, vérifié dans le bundle).
5. `vefa-neuf-build` ✓ (10 communes peintes, 14 hachurées — recalculé sur les DVF de la prod, qui fait foi).
6. Tuiles : `build-mvt` lancé en nohup ; **course avec le rebuild détaché du residuel-serve** (deadlocks, crash du CLI build-mvt ; `parcel_zone_plu` néanmoins reconstruite à **430 320 = Mac**, écart de fond 0.4 résorbé). Le rebuild détaché (chemin sanctionné) continue ; `build-mvt` sera rejoué SEUL après sa fin pour les tuiles q_v20. Leçon consignée : ne pas lancer `build-mvt` tant que le rebuild post-`residuel-serve` tourne.
7. `build-intersections` : non joué, inutile — `parcel_couche_intersection` identique Mac/prod (1 607 877) et spatial_layers inchangées (seule VEFA a bougé, aplat commune non intersecté).

---

## Phase 6 — test de fumée en prod (https://app.labuse.immo)

Authentification : **session temporaire (2 h) frappée côté serveur pour le compte test admin `gb-test-ae@labuse.local` (id 31)** — autorisée par Vic en session ; cookie en fichier 600 sur le VPS, jamais affiché ; sessions purgées en fin de fumée (celle du compte QA 30, compte suspendu donc inopérante, purgée aussi). Le compte admin réel a un TOTP : pas utilisé.

### Trois réparations trouvées PAR la fumée (toutes faites)
1. **Pieds « Sources : » des PDF en ids bruts** (`ban`, `bd_topo`…) au lieu des noms publics : `exports/pieds.py` lit `docs/CIRCUIT/inventaire/reservoirs.csv` **au runtime** — or `deploy_app.sh` exclut `docs/` du rsync ET mon ménage de phase 1 a supprimé le vieux `docs/` du VPS qui le portait (l'affirmation DISQUE-VPS-1 « docs/ jamais lu au runtime » était fausse pour ce fichier). Reposé ciblé : `docs/CIRCUIT/inventaire/` (276 K) + `docs/audit-2026-09/SOURCES/SCHEMAS.csv` (160 K, lu par `circuit_garanties`) ; les scripts `verite_terrain*` (cron mensuel) font `mkdir(parents=True)` — rien d'autre à reposer. Restart (lru_cache). ⚠ À corriger au dépôt : sortir ces CSV de `docs/` ou les inclure au rsync.
2. **`/outils/gabarit/{idu}` en 500** : `labuse_hauteur_lidar_m(real)` ABSENTE en prod — `ensure_hauteur_lidar_fn` n'est appelée que par `create_all` (création initiale), jamais par `ensure_schema`/doctor (trou du dépôt à signaler ; `labuse_zone_famille`, elle, était posée par `ensure_residuel_cache`). Fonction créée avec la DDL exacte du code (plafond 60 m, IMMUTABLE), bornes vérifiées (12,5→12,5 · 999→NULL · −1→NULL). Gabarit 3D → 200 en 0,85 s.
3. Les PDF générés AVANT ces réparations n'étaient pas représentatifs → régénération complète pour les comparaisons.

### Mesures (requêtes réelles via Caddy, session)
- Fiche parcelle BY0083 (`/parcels/{idu}?source=q_v20`) : **0,08–0,13 s** à chaud (3 mesures) ; 6,3 s au premier hit à froid pendant les rebuilds.
- 8 documents : dossier 200 (34,6 s) · apporteur 200 (2,4 s) · étude-zone 200 (50,7 s) · gabarit 200 (1,1–3,5 s) · comparatif 3 parcelles 200 (10,4 s) · **étude de faisabilité 24 T1 aérien : écran 200 en 30,4 s, PDF 200 en 33,5 s — < 75 s ✓** · pré-dossier 200 (69,3 s) · bilan (ci-dessous).
- Bilan : export à vide → **422** (« aucun chiffre d'affaires ») ✓ ; après saisie d'un programme (24 lots) → **200** (1,4 s) ✓. (2 documents créés sur le compte test : doc_id 5 et 6.)
- 3 outils : Gabarit 3D **200** (0,85 s) · Étude de zone **200** (17,9 s) · Scan patrimoine **200** (8,3 s).
- ⚠ Pendant le `build-mvt` complet (PostGIS saturé), un dossier régénéré a fait 500 (`QueryCanceled : statement timeout`) et un pré-dossier 504 — induits par la charge du build, pas par le code ; re-vérifiés après la fin du build (ci-dessous).

### Tuiles (fin de phase 5, constatée ici)
`build-mvt` complet terminé : `mvt_parcels` reconstruite (433 229, label q_v20), 300 tuiles parcelles z9-11 + 1 678 tuiles overlays préchauffées, cache purgé des versions q_v18. `/map/tiles/meta` : **run_label q_v20 · perime:false**. Au passage, `parcel_couche_intersection` « servitudes déjà à jour » confirmé par le build lui-même.

### Après stabilisation : les 8 documents régénérés, cohérence, référence
- 8/8 en 200, temps sans charge : dossier 15,3 s · apporteur 2,0 s · étude-zone 16,1 s · gabarit 1,9 s · comparatif 12,6 s · étude-faisa 31,5 s · pré-dossier 35,7 s · bilan 1,8 s.
- `scripts/docs_coherence.py` contre `https://app.labuse.immo` (copie /tmp à 3 lignes près : en-tête Cookie de la session de fumée — aucune porte d'auth contournée) : **0 écart sur 18 données partagées** ✓. (Un premier passage pendant les rebuilds donnait 1 écart 1736/1699 — artefact de génération en vol, disparu.)
- Texte des 8 PDF prod vs `reports/DOCS-COHERENCE-1/pdf-final/` (dates exclues) : **gabarit et étude-faisa IDENTIQUES** ; dossier 0,9993 et pré-dossier 0,9973 (résidu = uniquement les prix DVF — 3 602 €/m²/15 ventes réf → 4 125 €/m²/12 ventes prod — la PROD FAIT FOI sur DVF, et l'ordre d'extraction d'un libellé) ; apporteur 0,94 (bloc émetteur présent : généré en session vs mode local pour la référence) ; étude-zone 0,97 et comparatif 0,97 (prix/propriétaires DVF-PM prod) ; bilan 0,84 (mes saisies de test ≠ programme de la référence, par construction). **Mêmes chiffres partout où la donnée est de fond. ✓**
- Journaux du service sur 10 minutes : **0 ERROR/Traceback/CRITICAL, 0 HTTP 5xx**. ✓
- Nettoyage : sessions de fumée purgées (30 et 31), cookie et fichiers /tmp supprimés. Restent 2 documents Bilan de test (doc_id 5 et 6) dans « Mes documents » du compte gb-test-ae (table client — non touchée, à purger avec les autres artefacts [GB-TEST] déjà recensés).

**Phase 6 VERTE — déploiement validé.**

---

## Phase 7 — après

1. Fumée verte → `/opt/labuse/app-avant-1027` et `/opt/labuse/venv-avant-1027` **supprimés**. (Les copies de config `/root/*.avant-1027` — unité, Caddyfile, manifeste, crontab — restent : quelques Ko, utiles en référence.)
2. **Rotation des rapatriements Mac** :
   - Pourquoi rien depuis le 24/10 : le 24/10 le pull a échoué EN PLEIN rsync (« No space left on device » — le Mac était plein, 5 dumps empilés faute de rotation dans la vieille copie `~/.labuse/ops/pull_backups.sh`), une tentative a aussi échoué réseau (« Network is unreachable ») ; le 26/10 10:48 un pull a RÉUSSI (24+25+26 rapatriés) mais sans rotation ; le 27/10 au passage de 07:30 il n'y avait rien de plus récent à prendre (le dump quotidien VPS tombe à 13:49 Réunion = après le pull du matin).
   - Correctif : `deploy/scripts/pull_backups.sh` durci — **refus de télécharger sous 15 Go libres, écrit au journal** (en plus de la rotation existante « 2 dumps conservés, après pull vérifié ») ; copie posée dans `~/.labuse/ops/pull_backups.sh` (la cible launchd). `bash -n` OK, 10 tests pull/rotation passants.
   - Rapatriement relancé : les dumps du 27/10 descendus, rotation locale à 2. `hebdo-…-20261018.dump` conservé à part sur le Mac (rapatrié en phase 1, hors glob de rotation). `M7_SECRETS.txt` non touché.
3. Ce rapport, commité et poussé.

---

## Synthèse

**Déployé et validé** : main `f28550160` en prod — 4 recettes d'outils, Étude de faisabilité V6 (60 s moteur / 75 s bout en bout), DOCS-COHERENCE-1. La prod sert **q_v20 / q_v19_sources / résiduel 17 / division q_v19** (précédent q_v18 en retour arrière), front repli q_v20, tuiles q_v20 préchauffées, crontab ciblée (−recap-matin, +signal-instantane, gelés intacts).

**Décisions de Vic en session** : ménage disque complet ; « servir quand même » `enp_complements` (dérogation auditée) ; copie division q_v19+q_v20 + manifeste division q_v19 ; session de fumée gb-test-ae.

**À faire ensuite (hors mandat, par priorité)** :
1. **Ré-ingérer `enp_complements`** (DEAL Carmen) pour retrouver la Réserve Nationale Marine et lever la dérogation — le contrôle `d_enp_reserve_marine` restera rouge tant que la donnée amont n'est pas réparée ; rejouer le filtre sur le Mac aussi (son verdict « ok » du 13/09 est périmé).
2. **Dépôt** : (a) `ensure_hauteur_lidar_fn` (et toute fonction SQL) à appeler depuis `ensure_schema`/doctor, pas seulement `create_all` ; (b) `docs/CIRCUIT/inventaire/*.csv` + `docs/audit-2026-09/SOURCES/SCHEMAS.csv` sont LUS AU RUNTIME mais exclus du rsync de `deploy_app.sh` (et DISQUE-VPS-1 les croyait morts) — les sortir de `docs/` ou les inclure à l'envoi ; (c) `sync-run.sh` 5a : `ssh -n` (le ssh avale le stdin du `while read`, une seule table vérifiée) ; (d) `labuse parite` : la 1ʳᵉ table absente aborte la transaction et masque les suivantes ; (e) le générateur `jobs crontab` sort en TZ système (UTC sur Mac) — gênant pour les diffs.
3. **Disque VPS à 88 %** : le gros reliquat est en base — runs morts (q_v16 scoring, q_v13_sources1 cascade 17,6 M lignes…) à passer à `menage_disque.sh --execute` avec ta liste KEEP (q_v20 servi · q_v18 précédent · q_v11_m137 secours), en heure creuse.
4. Purge base des artefacts `[GB-TEST]` (SQL déjà fourni par la recette, ids 91→132) + les 2 bilans de test doc_id 5/6.
5. Fiches de démo : `labuse rebuild-demo --commune 97415` + `labuse warm-demo` (le doctor les signale 2/8 pré-chauffées — préexistant).
