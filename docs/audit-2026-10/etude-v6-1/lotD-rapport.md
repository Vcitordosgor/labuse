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

## Tableau LABUSE / architecte — AC0261

| Poste | LABUSE | Architecte (OCEANIS) |
|---|---|---|
| Nombre de lots | **11** | **16** |
| Surface moyenne | 430,4 m² | ~450 m² (lots 400–450) |
| Surface minimale | 303,9 m² | 400 m² |
| Voirie | **574,9 m²** (desserte unique 6 m) | principale 1 609,84 + secondaire 814,26 = **2 424 m²** |
| Places | 22 (2/lot, UD 12) + 9 visiteurs (Estimé) | 32 (2/lot) + 13 visiteurs |
| Pleine terre | exigée **4 442,8 m²** (40 %, UD 13) · estimée 2 840,9 | privatif 7 011,61 + commun 2 391,98 = 9 403 m² |
| EBC | **non trouvé dans les données LABUSE** (à vérifier) | présent au SE |
| PPR rouge | **2 129,7 m² retiré** de l'assiette (R1+R2) | **non figuré** |
| Règle PLU surface/largeur min de lot | **aucune** (loi ALUR) | — |
| Raccordements | électricité (MT) 0 m · assainissement 4 168 m → autonome | — |
| Régime | **Permis d'aménager** (>2 lots + voirie) — à qualifier | — |

## Tableau LABUSE / architecte — AC0264

| Poste | LABUSE | Architecte (OCEANIS) |
|---|---|---|
| Nombre de lots | **14** | **14** ✓ |
| Surface moyenne | 435,3 m² | ~450 m² |
| Surface minimale | 357,4 m² | 400–450 m² |
| Voirie | **830,6 m²** (desserte unique 6 m) | principale 1 519,14 + secondaire 4 466,26 |
| Places | **28** (2/lot) + 12 visiteurs | **28** (2/lot) + **12** visiteurs ✓ |
| Pleine terre | exigée 3 991,6 m² (40 %) · estimée 3 656,5 | privatif 5 313,16 + commun 3 085,82 = 8 399 m² |
| EBC | non trouvé (à vérifier) | — |
| PPR rouge | 0 | — |
| Règle min-lot | aucune (ALUR) | — |
| Régime | Permis d'aménager — à qualifier | — |

## Lecture
- **AC0264 colle à l'architecte** : 14 lots = 14, stationnement 28 + 12 visiteurs = identique.
- **AC0261 : LABUSE 11 vs archi 16.** Deux causes, honnêtes : (1) LABUSE **retire 2 130 m² de PPR rouge**
  (R1+R2) que l'architecte n'a pas figurés ; (2) LABUSE pave le long d'**une seule voirie** (575 m²)
  quand l'architecte dessine un **réseau** (2 424 m²) qui offre plus de façade donc plus de lots. Le
  pavage LABUSE est **conservateur** (Estimé) ; l'architecte a conçu un plan.
- **Voirie / pleine terre non comparables ligne à ligne** : LABUSE compte la desserte centrale et le
  jardin des lots ; l'architecte compte un réseau complet + tous les espaces verts (privatifs + communs).
  Les deux sont honnêtes dans leur définition — à ne pas additionner entre modèles.
- **EBC** : absent des couches LABUSE → « non vérifié », jamais « absent » (l'architecte en figure un au
  SE). **PPR rouge AC0261** : vu par LABUSE, non par l'architecte — même type de valeur que Saint-Denis.

## Livré
- **Backend** `src/labuse/implantation/lotissement.py` : réutilise `terrain.charger` (assiette, zone U/AU,
  PPR rouge retiré), retire l'EBC, pave en lots le long d'une voirie centrale (`_pave`), tableau des lots,
  voirie, pleine terre (UD 13), stationnement (UD 12 + visiteurs Estimé), raccordements (MT /
  assainissement, sourcés), régime procédural, note « pas de min-lot (ALUR) », GeoJSON. Service :
  `type_projet == "lotissement"` → `_lotissement_payload` (branche avant le moteur collectif) ; route
  `/modules/etude` inchangée (borne 30 s + message partagés). Rapide (< 2 s).
- **Frontend** `EtudeV6` : résultat lotissement dédié (4 chiffres, plan de division via `PlanMasseSvg` +
  kinds `lot`/`ebc`, tableau des lots, voirie/pleine terre/stationnement/EBC/min-lot/raccordements/régime,
  « logements futurs = hypothèse »). Les T1–T4 saisis = hypothèses de constructions futures, jamais le
  nombre de lots.

## Vérifié
- **tsc 0 · vitest 286/286** (EtudeV6 9, dont le lotissement). **pytest** : `test_etude_v6_lotissement`
  3/3 + `test_etude_v6_stationnement` 3/3 + implantation (1 échec `test_route_etude_*` **pré-existant**).
- **chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP**.
- **Captures** `captures/lotD-ac261-lotissement.png` (11 lots, PPR rouge exclu) et
  `lotD-ac264-lotissement.png` (14 lots, tableau complet).

## Reste
- **Lot E** : PDF depuis le même study_id (verrou chiffres), carte Docs, bilan surfacique clos.
