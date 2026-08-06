# M37 — BILAN (extinction du rail legacy + reliquats M33)

**Branche `m37-extinction-rail-legacy`** · base `main` 89baeaf1 · commits `[M37-Lot0.1]`,
`[M37-P0]`, `[M37-P1a/b/c]`, `[M37-P2]`. **Aucun changement de tier, aucune écriture sur le
run servi ou le cache scoring.** Golden **117/117** de bout en bout. Garde mécanique (addendum)
PASSE.

## Garde mécanique (addendum) — résultat

- **Dump exhaustif des vigilances AVANT/APRÈS, même script** (`qa/m37/dump_vigilances.py`,
  4 344 938 lignes de vigilance sur 431 632 parcelles, couche `declassement` + tout
  HARD_EXCLUDE/SOFT_FLAG, DEUX tables cascade).
- **SHA256 global identique** : `482da6f6848989b34aac7cbafcddc413079c5c2e1a9bd1b4bf186b1689e9abe9`
  (avant == après).
- **Diff des digests par parcelle : VIDE** (`diff` exit 0, 431 632 parcelles).
- → **0 vigilance perdue, modifiée ou inventée.** Confirmé aussi visuellement (capture 1 :
  AT2542 brûlante, vigilance « accès non identifié… servitude de passage à vérifier » intacte).

## Lot 0.1 — Mode B au k€ (point de formatage unique)

