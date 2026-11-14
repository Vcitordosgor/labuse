# SONDAGE-10 — dix règles de stationnement réingérées (pilote 5 communes)

ETUDE-STATIONNEMENT-FIX-1 (LOT 2). Pour chaque règle : la **valeur que LABUSE applique désormais**, la **citation** ingérée, l'**article** et la **page**, et un **extrait verbatim de la page** lu dans la base `plu_reglement_extrait` (texte opposable) pour contrôle. Rien n'est inventé : si la valeur ne correspondait pas au texte, l'écart serait visible ici.

## 1. Le Tampon — zone Ud (collectif + opération >5)
- **INSEE / zone** : 97422 / Ud
- **Article · page** : Ud12.2 · p.67
- **Valeur appliquée par LABUSE** : mode=par_typologie, retenue=max : collectif 0.5/logt ; collectif 1/logt ; collectif 1.5/logt ; individuel 1/logt ; collectif 1.5/logt [operation] ; social 1/logt
- **Condition(s) à vérifier (non comptées comme satisfaites)** : dont au moins 0,5 place à l'extérieur des espaces privatisés (opération/lotissement de plus de 5 logements/lots)
- **Citation ingérée (YAML)** : « Habitat individuel : 1 place par logement. Habitat collectif (autre que logements sociaux) : 0,5 place par chambre et studio ; 1 place par logement de 2 pièces ; 1,5 place par logement de 3 pièces et plus. Lotissement ou opération supérieur à 5 lots ou logements : 1,5 place par logement, arrondi à l'entier inférieur dont au moins 0,5 place à l'extérieur des espaces privatisés. Logement locatif financé par un prêt aidé de l'État : 1 place par logement au maximum. Foyer, résidence sociale (FPA, EHPAD, etc.) : 1 place pour 3 chambres ou logement. »
- **Extrait verbatim de la page (base) :**
  ```
  en dehors des voies publiques. Pour accéder aux places de stationnement depuis la voie publique, ne sont
  destination, aucune place de stationnement n’est requise dès lors qu’il n’y a pas d’augmentation du nombre de
  logements ou de création de surface de plancher destinée aux activités. Dans le cas contraire, le nombre de
  places de stationnement prévu à l’article 12.2 est requis pour chaque logement nouveau ou surface d’activité
  Lors de toute opération de construction, il doit être réalisé des places de stationnement selon les dispositions
  Nombre minimal de places de stationnement
  Constructions à destination d’habitation
  Logement locatif financé par un prêt aidé de l’État
  1 place par logement au maximum
  Habitat individuel
  1 place par logement
  Habitat collectif (autre que logements sociaux)
  ```

## 2. Le Tampon — zone Ua
- **INSEE / zone** : 97422 / Ua
- **Article · page** : Ua12.2 · p.22
- **Valeur appliquée par LABUSE** : mode=par_typologie, retenue=max : collectif 0.5/logt ; collectif 1/logt ; collectif 1.5/logt ; individuel 1/logt ; collectif 1.5/logt [operation] ; social 1/logt
- **Condition(s) à vérifier (non comptées comme satisfaites)** : dont au moins 0,5 place à l'extérieur des espaces privatisés (opération/lotissement de plus de 5 logements/lots)
- **Citation ingérée (YAML)** : « Habitat individuel : 1 place par logement. Habitat collectif (autre que logements sociaux) : 0,5 place par chambre et studio ; 1 place par logement de 2 pièces ; 1,5 place par logement de 3 pièces et plus. Lotissement ou opération supérieur à 5 lots ou logements : 1,5 place par logement, arrondi à l'entier inférieur dont au moins 0,5 place à l'extérieur des espaces privatisés. Logement locatif financé par un prêt aidé de l'État : 1 place par logement au maximum. Foyer, résidence sociale (FPA, EHPAD, etc.) : 1 place pour 3 chambres ou logement. »
- **Extrait verbatim de la page (base) :**
  ```
  en dehors des voies publiques. Pour accéder aux places de stationnement depuis la voie publique, ne sont
  destination, aucune place de stationnement n’est requise dès lors qu’il n’y a pas d’augmentation du nombre de
  logements ou de création de surface de plancher destinée aux activités. Dans le cas contraire, le nombre de
  places de stationnement prévu à l’article 12.2 est requis pour chaque logement nouveau ou surface d’activité
  Lors de toute opération de construction, il doit être réalisé des places de stationnement selon les dispositions
  Nombre minimal de places de stationnement
  Constructions à destination d’habitation
  Logement locatif financé par un prêt aidé de l’État
  1 place par logement au maximum
  Habitat individuel
  1 place par logement
  Habitat collectif (autre que logements sociaux)
  ```

