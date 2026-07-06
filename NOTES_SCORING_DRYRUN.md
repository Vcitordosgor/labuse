# NOTES — Dry-run scoring étages 1+2 (branche scoring/dryrun-etages-1-2)

Journal du chantier. À la FIN (validé), ces décisions deviendront `docs/product/SCHEMA_SCORING_LABUSE.md`
(la spec suivra le code, dans le repo). Périmètre : Saint-Paul (97415). Rien branché au live.

## Mécanisme (validé STOP 0)
- Tables PARALLÈLES `dryrun_parcel_evaluations` + `dryrun_cascade_results` par `run_label`.
  Isolées : le compute écrit là, JAMAIS sur parcel_evaluations/cascade_results live.
- `evaluate_parcels(dryrun_label=…)` → `_persist_dryrun` (compute inchangé). Commandes CLI
  `dryrun-evaluate` (chunké/résumable/progression) + `dryrun-report`.
- Traçabilité : `weight_applied` (base + Σ = score, testé) + `source_table`/`source_id` (cliquable)
  dans `verdict.extra` — installé pour TOUTES les nouvelles couches.
- IA = narratif only : `_apply_ai` n'injecte plus `ai_adjustment` (=0 partout).

## Décision ABF → UNKNOWN (validée)
Couche `abf` config-driven (`as_unknown: true`) → verdict UNKNOWN : impacte la complétude, 0 point
d'opportunité, flag « abords MH ~500 m, covisibilité à instruire » affiché. Réversible via config.

## Baseline 97415 (validée)
51 129 parcelles. Statuts : faux_positif_probable 24 396 (48 %), a_creuser 14 080 (28 %),
exclue 11 917 (23 %), opportunite 736 (1,4 %). Opportunité max 81, médiane 0 (masse exclue),
complétude médiane 74. UNKNOWN-ABF : 7 896. Traçabilité base+Σ=score : 14 802/14 816 (14 clampés).

Décomposition des 24 396 faux_positif_probable (validée « structurel, RAS ») : bâti 15 643 (déjà
bâti), surface 3 972 (micro-parcelles), zonage A/N 5 789, marginal (pente/osm/prescription).

## 📌 DETTE NOTÉE (à traiter plus tard, PAS maintenant)
- **Labellisation zone A/N** : les 5 789 parcelles en Zone A/N PLU (inconstructible réel) sont
  étiquetées `faux_positif_probable` car la couche `zonage_plu_gpu` émet son HARD_EXCLUDE avec le
  kind par défaut `faux_positif`. La règle est correcte ; c'est l'ÉTIQUETTE qui trompe → passer à
  kind `exclue` pour A/N. Fix de labellisation, hors étape 1/2.

## Étape 1 — QUALITÉ (décisions validées, implémentées en dry-run)
Couches phase 1 (config `cascade_rules.yaml` + `opportunity_weights.yaml`), module `layers/etage1.py` :
- **friche** (Cartofriches) : POSITIVE, bonus_key `friche` +8 « avec projet » / +5 « sans projet ».
- **sol_pollue** / **cavite** : SOFT_FLAG `faible` (le FLAG prime, malus léger) — flag « étude à
  prévoir » qui SURVIT à la fiche, `source_table/source_id` remplis.
- **icpe** : SOFT_FLAG GRADUÉ par distance — ≤50 m fort · ≤150 moyen · ≤300 faible.
- **mvt** : SOFT_FLAG `info` (multiplicateur ×0) → flag affiché, **0 point** (aléa déjà compté en PPR).
- **amenites** : POSITIVE, bonus_key `amenites` plafond **11**. Bandes (contexte 974 tout-voiture) :
  plein ≤500 m · 0.5 en 500–1200 m · 0 au-delà (école/commerce/santé) ; tcsp 300/800 m.
  Pondérations : école 0.30 + commerce 0.30 + santé 0.20 + tcsp 0.20.
- Proximité batch (ctx) : plus proche POI ponctuel + son id ; `parcel_amenites` lu en batch.

## Étape 1 FIGÉE (aménités plafond 7)
Vic 06/07 : à 11, aménités quasi-universel (+6,8 moyen sur 14k) → baissé à 7. Delta : 455 « inflations
aménités seules » redescendent opportunite→a_creuser ; +803 net vs baseline (promus par fondamentaux,
pas par aménités seul) ; plafond 91→87. Comportement validé, figé.

## Étape 2 — ACCESSIBILITÉ (implémentée en dry-run, layers/etage2.py)
- **age_dirigeant** (INPI, v_foncier_propension_vendre) : POINTS, courbe 55/65/75/85 → 4/8/12/14.
  ⚠ Âge ABSENT (gigogne plafonnée, non-diffusibles) → **UNKNOWN** (impacte la complétude comme ABF),
  JAMAIS un malus (exigence Vic). Âge <18 → UNKNOWN (fiche incohérente).
- **bodacc** (v_foncier_sous_pression) : FLAG 0 point (severity info ×0). **Machine à états sur les
  LIBELLÉS RÉELS** (SELECT DISTINCT validé, listes explicites en config) : rouge (ouverture/conversion/
  extension/résolution-LJ) · orange (plans) · gris (clôtures) · neutre (reste). Seul **rouge pose
  evenement='rouge'** → bascule « chaude » (étape 3).
