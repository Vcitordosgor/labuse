# DVF-DEGEL-1 — journal d'exécution (prod, gestes ciblés, sans deploy)

**2026-10-20 (Réunion).** Suite de FRAICHEUR-PROD-1. Branche `audit/fraicheur-prod-1`, pas de merge.
Aucun `deploy.sh`/`deploy_app.sh`. Chaque commande montrée avant lancement ; suppression après go.

## Ce qui a été fait

1. **Ligne synthétique DVF 33217 supprimée en prod.**
   - Contenu : `mutation_id` vide, `date_mutation` `2026-08-10 03:43:00.150591` (horodatée = insert machine),
     380 000 € « Vente » Saint-Paul, `type_local`/surfaces/`raw` vides, geom arrondie `POINT(55.28 -21)`,
     **id le plus haut** de la table, **seule** ligne horodatée / `mutation_id` vide, **absente du Mac**.
     → synthétique (test Phase 8), aucune provenance d'ingestion.
   - Sauvegardes : `backup-dvf-33217.json` + `backup-dvf-33217.sql` (INSERT restaurable) + dump complet de
     la table `pg_dump -Fc -t dvf_mutations` → `/var/backups/labuse/dvf_mutations-predvfdegel-20261020.dump` (957 K).
   - `DELETE 1` → prod **29 565** lignes, `max(date_mutation)` **2025-12-31** (= Mac, propre).

2. **`ingest-dvf` dégelé dans `/etc/cron.d/labuse` (ligne 34 seulement).**
   - Backup : `/etc/cron.d/labuse.bak-dvfdegel-20261020`.
   - `sed '/ingest-dvf/ s/^# GELÉ (Phase 8 Stéphanie) //'` → la ligne `ingest-dvf` est active ;
     les **6 autres `# GELÉ`** (radar-cloche, radar-cycle, radar-cycle-dvf, radar-cycle-mensuel, digest,
     restore-test) **intactes**.
   - ⚠ Le registre `src/labuse/jobs.py:418` garde encore `gel="Phase 8 Stéphanie"`. Un futur `deploy.sh`
     **re-gèlerait** la ligne. Le retrait de `gel=` (petit commit séparé) + redéploiement est le geste durable.

3. **`ingest-dvf` lancé une fois à la main** (via `run-job.sh`, env chargé) → **exit 0**, no-op (12 s).

## Résultat : no-op légitime — rien de plus récent à la source

`ingest-dvf` est **sûr** : refresh **incrémental par année** (`DELETE WHERE year=:y` + re-INSERT), **une
seule transaction**, `commit` unique à la fin ; un échec de téléchargement → **rollback**, la prod garde
sa DVF (jamais de table vide). Vérifié dans `ingestion/fraicheur.py:363 refresh_dvf`.

Le run n'a rien chargé parce que le **miroir geo-dvf que LABUSE consomme** est encore la livraison d'avril :
- `https://files.data.gouv.fr/geo-dvf/latest/csv/2025/departements/974.csv.gz` → `Last-Modified: Mon, 18 May 2026`
  (inchangé = livraison d'avril, données jusqu'au 31/12/2025) ;
- `.../2026/departements/974.csv.gz` → **404 Not Found** (le fichier de l'année en cours n'existe pas encore).

