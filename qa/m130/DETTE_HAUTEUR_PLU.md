# DETTE — Zones sortant en « hauteur non renseignée au PLU calibré »

**M130-12 §Dette.** Zones dont `resolve_zone` ne renvoie AUCUNE hauteur (he et hf
nuls) → la ligne « Hauteur PLU » affiche « non renseignée au PLU calibré ». Non
un trou silencieux : consigné nommément (commune, zone, millésime).

## Constaté sur les 4 packs de QA (M130-12)

| Commune | Zone | Famille | Millésime | Lignes | Nature |
|---|---|---|---|---|---|
| Saint-Pierre (97416) | `A` | agricole | 25/06/2024 | 8 | zone agricole — hauteur d'habitat non réglementée / non outillée |
| Saint-Pierre (97416) | `N` | naturelle | 25/06/2024 | 1 | zone naturelle — idem |

P1 (toute l'île, hors étage 0), P2 (Le Tampon), P4 : **aucune** zone « non
renseignée » (toutes les zones servies portent une règle, directe ou par renvoi).

## Lecture — ce qu'on sait, ce qu'on ne sait pas (panne ≠ absence)

**On ne sait pas** si le règlement de Saint-Pierre chiffre une hauteur en A / N.
Fait établi : `config/plu_saint_pierre.yaml` **ne calibre que les zones
constructibles U / AU** (en-tête du fichier : « règles chiffrées par zone
constructible (U / AU) »). Les zones A / N **n'y sont pas extraites** →
`resolve_zone` retombe sur l'estimation générique (he = hf = None).

Or le règlement de Saint-Pierre **contient bien des chapitres A et N** :
`config/plu_saint_pierre.yaml` (commentaire) cite « N, Nr, Nc, Ncu, Nci, Np,
Npnr, Nge (chap. p.212-221) » et une règle A (« logement de l'exploitant agricole
limité à 1/exploitation »). Leur **hauteur n'a simplement pas été lue/extraite**.

Donc : « non renseignée au PLU calibré » est **l'état honnête d'une donnée absente
de notre calibrage** — pas une affirmation que le règlement ne porte pas de règle.
On ne suppose rien. Pour lever la dette : lire le chap. A et le chap. N
(p.212-221) du règlement Saint-Pierre (25/06/2024) et, si une hauteur y figure,
l'ajouter au YAML ; sinon la marquer explicitement « non réglementée au règlement
(chap. X, p.Y) » — fait sourcé, distinct de « non outillée dans le YAML ».

Aucune zone **constructible** (U / AU) n'est sortie « non renseignée » sur les
packs de QA : la couverture PLU calibré Le Tampon / Saint-Pierre est complète
pour les zones servies (cf. tableau de couverture, rapport M130-12 §A).