- **dpe_passoire** (v_passoire_thermique) : FLAG 0 point « pression réglementaire datée » (gel loyers
  07/2024, G interdit 2028, F 2034). Pas de bascule chaude (réservée BODACC ouverte).
- Bascule : colonne `dryrun_cascade_results.evenement`.

### Arbitrages BODACC (validés)
- « Liste des créances… LJ » (9) → NEUTRE. **Orphelins vérifiés = 0/9** : ces 9 SIREN ont TOUS déjà
  un jugement rouge en base → aucun signal perdu, neutre DÉFINITIF.
- `type_procedure` vide (8) → neutre.

## 📌 DETTE D'INGESTION NOTÉE (à corriger à la SOURCE un jour, pas seulement mappée ici)
- **Mojibake dans `bodacc_procedures.type_procedure`** : double-encodage UTF-8 (ex.
  `Jugement arrÃªtant le plan de sauvegarde`, `DÃ©pÃ´t de l'Ã©tat des crÃ©ances`). Normalisé au mapping
  BODACC (config `mojibake`), mais la vraie correction est à la ré-ingestion BODACC (décodage UTF-8).

## 📌 DPE passoire — N/A foncier nu (ASSUMÉ, validé Vic)
Effet de bord vérifié : une passoire (maison F/G) est BÂTIE → exclue à l'étage 0 (couche `bati`) →
n'atteint jamais la phase 2 → le flag DPE ne se déclenche JAMAIS sur une parcelle scorée
(Saint-Paul : 2 passoires, 2/2 exclues étage 0). **N/A pour le foncier nu.** Câblage GARDÉ (coût
nul) — réservé à un FUTUR produit « reconversion / démolition du bâti ». Pas un bug, on n'y touche plus.

## Reste
- Étape 3 (matrice Q×A + bascule chaude sur evenement='rouge').
- Observations baseline différées à l'étape 3 : plafond opportunité ~81 (bonus bas), statut
  « opportunite » rare (règle sévère).

---

# PHASE 1 v2 — SOCLE SDP + GARDES G1/G2 (refonte SCORING_PREMIUM v2, branche refonte/scoring-v2-phase1-gardes)

Refonte fondée sur l'ÉCONOMIE (spec v2) : la constructibilité résiduelle devient le facteur Q
dominant, et 5 gardes anti-faux-positifs renforcent l'étage 0. Phase 1 câble G5/G1/G2 ; G3/G4 = dette.

## G5 — socle SDP résiduelle (couche `residuel_socle`, étage 1/Q, spec §4.1)
Barème SIGNÉ −25..+30 par bande de `parcel_residuel.sdp_residuelle_m2` (<100:−25 · 100–300:−10 ·
300–800:+5 · 800–2000:+15 · 2000–5000:+25 · >5000:+30). Poids direct via `scored()` (nouveau
mécanisme `Verdict.weight_override` : les bandes ±25 dépassent le multiplicateur de sévérité,
plafonné à ±15). **NON CALCULÉ (hors couverture parcel_residuel, ~61 %) = UNKNOWN, JAMAIS −25**
(règle absolue Vic) : l'absence de donnée n'est pas une absence de droits → impacte la complétude.
En Phase 1 le −25 fait SORTIR les micro-lots de « chaude » (vers a_creuser) ; l'effondrement complet
en « écartée » viendra en Phase 2 (retrait L2 des +16 zonage/surface encore présents).
- **Garde-fou d'écoulement (§4.1, SDP>2000 en secteur peu liquide → flag « profondeur de marché à
  vérifier ») : différé Phase 2** — dépend des quintiles de liquidité DVF (couche marché Phase 2).

## G1 — foncier public non acquérable (couche `foncier_public`, étage 0, HARD_EXCLUDE)
Classification DGFiP `parcelle_personne_morale.groupe`. Groupes EXCLUS = {1 État, 2 Région,
3 Département, 4 Commune, 9 Établissements publics}. Motif nominatif « Propriété publique (X) —
non acquérable ».
- **HLM (groupe 5) et SEM (groupe 6) = MARCHANDS, préservés VOLONTAIREMENT** — ce sont des
  contreparties acquérables (bailleurs sociaux / opérateurs mixtes qui cèdent et développent) et le
  futur segment « mode bailleur » de la roadmap. Les exclure tuerait 70 « chaudes » légitimes à
  Saint-Paul (21 HLM + 49 SEM). Le « non-marchand » de la spec est donc porteur.

