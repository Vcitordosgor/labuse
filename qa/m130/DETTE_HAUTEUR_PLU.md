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

## Lecture

Les zones **A / N** (agricole / naturelle) ne portent le plus souvent **aucune
hauteur d'habitat** au règlement (vocation non résidentielle) : « non renseignée
au PLU calibré » y est vraisemblablement **légitime**, pas une lacune de
calibrage. À confirmer si l'on veut distinguer « non réglementée au PLU » (fait
sourcé) de « non outillée dans notre YAML » (lacune) — cela suppose de lire le
règlement A/N de chaque commune. Tant que ce n'est pas fait, l'état honnête reste
« non renseignée au PLU calibré » (on ne prétend pas savoir).

Aucune zone **constructible** (U / AU) n'est sortie « non renseignée » sur les
packs de QA : la couverture PLU calibré Le Tampon / Saint-Pierre est complète
pour les zones servies (cf. tableau de couverture, rapport M130-12 §A).
