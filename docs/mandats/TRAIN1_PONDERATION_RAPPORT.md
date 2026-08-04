# TRAIN 1 — PONDÉRATION au_sous_plancher + DETTE #4 — rapport de mesure

> Régime [S]. **POINT D'ARRÊT — rien n'a basculé.** Le run servi `q_v8_calibre` est
> strictement intact (vérifié : ses tiers n'ont pas bougé d'une ligne). Tout ce qui suit
> est mesure à blanc sur runs jetables + code committé NON servi. Vic arbitre.

## 1 · Pondération option B — implémentation

`facteur = 1 − manque/seuil = surface/seuil`, appliqué au **signal p** des parcelles
`au_sous_plancher` AVANT rangs/percentiles (`_pondere_au_sous_plancher`, pipeline p_v2).
Même point de calcul que la mention de fiche (`au_ouverture.facteur_ponderation` =
`zone_regime` + `seuil_surface_m2`) — aucun seuil recopié. La parcelle **reste servie**
(mention + assemblage intacts) ; seule sa place dans le classement reflète le manque.
Kill-switch `LABUSE_DISABLE_AU_POND` ; `LABUSE_DISABLE_AU_STATUT` la coupe aussi.
Tests unitaires : 9 verts (dont le cas CX2555 : 195 m² / 3 333 → facteur 0,0585, manque
94,2 % — identique au motif de l'exception servie).

## 2 · Mesure à blanc (runs jetables q_v9_pond_avant / q_v9_pond_apres)

Protocole `rerun_ablanc` : même cascade étage 0 (`q_v8_calibre`), même hystérésis
(prev = `q_v8_calibre`), contrôle pond OFF vs traitement pond ON, 151 s / 153 s.
Hygiène : lignes `p_score_v2_runs` des jetables retirées — le « latest » hystérésis
reste `q_v8_calibre`. Les lignes de tiers restent en base pour ta revue (purge après
arbitrage, comme q_v8_au_*).

**Contrôle parfait** : AVANT vs `q_v8_calibre` = 2 écarts sur 431 663 — exactement les
2 exceptions manuelles (CX2555, CH1893). L'environnement reproduit le servi à l'identique ;
le delta AVANT→APRÈS est donc l'effet PUR de la pondération.

### Population au_sous_plancher : 1 069 (les « 708 » du 30/07 + calibrations depuis)

| commune | sous-plancher | bougées | sorties de tête |
|---|---:|---:|---:|
| Saint-Leu | 662 | 54 | 19 |
| Les Trois-Bassins | 407 | 19 | 19 |

### Matrice de mouvements (île entière, 117 parcelles bougent)

| avant → après | n | lecture |
|---|---:|---|
| chaude → a_creuser | 31 | sous-plancher fortement pondérées, sortent de tête |
| brûlante → a_creuser | 7 | idem, dont CX2555 et AB1911 (ex-rang 6) |
| a_creuser → chaude | 36 | **effet mécanique** : les rangs libérés font entrer les suivantes (rangs ~3030→~2980) |
| chaude → brûlante | 8 | effet mécanique du recalibrage brûlante (effectif 119→120, garde-fou [30-120] OK) |
| a_creuser → réserve | 35 | recalcul du top-décile C |

Effectifs finaux stables : brûlantes 120, chaudes 1 038 (vs 1 041), réserve +35.

### Sanity
- **0** parcelle sous-plancher n'ENTRE en tête à cause de la pondération.
- **8** sous-plancher RESTENT en tête (manque faible ou p brut très fort) — comportement
  proportionnel voulu par l'option B, pas une éviction. ⚠ Dont **AB1908 (rang 139) et
  AB1910 (rang 141)**, brûlantes à facteur ≈ 0,19 (manque ~81 %) qui survivent par p brut…
  et qui sont AUSSI dans la liste dette #4 (piscine détectée, couche bâti 0). Double signal —
  à trancher visuellement avant toute bascule.

### CX2555 — l'exception peut tomber
| run | tier | rang |
|---|---|---:|
| q_v8_calibre (servi, exception manuelle) | chaude | 1 034 |
| contrôle pond OFF (naturel) | brûlante | 1 034 |
| **pondération ON** | **a_creuser** | **427 206** |

La pondération la classe d'elle-même très loin de la tête (facteur 0,0585). **Reco :
lever l'exception manuelle au moment de la bascule de la pondération** — le classement
naturel fait mieux que l'exception (qui la gardait chaude).

## 3 · Cartes

`qa/ponderation/cartes_mouvements.html` — une carte ortho IGN par mouvement en tête
(82 cartes : 46 sorties + 44 entrées mécaniques, harnais maison `division_review`,
tuiles IGN cachées /tmp — même usage réseau que `cartes_assemblage`, noté règle 4).

## 4 · Dette #4 — têtes suspectes (couche batiment ≈ 0 vs preuves d'habitation)

Mesure : top 1 000 rangs du servi, emprise couche batiment < 20 m² (631 parcelles — l'emprise 0
est NORMALE pour une tête, le foncier nu est le produit), croisée avec les preuves INDÉPENDANTES :
piscine/PV ortho (hors faux positifs) et vente DVF bâtie.

**46 suspectes confirmées** (43 piscines, 1 PV, 3 DVF-bâti) : **13 brûlantes, 19 chaudes**,
le reste écartée/déclassée. Revue visuelle : `qa/dette4/revue_suspectes.html` (lien satellite
par parcelle). **Rien n'est déclassé** — arbitrage parcelle par parcelle après ta revue.

Motif systémique : le lotissement **DK à Saint-Paul** (10 parcelles, rangs 80-431, toutes avec
piscine sur couche vide) — trou de couche par SECTEUR, pas du bruit aléatoire.

### CH1893 — reco : PÉRENNISER l'exception
CH1893 est invisible de TOUTES les sources de données (couche batiment 9,4 m², ni piscine, ni
PV, ni DPE, ni DVF) — seule la photo ortho la montre. Aucun signal automatisé ne peut la
reclasser aujourd'hui. **Reco : exception pérennisée avec motif « couche batiment lacunaire,
aucun signal de rattrapage disponible », jusqu'au rechargement de la couche batiment**
(le vrai correctif, dette #4 train 5). Les CH1893-types ne se attrapent qu'à l'œil : le filet
piscine/PV/DVF détecte les suspectes ÉQUIPÉES, pas les maisons nues.

## 5 · Recommandations (arbitrage Vic)

1. **Basculer la pondération** (option B) au prochain re-score servi : effet net = 38 sorties
   de tête sous-plancher méritées, 0 entrée indue, effectifs stables. Réversible
   (`LABUSE_DISABLE_AU_POND=1`).
2. **Lever CX2555** au même moment (le naturel fait mieux que l'exception).
3. **Pérenniser CH1893** jusqu'au rechargement de la couche batiment.
4. **Revue visuelle des 46 suspectes** (page fournie) — les confirmer bascule par bascule ;
   AB1908/AB1910 en premier (brûlantes actives + double signal).
5. Recharger/compléter la **couche batiment** (secteur DK Saint-Paul d'abord) — c'est la
   dette racine ; la pondération et les exceptions n'en sont que des pansements.
6. Purge des jetables q_v9_pond_* après arbitrage (+ l'orphelin `q_v9_avant`, 431 k lignes
   sans ligne runs, résidu d'une mesure antérieure — à purger avec).

## Annexes
- Analyse SQL : `qa/ponderation/analyse_mouvements.sql` (rejouable).
- Mesure : `qa/ponderation/mesure_ablanc.py` · Cartes : `qa/ponderation/cartes_mouvements.py`.
- Suspectes : `qa/dette4/gen_revue_suspectes.py` + `revue_suspectes.html`.

---
# ADDENDUM — arbitrages Vic 04/08 + revue AB1908/AB1910

Arbitrages : **1)** pondération GO conditionné à AB1908/AB1910 · **2)** CX2555 levée validée
(à la bascule) · **3)** CH1893 pérennisée, motif dicté posé en base · **4)** revue des 46 après
AB1908/AB1910, mesure sectorielle demandée · **5)** rechargement couche = dette racine train 5 ·
**6)** purge après bascule.

