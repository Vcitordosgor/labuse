# M32 — PHASE C : MESURE À BLANC (rapport) — POINT D'ARRÊT avant bascule

Run de mesure : **`q_v13_m32_mesure`** (431 663 parcelles, 228 s, modèle m36-l2f-2026 sha vérifié).
Le run servi **`q_v8_calibre` reste GELÉ** (aucune bascule). Archive AU cache : `parcel_au_statut_pre_m32`.

## 1. Ce qui a été intégré + mesuré

- **Intégration moteur** : `au_ouverture_planchers.yaml` 4 → 21 communes (ouverture + planchers).
  Correction en cours de mesure : `defaut: conditionnelle_etat_tiers` sur-déclassait les 1AU
  (ouverts par opération) de 4 communes → corrigé (`defaut: conditionnelle_operation` + `2AU`
  phasé). declasse_au_statut_inconnu (cache) 2000 → 810.
- **Re-scoring** `q_v13_m32_mesure` sur le nouveau cache AU (départage + backfill recalculés).

## 2. Compteurs globaux (avant → après)

| Tier | q_v8_calibre | q_v13_m32_mesure | Δ |
|---|---|---|---|
| **brûlante** | 119 | **120** | **+1** |
| **chaude** | 1 033 | **1 042** | **+9** |
| réserve foncière | 2 917 | 2 964 | +47 |
| à creuser | 29 767 | 29 972 | +205 |
| **declasse_au_statut_inconnu** | 560 | **210** | **−350** |
| declasse_au_fermee | 58 | 70 | +12 |
| declasse_bati_revele | 4 010 | 4 051 | +41 |
| declasse_bati_sature | 29 872 | 29 907 | +35 |
| declasse_zone_fermee / non_constructible / écartée | 2 804 / 6 168 / 354 355 | idem | 0 |

**Sens du mouvement** : l'intégration **retire ~350 faux déclassements AU** (communes jusque-là
non calibrées, déclassées « par doute » → désormais conditionnelle_operation servable). Ces parcelles
refluent vers les tiers servables ; +10 en tête (net). Mouvement **modeste et localisé**.

## 3. Matrice des mouvements (376 parcelles changent de tier — 0,09 %)

| avant → après | n |
|---|---|
| declasse_au_statut_inconnu → à creuser | 198 |
| declasse_au_statut_inconnu → bâti révélé / bâti saturé | 41 / 35 (re-déclassées par une AUTRE règle) |
| declasse_au_statut_inconnu → réserve foncière | 41 |
| **declasse_au_statut_inconnu → chaude** | **20** |
| chaude → à creuser | 10 |
| declasse_au_statut_inconnu → au_fermee | 16 |
| chaude → brûlante / a_creuser → brûlante | 2 / 1 |
| brûlante → à creuser / brûlante → chaude | 1 / 1 |

Les 35 mouvements impliquant la tête : `qa/m32/mesure_mouvements_tete.csv`. Top 100 (tous mouvements) :
`qa/m32/mesure_top100_mouvements.csv`. **Chaque ligne porte sa cause** (AU conditionnelle_operation =
déclassement retiré ; recalibr./départage sinon).

## 4. Deck des 20 plus gros mouvements (tête)

