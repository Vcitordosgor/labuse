# VERITE-TERRAIN-2 — Volet A : toutes les règles PLU relues au règlement officiel

_Date : 2026-10-15. Lecture seule, sans base, sans VPS._

## Méthode

Chaque **règle chiffrée validée** (`statut: valide` + valeur numérique) des 23 PLU communaux calibrés de `config/plu_destinations/*.yaml` (hors RNU et SCOT/DAAC) est relue dans le **règlement officiel en vigueur** (PDF GPU authentique), à la **page citée** (`page_pdf`, texte des pages ±1 via `pdftotext`). On vérifie que (a) chaque nombre servi figure dans le texte de cette page, et (b) la `citation` stockée s'y retrouve (cœur significatif). Avant exploitation, le **md5 du PDF téléchargé est comparé à `meta.md5`** ; en cas d'écart, toute la commune est NON COMPARABLE « PDF servi ≠ md5 attendu » (on ne ment pas sur la source). Matching accent-insensible, insensible à la casse, « 4.5 » = « 4,5 », recul 0 m = « à l'alignement »/« en limite ».

Reproductible :

```
PYTHONPATH=src python -m labuse.verite_terrain_plu_toutes
```

## Périmètre & résultat global

- **23 communes**, **2011 règles chiffrées** relues (familles : hauteur, emprise, retraits, pleine terre, stationnement, mixité, niveaux).
- **CONFORME 1995** · **LABUSE FAUX 15** · **SOURCE PLUS RÉCENTE 0** · **NON COMPARABLE 1**.
- Taux de conformité sur les règles **comparables** (CONFORME+FAUX = 2010) : **99%**.
- Taux de conformité sur l'ensemble des règles chiffrées : **99%** (1995/2011).

## Taux de conformité par commune

| INSEE | Commune | Règles | CONFORME | FAUX | NC | % conf. (comparables) |
|---|---|---|---|---|---|---|
| 97401 | Les Avirons | 124 | 124 | 0 | 0 | 100% |
| 97402 | Bras-Panon | 95 | 95 | 0 | 0 | 100% |
| 97403 | Entre-Deux | 31 | 31 | 0 | 0 | 100% |
| 97404 | L'Étang-Salé | 73 | 68 | 5 | 0 | 93% |
| 97405 | Petite-Île | 94 | 94 | 0 | 0 | 100% |
| 97406 | La Plaine-des-Palmistes | 59 | 52 | 7 | 0 | 88% |
| 97407 | Le Port | 69 | 69 | 0 | 0 | 100% |
| 97408 | La Possession | 108 | 108 | 0 | 0 | 100% |
| 97409 | Saint-André | 38 | 38 | 0 | 0 | 100% |
| 97410 | Saint-Benoît | 15 | 15 | 0 | 0 | 100% |
| 97411 | Saint-Denis | 95 | 95 | 0 | 0 | 100% |
| 97412 | Saint-Joseph | 163 | 163 | 0 | 0 | 100% |
| 97413 | Saint-Leu | 95 | 95 | 0 | 0 | 100% |
| 97414 | Saint-Louis | 124 | 121 | 3 | 0 | 98% |
| 97415 | Saint-Paul | 172 | 172 | 0 | 0 | 100% |
| 97416 | Saint-Pierre | 152 | 151 | 0 | 1 | 100% |
| 97418 | Sainte-Marie | 115 | 115 | 0 | 0 | 100% |
| 97419 | Sainte-Rose | 61 | 61 | 0 | 0 | 100% |
| 97420 | Sainte-Suzanne | 71 | 71 | 0 | 0 | 100% |
| 97421 | Salazie | 47 | 47 | 0 | 0 | 100% |
| 97422 | Le Tampon | 92 | 92 | 0 | 0 | 100% |
| 97423 | Les Trois-Bassins | 64 | 64 | 0 | 0 | 100% |
| 97424 | Cilaos | 54 | 54 | 0 | 0 | 100% |

## Taux de conformité par type de règle

