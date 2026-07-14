# M8 — Vague ingestion réglementaire — RECONNAISSANCE (LOT 1, lecture seule)

**Date** : 2026-07-14 · **Branche** : `feat/m8-ingestion` · **Run servi** : `q_v5_m6b` · **Modèle P M3.6 GELÉ** (aucun ré-entraînement).

⚠️ **Ce document est un RAPPORT. Rien n'a été ingéré, aucune table créée, aucune écriture en base, aucun re-run.**
Vic décide du périmètre à partir de ce rapport ; le lot 2 (ingestion) n'est PAS enchaîné.

---

## 0. Méthode

- Source de vérité de dispo : **WFS GPU** `https://data.geopf.fr/wfs/ows`, couches `wfs_du:*`, filtre `partition='DU_<INSEE>'`
  (l'attribut `insee` du WFS est vide → inutilisable ; le filtre `partition` est le bon).
- 24 communes = référentiel `src/labuse/ingestion/run_all.py:REUNION_COMMUNES`.
- Pour chaque commune : `document` (version opposable + `gpu_status`), `zone_urba` (count), `prescription_{surf,lin,pct}`,
  `info_{surf,lin,pct}`, `secteur_cc`. Agrégation **par libellé** (voir §5.a : les codes `typepsc`/`typeinf` sont peu fiables).
- **Qualité géométrique** : le sondage a exclu la géométrie (`PROPERTYNAME` sans `the_geom`) pour la vitesse →
  la validité fine (auto-intersections, trous) reste **à valider à l'ingestion** (pas de `shapely` dans l'env de recon).
  Signaux qualité captés en recon : `gpu_status` (opposabilité), unicité `idpsc`/`idinfo` (doublons), présence/volume.
  **Tous les documents servis sont en `gpu_status = production`** (= version opposable courante).

---

## 1. Synthèse exécutive — go/no-go par couche

| # | Couche | Dispo GPU | Décision proposée | Motif court |
|---|--------|-----------|-------------------|-------------|
| 1 | **Emplacements réservés (ER)** | 18/20 communes PLU | **GO (gap-fill/promotion)** | Déjà dans `plu_gpu_prescription` (21 comm.) ; extraire en couche typée. Filtrer par libellé (code instable). |
| 2 | **EBC** | 19/20 communes PLU | **GO (gap-fill/promotion)** | `typepsc 01` fiable ; déjà partiellement en base. Qualité la meilleure des 7. |
| 3 | **OAP (23 hors St-Paul)** | **périmètre seul, ~7 comm.** | **GO partiel / NO-GO contenu** | Seul le *périmètre* OAP est vectorisé (7 comm.) ; le *contenu* OAP est PDF only. 15 comm. = rien. |
| 4 | **Zonage assainissement** ⭐ | **4/24 seulement** | **NO-GO GPU (0 net new)** | Les 4 dispo (SD, Le Port, St-Paul, Étang-Salé) sont **déjà en base**. GPU ne comble RIEN. Voir §5.4. |
| 5 | **SAR / SMVM** | **absent du wfs_du** | **NO-GO cette vague** | Pas de couche annexe par commune. Coupures déjà en zonage (zones `Acu`) + proxy ODS `sar` en base. |
| 6 | **DPU / ZAD** | 3/24 significatives | **NO-GO (recommandé)** | Couverture St-Paul/St-Denis/Ste-Marie seulement, non exhaustif ; faible valeur scoring. |
| 7 | **Bande 100 m loi Littoral** | **n'existe pas au GPU** | **NO-GO ingestion → à CALCULER** | Aucune source GPU. À dériver de `trait_de_cote` (déjà en base 24/24) × espaces urbanisés. |

**Le twist qui change le cadrage** : les couches « faciles » (ER, EBC) sont **déjà largement en base** ; la couche
**priorité haute (assainissement) est un cul-de-sac côté GPU** (4/24, déjà là). La vraie valeur M8 n'est donc pas
« aspirer le GPU » mais : (a) **promouvoir** ER/EBC en couches typées exploitables par le moteur, (b) **combler les
3 communes vides** (contraintes GPU), (c) traiter assainissement/bande-100m **hors GPU**.

