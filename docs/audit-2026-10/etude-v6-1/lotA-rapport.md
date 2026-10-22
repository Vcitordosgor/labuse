# ÉTUDE V6 — Lot A : le parcours en 3 étapes

Branche `feat/etude-v6`. Le parcours remplace la config monolithique de M22 dans l'overlay Docs
(`EtudeEcran` monte désormais `EtudeV6`). M22 reste pour son mode outil non-embedded et ses tests.

## Livré
- **Backend** `src/labuse/implantation/assiette.py` + route `POST /modules/etude/parcelles` (modules.py) :
  validation d'assiette AVANT le moteur (rapide, ~60 ms). Faits par parcelle (commune, référence,
  contenance = surface de référence, surface réelle + écart, zone PLU, qualité géométrique), union
  (surface réelle, périmètre, aire cadastrale, écart), **contiguïté par GRAPHE** (frontière partagée
  > 0,5 m — jamais un sommet, jamais les centroïdes ; composantes connexes ; réévaluée à chaque appel),
  signaux (communes/zones/ravine, propriétaires présumés = « non vérifié » si absent), sources +
  millésimes (data_sources). Ne conclut jamais sur la constructibilité.
- **Moteur T1** : `TYPES_LOGEMENT` = (T1,T2,T3,T4) + module `T1` (28 m², 1 pièce, Estimé) dans
  `config/implantation_conventions.yaml` (additif — T2/T3/T4 et repartition_equilibre inchangés).
- **Frontend** `EtudeV6.tsx` (3 étapes + récap + résultat base) ; `api.ts` `postEtudeParcelles` ;
  `EtudeEcran` monte EtudeV6. Réutilise ParcelInput (sans carte), Bouton, Badge, PlanMasseSvg, tokens
  noir/vert (aucun jeton nouveau). ① Parcelles (recherche adresse/IDU/réf, 1–8, faits + contiguïté +
  refus clair + signaux + sources, **sans carte**) ② Type (4 choix texte, **aucune présélection**, note
  stationnement à vérifier) ③ Programme (T1–T4 +/−, totaux directs, « jamais SDP ») → « Analyser mon
  projet ». Récap droite (terrain / projet / logements / surface / **Stationnement PLU = Non vérifié**).
- Boutons « · bientôt » **supprimés** ; verdict résultat = « Exploitable sous hypothèses ».

## Vérifié
- **tsc 0 · vitest 283/283** (dont `EtudeV6.test.tsx` 5, `EtudeDocs.test.tsx` recâblé 6).
- **pytest** : `test_etude_v6_assiette.py` 11/11 (8 contiguïté pure = acceptation 1–4 + 3 reel) ;
  implantation2/pareto inchangés (1 échec `test_route_etude_*` = **pré-existant**, DB `labuse_test` vide).
- **chasse_docs 20 OK · 0 ECART** (E-18/E-19/E-20 préservés). **chasse_donnees 21 OK · 2 ECART · 2 SKIP**
  = ECART `cloche-fraicheur`/`digest-vs-cloche` **PRÉ-EXISTANTS** (cloche q_v20 vs servi q_v19,
  detect-events = geste PROD refusé) ; SKIP = export 500 pré-existants. Aucun lié au Lot A.
- **Bout-en-bout navigateur** (captures `captures/lotA-01..04`) : étape 1 (AW99 contenance 501/réelle
  504,3/écart +3,3, AW451 « géométrie irrégulière », récap 1 744,2 m²) · étape 2 (4 types, note
  stationnement sur « senior ») · étape 3 (**10×T1 = 300,0 m² dont 60,0 varangues / 240,0 intérieur** =
  acceptation 8) · résultat (Scénario A barre, Exploitable sous hypothèses, 40 T1, SDP 1 360, plan masse).

## Acceptation mandat (Lot A)
6 (3 étapes, pas de carte) ✓ · 7 (4 choix sans icône, pas de présélection, T1–T4) ✓ · 8 (10×T1=300 dont 60,
jamais SDP) ✓ · 1–4 contiguïté (tests purs) ✓ · refus non-contigu avec message ✓.

## Reste (lots suivants)
- **Lot B** : résultat « qui explique » (Votre demande → ce que le terrain accueille → écart → facteurs
  limitants → alternative), 3 variantes, 4 grandeurs séparées, 5ᵉ état « À confirmer », pont Bilan.
- **Lot C** : règle de stationnement réelle par type (article/version/unité/exceptions/état).
- **Lot D** : lotissement = division-or sur l'assiette (actuellement mappé collectif).
- **Lot E** : PDF depuis le même study_id, carte Docs, bilan surfacique clos.
