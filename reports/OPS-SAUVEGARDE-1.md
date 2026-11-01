# OPS-SAUVEGARDE-1 — remise en route des sauvegardes PostgreSQL

**Date** 2026-11-02 (nuit, Réunion +04 ; Mac en CET) · **Opus** · depuis `~/Desktop/labuse-main`
**Accès prod** `ssh labuse-vps`, limité au mandat, **go de Vic**. Aucun redémarrage de l'app, aucune autre écriture.
**Déclencheur** `docs/audit-2026-11/nu-3/K/RAPPORT.md` — K-SAV-01 (BLOQUANT) : plus aucun dump depuis le 29/10.

---

## Résumé

| Étape | Résultat |
|---|---|
| 1. Restauration des 60 biens (RADAR-FIX-3) | **a tenu** — vérifiée indépendamment (59 `active` + 1 `en_vente_longue`, 0 `retiree_le`/`vendue_le` subsistant). |
| 2. Export de `pige_restauration_radarfix3` | `/opt/labuse/backups/` — dump custom **restaurable** + SQL lisible, 60 lignes, sha256 enregistrés. |
| 3. Suppression de la table | **DROP fait** (60 lignes avant, absente après) → unique blocage du dump levé. |
| 4. Les 2 tables absentes du dump (K-SAV-05) | `pige_restauration_radarfix3` (exportée+supprimée) et `signal_instantanes` (**désormais dans le dump**, aucun droit à accorder). |
| 5. Sauvegarde relancée | **`labuse-labuse-20261102-001017.dump` — 6,56 Go**, ~18 min, 2 dumps conservés, captures Radar archivées. |
| 6. Dump vérifié | taille OK, `pg_restore --list` propre (1742 entrées), `signal_instantanes` présente, `radarfix3` absente, 301 tables public (toutes sauf `spatial_ref_sys`). |
| 7. Copie hors-VPS | `pull_backups.sh` → Mac `~/labuse-backups`, **sha256 identique** VPS↔Mac (copie bit-pour-bit). |
| 8. Alerte muette | diagnostic en une phrase ci-dessous — **correction au mandat suivant**. |

**Écart de chemin noté :** le mandat dit `/opt/labuse/backups/` ; ce dossier **n'existait pas** (le dossier des
sauvegardes est `/var/backups/labuse/`). Je l'ai **créé** (`labuse:labuse`) et y ai rangé l'export de la table —
emplacement distinct, donc à l'écart de la rotation et des dumps quotidiens, ce qui convient pour un artefact
ponctuel. Les dumps PostgreSQL restent, eux, dans `/var/backups/labuse/`.

---

## 1. La restauration des 60 biens a tenu (vérifiée)

PROD-VERIF-1 l'avait déjà montré ; re-confirmé ici en lecture seule, en partant des 60 `bien_id` conservés
dans la table-filet elle-même :

```sql
-- les 60 bien_id du filet, état ACTUEL dans pige_biens
filet_lignes = 60   (tous capturés en statut 'retiree')
actuel: active = 59 ; en_vente_longue = 1
reste_retiree_le = 0 ; reste_vendue_le = 0
```

Les 60 biens faussement retirés par la passe #274 (28/10) sont tous revenus **vivants** (59 actifs + 1 en vente
longue, un état vivant re-confirmé) ; **aucun** ne traîne en `retiree`/`vendue`. La restauration de RADAR-FIX-3
est donc bien appliquée et stable → la table-filet a fait son office et peut partir.

## 2. Export + suppression de `pige_restauration_radarfix3`

`pige_restauration_radarfix3` est le **filet de réversibilité** de RADAR-FIX-3 (`docs/audit-2026-10/radar-fix-3/restauration.sql`) :
l'état d'avant des 60 lignes (`bien_id, statut, retiree_le, vendue_le, vendue_valeur, vendue_delai_j,
vendue_ecart_prix, capture_at`). Elle appartient à `postgres`, et `labuse` n'a **aucun SELECT** dessus → c'est
exactement ce qui faisait échouer `pg_dump` (un seul `LOCK TABLE` sur toutes les tables bute dessus).

**Export** (`postgres`, car `labuse` ne peut pas la lire), sous `/opt/labuse/backups/` :

```
pige_restauration_radarfix3-20261102-000942.dump   (format custom, restaurable ; TABLE + TABLE DATA)
  sha256 d80621304a22d45fccd6cd0fb71ee203c7030cae2e1e187b5cec7c6ac8d4601e
pige_restauration_radarfix3-20261102-000942.sql    (CREATE TABLE + COPY des 60 lignes, lisible)
  sha256 cee279eb9f59bf88ccff76695eb69f98213fcd586261b45d652441fb1b998294
```

