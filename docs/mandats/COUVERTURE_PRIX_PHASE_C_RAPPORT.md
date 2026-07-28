# RAPPORT — Mandat couverture prix, PHASE C : application du repli île (Fable)

**Exécuté le 28/07/2026** (branche `feat/couverture-prix-repli-ile`, base `main` APPLIQUÉ).
**Fable ne merge jamais — Vic merge en `--no-ff`.** GO Vic après acceptation de la vérification
d'artefact (rien ne bouge : back-test restreint frais 91 %, footprint nul en communes couvertes).

## 0 · Ce qui a été appliqué

Repli **île 4 375 €/m² (NON indexée)** en queue de préséance, couverture **5 → 16 communes**, avec
étiquetage à **4 niveaux de confiance**. L'estimateur île est validé sous tous les angles (ratio,
EPCI, temporel, hédonique tous mesurés et écartés — phase A). L'indexation a été mesurée puis
**rejetée par E3** (elle sur-évaluait) : on sert le 4 375 non indexé, conservateur.

## 1 · Séquence stricte (identique aux mandats du 28/07)

1. **Golden 116/116 avant** + tiers relevés (120 / 1031 / 3587 / 72980 / 353945).
2. **Instrument** (`dvf_prix_neuf.py`) : ligne `('__ILE__','ile')` = médiane MARCHÉ île (315 ventes
   d'appartements neufs hors bailleurs sociaux, non indexée) ajoutée au build. `resolve_prix_neuf_marche`
   — **préséance** : override bassin sourcé > dvf secteur local > dvf commune local > **REPLI ÎLE**
   (communes de marché sans local) > **NON CALCULABLE** (social-dominantes seulement). Le repli île
   **n'écrase jamais un prix local** et **n'atteint jamais une commune social-dominante**.
3. **Purge de tout socle résiduel + anti-réinjection** : le socle 4900 est déjà purgé (application
   précédente, sur main) ; **phase C n'introduit AUCUN nouveau socle** (l'île est une ligne CALCULÉE
   au build, pas une valeur semée dans `bilan_params`) → rien à réinjecter au boot.
4. **Étiquetage 4 niveaux** (`niveau_prix_label`, jamais de fausse précision) :
   - « Estimé — médiane locale, N ventes » → **5 communes** (Saint-Denis, Saint-Pierre, Saint-Paul,
     Saint-Leu, Le Tampon).
   - « Estimé — estimation île, ± 12 %, validée sur cette commune » → **9 communes** (L'Étang-Salé,
     La Possession, Saint-Benoît, Saint-Louis, Sainte-Marie, Sainte-Suzanne, Trois-Bassins,
     Les Avirons, Saint-André).
   - « Estimé — estimation île, aucune opération de marché observée sur cette commune » →
     **Sainte-Rose, Salazie**.
   - « Non calculable — collectif majoritairement social ou aidé » → **8 communes**.
5. **Golden 116/116 après** + **tiers au bit près** (aucun tier bougé). Le golden ne couvre aucun
   champ charge/marge — son PASS garantit cascade/tiers/zonages/ancres.
6. **Back-test sur le chemin de production** (`resolve_prix_neuf_marche`, PC 2015+, promotion marché
   ≥ 10 lgt) : **TOTAL 92 %, LOCAL 92 %, ÎLE 94 %** (référence 89-91). **E3 contrôle** (communes île) :
   **0/10 sur-évaluation** (ratio min 1,17) — le mode d'échec du 4900 est absent.
7. **Aucun tier n'a bougé d'un bit.**

## 2 · Portée servie

- **Cœur (fiche)** : `faisabilite/db.py` sert le prix résolu + `prix_neuf_label` + `prix_neuf_repli_ile`
  dans le payload. Vérifié en direct : Saint-Denis « médiane locale, 77 ventes » ; Sainte-Marie /
  L'Étang-Salé « estimation île validée » (charge servie) ; Salazie « aucune opération observée » ;
  Le Port « non calculable — majoritairement social ou aidé ».
- **score_e (marge)** : étendu au repli île (CTE `neuf_ile` + niveaux) → **estimables 29 353 → 49 636**
  (16 communes). Répartition : commune 28 724, secteur 629, ile_validee 18 965, ile_sans_operation
  1 318 ; social-dominantes + parcelles sans terrain/SDP en non-estimable.

## 3 · Contrôle de sortie — la leçon gravée (ajout Vic)

**Une purge de valeur en base n'est acquise que lorsque le correctif de seed qui l'empêche de
revenir est mergé sur `main`.** Tant que le code d'application vit sur une branche, la base est
désynchronisée et le prochain redémarrage annule la purge (piège du 2100 et du 4900). Contrôle
exécuté en sortie de phase C : **purge socle 4900 confirmée présente sur `main`** (`models.py`
`ensure_bilan_params`) et **socle absent du seed sur `main`** → purge acquise. Phase C n'ajoute
aucun socle. Verrou `test_boot_purge_socle_4900_idempotente` protège la purge d'un retrait silencieux.

## 4 · Les 8 communes social-dominantes ne sont pas un échec permanent (consigne Vic)

« Non calculable » sur Le Port, Entre-Deux, Saint-Philippe, Petite-Île, Cilaos, Bras-Panon,
Saint-Joseph, La Plaine veut dire **« pas de charge de MARCHÉ », PAS « pas de réponse »**. Le
**mode D (opération sociale)** de la spec multi-modes leur répondra — équilibre par subventions +
LLS/LLTS, pas par un prix de sortie de marché. Le commentaire de `motif_non_calculable` le grave.

## 5 · Tests

3 verrous de wording mis à jour vers la nouvelle vérité (repli, niveau_label, banquier) + verrou
`test_repli_ile_preseance_et_etiquettes` ajouté (partition exhaustive et disjointe des 24 communes
en 4 niveaux + étiquettes au mot près + le repli île ne touche jamais une social-dominante).
**95 tests verts** sur le périmètre.

## Artefacts

`/tmp/phaseC_backtest.py` (back-test production + E3, LECTURE SEULE). Golden 116/116 + tiers au bit
près (`/tmp/phaseC_tiers_avant.txt` = `/tmp/phaseC_tiers_apres.txt`). Branche non mergée — revue Vic.
