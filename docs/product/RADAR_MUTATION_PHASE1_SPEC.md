# Radar Mutation Foncière — Phase 1 : spécification V1 — ⏸️ **en attente de validation**

> Spécification **prête à implémenter** de la V1 Radar Mutation. **Aucune implémentation** : pas de code, DB,
> endpoint, UI, scoring modifié. Calibrage par **requêtes lecture seule** sur la DB réelle (431 663 parcelles).
> **Recommandation : 🟢 GO implémentation (Phase 2).**

## 1. Résumé exécutif

**Radar Mutation V1** = un **Score Mutation (0-100) distinct du verdict d'opportunité**, qui révèle les parcelles à
**potentiel de transformation foncière** — surtout celles que le verdict actuel laisse en « à creuser ». Calibré sur
la DB réelle, il produit une **shortlist premium de ~1 992 parcelles « prioritaires »** (≈ 412 pour Saint-Paul), pas
50 000 résultats inutiles. Les composantes sont **100 % calculables avec les données existantes** (mutabilité bâti,
surface, zonage, DVF, potentiel régional, propriété morale) **sans re-cascade ni nouvelle donnée**. Validation : les
6 meilleures parcelles sont de **vrais grands terrains sous-exploités** (2-3 ha, 0-3,5 % bâti, zone U, near-threshold,
propriétaires société/**Commune**/**Département**).

## 2. Définition de la V1

| Élément | Définition |
|---|---|
| **Nom fonctionnalité** | **Radar Mutation** (métrique : **Score Mutation** ; badge : « Potentiel de mutation ») |
| **Objectif utilisateur** | Repérer le **foncier à fort potentiel de transformation** (à acquérir/restructurer), pas seulement les opportunités déjà chaudes |
| **≠ verdict opportunité** | Le **verdict** = « à prospecter MAINTENANT » (signal fort + données suffisantes). Le **Radar Mutation** = « **potentiel futur à étudier** » — il surface surtout les `à creuser` latents (grand terrain sous-bâti, presque-seuil, foncier public) |
| **Cas d'usage promoteur** | « Montre-moi les **grandes parcelles sous-exploitées en zone constructible**, propriétaire acquérable, marché actif — même si ce n'est pas encore une opportunité chaude » |
| **Wording prudent** | Toujours **« potentiel de mutation à étudier »**, jamais « constructible certain » / « va muter » / « sera vendu ». Sépare explicitement **opportunité actuelle** et **potentiel futur**. |

## 3. Score Mutation V1 — formule détaillée

