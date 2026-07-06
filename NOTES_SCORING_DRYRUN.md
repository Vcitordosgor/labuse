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

## Reste
- Étape 2 (accessibilité : BODACC/INPI/DPE + bascule événementielle), étape 3 (matrice Q×A).
- Observations baseline différées à l'étape 3 : plafond opportunité ~81 (bonus bas), statut
  « opportunite » rare (règle sévère).
