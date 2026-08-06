# M39 — BILAN (signaux négatifs : piscine surfacique, solde dette #13)

**Branche `m39-signaux-negatifs`** · base `main` a2a28031 · commits atomiques `[M39-Px]`.
**AUCUNE bascule, AUCUN tier modifié, AUCUN merge.** La couche est construite, exposée en fiche
(informatif) et mesurée à blanc ; le geste de bascule est préparé et testé à blanc, JAMAIS exécuté.

---

## Le fil (constat P0 → arbitrages Vic → phases 1-2)

Dette #13 : le signal « piscine récente » était porté à la main au registre pour 2 parcelles
(AK1442, AL1154). Objectif : en faire une **règle produit** (couche surfacique + seuil), pour
écarter les fausses chaudes — une piscine = usage investi → probabilité de vente en baisse →
épargner au client une visite pour rien (la boussole appliquée au terrain).

Le **constat P0** (voir `M39_P0_CONSTAT.md`), vérifié sur pièces, a cassé une présomption du
mandat et Vic l'a validé :
- **La couche existe et est SURFACIQUE** : 19 899 détections piscine (polygones + surface + confiance
  + juge FLAIR + probe), **8 299 parcelles matérialisées** à **90,7 %** de précision.
- **Datation « récente » INFABRICABLE** : un seul millésime ortho en base (**2025**). Pas de N-1.
- **AK1442/AL1154 ne sont PAS dans la couche matérialisée** : leur « FLAIR 88 m² / 0,888 » du
  registre est en réalité la **confiance colorimétrique V0** + la surface ; `juge_flair` NULL (FLAIR
  gaté par le probe, probe≈0 → le classifieur produit conteste). Retenues à l'œil par Vic, hors
  couche automatique.

**Arbitrages Vic** : **A1** (signal « présente 2025 » non daté, jamais « récente ») · **B** (bande
**[15 ; 60] m²**) · **C1** (règle sur la couche matérialisée seule ; les seeds RESTENT au registre —
deux mécanismes, deux niveaux de preuve, zéro recouvrement ; **C2** = dette nommée non exécutée ;
**C3** V0-seul enterré).

---

## PHASE 1 — Couche & règle

### P1.1 · Couche datée (conventions millésime M32) — commit `[M39-P1]`
Source amont **« BD ORTHO 20 cm (IGN) »** enregistrée dans `data_sources` (l'âge de l'image = l'âge
du signal) : `source_millesime = « BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %) »`,
`source_horizon_at = 2025-01-01` (année du millésime — prise de vue non publiée, jamais inventée ;
PVA IGN vols 21/07–02/08/2025). Entrée `ortho_piscine` dans `fraicheur.SOURCES` ; cadence
pluriannuelle **volontairement non bornée** (comme `gpu_plu`) → `check_fraicheur` **ne l'alarme
pas** (un signal à 3-4 ans n'est pas un retard). `scripts/m39_register_source.py` (surgical,
idempotent, écriture catalogue **hors scoring**). Vérifié : `check_fraicheur` = 0 retard ortho.

### P1.2 · Règle produit en config — commit `[M39-P1]`
`config/calibrage/piscine_signal.yaml` (jamais en dur, même philosophie que
`au_ouverture_planchers.yaml`) : bande **[15 ; 60] m²**, bornes **nommées et justifiées par les faux
positifs mesurés** en commentaire (sous 15 : **355 FP / 190 ok** ; au-dessus 60 : **19 FP / 14 ok**).
Périmètre C1 (`exige_materialisee: true`), tiers source `[brulante, chaude]`, cible `a_creuser`,
motif client famille M35 (« détectée sur imagerie aérienne 2025 », **jamais « récente »**). Point de
calcul unique : `src/labuse/faisabilite/piscine_signal.py` (pur, lu par la fiche ET la bascule).
Doctrine AUDIT4 train 5 respectée : **une règle, pas un poids** de modèle.

