# CHASSE-ORFEVRE-1 — Journaux de prod (30 jours : 18/09 → 18/10/2026)

Collecte 18/10 ~18h15 Réunion, VPS `labuse-vps` (51.255.163.56), **lecture seule stricte** (journalctl, cat/grep).
Script rejouable : `scripts/angle_f_journaux.sh` ; copies brutes : `/tmp/orfevre-logs/` (hors dépôt). Détail complet : `brouillons/ANGLE-F.md`.

## Topologie
| Service | Rôle | Logs |
|---|---|---|
| `labuse.service` | FastAPI/Uvicorn 127.0.0.1:8000, 5 workers, MemoryMax=6G, Restart=always | journald |
| `caddy.service` | Reverse proxy TLS `app.labuse.immo` | `/var/log/caddy/access.log` (JSON) |
| `postgresql@18-main` | PostgreSQL 18 | `/var/log/postgresql/…` (rotation hebdo ×10) |
| cron `/etc/cron.d/labuse` | GÉNÉRÉ par deploy.sh (CRON-1 actif depuis le 07/10 04:00) | wrapper → `/var/log/labuse/jobs/*.log` |

Pas de docker. **Stable sans redémarrage depuis le 14/10 17:02.** Déploiements de la fenêtre : 22/09 · 25/09 · 01/10 · **06-07/10 (nuit de migration, 17 restarts)** · 09/10 · 13/10 ×2 · 14/10 ×5.

**Couverture des logs** : journald depuis le 19/09 (321 Mo) ; Caddy UN fichier 81 Mo depuis le 27/08 **sans rotation** ; sorties des jobs CRON-1 du 07→13/10 absentes du disque (wrapper-logs seulement depuis le 13/10).
**Piège** : `journalctl _COMM=cron` PERD des lignes (89 comptées vs 96 débuts réels le 17/10) — les « trous » du journal ne sont PAS des jobs manqués ; toujours recouper avec les wrapper-logs.

## Groupes d'erreurs

| Gravité | Groupes |
|---|---|
| Bloquant | — (aucun actif) |
| **Gênant ACTIF** | **G1** mail-queue 13:35 (→ ORF-01) · **G2** healthcheck 13:45 + alerte disque muette (→ ORF-02) · **G3** VACUUM jamais exécuté, job vert (→ ORF-03) |
| Gênant résolu | G4 (nuit de migration 06-07/10) · G5 (chemin Mac captures) · G6 (DVF mutation_id, corrigé + gelé → K-6) · G13 (churn du 13/10) |
| À surveiller | **G7** plus d'offsite ni restore-test (→ ORF-23) · G8 disque 84 %, logs sans rotation (→ ORF-24) · G9 worker mort 17/10 (→ ORF-25) |
| Cosmétique | G10 404 tuiles mer (→ K-4) · G11 scans/401 + burst admin 11/10 (→ ORF-52) · G12 weasyprint/geopf/Stripe 1× (→ ORF-52) |

### Les 3 gênants ACTIFS (fil rouge commun)
**Fenêtre pg_dump quotidienne 13:30-13:48 + DDL « ensure » rejouées à chaque run + timeout SIGALRM qui laisse la connexion sale** ; et un disque à un point du seuil d'alerte, alerte qui ne peut justement pas s'écrire pendant la fenêtre.
- **G1** — `mail-queue-consommer` : 9 échecs, 1/jour 13:35, 14→18/10, CONTINUE. `ALTER TABLE mail_queue` (mailfile.py:95-104) bloquée par pg_dump → `_Timeout 300s` → « another command is already in progress ». Impact : mails décalés ~10 min, 1 incident rouge/jour. **NON corrigé dans main.**
- **G2** — `healthcheck` : 1 traceback/jour 13:45, 14→18/10, CONTINUE. Le disque franchit 85 % pendant le dump → `ops_alertes.signaler` rejoue un DDL bloqué → timeout 120 s → **l'alerte disque n'est jamais enregistrée**. A commencé le 14/10 = jour où le disque a atteint le seuil. **NON corrigé.**
- **G3** — `pg-maintenance` : « VACUUM cannot run inside a transaction block » chaque dimanche (13/09→18/10), job `fin (code 0)`. Cause élucidée par l'angle H : `raw.autocommit=True` posé sur le proxy de pool, pas sur psycopg (jobs_impl.py:500-508), échecs avalés. **NON corrigé** (le run du 18/10, post-déploiement du 14/10, échoue encore).