`pg_restore --list` du `.dump` : propre, entrées `TABLE` + `TABLE DATA`. `.sql` : 60 lignes de données. Les deux
fichiers appartiennent à `labuse:labuse`.

**Suppression** (après export vérifié) : `DROP TABLE public.pige_restauration_radarfix3;` — 60 lignes avant,
`to_regclass` = `false` après.

### Choix : exporter **puis supprimer** (plutôt que garder + GRANT)

Le mandat laissait le choix. **J'ai supprimé**, parce que :
1. C'est une table de **secours à usage unique** ; la restauration qu'elle protégeait **a tenu** (vérifié §1) — son rôle est terminé.
2. La garder, c'est soit lui laisser le propriétaire `postgres` (et donc **re-casser le dump** demain), soit lui accorder un droit à une table morte **conservée dans chaque dump à vie**.
3. Sa donnée reste **entièrement récupérable** depuis le fichier daté (schéma + 60 lignes) ; la procédure de rollback de `restauration.sql` reste rejouable à partir de cet export si jamais nécessaire.

## 3. Les deux tables absentes du dump (K-SAV-05)

Audit en prod des tables `public` non détenues par `labuse` : **seules deux** posaient question, et une seule bloquait.

| Table | Propriétaire | labuse SELECT | Pourquoi absente du dump du 29/10 | Traitement |
|---|---|---|---|---|
| `pige_restauration_radarfix3` | postgres | **non** | créée après le 29/10 **ET** illisible par `labuse` (elle **cassait** le dump) | exportée (fichier daté) **+ supprimée** — n'entrera plus, sa sauvegarde est le fichier |
| `signal_instantanes` | **labuse** | oui | créée après le 29/10 (job mensuel `signal-instantane`, 1er du mois) — **simple postériorité**, aucun souci de droit | **aucune action** : elle entre d'elle-même au prochain dump |

> La seule autre table `public` au propriétaire `postgres` est `spatial_ref_sys` — mais `labuse` **a** le SELECT
> dessus (table système PostGIS). Elle est normalement **exclue** de `pg_dump` (gérée par l'extension, repeuplée
> au `CREATE EXTENSION postgis` à la restauration) : ce n'est pas un trou.

**Vérification dans le nouveau dump** : `signal_instantanes` y est avec **schéma + données + pkey + index**
(433 229 lignes) ; `pige_restauration_radarfix3` **n'y est plus**. Les deux tables sont donc réglées.

## 4. Sauvegarde relancée (invocation fidèle à la prod)

Lancée comme le fait la prod (`deploy/scripts/deploy_donnees.sh:48` ; le job `jobs_impl.backup_postgres` délègue
au même script) :

```
sudo -u labuse bash /opt/labuse/app/deploy/scripts/backup_postgres.sh
```

Journal :

```
▶ [2026-11-02 00:10:17] pg_dump labuse (lean) → /var/backups/labuse/labuse-labuse-20261102-001017.dump
✓ Sauvegarde OK (6.2G)
  2 dump(s) conservé(s) dans /var/backups/labuse
✓ captures Radar archivées → labuse-pige-captures-20261102-001017.tar.gz (1.7M)
```

Dossier après :

```
labuse-labuse-20261029-161844.dump   6 547 196 229 o   29/10 16:37   (précédent, conservé)
labuse-labuse-20261102-001017.dump   6 559 271 098 o   02/11 00:28   ← NOUVEAU
```

Rotation `KEEP=2` respectée (le dump du 29/10 reste comme second exemplaire). Durée ≈ 18 min.

## 5. Vérification du dump

- **Taille** : 6 559 271 098 o (6,2 Go), non vide.
- **`pg_restore --list`** : lisible, **1742 entrées** TOC, format CUSTOM, PostgreSQL 18.4. (La garde interne du script — `pg_restore --list` obligatoire sinon suppression + échec bruyant — est passée.)
- **Tables** : **301 tables `public` (schéma)** dans le dump = les 302 tables `public` de la prod **moins** `spatial_ref_sys` (extension PostGIS, cf. §3). Aucune table présente en prod n'est manquante hors celle-là.
- **Données exclues (lean, par conception)** : exactement les **8 reconstructibles** du script, schéma conservé, données vides — `cascade_results`, `dryrun_cascade_results`, `p_model_candidates`, `p_model_dataset`, `p_model_dataset_v2`, `p_model_dataset_v2bis`, `p_model_ext_dataset`, `score_snapshot_parcelles`. Liste identique à `backup_postgres.sh:40-43`.
- **`signal_instantanes`** : présente (schéma + data). **`pige_restauration_radarfix3`** : absente. ✓

