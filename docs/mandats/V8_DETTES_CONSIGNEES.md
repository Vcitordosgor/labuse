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

## 7 · Statut d'OUVERTURE des zones AU non gravé (PRIORITAIRE — dépasse O12)
Les YAML calibrent les DIMENSIONS des zones AU (hauteur, emprise, reculs — Art. 9/10/13) mais PAS
leur statut d'OUVERTURE (Art. 1/2 : ouverte / subordonnée à modification-OAP). Conséquence : toute
AU dotée d'articles chiffrés est servie constructible sans que son ouverture ait été lue.
**Mesure (run servi q_v7_defisc, 24 communes)** :
- **187 zones AU distinctes servies** ; ouverture DOCUMENTÉE 106, **NON documentée 81**.
- **6 636 parcelles servies en AU à ouverture NON documentée** (3 829 génériques + 2 807 « calibrées
  dimensions seules »), dont **420 EN TÊTE DE LISTE : 12 brûlantes, 172 chaudes, 236 réserve**.
- Risque de faux positif du même ordre que la brûlante 2AUd rattrapée le 29/07, à l'échelle.
**À intégrer au mandat de calibration** : extraire SYSTÉMATIQUEMENT l'Article 1/2 (caractère /
ouverture) des zones AU, pas seulement les articles dimensionnels. Tant que non fait, la garde
O12 « AU fermée = 2AU » ne peut pas distinguer ouverte/fermée sur ces 81 zones.

## 8 · L'ortho voit des contraintes que la cascade ne capte pas
Revue Vic (30/07) : la ravine SE de la carte 16 (97412000CS0625) et le risque mouvement de terrain
de Cilaos (carte 8, 97424000AE0089) sont VISIBLES à l'ortho mais **absents des exclusions cascade**
(seul « aléa mvt terrain FAIBLE » soft, aucune exclusion PPR/ravine). La détection géométrique et la
cascade ne captent pas tout ce que l'œil voit sur l'ortho. **Dette** : croiser systématiquement les
candidats servis avec une revue ortho (ou enrichir les couches ravine/aléa) avant exposition.

## 9 · Le tier est un percentile → un déclassement de masse promeut des brûlantes « par héritage de place »
Consigné sur arbitrage Vic (30/07). **La brûlante est un top-décile, donc un quota FIXE.** Retirer
en masse des parcelles de la tête (ici : déclassement des génériques AU) libère des places que des
parcelles-LIMITES remontent occuper — sans avoir rien gagné en signal propre. Cas mesuré :
**AR1423** (Entre-Deux, U) passe chaude→brûlante alors que son contrib_d (1,7468), son rang (27) et
son absence d'événement sont IDENTIQUES avant/après ; seul le seuil top-décile a glissé de 0,005 et
son D est tombé dedans (cf. V8_VERIF_RAPPORT). Mécanisme général, pas un cas isolé : sur les **139
backfills** de la mesure AU-OUVERTURE, une part est de ce type.
- **À mesurer au VRAI re-run post-calibration** : combien des backfills sont des montées « par
  héritage de place » (signal propre inchangé, seul le seuil bouge) vs « par mérite » (signal qui
  progresse). Instrument possible : comparer, pour chaque parcelle qui gagne un tier, son contrib_d
  et son rang AVANT/APRÈS — inchangés ⇒ héritage, en hausse ⇒ mérite.
- **Exigence de conception** : le distinguo « brûlante par mérite / par héritage de place » doit
  EXISTER quelque part. Une brûlante qui n'a hérité que d'une place vacante n'est pas de même nature
  qu'une brûlante dont le signal a monté — les servir à l'identique, sans trace, masque un effet de
  bord du quota. **Préférence Vic (30/07), non tranchée définitivement** : ça relève de la **FICHE,
  pas du log**. « Un pro qui voit une brûlante mérite de savoir si elle est montée parce qu'elle
  s'est améliorée ou parce qu'une place s'est libérée. C'est une information sur la PARCELLE, pas
  sur le run. » Décision finale au re-run.

## 10 · EBC / emplacements réservés : géo-joints mais ni cascade ni drapeau de fiche
Consigné sur arbitrage Vic (mandat GPU-PILOTE, 30/07). Les prescriptions bloquantes du PLU sont EN
BASE avec leur géométrie (`plu_gpu_prescription`) mais ne servent à rien côté produit : ni maillon de
cascade, ni signal de fiche. Mesuré à L'Étang-Salé : **EBC** (`typepsc 01`, 30 objets), **ER**
(`typepsc 05`, 15 objets). 3 958 parcelles intersectent un bloquant, dont 16 servies en tête.
- **Nuance retenue (Vic)** : intersecter ≠ être inconstructible. Un EBC/ER PARTIEL laisse du
  constructible. Donc **pas d'exclusion cascade automatique** sur la seule intersection.
- **Dette** : ces objets doivent apparaître comme **DRAPEAUX de fiche** — « parcelle partiellement
  en EBC », « emplacement réservé n°X » — pour que le professionnel le SACHE et vérifie. Information
  d'aide à la décision, pas un verdict. La donnée existe (géométrie + `typepsc/txt/libelle`) ; il
  manque le croisement par parcelle et l'affichage. **NON implémenté** (arbitrage Vic : consigner,
  pas coder). Cf. `docs/mandats/GPU_PILOTE_PHASE2_EXTRACTION.md`.

