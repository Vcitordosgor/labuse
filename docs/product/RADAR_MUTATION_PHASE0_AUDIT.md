# Radar Mutation Foncière — Phase 0 : audit read-only — ⏸️ **en attente de validation**

> Audit **lecture seule** des fondations (code, données, docs) pour la fonctionnalité signature
> **Radar Mutation**. **Rien implémenté, rien modifié** (ni code, ni DB, ni commit). **Recommandation : 🟢 GO V1.**

## 1. Résumé exécutif

**LA BUSE possède déjà ~70 % des briques d'un Radar Mutation V1.** Le produit calcule un **score d'opportunité**,
un **verdict prudent**, un **score de complétude** et surtout une **« Mutabilité » (ratio bâti, BD TOPO)** avec un
mode carte dédié et un concept de **« restructuration potentielle »** (peu bâti sur grand terrain). Les données
nécessaires couvrent **22-24 / 24 communes**. La V1 consiste donc surtout à **reframer et agréger l'existant** en
un **Score Mutation** distinct du verdict — **simple, robuste, vendable** — pas à construire une usine à gaz.

**Distinction produit clé** : le **verdict opportunité** dit « à prospecter MAINTENANT » ; le **Radar Mutation** dit
« potentiel de transformation à surveiller » — il éclaire les **9 103 opportunités** *et surtout* les **~73 000
grandes parcelles latentes** + **18 006 parcelles juste sous le seuil** que le verdict actuel laisse en « à creuser ».

## 2. État initial & méthode

- `main = origin/main = c05dbc3`, git clean. DB : **431 663 parcelles / 24 communes / 17 gold / 0 stale / 9 103 opp**. Disque 3,0 G.
- **Audité (read-only)** : `docs/BAREME_VERDICT_MUTABILITE.md`, le modèle de données (13 tables/couches), `src/labuse/ingestion/signals.py`, le mode carte « Mutabilité » (`app.js`).
- **Fichiers listés dans la mission mais ABSENTS du repo** (notés sans blocage) : `prototypes/radar-mutation/`, `docs/product/RADAR_MUTATION_READONLY_AUDIT.md`, `docs/product/LABUSE_PRODUCT_ROADMAP_V1_V2_V3.md`, `docs/product/MASTER_HANDOFF_FOR_CLAUDE.md`, `docs/competitors/kelfoncier/`, `prototypes/labuse-v1-ux/`. → Aucun prototype Radar Mutation ni doc concurrent Kelfoncier dans le dépôt. L'audit s'appuie donc sur le **code + données réels** et `BAREME_VERDICT_MUTABILITE.md`.

## 3. Fondations déjà présentes (à réutiliser, pas à refaire)

| Brique existante | Où | Réutilisable pour |
|---|---|---|
| **Mutabilité = ratio bâti** (vacant <5 % · peu bâti 5-15 % · … · déjà bâti ≥50 %) | `bati.py`, couche `batiment` (812 994 bât., 23 communes) | Sous-exploitation, maison/grand terrain |
| **« Restructuration potentielle »** (peu bâti + parcelle > 5 000 m²) | barème §8 | Signal mutation déjà conceptualisé |
| **Contexte marché DVF** (médiane €/m² + liquidité) | bonus `contexte_dvf_favorable`, `dvf_mutations` (29 715, 24 communes) | Quartier qui mute, marché actif |
| **Potentiel foncier régional** | couche `potentiel_foncier` (2 453 îlots, 24 communes ; 13 105 parcelles recouvertes) | Îlot mutable, foncier stratégique |
| **Propriétaire personne morale** (SIREN/dénomination/type) | `parcelle_personne_morale` (12 539 parcelles) | Foncier public, acquisition facilitée |
| **Feedback agrégé par zone 300 m** | `scoring` / `feedback_terrain` | Concentration / rue-quartier qui mute |
| **Zonage U/AU, SAR, PPR, pente, accès, surface** | couches `plu_gpu_zone` (24), `sar` (23), `ppr` (22), `pente` (24), `voirie` (24) | Contradictions favorable/bloquant |
| **Score 0-100 + complétude + traçabilité** | `opportunity_weights.yaml`, fiche | Réutiliser pour un Score Mutation traçable |

## 4. Ce qui est FAISABLE maintenant (sans nouvelle donnée) — quantifié

