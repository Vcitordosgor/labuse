# Rejeu des tests FIX-15

Deux archives des fichiers suivis ont été extraites avec `git archive` sous `.local/fix15-suite`. Seuls les fichiers de test ont été superposés. Pytest a importé le code de chaque archive, Vitest a compilé son front. Les chemins de connexion pour les tests désignaient `labuse_test`. Les répertoires temporaires ont été supprimés.

| Lot initial | Témoins rejoués | Sur 97da9366a | Sur cac55b070 |
|---|---|---:|---:|
| A | Identité binaire du PDF de Sainte-Marie, vérifiée par comparaison avec le GPU. Aucun correctif. | — | — |
| B | AU indicée de Bras-Panon et de Saint-Louis, UA 2.7 de L’Étang-Salé, sommaire d’Entre-Deux, intertitre de Saint-Benoît, réingestion de données seules | 6 échecs | 6 réussites |
| C | Mention sur les cinq cas de rattachement | 5 échecs | 5 réussites |
| D | Plafond du Tampon, places publiques de Saint-Louis, lien cliquable de Saint-Pierre | 3 échecs | 3 réussites |
| E | Dates de cinq communes, trois libellés de fiche, badge du règlement en faisabilité | 9 échecs | 9 réussites |
| F | Vote des Zattes, référence publique de La Possession, lien vers chaque livret de Saint-Paul | 3 échecs | 3 réussites |
| Complément de preuve écrit pendant cette reprise | Mention sur chacune de deux cartes, libellé de modification en couverture, lien cliquable vers le vote | 3 échecs | 3 réussites |

**Chronologie.** Les cinq premiers témoins du découpage figurent seuls dans `87c3abdd2`, avant le correctif `44a8674f1`. Le test des données seules figure dans le commit du correctif et la sortie rouge initiale archivée ne le mentionne pas. Pour les lots C à F, le journal d’origine conserve des sorties rouges, puis les tests et leurs corrections ont été commités ensemble. Le rejeu établit la régression entre versions. Git ne date pas l’ordre de rédaction à l’intérieur d’un commit. Les trois tests d’écran complémentaires datent de cette reprise. [Journal rouge d’origine](../preuves/rouges.txt)

**Sorties brutes de la comparaison.** [Python rouge, 24](97da9366a-python.txt) · [Python vert, 24](cac55b070-python.txt) · [Front rouge, 2](97da9366a-front.txt) · [Front vert, 2](cac55b070-front.txt) · [Compléments d’écran rouges, 3](97da9366a-restitution.txt) · [Compléments d’écran verts, 3](cac55b070-restitution.txt)

**Corrections de la reprise.** Le rejeu sur l’archive de `cac55b070` donne 15 échecs Python et un échec d’écran. Le contrôle final reprend ces cas avec les témoins historiques. [Python avant](cac55b070-avant-reprise-python.txt) · [Front avant](cac55b070-avant-reprise-front.txt) · [Python après](tests-python.txt) · [Front après](tests-front.txt)
