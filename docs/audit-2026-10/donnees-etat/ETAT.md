# ETAT.md — ce qui tourne vraiment

*DONNEES-ETAT-1 · 20/10/2026 · lecture seule. Preuves : base locale servie **q_v19** (`config/served_manifest.json`, promu 19/10), base prod **q_v18** (VPS, promu 13/10), `/etc/cron.d/labuse` (régénéré 20/10), table `job_runs` prod (3 007 lignes, du 13/10 au 20/10).*

> **Fait majeur.** Le **registre de jobs** (31 jobs, `src/labuse/jobs.py`) est **réellement posé en prod** depuis le 13/10 (`/etc/cron.d/labuse`, 24 lignes actives + 6 commentées gelées). Les crons tournent et laissent une ligne durable à chaque passage. **Prod sert q_v18 ; le Mac a déjà calculé et basculé q_v19 en local — q_v19 n'est PAS déployé.** Prod a donc **un run de retard** (assumé : les branches de fix sont « poussées non mergées »).

## Verdicts par étage

Légende : **MARCHE** (tourne et produit) · **TOURNE SANS EFFET** · **JAMAIS TOURNÉ** (depuis que le registre est posé) · **CASSÉ** · **GELÉ** (volontaire).

### Étage 1 — Sources
| Mécanisme | Code | Posé en prod | Dernière exéc. réelle | Preuve de production | Verdict |
|---|---|---|---|---|---|
| Catalogue `data_sources` | `seed_sources.py` | oui (base) | — (statique) | 129 lignes · 124 non retirées · **99 en vitrine** + ~25 internes/partenaires | **MARCHE** |
| Fraîcheur à la lecture | `etats_sources.py:68` | oui | à chaque ouverture page | prod : 94 `sans_echeance` · 5 `a_jour` · 25 non calculées | **MARCHE** |

### Étage 2 — Détection
| Mécanisme | Code | Posé en prod | Dernière exéc. | Preuve | Verdict |
|---|---|---|---|---|---|
| `sonde-sources` | `sentinelle.py` | cron 07:00 quotidien | **20/10 07:00 ok** (7 passages, ~160 s) | `job_runs` prod | **MARCHE** |
| `agents-sources` (IA) | `agent_source.py` | **hors crontab** (`planifie=False`) + plafond défaut **0 €** | **jamais** (absent de `job_runs`) | — | **JAMAIS TOURNÉ** (volontaire : non planifié + ne dépense rien tant que `LABUSE_AGENT_PLAFOND_EUR=0`) |
| Détection cadastre | `cadastre_disparue.py` | **pas un job** (geste CC) | SOURCES-MAJ-1, 10/10, **local seulement** | 2 919 nouvelles / 1 353 disparues marquées, non déployées | **MARCHE à la main**, non en prod |

### Étage 3 — À faire
| Mécanisme | Code | Posé | Dernière exéc. | Preuve | Verdict |
|---|---|---|---|---|---|
| Composition « À faire » | `circuit_resume.py:260` | oui (vue calculée) | à chaque ouverture | servie par `dashboard.py:2397`, rendue `AFaire.tsx` | **MARCHE** |

### Étage 4 — Ingestion
| Job | Cadence prod | Dernière exéc. réelle | Preuve de production | Verdict |
|---|---|---|---|---|
| `ingest-bodacc` | quotidien 06:40 | **20/10 06:40 ok** (7×, ~342 s) | `data_sources` BODACC `last_sync` **20/10** | **MARCHE** |
| `ingest-dvf` | hebdo mardi 05:00 | **20/10 05:00 ok** (2×) | DVF `last_sync` **20/10** (dégelé 20/10) | **MARCHE** |
| `sync-gpu` | mensuel le 15 | **15/10 04:00 ok** (1×) | `job_runs` | **MARCHE** |
| `ingest-sitadel` | mensuel le 10 | **jamais** (cron posé le 13, après le 10) → 1ʳᵉ fois **10/11** | data SITADEL 08-2026 (injectée à la main) | **JAMAIS TOURNÉ** (depuis le registre) |
| `ingest-dpe` | mensuel le 12 | **jamais** (posé le 13, après le 12) → **12/11** | DPE `last_sync` 13/10 = déploiement, pas le cron | **JAMAIS TOURNÉ** (depuis le registre) |
| `ingest-sirene` | mensuel le 7 | **jamais** → **07/11** | data SIRENE présente (injectée à la main) | **JAMAIS TOURNÉ** (depuis le registre) |
| La vanne (Injecter) | à-clic | — | pont supervisé `dashboard.py:1680` | **MARCHE** (sur clic) |
| Dépôt manuel (6 sources) | geste CLI | — | pas d'upload dashboard ; `labuse ingest-… --file` | **MARCHE à la main** |
| Garde 974 | à l'ingestion | — | `garde_974.py` (rejette homonymes métropole) | **MARCHE** |

