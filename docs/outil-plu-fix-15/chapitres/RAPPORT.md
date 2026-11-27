# Outil PLU · contrôle des chapitres du 26 novembre 2026

Les 441 recherches des quatre communes passent avec F, X, A et C à zéro. Le contrôle renforcé sur la version initiale 473c6a98a trouvait 57 recherches avec une carte étrangère, 61 avec un chapitre en bloc et deux avec une règle absente. Sept parcours depuis une fiche parcelle ont été vérifiés sur le front 10280. Les quatre fichiers officiels du disque sont identiques octet pour octet aux dépôts GPU en vigueur. [Identifiants et SHA-256](sources.txt)

| Commune | Preuve dans le règlement et à l’écran |
|---|---|
| Petite-Île | L’article 1AU.10 est p. 94, l’article 1AUZ.10 p. 104. La recherche conserve aussi le croquis commun cité par les deux articles 11, p. 166. Le croquis UEa.6 p. 167 est rattaché à UEa. [PDF p. 94](https://data.geopf.fr/annexes/gpu/documents/DU_97405/0b91a0d63909c727a863784113009109/97405_reglement_20230609.pdf#page=94) · [PDF p. 104](https://data.geopf.fr/annexes/gpu/documents/DU_97405/0b91a0d63909c727a863784113009109/97405_reglement_20230609.pdf#page=104) · [Écran 1AU](1au.png) · [Écran 1AUz](1auz.png) |
| Sainte-Marie | UC1 relève de la zone UC du chapitre résidentiel, avec 13 m au faîtage p. 22. UEm relève du chapitre d’activités, avec 16 m au faîtage p. 35. Les conditions et exceptions restent lisibles dans l’article entier. [PDF p. 22](https://data.geopf.fr/annexes/gpu/documents/DU_97418/3fe3fd7e85c27ce210c60b6058cabd0d/97418_reglement_20251126.pdf#page=22) · [Écran UC1](uc1-passage.png) · [PDF p. 35](https://data.geopf.fr/annexes/gpu/documents/DU_97418/3fe3fd7e85c27ce210c60b6058cabd0d/97418_reglement_20251126.pdf#page=35) · [Écran UEm](uem-passage.png) |
| Saint-Joseph | 140 articles isolés. L’article AUindicée 10 fixe 9 m au faîtage en AUto et 12 m pour les constructions de type industrie en AUtok. L’article N 10 reste au chapitre N et l’annexe commence p. 136. [PDF p. 110](https://data.geopf.fr/annexes/gpu/documents/DU_97412/ce1a1274209313eeaf6c85f947d03a13/97412_Reglement_20251210.pdf#page=110) · [Écran 1AUtok](autok-passage.png) · [Écran N](n.png) |
| Le Port | 196 articles isolés. Le stationnement en 1AUmut renvoie à l’article 1AUindicée 12, pp. 151–154. L’article 13 sur les voies commence plus bas p. 154. Le contrôle conserve les quatre pages du barème. [PDF p. 151](https://data.geopf.fr/annexes/gpu/documents/DU_97407/8cdd92497a52e883eddd7330b3836873/97407_reglement_20241209.pdf#page=151) · [PDF p. 154](https://data.geopf.fr/annexes/gpu/documents/DU_97407/8cdd92497a52e883eddd7330b3836873/97407_reglement_20241209.pdf#page=154) · [Écran 1AUmut](port-passage.png) |

## Mesure avant et après

Chaque cellule présente l’effectif initial puis l’effectif final lorsqu’il change. J = article applicable, R = renvoi, F = renvoi annoncé faux, X = chapitre étranger, A = règle absente de l’extrait, C = bloc, T = texte commun ou de zone mère, I = rattachement indéterminé. La mesure contrôle trois thèmes par libellé graphique. Elle ne certifie pas l’ensemble du règlement. [Avant brut](avant.txt) · [Après brut](apres.txt) · [2 034 lignes avant](avant.csv) · [2 034 lignes après](apres.csv)

| Commune | J | R | F | X | A | C | T | I | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Les Avirons | 68 | 0 | 0 | 0 | 0 | 0 | 13 | 0 | 81 |
| Bras-Panon | 37 | 33 | 0 | 0 | 0 | 0 | 11 | 0 | 81 |
| Entre-Deux | 22 | 0 | 0 | 0 | 0 | 0 | 23 | 0 | 45 |
| L'Étang-Salé | 56 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 66 |
| Petite-Île | 46 → 52 | 3 | 0 | 9 → 0 | 0 | 0 | 41 → 44 | 0 | 99 |
| La Plaine-des-Palmistes | 34 | 8 | 0 | 0 | 0 | 6 | 15 | 0 | 63 |
| Le Port | 41 → 50 | 0 → 3 | 0 | 0 | 0 | 30 → 0 | 7 → 25 | 0 | 78 |
| La Possession | 55 | 18 | 0 | 0 | 1 | 0 | 19 | 0 | 93 |
| Saint-Benoît | 137 | 0 | 0 | 0 | 41 | 0 | 23 | 0 | 201 |
| Saint-Denis | 82 | 0 | 0 | 0 | 1 | 2 | 14 | 0 | 99 |
| Saint-Joseph | 50 → 71 | 78 → 84 | 0 | 0 | 2 → 0 | 31 → 0 | 7 → 13 | 0 | 168 |
| Saint-Louis | 40 | 54 | 0 | 0 | 0 | 0 | 38 | 0 | 132 |
| Saint-Paul | 157 | 16 | 0 | 0 | 0 | 0 | 22 | 0 | 195 |
| Saint-Pierre | 80 | 0 | 0 | 0 | 0 | 0 | 52 | 0 | 132 |
| Sainte-Marie | 38 → 69 | 0 → 18 | 0 | 48 → 0 | 0 | 0 | 10 → 9 | 0 | 96 |
| Sainte-Rose | 36 | 24 | 0 | 0 | 0 | 0 | 9 | 0 | 69 |
| Sainte-Suzanne | 32 | 4 | 0 | 0 | 0 | 14 | 22 | 0 | 72 |
| Salazie | 31 | 3 | 0 | 0 | 0 | 0 | 11 | 0 | 45 |
| Le Tampon | 31 | 31 | 0 | 0 | 0 | 3 | 19 | 0 | 84 |
| Les Trois-Bassins | 39 | 16 | 0 | 0 | 8 | 11 | 13 | 0 | 87 |
| Cilaos | 20 | 6 | 0 | 0 | 0 | 0 | 22 | 0 | 48 |
| **Total** | 1132 → 1199 | 294 → 321 | 0 | 57 → 0 | 53 → 51 | 97 → 36 | 401 → 427 | 0 | 2034 |

Sur les dix-sept autres communes, les 1 593 classifications, les empreintes de l’extraction et les empreintes de la table sont identiques. Restent 51 absences et 36 blocs dans le corpus. Parmi les absences, 41 correspondent aux recherches de stationnement à Saint-Benoît pour lesquelles l’outil affiche une carte documentaire. [Constat et pages de Saint-Benoît](../suite/RAPPORT.md) · [Motifs et pages des autres communes](../MESURE.md)

## Preuves de vérification

Les dix tests initiaux échouent sur 473c6a98a et sont consignés dans le commit séparé 06ec22904. Le contrôle indépendant situe les cartes dans les chapitres du PDF, y compris quand la carte se déclare propre. Sur les sorties HTTP initiales, sa version finale rejette bien les quatre filtres demandés. Les témoins supplémentaires couvrent le croquis de UEa, les renvois vers U, les 336 articles, la frontière de U1 et le vrai bloc de deux articles. La dernière relecture à l’écran a aussi permis de corriger le titre tronqué des articles AU indicée. Les 41 tests ciblés passent. [Dix échecs initiaux](rouge-473c6a98a.txt) · [Croquis](croquis-rouge.txt) · [Renvois](renvoi-rouge.txt) · [336 articles](articles-rouge.txt) · [Cas limites](limites-rouge.txt) · [Titres rouges](titres-rouge.txt) · [Tests finaux](tests.txt)

Route réelle sur 7480 et parcours de la fiche à l’annuaire sur 10280. [HTTP avant](routes-avant.txt) · [HTTP après](routes-apres.txt) · [Assertions et pages](controle-http.txt) · [Filtres à l’écran](ecran-filtres.txt) · [Articles à l’écran](ecran-blocs.txt) · [Passages dépliés](ecran-passages.txt) · [Titres définitifs à l’écran](ecran-titres.txt)

Les sauvegardes datées du 26 novembre précèdent les réingestions. Seul le script du dépôt en mode données seules a écrit dans plu_reglement_extrait. La table passe de 3 322 à 3 356 extraits. [SHA avant](base-avant.txt) · [Après les deux premières communes](base-filtres.txt) · [Avant les blocs](base-avant-blocs.txt) · [Avant le dernier intercalaire](base-avant-titre.txt) · [SHA final](base-apres.txt) · [Extraction par commune](extraction-apres.txt)

Branche fix/outil-plu-1. Aucun fichier de consignes trouvé à la racine ou aux cinq emplacements demandés. [État Git initial brut](etat-initial.txt)
