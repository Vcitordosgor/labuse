# Bascule 2026 — base commune `labuse` / prod — RUNBOOK (NON exécuté)

> **⚠ À LANCER QUAND AUCUNE AUTRE SESSION NE LIT LA BASE.** La procédure **n'est pas atomique de bout en
> bout** : les étapes [2], [3], [4] committent séparément. Après une interruption, **la base reste modifiée
> jusqu'au `--rollback`** (explicite, nommant la sauvegarde). Prévoir une fenêtre fermée.
>
> OUTIL-SCAN-FIX-5/6. Procédure PRÉPARÉE, **non lancée** sur `labuse`/prod (l'agent ne lance `--go`/`--rollback`
> que sur `labuse_scanfix`). Script : `scripts/bascule_2026_labuse.py`. Vic choisit la cible et le moment.

## Périmètre RÉDUIT (décision OUTIL-SCAN-FIX-5)

**Le recalcul et la promotion du V-score NE font PLUS partie de cette bascule** (chantier du nouveau
classement). Le script ne touche NI le feature store (`p_model_*`), NI `data_sources`, NI
`p_score_v2_runs`/`parcel_p_score_v2`, NI `config/served_run.txt`/`served_manifest.json`. Ce code a été
**retiré** (pas désactivé par une option).

**Tables SERVIES écrites — liste exhaustive, lue dans le code de chaque étape :**

| Étape | Fonction(s) | Tables écrites (persistantes) | Couvert par la sauvegarde |
|---|---|---|---|
| [1] droits 2025+2026 | `pm_droits.ingest_droits` → table d'attente `parcelle_pm_droit_staging` (temp) puis promue | `parcelle_pm_droit` | **OUI** |
| [2] archive + flip | `archive_principal_depuis_droits` ; `recompute_principal` (swap `injection_sure`, temp `…__inj_staging`) | `pm_proprietaires_millesimes`, `parcelle_personne_morale` (+ col. `droit_code/droit_label`) | **OUI** |
| [3] BODACC | `bodacc.ingest_bodacc_depots` | `bodacc_depots` | **OUI** |
| [3] (effet de bord) | `_touch_source` ferait `UPDATE data_sources.last_sync_at` → **NEUTRALISÉ** (snapshot + restauration dans la même transaction) | `data_sources` : **inchangée** | sans objet |
| [4] blocs | `blocs.build_blocs` (temp `_blocs_pm` ; lit `parcel_residuel`/`residuel_runs`/`parcel_zone_plu` — non écrits) | `parcel_blocs`, `parcel_bloc_membres` | **OUI** |

→ **6 tables servies écrites, toutes dans `CONCERNEES`.** Temps droppées. **Rien d'autre.**

**`data_sources` — absence de changement établie par LECTURE DU CODE.** `_touch_source` ne modifie que
`last_sync_at` de la ligne `BODACC (procédures collectives)` ; le script lit cette valeur avant l'UPSERT et
la ré-écrit après, dans la **même transaction** → effet net nul. Sur `labuse_scanfix` la table `data_sources`
est **vide** (ligne BODACC absente) : l'empreinte y est donc **vacante** (0 avant / 0 après) et **ne prouve
rien**. Cette neutralisation **sera VÉRIFIÉE par empreinte avant/après** (`data_sources.last_sync_at`
identique) **lors de la bascule réelle sur `labuse`**, où la ligne existe.

## Procédure (une commande ; une étape qui échoue ARRÊTE, code ≠ 0, jamais « [OK] »)

```bash
P=.venv/bin/python; S=scripts/bascule_2026_labuse.py; U="postgresql+psycopg://<user>@<host>:5432/labuse"
$P $S --db "$U" --empreinte | --dry-run | --lister-sauvegardes          # lecture seule (donne l'identité serveur)
$P $S --db "$U" --go --confirme <base>@<system_identifier>:<port>        # bascule entière (droits→archive→flip→BODACC→blocs)
$P $S --db "$U" --rollback --sauvegarde <N> --confirme <base>@<system_identifier>:<port>
$P $S --db "$U" --purge-sauvegarde <N> --confirme <base>@<system_identifier>:<port>   # quand validé
```

(Sûretés : `--db` obligatoire — ni env ni `.env` ni défaut ; `--confirme` = identité serveur
`current_database()@system_identifier:port`, localhost=127.0.0.1=::1=casse, refus n'imprime pas la valeur ;
sauvegardes numérotées/datées, `--go` refuse une sauvegarde ancienne sauf `--malgre-sauvegarde N`.)

## Classement servi : DEUX MILLÉSIMES tant que le V-score n'est pas recalculé

