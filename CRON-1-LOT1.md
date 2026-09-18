# CRON-1 · Lot 1 — le nouveau registre, job par job

**Branche** `feat/cron-1` · un commit. Aucun job posé en prod. Le registre unique est `src/labuse/jobs.py` : chaque `Job` porte désormais **une raison (FR)**, **ce qu'il touche** (`eau` / `exploitation`) et **le node-id de son test**. Un méta-test (`test_job_a_une_raison`) refuse tout job muet — *un job sans raison n'existe pas*. `TOUCHE_EAU` n'est plus une liste tenue à la main : elle est **dérivée** du registre (`touche == 'eau'`).

## Les jobs réinscrits (16)

### L'eau — surveillance & ingestion des 94 (9)
| Job | Cron (UTC) | Réunion | Raison (résumé) |
|---|---|---|---|
| **sonde-sources** | `0 3 * * *` | 07:00 | l'œil sur les 94 : HTTP sur tout amont interrogeable, détecte une nouvelle version, n'ingère rien |
| **agents-sources** | `0 19 * * 0` | dim 23:00 | le détective IA, **plafonné** (arrête proprement, signale les non traitées) |
| **filtres-sources** | `5 3 * * *` | 07:05 | rejoue les contrôles qualité sur les versions servies |
| **coherence-robinets** | `25 3 * * *` | 07:25 | la sonde « tout coule » : fuites + eau ancienne |
| **ingest-bodacc** | `40 2 * * *` | 06:40 | procédures collectives J+2 (recoupement tranché) |
| **ingest-sitadel** | `30 0 10 * *` | le 10 | permis SDES (recoupement tranché : mensuel) |
| **ingest-dpe** | `0 0 12 * *` | le 12 | DPE ADEME (recoupement tranché : mensuel) |
| **ingest-sirene** | `0 0 7 * *` | le 7 | concurrents géolocalisés |
| **sync-gpu** | `0 0 15 * *` | le 15 | diff PLU des 24 communes |

### L'exploitation — faire tourner le serveur (7)
| Job | Cron (UTC) | Réunion | Raison (résumé) |
|---|---|---|---|
| **backup-postgres** | `30 9 * * *` | 13:30 | **la seule sauvegarde** — reprise à l'identique du legacy (sans trou) |
| **pg-maintenance** | `0 0 * * 0` | dim 04:00 | VACUUM ANALYZE (sinon le planner dérive) |
| **healthcheck** | `*/15 * * * *` | 15 min | dead-man local (/health + disque) |
| **sante-endpoints** | `7,37 * * * *` | 30 min | sonde métier (écran vide, source vide, Radar cassé) |
| **copilote-purge** | `30 23 * * *` | 03:30 | rétention Copilote (coût + minimisation) |
| **radar-digests** | `0 14 * * *` | 18:00 | alertes de veille — un mail par client (les biens qui matchent) |
| **restore-test** | `0 1 1 * *` | le 1er | une sauvegarde non restaurable ne vaut rien |

### Non repris (retirés, avec la raison)
- **Radar : pas de job** — le traitement est déclenché au dépôt (manuel) ; une **échéance attendue en base** → dépassée = tâche du Résumé (verrou G8, lot 2). Donc `radar-cycle`, `radar-releves` retirés.
- `sources-fraicheur` : le verdict de fraîcheur est calculé à la lecture (`etats_sources`) + la sonde porte la veille amont → doublon.
- `fiche-commune-cache` : réchauffeur de cache non essentiel.
- `coherence-run` : le mandat ne reprend que `filtres-sources` + `coherence-robinets` ; la cohérence de run est couverte par eux + les verrous.
- `rapport-admin` : redondant avec la Tour de contrôle (Pilotage en direct).
- `regles-references`, `ingest-bdnb` : IA à la demande / amont 974 absent (inchangé).

## Les deux exigences

