# SYNTHÈSE M9 — Fiche enrichie : indice de confiance, règlement PLU, signalement, mutabilité

**Branche** `feat/m9-fiche-enrichie` (aucun merge) · **base servie** `q_v5_m6b` / run v2 `m36-l2f-2026-2026-07-14`
· Additif : aucun ré-entraînement du modèle P (gelé), aucune donnée supprimée hors décision Mutabilité (lot 4).
**Gates** : Golden **32/32**, cohérence **3/3**, E2E M9 **21/21**, pytest **792 passed** (8 échecs PRÉ-EXISTANTS, cf. §6).

---

## Lot 1 — Indice de confiance données (ICD)

### Ce que c'est (et ce que ce n'est pas)
L'**ICD ∈ [0, 100]** mesure la **complétude PONDÉRÉE** des données qui alimentent le scoring v2
pour UNE parcelle : combien de couches sont présentes vs manquantes. Il implémente la spec
d'audit **§1.4 A.4** (`reports/m6-audit/sections/1-4-scoring-v2.md`).

> ⚠ **Cloisonnement strict du score P.** L'ICD **ne modifie jamais** le score P (`p_raw`), le rang,
> le percentile ni le tier. Le modèle P reste **gelé** (sha256 au manifeste). L'ICD est une **colonne
> annexe** (`parcel_p_score_v2.icd` / `.icd_detail`) calculée **en lecture** depuis `p_model_ext_dataset` ;
> aucun recalcul, aucune ré-évaluation. Une parcelle à ICD bas peut porter n'importe quel tier : l'ICD
> dit « à quel point les données sont complètes », pas « à quel point c'est une opportunité ».
> Source unique de la formule : `src/labuse/scoring/icd.py` (SQL et Python dérivent de la même table `ICD_GROUPS`).

### Formule (9 groupes nullables, poids = 100)

| Groupe | Test « renseigné » | Poids |
|---|---|---|
| Résiduel / capacité C | `pct_potentiel IS NOT NULL` | 20 |
| Zonage PLU | `zone_plu <> 'inconnu'` | 15 |
| Végétation | `canopee_pct IS NOT NULL` | 15 |
| Prix terrain secteur | `med_pm2_terrain_36m IS NOT NULL` | 10 |
| Prix bâti secteur | `med_pm2_bati_36m IS NOT NULL` | 10 |
| Filosofi | `filo_snv_pp IS NOT NULL` | 10 |
| Tenure | `tenure_bin <> 'inconnu'` | 10 |
| Tendance prix | `tendance_pm2_bati IS NOT NULL` | 5 |
| Pente | `pente_moy_deg IS NOT NULL` | 5 |

`ICD = Σ poids des groupes renseignés`. `icd_detail` = `{groupe: bool}` des 9 groupes (→ libellés client
« ce qui manque »). Bandes d'affichage : **≥ 85** confiance haute (aucun badge), **60–84** « données
partielles » (badge gris), **< 60** « confiance faible » (badge orange + mention obligatoire au PDF).

### Distribution observée (run servi, 431 663 parcelles) — cf. `captures/icd-distribution.txt`

| Bande | Parcelles | % | (spec §1.4 attendait) |
|---|---|---|---|
| haute (≥ 85) | 250 106 | **57,9 %** | ~60 % du parc |
| partielle (60–84) | 151 738 | 35,2 % | — |
| faible (< 60) | 29 819 | 6,9 % | — |

Bornes **5 → 100**, médiane **90**, 0 NULL. **Preuve de cloisonnement / d'invariance** : le taux de
complétude **croît** avec l'ambition du tier, MAIS un même ICD couvre plusieurs tiers (l'E2E `1d`
vérifie qu'un ICD ∈ [84, 86] coexiste sur **5 tiers distincts** → l'ICD n'est pas fonction du tier) :

| Tier | n | ICD moyen | ICD min |
|---|---|---|---|
| brûlante | 119 | 92,0 | 80 |
| chaude | 1 032 | 91,9 | 60 |
| réserve foncière | 4 547 | 87,6 | 40 |
| à creuser | 83 680 | 87,2 | 5 |
| écartée | 342 285 | 79,2 | 5 |

→ **aucune brûlante/chaude sous 60** : une parcelle lacunaire ne paraît jamais aussi sûre qu'une
parcelle complète, sans que l'ICD ait touché le score.

### Où il apparaît
- **Fiche** (API `/parcels/{idu}` → bloc `icd`) : chip en tête si < 85 + bloc « Confiance données »
  dépliable listant **ce qui manque** (`captures/fiche-m9-panel.png`).
- **Exports** : colonnes CSV `icd` + `confiance_donnees` ; **PDF** mention (obligatoire + avertissement si < 60).
- **Stockage / backfill** : colonnes `icd smallint` + `icd_detail jsonb` (helper idempotent
  `models.ensure_icd_columns`) ; backfill lecture `scoring/icd.backfill_run` sur les runs existants, et
  **automatique** au prochain run v2 (`p_v2/pipeline.py`, best-effort, cloisonné).

---

## Lot 2 — Lien règlement PLU

Chaque zone affichée en fiche renvoie vers **la page/section exacte** du règlement PLU. La traçabilité
article/page vit dans les YAML calibrés (`config/plu_<commune>.yaml`, clés `*_src` + bloc `source`) —
`src/labuse/plu_reglement.py` la relaie **sans rien inventer** :

- **Commune outillée** (Saint-Paul, Saint-Denis) → document + URL + citations article/page. Quand la page
  imprimée est connue, on construit un **lien profond** `…pdf#page=N` (N = page imprimée +
  `offset_pdf_vs_imprimee`). Ex. zone `U1b` : 6 articles, deep-link `#page=20` (Art. 6, p.16 + offset 4).
