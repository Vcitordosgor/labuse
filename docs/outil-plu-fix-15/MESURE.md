# Mesure FIX-14 — 2 034 contrôles

Chaque case donne la valeur avant et après FIX-15. Une valeur seule signifie que le compte est identique aux deux passages.

| Commune | J | R | F | X | A | C | T | I | Contrôles |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Les Avirons | 67 | 0 | 0 | 0 | 1 | 0 | 13 | 0 | 81 |
| Bras-Panon | 36 | 22 → 33 | 0 | 0 | 12 → 1 | 0 | 11 | 0 | 81 |
| Entre-Deux | 1 → 22 | 0 | 0 | 0 | 0 | 39 → 0 | 5 → 23 | 0 | 45 |
| L'Étang-Salé | 0 → 16 | 0 → 1 | 0 | 0 | 0 | 61 → 30 | 5 → 19 | 0 | 66 |
| Petite-Île | 53 | 3 | 0 | 0 | 2 | 0 | 41 | 0 | 99 |
| La Plaine-des-Palmistes | 34 | 8 | 0 | 0 | 0 | 6 | 15 | 0 | 63 |
| Le Port | 41 | 0 | 0 | 0 | 0 | 30 | 7 | 0 | 78 |
| La Possession | 54 | 18 | 0 | 0 | 2 | 0 | 19 | 0 | 93 |
| Saint-Benoît | 97 → 120 | 0 | 0 | 0 | 41 | 58 → 35 | 5 | 0 | 201 |
| Saint-Denis | 82 | 0 | 0 | 0 | 1 | 2 | 14 | 0 | 99 |
| Saint-Joseph | 50 | 78 | 0 | 0 | 2 | 31 | 7 | 0 | 168 |
| Saint-Louis | 40 | 18 → 54 | 0 | 0 | 36 → 0 | 0 | 38 | 0 | 132 |
| Saint-Paul | 157 | 16 | 0 | 0 | 0 | 0 | 22 | 0 | 195 |
| Saint-Pierre | 80 | 0 | 0 | 0 | 0 | 0 | 52 | 0 | 132 |
| Sainte-Marie | 86 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 96 |
| Sainte-Rose | 36 | 24 | 0 | 0 | 0 | 0 | 9 | 0 | 69 |
| Sainte-Suzanne | 32 | 4 | 0 | 0 | 0 | 14 | 22 | 0 | 72 |
| Salazie | 31 | 3 | 0 | 0 | 0 | 0 | 11 | 0 | 45 |
| Le Tampon | 31 | 31 | 0 | 0 | 0 | 3 | 19 | 0 | 84 |
| Les Trois-Bassins | 38 | 16 | 0 | 0 | 10 | 11 | 12 | 0 | 87 |
| Cilaos | 20 | 6 | 0 | 0 | 0 | 0 | 22 | 0 | 48 |
| **Total** | 1066 → 1126 | 247 → 295 | 0 | 0 | 107 → 60 | 255 → 162 | 359 → 391 | 0 | 2034 |

J = article de zone. R = renvoi exprès. F = renvoi annoncé contredit. X = règle étrangère. A = absence ou extrait de moins de 60 caractères hors espaces. C = chapitre ou bloc. T = texte commun ou de zone mère. I = rattachement indéterminé dans la classification FIX-14.

Le script appelle la fonction de la route sur les libellés graphiques. Il classe toujours en T selon la provenance, même si la carte porte maintenant sa mention. Son I à zéro ne tranche pas les neuf cas incertains de l’audit manuel. Les contrôles HTTP des mentions sont consignés séparément. [Mesure initiale](preuves/avant.txt) · [Mesure finale](preuves/fin.txt) · [CSV initial](preuves/avant.csv) · [CSV final](preuves/fin.csv) · [Neuf cas incertains](preuves/mentions-i.txt)

## Arrêts par commune

Exemples tirés de la route et comparés aux pages PDF du dépôt correspondant. Les cinq communes du lot B apparaissent en gras. [Réponses HTTP](preuves/temoins-arret.txt)

| Commune | Motif et page PDF |
|---|---|
| Les Avirons | AUes 10 p. 43 répond « Sans objet ». La réponse complète tombe sous le seuil de longueur A. |
| **Bras-Panon** | Même cas pour AUst 10 p. 84. Le renvoi de l’article AU indicée 12 est désormais entier p. 80. |
| **Entre-Deux** | C passe de 39 à 0, A reste à 0. U12 est servi avec son texte p. 27. |
| **L’Étang-Salé** | Il reste 30 C. La carte ZONE A pp. 89–90 commence en cours de disposition. AU 3.2 pp. 84–87 atteint la couverture du titre agricole p. 87. UA 2.7 est bien isolé pp. 21–22. |
| Petite-Île | 2AU.10 et 2AU.12 répondent « Sans objet » p. 141. Les deux réponses brèves sont classées A. |
| La Plaine-des-Palmistes | En AUb, un fragment du dossier de modification traverse les pp. 171–176. |
| Le Port | En 1AUa et 1AUc, le renvoi de l’article 12 pp. 151–154 et le début de la section 3 pp. 154–155 forment des blocs. |
| La Possession | AUst 10 p. 82 répond « Sans objet ». La recherche de hauteur Up reste vide. |
| **Saint-Benoît** | Le stationnement A/N reste vide dans les chapitres agricoles et naturels pp. 32–48. A11 p. 39 et N12 p. 48 traitent des réseaux. L’article de stationnement AU figure pp. 29–30, en colonnes règle et explication. Son extrait pp. 29–32 les entremêle encore. Pour AUa18, la route remonte aussi la liste des emplacements réservés pp. 150–152. |
| Saint-Denis | AUx.12 p. 111 répond « Non réglementé ». Le filtre A/Ac récupère le titre « Zone A Urbaniser d’activités » p. 106. |
| Saint-Joseph | La hauteur de 1AUto et 1AUtok reste vide. La mention de 1AUto p. 108 ne fournit pas de hauteur propre. En N, le bloc environnemental couvre les pp. 135–145. |
| **Saint-Louis** | A passe de 36 à 0, C reste à 0. Les articles AU indicée rendent leur renvoi aux pp. 109–110. |
| Sainte-Suzanne | La recherche en 1AUe ramène un bloc « Section 2 » pp. 30–31. |
| Le Tampon | Le bloc Ue3 pp. 73–75 empiète sur Ue4, qui commence p. 74. |
| Les Trois-Bassins | Stationnement vide sous 1AUa/b malgré AU indicée 12 p. 69. Sous N/Nco, une fiche de patrimoine pp. 96–112 remonte pour l’implantation. |