### P1.3 · Registre — généalogie, motif client intact — commit `[M39-P1]`
Note de généalogie ajoutée au **motif interne** des seeds AK1442/AL1154 (« FLAIR » = confiance
colorimétrique V0, juge FLAIR non calculé/probe-gaté ; retenue sur revue visuelle Vic, hors couche
matérialisée → hors règle générique ; bande probe-ratée = dette C2). **`motif_client` INCHANGÉ**
(M35 Lot B : `verdict_servi` ne lit que `motif_client` — la note n'est jamais servie).
`scripts/m39_registre_genealogie.py`, idempotent. Écriture registre **hors scoring**.

---

## PHASE 2 — Fiche (informatif) + mesure à blanc

### P2.1 · Vigilance fiche — commit `[M39-P2]`
Sur un tier haut portant une piscine matérialisée en bande, la fiche (`resume`) ajoute une
**VIGILANCE informative** : *« Piscine détectée sur imagerie aérienne 2025 — usage du terrain à
vérifier. Détection ortho IGN 2025, fiabilité ~90,7 % (statistique, non contractuelle). »* Étiquette
**Sourcé**, « détectée » **jamais « présente certifiée »**, jamais « récente ». N'affecte NI tier NI
verdict. Assemblage **read-time** (`resume._vigilance`, jamais un insert cascade) → **SHA256
vigilances M37 inchangé par construction**. Vérifié bout-en-bout : présente en fiche, one-pager ET
markdown (repris dans les exports).

### P2.2 · Mesure à blanc — commit `[M39-P2]`
**Compte exact APRÈS seuil [15;60] : 34 déclassements** (2 brûlante + 32 chaude), 9 communes.
Écartés par le plancher (<15 m²) : 13 (témoins) ; par le plafond (>60) : 0.

| INSEE | Commune | total | brûlante | chaude |
|---|---|---|---|---|
| 97415 | Saint-Paul | 13 | 2 | 11 |
| 97411 | Saint-Denis | 7 | 0 | 7 |
| 97416 | Saint-Pierre | 3 | 0 | 3 |
| 97408 | La Possession | 3 | 0 | 3 |
| 97413 | Saint-Leu | 3 | 0 | 3 |
| 97405 | Petite-Île | 2 | 0 | 2 |
| 97423 | Les Trois-Bassins | 1 | 0 | 1 |
| 97420 | Sainte-Suzanne | 1 | 0 | 1 |
| 97401 | Les Avirons | 1 | 0 | 1 |

Liste exhaustive (47 = 34 bande + 13 témoins) : `qa/m39/mesure_a_blanc_p2.csv`.

### P2.2-bis · Vérification géométrique piscine ⊂ parcelle (demande Vic — chiffre d'abord)

**La bonne question** (soulevée par Vic) : la piscine détectée est-elle géométriquement **contenue
dans la parcelle servie**, ou est-ce celle du voisin (rattachement par proximité) ? Une détection
décalée déclasserait un terrain nu à cause de la piscine d'à côté. **Mesuré sur les 34**
(`ST_Contains` / `ST_Intersects` / centroïde, CRS métrique 2975 ;
`qa/m39/geometrie_piscine_parcelle_p2.csv`) :

| statut géométrique | n | lecture |
|---|---|---|
| **CONTENUE** (piscine 100 % dans la parcelle) | **23** | net |
| **À CHEVAL** (straddle le bord cadastral) | **11** | dont 2 à ratio 1,00 (bord tangent = de fait contenues) |
| **HORS parcelle** | **0** | aucune détection entièrement chez le voisin |

**Point rassurant** : les **34 ont leur centroïde piscine DANS la parcelle servie** — le
rattachement (par centroïde) n'a jamais désigné une piscine dont le centre est chez le voisin. Les
à-cheval sont des bassins qui **traversent la limite cadastrale**. Les plus douteux (part de la
piscine dans la parcelle < 60 %) : **BE1329 (44 %), CY0402 (52 %), DE2193 (52 %), CY0985 (55 %),
AV0547 (60 %)** — 5 cas à trancher à l'œil.

**Deck refait** (`qa/m39/deck_m39.html`, `gen_deck_m39.py`) : les **34** parcelles, **zoomées sur la
parcelle**, avec **contour parcelle (orange, comme les fiches)** + **polygone piscine (bleu)** +
rappel chiffré (surface parcelle, surface piscine, % piscine/parcelle, ratio dans la parcelle,
position central/périphérique). **À-cheval en tête** (ratio croissant). Aperçu :
`qa/m39/screens/4_deck_apercu_geo.png`.

**Recommandation de règle (mesurée, NON implémentée — décision Vic)** : ajouter une exigence de
**contenance** à `piscine_signal.yaml`. Options chiffrées :
- `ST_Contains` **strict** → 23/34 (écarte les 11, dont 2 tangents pourtant OK) — trop dur.
- **centroïde dans la parcelle** (déjà 34/34) **ET** part de la piscine dans la parcelle
  `ratio ≥ 0,5` → écarte **BE1329 seul** (44 %) → 33/34. **Recommandé** comme garde-fou honnête
  (« la piscine est majoritairement sur cette parcelle »), le reste tranché sur le deck.

Rien n'est implémenté : le knob de contenance et son seuil sont à fixer par Vic après revue du deck.

### P2.2-ter · Critère de surface RELATIVE — 4 scénarios mesurés (demande Vic)

**Ce que le deck géométrique a révélé** : la piscine occupe **1 à 5 % de la parcelle dans la
grande majorité des 34** (CY0363 1,8 % sur 1 335 m², AB0321 0,7 % sur 3 896 m²…). Une piscine de
24 m² sur 1 300 m² **ne bloque pas** la parcelle — elle signale une maison occupée (domaine du
**filtre bâti**), pas un « usage installé ». Déclasser ces chaudes serait une perte sèche
d'opportunités. Vic a raison : la bande absolue [15;60] seule sur-déclasse.

**Sweep du critère relatif** (piscine / surface parcelle), **avec garde de contenance appliquée**
(centroïde dans + ratio ≥ 0,5 → base 33, BE1329 écartée). Digest par parcelle :
`qa/m39/mesure_scenarios_relatif_p2.csv`.

| scénario (bande [15;60] + contenance +) | déclassées | brûlante | chaude | communes |
|---|---|---|---|---|
| contenance seule (pct ≥ 0) | 33 | 2 | 31 | 9 |
| **+ pct ≥ 5 %** | 12 | 2 | 10 | 6 |
| **+ pct ≥ 10 %** | 8 | 1 | 7 | 5 |
| **+ pct ≥ 15 %** | **5** | 1 | 4 | 3 |
| **+ pct ≥ 20 %** | 1 | 0 | 1 | 1 |

Par commune (déclassées, garde de contenance) :

| INSEE · commune | ≥5 % | ≥10 % | ≥15 % | ≥20 % |
|---|---|---|---|---|
| 97415 Saint-Paul | 6 | 3 | 3 | 0 |
| 97413 Saint-Leu | 2 | 2 | 0 | 0 |
| 97401 Les Avirons | 1 | 1 | 1 | 1 |
| 97408 La Possession | 1 | 1 | 1 | 0 |
| 97411 Saint-Denis | 1 | 1 | 0 | 0 |
| 97420 Sainte-Suzanne | 1 | 0 | 0 | 0 |

**Scénario 15 % — les 5 retenues** (deck `qa/m39/deck_m39_s15.html`, aperçu
`screens/5_deck_s15_apercu.png` ; 5 retenues + 5 témoins juste sous le seuil) :

| IDU | tier | parcelle | piscine | pct | ratio |
|---|---|---|---|---|---|
| 97401000AR1289 | chaude | 157 m² | 40,2 m² | 25,7 % | 0,75 |
| 97415000BV0606 | brûlante | 125 m² | 21,9 m² | 17,5 % | 1,00 |
| 97415000CX0650 | chaude | 216 m² | 36,5 m² | 16,9 % | 1,00 |
| 97415000CY0985 | chaude | 156 m² | 25,1 m² | 16,1 % | 0,55 |
| 97408000AC2215 | chaude | 131 m² | 19,9 m² | 15,1 % | 1,00 |

**Ma lecture métier (question 4 de Vic)** — à partir de quand le déclassement se défend ?
- **< 10 %** : « une maison avec bassin » sur une parcelle qui garde du résiduel mobilisable
  (parcelles de 500–3 900 m²). L'occupation est déjà le travail du **filtre bâti** ; le signal
  piscine n'ajoute rien de décisif → **ne pas déclasser** (le doute profiterait au déclassement).
- **≥ 15 %** : la piscine seule prend 1/6 à 1/4 du terrain — les 5 retenues sont de **petites
  parcelles (125–216 m², une à 513 m²)** déjà bâties, où bassin + maison **saturent le lot**. Là
  le signal dit « usage installé », pas « maison anodine ». Ces 5 sont servies chaude/brûlante donc
  **non déjà prises par le filtre bâti-saturé** — le signal piscine apporte une info réelle.
- **≥ 20 %** (1 seule) : trop étroit, on perd des vrais cas (BV0606/CX0650 à 17 %).

**Recommandation : seuil relatif ≥ 15 % + bande [15;60] m² + contenance (centroïde dans +
ratio ≥ 0,5).** Population défendable : **5 parcelles** (vs 34 sur la bande absolue seule) —
Saint-Paul 3, Les Avirons 1, La Possession 1. C'est la boussole : on ne déclasse que là où on est
sûr que la parcelle est réellement hors marché. **Rien n'est implémenté** ; la config reste inerte,
la décision (seuil 10 vs 15 %) se prend sur les chiffres et le deck 15 %.

### P2.3 · Geste de bascule préparé, JAMAIS exécuté — commit `[M39-P2]`
`scripts/bascule_m39.py` sur le modèle de `bascule_m32.py` : **DRY-RUN par défaut** (n'écrit rien),
geste réel gaté derrière `LABUSE_M39_EXECUTE=1` (jamais posé). Le geste réel :
persist_millesime(ortho) · archive `q_v8_calibre → q_v8_calibre_pre_m39` · re-score · **CONFORME
STRICT hors registre** · **ré-applique le registre existant à l'identique** (motif + motif_client) ·
applique les 34 déclassements (motif client famille) · verify_completude · check_fraicheur ·
**golden_regen dans le geste** (6e garde). **Dry-run testé** : 34 déclassements, 9 communes,
**chevauchement règle ∩ registre = 0** (zéro double comptage), 5 entrées registre préservées.

**Mode d'emploi (pour Vic, quand décidé)** : `LABUSE_M39_EXECUTE=1 PYTHONPATH=src python
scripts/bascule_m39.py` puis merge `--no-ff` après revue. Sans le flag, la commande n'imprime que
le plan.

---

## VÉRIFICATION (2026-08-06)

| Contrôle | Résultat |
|---|---|
| **Golden** | **117/117 PASS, 0 FAIL** (API sur code M39, 0 incohérence base↔API) |
| **Re-mesure M34/M35** (`mesure_p2`, 1071 parcelles) | **0 divergence dans les deux sens — PASS** |
| **SHA256 vigilances M37** | `482da6f6…e9abe9` — **INCHANGÉ** (recalculé : 4 344 938 lignes / 431 632 parcelles) |
| **Tiers servis** | **0 tier modifié** — distribution identique au baseline P0 ; AK1442/AL1154 restent a_creuser, motif_client intact |
| **Tests ciblés** | 32 verts (resume/verdict_servi/bascule_gardes/fraicheur/piscine) |

**Écritures DB, toutes hors scoring et tracées** : `data_sources` (millésime ortho) ·
`served_run_exceptions.motif` des 2 seeds (interne, jamais servi). Aucune écriture
`parcel_p_score_v2` / run / cache scoring / cascade.

### Captures (`qa/m39/screens/`)
1. `1_chaude_vigilance_piscine.png` — une chaude (97411000EL0203, 48,6 m²) : vigilance piscine servie.
2. `2_AL1154_reconciliation_registre.png` — AL1154 : réconciliation registre → règle, **motif client
   identique** (« Piscine détectée sur imagerie aérienne 2025 — usage du terrain à vérifier »).
3. `3_temoin_sous_seuil_sans_vigilance.png` — témoin 97411000BX0347 (14,9 m² < 15) : **AUCUNE
   vigilance piscine** (le plancher écarte — témoin du seuil).

### Digests de preuve (convention M37)
- `candidats_declassement_p0.csv` (47) · `mesure_a_blanc_p2.csv` (47, bande/écartés) ·
  `mesure_par_commune_p2.csv` (9) · `piscines_materialisees_x_tier.csv.gz` (8 299, exhaustif) ·
  `_global.txt` (SHA256 + résumé vérif).

---

## Ce qui N'A PAS été fait (par conception) et les dettes nommées

- **Aucune bascule** : les 34 restent brûlantes/chaudes. La décision est à Vic sur la mesure à blanc
  + les 20 orthos. Le geste est prêt.
- **Dette C2** (nommée, non exécutée) : la **bande probe-ratée** — ~4 858 détections FLAIR-NULL à V0
  fort sur l'île (dont 11 sur chaudes servies, plus les 2 seeds) où FLAIR n'a jamais été calculé.
  Re-run FLAIR possible (coût : re-télécharger les tuiles, cache purgé). Rejoindra la file si la
  règle C1 prouve sa valeur en usage.
- **Dette A2** (nommée) : acquisition d'un millésime ortho **historique** IGN pour dater vraiment les
  piscines (« récente ») — non financée tant que le signal non daté n'a pas montré sa valeur.