> **Point d'attention** : les 3 ingests **mensuels** (Sitadel, DPE, SIRENE) **n'ont jamais tourné via le cron** parce que le registre a été posé le **13/10**, après leur date du mois. Leur premier vrai passage automatique sera en **novembre**. Rien ne manque côté donnée (présente, injectée à la main lors de SOURCES-MAJ-1), mais tant qu'ils n'ont pas tourné une fois, on **ne peut pas prouver** que le cron les exécute sans erreur en prod.

### Étage 5 — Calcul (geste CC, plusieurs heures, sur le Mac)
| Mécanisme | Dernière exéc. | Preuve | Verdict |
|---|---|---|---|
| cascade / résiduel / scoring / manifeste | run **q_v19** (local, 18–19/10) | `served_manifest.json` local = q_v19 / q_v19_sources / résiduel seq 16 | **MARCHE** (local) |
| En prod | **q_v18** (13/10) | manifeste prod = q_v18 | un run de retard |

### Étage 6 — Bascule + rebuild
| Mécanisme | Dernière exéc. | Preuve | Verdict |
|---|---|---|---|
| `bascule_flux.basculer` | local 19/10 (`par: fix/rouges-restants`) ; prod 13/10 (`par: cli`) | manifestes | **MARCHE** |
| rebuild (tuiles/intersections/communes/caches) | auto après bascule | `fiche-commune-cache` tourne (voir §8) | **MARCHE** |

### Étage 7 — Prod (Mac → VPS)
| Mécanisme | Posé | Preuve | Verdict |
|---|---|---|---|
| `deploy_donnees.sh` (8 gardes) | script présent | dernier déploiement données = q_v18 (13/10) | **MARCHE** (q_v19 pas encore poussé) |
| `deploy.sh` → `/etc/cron.d/labuse` | oui | crontab régénéré 20/10, 24 actives + 6 gelées | **MARCHE** |
| `labuse parite` | script présent | — (non rejoué ici) | existe |

### Étage 8 — Surveillance
| Mécanisme | Cadence | Dernière exéc. réelle | Preuve de production | Verdict |
|---|---|---|---|---|
| `coherence-banc` | quotidien 03:45 | **20/10 03:45 ok** (7×, ~744 s) | `coherence_runs` id 8 : 135 écarts, **0 faux-client** ; `chasse_runs` : **25 gardes 21 ok 0 écart 4 skip** | **MARCHE** |
| `verite-sources` | mensuel le 15 | **15/10 06:00 ok** (1×) | `verite_sources_runs` + **incident OUVERT** (3 écarts `risques_presence`) | **MARCHE** (a détecté un vrai écart — non résolu) |
| `recap-matin` | quotidien 07:30 | **20/10 07:30 ok** (8×) | `job_runs` | **MARCHE** |
| `ops_alertes` | à l'incident | en continu | 8 incidents (7 résolus, 1 ouvert) | **MARCHE** |
| `healthcheck` / `sante-endpoints` | 15 / 30 min | **20/10 15:45 / 15:37 ok** | `job_runs` (649 / 324 passages) | **MARCHE** |
| `backup-postgres` | quotidien 13:30 | **20/10 13:30 ok** (7×, ~1 098 s) | dump 6,5 Go 20/10 13:49 ; 4 quotidiens + 1 hebdo | **MARCHE** |
| Copie externe (Mac launchd) | hebdo + au montage | **19/10** (disque « MUSIQUE-VIDEO ») | marqueur `.copie-externe.json` | **MARCHE** |
| `mail-queue-consommer` | toutes les 5 min | **20/10 15:45 ok** (1 937×) | **mais échoue chaque jour ~13:35** | **CASSÉ (intermittent)** — voir ECARTS |
| `pg-maintenance` | hebdo dim 04:00 | **18/10 04:00 ok** (1×) | `job_runs` | **MARCHE** |
| `fiche-commune-cache` | quotidien 03:00 | **20/10 03:00 ok** (7×, ~749 s) | `job_runs` | **MARCHE** |
| `evaluer-suivis` / `detect-events` | quotidien 07:02 / 07:04 | **20/10 ok** | `job_runs` | **MARCHE** (⚠ voir digest gelé) |
| `copilote-purge` / `abuse-scan` / `purge-sessions` | quotidien | **20/10 ok** | `job_runs` | **MARCHE** |
| `signal-instantane` | mensuel le 1er | **jamais** → **01/11** | — | **JAMAIS TOURNÉ** (depuis le registre) |