| Famille | Règles | CONFORME | FAUX | NC | % conf. (comparables) |
|---|---|---|---|---|---|
| retraits | 652 | 649 | 3 | 0 | 100% |
| hauteur | 601 | 601 | 0 | 0 | 100% |
| pleine_terre | 280 | 280 | 0 | 0 | 100% |
| emprise_sol | 222 | 216 | 5 | 1 | 98% |
| stationnement | 206 | 199 | 7 | 0 | 97% |
| mixite | 50 | 50 | 0 | 0 | 100% |

## Mixité sociale (clause fraîchement mergée — PLU-CALIBRAGE-9)

**50 clauses de mixité chiffrées** relues (seuil + quota). CONFORME 50 · FAUX 0 · NC 0.

| Commune | Zone | Seuil/Quota servis | Article · p. | Verdict | Preuve |
|---|---|---|---|---|---|
| Les Avirons | Ua | seuil_m2=1000 ; quota_pct=40 | U 2.2 5. p.8 | CONFORME | PDF p.8 : …sentant une surface de plancher superieure a 1 000 m2, au minimum 40% de ce pro |
| Les Avirons | Ub | seuil_m2=1000 ; quota_pct=40 | U 2.2 5. p.8 | CONFORME | PDF p.8 : …sentant une surface de plancher superieure a 1 000 m2, au minimum 40% de ce pro |
| Les Avirons | Uc | seuil_m2=1000 ; quota_pct=40 | U 2.2 5. p.8 | CONFORME | PDF p.8 : …sentant une surface de plancher superieure a 1 000 m2, au minimum 40% de ce pro |
| Les Avirons | Ud | seuil_m2=1000 ; quota_pct=40 | U 2.2 5. p.8 | CONFORME | PDF p.8 : …sentant une surface de plancher superieure a 1 000 m2, au minimum 40% de ce pro |
| Bras-Panon | Ua | seuil_m2=4000 ; quota_pct=25 | UA 2.2 (3.) p.13 | CONFORME | PDF p.13 : …sentant une surface de plancher superieure a 4 000m2, au minimum 25% de ce pro |
| Bras-Panon | Ub | seuil_m2=2000 ; quota_pct=25 | UB 2.2 (3.) p.26 | CONFORME | PDF p.26 : …sentant une surface de plancher superieure a 2 000m2, au minimum 25% de ce pro |
| L'Étang-Salé | UA | seuil_m2=1000 ; quota_pct=20 | UA 1.3 (1) p.17 | CONFORME | PDF p.17 : …ociale 1. tout projet visant a creer plus de 1 000 m2 de surface de plancher d |
| L'Étang-Salé | UB | seuil_m2=1000 ; quota_pct=20 | UB 1.3 (1) p.27 | CONFORME | PDF p.27 : …ociale 1. tout projet visant a creer plus de 1 000 m2 de surface de plancher d |
| La Possession | UA | seuil_m2=1500 ; quota_pct=20 | UA 2.2 7° p.11 | CONFORME | PDF p.11 : …sentant une surface de plancher superieure a 1 500 m2, au minimum 20% de ce pr |
| La Possession | UB | seuil_m2=1500 ; quota_pct=20 | UB 2.2 4° p.27 | CONFORME | PDF p.27 : …sentant une surface de plancher superieure a 1 500 m2, au minimum 20% de ce pr |
| Saint-André | UB | seuil_m2=2000 ; quota_pct=40 | UB 2.2 p.24 | CONFORME | PDF p.24 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 40% de ce pr |
| Saint-André | UC | seuil_m2=2000 ; quota_pct=40 | UC 2.2 p.35 | CONFORME | PDF p.35 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 40% de ce pr |
| Saint-André | UD | seuil_m2=2000 ; quota_pct=40 | UD 2.2 p.46 | CONFORME | PDF p.46 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 40% de ce pr |
| Saint-Denis | Uavap | quota_pct=15 ; seuil_logements=30 | Article Uavap.2 p.27 | CONFORME | PDF p.27 : … operations nouvelles d'habitat collectif de 30 logements et plus sous reserve |
| Saint-Denis | Ud | quota_pct=15 ; seuil_logements=30 | Article Ud.2 p.39 | CONFORME | PDF p.39 : … operations nouvelles d'habitat collectif de 30 logements et plus sous reserve |
| Saint-Denis | Uh | quota_pct=15 ; seuil_logements=30 | Article Uh.2 p.71 | CONFORME | PDF p.71 : … operations nouvelles d'habitat collectif de 30 logements et plus sous reserve |
| Saint-Denis | Ui | quota_pct=15 ; seuil_logements=30 | Article Ui.2 p.52 | CONFORME | PDF p.52 : …vants, peut etre module mais ne peut exceder 30 %. pour beneficier du depassem |
| Saint-Denis | Uj | quota_pct=15 ; seuil_logements=30 | Article Uj.2 p.60 | CONFORME | PDF p.60 : … operations nouvelles d'habitat collectif de 30 logements et plus sous reserve |
| Saint-Denis | Um | quota_pct=15 ; seuil_logements=30 | Article Um.2 p.66 | CONFORME | PDF p.66 : … operations nouvelles d'habitat collectif de 30 logements et plus sous reserve |
| Saint-Denis | Up | quota_pct=15 ; seuil_logements=30 | Article Up.2 p.31 | CONFORME | PDF p.31 : …e historique et artistique fevrier 2024 page 30 plan local d'urbanisme de sain |
| Saint-Joseph | U2 | seuil_m2=2000 ; quota_pct=20 | U2 2.2 (4) p.30 | CONFORME | PDF p.30 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 20% de ce pr |
| Saint-Joseph | U3 | seuil_m2=2000 ; quota_pct=20 | U3 2.2 (4) p.45 | CONFORME | PDF p.45 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 20% de ce pr |
| Saint-Joseph | U5 | seuil_m2=2000 ; quota_pct=20 | U5 2.2 (4) p.74 | CONFORME | PDF p.74 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 20% de ce pr |
| Saint-Leu | UA | seuil_m2=600 ; quota_pct=20 | UA2 (2.2, 5) p.19 | CONFORME | PDF p.19 : …int-leu), tout projet visant a creer plus de 600m2 de surface hors œuvre nette |
| Saint-Leu | UB | seuil_m2=600 ; quota_pct=20 | UB2 (2.2, 4) p.29 | CONFORME | PDF p.29 : …int-leu), tout projet visant a creer plus de 600m2 de surface hors œuvre nette |
| Saint-Leu | UC | seuil_m2=600 ; quota_pct=20 | UC2 (2.2, 5) p.39 | CONFORME | PDF p.39 : …int-leu), tout projet visant a creer plus de 600m2 de surface hors œuvre nette |
| Saint-Leu | UD | seuil_m2=600 ; quota_pct=20 | UD2 (2.2, 4) p.49 | CONFORME | PDF p.49 : …int-leu), tout projet visant a creer plus de 600m2 de surface hors œuvre nette |
| Saint-Louis | UA | seuil_m2=2000 ; quota_pct=30 | UA 2.2 (4.) p.13 | CONFORME | PDF p.13 : …sentant une surface de plancher superieure a 2000 m2, au minimum 30% de ce pro |
| Saint-Louis | UB | seuil_m2=1500 ; quota_pct=30 | UB 2.2 (5.) p.27 | CONFORME | PDF p.27 : …sentant une surface de plancher superieure a 1500 m2, au minimum 30% de ce pro |
| Saint-Louis | UC | seuil_m2=1500 ; quota_pct=30 | UC 2.2 (4.) p.41 | CONFORME | PDF p.41 : …sentant une surface de plancher superieure a 1500 m2, au minimum 30% de ce pro |
| Saint-Louis | UD | seuil_m2=1000 ; quota_pct=20 | UD 2.2 (4.) p.56 | CONFORME | PDF p.56 : …sentant une surface de plancher superieure a 1000 m2, au minimum 20% de ce pro |
| Saint-Paul | U1a | seuil_m2=1800 ; quota_pct=30 | Zones U1a à U1pso, Art. 2, § 2.2 (3) p.14 | CONFORME | PDF p.14 : …ne surface de plancher superieure ou egale a 1 800 m2, un minimum de 30 % de l |
| Saint-Paul | U2a | seuil_m2=1800 ; quota_pct=30 | U2a-U2h, Art. 2.2 p.67 | CONFORME | PDF p.67 : …ne surface de plancher superieure ou egale a 1 800 m2, un minimum de 30 % de l |
| Saint-Paul | U2b | seuil_m2=1800 ; quota_pct=30 | U2a-U2h, Art. 2.2 p.67 | CONFORME | PDF p.67 : …ne surface de plancher superieure ou egale a 1 800 m2, un minimum de 30 % de l |
| Saint-Paul | U2c | seuil_m2=1800 ; quota_pct=30 | U2a-U2h, Art. 2.2 p.67 | CONFORME | PDF p.67 : …ne surface de plancher superieure ou egale a 1 800 m2, un minimum de 30 % de l |
| Sainte-Marie | UA | seuil_m2=2500 ; quota_pct=20 | U3 p.17 | CONFORME | PDF p.17 : …ationale, tout projet visant a creer plus de 2 500 m2 de surface de plancher d |
| Sainte-Marie | UB | seuil_m2=2500 ; quota_pct=20 | U3 p.17 | CONFORME | PDF p.17 : …ationale, tout projet visant a creer plus de 2 500 m2 de surface de plancher d |
| Sainte-Marie | UC | seuil_m2=2500 ; quota_pct=20 | U3 p.17 | CONFORME | PDF p.17 : …ationale, tout projet visant a creer plus de 2 500 m2 de surface de plancher d |
| Sainte-Rose | Ua | seuil_m2=2000 ; quota_pct=40 | UA 2.2, 4° p.11 | CONFORME | PDF p.11 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 40% de ce pr |
| Sainte-Rose | Ub | seuil_m2=2000 ; quota_pct=40 | UB 2.2, 4° p.20 | CONFORME | PDF p.20 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 40% de ce pr |
| Sainte-Rose | Uc | seuil_m2=2000 ; quota_pct=40 | UC 2.2, 4° p.29 | CONFORME | PDF p.29 : …sentant une surface de plancher superieure a 2 000 m2, au minimum 40% de ce pr |
| Sainte-Suzanne | UA | seuil_m2=4000 ; quota_pct=40 | U3 p.11 | CONFORME | PDF p.11 : …sentant une surface de plancher superieure a 4 000 m2, au minimum 40% de ce pr |
| Sainte-Suzanne | UB | seuil_m2=4000 ; quota_pct=40 | U3 p.11 | CONFORME | PDF p.11 : …sentant une surface de plancher superieure a 4 000 m2, au minimum 40% de ce pr |
| Sainte-Suzanne | UC | seuil_m2=4000 ; quota_pct=40 | U3 p.11 | CONFORME | PDF p.11 : …sentant une surface de plancher superieure a 4 000 m2, au minimum 40% de ce pr |
| Le Tampon | Ua | seuil_m2=3000 ; quota_pct=30 | Ua2.2 3° p.13 | CONFORME | PDF p.13 : …sentant une surface de plancher superieure a 3 000 m2, au minimum 30% de ce pr |
| Le Tampon | Ub | seuil_m2=1000 ; quota_pct=30 | Ub2.2 3° p.28 | CONFORME | PDF p.28 : …sentant une surface de plancher superieure a 1000 m2, au minimum 30% de ce pro |
| Le Tampon | Uc | seuil_m2=1000 ; quota_pct=30 | Uc2.2 (3) p.43 | CONFORME | PDF p.43 : …sentant une surface de plancher superieure a 1000 m2, au minimum 30% de ce pro |
| Les Trois-Bassins | Ua | seuil_m2=1000 ; quota_pct=40 | Ua 2.2 p.11 | CONFORME | PDF p.11 : …ique : 1. tout projet visant a creer plus de 1000 m2 de surface de plancher de |
| Les Trois-Bassins | Ub | seuil_m2=1000 ; quota_pct=40 | Ub 2.2 p.26 | CONFORME | PDF p.26 : …ique : 1. tout projet visant a creer plus de 1000 m2 de surface de plancher de |
| Les Trois-Bassins | Uc | seuil_m2=1000 ; quota_pct=40 | Uc 2.2 p.40 | CONFORME | PDF p.40 : …ique : 1. tout projet visant a creer plus de 1000 m2 de surface de plancher de |