## 11 · Assemblage : la contiguïté géométrique ne dit rien de l'ACQUÉRABILITÉ
Consigné sur arbitrage Vic (GPU-PILOTE, 30/07). Le statut `au_sous_plancher` sert une parcelle « trop
petite seule » comme candidate à l'assemblage, avec le nombre de voisines CONTIGUËS de même zone qui
atteindraient le seuil (mesuré : 399/708 sous-seuil assemblables, 66 % des têtes). **Mais la
contiguïté est GÉOMÉTRIQUE — elle ne dit rien de l'acquérabilité.**
- **Prochaine couche** : croiser les voisines avec la PROPRIÉTÉ (DGFiP / personnes morales).
- **Distinguer** : « MÊME propriétaire » (division simple, sans négociation) vs « propriétaires
  DISTINCTS » (assemblage à négocier). **Le premier cas vaut beaucoup plus cher** (constructible
  immédiatement par simple division du foncier détenu).
- **Mesurer PLUS TARD** (Vic), pas maintenant. Tant que non fait, `au_sous_plancher` ne distingue pas
  les deux : la mention dit « assemblage possible » sans dire s'il est gratuit (même proprio) ou à
  négocier. Cf. `docs/mandats/GPU_PILOTE_MESURE_PLANCHERS.md`.

---

# MàJ RE-RUN (Vic, 04/08) — revue des 19 têtes entrantes

## 9 (suite) · Mérite / héritage — MESURÉ et TRANCHÉ
Re-run 04/08 (candidat `q_v9_apres` vs servi `q_v7_defisc`). Sur les 11 nouvelles brûlantes :
**2 par MÉRITE** (`p_raw` en hausse : 97424 AM0894 Cilaos 0,0534→0,0696 ; 97408 AM0989 0,0534→0,0677),
**9 par SEUIL** (`p_raw` STRICTEMENT inchangé — promues par l'abaissement du seuil brûlante 1,544→1,412).
Côté correctif AU isolé, les 153 backfills Saint-Benoît sont TOUS par héritage (rang inchangé).
Mécanisme confirmé et DOMINANT. **Décision Vic (04/08)** : le distinguo mérite/héritage doit figurer
sur la **FICHE** — acté comme **exigence de la PROCHAINE itération**, PAS du re-run 04/08 ; ne bloque
pas la bascule.

## 4 (suite) · Angle mort `batiment` — cas mesuré CH1893 (dette #4 en direct)
Q2 du re-run (04/08). Le modèle n'a **aucune feature d'emprise bâtie AU NIVEAU PARCELLE** : le bâti
n'entre que via `sdp_residuelle_m2` / `nu_constructible` (résiduel = plafond zone − bâti détecté) et
la densité de SECTEUR. **Dépendance unique à la complétude de la couche `batiment`, sans garde-fou.**
Cas mesuré : **97414 CH1893** (Saint-Louis, servie brûlante rang 1034) — OCS `Bâti 100 %`, un toit
NETTEMENT visible à l'ortho DANS la parcelle, mais la couche `batiment` ne capte que 2,4 % → `sdp_
residuelle` faussement à 135 m² → servie à l'aveugle. **À retirer/flaguer** avant exposition.
- **Piste de garde** : croiser `sdp_residuelle` avec l'OCS `Bâti`. MAIS l'OCS n'est PAS fiable seule —
  contre-exemple mesuré **97415 AY1608** : OCS `Bâti 100 %` alors que l'ortho montre de la VÉGÉTATION
  (couche `batiment` correcte à 0 %). L'OCS sur-classe. → croisement à valider À L'ŒIL, pas automatique.

## 12 · Le score ignore l'ampleur du manque de surface d'un `au_sous_plancher` (NOUVEAU)
Q1 du re-run (04/08). Un `au_sous_plancher` reçoit son rang de modèle PLEIN ; le ratio
`surface_manquante / seuil_opération` n'a **aucun effet** sur le score. Mesure (candidat `q_v9_apres`) :
**388 `au_sous_plancher` servis en tiers de tête**, dont au SOMMET de l'île —
**97423 AB1908 (313 m², manque 81 %) = brûlante RANG 1**, AB1910 (85 %) rang 4, AB1911 (89 %) rang 6 ;
97413 CX2555 (195 m², manque **94 %**) brûlante rang 1034. Une parcelle constructible seulement en
acquérant 16× sa surface n'est pas la 1034ᵉ opportunité de l'île — **la mention dit vrai mais le rang
ment**.
- **Proposition (Vic : proposer, ne pas coder)** : pondérer le statut par un facteur de complétude
  `c = surface_parcelle / seuil_opération ∈ ]0,1]`. Un manque de 10 % (`c≈0,9`) ne pénalise presque
  pas ; un manque de 94 % (`c≈0,06`) rétrograde fortement. Trois designs possibles :
  (a) **multiplicatif** `p_eff = p_raw × c^k` (k à calibrer) avant l'assignation de tier ;
  (b) **plafond de tier** : `c < 0,5` ⇒ tier plafonné à `a_creuser`, `c < 0,25` ⇒ `reserve_fonciere` ;
  (c) **exclusion de la brûlante** si `c < seuil` (le plus simple, le plus brutal).
  Recommandation : (b) — lisible, réversible, borne le pire sans effacer le signal. `c` déjà calculable
  (`seuil_surface_m2` existe dans `au_ouverture.py`). **À arbitrer, non codé.**
- **En attendant (arbitrage Vic 04/08)** : **CX2555 retenue en `chaude`**, pas exposée en brûlante.
