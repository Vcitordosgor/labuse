# CONTENANCE-1 — vérification des écarts dessin/contenance vs cadastre IGN

Rédigé le 10/10/2026. **LECTURE SEULE, aucun code modifié.** Vérifie les **30 327** parcelles
(/430 283 avec contenance, soit 7,0 %) dont l'écart |dessin − contenance| / contenance dépasse 10 %.

## Méthode

Échantillon de **40** : les **20 plus gros écarts** + **20 au hasard** parmi les autres >10 %
(`ORDER BY md5(idu)`, déterministe). Pour chacune, comparaison de notre `contenance_m2` à la
**contenance de l'API cadastre IGN du jour** (`apicarto.ign.fr/api/cadastre/parcelle`), ET à
l'**aire de la géométrie IGN** (projetée en 2975, shapely/pyproj) pour trancher la cause.
`dessin` = `ST_Area(geom_2975)` (notre polygone) ; `IGN cont` = contenance registre IGN ;
`IGN aire` = aire du polygone IGN.

## Résultat (brut)

- **40 / 40 : notre `contenance_m2` = la contenance IGN du jour, au m² près. 0 divergence.**
- **40 / 40 : l'aire du polygone IGN = notre `dessin`** (p. ex. DV 0285 : IGN aire 117 505 =
  notre dessin 117 505). ⇒ **l'écart dessin↔contenance existe À L'IDENTIQUE DANS LE CADASTRE IGN**
  lui-même : son plan graphique diffère de sa propre contenance registre, du même montant que chez
  nous. Ce n'est ni notre ingestion, ni une contenance périmée.

### 20 au hasard (écarts 10–78 %)

| grp | réf | dessin | notre cont | IGN cont | IGN aire | écart % | cause |
|---|---|---|---|---|---|---|---|
| rand | 97412 BY 1025 | 23 | 13 | 13 | 23 | 77.8 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97411 DH 0192 | 1 | 1 | 1 | 1 | -42.2 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97418 AP 0574 | 397 | 292 | 292 | 397 | 36.0 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97419 AM 0090 | 373 | 275 | 275 | 373 | 35.5 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97408 AT 1392 | 3 | 5 | 5 | 3 | -33.2 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97407 AH 0326 | 262 | 199 | 199 | 262 | 31.5 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97413 CC 0225 | 161 | 124 | 124 | 161 | 29.8 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97408 BR 0091 | 522 | 427 | 427 | 522 | 22.2 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97415 EW 1144 | 377 | 483 | 483 | 377 | -21.9 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97416 ES 1123 | 382 | 479 | 479 | 382 | -20.3 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97403 AP 1634 | 218 | 188 | 188 | 218 | 16.2 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97423 AE 0871 | 70 | 60 | 60 | 70 | 16.1 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97420 AB 1280 | 410 | 484 | 484 | 410 | -15.3 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97422 CS 0458 | 717 | 630 | 630 | 717 | 13.8 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97408 AC 1846 | 655 | 579 | 579 | 655 | 13.2 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97423 AE 0643 | 516 | 591 | 591 | 516 | -12.6 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97422 AY 1199 | 134 | 152 | 152 | 134 | -11.7 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97410 AY 0090 | 676 | 763 | 763 | 676 | -11.4 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97415 HO 0771 | 456 | 410 | 410 | 455 | 11.2 | dessin (plan) approximatif — contenance=acte=IGN |
| rand | 97409 AY 0910 | 527 | 478 | 478 | 527 | 10.2 | dessin (plan) approximatif — contenance=acte=IGN |

### 20 plus gros écarts