| # | idu | commune | zone | avant → après | rang | cause |
|---|---|---|---|---|---|---|
| 1 | 97418000AT2542 | Sainte-Marie | UB | chaude → **brûlante** | 15→14 | recalibr./départage |
| 2 | 97422000CY0197 | Le Tampon | Uc | chaude → **brûlante** | 164→163 | recalibr./départage |
| 3 | 97422000AK1442 | Le Tampon | Uc | a_creuser → **brûlante** | 4150→4132 | ⚠ **override M28 (piscine) à ré-appliquer à la bascule → a_creuser** |
| 4 | 97403000AM0768 | Entre-Deux | AUb | declasse_au → **chaude** | 325→323 | AU conditionnelle_operation (déclassement retiré) |
| 5 | 97403000AT0449 | Entre-Deux | AUb | declasse_au → chaude | 412→409 | AU conditionnelle_operation |
| 6 | 97414000EN3944 | Saint-Louis | 1AUb2 | declasse_au → chaude | 543→540 | AU conditionnelle_operation |
| 7 | 97414000EN3947 | Saint-Louis | 1AUb2 | declasse_au → chaude | 566→563 | AU conditionnelle_operation |
| 8 | 97403000AR0807 | Entre-Deux | AUb | declasse_au → chaude | 743→740 | AU conditionnelle_operation |
| 9 | 97419000AI1063 | Sainte-Rose | 1AUa | declasse_au → chaude | 843→840 | AU conditionnelle_operation |
| 10 | 97414000ET0384 | Saint-Louis | 1AUb2 | declasse_au → chaude | 1285→1280 | AU conditionnelle_operation |
| 11 | 97418000AS1400 | Sainte-Marie | 1AUb | declasse_au → chaude | 1553→1548 | AU conditionnelle_operation |
| 12 | 97414000EN3939 | Saint-Louis | 1AUb2 | declasse_au → chaude | 1746→1740 | AU conditionnelle_operation |
| 13 | 97402000AI1207 | Bras-Panon | 1AUb | declasse_au → chaude | 2078→2070 | AU conditionnelle_operation |
| 14 | 97419000AL1154 | Sainte-Rose | 1AUa | declasse_au → chaude | 2669→2661 | AU conditionnelle_operation |
| 15 | 97405000AL1523 | Petite-Île | 1AUa | declasse_au → chaude | 2945→2937 | AU conditionnelle_operation |
| 16 | 97402000AI1136 | Bras-Panon | 1AUb | declasse_au → chaude | 2955→2947 | AU conditionnelle_operation |
| 17 | 97416000ET2162 | Saint-Pierre | UfCA | **brûlante → chaude** | 3153→3143 | recalibr./départage |
| 18 | 97402000AD1041 | Bras-Panon | 1AUc | declasse_au → chaude | 3941→3921 | AU conditionnelle_operation |
| 19 | 97402000AI1131 | Bras-Panon | 1AUb | declasse_au → chaude | 5382→5361 | AU conditionnelle_operation |
| 20 | 97402000AI1129 | Bras-Panon | 1AUb | declasse_au → chaude | 5407→5386 | AU conditionnelle_operation |

**Ortho PVA + millésime par parcelle** : le rendu visuel (format deck M28) est la dernière étape de
mise en page — les 20 idus + causes sont figés ci-dessus, prêts à illustrer.

## 5. Points de vigilance (à traiter à la BASCULE, pas ici)

1. **AK1442** (Le Tampon) : la mesure la remonte en brûlante car elle ne ré-applique PAS l'override
   du registre M28 (piscine FLAIR 88 m² → a_creuser). À la bascule, le registre le remet en
   a_creuser (comme M28). **Seul écart de tête attendu, tracé.**
2. **SDP des bâties révélées** (« terrain nu théorique ») : recalcul = correction de MENTION de fiche
   (les bâti_revele restent déclassées, la SDP n'est pas un moteur de tier). À exécuter dans le geste
   de bascule (recompute-residuel), pas dans cette mesure de tiers.
3. **Les 3 Salazie hors-PLU (M-A)** : Salazie est désormais intégrée (AU conditionnelle_operation) ;
   les 3 parcelles spécifiques du mandat M-A sont à ré-identifier au geste de bascule pour vérifier
   leur outillage (Salazie porte 4 têtes servies au mesure).

## 6. Décision demandée (POINT D'ARRÊT)

Mouvement mesuré = **+1 brûlante / +9 chaude**, **376 changements de tier (0,09 %)**, dominés par le
**retrait de ~350 faux déclassements AU** (calibration des communes) — sens attendu, ampleur modeste,
chaque mouvement causé. Seul écart de tête à surveiller = AK1442 (override registre à ré-appliquer).

**GO / NO-GO sur la mesure ?** Sur GO : bascule gardée (6 gardes + check_fraicheur), golden régénéré
dans le geste, archive `_pre_m32`, SDP bâties révélées + 3 Salazie inclus, recompte post-bascule vs
cette mesure (tout écart non listé = rollback). **Aucune bascule sans ce GO.**