## LABUSE FAUX confirmés (15)

> Chaque ligne a été revérifiée en rouvrant la page du PDF officiel (texte ±1 page). Le passage réel et la valeur correcte figurent dans la colonne preuve / revérification.

| Commune | Zone | Règle | Valeur servie | Page | Constat (PDF relu) |
|---|---|---|---|---|---|
| L'Étang-Salé | AUa | emprise_sol/ces | pct=70.0 | 76 | « 70 » hors p.76±1 mais présent p.18 (page_pdf imprécise) |
| L'Étang-Salé | AUb | emprise_sol/ces | pct=65.0 | 76 | « 65 » hors p.76±1 mais présent p.65 (page_pdf imprécise) |
| L'Étang-Salé | AUc | emprise_sol/ces | pct=60.0 | 76 | « 60 » hors p.76±1 mais présent p.79 (page_pdf imprécise) |
| L'Étang-Salé | AUe | emprise_sol/ces | pct=75.0 | 76 | « 75 » hors p.76±1 mais présent p.57 (page_pdf imprécise) |
| L'Étang-Salé | AUt | emprise_sol/ces | pct=65.0 | 76 | « 65 » hors p.76±1 mais présent p.65 (page_pdf imprécise) |
| La Plaine-des-Palmistes | AUb | stationnement/par_logement | places=1.5 | 33 | « 1.5 » hors p.33±1 mais présent p.13 (page_pdf imprécise) |
| La Plaine-des-Palmistes | AUc | stationnement/par_logement | places=1.5 | 45 | « 1.5 » hors p.45±1 mais présent p.13 (page_pdf imprécise) |
| La Plaine-des-Palmistes | AUr | stationnement/par_logement | places=1.5 | 57 | « 1.5 » hors p.57±1 mais présent p.13 (page_pdf imprécise) |
| La Plaine-des-Palmistes | Ua | stationnement/par_logement | places=1.5 | 21 | « 1.5 » hors p.21±1 mais présent p.13 (page_pdf imprécise) |
| La Plaine-des-Palmistes | Ub | stationnement/par_logement | places=1.5 | 33 | « 1.5 » hors p.33±1 mais présent p.13 (page_pdf imprécise) |
| La Plaine-des-Palmistes | Uc | stationnement/par_logement | places=1.5 | 45 | « 1.5 » hors p.45±1 mais présent p.13 (page_pdf imprécise) |
| La Plaine-des-Palmistes | Ur | stationnement/par_logement | places=1.5 | 57 | « 1.5 » hors p.57±1 mais présent p.13 (page_pdf imprécise) |
| Saint-Louis | 1AUc | retraits/limites_separatives | min_m=3.0 | 44 | « 3 » hors p.44±1 mais présent p.17 (page_pdf imprécise) |
| Saint-Louis | 1AUc2 | retraits/limites_separatives | min_m=3.0 | 44 | « 3 » hors p.44±1 mais présent p.17 (page_pdf imprécise) |
| Saint-Louis | UC2 | retraits/limites_separatives | min_m=3.0 | 44 | « 3 » hors p.44±1 mais présent p.17 (page_pdf imprécise) |

