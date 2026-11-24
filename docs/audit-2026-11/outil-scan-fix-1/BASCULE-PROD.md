# Bascule 2026 — base commune `labuse` / prod — RUNBOOK (NON exécuté)

> OUTIL-SCAN-FIX-3. Séquence PRÉPARÉE, **non lancée** sur `labuse`/prod (l'agent ne lance `--go`/`--rollback`
> que sur `labuse_scanfix`). Script : `scripts/bascule_2026_labuse.py`. Vic choisit la cible et le moment.
> État mesuré de `labuse` (lecture seule) : `programmes`=9 (DÉJÀ là), `sirene_etablissements`=155 505 (DÉJÀ là),
> `bodacc_depots`=14 078 (à rafraîchir), `parcelle_personne_morale`=82 701 (2025), `parcelle_pm_droit` absente.

## Sûretés intégrées au script (relecture-scan-2)

- **Garde-fou de cible** : `--go` et `--rollback` REFUSENT sans `--confirme <base>@<hôte>`, comparé à
  `current_database()` et à l'hôte réel de la connexion. **Aucune base par défaut.** Avant d'agir : affichage
  base, hôte, nombre de lignes des 5 tables concernées.
- **Staging + transaction unique** : les droits 2025 ET 2026 sont chargés dans une TABLE D'ATTENTE
  (`parcelle_pm_droit_staging`) ; la promotion des droits + l'archive 2025 (même règle) + le flip 2026 passent
  dans **UNE seule transaction** (`commit=False` partout, un seul `commit` final). **Interruption avant ce commit
  ⇒ base servie strictement inchangée** (prouvé : interruption dure post-staging → empreintes servies = AVANT).
- **Sauvegarde complète, non-écrasante** : `--go` copie d'abord les 5 tables concernées
  (`parcelle_personne_morale`, `pm_proprietaires_millesimes`, `parcelle_pm_droit`, `bodacc_depots`,
  `parcel_blocs`) dans `_bascule_bak__*` et mémorise le **run V-score servi** (re-servable). Relancer `--go`
  ne réécrit pas la sauvegarde → un rollback revient toujours à l'AVANT d'origine.
- **Rollback réel** : `--rollback` restaure les 5 tables depuis la sauvegarde EN UNE transaction (et RETIRE
  les tables/colonnes créées par la bascule — `parcelle_pm_droit`, colonnes `droit_code/droit_label`). Plus
  AUCUNE commande SQL à taper. *(L'ancien `TRUNCATE … WHERE false` du runbook précédent était du SQL invalide.)*

## Séquence

```bash
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"   # local commun ; prod = /etc/labuse/labuse.env
BIN=.venv/bin/python; S=scripts/bascule_2026_labuse.py

# Inspection (lecture seule) :
$BIN $S --empreinte
$BIN $S --dry-run

# 1-3. DONNÉES — staging + transaction unique (le script sauvegarde tout d'abord) :
$BIN $S --go --confirme labuse@localhost          # adapter base@hôte à la cible réelle

# 4. Rafraîchir les dépôts de comptes BODACC (fait daté ; corrige le retard, ex. 449090075 arrêté 2023) :
.venv/bin/labuse ingest-bodacc-depots

# 5. Recalcul V-SCORE derrière le flip (le classement lit parcelle_personne_morale) puis promotion :
.venv/bin/labuse p-score-v2 --label q_vXX_scan2026 --rebuild
#   puis promouvoir q_vXX_scan2026 (chaîne golden-promote).

# 6. Reconstruire les blocs (une parcelle multi-titulaire peut changer de bloc) :
.venv/bin/labuse blocs-build
```

(programmes et sirene_etablissements sont DÉJÀ en base `labuse` → rien à recharger. Base vide : programmes via
l'admin `/admin/programmes/collecter`+`valider`, sirene via `labuse ingest-sirene-etab`.)

## Ce que la bascule change (parcelles multi-titulaires : ≈ 2 711 SIREN principaux, 3 989 `groupe`)

| Écran / moteur | Effet |
|---|---|
| **Fiche parcelle** | propriétaire affiché = le propriétaire (P), plus la 1re ligne, sur les multi-titulaires ; + « + N autres titulaires ». |
| **Blocs fonciers** | **rebâtir** (`labuse blocs-build`) : une parcelle multi-titulaire peut changer de bloc. |
| **Communes — « changements de propriétaires »** | archive 2025 par la MÊME règle → **963** vrais changements affichés, plus **2 019** (≈ 1 056 artefacts de règle supprimés). |
| **Classement / V-score** | lit `parcelle_personne_morale` → **recalcul V-score obligatoire** (étape 5) + promotion. |
| **Scan patrimoine / Copilote** | millésime 2026, droits séparés, DP/annulés à part, catégorie NAF ; plus de valorisation. |

## Les 12 témoins de cohérence (hook)

Marché €/m² (terrain/bâti), **indépendants du propriétaire** → le flip (côté owner) ne crée aucun écart
1 €/1 m² attendu. **Relancer** `bash scripts/ci/coherence_run.sh` après flip + recalcul V-score : un témoin
multi-titulaire verra son owner changer **de façon identique sur tous les écrans** (source unique
`parcelle_personne_morale`) → 0 divergence. Toute divergence = cache d'écran non invalidé, à corriger.

## Durée (ordre de grandeur, base locale)

0 sauvegarde (5 tables) ~ secondes · 1 téléchargement 2 ZIP (149 Mo ×2) + staging ~ 5-8 min (réseau ; cache
/tmp réutilisable) · 2 transaction unique (promotion + archive + flip, swap bref) ~ secondes · 4
`ingest-bodacc-depots` ~ minutes (API) · 5 recalcul V-score ~ **poste long** (minutes-dizaines) · 6 blocs-build
~ minutes. **Coupure lecteurs** : seulement le commit de la transaction unique (bref ; MVCC → jamais de table
vide ; les lecteurs voient l'ancien jusqu'au commit).

## Rollback

- **Avant le commit de la transaction unique** : rien n'a bougé côté servi — il n'y a rien à annuler (la
  table d'attente peut être laissée ou `DROP TABLE parcelle_pm_droit_staging`).
- **Après un `--go` réussi** : `$BIN $S --rollback --confirme <base>@<hôte>` — restaure les 5 tables depuis
  `_bascule_bak__*`, retire `parcelle_pm_droit` et les colonnes `droit_code/droit_label` ajoutées. **Prouvé
  identique à l'AVANT, table par table** (empreinte = n_lignes + Σ hashtext des colonnes métier).
- **bodacc_depots** : l'étape 4 (upsert) est couverte par la sauvegarde (restaurée au rollback).
- **V-score** : le run précédent est MÉMORISÉ par la sauvegarde (`_bascule_bak__meta.vscore_run_servi`) et
  **re-servable** par la chaîne golden-promote (repointer le run servi). Son nom est affiché par `--rollback`.
- **parcel_blocs** : restauré par le rollback ; sinon `labuse blocs-build` reconstruit depuis l'état courant.

## ARRÊT

Rien n'est exécuté sur `labuse`/prod. Vic déclenche la fenêtre.