---

## 2. État de la base AVANT M8 (pour ne rien ré-ingérer)

`spatial_layers` contient déjà (extrait pertinent) :

| kind | features | communes | Rapport aux couches M8 |
|---|--:|--:|---|
| `plu_gpu_prescription` | 10 490 | 21 | **contient déjà ER + EBC + périmètre OAP** (voir subtypes ci-dessous) |
| `plu_gpu_zone` | 5 848 | 24 | zonage (dont coupures `Acu` = proxy SAR) |
| `zonage_assainissement` | 258 | **4** | = exactement les 4 communes dispo au GPU (SD 119, Le Port 92, St-Paul 27, Étang-Salé 20) |
| `sar` | 2 453 | 24 | **proxy ODS Région** (`espacesar`), pas le réglementaire |
| `trait_de_cote` | 24 168 | 24 | base pour **calculer** la bande 100 m (couche 7) |
| `cinquante_pas` | 163 | 0* | 50 pas géométriques — servitude **distincte**, ne couvre PAS la bande 100 m |
| `sup` | 417 | 24 | servitudes d'utilité publique (hors périmètre des 7 couches) |
| `ppr` | 164 | 24 | risques (déjà traité) |

Subtypes `plu_gpu_prescription` déjà en base : `05`=Emplacement réservé (2250), `01`=Espace boisé classé (1782),
`18`=Périmètre OAP (100), etc. → **ER/EBC/OAP-périmètre sont déjà partiellement ingérés**, pas une ingestion vierge.

\* `commune` NULL pour `cinquante_pas` (ingéré sans rattachement commune).

---

## 3. Tableau maître — dispo GPU par commune × couche

Compte de features **au GPU** (live 2026-07-14), filtre `partition='DU_<INSEE>'`.
ER/EBC/OAP = comptés dans les prescriptions **par libellé** ; Assain./DPU-ZAD dans les informations.

| INSEE | Commune | Doc GPU opposable | zones | ER | EBC | OAP | Assain. | DPU/ZAD |
|---|---|---|--:|--:|--:|--:|--:|--:|
| 97401 | Les Avirons | 97401_PLU_20241206 | 163 | 25 | 57 | 0 | 0 | 0 |
| 97402 | Bras-Panon | 97402_PLU_20260428 | 130 | 50 | 55 | 0 | 0 | 0 |
| 97403 | Entre-Deux | 97403_PLU_20240924 | 182 | 63 | 101 | 0 | 0 | 0 |
| 97404 | L'Étang-Salé | 97404_PLU_20250917 | 78 | 0 | 30 | 12 | **20** | 0 |
| 97405 | Petite-Île | 97405_PLU_20230609 | 335 | **0** | **0** | 0 | 0 | 0 |
| 97406 | La Plaine-des-Palmistes | 97406_PLU_20230527 | 274 | 61 | 87 | 0 | 0 | 0 |
| 97407 | Le Port | 97407_PLU_20241209 | 110 | 24 | 28 | 8 | **92** | 1 |
| 97408 | La Possession | 97408_PLU_20251217 | 246 | 53 | 8 | 2 | 0 | 0 |
| 97409 | Saint-André | **— vide (AGORAH)** | 0 | 0 | 0 | 0 | 0 | 0 |
| 97410 | Saint-Benoît | 97410_PLU_20200206 | 306 | 62 | 170 | 0 | 0 | 0 |
| 97411 | Saint-Denis | 97411_PLU_20260423 | 259 | 493 | 405 | 0 | **119** | 71 |
| 97412 | Saint-Joseph | 97412_PLU_20251210 | 343 | 0 | 64 | 19 | 0 | 0 |
| 97413 | Saint-Leu | **— vide (AGORAH)** | 0 | 0 | 0 | 0 | 0 | 0 |
| 97414 | Saint-Louis | **— vide (RETIRÉ)** | 0 | 0 | 0 | 0 | 0 | 0 |
| 97415 | Saint-Paul | 97415_PLU_20251217 | 765 | 155 | 12 | 15 | **27** | 160 |
| 97416 | Saint-Pierre | 97416_PLU_20240625 | 285 | 346 | 58 | 0 | 0 | 0 |
| 97417 | Saint-Philippe | **— vide (RNU)** | 0 | 0 | 0 | 0 | 0 | 0 |
| 97418 | Sainte-Marie | 97418_PLU_20251126 | 268 | 15 | 221 | 12 | 0 | 2 |
| 97419 | Sainte-Rose | 97419_PLU_20190504 | 125 | 2 | 3 | 0 | 0 | 0 |
| 97420 | Sainte-Suzanne | 97420_PLU_20250929 | 191 | 27 | 50 | 21 | 0 | 0 |
| 97421 | Salazie | 97421_PLU_20220524 | 325 | 90 | 137 | 0 | 0 | 0 |
| 97422 | Le Tampon | 97422_PLU_20230811 | 391 | 158 | 40 | 13 | 0 | 0 |
| 97423 | Les Trois-Bassins | 97423_PLU_20220602 | 165 | 41 | 122 | 0 | 0 | 0 |
| 97424 | Cilaos | 97424_PLU_20240213 | 149 | 98 | 63 | 0 | 0 | 0 |

