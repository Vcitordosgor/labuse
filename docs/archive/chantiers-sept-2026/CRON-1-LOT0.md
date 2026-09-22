# CRON-1 · Lot 0 — Table rase : inventaire des jobs existants

**Branche** `feat/cron-1` · **départ** `main 403526eb`. Lecture (dont **observation VPS en lecture seule**, sanctionnée par le mandat) puis suppression des deux anciens jeux du dépôt. **Aucun job posé en prod.**

## État réel du VPS (observé en lecture seule — `ssh labuse-vps 'ls /etc/cron.d/ ; crontab -l'`, 18/09)

- `/etc/cron.d/` porte **exactement les 11 fichiers `labuse-*` LEGACY** (abuse, backup, ban, bodacc, dpe, dvf, fraicheur, notifications, radar, sessions, sitadel), datés du 27/08, **et rien d'autre**.
- `crontab -l` (root et `labuse`) est **vide**.
- **Le wrapper (`deploy/cron.d-labuse`) n'a JAMAIS été posé** : aucun fichier `/etc/cron.d/labuse` (sans suffixe). Ce qui tourne en prod = **les 11 legacy**, confirmé par les mtimes des logs `/var/log/labuse/*.log`.
- ⚠️ `deploy/cron.d/OBSOLETE.md` affirmait « le seul jeu déployé est le wrapper » — **c'est faux** : la réalité VPS est l'inverse (legacy encore seul posé). C'est exactement le désordre que ce mandat efface.

## Les deux anciens jeux — tableau

### Jeu A — LEGACY `deploy/cron.d/*` (11 fichiers, **13 jobs**) — **posés & actifs sur le VPS**

| Job (commande) | Cron (UTC) | Touche | En prod | Dernier passage (mtime log VPS) |
|---|---|---|---|---|
| `abuse-scan` | `0 10 * * *` | exploitation | **oui** | 18/09 10:00 |
| `backup_postgres.sh` | `30 9 * * *` | exploitation | **oui** | 18/09 09:41 |
| `db_maintenance.sh` | `0 8 * * 0` | exploitation | **oui** | 13/09 08:00 |
| `ingest-ban --download` | `30 7 5 * *` | eau | **oui** | 05/09 07:33 |
| `ingest-bodacc` + `fraicheur-derives` | `30 6 * * *` | eau | **oui** | 18/09 06:35 |
| `ingest-dpe` + `fraicheur-derives` | `20 9 * * 2` | eau | **oui** | 15/09 09:22 |
| `refresh-dvf` + `fraicheur-derives` | `0 9 * * 3` | eau | **oui** | 16/09 09:00 |
| `check-fraicheur` | `30 10 * * *` | eau | **oui** | 18/09 10:30 |
| `evaluer-suivis`/`evaluer-veilles`/`notifier-fraicheur`/`purge-notifications`/`digest quotidien` | `0 7 * * *` | exploitation | **oui** | 18/09 07:00 |
| `radar-sources` | `0 6 * * 1` | eau | **oui** | 14/09 06:00 |
| `purge-sessions` | `0 8 * * *` | exploitation | **oui** | 18/09 08:00 |
| `permits_sdes --refresh` + `fraicheur-derives` | `15 6 * * *` | eau | **oui** | 18/09 06:18 |
| `fraicheur-derives --hebdo` | `45 7 * * 1` | eau | **oui** | (log `sitadel_refresh.log`) |

### Jeu B — WRAPPER `deploy/cron.d-labuse` + registre `labuse.jobs.JOBS` (**23 jobs** ; 21 au crontab, 2 désactivés) — **jamais déployé (0 posé)**

| Job (`labuse jobs run …`) | Cron (UTC) | Touche | En prod | Dernier passage |
|---|---|---|---|---|
| `backup-postgres` | `45 1 * * *` | exploitation | non | jamais posé |
| `sources-fraicheur` | `0 2 * * *` | eau | non | jamais |
| `radar-cycle` | `30 2 * * *` | eau | non | jamais |
| `radar-digests` | `0 14 * * *` | exploitation | non | jamais |
| `fiche-commune-cache` | `0 23 * * *` | eau | non | jamais |
| `copilote-purge` | `30 23 * * *` | exploitation | non | jamais |
| `healthcheck` | `*/15 * * * *` | exploitation | non | jamais |
| `sante-endpoints` | `7,37 * * * *` | exploitation | non | jamais |
| `pg-maintenance` | `0 0 * * 0` | exploitation | non | jamais |
| `rapport-admin` | `15 2 * * 1` | exploitation | non | jamais |
| `ingest-bodacc` | `40 2 * * *` | eau | non | jamais |
| `ingest-sirene` | `0 0 7 * *` | eau | non | jamais |
| `ingest-sitadel` | `30 0 10 * *` | eau | non | jamais |
| `ingest-dpe` | `0 0 12 * *` | eau | non | jamais |
| `sync-gpu` | `0 0 15 * *` | eau | non | jamais |
| `sentinelle-sources` | `0 3 * * *` | eau | non | jamais |
| `radar-releves` | `0 13 * * *` | eau | non | jamais |
| `filtres-sources` | `5 3 * * *` | eau | non | jamais |
| `coherence-run` | `15 3 * * *` | eau | non | jamais |
| `coherence-robinets` | `25 3 * * *` | eau | non | jamais |
| `restore-test` | `0 1 1 * *` | exploitation | non | jamais |
| `agents-sources` (désactivé) | `0 0 3 * *` | exploitation | non | jamais posé (à la demande) |
| `regles-references` (désactivé) | `0 0 4 * *` | exploitation | non | jamais posé (à la demande) |

### Recoupements (mêmes données servies par les deux jeux, cadences DIVERGENTES)
- **bodacc** : legacy `30 6 * * *` (06:30 UTC) ↔ wrapper `40 2 * * *`.
- **dpe** : legacy hebdo `20 9 * * 2` ↔ wrapper mensuel `0 0 12 * *`.
- **sitadel** : legacy quotidien `15 6 * * *` ↔ wrapper mensuel `30 0 10 * *`.
- **backup** : legacy `30 9 * * *` ↔ wrapper `45 1 * * *`.
- **fraîcheur / sentinelle / cohérence** : dispersés entre `check-fraicheur` (legacy) et `sources-fraicheur`/`sentinelle-sources`/`filtres-sources`/`coherence-*` (wrapper).

## Suppression

Supprimés du dépôt (les deux jeux de **crontab déployables**) :
- `deploy/cron.d/` — 11 fichiers legacy + `OBSOLETE.md` ;
- `deploy/cron.d-labuse` — le wrapper.

**Jobs jetés : 34 lignes de crontab** (13 legacy + 21 wrapper) ; 36 définitions avec les 2 désactivés.

Les **implémentations** (`labuse.jobs` / `jobs_impl.py` — les fonctions backup, sentinelle, cohérence, ingestions…) sont **conservées** : le lot 1 en refait **un seul registre** (nom · cadence · **raison** · eau/exploitation · **test**) d'où le crontab sera GÉNÉRÉ. Aucun job ne « survit » comme crontab ; ce qui a une raison sera réinscrit au lot 1, le reste jeté.

Tests qui lisaient ces fichiers (assertions sur les artefacts supprimés) neutralisés ici, à re-porter sur le registre/`deploy.sh` aux lots 1–3 : `test_circuit1_lot8` (crontab==registre), `test_circuit4_lot5` (job jamais posé), `test_ingest_permits_cablage` (voie sitadel), `test_ops_healthz` (OBSOLETE.md/deploy.sh).