## 6. Copie hors-VPS (moyen prévu par le dépôt)

Le dépôt prévoit **deux** chemins hors-VPS, tous deux *tirés* depuis le Mac (le VPS n'a aucun accès vers nous) :

1. **`deploy/mac/backup_offsite_disque.sh`** → disque externe `/Volumes/MUSIQUE-VIDEO` (copie durable, rétention 8 hebdo + 12 mensuelles). **Le disque n'est PAS monté** en ce moment → ce script ne ferait rien (il sort proprement « disque non branché »). **À faire par Vic : brancher le disque** pour la copie longue durée (et refermer K-SAV-02 : marqueur `.copie-externe.json` figé au 19/10).
2. **`deploy/scripts/pull_backups.sh`** → Mac `~/labuse-backups` (fenêtre courte, 2 dumps). **Réalisable maintenant** — c'est ce que j'ai utilisé :

```
PG_RESTORE_BIN=…/labusedb/bin/pg_restore  bash deploy/scripts/pull_backups.sh labuse-vps
→ rapatriés : labuse-labuse-20261029-161844.dump + labuse-labuse-20261102-001017.dump (13 Go)
→ ✓ rapatrié + intègre : labuse-labuse-20261102-001017.dump (pg_restore --list OK)
→ rotation : 2 conservés (vieux dump de test c6 retiré)
```

**Intégrité prouvée** — sha256 du nouveau dump identique des deux côtés :

```
Mac : 32b5a548eba21b19e9509c4469f650a1ba1065966e6f71fd815211165b3e162e
VPS : 32b5a548eba21b19e9509c4469f650a1ba1065966e6f71fd815211165b3e162e   → IDENTIQUE ✓
```

Mac après : 23 Gio libres (au-dessus du seuil 15 Go du script).

## 7. Pourquoi l'incident du 30/10 n'a alerté personne (une phrase)

> **Le seul signal réel — l'incident `job-échec`/`job-retard:backup-postgres` (ouvert le 30/10, rappels quotidiens) — n'est parti qu'en mail Brevo + cloche admin vers un canal d'exploitation que personne ne surveille, noyé parmi plusieurs incidents chroniquement ouverts (cohérence-banc, copie-externe, abuse-scan), pendant que la vigie dédiée « sauvegarde » (`ops_alertes.py:378-390`) affichait « présente/OK » parce qu'elle ne teste que l'*existence* d'un fichier `*.dump` (le vieux dump du 29/10 est toujours là) et son non-rétrécissement — jamais son *âge*.**

*(Correction au mandat suivant : faire que la vigie « sauvegarde » juge la **fraîcheur** du dump, pas sa seule présence, et qu'une panne de sauvegarde de >24-36 h **escalade** d'un cran plutôt que de rejoindre la file des incidents non suivis.)*

---

## Reste à savoir / limites

- **`job_runs` / cockpit** : j'ai lancé le **script** directement (pas via le lanceur de jobs) pour rester dans « aucune écriture applicative, aucun redémarrage ». Donc le cockpit montre encore `backup-postgres` en **échec** (dernier `job_runs` = 01/11 13:30) et les incidents `job-échec`/`job-retard:backup-postgres` restent **ouverts** : ils se **refermeront d'eux-mêmes au prochain passage planifié (13:30)**, qui réussira maintenant que le blocage est levé. Rien à corriger à la main.
- **Offsite durable** : la copie faite ici est sur le Mac (fenêtre courte). La copie **disque externe** (longue rétention) attend que Vic **branche le disque** (K-SAV-02).
- **Hors périmètre, laissé en l'état** : K-SAV-03 (aucun `restore-test.json` de contrôle en routine), K-RAD-01/02/03 (Radar : Mac qui dort, verrou `running` figé, nuit brûlée) — ce sont d'autres mandats.

## Écritures effectuées (et rien d'autre)

1. `mkdir /opt/labuse/backups` + 2 fichiers d'export (`.dump`, `.sql`).
2. `DROP TABLE public.pige_restauration_radarfix3`.
3. Nouveau dump `labuse-labuse-20261102-001017.dump` + tar des captures Radar (via le script de sauvegarde).
4. Copie des dumps sur le Mac `~/labuse-backups` (+ rotation locale du script de pull).

Aucun redémarrage de l'app, aucune autre modification en base, aucune écriture de code applicatif.
