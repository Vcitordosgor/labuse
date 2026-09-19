# FICHE-TUILES-OUTILS-1 Lot 2 — audit des portes vers les outils (lecture seule)

## **11 outils sur 17 accessibles depuis la fiche.**

Preuve par capture : `captures/fiche-tuiles-outils1/portes/*.png` (chaque porte cliquée, l'outil
ouvert avec la parcelle). Témoins : 97410000AN0347 (PM, Saint-Benoît) et 97422000AK0924 (PP,
Le Tampon). Vérification du contexte parcelle = idu / commune / SIREN du propriétaire présents.

## Tableau 1 — les portes actuelles

| Porte (libellé) | Section | Outil visé (clé) | Condition d'affichage | Parcelle en contexte |
|---|---|---|---|---|
| Scan patrimoine du propriétaire | §1 Identité | patrimoine | `proprietaire_moral.siren` | ✓ (SIREN du propriétaire) |
| Courrier SPF | §1 Identité | courriers | `!proprietaire_moral` (PP) | ✓ (idu, courrierPrefill) |
| Annuaire PLU de la commune | §4 Urbanisme | plu | toujours | ✓ (insee + zone) |
| Vérif procédure PLU | §4 Urbanisme | plu | toujours | ✓ (selectedIdu préservé) |
| Pièges et risques | §5 Risques | risques | toujours | ✓ (selectedIdu) |
| Taxe d'aménagement | §7 Fiscalité | taxe-amenagement | `f.taxe_amenagement` | ✓ (parcelPrefill + selectedIdu) |
| Voir le marché de {commune} | §8 Marché | communes (fiche commune) | `f.commune` | ✓ (commune) |
| Taxe d'aménagement | §8 Marché | taxe-amenagement | toujours | ✓ (selectedIdu) — **DOUBLON de §7** |
| N parcelles « À suivre » (secteur) | §8 Marché | — (carte + filtres, pas un outil du menu) | `secteur_opportunites.n>0 && commune` | ✓ (filtre commune + recentrage) |
| Comparer des parcelles | §8 Marché | comparer | toujours | ✓ (addToCompare(idu) → liste, iduCourt) |
| Remonter le temps | §8 Marché | temps | `f.coords` | ✓ (parcelPrefill) |
| Faisabilité | §11 Simulation | programme | toujours | ✓ (parcelPrefill) |
| Calculette foncière | §11 Simulation | scoreur-adresse (alias M23 calculette-fonciere) | toujours | ✓ (calcPrefill) |
| Assemblage | §11 Simulation | assemblage | toujours | ✓ (parcelPrefill) |
| Courrier (tuile export) | Pied · Actions | courriers | toujours | ✓ (courrierPrefill) |
| Remonter le temps (tuile export) | Pied · Actions | temps | toujours | ✓ (parcelPrefill) |

**Aucune porte ne perd la parcelle** : 16/16 ouvrent l'outil avec la parcelle en contexte.
Les portes « setModule seul » (Vérif procédure, Pièges et risques, Taxe §8) marchent parce que
l'outil ADOPTE `selectedIdu` (jamais effacé par setModule). Vérifié : TaxeAmenagement lit
`selectedIdu` en continu.

## Tableau 2 — les 17 outils du menu : porte depuis la fiche ?

| # | Outil (menu) | Clé | Porte fiche ? | Section (ou section où elle manque) |
|---|---|---|---|---|
| 1 | PLU | plu | ✓ | §4 Urbanisme (Annuaire + Vérif procédure) |
| 2 | Permis | permis | ✗ | manque → **§9 Quartier** (permis à proximité) ou §1 (historique permis) |
| 3 | Communes | communes | ✓ | §8 Marché (Voir le marché de X) |
| 4 | Étudier un bien | scoreur-adresse | ✓ | §11 Simulation (Calculette foncière, alias) |
| 5 | Scan patrimoine | patrimoine | ✓ | §1 Identité |
| 6 | Assemblage | assemblage | ✓ | §11 Simulation |
| 7 | Comparer des parcelles | comparer | ✓ | §8 Marché |
| 8 | Pièges et risques | risques | ✓ | §5 Risques |
| 9 | Étude de zone | etude-zone | ✗ | manque → **§9 Quartier** (chalandise / isochrone, déjà rendu là) |
| 10 | Remonter le temps | temps | ✓ | §8 Marché + tuile export |
| 11 | Faisabilité | programme | ✓ | §11 Simulation |
| 12 | Taxe d'aménagement | taxe-amenagement | ✓ | §7 Fiscalité (+ §8 Marché, doublon) |
| 13 | Prospection solaire | prospection-solaire | ✗ | manque → **§3 Bâti** (toit/soleil) ou §10 Potentiel |
| 14 | Densifier l'existant | renouvellement | ✗ | manque → **§10 Potentiel** (densification) |
| 15 | Blocs fonciers | blocs-fonciers | ✗ | manque → **§1 Identité** (foncier du propriétaire, près de Scan patrimoine) |
| 16 | Successions à venir | successions | ✗ | manque → **§1 Identité** (propriétaire) |
| 17 | Courrier propriétaire | courriers | ✓ | §1 Identité + tuile export |

Accessibles (11) : 1,3,4,5,6,7,8,10,11,12,17. Manquants (6) : 2,9,13,14,15,16.

## Portes mal placées (outil sans rapport avec le sujet de la section)
- **§8 Marché → « Taxe d'aménagement »** : la taxe est un levier FISCAL/projet, pas du marché
  (prix DVF). Elle a déjà son foyer en §7 Fiscalité. → mal placée + doublon (voir ci-dessous).
- **§8 Marché → « Comparer des parcelles »** et **« Remonter le temps »** : borderline — relèvent
  du projet / de l'identité de la parcelle plus que du marché-prix. À surveiller (pas un contresens).
- Les autres sont bien placées (patrimoine→§1, PLU→§4, risques→§5, faisabilité/calculette/
  assemblage→§11).

## Doublon « Taxe d'aménagement » — §7 et §8
**DEUX portes vers le MÊME outil** (`taxe-amenagement`), sous-titres différents :
- §7 Fiscalité : « Changer les hypothèses… » — conditionnelle (`f.taxe_amenagement`).
- §8 Marché : « Estimation détaillée pour un projet ici… » — inconditionnelle.
Les deux marchent (parcelle via `selectedIdu`). C'est une redondance : recommandation (hors
correction) — garder UNE porte, en §7 Fiscalité (son foyer), retirer celle de §8.

*Lot 2 = lecture seule, aucune correction appliquée.*
