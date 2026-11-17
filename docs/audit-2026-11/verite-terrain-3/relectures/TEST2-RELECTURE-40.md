# TEST2 — Relecture des 40 dépassements d'enveloppe (aut_plancher > 1,10 × enveloppe LABUSE)

Audit VERITE-TERRAIN-3, lecture seule. Date : 2026-11-15.
Entrée : `cohortes/TEST2-DEPASSEMENTS-40.csv`. Sortie détaillée : `TEST2-RELECTURE-40.csv`.

Méthode : pour chaque cas, re-calcul `labuse.faisabilite.db.parcel_faisabilite` (steps) +
`gabarit.builder/engine` (setbacks par côté, exclusions, plafond CES) ; confrontation au
règlement via `plu_reglement_extrait` (verbatim DB) et, quand la commune est absente de la
table (97413 Saint-Leu, 97409 Saint-André, 97405 art. 7), aux citations calibrées des YAML
`config/plu_destinations/` (article + page PDF).

## Décompte

| Classement | n |
|---|---|
| erreur_labuse | 34 |
| decalage | 3 |
| indetermine | 2 |
| donnee_permis_douteuse | 1 |
| **Total** | **40** |

## Erreur LABUSE n° 1 (systémique, 33 des 34 cas) — le retrait séparatif FACULTATIF est appliqué comme OBLIGATOIRE

Dans tous les cas, l'étape bornante de l'enveloppe est « Emprise au sol — reculs »
(`min(reculs, CES)` = reculs partout ; le plafond CES est 5 à 30 fois au-dessus).
Le moteur insète le contour de 3 à 6 m sur TOUTES les limites (voie + séparatives + fond) ;
sur ces parcelles étroites (largeur inscrite 7 à 17 m), la zone d'implantation s'effondre
à 6–90 m². Or les règlements offrent explicitement l'alternative « en limite séparative »,
que le moteur ignore (le flag `recul_limites_alignement` existe dans l'engine mais n'est posé
dans aucun YAML concerné).

Verbatims (base `plu_reglement_extrait`, sauf mention YAML) :

- **Saint-Louis UC 7.2, p. 45** : « Les constructions peuvent être implantées sur une seule
  limite latérale. En cas de retrait […] au moins égale 3 mètres. » ; 7.3 (fond) :
  « L'implantation en limite est possible dès lors que la nouvelle construction n'excède pas
  4 mètres de hauteur ».
- **Saint-Pierre Ug3 2/, p. 101-102** : « Les constructions nouvelles doivent être implantées :
  Soit en limites séparatives et au maximum sur 2 limites séparatives […] Soit en retrait de
  3 mètres. » (idem Uf3.2 p. 117, citation YAML).
- **Cilaos Ub 7.2, p. 35** : « peuvent être implantées sur une seule des deux limites
  séparatives ou sur les deux limites si la largeur sur voie […] est inférieure à 20 mètres ».
- **Sainte-Suzanne U5.2, p. 13** : « En zones UA et UB, la construction peut être implantée
  sur les deux limites latérales, sur une seule ou en retrait. » (et U7 p. 14 : emprise au sol
  « Sans objet »).
- **Le Port Uc 5, p. 54** : « peuvent être implantées soit en limite séparative, soit en
  retrait. En cas de retrait […] au moins égale à 4 mètres. »
- **Saint-Denis Um.7, p. 67** : « Chaque construction pourra s'implanter sur 1 ou 2 limites
  séparatives sur une longueur maximale de 10 m par limite. »
- **Saint-Joseph U3 7.2, p. 48** : « peuvent être implantées sur les deux limites séparatives,
  sur une seule ou en retrait. »
- **Trois-Bassins Uc 7.2, p. 44** : « Chaque construction peut s'implanter sur une limite
  séparative. »
- **Saint-Paul U4 7.2, p. 173 (zones U4b/U4c)** : « Les constructions pourront s'implanter sur
  une limite séparative sur une longueur maximale de 10 m. »
- **Sainte-Rose UC 7.2, p. 31** : « peuvent être implantées en retrait ou : sur les deux
  limites séparatives latérales pour les terrains dont la largeur sur voie ≤ 12 mètres ».
- **Saint-Leu (YAML, commune absente de la table)** : citation calibrée art. 7 (UD p. 52,
  UB p. 32, UA p. 22) : « **Si** une construction est implantée **en retrait** des limites
  séparatives […] la marge d'isolement minimale doit être de 3,00 m » — formulation
  conditionnelle ; le même règlement, art. UC 7 p. 42, dit : « Les constructions peuvent être
  implantées sur une limite séparative (ou les deux, si celles-ci sont distantes de moins de
  18 mètres l'une de l'autre) ».
- **Saint-André (YAML, commune absente de la table)** : citation calibrée art. 7 (UB p. 27,
  UC p. 39, UD p. 50) : « **En cas de retrait** de la construction […] au moins égale 3
  mètres » — conditionnelle.

