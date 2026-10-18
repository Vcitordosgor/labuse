# CHASSE-ORFEVRE-1 — RAPPORT

Audit du 18/10/2026 · branche `audit/chasse-orfevre-1` (depuis main `ea71e5db`) · worktree `~/Desktop/labuse-orfevre` · lecture seule · **ne merge pas**.

## Verdict en 5 lignes

1. **Aucun écart bloquant** : rien de ce qui a été trouvé ne fausse un chiffre servi au client de façon trompeuse à grande échelle, et les fondations (géométries, SIREN, fuseaux, dépendances prod, webhooks Stripe) sont remarquablement saines.
2. L'audit relève **0 bloquant · 22 gênants (dont 3 ACTIFS en prod) · 21 à surveiller · ~35 cosmétiques groupés en 9 · 6 déjà connus** — chaque écart est prouvé (requête, fichier:ligne ou capture) dans `ECARTS.md`.
3. **À corriger avant le déploiement** : les 3 gênants actifs de prod qui partagent la même racine (DDL rejouées à chaque run + fenêtre pg_dump 13:30-13:48 + SIGALRM qui salit la connexion : ORF-01/02/03), le rétablissement d'une sauvegarde hors-VPS (ORF-23, disque à 84 %), et la purge des 12 mails de recette encore DUS dans la file (ORF-07) avant toute pose de `LABUSE_MAIL_REEL`.
4. **Remarquablement sain** : DVF identique octet pour octet aux fichiers officiels, 0 SIREN Luhn-invalide sur toute la base, 0 géométrie invalide, 0 NaN/Infinity, 100 % des colonnes temporelles en `timestamptz` avec session forcée Indian/Reunion, 0 CVE sur les dépendances de prod (Python et npm), 18/30 jobs idempotents prouvés, 0 undefined/NaN sur 49 écrans.
5. **Réserve** : la base de dev est PARTAGÉE et bouge sans journal pendant l'audit (15 009 lignes SIRENE évaporées dans la journée — ORF-11) ; les comptes sont donc datés du 18/10, et le constat de traçabilité vaut en lui-même.

## Écarts par gravité × angle (après consolidation)

| Angle | Bloquant | Gênant | À surveiller | Cosmétique | Déjà connu |
|---|---|---|---|---|---|
| A — tables | 0 | 8 (ORF-04, 07, 12, 13, 14, 15, 16, 22) | 3 (ORF-26, 27, 28) | 4 constats (ORF-48) | K-1, K-2, K-3 |
| B — sources | 0 | 2 (ORF-06, 11) | 1 (ORF-26) | 2 constats (ORF-48, 49) | K-5 |
| C — calcul | 0 | 2 (ORF-04, 05) | 4 (ORF-29, 30, 31, 32) | 3 constats (ORF-45) | — |
| D — temps | 0 | 1 (ORF-17, conditionnel) | 2 (ORF-33, 34) | 6 constats (ORF-46) | — |
| E — jobs/files | 0 | 5 (ORF-02b, 07, 08, 09, 10) | 4 (ORF-35, 36, 37, 38) | 4 constats (ORF-47) | — |
| F — prod | 0 | 3 ACTIFS (ORF-01, 02a, 03) + 4 résolus | 3 (ORF-23, 24, 25) | 2 groupes (ORF-52) | K-4, K-6 |
| G — front | 0 | 1 (ORF-21) | 1 (ORF-43) | 9 constats (ORF-44, 51) | K-4 |
| H — code | 0 | 3 (ORF-03/18/19, 20) | 4 (ORF-39, 40, 41, 42) | 2 groupes (ORF-49, 50) | — |

(Un même ORF peut apparaître sur deux angles : la consolidation est dans `ECARTS.md` — **total dédupliqué : 22 gênants, 21 à surveiller, 9 groupes cosmétiques, 6 connus**.)

## Corrections recommandées AVANT le déploiement (ordre proposé)

