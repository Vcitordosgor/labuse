# M51-P2 — Saint-Benoît : les fiches AU vs la calibration servie (LECTURE SEULE · liste d'écarts)

**Aucun changement de calibration.** Constat sur pièces (`97410_reglement_20200206.pdf`, opposable
GPU idurba `97410_PLU_20200206`, garde idurba+sha OK, ingéré P1). Les arbitrages viennent sur cette liste.

## Les fiches AU passées une à une (18 présentes — **N°04 absente**)
| Fiche | zone | recul voirie | régime 1AU | ER | PPR | secteur (p.PDF) |
|---|---|---|---|---|---|---|
| N°01 | AUp | 3 m | oui | oui | oui | Beauvallon pôle d'activités (54) |
| N°02 | AUb | **10 m** | oui | oui | — | Bourbier les Hauts – ch. Montjol (55) |
| N°03 | AUe | 3 m | oui | oui | oui | Beaulieu zone commerciale (56) |
| N°05 | AUa | 3 m | oui | — | — | Le Conardel habitat (57) |
| N°06 | AUb | 3 m | oui | — | — | Bras-Canot Sarda Garriga (59) |
| N°07 | AUb | 3 m | oui | oui | oui | Bras-Canot Prévoisy (60) |
| N°08 | AUa | 3 m | oui | oui | — | Le Cap les Bas Lataniers (61) |
| N°09 | AUa | 3 m | oui | oui | — | Le Cap les Bas Jonquilles (62) |
| N°10 | AUb | 3 m | oui | — | — | Le Cap les Bas Palmistes (63) |
| N°11 | AUb | 3 m | oui | — | — | Le Cap les Bas Impasse Louis (64) |
| N°12 | AUb | 3 m | oui | — | — | Le Cap les Hauts Lot. Baies (65) |
| N°13 | AUb | 3 m | oui | — | — | Le Cap les Hauts Lee-Fong (66) |
| N°14 | AUb | 3 m | oui | — | oui | Sainte-Anne ch. Blémir (67) |
| N°15 | AUb | 3 m | oui | oui | — | Sainte-Anne ch. Jacquemin (68) |
| N°16 | AUb | 3 m | oui | — | — | Sainte-Anne ch. Morange (69) |
| N°17 | AUb | 3 m | oui | — | — | Petit Saint-Pierre ch. Gallias (70) |
| N°18 | AUa | 3 m | oui | oui | — | Petit Saint-Pierre ch. Impérial (71) |
| N°19 | AUb | 3 m | oui | — | oui | Cambourg Amaryllis II (72) |

*(Pages PDF — pagination du document AMBIGUË, 2ᵉ bloc « Page 1..114 » ; ces p.PDF sont celles du fichier.)*

## Ce que la calibration SERT pour AU (`config/plu_saint_benoit.yaml`)
- `zones: {}` — **hauteurs AU DÉ-CALIBRÉES** (secteurs graphiques, arbitrage Vic 28/07) ✔ cohérent :
  les 18 fiches ne donnent **aucune hauteur** → la dé-calibration est confirmée, **pas d'écart** ici.
- Règles génériques AU servies : emprise 80 % (Art. AU 5), limites séparatives 1 m (Art. AU 7),
  espaces libres 20 % perméable (Art. AU 9), stationnement (Art. AU 12).
- `zones_au_st` (habitat interdit, capacité zéro) : Ue, Up, Ut, AUe3, AUp1.

## ÉCARTS — pour ton arbitrage (rien appliqué)
1. **Recul voirie NON servi.** Chaque fiche impose un **recul de 3 m** de la voie (**10 m** pour la
   fiche N°02, AUb Bourbier). La calibration sert le recul *séparatif* (1 m) mais **pas le recul
   voirie**. Un recul de 3–10 m réduit l'emprise constructible d'une parcelle AU → la capacité AU
   servie peut être **sur-estimée**. Le plus fort : N°02 (10 m). **Arbitrage : intégrer le recul
   voirie AU (3 m défaut, 10 m N°02) ou l'assumer hors périmètre ?**
2. **Régime 1AU (opération d'ensemble) — les 18 fiches le portent** : « constructions acceptées
   seulement dans une opération d'ensemble réalisant les équipements internes, OU après leur
   réalisation ». **Arbitrage : la capacité AU servie reflète-t-elle cette porte 1AU** (une parcelle
   AU isolée n'est pas constructible seule) **ou est-elle comptée comme constructible directe ?**
3. **N°04 ABSENTE** de la séquence AU (01-03, 05-19). 18 fiches AU, pas 19. **Constat brut, non
   fabriqué** : soit un trou de numérotation, soit une fiche classée hors bloc AU. **Arbitrage :
   vérifier en mairie si N°04 existe (zone AU non couverte ici).**

## Couvert AILLEURS (référencé par les fiches, PAS un écart de calibration)
- **PPR R1 non constructible** (8 fiches, ex. N°19 Cambourg : « secteurs en zone R1 non constructible,
  PPR approuvé 02/10/2017 ») → servi par la **couche PPR** (campagne PPR rouge/bleu). *À vérifier :
  la couche PPR est-elle active sur ces secteurs AU de Saint-Benoît ?* (hors calibration règlement).
- **Emplacements réservés** (8 fiches) → couche ER/servitudes, pas la calibration règlement.
- **Boisements à conserver** (N°19) → EBC/servitude, hors calibration.

## Incertitude M40 — RECONSIGNÉE, non fabriquée
L'annuaire sert le **PLU 2020 opposable** (idurba `97410_PLU_20200206`, présent au GPU, garde OK).
D'**éventuelles modifications n°2/n°3** approuvées postérieurement **ne sont PAS au GPU** (à confirmer
en mairie, hors open-data) — comme en M40. Rien n'est inventé : le verbatim servi est celui du 2020.