### 1. Le backup — sans trou
Repris **à l'expression EXACTE du legacy** (`30 9 * * *`) : le nouveau job tourne au **même instant** que l'ancien. La garde `deploy.sh` (lot 3) **pose le nouveau crontab AVANT** de retirer le legacy `/etc/cron.d/labuse-backup` → jamais une nuit sans dump. Verrou : `test_backup_sans_trou`.

### 2. Les 4 recoupements — tranchés, avec la raison
| Job | Legacy | Wrapper | **Tranché** | Pourquoi (écrit dans `raison`) |
|---|---|---|---|---|
| backup | `30 9` (actif) | `45 1` | **`30 9`** | le job réellement vivant ; horaire identique = remplacement sans trou |
| bodacc | `30 6` quotidien | `40 2` quotidien | **quotidien `40 2`** | les deux en quotidien ; l'heure wrapper place l'ingestion **avant** les alertes de 07:00 |
| dpe | hebdo (mardi) | mensuel (12) | **mensuel le 12** | ADEME publie en train **mensuel** ; l'hebdo re-téléchargeait sans nouvelle donnée |
| sitadel | quotidien | mensuel (10) | **mensuel le 10** | SDES publie **mensuellement** ; le quotidien re-téléchargeait le même jeu |

Verrou : `test_recoupements_arbitres`.

## La sonde — monter de 78 vers le maximum
Discipline : *une URL n'est inscrite que si elle a été appelée pour de vrai.*

**Ajouté** (probé le 18/09, HTTP 200, signal daté source-spécifique) : **Inventaire SRU (DHUP)** → `api` `data.gouv.fr/api/1/datasets/communes-et-inventaire-sru/`, sélecteur `last_update` (2026-08-11). SRU **sort des rappels** (l'ancien constat « pas d'URL de version stable » ratait l'API du dataset). Sonde : **78 → 79**.

**Frontière honnête** (probé, pas de signal daté propre → restent hors sonde, raison écrite) :
- **Communes contours** : `admin-express` `last_update` existe (200) mais **national** (bouge pour n'importe quel changement français) → bruit sur un référentiel quasi immuable ; le « seed statique » reste justifié.
- **INPN / patrinat** : WFS GetCapabilities (data.geopf.fr) répond mais signal **national bruyant**, pas de date propre au 974 sans creuser le typename — à affiner.
- **SPANC / PLH** : entrent par leur **page de publication** (mandat) — mais aucune URL de publication n'est renseignée en base (`endpoint_url` vide) ; à fournir pour poser la sonde (le dépôt du fichier reste manuel).
- **Légifrance** (FRR/ZRR, ZFANG, RTAA DOM) : Cloudflare bloque les non-navigateurs (403) — pas de sonde mécanique honnête.
- **Overpass, PVGIS** : interrogées **en direct** (aucun snapshot à comparer) — non sondables par nature.
- **INSEE RP Logement 2023, INPI RNE** : amont existant mais sans slug data.gouv / date lisible trouvés → à rechercher.

## L'agent — le dimanche, plafonné (dépense = 0 par défaut)
`agents-sources` (dimanche 23:00) appelle `agent_source` sur les sources vitrine, 5 en parallèle, **sous plafond** `LABUSE_AGENT_PLAFOND_EUR` (défaut **0 = ne dépense rien** tant que Vic n'a pas fixé un plafond). Entre chaque source, le passage lit le coût cumulé au ledger `ia_log` (`kind='agent_source'`) et **s'arrête proprement** dès le plafond atteint, en signalant les sources **non traitées**. La **mesure réelle** du coût (10 sources, 2 modèles, extrapolation à 94) reste à faire avec ton feu vert à la dépense (elle appelle l'API Claude pour de vrai).

## Preuves
- `tests/test_cron1_registre.py` : méta-test (raison/touche/test par job) + backup sans trou + recoupements + sonde couvre le max + agent dimanche + Radar sans job. **Tests verts** (pytest, `pythonpath=src`).
- `PYTHONPATH=src labuse circuit verrous` **complet vert** (le CLI `labuse` du venv pointe le worktree couches-tuyau ; on force le worktree cron par `pythonpath=src`).
