# MANDAT DVF — Le prix au m² affiché doit être un prix de TERRAIN

> Mandat DÉDIÉ, issu du diagnostic M70 (déc. 10). Ne PAS le glisser dans une passe visuelle : il
> touche la **magnitude de scoring** de 431 663 parcelles. Séquencer comme le rejeu.

## Pourquoi (mesuré en M70)

Le prix au m² est le premier chiffre que le client regarde. Se tromper d'un facteur 2 dessus
décrédibilise tout le reste. Or la fiche affiche aujourd'hui DEUX prix au m² incompatibles sur la
même parcelle (canari 97415000AC0253 : **379 €/m²** ligne cascade vs **173 €/m²** secteur).

**Mesure de ce que chaque chiffre calcule :**

| | Ligne cascade « Marché DVF » (379) | Secteur, tiroir (173) |
|---|---|---|
| Assiette | `valeur_fonciere ÷ surface_terrain` | `valeur_fonciere ÷ surface_terrain` |
| Types de biens | **TOUS** (maison, appart, terrain…) | **terrain nu UNIQUEMENT** |
| Périmètre | rayon 250 m (centroïde) | secteur cadastral (insee+000+section) |
| Période | 5 ans glissants | 2021-2025 |
| Aberrants | **aucune exclusion** | aucune exclusion |
| Grain / n | mutation ; **canari = 1 seule** (avec bâti) | mutation, ventes ; canari = 3 (terrain) |

**Verdict** : le 379 = valeur TOTALE d'une maison ÷ sa surface de TERRAIN, sur 1 seule mutation.
Il **compte du bâti au m² de terrain** → ce n'est PAS un prix foncier, c'est un chiffre non
interprétable affiché comme un prix au m². **À supprimer, pas à réconcilier.** (Code : `dvf_stats`
dans `cascade/context.py`, ligne construite dans `cascade/layers/phase2.py` `DvfLayer`.)

## Ce que le mandat doit livrer (décisions Vic)

1. **Le €/m² AFFICHÉ = prix de TERRAIN** : ventes de **terrain nu uniquement**. Le **173** (source
   `dvf_secteur_medianes` type=terrain) est le bon chiffre.
2. **Le prix du BÂTI (225 €/m² sur le canari) peut exister mais SÉPARÉMENT**, jamais confondu avec
   le terrain (ni divisé par la surface de terrain).
3. **Un chiffre appuyé sur 1 mutation n'est pas une médiane.** Définir un **seuil minimum**
   (3 ventes ? 5 ?) ; en dessous → « échantillon insuffisant » (comme le fait déjà le one-pager),
   jamais un nombre affiché comme robuste.
4. **Rayon 250 m vs secteur cadastral = deux périmètres différents. TRANCHER lequel fait foi** — un
   seul point de calcul (doctrine « un critère = un endroit », mécanisme M75 : `note` unique,
   vérif programmatique fiche.note == export.note).

## Contrainte de sécurité (comme ENS/rejeu)

Corriger le €/m² touche la **magnitude de scoring** de la couche DVF (composante prix, `w_price`
dans `DvfLayer`) → change le classement. **Mesurer l'effet sur le classement AVANT/APRÈS et le
rapporter avant tout changement servi.** Ne rien basculer avant que Vic voie le delta. Séquencer
après le golden-rebase, avec le mandat rejeu.

## Périmètre à ne PAS oublier
- La ligne cascade `dvf` (verbatim depuis le run gelé) : sa correction n'est effective qu'au rejeu.
- L'affichage : ligne cascade « Marché DVF », valeur/MicroSpark du tiroir Marché (`dvfSecteur`),
  encart voisinage (`voisinage_proche`), bloc `market_signal` (déjà single-calc), et **les exports
  PDF** (mêmes libellés au mot près).
- Vérifier qu'aucun autre consommateur (`score_e`, `bilan`, `carnet`, `fiche_ask`, `moteurs`) ne
  propage le €/m² bâti-contaminé.
