# ÉTUDE V6 — Lot D : lotissement (division foncière)

Cas tests : **Saint-Leu AC0261 et AC0264, zone Ud, chacune seule.** Le type « Lotissement » ne lance
pas le moteur collectif : il branche la **division foncière de l'assiette** (à la demande, pas le batch
île), avec la **même borne de temps (30 s) et le même message** que l'Étude.

## Règle PLU Ud de surface / largeur minimale de lot
**Elle n'existe pas.** Zone Ud de Saint-Leu : aucune superficie ni largeur minimale de lot au PLU
(suppression des **articles 5** par la **loi ALUR, 2014**). Le nombre de lots est donc **géométrique**
(pavage le long d'une voirie, Estimé), pas une règle opposable. Ce que le PLU Ud impose et que LABUSE
sert, avec source : CES **40 %** (UD 9), **pleine terre 40 %** (UD 13), **2 places/logement** (UD 12 →
Art. 11 dispositions générales), hauteur R+combles (UD 10), retrait 5 m (UD 8).

> **Mise à jour (3 corrections).** Pleine terre = jardins privatifs (lot − emprise future au CES de la
> zone, 40 %) + espaces communs, avec un **contrôle Réussi/Échoué chiffré** ; voirie réaliste (largeur
> hypothèse faute de règle PLU, **aire de retournement d'impasse**, tracés I/T/croix essayés — l'impasse
> l'emporte ici) ; EBC vérifié (absent de la base). Chiffres ci-dessous = après correction.

## Tableau LABUSE / architecte — AC0261

| Poste | LABUSE | Architecte (OCEANIS) |
|---|---|---|
| Nombre de lots | **10** | **16** |
| Surface moyenne | 421,3 m² | ~450 m² (lots 400–450) |
| Surface minimale | 275,1 m² | 400 m² |
| Voirie | **488,0 m²** · impasse + aire de retournement (largeur hypothèse 5 m + trottoir, pas de règle PLU) | principale 1 609,84 + secondaire 814,26 = **2 424 m²** |
| Places | 20 (2/lot, UD 12) + 8 visiteurs (Estimé) | 32 (2/lot) + 13 visiteurs |
| **Pleine terre** | **Réussi** : **6 872,6 m²** ≥ 4 442,8 exigés (40 %, UD 13) — jardins privatifs 2 528 + communs 4 344,6 | privatif 7 011,61 + commun 2 391,98 = 9 403 m² |
| EBC | **absent de la base LABUSE** (à vérifier — voir ci-dessous) | « EBC » hachuré au SE |
| PPR rouge | **2 129,7 m² retiré** de l'assiette (R1+R2) | **non figuré** |
| Règle PLU surface/largeur min de lot | **aucune** (loi ALUR) | — |
| Raccordements | électricité (MT) 0 m · assainissement 4 168 m → autonome | — |
| Régime | **Permis d'aménager** (>2 lots + voirie) — à qualifier | — |

## Tableau LABUSE / architecte — AC0264

| Poste | LABUSE | Architecte (OCEANIS) |
|---|---|---|
| Nombre de lots | **14** | **14** ✓ |
| Surface moyenne | 417,0 m² | ~450 m² |
| Surface minimale | 254,6 m² | 400–450 m² |
| Voirie | **699,9 m²** · impasse + aire de retournement (largeur hypothèse 5 m + trottoir) | principale 1 519,14 + secondaire 4 466,26 |
| Places | **28** (2/lot) + 12 visiteurs | **28** (2/lot) + **12** visiteurs ✓ |
| **Pleine terre** | **Réussi** : **5 261,1 m²** ≥ 3 991,6 exigés (40 %) — jardins 3 503 + communs 1 758 | privatif 5 313,16 + commun 3 085,82 = 8 399 m² |
| EBC | absent de la base (à vérifier) | — |
| PPR rouge | 0 | — |
| Règle min-lot | aucune (ALUR) | — |
| Régime | Permis d'aménager — à qualifier | — |

## Corrections (retours)
1. **Pleine terre** : désormais jardins privatifs (lot × (1 − CES 40 %)) + espaces communs ; **contrôle
   Réussi/Échoué** chiffré, servi dans `controles[]` et affiché avec son badge. Les deux parcelles sont
   **Réussi** (large marge). Le verdict lotissement reste « À compléter » (régime à qualifier) et ne peut
   jamais être « Exploitable » (a fortiori si un contrôle est Échoué).
2. **Voirie réaliste** : largeur **hypothèse** affichée (aucune règle de voirie au PLU Ud → chaussée 5 m,
   trottoir à prévoir, Estimé) ; **aire de retournement** ajoutée au bout de l'impasse (visible au plan) ;
   le moteur essaie **I / T / croix** et retient le tracé qui donne le plus de lots — ici l'impasse en I
   gagne (parcelles allongées), le réseau en T/croix ne fait pas mieux.
3. **EBC** : vérifié — **aucune prescription EBC du GPU en base pour Saint-Leu** (table
   `plu_gpu_prescription` absente, aucune couche `ebc` sur la commune) → « non vérifié », jamais « absent ».
   **Superposition** : la zone « EBC » hachurée que l'architecte place au **sud-est** d'AC0261 **coïncide
   géographiquement avec le PPR rouge vu par LABUSE** (centroïde du PPR à x≈0,73 est / y≈0,20 sud = SE,
   2 130 m²). Même aire exclue de la construction, étiquetée EBC par l'archi et PPR inondation/mouvement
   de terrain par LABUSE. **L'ingestion des EBC du GPU est un mandat données à part — non fait ici.**

## Lecture
- **AC0264 colle à l'architecte** : 14 lots = 14, stationnement 28 + 12 visiteurs = identique.
- **AC0261 : LABUSE 10 vs archi 16.** Deux causes, honnêtes : (1) LABUSE **retire 2 130 m² de PPR rouge**
  (R1+R2) que l'architecte n'a pas figurés ; (2) LABUSE dessine une **impasse** conservatrice (le réseau en
  T/croix, essayé, ne fait pas mieux sur cette parcelle allongée) quand l'architecte conçoit un **réseau**
  (2 424 m²) offrant plus de façade donc plus de lots. Le pavage LABUSE est **Estimé** ; l'archi a conçu un plan.
- **Voirie / pleine terre non comparables ligne à ligne** : LABUSE compte la desserte centrale et le
  jardin des lots ; l'architecte compte un réseau complet + tous les espaces verts (privatifs + communs).
  Les deux sont honnêtes dans leur définition — à ne pas additionner entre modèles.
- **EBC** : absent des couches LABUSE → « non vérifié », jamais « absent » (l'architecte en figure un au
  SE). **PPR rouge AC0261** : vu par LABUSE, non par l'architecte — même type de valeur que Saint-Denis.

## Livré
- **Backend** `src/labuse/implantation/lotissement.py` : réutilise `terrain.charger` (assiette, zone U/AU,
  PPR rouge retiré), retire l'EBC, pave en lots le long d'une voirie (`_pave_reseau` : I/T/croix, choix du
  tracé donnant le plus de lots, + aire de retournement d'impasse), tableau des lots,
  voirie, pleine terre (jardins privatifs au CES + communs, **contrôle Réussi/Échoué**), stationnement (UD 12 + visiteurs Estimé), raccordements (MT /
  assainissement, sourcés), régime procédural, note « pas de min-lot (ALUR) », GeoJSON. Service :
  `type_projet == "lotissement"` → `_lotissement_payload` (branche avant le moteur collectif) ; route
  `/modules/etude` inchangée (borne 30 s + message partagés). Rapide (< 2 s).
- **Frontend** `EtudeV6` : résultat lotissement dédié (4 chiffres, plan de division via `PlanMasseSvg` +
  kinds `lot`/`ebc`, tableau des lots, voirie/pleine terre/stationnement/EBC/min-lot/raccordements/régime,
  « logements futurs = hypothèse »). Les T1–T4 saisis = hypothèses de constructions futures, jamais le
  nombre de lots.

## Vérifié
- **tsc 0 · vitest 287/287** (EtudeV6 9, dont le lotissement : voirie en impasse + aire de retournement +
  contrôle pleine terre). **pytest** : `test_etude_v6_lotissement` 3/3 + `test_etude_v6_stationnement` 3/3
  + implantation (1 échec `test_route_etude_*` **pré-existant**).
- **chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP**.
- **Captures** `captures/lotD-ac261-lotissement-v2.png` (10 lots, impasse + retournement, PPR rouge exclu,
  pleine terre Réussi) et `lotD-ac264-lotissement-v2.png` (14 lots).

## Reste
- **Lot E** : PDF depuis le même study_id (verrou chiffres), carte Docs, bilan surfacique clos.
