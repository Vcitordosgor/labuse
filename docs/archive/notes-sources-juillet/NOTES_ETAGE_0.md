# NOTES — Refonte scoring, session 1 : Étage 0 (filtre dur) + fix `_resolve_commune`

Branche `refonte/etage-0-filtre-dur`. **Non mergée** — Vic valide puis merge en `--no-ff`.

## Ce qui a été fait (rappel des 3 livrables)

### Livrable 1 — Fusion des bloquants francs du déclassement dans le filtre dur (phase 1)

Les bloquants **francs** deviennent des couches d'élimination de **phase 1**, « au même titre que
`eau` » (brief). Choix d'implémentation : chaque franc va dans **sa couche respective** (le brief dit
« params de leurs couches respectives »), qui existait déjà :

| Bloquant franc | Couche phase 1 | Nouveau param YAML | Ex-constante `declassement.py` |
|---|---|---|---|
| micro-parcelle | `surface` | `faux_positif_max_m2: 100` | `SURFACE_FAUX_M2` |
| pente non aménageable | `pente` | `seuil_faux_positif_pct: 60` | `PENTE_FAUX_PCT` |
| équipement OSM dominant | `osm_faux_positif` | `faux_positif_coverage: 0.50` | `OSM_FAUX_COVERAGE` |
| déjà bâti franc | **`bati`** (nouvelle) | — (cf. ci-dessous) | (logique R1, `bati.py`) |

Ces couches émettent désormais un `HARD_EXCLUDE` **kind=`faux_positif`** en phase 1. Effet clé :
`compute_opportunity` voit le hard-exclude → **score brut = 0**. Plus de « 78/100 — faux positif
probable » : une parcelle éliminée n'a plus de score fantôme.

**Signaux réutilisés, pas réécrits** : `compute_declass_signals` est calculé **une fois**, AVANT la
cascade, et injecté dans `ctx.declass_signals`. Les couches `surface`/`pente`/`osm_faux_positif`
lisent déjà leur signal via `parcel.surface_m2` / `ctx.intersections` (mêmes sources exactes que le
déclassement — `Parcel.surface_m2` est bien `ST_Area(geom_2975)`, vérifié). Seule la couche `bati`
lit `ctx.declass_signals` (la couche `kind='batiment'` est volontairement exclue du `prime()` pour le
coût overlay — inchangé).