## G2 — emprise linéaire (couche `emprise_lineaire`, étage 0, HARD_EXCLUDE)
`ST_OrientedEnvelope` : largeur < 8 m ET ratio L/l > 8 (CUMULÉS). La jambe « largeur » protège les
drapeaux (corps large + lanière d'accès). Échantillon Saint-Paul validé : 0/3831 drapeaux flaggés,
2/1183 flaggées à SDP≥300 (ne retire quasi jamais du constructible). Conservateur (17 % des rues
réelles — les avenues larges relèvent de G1/G5).

## G3 / G4 — DETTE PHASE 1bis (NON câblés — inmesurables sans ingestion dédiée)
On ne donne AUCUN poids à ce qu'on ne peut pas mesurer.
- **G3 équipement en usage** : extension de la couche OSM faux-positifs existante à
  `leisure=pitch/stadium/sports_centre/park/playground`, `amenity=parking`,
  `landuse=cemetery/railway/military`. Même source (Overpass), requête élargie — petite ingestion.
- **G4 emprise routière** : la couche `voirie` est en `LineString` (aire = 0) → impossible de
  mesurer un recouvrement surfacique. Nécessite les SURFACES routières BD TOPO (troncon → polygone
  de chaussée). Ingestion séparée.

## Mécanisme `weight_override` (base.py / opportunity.py)
Nouveau champ `Verdict.weight_override` + helper `scored()` : contribution SIGNÉE directe au score,
court-circuite sévérité/bonus. Rétro-compatible (défaut None = comportement inchangé ; aucune couche
live ne l'émet). Fondation aussi pour la pente graduée Phase 2 (−16/−10/−4, idem inexprimables par
sévérité). Défensif : un poids négatif porte Severity.INFO (×0) — si l'override était ignoré, 0 point
plutôt qu'un malus fantôme.

---

# PHASE 2 v2 — Q ÉCONOMIQUE (run q_v2)

Refonte de Q sur l'économie. Résumé (barèmes effectifs : cf. docs/product/SCHEMA_SCORING_LABUSE.md).
- **L2 supprimé** : `zonage_u_au=0`, `surface_utile=0` (subsumés par le socle SDP). Hard-excludes zonage/micro conservés.
- **Marché → Q, A pur vendeur** : `dvf` + `sitadel` retirés de `a_layers`. A = proprietaire/age/bodacc/dpe.
- **Prix = quintile ÎLE du €/m² BÂTI** (prix de sortie promoteur), bornes `[1719,2307,2917,3968]` data-issues.
  DÉCISION : base bâti retenue (option 1 de la reco) — le €/m² terrain (bornes 262-893) mettait 100 % en Q1
  (signal mort) ; les bornes citées 976/1553/2249/3407 ne se reproduisaient d'aucune base. Retunable en config.
- **Vue mer** +8/+4 · **assemblage** +6 (ST_DWithin 1 m, garde-fou détention ≤10) · **OCS artificialisé** +4
  (cumul plafonné à +10 avec la vue mer) · **pente graduée** 0/−4/−10/−16 · **flag écoulement** SDP>2000 + peu liquide.
- Résultat : chaude 212→**83** (déflation assumée, 1,6 ‰). Invariants au vert (AC0253 override, 31 entrantes premium).

## Cumul vue mer + OCS (documenté, exigence Vic)
Deux signaux RÉELS et DISTINCTS (prime de prix de sortie ≠ absence de dette ZAN) mais **corrélés
géographiquement** (le littoral artificialisé cumule les deux). Cumul plafonné à **+10** sur la paire
(`ocs_ge.pair_cap_points`) : la vue mer est prioritaire (+8/+4), l'OCS complète jusqu'à 10. Évite de
sur-récompenser une double-prime de localisation qui ne double pas la valeur foncière.

---

# 📌 DETTES DU CHANTIER v2 (à traiter en usage / chantiers suivants)

1. **G3 / G4 non câblés (ingestion Phase 1bis)** — on ne pondère pas ce qu'on ne peut pas mesurer :
   - **G3 équipement en usage** : extension couche OSM faux-positifs → `leisure=pitch/stadium/sports_centre/
     park/playground`, `amenity=parking`, `landuse=cemetery/railway/military` (même source Overpass).
   - **G4 emprise routière** : la couche `voirie` est en LineString (aire nulle) → besoin des SURFACES
     routières BD TOPO (troncon → polygone de chaussée). Sans elles, G4 reste N/A.

2. **Couverture `parcel_residuel` ≈ 61 % (37 % UNKNOWN socle)** — chantier data PRIORITAIRE post-calibrage.
   14 % des chaudes premium ont une SDP inconnue : étendre le calcul du résiduel dé-risque directement le
   funnel. Comprendre le POURQUOI des 39 % non calculés (parcelles sans PLU calibré ? géométries dégénérées ?)
   fait partie du chantier — pas maintenant.

3. **« Loyers orphelins »** *(interprétation à confirmer par Vic)* — passoires thermiques DPE F/G (gel des
   loyers depuis 07/2024) non rattachées à une parcelle (géocodage BAN imparfait à 974). Le flag
   `dpe_passoire` ne se déclenche que sur les DPE géocodés ; les orphelins sont perdus. À réconcilier à la
   ré-ingestion DPE. *(Si Vic visait une autre dette « loyers », corriger cette entrée.)*

4. **Mojibake BODACC à la source** — `bodacc_procedures.type_procedure` en double-encodage UTF-8
   (`Jugement arrÃªtant…`). Normalisé au mapping (config `mojibake`) mais la vraie correction est au
   décodage à la ré-ingestion BODACC.