## Revue AB1908 / AB1910 (cartes : qa/ponderation/cartes_ab1908_ab1910.html)

**CORRECTION D'ABORD** : mon rapport initial les disait « aussi dans la liste dette #4
(piscine sur couche vide) ». C'était FAUX — erreur de recoupement avec la série DK/AB1911.
Vérifié par IDU ET par géométrie : **zéro détection** sur ces deux parcelles, et elles ne sont
pas dans les 46. L'ortho le confirme : parcelles **nues**, la couche dit vrai.

| | AB1908 | AB1910 |
|---|---|---|
| Surface / seuil | 313 m² / 1 667 m² | 250 m² / 1 667 m² |
| Manque / facteur | 1 354 m² (81 %) / 0,188 | 1 416 m² (85 %) / 0,150 |
| Rang naturel → pondéré | **1** → 139 (brûlante) | **4** → 141 (brûlante) |
| Ortho | nue, rangée en chantier (Impasse des Pétrels, même îlot qu'AB1911 ex-rang 6) : terrassements frais, constructions mitoyennes, voirie neuve | idem, parcelle terrassée nue dans la même rangée |
| Couche batiment | 0 m² — VRAIE | 0 m² — VRAIE |

**Pourquoi le p brut est si élevé : SATURATION.** p_raw = **1,0 exact** pour les deux.
Top 5 du modèle : permis < 2 ans (+1,30 — dominant, le lotissement se construit autour),
zone AU (+0,39), canopée ≤ 0,4 (+0,24), croisement tenure×permis (+0,22), rotation foncier
nu (+0,21). L'île compte **5 parcelles à p=1,0 : les rangs 1-2-3-4-5 du servi** (AB1908/AB1910
Trois-Bassins + AP1647/AP1610/AP1609 La Possession — 2 lotissements récents). Les 3 AP ne sont
PAS pondérables (La Possession = densité seule, pas de plancher). → Audit train 5 (permis_bin,
plafonnement proba) consigné au BACKLOG.