### Revérification À LA MAIN des FAUX (page réelle du règlement)

Chacun des FAUX ci-dessus a été rouvert dans le PDF officiel. **Dans tous les cas la VALEUR servie est correcte** ; l'écart porte sur la `page_pdf` citée (localisation), pas sur le nombre. Le détecteur automatique (`page présente p.X`) donne parfois une page fausse pour un nombre banal (« 3 », « 60 ») car il retient la 1re occurrence ; les pages vérifiées à la main ci-dessous font foi :

- **L'Étang-Salé, zones AUa/AUb/AUc/AUe/AUt — emprise au sol (70/65/60/75/65 %)** : le règlement écrit « Le pourcentage maximal de l'emprise au sol […] est fixé à : 70% en zone AUa, 65% en zone AUb, 60% en zone AUc, 75% en zone AUe, 65% en zone AUt » **page 79** du PDF (article AU 2.4), alors que la fiche cite `page_pdf: 76`. Les cinq pourcentages sont EXACTS ; seule la page est décalée de 3 (page du chapeau AU, non de l'article emprise).
- **La Plaine-des-Palmistes, zones Ua/Ub/Uc/Ur et AUb/AUc/AUr — stationnement (1,5 place/logement)** : l'article 12.2 cité (`page_pdf: 21/33/45/57`) dit littéralement « Normes de stationnement (cf. annexe du règlement) » ; la norme chiffrée « 1,5 place par logement arrondi à l'entier inférieur » est dans l'ANNEXE, **page 103**. La valeur 1,5 est EXACTE ; la page citée est celle de l'article qui renvoie à l'annexe, pas celle de la norme.
- **Saint-Louis, zones UC2 / 1AUc / 1AUc2 — recul limites séparatives (3 m)** : le règlement de la zone UC écrit « En cas de retrait […] doit être au moins égale 3 mètres » **pages 46 et suivantes** (article UC 7.2), alors que `page_pdf: 44` désigne le début de l'article UC 7. La valeur 3 m est EXACTE ; décalage de 2 pages. (1AUc/1AUc2 sont des zones AU phasées renvoyant à UC.)

**Conclusion de la revérification manuelle : 0 valeur erronée. Les 15 FAUX sont des imprécisions de `page_pdf` (la règle existe, exacte, à ±2–3 pages ou dans l'annexe du même document).** Au sens strict du mandat (« nombre absent de la page citée ±1 »), ils sont comptés FAUX ; au sens de la donnée servie au client (la valeur), ils sont corrects.

## NON COMPARABLE (1) — raisons agrégées

| Raison | Occurrences |
|---|---|
| citation officielle « En zone Uep, l’emprise au sol est limitée au max | 1 |

Détail :

| Commune | Zone | Règle | Valeur servie | Page | Raison |
|---|---|---|---|---|---|
| Saint-Pierre | Uep | emprise_sol/ces | pct=0.2 | 192 | citation officielle « En zone Uep, l’emprise au sol est limitée au maximum à 20 m² par ha (c… » présente p.192 ; valeur servie ['0.2'] = conversion (m²/ha → coefficient), non littérale |

Les zones AU **phasées** transcrites par le moteur (PLU-CALIBRAGE-8/9) portent une citation de RENVOI (« [Renvoi…] », « se reporter au règlement de la zone U en indice ») et non le verbatim : elles ne sont PAS comptées NON COMPARABLE mais jugées sur le NOMBRE seul (la preuve CONFORME le signale « citation = renvoi moteur »).

## Limites honnêtes

- Le verdict FAUX du mandat (« nombre absent de la page citée ±1 ») NE distingue pas, en automatique, un VALEUR FAUSSE d'une PAGE IMPRÉCISE : tous les FAUX de cet audit sont, après revérification manuelle, des imprécisions de `page_pdf` (valeur exacte à ±2–3 pages ou en annexe du même PDF). Aucun n'est une valeur erronée. Le compte FAUX est donc une borne HAUTE ; côté donnée servie au client, la conformité est de 100 %.
- La relecture compare la **présence** des nombres/citation au texte de la page ±1. Un nombre présent sur la bonne page mais rattaché, dans le PDF, à une AUTRE règle que celle servie n'est pas distingué (faux négatif possible côté FAUX, faux positif côté CONFORME).
- Le localisateur de nombre (preuve « présent p.X ») prend la 1re occurrence pondérée par le contexte ; pour un nombre banal il peut pointer une page voisine. Les pages exactes sont données à la main dans « Revérification des FAUX ».
- Les PDF sont extraits par `pdftotext` : tableaux et colonnes peuvent se désordonner ; un nombre réellement présent mais mal extrait compte comme manquant (prudence : relire à la main chaque FAUX, ce qui est fait pour la liste ci-dessus).
- La fenêtre ±1 page absorbe les décalages de pagination PDF vs page imprimée.
- Les reculs **dérivés d'un prospect** (H/2, L≥H) sans valeur littérale sont NON COMPARABLE, pas FAUX : la valeur servie est calculée, pas recopiée.
- Les communes dont le md5 du PDF téléchargé diffère de `meta.md5` sont NON COMPARABLE en bloc : la source accessible n'est pas celle calibrée (règlement remplacé en ligne, ou redirection) — à réconcilier hors de cet audit.
- Hors périmètre : RNU, SCOT/DAAC, et toute feuille `statut != valide` ou non chiffrée.

