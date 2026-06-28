# Radar Mutation V1 — Notes de version

> Fonctionnalité de **détection de potentiel de transformation foncière**, **distincte** du
> verdict d'opportunité LA BUSE. Lecture seule, prudente, calibrée sur Saint-Paul (pilote).
> État : moteur + API + UI (fiche, sidebar, calque carte) + cache + docs. Rédigé le 2026-06-27.

## Ce que fait Radar Mutation

Radar Mutation attribue à chaque parcelle un **score 0–100** de **potentiel de transformation
foncière** — la probabilité qu'une parcelle soit un **sujet à étudier** pour une mutation (densification,
restructuration, mobilisation de foncier). Il combine des **signaux additifs explicables** :

- **Sous-exploitation** : grand terrain peu bâti (courbe saturante surface × (1 − bâti)).
- **Intensité latente** : parcelle « à creuser » proche du seuil d'opportunité (presque-seuil).
- **Zonage favorable** : zone U/AU (constructible au PLU).
- **Potentiel régional** : recouvre un îlot de potentiel foncier (SAR/Région).
- **Marché actif** : mutations DVF à proximité.
- **Foncier acquérable** : propriétaire personne morale / public (acquisition potentiellement facilitée).
- **Malus** : contrainte forte (PPR / pente forte) → vigilance.

Chaque score s'accompagne de **badges**, de **raisons chiffrées** (`+points`), d'une **confiance**
(complétude des données) et de **niveaux** : **prioritaire ≥ 70**, **forte 55–69**, **à surveiller
40–54**, **faible < 40**. Règle d'or : sous une confiance de 50, jamais de niveau « ferme »
(plafonné à « surveiller »).

**Exposition produit :**
- **Fiche parcelle** : bloc « Radar Mutation » (accent violet) sous le verdict.
- **Sidebar** « Radar Mutation — à surveiller » : top du jour, filtre **Prioritaire / Forte**.
- **Carte** : calque « Radar Mutation (potentiel) » optionnel (OFF par défaut), parcelles violettes.
- **API** : `GET /mutation/{idu}`, `GET /mutation?commune&niveau&min_score&limit`,
  `GET /map/mutation.geojson` (lecture seule, cache mémoire TTL).

## Ce que ça ne promet PAS

- ❌ **Pas** une garantie de **constructibilité** (le PLU/PPR/SAR restent à croiser).
- ❌ **Pas** un conseil d'**achat**, **pas** une prédiction que « le propriétaire vendra ».
- ❌ **Pas** un verdict d'opportunité (c'est un **axe différent**, cf. ci-dessous).
- C'est un **potentiel à étudier** — un point de départ d'analyse, jamais une conclusion.

## Différence avec le verdict d'opportunité

| | Verdict d'opportunité | Radar Mutation |
|---|---|---|
| Question | « Est-ce un sujet à prospecter **maintenant** ? » | « Cette parcelle a-t-elle un **potentiel de transformation** à étudier ? » |
| Sortie | opportunité / à creuser / écartée / faux positif | score 0–100 + niveau (prioritaire…faible) |
| Couleur UI | vert / orange / gris / rouge | **violet** (volontairement distinct) |
| Relation | — | **indépendant** : une parcelle peut être « à creuser » au verdict **et** « prioritaire » au radar |

Les deux **coexistent** dans la fiche, clairement séparés, pour éviter toute confusion.

## Exemples (Saint-Paul, réels)

- **`97415000DM0031`** — Radar **Prioritaire 100/100** (24 038 m², 0 % bâti, Département) ; verdict
  « À creuser ». Grand terrain public sous-exploité → fort potentiel **à étudier**.
- **`97415000CP0024`** — verdict **« Opportunité » (85)** **ET** Radar **Prioritaire 75/100** :
  coexistence des deux axes sans contradiction.
- **`97415000AB0491`** — Radar **Prioritaire 88/100**, verdict « À creuser ».
- **`97415000ET1719`** — Radar **Faible 33/100** : potentiel limité (petite parcelle bâtie).

## Limites connues

- **Calibrage pilote** : pondérations V1 calées sur Saint-Paul, à confirmer terrain (24 communes).
- **Cold start** : 1er calcul d'une liste commune ~4,7 s (puis **mémorisé**, ~0–9 ms). Cf. plan perf.
- **Sidebar « à surveiller »** : le top ne remonte que **prioritaire / forte** (la présélection
  privilégie le haut du panier ; « surveiller » nécessiterait un pool plus large — cf. perf plan).
- **Bâti** : ratio issu de BD TOPO (indicatif) ; si la couche manque, jamais de faux « vacant ».

## Prochaine étape

- **Perf froide** : réécriture SQL une passe + départage déterministe (×3,9, reproductible — décision
  produit) ou **index** `cascade_results` (×5–9, GO DB). Voir `RADAR_MUTATION_PERF_PLAN.md`.
- **Calibrage multi-communes** et éventuelle **matérialisation** des scores (multi-niveaux instantané).
