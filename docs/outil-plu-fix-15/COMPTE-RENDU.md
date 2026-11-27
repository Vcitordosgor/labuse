# OUTIL-PLU-FIX-15

[Reprise du 26 novembre — résultats finaux, contre-épreuves et infobulles](suite/RAPPORT.md)

## A — Sainte-Marie

Le répertoire officiel local contient un seul règlement pour Sainte-Marie. La version 6 du dépôt est en vigueur. Le même nom d’archive désigne aussi la version 5 archivée. La fiche de la version 6 indique une publication le 9 mars 2026 à 13 h 55 et identifie le règlement écrit. [Dépôt en vigueur](https://www.geoportail-urbanisme.gouv.fr/document/by-id/3fe3fd7e85c27ce210c60b6058cabd0d) · [Dépôt archivé](https://www.geoportail-urbanisme.gouv.fr/document/by-id/54cf15d941230465f2d947f9667b8db2)

```text
97418_reglement_20251126.pdf 3099673
f8b1174ef44df402cec85a7297eb268d4d202d5de5a8d4c0e2e1ece0dcc25968
Prescrit le 3 juin 2021
Arrêté le 5 mars 2025
Approuvé le 26 novembre 2025
```

Comparaison par `cmp` du fichier local avec le flux HTTPS de la pièce du dépôt en vigueur, code retour 0. La recherche HTTP `/modules/plu-annuaire/search?insee=97418&zone=UC1&q=hauteur` sur le port 7480 fournit ce même PDF pour les huit cartes zonées. Sur le front 10280, la recherche communale « hauteur » affiche ce lien sur la première carte.

```text
GPU = disque (cmp 0)
n 8 n_total 9
règlement PDF ↗ (p. 57) https://data.geopf.fr/annexes/gpu/documents/DU_97418/3fe3fd7e85c27ce210c60b6058cabd0d/97418_reglement_20251126.pdf#page=57
```

La comparaison établit l’identité du PDF servi. L’attribution des extraits à UC1 est une question distincte. Lot A clos sans remplacement.

## B — Découpage

Cinq témoins sur PDF rouge avant correction, cinq verts après. Un sixième contrôle vérifie que la réingestion de données seules saute toute préparation du schéma. À Entre-Deux, les pages 2–4 du sommaire contaminaient les résultats de vrais articles, dont U12 p. 27. À Saint-Benoît, l’intertitre « Section 2 » p. 23 remontait parmi les règles. Le stationnement AU se trouve aux p. 29–30. À L’Étang-Salé, UA 2.7 commence p. 21. Les articles AU indicée 6–8 et 12 conservent leur renvoi à Bras-Panon (p. 79–80) et Saint-Louis (p. 109–110).

Sauvegarde PostgreSQL COPY datée de toutes les lignes et colonnes dans le worktree. Comparaison HTTPS octet par octet des cinq PDF avant réingestion. SHA-256 des lignes dans l’ordre INSEE, id, données techniques comprises.

```text
avant  3209  e9c1fd93daff4f99ba5f515c315accc18102a8bb96db71416bac92ee1220284c
après  3271  9c183f2e15e33394716eb0373be654e4c9d963301d9e77b0f40d8c835dd112fb
communes modifiées, extraction et table : 97402 97403 97404 97410 97414
autres communes identiques : 16/16
```

## C et D — Cartes et fiche

Les cartes distinguent la zone mère, les dispositions communes identifiées et le rattachement à vérifier. Le règlement d’Entre-Deux décrit Nci dans le chapitre N (p. 40). Les libellés Nto1 des Trois-Bassins, Ub1 et NtoPOS de Cilaos n’ont pas de correspondance établie dans leurs pièces écrites.

Stationnement. Le Tampon Ud 12.2 p. 67 plafonne le logement locatif aidé. Saint-Louis UA 12.2 p. 23 fixe 0,5 place publique par logement pour une opération de plus de dix logements. La tuile de Saint-Pierre Ud porte son propre lien vers le tableau p. 93.

| Autres zones relues | Pages PDF | Point contrôlé |
|---|---|---|
| Bras-Panon Ua, Ub, Uc | 22, 35, 49 | Logement aidé, 1 place maximum par logement |
| Entre-Deux Ua, Ub | 27 | Logement ordinaire, 2 places par logement, dérogation prêt aidé |
| Saint-Louis UB, UC | 37, 52 | Social, 1 place par logement. Opérations de plus de 10 logements, 0,5 place publique par logement |
| Le Tampon Ua | 22 | Logement locatif aidé, 1 place maximum |
| Sainte-Marie UA, UB | 26 | Logement aidé, plafond, avec condition de desserte à moins de 500 m dans le tableau |

Les dix fiches HTTP ont aussi été relues. Trois précisions restent absentes de leur infobulle. À Bras-Panon, le ratio d’une place pour trois logements ou chambres de foyer est un **maximum**. À Entre-Deux, U12 prévoit aussi une place visiteur par tranche de dix logements aidés, et par tranche de cinq logements ou lots pour les autres. À Sainte-Marie, le tableau prévoit 0,5 place par logement sous condition de desserte à moins de 500 m. [Valeurs effectivement servies aux dix parcelles](preuves/dix-zones.txt)

Les 391 recherches classées T ont été rejouées en HTTP. Les 1 626 cartes de zone mère ou dispositions communes examinées portaient une mention. Les neuf recherches jugées incertaines par l’audit affichent toutes la réserve. À Saint-Denis, une carte de la p. 9 porte « disposition commune à toutes les zones ». [Comptage T](preuves/mentions.txt) · [Neuf recherches et disposition commune](preuves/mentions-i.txt)

## E — Dates du règlement

Les 21 couvertures ont été relues. Saint-Denis et Saint-Pierre donnent seulement le mois. La couverture de Saint-Benoît laisse l’approbation vide. L’annuaire distingue aussi la date incluse dans l’identifiant du lot et celle de sa publication. Sur la fiche de Saint-Pierre, le libellé rendu est « Approbation en couverture · 06/2024 ». [Extraits des couvertures](preuves/couvertures.txt) · [Écrans](preuves/ecran-final.txt)

| Commune | Approbation en couverture | Dernière modification en couverture | Millésime du dépôt |
|---|---|---|---|
| Le Port | 02/10/2018 | 30/01/2024 | 09/12/2024 |
| La Possession | 12/06/2019 | 17/12/2025 | 25/06/2026 |
| Saint-Louis | 11/03/2014 | 09/07/2025 | 18/12/2025 |
| Les Trois-Bassins | 21/02/2017 | 02/06/2022 | 02/06/2022 |

## F — Actes et livrets

- **Les Trois-Bassins.** Le point 2.6 de la liste des délibérations du 27 août 2026 porte sur la mise en compatibilité du PLU pour le secteur des Zattes – Littoral Sud. Le conseil a voté « Approuvée à la majorité ». La pièce ne fixe pas la date d’entrée en vigueur. L’avertissement affiché renvoie à la p. 2. [Pièce municipale](https://docs.trois-bassins.re/arretes-delibarations/CM/2026/27AOUT2026/LISTE-DES-DELIBERATIONS-EXAMINEES_CM_27082026.pdf#page=2)
- **La Possession.** La note indique le dépôt 97408_PLU_20260625, sa publication le 29 octobre 2026 et un lien direct vers le règlement. [Règlement du dépôt](https://data.geopf.fr/annexes/gpu/documents/DU_97408/77244f114938a3230afb98948d9498bc/97408_reglement_20260625.pdf)
- **Saint-Paul.** La recherche de stationnement en Usdu fournit quatre liens. Plateau Caillou ouvre p. 139, La Plaine – Bois de Nèfles p. 200, La Saline p. 246 et Guillaume p. 306. [Liens relevés à l’écran](preuves/ecran-final.txt)

## Vérification

Le script FIX-14, inchangé, porte sur 2 034 recherches. F et X restent à 0. A passe de 107 à 60 et C de 255 à 162. Les deux cibles sont atteintes à Entre-Deux et Saint-Louis. Arrêt à Bras-Panon, L’Étang-Salé et Saint-Benoît. Le tableau détaille également les communes hors du périmètre de réingestion. [Tableau des 21 communes et motifs paginés](MESURE.md)

API locale sur 7480, écrans sur 10280. Tests ciblés, 25 Python et 6 front réussis. TypeScript passe sans diagnostic. La sauvegarde complète datée et la copie après réingestion se trouvent dans `.local/fix15/` du worktree. [Échecs avant correction](preuves/rouges.txt) · [Tests Python](preuves/tests-fin.txt) · [Tests front](preuves/tests-front.txt) · [Route HTTP](preuves/routes-finales.txt) · [Écrans et infobulles](preuves/ecran-final.txt) · [Réingestion](preuves/reingestion.txt) · [Empreintes avant](preuves/base-avant.txt) · [Empreintes après](preuves/base-apres.txt)