**4 communes sans document GPU** : Saint-André (97409) & Saint-Leu (97413) = repli AGORAH connu ;
Saint-Louis (97414) = **doc GPU retiré** (voir §5.a) ; Saint-Philippe (97417) = **RNU, aucun PLU** (voir §5.a).
`secteur_cc = 0` partout (confirme : PLU purs, pas de cartes communales).

---

## 4. Écrasement de version : AUCUN drift

Comparaison `idurba` **en base** (`spatial_layers.plu_gpu_zone`) vs **opposable au GPU** aujourd'hui :
**identiques sur les 20 communes calibrées**. Les pièges d'écrasement redoutés en mémoire (Saint-Joseph, Bras-Panon)
sont **déjà résolus** — la base porte bien `97412_PLU_20251210` et `97402_PLU_20260428`.
→ **Pas de ré-ingestion de zonage requise pour écrasement.** Les annexes M8 se rattachent au même `partition` déjà servi.

Cas particuliers de base :
- Saint-André `97409_20190228`, Saint-Leu `97413_20070226` = zonage **AGORAH** (GPU vide) — cohérent.
- Saint-Louis `97414_plu_20251218` (245 zones en base) alors que **GPU actuellement vide** → source antérieure/hors-GPU.
- Saint-Philippe : base = `97412_PLU_20240320` (3 zones) = **spillover Saint-Joseph 97412**, pas de vrai zonage (RNU).

---

## 5. Détail par couche — ingérable vs écarté

### 5.a Constats qualité transverses (leçon des 441 doublons M6)
1. **`typepsc`/`typeinf` non fiables entre communes** : ex. « Emplacement réservé » est tantôt `typepsc 05`,
   tantôt libellé « ER n° … » sous un autre code ; `07` sert ailleurs à « SPR - Front végétalisé ».
   → **toute ingestion doit classer par libellé (regex), pas par code numérique.**
2. **`idpsc`/`idinfo` uniques** : 0 doublon d'identifiant détecté au GPU sur les prescriptions surfaciques (bon signe).
3. **Saint-Louis (97414)** : doc GPU **toujours retiré** (0 zone, 0 prescription, pas de document `production`).
   Conformément à la consigne : **pas de ré-ingestion tant qu'il l'est**. Le zonage `97414_plu_20251218` déjà en base
   n'a **pas** d'annexes GPU rattachables aujourd'hui → couches M8 **non fetchables** pour St-Louis.
4. **Saint-Philippe (97417)** = RNU, aucun PLU opposable, GPU 0 doc → **non concerné** par toutes les couches M8.
5. **Petite-Île (97405)** : anomalie — **0 prescription surfacique** au GPU (ni ER ni EBC) alors que 335 zones existent.
   Le PLU a des ER/EBC au règlement mais **non vectorisés** au GPU. → NO-GO ER/EBC pour Petite-Île (rien à ingérer).