| Signal | Calcul (données existantes) | Volume mesuré |
|---|---|---|
| **Sous-exploitation / maison sur grand terrain** | `batiment ∩ parcelle / surface` faible (5-30 %) sur grande surface | infra prête (812 994 bât.) ; **73 657** parcelles > 2 000 m² non-opp à filtrer |
| **À creuser presque opportunité** | `opportunity_score` 60-64 | **18 006** (55-64 : 30 462) |
| **Zonage favorable MAIS contrainte forte** | zone U/AU + PPR fort (ou SOFT_FLAG fort) + à creuser | **32 866** |
| **Foncier public stratégique** | `parcelle_personne_morale` type ∈ Commune/État/Département/Région/Étab. publics | **~4 823** (+ HLM 816, SEM 1 469 para-public) |
| **Marché actif (DVF)** | mutations DVF récentes ≤ 500 m, médiane €/m², liquidité | **~308 000** parcelles avec contexte DVF (24 communes) |
| **Recouvrement potentiel foncier régional** | `potentiel_foncier ∩ parcelle` | **13 105** parcelles |
| **Concentration / quartier qui mute** | densité d'opportunités + mutations DVF dans un buffer 300 m (infra feedback existe) | calculable (agrégation spatiale) |
| **Îlot mutable** | groupes de parcelles adjacentes sous-exploitées en zone U/AU | calculable (clustering spatial, V1 léger possible) |

## 5. Ce qui est À ÉVITER aujourd'hui (impossible / risqué)

| À éviter | Pourquoi |
|---|---|
| **Propriétaire privé nominatif / contact** | **Fichiers fonciers non branchés** (cascade `proprietaire` = 0 actif). Seules les **personnes morales** (SIREN, donnée légale publique) sont dispo. **RGPD** : pas de personne physique nominative. |
| **« Intention de vendre » / prédiction de vente** | Aucune donnée signal-faible fiable ; affirmation invendable et juridiquement risquée. |
| **Prédiction trop affirmative** (« va muter », « sera vendu ») | Contredit la **règle d'or** du produit (intensité ≠ promesse). Wording prudent obligatoire (« potentiel », « à surveiller »). |
| **Signaux SITADEL en l'état** | Couche présente mais **0 parcelle active** (permis non rattachés aux parcelles) → non fiable tant que non recâblé (V2). |
| **Score mutation « certain » par parcelle** | Trop bruité ; toujours assortir d'un **niveau de confiance** (complétude) + explication. |

## 6. Mapping données → signaux (synthèse)

```
batiment (23c)            → sous-exploitation, mutabilité, îlot mutable
parcels.surface_m2        → grand terrain, micro/macro
dvf_mutations (24c)       → marché actif, quartier qui mute
potentiel_foncier (24c)   → îlot mutable, foncier stratégique
parcelle_personne_morale  → foncier public, acquisition facilitée
plu_gpu_zone (24c) + sar  → zonage favorable, contradiction
ppr (22c) + pente (24c)   → contrainte bloquante (vigilance, pas exclusion)
parcel_evaluations        → near-threshold, base score/complétude
voirie (24c)              → accès (vigilance)
feedback_terrain / 300 m  → concentration de signaux par secteur
```

## 7. Scoring proposé — **Score Mutation (0-100)**, distinct du verdict