Cette bascule change les **propriétaires** (`parcelle_personne_morale` → millésime 2026) mais **PAS le
classement servi**. Le run V-score servi (**`q_v20`**, point de vérité `config/served_manifest.json`) reste
**calculé sur les propriétaires 2025** jusqu'au nouveau calcul (chantier séparé). Donc, entre la bascule et
ce recalcul, ces écrans affichent un **propriétaire 2026** à côté d'un **classement/score bâti sur 2025** :

- **Fiche parcelle** : propriétaire (2026) + tier/rang V-score (`tier_v2`/`rang_v2`, 2025).
- **Scan patrimoine › Possession** : propriétaire et droits (2026) + le tier servi par parcelle (2025).
- **Classement / Radar / listes triées par probabilité** : rang V-score (2025) sur des parcelles dont le
  propriétaire affiché est 2026.

À dire aux utilisateurs : « propriétaires à jour (2026) ; classement encore sur la photo 2025, recalcul à venir ».

## Durée réelle estimée sur `labuse` (V-score EXCLU)

Mesuré sur `labuse_scanfix` (tranche, ZIP en cache) : **≈ 40 s**. Sur `labuse` (île complète), postes
dominants, sans le V-score (le gros poste d'avant) :
- [0] sauvegarde : `CREATE TABLE AS` des 6 tables (toutes petites ici : `parcel_bloc_membres` ≈ 59 870,
  `parcelle_personne_morale` 82 701) → secondes.
- [1] droits : téléchargement 2 ZIP (149 Mo ×2) + parse 2×~95 k lignes → **~5-8 min** (réseau ; cache /tmp).
- [2] flip : swap `injection_sure` 84 045 lignes → secondes.
- [3] BODACC : `--bodacc-limit 0` interroge l'API pour ~12 600 SIREN → **minutes** (dépend de l'API).
- [4] blocs : self-join spatial `ST_DWithin` des 82 701 parcelles PM → ~11 222 blocs / ~59 870 membres → **minutes**.
→ **Ordre de grandeur : 10-20 min**, dominé par BODACC (API) et blocs ; **plus de reconstruction du feature
store de 4,3 M lignes** (retirée avec le V-score).

## Ce que les autres sessions verront changer pendant la bascule

- **Plus de `DROP/CREATE` du feature store** (V-score retiré) → la collision franche d'avant (scoring/
  `calcul-nuit`/candidat tombant sur « relation does not exist ») **n'existe plus**.
- [2] : `recompute_principal`→`remplacer_servie` exécute EN TÊTE de la transaction
  `ALTER parcelle_personne_morale ADD COLUMN IF NOT EXISTS droit_code/droit_label`. Sur `labuse` ces
  colonnes n'existent pas encore → l'ALTER prend un **`AccessExclusiveLock` sur `parcelle_personne_morale`,
  tenu jusqu'au commit** : **tout lecteur de cette table est BLOQUÉ (en attente) pendant l'étape [2]
  (quelques secondes)** — il ne « voit » pas l'ancienne version, il attend.
- [4] `build_blocs`→`ensure_schema` exécute EN TÊTE `ALTER parcel_blocs ADD COLUMN IF NOT EXISTS is_public`.
  Sur `labuse` la colonne existe déjà (no-op) **mais l'ALTER prend quand même un `AccessExclusiveLock` sur
  `parcel_blocs`, tenu jusqu'au commit** — donc pendant **TOUT** [4], y compris les **minutes** du
  `compute_blocs` (self-join spatial), AVANT toute écriture. **Les LECTURES de `parcel_blocs` (outil Blocs,
  pont Scan→Blocs) sont bloquées pendant toute la reconstruction**, pas seulement les écritures.
  `parcel_bloc_membres` : `DELETE`+`INSERT` (ROW EXCLUSIVE, lectures non bloquées sur cette table).
- [0]/`--rollback` : `CREATE TABLE AS` / `DELETE+INSERT` des 6 tables (rotation WAL modérée).
- **Reco** : fenêtre calme ; les propriétaires/blocs changent en quelques minutes. Le classement servi, lui,
  ne bouge pas (V-score hors bascule).

## Rollback — ce qui revient (prouvé)

`--rollback --sauvegarde <N>` restaure les **6** tables depuis `_bascule_bak__<N>__*` EN UNE transaction
(retire aussi `parcelle_pm_droit` et les colonnes `droit_code/droit_label` créées). Prouvé sur
`labuse_scanfix`, empreinte **toutes colonnes** : retour **identique à l'AVANT, table par table**, y compris
après un blocs-build RÉEL (669 blocs / 5 367 membres révertés) et après une interruption dure au milieu de
n'importe quelle étape. `data_sources` est neutralisée en [3] (net inchangée par le code ; à vérifier par
empreinte avant/après lors de la bascule réelle sur `labuse`), il n'y a donc rien à y restaurer.

## ARRÊT

Rien n'est exécuté sur `labuse`/prod. Vic déclenche la fenêtre.