## 3. Saint-Pierre — zone Ud (1 place / 75 m²)
- **INSEE / zone** : 97416 / Ud
- **Article · page** : Ud6 · p.93
- **Valeur appliquée par LABUSE** : mode=par_m2_sdp, 1 place / 75 m² (tranche complète), arrondi superieur
- **Condition(s) à vérifier (non comptées comme satisfaites)** : 0,5 place par parcelle pour les lotissements d'habitat individuel (espaces communs)
- **Citation ingérée (YAML)** : « Logement : 1 place de stationnement par tranche de 75 m² de surface de plancher. 1 place pour les logements locatifs sociaux. 0,5 place par parcelle, à réaliser au sein des espaces communs, pour les lotissements d'habitat individuel. (Toute norme exprimée par tranche est comptabilisée par tranche complète.) »
- **Extrait verbatim de la page (base) :**
  ```
  Pour tout projet nécessitant la création de plus de 20 places de stationnement, 20 % d’entre elles au
  Dès lors que la norme de stationnement est exprimée par tranche, la place de stationnement est
  comptabilisée par tranche complète.
  Habitation
  Logement
  1 place de stationnement par tranche
  de 75 m² de surface de plancher.
  1 place pour les logements locatifs
  0,5 place par parcelle, à réaliser au sein
  lotissements d’habitat individuel.
  300 m² de surface de
  place
  ```

## 4. Saint-Pierre — zone Ucv (social 0,85)
- **INSEE / zone** : 97416 / Ucv
- **Article · page** : Ucv6 · p.72
- **Valeur appliquée par LABUSE** : mode=par_m2_sdp, 1 place / 75 m² (tranche complète), arrondi superieur
- **Condition(s) à vérifier (non comptées comme satisfaites)** : 0,5 place par parcelle pour les lotissements d'habitat individuel (espaces communs)
- **Citation ingérée (YAML)** : « Logement : 1 place de stationnement par tranche de 75 m² de surface de plancher. 1 place pour les logements locatifs sociaux. 0,5 place par parcelle, à réaliser au sein des espaces communs, pour les lotissements d'habitat individuel. (Toute norme exprimée par tranche est comptabilisée par tranche complète.) »
- **Extrait verbatim de la page (base) :**
  ```
  Pour tout projet nécessitant la création de plus de 20 places de stationnement, 20 % d’entre elles au
  Dès lors que la norme de stationnement est exprimée par tranche, la place de stationnement est
  comptabilisée par tranche complète.
  Habitation
  Logement
  1 place de stationnement par tranche de
  75 m² de surface de plancher.
  place
  logement social
  300 m² de surface de
  place
  1 place par tranche de 70 m² de surface
  ```

## 5. Saint-Pierre — zone Uf (1,5/logt + social)
- **INSEE / zone** : 97416 / Uf
- **Article · page** : Uf6 · p.127
- **Valeur appliquée par LABUSE** : mode=par_logement, 1.5 place/logt, arrondi superieur
- **Condition(s) à vérifier (non comptées comme satisfaites)** : 0,5 place par parcelle pour les lotissements d'habitat individuel (espaces communs)
- **Citation ingérée (YAML)** : « 1,5 place de stationnement par logement. 1 place pour les logements locatifs sociaux. 0,5 place par parcelle, à réaliser au sein des espaces communs, pour les lotissements d'habitat individuel. »
- **Extrait verbatim de la page (base) :**
  ```
  Pour tout projet nécessitant la création de plus de 20 places de stationnement, 20 % d’entre elles, au
  Dès lors que la norme de stationnement est exprimée par tranche, la place de stationnement est
  comptabilisée par tranche complète.
  Habitation
  Logement
  place
  logement
  1 place pour les logements locatifs
  0,5 place par parcelle, à réaliser au sein
  lotissements d’habitat individuel.
  de 300m² de surface
  place
  ```