### 5.1 Emplacements réservés (ER) — **GO (gap-fill + promotion typée)**
- **Ingérable** : 18/20 communes PLU (fort : St-Denis 493, St-Pierre 346, Le Tampon 158, St-Paul 155, Cilaos 98, Salazie 90).
- **Écarté** : Petite-Île (0 vectorisé), Sainte-Rose (2, quasi rien), + les 4 communes sans doc (SA, SL, StL, SPh).
- **Nuance forte** : ER **déjà présent** dans `plu_gpu_prescription` (subtype 05, 2250 features). M8 = surtout **promouvoir**
  ces prescriptions en couche ER typée pour le moteur (ER = servitude d'inconstructibilité de fait → signal foncier),
  + combler les communes non couvertes. Classer par libellé (`emplacement réservé` OU `ER `).

### 5.2 EBC — **GO (gap-fill + promotion typée)**
- **Ingérable** : 19/20 communes PLU (`typepsc 01` cohérent + libellé « Espace boisé classé »). Fort : St-Denis 405,
  Ste-Marie 221, St-Benoît 170, Salazie 137, Trois-Bassins 122, Entre-Deux 101.
- **Écarté** : Petite-Île (0), + 4 communes sans doc. Sainte-Rose faible (3).
- **Meilleure qualité des 7 couches** (code fiable). EBC = inconstructibilité dure → signal net pour le moteur.

### 5.3 OAP (23 communes hors Saint-Paul) — **GO partiel (périmètre) / NO-GO (contenu)**
- **Ingérable** : **périmètre OAP** vectorisé (prescription « Périmètre OAP ») pour **~7 communes** : Sainte-Suzanne 21,
  Saint-Joseph 19, Saint-Paul 15 (déjà M6), Le Tampon 13, L'Étang-Salé 12, Sainte-Marie 12, Le Port 8, La Possession 2.
- **Écarté** :
  - **Contenu OAP** (orientations, schémas d'aménagement, principes) = **PDF only**, non vectorisé au GPU → NO-GO.
  - **15 communes n'ont AUCUN périmètre OAP** au GPU → rien à ingérer.
- Couche **faible au GPU** : n'apporte qu'un polygone « il y a une OAP ici », sans la règle. Valeur limitée.

### 5.4 Zonage d'assainissement collectif/non-collectif — **NO-GO GPU (priorité haute mais cul-de-sac)** ⭐
- **Dispo GPU = 4 communes seulement** (`info_surf typeinf 19`) : St-Denis 119 (actuel/court/moyen/long terme),
  Le Port 92 (collectif/autonome), St-Paul 27 (collectif/semi-collectif), Étang-Salé 20 (collectif/non collectif).
- **Ces 4 sont déjà en base** (`zonage_assainissement`, 258 features, exactement ces 4 communes) → **net new GPU = 0**.
- **Les 20 autres communes n'ont PAS de zonage d'assainissement au GPU.**
- **Conclusion** : le GPU ne peut PAS servir la priorité haute au-delà de l'existant. Pour couvrir les 20 restantes :
  source **hors GPU** (zonage d'assainissement communal/EPCI — SDAEU, arrêtés) OU conserver le proxy INSEE EGOUL
  (`parcel_anc`, déjà en base) comme approximation. **Décision produit à Vic.**

### 5.5 SAR / SMVM (coupures d'urbanisation, espaces agricoles protégés) — **NO-GO cette vague**
- **Absent du `wfs_du`** : le SAR est un document de rang supérieur régional, pas une annexe PLU par commune.
  Aucune couche SAR dédiée au WFS GPU (seul `wfs_scot:*` existe, pour les SCoT — pas le SAR Réunion).
- **Déjà proxié en base** : les coupures d'urbanisation SAR sont matérialisées dans le zonage PLU en zones `Acu`
  (`plu_gpu_zone`, en base) + couche `sar` proxy ODS Région (2 453 features, 24 comm.).
- Une ingestion du **document SAR régional** (mono-document, hors périmètre par-commune) serait un chantier séparé —
  **à arbitrer hors M8**.

### 5.6 DPU / ZAD — **NO-GO (recommandé)**
- **Dispo GPU** significative sur **3 communes** : St-Paul (DPU 149 + délégations, ZAD Cambaie/Barrage),
  St-Denis (DPU 39+2, ZAD 1, préemptions Dept/ENS/SAFER), Sainte-Marie (2). Ailleurs ~0.
- Le DPU couvre en pratique **toute la zone U** (droit communal) : l'info GPU est donc **partielle et non exhaustive**,
  et le signal « préemption » a une valeur scoring faible (friction diffuse, pas discriminant foncier).
- **GO opportuniste possible** (St-Paul + St-Denis uniquement) si Vic veut un badge « périmètre de préemption » ;
  sinon **NO-GO**.

### 5.7 Bande 100 m loi Littoral — **NO-GO ingestion → tâche de CALCUL**
- **N'existe PAS comme couche GPU.** Les « 100 m » trouvés au GPU sont des **périmètres bâtiments d'élevage**
  (agricole, RSD) — **rien à voir** avec la loi Littoral. Piège de libellé à ne pas confondre.
- À **dériver** : `trait_de_cote` DEAL (déjà en base, 24 168 features, 24 comm.) → tampon 100 m ∩ **espaces urbanisés**
  (à définir : OCS-GE / zones U du PLU). Inconstructibilité L.121-16 hors espaces urbanisés.
- Attention : `cinquante_pas` en base (163) = **50 pas géométriques**, servitude distincte, **ne couvre pas** la bande 100 m.
- **Décision** : hors « ingestion » — c'est une **couche calculée** à cadrer (LOT dédié), pas un fetch GPU.

---

## 6. Ce qui est ingérable vs écarté — récapitulatif décision

**Ingérable au GPU (go)** :
- **ER** — 18 communes, en promotion/gap-fill (classer par libellé).
- **EBC** — 19 communes, meilleure qualité, promotion/gap-fill.
- **OAP périmètre** — 7 communes seulement, polygone sans contenu (valeur limitée).

**Écarté (no-go), avec raison** :
- **Assainissement** — GPU plafonné à 4 communes déjà en base (0 net new) ; reste = hors GPU.
- **SAR/SMVM** — pas de couche GPU par commune ; déjà proxié (zones `Acu` + ODS `sar`).
- **DPU/ZAD** — couverture 3/24, non exhaustif, faible valeur (go opportuniste St-Paul/St-Denis au choix de Vic).
- **Bande 100 m Littoral** — inexistante au GPU ; **couche à calculer**, pas à ingérer.
- **OAP contenu** — PDF only, non vectorisé.
- **4 communes hors périmètre annexes** : Saint-André & Saint-Leu (AGORAH), Saint-Louis (GPU retiré — **ne pas ré-ingérer**),
  Saint-Philippe (RNU).

---

## 7. Décisions demandées à Vic (avant LOT 2)

1. **ER + EBC** : GO promotion en couches typées ? (source = re-fetch GPU propre, OU dérivation depuis
   `plu_gpu_prescription` déjà en base). Périmètre = 18-19 communes (Petite-Île & les 4 vides exclues).
2. **Assainissement (priorité haute)** : le GPU est un cul-de-sac (4/24 déjà là). Arbitrer la source des 20 restantes
   (SDAEU communal/EPCI hors GPU vs conserver proxy EGOUL `parcel_anc`).
3. **OAP** : ingérer le périmètre pour les 7 communes malgré la faible valeur, ou écarter ?
4. **DPU/ZAD** : NO-GO (défaut) ou GO opportuniste St-Paul + St-Denis ?
5. **Bande 100 m** : ouvrir un LOT « couche calculée » séparé (trait de côte × espaces urbanisés) ?
6. **SAR régional** : chantier mono-document séparé, ou on se contente du proxy existant ?

---

*Fin du LOT 1. Aucune ingestion effectuée. STOP — en attente de l'arbitrage de périmètre de Vic.*