`compute_mode_b` sert `achat_max_libelle` (formaté k€ via `_eur`, le helper de l'export) —
POINT UNIQUE lu par fiche web + exports + assistant. `fmtEurCompact` retiré du front (il ne
basculait au k€ qu'au-delà de 10 k€). Vérifié : AW2362 → « ~181 k€ », BW0326 → « 7 k€ »
(capture 2).

## Lot 0.2 — Audit « Confiance et données » : c'est l'ICD, GARDÉ

Le tiroir sert `f.icd.score` — l'ICD (`scoring/icd.py`, 9 groupes nullables), PAS la
Complétude retirée M36. Distribution mesurée : **19 valeurs distinctes (5-100), médiane 90,
moyenne 80,4** (informatif, contraste avec les 3 valeurs de la Complétude). **Reco GARDER**
(remplaçant préservé par M36). Audit-only, rien implémenté.
⚠ **Note pour geste ultérieur** (le mandat le demande) : le libellé « Confiance données » +
tooltip « Complétude des couches… n'entre pas dans le score » existe (IcdBlockView), mais un
client pressé pourrait ne pas comprendre que 90 % = complétude des SOURCES, pas une note de
qualité. Un micro-libellé explicite serait utile — **non improvisé ici**, consigné.

## Diff vs cartographie M34-P0

M34-P0 cartographiait le chemin **fiche**. Éléments touchant encore `parcel_evaluations.status`
non listés là (tous NON servis comme verdict — vérifiés sur pièces, pas sur la parole des
agents) : `/map/parcels.geojson` fallback (mort pour le produit — le front envoie toujours
`?source` via `q()`), `POST /parcels/{idu}/evaluate` (admin, non appelé par le front),
writers CLI/batch, `division_or` (= dryrun étage0, hors cible), audit/demo (admin/démo).
**Aucune divergence servie.** Les 2 agents avaient cru la carte et POST evaluate « bloquants » ;
la lecture du helper `q()` et des callers a INFIRMÉ ces deux points.

## Plan d'extinction EXÉCUTÉ

**P1a — lecteurs coupés** (verdict = tier servi partout) :
- `/map/parcels.geojson` : fallback legacy SUPPRIMÉ ; défaut `source=Q_A_RUN_LABEL` (lu de
  `config/served_run.txt`) → un seul chemin v2.
- `assemblage.py` : voisin = tier servi (`parcel_p_score_v2`), comme voisinage.py (M34).
- `audit._cached` : cache-hit = éval propre existante ; `status` = tier si au run, None sinon.
- `demo.py` (4 lectures) : verdict/tri/QA re-sourcés sur tiers ; `attendu[]` des 8 parcelles
  démo aligné sur les tiers réels (factuel — **narration role/montre INCHANGÉE ; révision copy
  démo à faire, consignée**).
- tests re-sourcés (geojson v2-only, demo tiers, QA Saint-Paul tiers, audit cache préservé).

**P1b — writer gelé + colonne archivée** :
- `pipeline._persist` ne persiste plus `status` (le status reste calculé en mémoire pour
  l'audit/outcome). Vigilance (motif) → cascade_results INCHANGÉE.
- `ParcelEvaluation.status` retiré du modèle (l'ORM ne le sélectionne plus).
- **Migration idempotente `ensure_parcel_eval_status_archived`** (dans `create_all`) : RENAME
  `status` → `status_pre_m37` + DROP NOT NULL, si `status` existe et pas déjà archivé.
  Appliquée base live + base de test.

**P1c — matrice_statut** :
- **Sortie affichage** : chip « Statut matrice (historique) » (fiche) + mention « (matrice : X) »
  (TierBadge) RETIRÉS.
- **Bascule tiers** (comportement + payload, faite maintenant — zéro partenaire actif) :
  modules Outils (bailleur + gisement), moteurs, API partenaire `/api/v1/parcels` + profils.
  Étiquette partenaire VRAIE (« classement servi — tiers brûlante → à creuser »). Vérifié :
  bailleur → 200, statuts servis = tiers.

## Sort de chaque surface `matrice_statut` (arbitrages Vic appliqués)

| Surface | Décision | État |
|---|---|---|
| Chip « Statut matrice (historique) » fiche | SORTIE | fait |
| TierBadge « (matrice : X) » | SORTIE | fait |
| Modules Outils (bailleur, gisement) filtre+payload | BASCULE tiers | fait |
| Moteurs (radar/mutation) filtre+payload | BASCULE tiers | fait |
| API partenaire `/api/v1/parcels` + profils | BASCULE tiers + étiquette vraie | fait |
| Légende carte (repli sans run v2) | MAINTIEN, étiquette vraie « Classement historique » (M36) | inchangé |
| Tuiles MVT (`tiles.py`) | MAINTIEN — les tuiles portent `tier_v2` ; `matrice_statut` = méta interne, non servie comme verdict | inchangé |
| `matrice_statut` en base (dryrun_parcel_evaluations) | CONSERVÉE — axe Q×A du run servi, distinct du rail éteint | inchangé |
| `/stats?legacy=1` (deprecated) | MAINTIEN (déjà étiqueté deprecated) | inchangé |
| `events.py` digest (transitions matrice) | MAINTIEN (digest historique interne) — bascule tiers = geste ultérieur si Vic le veut | inchangé |

## Rollback (réversible, sans perte)

- **Code** : `git revert` des commits M37 (ou reset de la branche avant merge).
- **Colonne archivée** : `ALTER TABLE parcel_evaluations RENAME COLUMN status_pre_m37 TO status;`
  restaure la colonne (les valeurs pré-M37 sont INTACTES — archivage par renommage, aucune
  suppression). Puis remettre l'attribut `status` au modèle + la ligne `status=status` du writer.
- Aucune donnée détruite : le rail est éteint, pas effacé (geste de suppression physique =
  ultérieur, à froid, décision Vic).

## Vérifications

1. **Golden 117/117** après chaque phase (dernier passage code final, 0 incohérence base↔API).
2. **Re-mesure M34/M35 : 0 divergence** dans les deux sens (1 071 parcelles) ; ancres intactes.
3. **Garde mécanique vigilances : SHA identique + diff digests VIDE** (0 vigilance touchée).
4. Aucun tier modifié, aucune écriture run/cache scoring. Écritures DB hors scoring, tracées :
   1 renommage de colonne (archivage).
5. Suite pytest : **1 307 verts** (verrous re-sourcés : geojson v2, demo tiers, QA Saint-Paul,
   audit cache, R3 desambiguisation) ; 5 échecs PRÉ-EXISTANTS env (residuel ×4, au_ouverture),
   consignés depuis M34.
6. **Captures** `qa/m37/screens/` : 1 brûlante AT2542 (vigilance accès **intacte** post-
   extinction) · 2 saturée AW2362 (mode B « ~181 k€ ») · 3 nue AP1610 (témoin).

## Reliquats consignés

- **Révision copy démo** : la narration des 8 parcelles démo (role/montre) décrit encore des
  statuts legacy (« opportunité vitrine », « faux positif parking »), alors que `attendu[]` est
  désormais le tier servi (BK0023 = a_creuser, BP0571 = ecartee). Réécriture du storytelling =
  geste produit ultérieur (non improvisé ici).
- **Micro-libellé ICD** (Lot 0.2) : expliciter que « Confiance données » = complétude des
  sources, pas une note de qualité.
- **events.py digest** : transitions encore sur matrice_statut — bascule tiers si Vic le veut.
- **Suppression physique** de `status_pre_m37` : geste ultérieur Vic, à froid.