## 6. Les Avirons — zone Ua (max de deux formules)
- **INSEE / zone** : 97401 / Ua
- **Article · page** : U 12.2 · p.17
- **Valeur appliquée par LABUSE** : mode=par_typologie, retenue=max : individuel 1.5/logt ; collectif 1.25/logt [alt] ; collectif 1 place/35 m² [alt]
- **Condition(s) à vérifier (non comptées comme satisfaites)** : 0,5 place supplémentaire sur voie par terrain pour les lotissements de plus de 5 lots
- **Citation ingérée (YAML)** : « 1,5 place par logement. En outre, 0,5 place de stationnement supplémentaire sur voie par terrain, pour les lotissements de plus de 5 lots. Dans le cas d'opération d'habitat collectif, la norme 1,5 est ramenée à 1,25 place par logement ou une place par tranche de 35 m² de surface de plancher. La norme produisant le plus de places de stationnement devra être retenue. »
- **Extrait verbatim de la page (base) :**
  ```
  dès lors qu’il n’y a pas d’augmentation du nombre de logements ou de création de surface de plancher destinée aux activités. Dans le cas contraire,
  le nombre de places de stationnement prévu à l’article U 12.2 est requis pour chaque logement nouveau ou surface d’activité supplémentaire.
  Logements locatifs financés avec
  1,5 place par logement. En outre, il est demandé 0,5 place de stationnement supplémentaire sur voie par
  Dans le cas d’opération d’habitat collectif, la norme 1,5 est ramenée à 1,25 place par logement ou une
  place par tranche de 35 m² de surface de plancher. La norme produisant le plus de places de
  il ne peut être exigé la réalisation de plus d'une aire de stationnement par logement lors de la
  construction de logements locatifs financés avec un prêt aidé par l'Etat,
  transformation ou d'amélioration de bâtiments affectés à des logements locatifs financés
  pour les constructions à destination d’habitation comportant au moins deux logements, hors résidence pour personnes âgées : un
  emplacement minimum par logement,
  ```

## 7. Les Avirons — zone Uc
- **INSEE / zone** : 97401 / Uc
- **Article · page** : U 12.2 · p.17
- **Valeur appliquée par LABUSE** : mode=par_typologie, retenue=max : individuel 1.5/logt ; collectif 1.25/logt [alt] ; collectif 1 place/35 m² [alt]
- **Condition(s) à vérifier (non comptées comme satisfaites)** : 0,5 place supplémentaire sur voie par terrain pour les lotissements de plus de 5 lots
- **Citation ingérée (YAML)** : « 1,5 place par logement. En outre, 0,5 place de stationnement supplémentaire sur voie par terrain, pour les lotissements de plus de 5 lots. Dans le cas d'opération d'habitat collectif, la norme 1,5 est ramenée à 1,25 place par logement ou une place par tranche de 35 m² de surface de plancher. La norme produisant le plus de places de stationnement devra être retenue. »
- **Extrait verbatim de la page (base) :**
  ```
  dès lors qu’il n’y a pas d’augmentation du nombre de logements ou de création de surface de plancher destinée aux activités. Dans le cas contraire,
  le nombre de places de stationnement prévu à l’article U 12.2 est requis pour chaque logement nouveau ou surface d’activité supplémentaire.
  Logements locatifs financés avec
  1,5 place par logement. En outre, il est demandé 0,5 place de stationnement supplémentaire sur voie par
  Dans le cas d’opération d’habitat collectif, la norme 1,5 est ramenée à 1,25 place par logement ou une
  place par tranche de 35 m² de surface de plancher. La norme produisant le plus de places de
  il ne peut être exigé la réalisation de plus d'une aire de stationnement par logement lors de la
  construction de logements locatifs financés avec un prêt aidé par l'Etat,
  transformation ou d'amélioration de bâtiments affectés à des logements locatifs financés
  pour les constructions à destination d’habitation comportant au moins deux logements, hors résidence pour personnes âgées : un
  emplacement minimum par logement,
  ```

