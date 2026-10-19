# CRON-PROD-1 — les 6 crons que `/healthz/crons` signalait « en défaut » (19/10)

Diagnostic **lecture seule sur le VPS** (crontab, registre, journaux, états JSON) puis correctif sur
`fix/crons-prod`. Aucune modification faite sur le VPS.

## Constat healthz

`GET /healthz/crons` (servi par l'API, `labuse.api.ops`) surveille les jobs qui *touchent l'eau* +
`backup-postgres`, et qui sont `planifie`. Six d'entre eux lisent leur dernier passage dans un
**fichier d'état JSON** (`trace == "etat_json"`) : `sonde-sources`, `filtres-sources`,
`coherence-robinets`, `sync-gpu`, `ingest-dvf`, `backup-postgres`. Ce sont exactement les six en défaut.
Les `ingest-bodacc/dpe/sirene/sitadel` lisent la **DB** (`data_sources`/`ingestion_runs`), insensible au
bug ci-dessous — ils étaient verts.

## Cause prouvée (par cron)

| Cron | Dans crontab ? | Registre ? | Se lance ? | État lu par l'API | Cause |
|---|---|---|---|---|---|
| sonde-sources | oui (07:00) | oui | **oui** — log `/var/log/labuse/jobs/sonde-sources.log` 19/10 07:03, état `/home/labuse/.local/state/jobs/sonde-sources.json` `fin 2026-10-19T03:03Z statut ok` | `/opt/labuse/app/.local/state/jobs/…` `fin 2026-09-22` | **chemin d'état relatif résolu contre le CWD** |
| coherence-robinets | oui (07:25) | oui | **oui** — log 19/10 07:42, état `fin 2026-10-19 ok` | stale `fin 2026-09-22` | idem |
| filtres-sources | oui (07:05) | oui | **oui** — log 19/10 07:05, état `fin 2026-10-19 ok` | **fichier absent** → `jamais_vu` | idem (jamais écrit dans le dir lu par l'API) |
| sync-gpu | oui (04:00 le 15) | oui | **oui** — log 15/10 04:00, état `fin 2026-10-15 ok` | **fichier absent** → `jamais_vu` | idem |
| backup-postgres | oui (13:30) | oui | **oui** — log 19/10 13:48, état `fin 2026-10-19 ok`, **dump du 19/10 présent** | stale `fin 2026-08-30` | idem |
| ingest-dvf | **commenté `# GELÉ (Phase 8 Stéphanie)`** | oui (`planifie=True`) | non (gel volontaire) | fichier absent → `jamais_vu` | **gel invisible du registre/healthz** |

**Racine des 5 premiers — un seul défaut :** `config.Settings.jobs_state_dir` valait `.local/state/jobs`
(RELATIF). `Path(...)` le résout contre le **CWD du process** :
- le **cron** tourne avec `CWD = /home/labuse` → écrit l'état dans `/home/labuse/.local/state/jobs/` (frais, vérifié) ;
- l'**API** tourne sous systemd avec `WorkingDirectory = /opt/labuse/app` → **lit** `/opt/labuse/app/.local/state/jobs/`,
  un **snapshot gelé** de l'ancien déploiement (`backup-postgres` 30/08, `sonde`/`robinets` 22/09, les autres jamais créés).

C'est le **même CWD** que celui qui, le 13/10, a fait passer les logs de `/var/log/labuse/*.log` au
sous-dossier `/var/log/labuse/jobs/` : les deux process (cron vs API) ont divergé.

**ingest-dvf :** gelé pour de vrai (Phase 8 Stéphanie, dégel DVF après la recette de restauration). Il
n'était figé que par un **commentaire posé à la main** dans le crontab (`poser_crontab_solidite.sh`),
donc le registre le croyait actif et `/healthz/crons` le comptait `jamais_vu` → fausse alerte.

## Correctif (`fix/crons-prod`)

1. **Racine (5/6)** — `config.py` : un `@model_validator` ancre tout dossier job RELATIF
   (`jobs_state_dir`/`jobs_log_dir`/`jobs_lock_dir`) sur **`$HOME`** (sémantique XDG de `.local/state`).
   Cron et API tournent tous deux sous `labuse` → convergent sur `/home/labuse/.local/state/jobs/`,
   **là où les états frais existent déjà**. Un chemin ABSOLU (env prod, tests en tmp) passe inchangé.
2. **Gel volontaire (ingest-dvf)** — nouveau champ `Job.gel` (motif court). Un job gelé :
   - est émis **commenté** par le générateur de crontab (`cli._crontab_du_registre`) → `deploy.sh` qui
     régénère depuis le registre **ne perd plus le gel** (le hack `poser_crontab_solidite.sh` devient inutile) ;
   - est classé **`gele`** par `/healthz/crons` **sans dégrader** `ok` (gel assumé ≠ panne) ;
   - est **ignoré** par la vigie « jobs en retard » (`ops_alertes._jobs_en_retard`).
   Marqués gelés : `ingest-dvf` + les 6 exploitations déjà commentées en prod (`radar-cloche`,
   `radar-cycle`, `radar-cycle-dvf`, `radar-cycle-mensuel`, `digest`, `restore-test`).
3. **Défense en profondeur** — `deploy/env/labuse.env.example` documente les 3 dossiers EN ABSOLU.

**Preuve :** `labuse jobs crontab --tz reunion` est désormais **byte-identique** à `/etc/cron.d/labuse`
(seul ajout légitime : `signal-instantane`, job récent absent du crontab déployé — un redeploy le pose).
Tests : `tests/test_crons_prod_fix.py` + suite cron/healthz/radar/veille verte.

## À faire au déploiement (pour que les 6 repassent au vert)

Toutes les corrections sont dans le code ; aucun run de données. Après merge de `fix/crons-prod` :

1. **Déployer le code** (`deploy_app.sh`) puis **redémarrer l'API** : `sudo systemctl restart labuse`.
   → l'API lit alors `/home/labuse/.local/state/jobs/` (états frais) ⇒ `sonde-sources`, `filtres-sources`,
   `coherence-robinets`, `sync-gpu`, `backup-postgres` passent **`ok`** immédiatement (pas besoin d'attendre
   le prochain cron ; `sync-gpu` reste `ok` jusqu'au 15/11 car cadence mensuelle, âge < 35 j).
2. **(Recommandé) Verrouiller l'env** — ajouter à `/etc/labuse/labuse.env` :
   ```
   LABUSE_JOBS_STATE_DIR=/home/labuse/.local/state/jobs
   LABUSE_JOBS_LOG_DIR=/var/log/labuse/jobs
   LABUSE_LOCK_DIR=/run/lock
   ```
   puis `sudo systemctl restart labuse`. (Rend le correctif indépendant de `$HOME` ; répare aussi le
   visualiseur de logs admin `GET /admin/cron/{nom}/log`, qui lisait un dossier relatif vide.)
3. **ingest-dvf** restera `gele` dans `/healthz/crons` (statut informatif, **plus d'alerte**) tant que
   la Phase 8 n'est pas levée. Dégel le moment venu = retirer `gel=...` du registre (et le job repasse
   actif au crontab régénéré).
4. **(Optionnel, cosmétique)** supprimer le dossier orphelin `/opt/labuse/app/.local/state/jobs/` (et
   `/opt/labuse/app/.local/log/`), désormais plus lus.

Vérification : `curl -s https://app.labuse.immo/healthz/crons | jq '.ok, .crons'` → `ok:true`,
chaque cron `ok` sauf `ingest-dvf` = `gele`.