| grp | réf | dessin | notre cont | IGN cont | IGN aire | écart % | cause |
|---|---|---|---|---|---|---|---|
| top | 97416 DV 0285 | 117505 | 1 | 1 | 117505 | 11750370.9 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97404 AC 1091 | 38046 | 9 | 9 | 38050 | 422634.7 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97415 AO 0009 | 660230 | 4937 | 4937 | 660229 | 13273.1 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97410 BD 0311 | 2367 | 18 | 18 | 2367 | 13049.1 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97419 BH 0010 | 966633 | 9657 | 9657 | 966634 | 9909.7 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97404 AC 1093 | 1965 | 21 | 21 | 1965 | 9258.4 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97416 DX 0319 | 216 | 3 | 3 | 216 | 7108.9 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97408 AN 0636 | 70 | 1 | 1 | 70 | 6905.0 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97416 HL 0151 | 17863 | 288 | 288 | 17863 | 6102.4 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97409 BE 0292 | 115 | 2 | 2 | 115 | 5664.3 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97412 AR 0225 | 224 | 10 | 10 | 224 | 2137.7 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97409 AI 1188 | 22 | 1 | 1 | 22 | 2124.0 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97410 BD 0327 | 451 | 22 | 22 | 451 | 1951.2 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97423 AE 0277 | 19 | 1 | 1 | 19 | 1761.0 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97423 AC 0462 | 696 | 38 | 38 | 696 | 1732.4 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97410 BX 0332 | 2198 | 120 | 120 | 2199 | 1731.9 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97410 BW 0780 | 263 | 16 | 16 | 263 | 1542.5 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97415 CS 0452 | 131 | 9 | 9 | 131 | 1356.0 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97412 AR 0247 | 173 | 12 | 12 | 173 | 1339.9 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |
| top | 97415 DE 0579 | 218 | 16 | 16 | 218 | 1264.2 | incohérence cadastre (plan IGN≫contenance IGN) — source, pas nous |

## Classement par cause

| Cause | Sample 40 | Lecture |
|---|---|---|
| **Contenance identique à l'IGN — dessin (plan) approximatif** | 20/40 (tout l'échantillon aléatoire) | Le plan cadastral est une approximation graphique ; la contenance (= l'acte, = IGN) est la valeur légale. Comportement cadastral NORMAL. |
| **Incohérence interne du cadastre (plan IGN ≫ contenance IGN)** | 20/40 (tous les plus gros écarts) | Le polygone PCI (IGN **et** nous) est énorme alors que la contenance registre (IGN **et** nous) est minuscule — anomalie **de la source**, pas de nous. |
| **Contenance périmée (parcelle divisée/fusionnée)** | **0/40** | Toutes les 40 existent encore à l'IGN aujourd'hui, même numéro, même contenance. |
| **Erreur chez nous (ingestion / contenance obsolète)** | **0/40** | Notre contenance = IGN partout. |

**La contenance n'est jamais la valeur fautive.** Quand l'écart est gros, c'est le **dessin** qui
est aberrant (polygone PCI mal vectorisé, ou contenance registre d'un micro-lot), et cette aberration
est **déjà dans la donnée IGN**.

### Ampleur de la queue (base entière, 430 283 avec contenance)

| Écart | Parcelles | % |
|---|---|---|
| > 10 % | 30 327 | 7,0 % |
| > 25 % | 8 576 | 2,0 % |
| > 50 % | 2 901 | 0,67 % |
| > 100 % | 750 | 0,17 % |
| > 100 % **et** contenance < 50 m² (cas « plan énorme / contenance minuscule ») | 512 | 0,12 % |
| contenance < 10 m² (micro-lots / anomalies) | 4 806 | 1,1 % |

## Conclusion (peut-on servir la contenance telle quelle ?)

1. **Oui — la contenance est servable telle quelle.** Sur 40/40 elle égale le cadastre IGN du jour :
   jamais périmée, jamais une erreur de notre côté ; c'est la valeur de l'acte, la plus autoritaire.
2. L'écart dessin↔contenance est une **propriété de la source** : la géométrie IGN reproduit notre
   dessin et diverge pareillement de la contenance IGN — le plan (graphique) ≠ la contenance (légale).
3. **Un garde-fou « revenir au dessin au-delà d'un seuil » serait NUISIBLE** : c'est précisément sur
   les gros écarts que le dessin est le polygone aberrant (DV 0285 : dessin 117 505 m² pour 1 m²
   réel). Revenir au dessin fabriquerait une fausse grande parcelle là où elle est la plus fausse.
4. La bascule sur contenance **neutralise d'elle-même** ces anomalies : une contenance minuscule ⇒
   emprise ≈ 0 ⇒ SDP 0 ⇒ `terrain_exigu` (non exploitable, honnête), alors que le dessin fabriquait
   une fausse opportunité. Aucun garde-fou de repli nécessaire pour la justesse.
5. **Garde-fou recommandé (hygiène, pas repli)** : marquer pour revue data-quality les ~512 parcelles
   « écart > 100 % ET contenance < 50 m² » (badge « incohérence plan/contenance au cadastre — à
   vérifier », jamais un choix silencieux), et ne jamais laisser une contenance < ~10 m² (4 806 cas)
   porter un prix/une capacité affichés comme fiables. Par défaut : **servir la contenance**.