## 8. Saint-Benoît — zone Ua (visiteur >5 + aidé)
- **INSEE / zone** : 97410 / Ua
- **Article · page** : U 12 · p.17
- **Valeur appliquée par LABUSE** : mode=par_logement, 1 place/logt, arrondi superieur ; visiteurs 1 / 5 logts (au-delà de 5 logts)
- **Citation ingérée (YAML)** : « Logements individuels, construction ou opération de 5 logements ou moins : 1 place par logement. Lotissements ou opérations de plus de 5 logements : 1 place par logement, plus une place visiteur par tranche de 5 lots ou 5 logements. Logements aidés : 1 place pour 2 logements. Résidences universitaires et de personnes âgées : 1 place pour 3 logements ou 3 chambres. »
- **Extrait verbatim de la page (base) :**
  ```
  En cas de réalisation d’un programme immobilier de 20 logements ou plus, une aire de jeux
  de logements denses, afin de garantir un cadre de vie de qualité aux occupants et
  3,50 mètres si la voirie fait moins de 25 mètres et dessert moins de 5 logements,
  6,00 mètres si la voirie fait plus de 25 mètres et dessert 5 logements et plus.
  Toute construction d’immeubles neufs regroupant plusieurs logements ou des locaux à
  Logements individuels,
  logements ou moins :
  1 place par logement.
  fonction des typologies de logements, afin de tenir compte de l’évolution des
  plus de 5 logements :
  1 place par logement, plus une place visiteur par
  tranche 5 lots ou 5 logements.
  ```

## 9. Le Port — zone Ua (0,3/logt + visiteur/100 m²)
- **INSEE / zone** : 97407 / Ua
- **Article · page** : Ua 12.1 · p.30
- **Valeur appliquée par LABUSE** : mode=par_logement, 0.3 place/logt, arrondi superieur ; visiteurs 1 / 100 m²
- **Citation ingérée (YAML)** : « 0,3 place de stationnement par logement. En outre, 1 place de stationnement pour visiteur par tranche de 100 m² de surface de plancher. Logement locatif financé avec un prêt aidé de l'État : 0,2 place par logement, plus 8 places par tranche de 1000 m² de surface de plancher. »
- **Extrait verbatim de la page (base) :**
  ```
  mais sans changement de destination, aucune place de stationnement n’est requise dès lors
  qu’il n’y a pas d’augmentation du nombre de logements ou de création de surface de plancher
  destinée aux activités. Dans le cas contraire, le nombre de places de stationnement prévu ci-
  après est requis pour chaque logement nouveau ou surface d’activité supplémentaire.
  Pour les opérations de plus de 1 000 m² de surface de plancher, une partie de ces places doit
  plus de 1 000 m²
  Le nombre de place de stationnement à aménager doit
  Pour une opération de moins de 60 m² de surface de
  plancher, aucune place n’est exigée,
  Pour une opération comprise entre 60 m² et 500 m² de
  surface de plancher, 1 place de stationnement par
  tranche de 60 m² de surface de plancher,
  ```

## 10. Le Port — zone Ud
- **INSEE / zone** : 97407 / Ud
- **Article · page** : Ud 12.1 · p.73
- **Valeur appliquée par LABUSE** : mode=par_logement, 0.3 place/logt, arrondi superieur ; visiteurs 1 / 100 m²
- **Citation ingérée (YAML)** : « 0,3 place de stationnement par logement. En outre, 1 place de stationnement pour visiteur par tranche de 100 m² de surface de plancher. Logement locatif financé avec un prêt aidé de l'État : 0,2 place par logement, plus 8 places par tranche de 1000 m² de surface de plancher. »
- **Extrait verbatim de la page (base) :**
  ```
  mais sans changement de destination, aucune place de stationnement n’est requise dès lors
  qu’il n’y a pas d’augmentation du nombre de logements ou de création de surface de plancher
  destinée aux activités. Dans le cas contraire, le nombre de places de stationnement prévu ci-
  après est requis pour chaque logement nouveau ou surface d’activité supplémentaire.
  Pour les opérations de plus de 500 m² de surface de plancher, une partie de ces places doit être
  plus de 500 m² de
  Le nombre de place de stationnement à aménager doit
  Pour une opération de moins de 60 m² de surface de
  plancher, aucune place n’est exigée,
  Pour une opération comprise entre 60 m² et 500 m² de
  surface de plancher, 1 place de stationnement par
  tranche de 60 m² de surface de plancher,
  ```
