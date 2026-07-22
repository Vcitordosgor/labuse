# M7 — MISE EN LIGNE DE LABUSE (app.labuse.immo) — rapport final

Mode autonome, un seul rendez-vous : **GOLDEN 116/116 PASS contre la production** (22/07/2026, ~02:50
heure Réunion). Branche versionnée : `m7/mise-en-ligne` (pushée, Vic merge — je ne merge pas).
Gel des écritures locales annoncé et tenu pendant la fenêtre dump→restore (aucun batch local).

## Ce qui tourne, et où

| Brique | État |
|---|---|
| **VPS-3** `51.255.163.56` (vps-5563949c, Ubuntu 24.04, 6 vCPU, 11 GB RAM, 96 GB) | durci |
| SSH | **clés uniquement** (`00-labuse-hardening.conf`), root off, mot de passe initial **mort** à la 1ʳᵉ connexion ; fail2ban actif |
| ufw | SSH 22 rate-limité + 80/443, deny entrant par défaut — activé avec **filet anti-lock-out** (timer systemd) et **session fraîche vérifiée** |
| PostgreSQL | **18.4 + PostGIS 3.6** (PGDG — même majeure que le local, exigence dump 18), base `labuse`, rôle `labuse`, **timezone `Indian/Reunion`** (alignée local) |
| App | systemd `labuse.service` (uvicorn 2 workers, 127.0.0.1:8000, `LABUSE_ENV=production`, `LABUSE_SERVED_RUN=q_v7_defisc`), secrets dans `/etc/labuse/labuse.env` (640) |
| Front | **construit sur le VPS** (`VITE_RUN_LABEL=q_v7_defisc`), servi sous `/socle/` |
| Tuiles | `build-mvt` exécuté sur le VPS : 431 663 parcelles, `mvt_meta.run_label=q_v7_defisc` (3 min 41) |
| Caddy | **TLS Let's Encrypt obtenu au 1ᵉʳ essai** + **rideau basic auth TOTAL** (user `labuse`) — temporaire jusqu'à l'auth comptes post-M7 |
| DNS | `app.labuse.immo → 51.255.163.56` (posé par Vic, TTL 300) — **aucune action DNS restante** |

## Migration comptée (garde-fous tenus)

Dump réutilisé (< 24 h, **3,8 GB**, aucune écriture locale depuis) → transfert **2 min** (md5 vérifié
`5567659208ff`) → base distante **vide vérifiée** (seule `spatial_ref_sys`) → `pg_restore -j 4` **4 min 44**
→ `ANALYZE`. **Comptages : TOUS EXACTS** — parcels **431 663**, `q_v7_defisc` **431 663**, `q_v6_m8`
**431 663**, defisc 1 166 (797 actives), pc_caducs 2 164, score_e 77 718 (51 926 estimables), outils
62/11 784/123, dormantes spin-off intactes. Écart initial d'inventaire diagnostiqué et résorbé :
`rgealti_pente_5m` (raster) exigeait `postgis_raster` — extension créée, table restaurée (2 793 dalles,
226 tables = 226). Fenêtre bascule données totale : **~10 min**.

## Exposition (décisions appliquées)

Table OUTILS_SUITE telle quelle : Score É **exposé** (`niveau_label` visible), O1-O7/O9/O11 servis,
**O8 masqué**, **O12 masqué** (revue 20 cartes en attente), Surface D moteur seul. Badge forme juridique
O11 : **non trivial** (nécessite jointure forme_juridique dans la détection) → **post-M7** (J+2).

## Le juge, puis le rideau

- **GOLDEN : 116/116 PASS, 0 FAIL, 0 incohérence base↔API — contre `https://app.labuse.immo`**
  (rideau + login réels), face DB via tunnel SSH. C'est la **baseline golden prod** (`/tmp/golden_prod6.log`
  du 22/07). Voie QA documentée ci-dessous — **jamais dev_mode**.
- **Smoke 13/13** : healthz, healthz/crons, fiche brûlante, recherche, filtres defisc/caduc, anti-fiche,
  export CSV, tuiles meta + une tuile MVT, front, **scoreur d'adresse live** (BAN → parcelle réelle),
  **dossier banquier PDF (270 KB)**, **dossier Flash PDF (129 KB)**.
- `test_run_serving_coherence` **vert contre la prod** (backend = front = tuiles = `q_v7_defisc`).
- **Vérification extérieure** : le Mac (La Réunion) est réseau-extérieur au VPS (Gravelines) — TLS valide,
  rideau 401 sans credentials ; Let's Encrypt a de plus validé le port 80 depuis SES serveurs (preuve
  d'accessibilité publique indépendante).