**Cas non-francs laissés en place** (`declassement.py`, chacun tagué `# TODO étage 1`) : surface
100–250 m², pente 40–60 %, OSM 30–50 %, occupation partielle, accès à vérifier. **Comportement
inchangé.** Ils ne s'appliquent plus qu'aux **survivants** de l'étage 0 (garde `if not
opportunity.hard_exclude` dans le pipeline) — ce qui garantit aussi que la borne basse de chaque
bande non-franche = le seuil franc de la couche (un survivant a forcément `surface ≥ 100`, `pente ≤ 60`,
`OSM < 0.50`), sans dupliquer de constante.

### Livrable 2 — Plus aucun HARD_EXCLUDE en aval de la cascade

- Couches **phase 2** (`dvf`, `sitadel`, `potentiel_foncier_region`, `proprietaire`) : vérifié, aucune
  n'émet de `HARD_EXCLUDE`.
- Le bloc déclassement du pipeline n'émet plus QUE des `SOFT_FLAG` (le franc a migré en phase 1).
  Imports `hard_exclude` / `EvaluationStatus` retirés de `pipeline.py` (devenus inutiles).
- **Invariant testé** (`tests/test_cascade.py::test_invariant_survivant_aucun_hard_exclude_en_aval`,
  + `test_eliminee_na_pas_de_score_fantome`) : toute parcelle promue → zéro HARD_EXCLUDE en aval ;
  toute parcelle éliminée → score = 0. **Verts sur données réelles (démo Saint-Paul).**

### Livrable 3 — Fix `_resolve_commune` + garde-fou échec bruyant

- `_resolve_commune` : un INSEE 5 chiffres (pilote **ou non**) est résolu vers le nom officiel via
  `_commune_nom` avant d'être renvoyé brut. (Avant : INSEE non-pilote renvoyé brut → 0 parcelle
  silencieuse.)
- `_fail_zero_parcel` (nouveau) : `evaluate` **et** `discover` échouent bruyamment (`typer.Exit(1)`)
  sur 0 parcelle, en distinguant « base vide » de « commune inconnue / résolution INSEE échouée ».
  Jamais un succès vide silencieux.

## Décisions / écarts à connaître pour la revue

1. **Seuils `bati` NON migrés en YAML — volontaire.** Les paliers d'occupation bâtie vivent dans
   `bati.py` (mission R1) et sont la **source unique de vérité** partagée avec la fiche « Occupation »
   et les exports. Les migrer en `cascade_rules.yaml` les dédoublerait/désynchroniserait. La couche
   `bati` réutilise `bati.classify` tel quel ; seul le cas `declasse == 'faux_positif'` élimine. Les
   constantes `declassement.py:18-28` visées par le brief (surface/pente/OSM) sont, elles, bien
   migrées.

2. **« Enclavement franc » (brief §Livrable 1) : rien à déplacer.** Le brief le liste parmi les
   bloquants francs, mais dans le code l'accès (`acces_dist_m`) ne produit **jamais** de
   `faux_positif` — uniquement `à creuser` (audit O1 : une servitude/desserte non cartographiée reste
   possible → jamais une exclusion). Il n'existe donc aucun cas franc d'enclavement à éliminer. Laissé
   intégralement en non-franc dans `declassement.py`. **À confirmer par Vic** si un vrai enclavement
   franc (0 accès possible) doit devenir éliminatoire un jour — ce serait un changement de politique,
   hors périmètre de cette session.

3. **Perte de l'escalade « ≥2 signaux francs → EXCLUE ».** Avant, deux faux positifs francs cumulés
   (ex. surface 40 + pente 80) donnaient `exclue`. Sous le modèle cascade, deux HARD_EXCLUDE
   `kind=faux_positif` restent `faux_positif` (l'escalade vers `exclue` est réservée aux vraies
   exclusions dures : eau, cœur Parc, PPR rouge). Jugé **plus correct** (ce sont des faux positifs,
   pas des interdictions réglementaires). Test `test_plusieurs_signaux_forts_excluent` retiré/adapté.

4. **Tests mis à jour (avec justification en docstring/commentaire)** :
   - `test_declassement.py` : réécrit pour le contrat NON-franc (les entrées franches ne renvoient
     plus `faux_positif`/`exclue` ici — couvert par `test_etage0_filtre_dur.py`).
   - `test_bati.py` : les 2 cas `apply_declassement` francs (déjà bâti / ensemble bâti) → n'émettent
     plus de motif ici (déplacés en phase 1). Le reste (classify pur, a_creuser, accès, signaux DB)
     inchangé.
   - `tests/test_etage0_filtre_dur.py` (nouveau, PUR) : verrouille l'élimination franche des 4
     couches via un `ctx` simulé + les params YAML réels.
   - `tests/test_cli_resolve.py` (nouveau, PUR) : résolution INSEE pilote/non-pilote/inconnu.

## Environnement / pré-existant (à NE PAS confondre avec cette session)

Suite lancée localement avec `LABUSE_TEST_DATABASE_URL=postgresql+psycopg://openclaw@127.0.0.1:5432/labuse_test`
et `PROJ_DATA=/Users/openclaw/miniforge3/envs/labusedb/share/proj` (pyproj n'a pas de PROJ data dans
le `.venv`). Résultat : **507 passed**, 12 skipped, 4 failed — **les 4 échecs sont PRÉ-EXISTANTS sur
`main`/HEAD** (diff des échecs branche vs HEAD = ∅, aucune régression) :

- `test_cascade.py` : `test_statuts_attendus`, `test_exclusions_sont_dures`,
  `test_promotion_phase2_ne_tourne_pas_sur_exclues` — P3 (PPR rouge) n'est pas exclue **dans cette
  base de démo locale** (la couche PPR rouge ne s'y sème pas en `INTERDICTION`). Indépendant de cette
  session (identique en stashant tous mes changements). À revérifier en CI où la démo est correcte.
- `test_backup.py::test_backup_puis_restore_sur_base_temporaire` — dépend de `pg_dump`/droits temp DB.

## Tentations HORS périmètre repérées (non faites — pour une autre session)

- Le bloc déclassement du pipeline pourrait, à terme, disparaître complètement au profit des flags
  qualité de l'étage 1 (session suivante). Laissé en place, comportement non-franc intact.
- Double calcul surface/pente/OSM (`compute_declass_signals` **et** `ctx.prime`) : pré-existant, non
  optimisé ici (aucune requête ajoutée par mes changements). Piste perf hors périmètre.
- Migration complète des bandes non-franches (250 / 40 / 0.30) en YAML : c'est l'étage 1.