### Gênants RÉSOLUS
- **G4 — nuit de migration 06/10 20:00 → 07/10 03:28** : la TOTALITÉ des tracebacks API des 30 jours (378) et des 500 (46 ; 137/142 5xx Caddy). Sous-groupes : FREEZE-scoring2026.json absent (21, `/v2/modele`) · `mode_remplissage` pas encore migrée (20, `/admin/circuit`) · QueuePool épuisé (77) · QueryCanceled (19) · tables pas encore créées (3). Trafic = IP opérateur seule. **0 récidive en 11 jours.** Leçon : app restée EXPOSÉE pendant la migration.
- **G5 — chemin Mac en prod (06→14/10)** : 95 ERROR « répertoire de captures INACCESSIBLE : /Users/openclaw/labuse-pige/captures » — env prod pointant le Mac de dev ; corrigé au restart du 14/10 16:50 ; impact nul (Radar gelé Phase 8).
- **G6 — refresh DVF cassé** (`mutation_id` inexistante, échecs 23 et 30/09) : le bug CORRECTIFS-1 E1, corrigé dans main, cron DVF gelé Phase 8 (→ K-6).
- **G13 — churn du 13/10** : replay de tous les jobs avec `PermissionError '.local/state/jobs'` (chemin d'état RELATIF — piège : `jobs_state_dir` doit être absolu) ; 51 échecs mail-queue pendant la bascule env/postgres (15:30→17:25) ; salve unique au restart du 22/09.

## Jobs : régularité, manqués, durées
- **Aucun job planifié manqué** (prouvé wrapper-logs 13→18/10 : tous les `début` ont leur `fin (code 0)` SAUF G1/G2).
- Jobs rares à l'heure : ingest-sirene 07/10, ingest-sitadel 10/10, ingest-dpe 12/10, sync-gpu 15/10, verite-sources 15/10, pg-maintenance les dimanches, backup 13:30 (18 min stable).
- **Gelés volontairement (Phase 8, commentés dans le cron)** : ingest-dvf, radar-* ×4, digest, restore-test. **RETIRÉ (non commenté, disparu)** : backup-offsite (→ ORF-23).

## Caddy (18/09 → 18/10)
51 028 requêtes : 2xx 25 875 · 3xx 2 711 · 4xx 10 561 · **5xx 142** (06-07/10 = 137 ; 09/10 = 1 scan pendant restart ; 17/10 = 4 worker mort) · « 0 » abandon client 11 739. Latences > 30 s : 82, toutes dans la nuit G4 (max 598 s). 0 erreur TLS/certificats.
4xx : 483/724 404 = tuiles mer (K-4) ; 9 823 × 401 = scanners (/.env, /.git, wp — fail2ban 350 bans) + burst 599 × 401 `/admin/*` le 11/10 (dashboard opérateur à session expirée qui re-polle — ORF-52).

## Système
- **OOM : aucun** (pic RAM service 1,07 G / 6 G). **Disque : 84 %** (→ ORF-24).
- PostgreSQL : pas de PANIC ; 1 deadlock (nuit G4) ; « VACUUM cannot run… » hebdo (G3) ; 4 FATAL auth le 28/09 (bref, non répété).
- Brevo : **0 échec d'envoi** (les échecs du job G1 sont AVANT l'envoi). 1 webhook Stripe rejeté-signature le 09/10 (garde OK, unique).

## Croisements avec les audits précédents
- G4 = la mise en prod des mandats SCORING-7/CHASSE-INVARIANTS (tables score_labuse, commune_zonage_abc, batiment_hauteur_lidar créées dans la nuit).
- G6 = le bug décrit/corrigé par CORRECTIFS-1 E1 ; les logs prod datent les dernières morsures réelles (23 et 30/09).
- Le gel Phase 8 est confirmé par le cron ; l'angle NEUF est G7 : l'offsite est RETIRÉ, pas seulement gelé.
- Le « QueryCanceled → rollback silencieux » de SCORING-6 ne réapparaît pas hors nuit G4.