> **Principe** : un score *additif borné et traçable*, à l'image du score d'opportunité, mais orienté **potentiel de
> transformation**, pas **prospection immédiate**. Chaque composante est plafonnée (pas d'effet mécanique), tracée,
> et assortie d'une **confiance = complétude**. Formule **indicative V1 (à calibrer, jamais présentée comme sourcée)** :

```
score_mutation = clamp( Σ composantes , 0, 100 )   # chaque composante ∈ [0, plafond]
  + sous_exploitation   (plafond 30) : grand terrain peu bâti (courbe saturante surface × (1 − ratio_bâti))
  + marche_actif        (plafond 20) : liquidité + tendance €/m² DVF dans le voisinage
  + zonage_favorable    (plafond 15) : zone U/AU (binaire) × accès
  + potentiel_regional  (plafond 15) : recouvrement îlot potentiel foncier régional
  + foncier_strategique (plafond 10) : propriétaire public/morale acquérable
  + concentration_300m  (plafond 10) : densité d'opportunités/mutations dans le secteur
  − contraintes_fortes  (malus)      : PPR fort / pente / ER (vigilance, plafonne le niveau de confiance)
confiance = score_complétude (déjà calculé)
```

**Badges / niveaux prudents** (jamais 4 verdicts ré-inventés) :
- 🟣 **Mutation à surveiller** (score élevé + confiance ≥ 50)
- 🟡 **Potentiel à creuser** (score moyen ou confiance < 50)
- ⚪ **Peu de potentiel mutation** (score bas)
- Wording type : *« Potentiel de transformation : grand terrain peu bâti en zone U, marché actif à proximité — à
  vérifier (PPR à confirmer) »*. **Toujours** « potentiel/à surveiller », jamais « va muter ».

## 8. Intégration backend (V1, minimale)

- **1 vue/calcul read-only** `mutation_score(parcel)` réutilisant les couches déjà cascadées (aucune re-cascade) —
  idéalement une **vue SQL matérialisée** ou un champ dérivé calculé à la volée comme `/stats`.
- **1 endpoint** : `GET /mutation?commune=…` (liste triée par score mutation) + `GET /parcels/{idu}` enrichi d'un
  bloc `mutation` (score + composantes + confiance + explication), sur le modèle du bloc `verdict` existant.
- **Aucune écriture DB** côté lecture ; si persistance souhaitée plus tard, table `parcel_mutation` séparée (ne
  jamais toucher `parcel_evaluations`).

## 9. Intégration frontend (V1, minimale)

- **Réutiliser le mode carte « Mutabilité »** existant → ajouter un **3ᵉ mode « Radar Mutation »** (coloration par
  score mutation), à côté de `Couleur / Verdict / Mutabilité`.
- **Badge mutation** sur les fiches + une **liste « Radar Mutation »** (top potentiels du secteur), distincte de la
  shortlist opportunités.
- **Bandeau d'explication** prudent + **niveau de confiance** visible (réutilise le bandeau de fiabilité non-gold
  déjà présent). Filtre « afficher le potentiel mutation » sur la carte.

## 10. Risques

- **Bruit / sur-promesse** → mitigé par le plafonnement, la confiance (complétude) et le wording prudent.
- **RGPD** (propriétaires) → s'en tenir aux **personnes morales** (donnée légale) ; **jamais** de personne physique.
- **Calibration** → seuils V1 = **PLACEHOLDER** à caler avec le terrain (comme le barème actuel), jamais sourcés.
- **Couverture** → 1-2 communes manquent sur `batiment`/`ppr`/`sar` → afficher « occupation/risque non vérifié »,
  jamais un faux « vacant » (politique déjà en place).
- **Performance** → agrégations spatiales 300 m / clustering îlot : borner au commune-par-commune (comme la cascade).

## 11. Plan d'implémentation par étapes

- **V1 — rapide, données actuelles (recommandé)** : Score Mutation additif (composantes §7 disponibles à 100 %),
  endpoint `/mutation`, 3ᵉ mode carte + badge + liste. **0 nouvelle donnée, 0 re-cascade.** Cible : sous-exploitation,
  near-threshold, zonage+contrainte, foncier public, marché DVF, potentiel régional.
- **V2 — enrichissement léger** : recâbler **SITADEL** (permis ↔ parcelles), **clustering « îlot mutable »**
  (parcelles adjacentes), **indice quartier-qui-mute** (série temporelle DVF + densité permis 300 m), brancher
  formellement la donnée **personne morale** dans le score.
- **V3 — premium, long terme** : **Fichiers fonciers** nominatifs (cadre convention + RGPD), **suivi temporel** de
  mutation (DVF time-series → « secteur en bascule »), **alertes/watch-zones** sur déclencheurs de mutation,
  éventuel modèle prédictif **calibré et prudent**.

## 12. Recommandation finale — 🟢 **GO (V1 prudente)**

Le Radar Mutation V1 est **faisable immédiatement, à faible risque**, car LA BUSE possède déjà la mutabilité (bâti),
le marché (DVF), le zonage, le potentiel foncier régional, la propriété morale et un moteur de score traçable, le
tout sur **22-24/24 communes**. La valeur produit est forte (révéler les **~73 k grandes parcelles latentes** + **18 k
near-threshold** + **~4,8 k fonciers publics** que le verdict actuel ne met pas en avant) **sans toucher au scoring
opportunité existant**. **Garde-fous** : score *distinct* du verdict, wording « potentiel/à surveiller », confiance
visible, personnes morales uniquement. **ATTENTION** ciblée sur la calibration (PLACEHOLDER) et SITADEL (V2).

---

### Provenance (lecture seule)
- Comptes/couvertures via `psql` (SELECT). Barème via `docs/BAREME_VERDICT_MUTABILITE.md`. Aucune écriture DB, aucun
  code modifié, aucune re-cascade/import/migration, aucun commit. Rapport **non commité**.