**Lecture CC pour le GO** : elles TIENNENT au sens dette #4 (aucun bâti caché — le contraire
de CH1893). Leur maintien en brûlante post-pondération est un artefact de la saturation, pas
de la pondération : même à facteur 0,15, p pondéré 0,15 bat l'écrasante majorité de l'île.
Le GO final sur cartes appartient à Vic.

## Mesure sectorielle (arbitrage 4) — le trou est-il localisé ?

Profil « piscine détectée × couche < 20 m² », île entière : **1 061 parcelles · 456 secteurs ·
24 communes**. Concentration : 39 secteurs = 25 % du volume, 111 = 50 %, 224 = 75 %.
Communes de tête : Saint-Paul 188, Le Tampon 112, Saint-Pierre 107, Saint-Denis 71, Saint-Leu 68.
**Verdict : points chauds réels (EW/DK/CP Saint-Paul, CX Saint-Leu, EN Saint-Louis…) mais dette
DIFFUSE** — un ciblage strict par secteur ne la règle pas ; rechargement **par commune**
(Saint-Paul d'abord) ou complet.

## État post-arbitrages
- CH1893 : motif mis à jour dans `served_run_exceptions` (dicté Vic, tracé, lié train 5).
- CX2555 : levée actée, s'exécutera à la bascule.
- Purge q_v9_pond_* + q_v9_avant : après bascule.
- Toujours AUCUNE bascule : q_v8_calibre intact.