Contre-épreuve chiffrée : en recalculant l'enveloppe avec l'emprise plafonnée par le CES du
règlement (au lieu des reculs) et une tolérance combles (+0,5 niveau pour les zones
« R+combles »), 33 des 34 cas classés erreur_labuse retombent sous ou autour du plancher
autorisé (ratio corrigé 0,13 à 1,12, le reliquat étant dans le bruit de la conversion
surf_hab × 1,15).

## Erreur LABUSE n° 2 — Saint-André UB : le recul voie « 6 m » est un MAXIMUM lu comme un MINIMUM

Citation calibrée (YAML 97409, UB 6, p. 27) : « Toutefois, la façade principale de la
construction ne doit **pas** être implantée **au-delà** d'une marge de recul de 6 mètres
parallèle à la limite de la voie » — c'est une obligation de proximité (recul maximal 6 m),
modélisée `voie.min_m = 6.0` et appliquée par le moteur comme un recul minimal de 6 m.
Règle inversée, aggrave l'effondrement sur les 6 parcelles UB de la section BD (lotissement,
permis du 22/11/2019) + BH0425.

## Erreur LABUSE n° 3 — SUP AC2 (site inscrit) traitée comme exclusion totale

`gabarit/builder.py` (l. 477) : « les autres SUP (ac1/ac2/ac3/ac4 monuments·sites, el10,
pm2/pm3) restent des exclusions réelles » — la servitude **AC2 « LA POINTE AU SEL »**
(typeass « Enceinte du site ») est découpée de la zone d'implantation comme si elle était
inconstructible. Une AC2 (protection des sites et monuments naturels) impose un régime
d'avis/déclaration, pas une interdiction de construire.
Cas : **97413000CY1293** (83 % de la parcelle déduits, permis 2014 pour 110 m² hab) ;
contribue aussi à 97413000CY1189.

## Cas non imputables à une règle LABUSE

### decalage (3)
- **97440920A0227 / 97409000BM1098** (Saint-André UD) : 84 % en PPR rouge R1/R2, mais
  approbation du PPR INONDATION+MOUVEMENTS_DE_TERRAIN = **2026-04-16** (attrs spatial_layers) ;
  permis du 2021-02-09, antérieur de 5 ans.
- **9744191900018 / 97419000AM0438** (Sainte-Rose Uc) : 65 % rouge, PPR MULTI approuvé
  **2022-12-29** ; permis du 2019-07-12.
- **97441313A0251 / 97413000CY1189** (Saint-Leu UD) : 57 % rouge, PPR Saint-Leu approuvé
  **2015-11-23** ; permis du 2013-12-13 (+ sur-déduction AC2, cf. erreur n° 3).

(97413000CQ0431, permis 2022 postérieur au PPR 2015, reste classé erreur_labuse : la maison
tient dans les 29 % hors rouge, où c'est de nouveau le retrait forcé qui écrase l'enveloppe.)

### donnee_permis_douteuse (1)
- **97440526A0025 / 97405000AZ0999** (Petite-Île UD) : 143 m² de plancher (124 m² hab × 1,15)
  sur une parcelle de **135 m²** ; CES 40 % (UD.9 p. 48) ⇒ 54 m² d'emprise, soit 2,6 niveaux
  sous un faîtage de 7 m (UD.10) — invraisemblable sur cette seule parcelle : assiette
  probablement multi-parcelles ou surf_hab erronée.

### indetermine (2)
- **97440524A0033 / 97405000AW1235** (Petite-Île, N 84,6 % / UD 15,4 %) : permis 2024 de
  81 m² hab, au-dessus même de l'enveloppe corrigée de la portion UD (~51 m²). Zonage
  différent à l'instruction, redécoupage ou dérogation : non tranchable en lecture seule.
- **97440526A0029 / 97405000AY0747** (Petite-Île, N 75,2 % / UC 24,8 %) : permis 2026 de
  210 m² hab sur portion UC de 124 m² ; dépasse l'enveloppe corrigée (~156 m²).

## Lecture d'ensemble

Le « dépassement » de ces 40 permis n'est pas un bruit de conversion : il mesure d'abord une
**règle moteur trop sévère** (retrait séparatif facultatif rendu obligatoire), concentrée sur
les petites parcelles étroites (7–17 m de large) où la maison réelle est construite en limite —
ce que `p_model_bati` confirme (emprises bâties de 40 à 272 m², souvent > zone d'implantation
LABUSE × 5). Correctifs candidats, par ordre d'impact :
1. modéliser l'alternative « en limite séparative » (flag existant `recul_limites_alignement`,
   ou mieux : implantation autorisée sur 1–2 limites avec longueur max), au moins pour les
   zones citées ci-dessus ;
2. corriger l'inversion du recul voie UB Saint-André (maximum lu comme minimum) ;
3. ne plus traiter les SUP AC1/AC2 en exclusion totale (régime d'avis, pas d'interdiction) ;
4. dater les couches PPR : toute comparaison permis/enveloppe doit écarter les permis
   antérieurs à l'approbation du PPR (3 cas ici).