- **Mise en service publique = faite** : DNS déjà posé + Caddy actif → l'app est en ligne **derrière le
  rideau** (état final voulu de ce mandat). Aucune action restante pour Vic côté DNS.

## Voie QA du golden en prod (documentée)

```
LABUSE_QA_TARGET=https://app.labuse.immo
LABUSE_QA_BASIC=labuse:<mdp rideau>          # traverse le basic auth Caddy
LABUSE_QA_PASSWORD=<mdp pilote>              # login app → cookie session
LABUSE_DATABASE_URL=postgresql://labuse:<mdp pg>@127.0.0.1:15432/labuse   # face DB via tunnel :
ssh -N -L 15432:127.0.0.1:5432 labuse-vps
```
+ `LABUSE_QA_ALLOWLIST` (env VPS) = IP publique du Mac : exempte le golden du rate-limit **sans toucher
au régime des clients** (nécessite `LABUSE_TRUSTED_PROXIES=127.0.0.1` — posé — pour que l'app voie l'IP
réelle derrière Caddy). Si l'IP du Mac change : mettre à jour l'allowlist dans `/etc/labuse/labuse.env`.

## Backups (jour 1, PROUVÉS)

- **VPS** : `deploy/cron.d/backup` (3h, `backup_postgres.sh`, rotation 7) — **testé réellement** :
  dump 3,8 GB produit sur le VPS.
- **Rapatriement** : **pull depuis le Mac** (le VPS ne détient aucun credential vers chez nous) —
  `pull_backups.sh` **testé réellement** (rapatrié + intègre, 970 objets listés par pg_restore 18),
  **LaunchAgent macOS posé** (`immo.labuse.pull-backups`, 7h30 quotidien, log `~/labuse-backups/pull.log` — crontab refusé par les permissions macOS, launchd est la voie native).
- Les 5 cron.d actifs : sitadel, ban, catnat, abuse, backup (le cron solaire mort a été retiré au pré-vol).
  État observable : `GET /healthz/crons`.

## Secrets

Tous dans `/etc/labuse/labuse.env` (640) et `/etc/caddy/labuse.env` (600) sur le VPS. Copie de référence
**locale, hors git** : **`~/labuse-backups/M7_SECRETS.txt`** (600) — mot de passe PG, mot de passe pilote,
secret de session, et le **basic auth du rideau** (`labuse:<voir fichier>`). Rien dans le dépôt.

## RUNBOOK — rollback en 10 minutes

1. **Le Mac peut reprendre le serving à tout moment** : la base locale est intacte (rien n'a été retiré) ;
   `labuse api --port 8010` tourne déjà en local.
2. **DNS** : TTL 300 s → pointer `app.labuse.immo` ailleurs (ou le retirer) prend effet en ~5 min chez
   Cloudflare (interdit de toucher au reste de la zone).
3. **Ou sans DNS** : `ssh labuse-vps 'sudo systemctl stop caddy'` — le rideau tombe avec le service,
   plus rien n'est exposé (ufw ne laisse que 22/80/443, l'API n'écoute que localhost).
4. **Données** : dump migration `~/labuse-backups/labuse_m7_20260721.dump` + backup VPS rapatrié
   `~/labuse-backups/vps/…dump` (intègre, testé) — restaurables via pg_restore 18
   (`PG_RESTORE_BIN=…/labusedb/bin/pg_restore`).
5. Resynchronisation ultérieure Mac→VPS : re-dump/restore (fenêtre mesurée ~10 min) — procédure §Migration.

## Sync des tables de run (le Mac calcule, le VPS sert)

Après un recompute local (gel-cascade, retrain, nouveau run servi) : dump ciblé des tables de run
(`parcel_p_score_v2`, `p_score_v2_runs`, `dryrun_*` du label, badges recalculés, `score_e`…) →
restore VPS → `labuse build-mvt` sur le VPS → golden. Un script dédié est listé en J+2 (premier besoin
réel au prochain run).

## Incidents de mise en ligne (tous diagnostiqués, aucun contournement silencieux)

1. `cv2` manquant (dépendance implicite hors pyproject) → `opencv-python-headless` installé ; **J+2 :
   déclarer la dépendance**. 2. Pango/gdk-pixbuf manquants (WeasyPrint) → installés ; **J+2 : ajouter au
   vps_setup.sh**. 3. Hash bcrypt mangé par un heredoc non quoté → réécrit côté VPS (leçon consignée).
4. Golden 84/116 ×3 : CA manquants (urllib venv) → contexte certifi (versionné) ; puis backend en boot
   pendant le run (boot ~20-25 s + **verrous du pg_dump concurrent** — leçon : jamais de restart pendant
   un backup) ; 5. 99/116 : **timezone** (`Etc/UTC` vs `Indian/Reunion`, dates permis à −1 jour) →
   `ALTER DATABASE … SET timezone` (config, zéro donnée modifiée) → **116/116**. 6. Motif rsync du
   rapatriement (`labuse_*` vs `labuse-*`) + pg_restore 16 du PATH → corrigés dans le script.

## Liste J+2 (premier mandat post-M7)

1. Déclarer `opencv-python-headless` (+ pango dans vps_setup.sh) — dépendances implicites découvertes.
2. Script `sync-run.sh` (dump/restore ciblé des tables de run + build-mvt + golden).
3. Badge forme juridique O11 (jointure non triviale).
4. Monitoring extérieur (uptime + alerte sur `/healthz/crons`) — le healthz existe, le poller manque.
5. Boot : envisager `--workers 1` au startup DDL puis reload 2 workers, ou readiness gate systemd
   (ExecStartPost curl) — le boot ~25 s expose une fenêtre 502 au restart.
6. Revue O12 (20 cartes) → décision d'exposition. 7. Clé ANTHROPIC (IA en repli déterministe pour l'instant).
8. Basic auth : tombera avec l'auth comptes (post-M7) — le mdp du rideau est chez Vic (M7_SECRETS).