- **Commune non outillée** → **repli propre** : lien Géoportail de l'Urbanisme + réf. `idurba` + note
  explicite. Jamais de page inventée.

Bloc fiche `reglement_plu` (API), rendu `ReglementPluBlock` (liens `data-plu-link`), disclaimer « le
règlement PLU fait foi… ». Fallback validé sur commune non calibrée (E2E `3a-3c`).

---

## Lot 3 — Signaler une erreur

Bouton **« Signaler une erreur »** sur la fiche → formulaire (type d'erreur, champ concerné, commentaire)
→ table **`signalements`** horodatée (schéma `captures/signalements-schema.txt`). **Aucune action
automatique sur les données** : c'est une file de **QA humaine** (utile aux faux positifs — piscines
90,7 %, futurs verrous). Endpoints : `POST /signalements`, `GET /signalements`, `GET /signalements/export.csv`
(BOM Excel). Statut initial `nouveau`. Persistance vérifiée en base par l'E2E (`4a/4b`) et via l'UI (`6.4/6.5`).

Colonnes : `id, parcelle_id, type_erreur, champ, commentaire, utilisateur, statut, created_at`.

---

## Lot 4 — Décision Mutabilité : FONDUE + RETIRÉE

### Constat
L'« outil Mutabilité » n'était **pas** un outil séparé de la nav mais un **mode d'affichage carte**
(bascule `Verdict / Mutabilité` dans l'en-tête, `Header.tsx`) qui **coloriait les parcelles par
`sdp_residuelle_m2`** — c.-à-d. exactement la donnée résiduelle du **bloc D** du modèle P.

### Avant / après

| | AVANT (mode carte « Mutabilité ») | APRÈS (indicateur fiche « Potentiel de transformation ») |
|---|---|---|
| Forme | dégradé de couleur sur toute la carte | indicateur **à la parcelle**, dans la fiche |
| Donnée | `sdp_residuelle_m2` (bloc D) | ratio **SDP consommée/autorisée** (`pct_potentiel`, bloc D) + `sdp_residuelle_m2` + `sous_densite` |
| Niveau | — (lecture visuelle seule) | **fort / modéré / faible / nul** + libellé |
| Surélévation | **absente** | **`surelevation_possible` + marge de hauteur** (BD TOPO × PLU) |
| Traçabilité | aucune | source affichée + confiance du potentiel bâti |

### Ce qui est couvert / ce qui aurait pu être perdu
Le mode carte ne montrait **que** `sdp_residuelle_m2`, entièrement couvert par le bloc D → **rien de
perdu** de ce mode. **Signal à préserver signalé AVANT retrait** (mandat 4.2) : la **surélévation**
(`surelevation_possible`, `hauteur_bati/hauteur_max`) n'est **pas** dans le seul ratio SDP — elle vient
de `parcel_residuel_bati`. Elle est donc **intégrée** au nouvel indicateur (et non perdue). Le *mutation
score* (`mutation.py`, étape opportunité) reste un métrique **distinct**, non fusionné (question
différente : « transformable ? » vs « sous-utilisé ? »).

### Retrait
Bascule carte supprimée de la nav (`Header.tsx`), avec nettoyage complet du mode `mutabilite`
(`MapView.tsx`, `Legend.tsx`, `store/useApp.ts`, `types.ts` — aucun code orphelin). Nouveau bloc
`potentiel_transformation` (API) + `TransformationBlock` (fiche). Vérifié : E2E `6.0` (0 bouton
« Mutabilité »), `5a/5b` (indicateur présent, alimenté par le ratio SDP), `6.3` (bloc visible).

---

## Lot 5 — Tests

- **E2E** `qa/e2e_m9_fiche.mjs` : **21/21 vert** (`captures/e2e-m9-output.txt`) — ICD affiché + exports,
  lien PLU + deep-link article/page, signalement persisté en base + UI, indicateur transformation, outil
  Mutabilité retiré, 0 erreur console.
- **Golden 32/32 PASS** (aucun champ golden touché — l'ICD est une colonne annexe).
- **Cohérence 3/3** (front SOURCE = `q_v5_m6b`, bundle reconstruit `npm run build`, tuiles mvt inchangées).
- **pytest 792 passed**, 14 skipped, **8 failed PRÉ-EXISTANTS** vérifiés à l'identique sur l'arbre pristine
  (`git stash`) : `test_backup`, `test_cascade` ×3, `test_ortho_detection`, `test_verdict_effectif` ×3 —
  tous des « relation … does not exist » de setup de la base de test (`parcel_terrain`, tables ortho),
  **sans lien avec M9**.

---

## Fichiers livrés (`reports/m9-fiche/`)
- `SYNTHESE-M9.md` (ce fichier)
- `captures/fiche-m9-panel.png`, `fiche-m9-entete.png`, `fiche-m9-blocs.png` — fiche enrichie
- `captures/signalements-schema.txt` — schéma table signalements
- `captures/icd-distribution.txt` — distribution ICD + croisement tiers
- `captures/e2e-m9-output.txt` — sortie E2E 21/21

## Code touché (résumé)
Backend : `models.py` (colonnes ICD + table signalements, helpers idempotents), `scoring/icd.py` (nouveau),
`scoring/p_v2/pipeline.py` (backfill auto), `plu_reglement.py` (nouveau), `api/app.py` (blocs fiche `icd`
/ `reglement_plu` / `potentiel_transformation`, endpoints signalements, colonnes CSV), `api/pdf_premium.py`
(mention ICD + transformation). Frontend : `lib/types.ts`, `lib/api.ts`, `components/fiche/Fiche.tsx`
(4 blocs), retrait mode Mutabilité (`Header.tsx`, `MapView.tsx`, `Legend.tsx`, `store/useApp.ts`).