> Score **additif, borné [0,100], traçable** (même philosophie que le score d'opportunité). Chaque composante est
> **plafonnée** ; la **confiance = score de complétude** (déjà calculé). Seuils = **PLACEHOLDER à calibrer terrain**.

```
score_mutation = clamp( Σ composantes , 0 , 100 )
  + sous_exploitation   (plafond 30) : surface saturante × (1 − ratio_bâti)   [bâti via bati.py/BD TOPO]
  + intensite_latente   (plafond 25) : statut × score d'opportunité (cf. table)
  + zonage_favorable    (plafond 15) : zone U/AU (binaire)
  + potentiel_regional  (plafond 15) : recouvrement îlot « potentiel foncier régional »
  + marche_actif        (plafond 10) : contexte DVF favorable (liquidité + médiane €/m²)
  + foncier_acquerable  (plafond  8) : propriétaire personne morale (public stratégique = +badge)
  − contraintes_fortes  (malus −15)  : PPR fort / pente forte / ER (vigilance ; plafonne aussi la confiance)
confiance = completeness_score   (0-100, bande forte/moyenne/faible déjà définie)
```

**`intensite_latente`** (cœur : « presque opportunité » > déjà opportunité) :

| Statut + score | Points | Logique |
|---|:--:|---|
| `à creuser` score 55-64 | **25** | near-threshold — le gisement principal |
| `à creuser` score 45-54 | 15 | potentiel moyen |
| `à creuser` autre | 8 | base latente |
| `opportunité` | 5 | déjà surfacée par le verdict (mutation = bonus faible) |
| `faux positif` / `exclue` | 0 | déjà bâti / bloqué — pas de mutation |

## 4. Calibrage chiffré (requêtes lecture seule, 427 501 parcelles évaluées)

| Niveau | Seuil score | Parcelles | Usage |
|---|---|---:|---|
| 🔴 **Mutation prioritaire** | ≥ 70 | **1 992** | **Shortlist premium** (Saint-Paul 412, Le Tampon 304, Saint-Pierre 180…) |
| 🟣 **Mutation forte** | 55-69 | **16 855** | Liste « à explorer » (filtrable) |
| 🟡 **À surveiller** | 40-54 | 47 790 | Carte / filtre secondaire |
| ⚪ **Faible / négligeable** | < 40 | ~360 800 | Fond de carte |

Moyenne 23,4 · max 93 (= plafond réel des composantes). **La V1 expose surtout les niveaux 🔴/🟣 (~19 k), shortlist
🔴 ~2 k.** Validation bâti (6 top) : **0-3,5 % bâti sur 19 000-31 000 m²** → vrais grands terrains sous-exploités.

## 5. Signaux V1 retenus

| Signal | Source DB | Condition exacte | Poids | Fiabilité | Risque faux-positif | Wording |
|---|---|---|:--:|---|---|---|
| **Sous-exploitation / maison sur grand terrain** | `batiment` (BD TOPO) ∩ `parcels.surface_m2` | `bati_ratio < 15 %` ET `surface > 1000 m²` | 30 | **Haute** (BD TOPO) | bas (couche fiable ; 23/24 communes) | « Grand terrain peu bâti (X % bâti) » |
| **Intensité latente (near-threshold)** | `parcel_evaluations` | `à creuser` ET `score 55-64` | 25 | Haute | bas | « Presque opportunité (score X/65) » |
| **Zonage favorable** | `cascade_results` zonage_plu_gpu | `POSITIVE` (zone U/AU) | 15 | Haute (24/24) | bas | « Zone constructible (U/AU) » |
| **Potentiel foncier régional** | couche `potentiel_foncier` | recouvrement îlot | 15 | Moyenne (planif. régionale) | moyen (indicatif) | « Dans un îlot de potentiel foncier régional » |
| **Marché actif (DVF)** | `dvf_mutations` / cascade dvf | mutations ≤ 500 m, médiane €/m² + liquidité | 10 | Haute (24/24) | bas | « Marché actif à proximité (~X €/m²) » |
| **Foncier acquérable / public** | `parcelle_personne_morale` | propriétaire morale ; public si Commune/État/Dpt/Région/Étab. | 8 | Haute (donnée légale) | bas | « Propriétaire personne morale (acquisition facilitée) » / « Foncier public » |
| **Contrainte forte (malus)** | cascade risques/pente/prescription | PPR fort / pente forte / ER | −15 | Haute | — | « Vigilance : PPR fort / pente — à confirmer » |
| **Concentration secteur (optionnel V1.1)** | agrégation 300 m | densité opp + mutations DVF voisines | (bonus) | Moyenne | moyen | « Secteur en mouvement » |

## 6. Signaux EXCLUS de la V1 (NO-GO)

| Exclu | Raison |
|---|---|
| **Propriétaire privé nominatif / contact** | Fichiers fonciers **non branchés** (cascade `proprietaire` = 0 actif) + **RGPD** (personne physique). Seules les **personnes morales** (SIREN) sont autorisées. |
| **Intention de vendre / prédiction de vente** | Aucune donnée fiable ; juridiquement risqué et invendable. |
| **Prédiction « certaine »** (constructible/va muter) | Contredit la règle d'or (intensité ≠ promesse). |
| **SITADEL en l'état** | Couche présente mais **0 parcelle active** (permis non rattachés) → V2 après recâblage. |
| **Score sans confiance affichée** | Toujours assortir le score d'un **niveau de confiance** (complétude) + explication. |

## 7. Architecture backend (à implémenter en Phase 2 — non fait ici)

- **Service** `mutation.py` : `mutation_score(session, parcel_id|commune) -> dict` (lecture seule). Réutilise
  `bati.stats_batch` (ratio bâti, déjà utilisé par `/map/bati`), les `cascade_results` déjà persistés et
  `parcel_evaluations` — **aucune re-cascade**.
- **Tables utilisées (lecture)** : `parcels`, `parcel_evaluations`, `cascade_results`, `spatial_layers` (batiment,
  potentiel_foncier, plu_gpu_zone), `dvf_mutations`, `parcelle_personne_morale`. **Aucune écriture** ; si persistance
  voulue plus tard → table **`parcel_mutation`** séparée (jamais toucher `parcel_evaluations`).
- **Endpoint** `GET /mutation?commune=…&min_score=…&limit=…` → liste triée ; bloc `mutation` ajouté à
  `GET /parcels/{idu}` (sur le modèle du bloc `verdict`).
- **Format JSON** (proposé) :

```json
{ "idu": "97415000DM0031", "commune": "Saint-Paul",
  "mutation": {
    "score": 83, "niveau": "prioritaire", "confiance": 92,
    "composantes": [
      {"cle": "sous_exploitation", "points": 30, "detail": "0 % bâti sur 24 038 m²"},
      {"cle": "intensite_latente", "points": 25, "detail": "à creuser, score 63/65"},
      {"cle": "zonage_favorable", "points": 15, "detail": "zone U"},
      {"cle": "marche_actif", "points": 10, "detail": "marché DVF actif"},
      {"cle": "foncier_acquerable", "points": 8, "detail": "propriétaire : Département (foncier public)"}
    ],
    "explication": "Grand terrain quasi non bâti en zone constructible, presque-seuil, propriété publique — potentiel de transformation à étudier.",
    "avertissement": "Potentiel à étudier — ni constructibilité ni vente garanties." } }
```

- **Tests à écrire** : score borné [0,100] ; idempotence ; une parcelle déjà bâtie (`bati_ratio` élevé) ne sort
  jamais « prioritaire » ; PPR fort applique le malus ; foncier public détecté ; couverture commune sans `batiment`
  → composante sous-exploitation absente (jamais un faux « vacant »).

## 8. Architecture frontend (Phase 2)

- **Mode carte « Radar Mutation »** : 3ᵉ bascule à côté de `Couleur / Verdict / Mutabilité` (réutilise le toggle
  existant `app.js`), coloration par niveau (🔴/🟣/🟡/⚪).
- **Badge fiche** : « Potentiel de mutation : prioritaire/forte/à surveiller » + **niveau de confiance**.
- **Liste « Parcelles à surveiller »** : onglet distinct de la shortlist opportunités, trié par Score Mutation.
- **« Pourquoi cette parcelle remonte ? »** : liste des composantes (cf. JSON) en clair.
- **Filtres** : niveau min, surface min, « foncier public uniquement », « zone U/AU », « exclure PPR fort ».
- **Libellés prudents** : « potentiel à étudier », bandeau d'avertissement réutilisant le bandeau de fiabilité.

**5 cartes types (exemples réels validés, Saint-Paul)** :
1. `97415000DM0031` — 24 038 m², **0 % bâti**, zone U, à creuser 63, **Département (foncier public)** → MS 83 « prioritaire ».
2. `97415000HK0566` — 19 936 m², 1,2 % bâti, **Commune** → MS 83 « foncier public stratégique ».
3. `97415000DM0890` — 31 581 m², 1,3 % bâti, société, score 61 → MS 83 « grand terrain sous-exploité ».
4. `97415000ET1724` — 30 117 m², 3,5 % bâti, score 63 → MS 83 « presque opportunité sur grand foncier ».
5. *(contre-exemple)* parcelle `à creuser` zone U **MAIS PPR fort** (cf. 32 866 parcelles) → malus −15, « à surveiller » + vigilance risque.

## 9. Risques & complexité

| Axe | Niveau | Mitigation |
|---|---|---|
| **Complexité technique** | **Faible-moyenne** | ~70 % des briques existent ; le service est de la lecture/agrégation. Seul point spatial : `bati.stats_batch` (déjà en prod via `/map/bati`). |
| **Bruit / sur-promesse** | Moyen | Plafonds + confiance + wording prudent + malus contraintes. |
| **Calibration** | Moyen | Seuils PLACEHOLDER (70/55/40) à caler avec le terrain (Vic), comme le barème actuel. |
| **RGPD** | Faible (si discipline) | Personnes morales uniquement. |
| **Performance** | Faible | Borné commune-par-commune (comme cascade/map). |

## 10. Plan d'implémentation Phase 2

1. `mutation.py` (service lecture seule) + tests unitaires (formule, bornes, garde-fous).
2. Endpoint `GET /mutation` + bloc `mutation` dans `/parcels/{idu}`.
3. Mode carte + badge + liste + « pourquoi » (frontend).
4. Calibration terrain des seuils (70/55/40) avec Vic sur Saint-Paul (pilote, 412 prioritaires).
5. (V1.1) composante concentration 300 m si jugée utile.

## 11. Recommandation finale — 🟢 **GO (implémentation Phase 2)**

V1 **faisable, à risque faible, fortement vendable** : score distinct du verdict, calibré (shortlist premium ~2 k,
validée sur cas réels), 100 % données existantes, garde-fous RGPD/prudence intégrés. **ATTENTION** : caler les seuils
en terrain (PLACEHOLDER) et garder SITADEL pour V2. **NO-GO** maintenir sur tout signal propriétaire-privé/prédictif.

---

### Provenance (lecture seule)
- Lus : `docs/product/RADAR_MUTATION_PHASE0_AUDIT.md`, `docs/BAREME_VERDICT_MUTABILITE.md`, `ingestion/signals.py`,
  `api/app.py` (`/map/bati`, mode mutabilité `app.js`). Calibrage : SELECT sur `parcel_evaluations`/`cascade_results`/
  `parcels`/`parcelle_personne_morale` + `bati.stats_batch` (6 parcelles). **Aucune écriture DB, aucun code modifié,
  aucune re-cascade/import, aucun commit.** Spec **non commitée**.