---

## POST-REVIEW VIC — incident « vieille UI » : diagnostic, fix, leçon outillée

**Constat Vic (navigateur)** : la racine servait l'UI Vue HISTORIQUE (« Radar foncier », shortlist
mono-commune 51 129, spinner infini) — pas le front M2.

**Diagnostic (la cause exacte)** : dans le backend, `/` fait `RedirectResponse("/app/")` et le POST
`/login` renvoie **303 → `/app/`** ; `/app` = `StaticFiles(WEB_DIR)` = le prototype Vue « de transition ».
Le front M2 était bien servi… sous **`/socle/`** (base vite `/socle/`), que mon smoke validait en 200.
L'incident est né là : **« une page répond » ≠ « la bonne app répond »**.

**Fix (Caddy = source de vérité du front en prod, zéro code produit touché)** :
- dist **rebuildé `--base=/`** sur le VPS (`VITE_RUN_LABEL=q_v7_defisc`) et servi **statiquement à la
  racine** par Caddy (shell + assets) ; API/tuiles/login/PDF en proxy.
- **`/app` et `/app/*` ne sont JAMAIS exposés** (301 → `/`) — choix : la vieille UI reste montée dans le
  backend pour le dev local (aucun refactor du monolithe la veille), la prod ne la voit pas ; le 301
  neutralise aussi le 303 post-login du backend.
- Navigation `/` **sans cookie de session → 302 `/login`** (matcher Caddy sur l'absence du cookie) : le
  front React n'a pas d'écran de login — flux rideau → login → app, temporaire jusqu'à l'auth comptes.
- Vérifié bout en bout : `/` sans session → login ; login → cookie → `/` sert le shell React ; bundle
  `/assets/index-BuYFaYH5.js` contient les **marqueurs M2** (« Scorer une adresse », « Pourquoi pas ? »,
  « Afficher l'analyse LABUSE »). ⚠ le `<title>` est identique entre vieille et nouvelle UI — le titre ne
  discrimine PAS, d'où le marqueur bundle.

**Leçon OUTILLÉE** : **`qa/smoke_prod.sh`** (versionné) — exige le rideau fermé (401 nu), le flux
login, et **le MARQUEUR M2 dans le bundle servi à la racine** ; un 200 ne suffit plus jamais. Run : VERT.

**Re-vérification complète post-fix** : **GOLDEN 116/116 PASS** (exit 0) · smoke endpoints 8/8 (dont PDF
banquier, tuile MVT, assets) · marqueur M2 ✓. **Hygiène** : le mot de passe du rideau a transité dans un
log de session (redirect_url de curl) → **roté immédiatement** (nouveau mdp actif, uniquement dans
`~/labuse-backups/M7_SECRETS.txt` ; l'ancien est refusé).
