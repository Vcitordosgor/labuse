# VERITE-TERRAIN-3 — ERREURS CONFIRMÉES DE LABUSE (V1…V10)

Chaque entrée a été relue cas par cas (jamais déduite d'un agrégat), avec parcelle, numéro de
permis, valeurs, requête de reproduction et verbatim du règlement quand une règle est en cause.
Détail intégral : `relectures/`. Ordre = de la plus grave à la moins grave (impact client ×
fréquence mesurée). Moteur jugé : main `e269abaa0` ; servi : run q_v20 du 21/10/2026.

---

## V1 — Le retrait séparatif FACULTATIF est appliqué comme OBLIGATOIRE (systémique)

**La plus grave.** Le moteur insète systématiquement 3 à 6 m sur TOUTES les limites
séparatives ; or la plupart des règlements de l'île admettent l'implantation **en limite**
(« Soit en limites séparatives… soit en retrait de 3 m »). Sur une parcelle étroite
(7-17 m de large), l'assiette s'effondre ou se vide → faux « terrain trop exigu » ou capacité
dérisoire, alors que des maisons y sont réellement accordées et construites.

- Preuves (verbatims en table `plu_reglement_extrait`, cités dans
  `relectures/TEST2-RELECTURE-40.md` et `TEST1-RELECTURE-2.md`) : Saint-Louis UC 7.2 p.45
  (« peuvent être implantées sur une seule limite latérale »), Saint-Pierre Ug3 p.101-102 et
  Uf3 (« Soit en limites séparatives … Soit en retrait de 3 mètres »), Cilaos Ub 7.2 p.35,
  Sainte-Suzanne U5.2 p.13, Le Port Uc 5 p.54 et Ub 5 p.38 (implantation sur les DEUX limites
  imposée aux terrains ≤ 12 m), Saint-Denis Um.7 p.67, Saint-Joseph U3 7.2 p.48, Trois-Bassins
  Uc 7.2 p.44, Saint-Paul U4b/c 7.2 p.173, Sainte-Rose UC 7.2 p.31, Salazie UC7, Saint-Leu
  UB7/UD7 (« Si … en retrait … 3,00 m »).
- Fréquence mesurée : **33 des 40** plus forts dépassements d'enveloppe du Test 2 ; **4** des
  16 erreurs du Test 1 ; explique l'essentiel des **71 « terrain_exigu »** restants du défaut
  VT-2 et pèse dans les **798 ventes « terrain à bâtir » en zone U** fermées pour exigu (LOT 5).
- Contre-épreuve (Test 2) : enveloppe recalculée au CES du règlement → le dépassement disparaît
  (ratios 0,13-1,12).
- Cause dans le code, DEUX étages prouvés :
  1. ancien : `faisabilite/engine.py` applique `recul_limites_sep_m` comme un minimum dur ; le
     drapeau `recul_limites_alignement` (implantation en limite, recul 0 sourcé) existe mais
     n'est posé dans AUCUN des YAML des zones concernées ;
  2. **régression du 31/10** : commit `3cf76e039` (FAISA-REGLES-1 D-024),
     `gabarit/builder.py` l.273-290 — le retrait devient « H/2 min 3 m » avec H = **faîtage
     maximal de la ZONE**, sur toutes les limites, alors que les règlements définissent H comme
     la hauteur À L'ÉGOUT de la **façade concernée** et n'exigent le retrait qu'« en cas de
     retrait ». Reconstruction numérique exacte (relecture VT-2) : La Possession UA, parcelle
     AO1919 — octobre inset 3 m → 564 m² ; novembre recul 8 m (=16/2) → 73 m². **19 permis
     réels couverts en octobre ne le sont plus** (La Possession, Saint-Joseph, Bras-Panon,
     Sainte-Rose…) ; millésimes PLU et YAML INCHANGÉS (git diff vide) — c'est le code.
- Cas types : 97441313A0107 / 97413000CY1217 (maison 91 m² accordée et bâtie, parcelle vidée
  par l'inset −3 m) ; 9744072500021 / 97407000AL1652 (Ub Le Port, 166 m² servis
  « terrain_exigu » là où le règlement IMPOSE la limite) ; 97409000BI0220 (UB Saint-André,
  5 logements achevés, inset règlementaire laisse 57,7 m² non vides).
- Traces rejouables : `relectures/_v1_moteur.json`, `_v1_setbacks.json`.

## V2 — Le stock servi (run du 21/10) n'a pas été rejoué après les correctifs : le client
voit encore des verdicts que le moteur ne produit plus

- Sur la cohorte H, **263 permis** restent « fermés » au classement servi alors que le moteur
  de main les ouvre (92 AU « générique », 88 declasse_non_constructible, 39 zone fermée,
  20 terrain_exigu, 13 rédhibitoire) : Test 1 servi 90,8 % contre moteur 96,3 %.
- Cas prouvés en relecture : 97406000AW0822 (Ur, 3 294 m²) servi `terrain_exigu`/0 m² quand le
  moteur du jour rend « assiette à vérifier » ; 97403000EM0999, 97404000BN1868 (moteur : 33 m²,
  bande D — servi : 0), 97407000AE0479 (Ub 246 m², inset laisse 92 m²).
- Requête de reproduction : `SELECT r.cause, r.sdp_residuelle_m2 FROM parcel_residuel r JOIN
  parcels p ON p.id=r.parcel_id WHERE p.idu='97406000AW0822';` → `terrain_exigu | 0` à comparer
  au cache moteur `cache/capacite/97406000AW0822.json` (`assiette_a_verifier`).
- Gravité : c'est TOUT l'écart moteur/servi des tests — les correctifs CAPACITE-1/EXIGU-FIX
  n'atteignent pas le client tant qu'aucun run n'est rejoué et basculé.

## V3 — Les secteurs d'habitat de la zone agricole (Aba/Arh…) sont calibrés dans les
destinations mais le moteur de capacité ne les lit pas

- Le règlement ADMET l'habitat neuf plafonné dans ces secteurs : Salazie A2 2.2-7 p.41-42
  (150 m²), Le Tampon A2 2.2-6 p.92-93 (120 m²), Trois-Bassins A2.2 (8.) p.75 (120 m²) ;
  `config/plu_destinations/*.yaml` le modélise (`logement: sous_condition`, seuils 120/150) —
  mais `resolve_zone` n'a pas de feuille d'enveloppe pour ces secteurs → famille A →
  « Construction neuve non autorisée ».
- 5 permis relus, TOUS sous le seuil réglementaire : 97442122A0074 (146 ≤ 150),
  9744212500022 (117), 9744212600010 (113), 9744222600036 (115 ≤ 120), 9744232600011 (77 ≤ 120).
- S'y ajoutent, mêmes preuves verbatim (relecture VT-2, volet 2) : Saint-Benoît **Ns21/Ns34/
  Ns46** (N-2 p.42 : construction neuve d'habitation ADMISE dans les hameaux Ns, CES 70 %
  p.46), Salazie **Aba** ×2 (A2 p.41, ≤ 150 m² — permis de 75 et 91 m²), Saint-André **Aba**
  (A2.2 (11) p.106, ≤ 120 m²). Divergence de relecture consignée : la moitié 1 du Test 1 a
  classé 14 permis Ns 2020-2021 en « exception légale » (caducité ELAN invoquée) — le verbatim
  du règlement EN VIGUEUR admettant l'habitat, les cas postérieurs aux règles actuelles sont
  retenus ici comme règle non lue ; les deux lectures sont dans `CAS.csv`.
- Même famille que le « C4 règle existante non ingérée » de CAPACITE-1 ; ici la règle est DÉJÀ
  dans la config (`sous_condition`), seule la lecture par le moteur de capacité manque.

## V4 — Un échec de géométrie (« assiette à vérifier ») est servi comme un NON ferme

- Quand le moteur ne parvient pas à établir l'assiette, il rend `assiette_a_verifier`
  (ignorance) — mais ce verdict compte comme « non constructible » dans le potentiel et, au
  servi périmé, comme `terrain_exigu` certain (bande « Non retenue », jamais « Analyse
  incomplète »).
- Cas : 97440623A0040 / 97406000AD0854 (Uc, 425,8 m², B3 100 %, aléa faible : AUCUNE contrainte
  opposable, servi « non constructible ») ; 97406000AW0822 (3 294 m², idem).
- Les correctifs « ignorance ≠ verdict » (EXIGU-FIX-1, C3-04) couvrent le Score mais pas la
  lecture « potentiel à bâtir »/Test 1, et le stock servi antérieur n'est pas rejoué (V2).

## V5 — Saint-André UB : le recul sur voie MAXIMUM (≤ 6 m) est modélisé comme un MINIMUM

- UB 6 p.27 : « la façade principale ne doit pas être implantée **au-delà** d'une marge de
  recul de 6 mètres » = la maison doit être À MOINS de 6 m de la voie. LABUSE l'applique comme
  un retrait obligatoire de 6 m, qui ampute l'avant de chaque parcelle.
- Touche les 7 cas UB du Test 2 (lotissement section BD, permis du 22/11/2019) et le cas
  97440921A0264 / 97409000BI0220 du Test 1 (5 logements construits, DAACT 23/05/2024 ; en plus
  UB 7 admet la limite séparative).

## V6 — PPR : une touche partielle de zone rouge ferme TOUTE la parcelle

- 97440624A0002 / 97406000AD0863 (Uc) : « couverte par le PPR en zone rouge » servi alors que
  le rouge (R1) ne couvre que **9,1 %** de la parcelle (B3 prescriptif 90,9 %). Permis accordé.
  SQL de reproduction dans `relectures/TEST1-RELECTURE-1.csv`.
- L'override « PPR partiel » existe (potentiel_batir `_override_ppr_partiel`) mais n'a pas
  joué ici — à instruire : seuil de déclenchement / données de parts.

## V7 — Bande prospective « trait de côte » traitée en interdiction rédhibitoire

- 97441021A0161 / 97410000BX0750 (Ua, Saint-Benoît) : la couche prospective de recul du trait
  de côte (−0,192 m/an) couvre 100 % de la parcelle → facteur 0 « rédhibitoire »
  (`faisabilite/engine.py` ~l.840-848) malgré 347 m² d'emprise R+2. La maison est ACHEVÉE
  (DAACT 17/07/2025). Une projection d'érosion n'est pas une servitude d'interdiction.

## V8 — SUP AC2 (sites inscrits / abords) déduite comme inconstructible totale

- `gabarit/builder.py:477` soustrait les périmètres ac1/ac2 de l'assiette ; 97413000CY1293 perd
  **83 %** de sa surface au titre de l'AC2 « LA POINTE AU SEL » — régime d'AVIS (ABF), pas
  d'interdiction de construire.

## V9 — Faux « hors PLU » sur trou de la couche de zonage

- 97441315A0075 / 97413000DE2186 (Saint-Leu) : parcelle bâtie (4 bâtiments, 103 m²) rue
  Félicien Hibon, à 23 m d'un polygone UC — le zonage DU_97413 (2007) a un trou ; « hors PLU
  outillé » est matériellement faux. 3 cas « hors_plu » dans les 180 « non » du Test 1 ; le
  gate servi compte en outre ces ignorances (`hors_plu`, `zone_non_resolue`) comme « fermées ».

## V10 — Contradiction interne AU « générique » : SDP servie positive, gate fermé sans cause

- 97415000CD0898 : `parcel_residuel` sert 168 m² de SDP SANS cause, mais le gate ferme la
  parcelle par la classe AU « générique » (zone AUb19 non calibrée) → le client voit « rien à
  bâtir » et une capacité positive selon l'écran. (LOT 5, relecture.) Les 92 « générique » de
  l'écart moteur/servi du Test 1 relèvent du même mécanisme.

---

## Sous le seuil d'« erreur » mais à suivre (mesuré, relu)

- ~~21 régressions « nouveaux millésimes PLU »~~ : hypothèse RÉFUTÉE en relecture — 19/21 sont
  l'étage 2 de **V1** (commit D-024 du 31/10), 2 sont des découpes PPR correctes
  (Plaine-des-Palmistes AP0422 41,5 % en zone d'interdiction mesurée, Saint-Louis CH1877).
- **Le Tampon 2AUc** : 6 permis neufs 2024-2026 dans une zone que le règlement au GPU (2023)
  dit subordonnée à ouverture — signal d'une modification non répercutée au GPU, pas une
  erreur LABUSE (décalage de source).
- **Barème du Score sévère sur petites parcelles bâties en limite** (LOT 4) : 10/30 permis
  réels sous-classés avec SDP résiduelle < autorisé (×1,2 à ×11) — conséquence directe de V1
  pour l'essentiel.