## Les 31 jobs du registre (le mandat disait « 19 » — c'est désormais 31)

**24 émis au crontab** (planifiés, non gelés) · **6 gelés Phase 8** (commentés dans le crontab) · **1 hors crontab** (`agents-sources`, `planifie=False`).

**Gelés (Phase 8 Stéphanie) — RESTENT au registre, émis COMMENTÉS, non lancés, non dégradés au healthz :**
| Job | Rôle | Effet du gel |
|---|---|---|
| `digest` (07:15) | le mail du matin (suivis + Radar + nouveautés) | ⚠ `evaluer-suivis`/`detect-events` posent les événements à la cloche, mais **aucun mail ne part** — voir ECARTS |
| `radar-cloche` (07:05) | annonces Radar → cloche avant le digest | dort |
| `radar-cycle` (04:00) | expirées / vente longue / à revérifier | dort |
| `radar-cycle-dvf` (04:30) | rapprochement vente DVF → « vendue » | dort |
| `radar-cycle-mensuel` (1er) | cible Courrier « retirée sans vente » | dort |
| `restore-test` (1er) | restaure le dernier dump dans une base jetable | **le test de restauration ne tourne pas** (mais la variante Mac launchd existe) |

**Jobs du registre jamais tournés depuis la pose (13/10), par date de mois** : `ingest-sitadel` (10), `ingest-dpe` (12), `ingest-sirene` (7), `signal-instantane` (1er), `verite-sources` a tourné le 15. Tous premiers passages réels en **novembre** (sauf verite-sources déjà fait).

## Millésime servi par source — local vs prod (échantillon des sources qui bougent)

| id | Source | Millésime / contrôle local | Millésime / contrôle prod | Par qui |
|---|---|---|---|---|
| 5 | DVF | sync 14/09 | sync **20/10** | cron `ingest-dvf` (prod) |
| 29 | BODACC | sync 14/09 | sync **20/10** | cron `ingest-bodacc` (prod) |
| 37 | DPE ADEME | sync 19/09 | sync 13/10 (déploiement) | CC / déploiement |
| 16 | SITADEL | millésime **2026-08** | sync 13/10, millésime vide | CC (SOURCES-MAJ-1) |
| 86 | SIRENE géoloc. | sync 18/10 | sync 13/10 | CC (SOURCES-MAJ-1) |
| 1/96 | Cadastre | 2026-09 (q_v19) | 2026-09 (q_v18) | CC |
| — | **~115 autres** | **identiques** local/prod | **identiques** | sonde (veille) / flux continu |

> Lecture : sur les tables **quotidiennes** (DVF, BODACC), **la prod est en avance** sur le Mac — c'est **normal et attendu** (prod fait foi, le Mac récupère au prochain calcul, `labuse parite`). Sur les tables de **fond** (cadastre, SITADEL, SIRENE), le Mac a été l'auteur (SOURCES-MAJ-1) et la prod suit le déploiement. **Aucun écart de fond non expliqué** entre local et prod sur les millésimes.

## Disque & sauvegardes (prod)
- Disque **84 % (16 Go libres)** — remonté de 76 % (après le ménage du 13/10) à 84 % en une semaine. Pas critique, mais la tendance est à surveiller : un run q_v19 déployé ajoutera plusieurs Go.
- Sauvegardes : 4 quotidiennes + 1 hebdo, 6,5 Go chacune, dernière **20/10 13:49**. Copie externe chiffrée sur le Mac : **19/10**. Les deux **MARCHENT**.