1. **ORF-01/02/03 — le fil rouge prod** : ne jouer les DDL « ensure » qu'une fois (mailfile, ops_alertes), nettoyer la connexion après `_Timeout`, `raw.driver_connection.autocommit` + échec si `faites=[]` pour le VACUUM, et réparer le compteur d'échecs du healthcheck (la vigie est aveugle aujourd'hui).
2. **ORF-23 — sauvegarde hors-VPS** : réactiver backup-offsite (ou livrer `feat/sauvegarde-disque`) + restore-test ; disque à 84 %, aucune copie hors machine depuis le 14/10.
3. **ORF-07 — purger les 12 mails de recette dus** (3 vers un compte supprimé) et durcir `consommer()` (garde d'âge + existence du compte) — AVANT toute pose de `LABUSE_MAIL_REEL` ou d'une clé Brevo.
4. **ORF-04 — borner la phrase de score** « bâti existant sur N % » (> 100 → « saturé ») : effet au prochain run ou reprise SQL des libellés q_v19 ; **ORF-05** — clamper les parts CoSIA au service.
5. **ORF-06 — supprimer la mutation DVF inventée** (1 DELETE) et retirer le contournement de dvf_fenetre.py.
6. **ORF-12 — purge des résidus de recette** (comptes 61/62, utilisateur 30 sans hash, événements orphelins) en étendant la purge [GB-TEST] déjà fournie — après accord Vic.
7. **ORF-18 — poser les 2 index** (`sirene_etablissements(siren)`, `dvf_mutations(date_mutation DESC)`) : gain direct sur chaque fiche propriétaire et chaque fenêtre DVF.

Ensuite, au fil de l'eau : ORF-08/09/10 (idempotence réelle de la file mail, du dépôt Radar, des sous-process d'ingestion), ORF-19 (les 6 avaloirs d'exceptions), ORF-17 (trancher la branche serveur-UTC de deploy.sh), ORF-26 (rattachements de millésimes).

## Méthode

- **8 angles, un sous-agent par angle, un seul à la fois** (Mac 8 Go), orchestrés séquentiellement ; un commit par angle sur `audit/chasse-orfevre-1`.
- **Lecture seule** : rôle read-only en base (Luhn en SQL pur, pas de TEMP TABLE), TestClient sans lifespan pour sonder l'API, VPS en commandes de lecture uniquement, aucun job exécuté, aucun formulaire soumis.
- **Scripts rejouables** (`scripts/`) : `angle_a_tables.py` (68 contrôles), `angle_b_sources.py` (`--en-ligne` producteurs), `angle_c_calcul.py`, `angle_d_temps.py`, `angle_e_jobs.py`, `angle_f_journaux.sh`, `angle_g_front.mjs` (+ `angle_g_report.json`), `angle_h_code.sh` — à rejouer après chaque run/déploiement.
- **Livrables** : `ECARTS.md` (consolidé dédupliqué), `TABLES.md`, `SOURCES.md`, `PROD-JOURNAUX.md`, ce rapport ; matière brute dans `brouillons/ANGLE-{A..H}.md` ; captures `captures-g/`.

## Limites et effets de bord déclarés

- **Base dev partagée et vivante** : les comptes datent du 18/10 ; une purge SIRENE non journalisée a eu lieu PENDANT l'audit (ORF-11) ; `job_runs` quasi vide est normal en dev (pas de cron local) — les verdicts « files/jobs » d'état réel sont à recompter en prod.
- **Écritures involontaires, déclarées** : les sondes GET de l'angle C ont écrit **23 lignes dans `consultation_log`** (quota) et la navigation de l'angle G a produit les logs d'usage inhérents aux GET. Purge proposée (NON exécutée, à valider) : `DELETE FROM consultation_log WHERE ts BETWEEN '2026-10-18 17:27:00+04' AND '2026-10-18 17:45:00+04';`
- **Référentiel mouvant** : le servi est **q_v19 / résiduel run 16** (le mandat citait q_v18, périmé) ; `labuse_hauteur_lidar_m` EST en base (contrairement à l'hypothèse du mandat).
- **Couverture prod** : journald depuis le 19/09 seulement, sorties des jobs 07→13/10 absentes du disque, Caddy depuis le 27/08 (sans rotation).
- **Fixes non mergés** : l'audit juge MAIN ; plusieurs branches poussées non mergées (fix/chasse-invariants-2 `f9d5fb01`, fix/affirmations, FIX-1 recette…) corrigent déjà des points recoupés ici (K-1, q_v18 banc2) — piège de merge noté sur `filtre_bati.py` (ORF-49).
- **pg_stat de dev** : les seq_scan (ORF-18) incluent les runs batch locaux — indices forts, à confirmer en prod.

## Purges SQL fournies, NON exécutées (rappel)

1. `[GB-TEST]` pipeline_entries ids 91→132 (38 lignes — RECETTE-GENERALE-1, K-3).
2. Les 23 lignes `consultation_log` de l'audit (ci-dessus).
3. Proposées dans ECARTS (à faire valider) : 12 mails de recette (ORF-07), mutation DVF démo (ORF-06), comptes/utilisateur/événements de recette (ORF-12).

**Ne merge pas.**