La publication d'**octobre annoncée sur data.gouv (12/10/2026)** concerne le jeu DVF **brut** ; le dérivé
**geo-dvf géolocalisé par département** que LABUSE ingère **n'a pas encore propagé le semestre S1 2026**.
`check_dvf_livraison` (l'app, en prod) renvoie **`{'modifies': [], 'n': 0}`** : **aucune livraison plus
récente disponible**. La prod est donc à **la dernière version disponible** du producteur consommé.

**Correction d'audit.** Le verdict « EN RETARD » de FRAICHEUR-PROD-1 pour DVF mesurait la date de
publication data.gouv (brut), pas le miroir geo-dvf réellement lu. Verdict rectifié : **DVF À JOUR
(dernière livraison geo-dvf disponible)**. Quand geo-dvf publiera le fichier 2026, le cron du mardi
(désormais dégelé) le chargera automatiquement.

## Vérification (step 4) — verrou `fraicheur.py` rejoué, colonne D comprise

Verrou affiné : `g01` ne se base plus sur le calendrier (avril/octobre) — qui aurait produit un faux
« EN RETARD » tant que le miroir ne publie pas — mais sur `check_dvf_livraison` (Last-Modified réel du
miroir consommé). Résultat **en prod** (gardes rejouées, lecture seule) :

| Garde | Verdict prod | Preuve |
|---|---|---|
| `dvf-en-retard` | **OK — À JOUR** | `check_dvf_livraison` = `{'modifies': [], 'n': 0}` |
| `dvf-ligne-incoherente` | **OK** | 0 ligne horodatée/future (33217 supprimée) |
| `nouvelle-version-pendante` | ECART (hors DVF) | #73 FRR, #152 EnR — pré-existant, autre périmètre |
| `gel-motive` | OK | crontab : `ingest-dvf` actif ; 6 gels restants motivés |
| `sources-non-surveillees` | OK (rapport) | INPI RNE, CBS, OSM, EduGéo… |

→ **DVF passe À JOUR.** Les 2 ECART restants (FRR, EnR) sont ceux de FRAICHEUR-PROD-1, hors de ce mandat.

**Colonne D (lecteurs & caches) :**
- **Lecteurs vivants** (fenêtre marché 12 mois, `zone.py`, `signal_instantane`) ancrés sur
  `max(date_mutation)` (`dvf_fenetre.py:15 ANCRE_DVF_SQL`) : la suppression de 33217 les **auto-corrige**
  (ancre revenue de août-2026 à **déc. 2025**) au prochain calcul, en direct.
- **`dvf_secteur_medianes`** (2 359 lignes, `computed_at` 2026-08-17, fenêtre **« 2021-2025 »** par
  millésime, pas par date) : non décalée par la ligne synthétique ; reflète les données réelles 2021-2025.
- **Fiche Marché** : « DVF — jusqu'à déc. 2025 » (lu de `source_horizon_at`=2025-12-31) — correct.
- **Résidu** : le cache process `_dvf_couverture` (`api/modules.py:1745`) peut garder « août 2026 » dans le
  process API courant jusqu'au prochain redémarrage/bascule — **masqué** par `source_horizon_at` sur la
  fiche (rien de faux n'atteint le client). Un redémarrage API (hors de ce mandat) le purge.

Pas de **nouvelles ventes** à lire (no-op) : les lecteurs sont cohérents avec la base (déc. 2025).

## Récupération prod → Mac (règle de flux — quand une vraie livraison arrivera)

Aujourd'hui inutile (prod == Mac == 29 565, déc. 2025). Le jour où ingest-dvf chargera le S1 2026 en prod :

```bash
PG=~/miniforge3/envs/labusedb/bin ; L="postgresql://openclaw@localhost:5432/labuse" ; S=/tmp/flux_prod ; mkdir -p "$S"
ssh labuse-vps "sudo -u postgres pg_dump -Fc -t dvf_mutations -d labuse" > "$S/dvf_mutations.dump"
$PG/pg_restore --clean --if-exists --no-owner --no-acl -d "$L" "$S/dvf_mutations.dump"
$PG/psql "$L" -tAc "SELECT 'dvf_mutations prod→Mac = '||count(*)||' max '||max(date_mutation)::date FROM dvf_mutations"
```
(EXPLOITATION.md §15 — flux quotidiens, prod fait foi, sens prod→Mac.)

## Reste à faire (hors ce mandat)
- Petit commit séparé : retirer `gel=` de `ingest-dvf` dans `jobs.py` (sinon un `deploy.sh` re-gèle).
- Redémarrage API pour purger le cache `_dvf_couverture` (cosmétique, masqué).
- FRR (73) / EnR (152) : cf. FRAICHEUR-PROD-1 §1.
