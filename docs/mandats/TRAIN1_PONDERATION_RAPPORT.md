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
