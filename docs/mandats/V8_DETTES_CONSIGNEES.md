# Dettes consignées — arbitrages B-PRIME (Vic 30/07)

## 1 · Filtrabilité par motif des déclassées écartées (dette produit, lot filtres)
Les 427 parcelles étiquetées déclassées (A/B) qui sont hard-exclues à l'étage 0 sortent en tier
`ecartee` (l'exclusion étage 0 prime sur le déclassement, `assign_tiers` statuts.py:120). VALIDÉ :
leur motif reste servi sur la fiche (`_constructibilite`, indépendant du tier). **Dette** : on perd
la FILTRABILITÉ par motif de déclassement pour ces 427 (elles filtrent comme « écartées », pas
comme « zone fermée »/« inconstructible »). Non-régression — à traiter au **lot filtres**.

## 2 · Golden AT2379 / AI0355 — INDÉTERMINÉS (ne pas ajuster le golden)
Deux ancres golden montrent un résiduel changé dont la justification est INDÉTERMINÉE, car leurs
zones ne sont PAS calibrées (`calibree=False`) :
- **97418000AT2379** (Sainte-Marie, zone U générique 9 m) : résiduel 108 → 146.
- **97424000AI0355** (Cilaos, zone « 86 » → AUst, non calibrée) : résiduel 395 → 209.
Le mouvement vient du recompute résiduel, pas d'un article de règlement. **À reprendre quand ces
zones seront calibrées.** NE PAS ajuster le golden pour les faire passer (les 9 FAIL golden restent
acceptés comme conséquence attendue de la calibration ; cf. V8_VERIF_RAPPORT B.2/B'.2).

## 3 · Saint-Benoît — dette « muettes » requalifiée : 2 743 (pas 21 671)
Sur 21 671 parcelles, 9 671 sans capacité résiduelle : **6 928 en A/N = absence RÉELLE** (non
constructible légitime, PAS une dette) ; **2 743 en U/AU = la vraie dette** « muette en capacité ».
Corrigé à la source (`PLU_NUIT_PHASE4_MESURES.md §7`). **La dette réelle vaut 2 743**, plus jamais
« 21 671 muettes ». (Le « 12 000 capacité renseignée » = 12 238 − 238, rond par coïncidence, pas un
cap — cf. V8_VERIF_RAPPORT B'.3.)

## 4 · Le hard-exclude « déjà bâti » traverse plusieurs mécanismes (à traiter ensemble)
Le signal « déjà bâti » (parcelle déjà construite à N %) intervient dans AU MOINS deux mécanismes
indépendants : (a) l'ÉCARTEMENT cascade (couche `bati`, `faux_positif_probable`) et (b) la DÉTECTION
O12 (`bati_ratio` 0,08-0,45 = prémisse). Ils tirent en sens OPPOSÉ : la cascade veut écarter le bâti,
O12 veut précisément le bâti-avec-résiduel-détachable. **Traiter ENSEMBLE, pas séparément.**
Arbitrage Vic (30/07) : `faux_positif_probable` = probabilité, pas fait → ne jamais écarter O12
dessus (garde restreinte à `status='exclue'`). **Solution cible** : filtre CLIENT + hiérarchisation
par ANNÉE DE CONSTRUCTION (DPE ADEME / BDNB), étiquetée **Sourcé / Absent** — laisser l'utilisateur
juger un bâti récent vs ancien plutôt que le moteur écarter au soupçon.

## 5 · O12 — AUCUN critère de PENTE (dette, à mesurer sur MNT IGN)
O12 ne teste pas la pente du lot résiduel. À La Réunion c'est décisif : un lot de 660 m² à 30 %
de pente n'est pas un lot de 660 m². Revue Vic (30/07) : 6 des 24 candidats sont visiblement sur
versant raide (cartes 4, 11, 15, 20, 21, 24). **À mesurer** : faisabilité d'un critère de pente à
partir du MNT IGN (BD ALTI / RGE ALTI) sur l'emprise du lot proposé — seuil à calibrer.

## 6 · O12 — les indicateurs s'auto-valident sur la famille « lot à découper »
Sur les 17 candidats `decoupe` (algo TRACE lui-même le lot), la compacité converge vers π/4 ≈ 0,785
(carré parfait) et la solidité vers 0,998-1,000 : l'algorithme mesure la qualité de SON PROPRE
tracé, pas celle du terrain. **Ces deux chiffres ne doivent plus être présentés comme indicateurs
de QUALITÉ sur la famille `decoupe`** — seulement sur `libre`/`demolition`, où la géométrie est
celle du terrain réel. (Confirmé : famille `decoupe` compacité ∈ [0,608 ; 0,785], resserrée ;
famille `libre` étalée [0,485 ; 0,770] = vraie variance terrain.)
