# PHASE 0 J3 — étape 1 : PROPOSITION golden 32 → ~120 (à valider par Vic)

**Statut : PROPOSITION — STOP validation ligne à ligne.** Je ne m'auto-certifie AUCUNE attendue :
Vic est la vérité terrain. Le noyau des **32 golden existants est conservé tel quel** (inchangé) ;
ci-dessous **84 additions** (total **116**) sélectionnées de façon **déterministe** (script
`scripts/j3_golden_proposition.py`, lecture seule, run servi `q_v6_m8`).

## Stratification obtenue
- **Communes** : les **24** communes couvertes à **≥2** (dont Saint-Philippe 97417, RNU).
- **Tiers v2** : chaque tier `brulante / chaude / reserve_fonciere / a_creuser / ecartee` à **≥5**.
- **Motifs d'exclusion (étage 0)** : chacun des 10 motifs majeurs à **≥8** — eau, zone A/N, PPR/aléa
  fort, pente, micro-surface, OSM faux positif, foncier public, emprise linéaire, emprise routière,
  prescription PLU (ER/EBC).
- **Cas limites** (×4 chacun) : copro flaggée, bailleur social (V NULL + badge), **événement rouge**
  (DISTINCT du canari `97415000AC0253`, non dupliqué), vue mer dégagée, SDP résiduelle > 0,
  propriétaire personne physique (masquage privacy).

## Comment valider
Pour chaque ligne : l'IDU, sa commune, son **tier v2 actuel** (run servi), le **motif** d'exclusion
le cas échéant, le **cas limite** le cas échéant, et une justification d'une ligne. La colonne « verdict
actuel » = ce que le run servi produit AUJOURD'HUI ; à la validation, ce verdict devient l'attendue gelée
(étape 2), après ton feu vert. **Barre/annote les lignes à écarter ou à corriger.**

> Rappel méthode (mandat) : l'extension AJOUTE, ne modifie jamais une attendue existante. Les 32 du
> noyau ne sont pas listés ici (inchangés).

_Distribution : 

| # | IDU | Commune | Tier v2 | Motif exclusion | Cas limite | Justification |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `97401000AB0001` | Les Avirons | ecartee | PPR/aléa fort | — | exclusion étage 0 : PPR/aléa fort |
| 2 | `97401000AB0002` | Les Avirons | ecartee | foncier public | — | exclusion étage 0 : foncier public |
| 3 | `97401000AD0016` | Les Avirons | a_creuser | — | propriétaire personne physique (masquage) | cas limite : propriétaire personne physique (masquage) |
| 4 | `97401000AD0095` | Les Avirons | a_creuser | — | propriétaire personne physique (masquage) | cas limite : propriétaire personne physique (masquage) |
| 5 | `97401000AD0124` | Les Avirons | a_creuser | — | SDP résiduelle > 0 | cas limite : SDP résiduelle > 0 |
| 6 | `97401000AD0192` | Les Avirons | a_creuser | — | SDP résiduelle > 0 | cas limite : SDP résiduelle > 0 |
| 7 | `97401000AD0971` | Les Avirons | a_creuser | — | bailleur social (V NULL + badge) | cas limite : bailleur social (V NULL + badge) |
| 8 | `97401000AD0973` | Les Avirons | ecartee | micro-surface | bailleur social (V NULL + badge) | cas limite : bailleur social (V NULL + badge) |
| 9 | `97401000AD1599` | Les Avirons | ecartee | bati | copro flaggée | cas limite : copro flaggée |
| 10 | `97401000AI0394` | Les Avirons | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 230916) — Les Avirons |
| 11 | `97401000AM0193` | Les Avirons | a_creuser | — | vue mer dégagée | cas limite : vue mer dégagée |
| 12 | `97401000AM0213` | Les Avirons | a_creuser | — | vue mer dégagée | cas limite : vue mer dégagée |
| 13 | `97401000AM0380` | Les Avirons | ecartee | bati | copro flaggée | cas limite : copro flaggée |
| 14 | `97401000AN0388` | Les Avirons | ecartee | bati | événement rouge (≠ canari) | cas limite : événement rouge (≠ canari) |
| 15 | `97401000AN0797` | Les Avirons | ecartee | bati | événement rouge (≠ canari) | cas limite : événement rouge (≠ canari) |
| 16 | `97402000AB0001` | Bras-Panon | ecartee | pente forte | — | exclusion étage 0 : pente forte |
| 17 | `97402000AB0002` | Bras-Panon | ecartee | zone A/N inconstructible | — | exclusion étage 0 : zone A/N inconstructible |
| 18 | `97402000AI0725` | Bras-Panon | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 235828) — Bras-Panon |
| 19 | `97403000AH0341` | Entre-Deux | ecartee | emprise linéaire (délaissé) | — | exclusion étage 0 : emprise linéaire (délaissé) |
| 20 | `97403000AK0044` | Entre-Deux | ecartee | emprise routière | — | exclusion étage 0 : emprise routière |
| 21 | `97403000AR1424` | Entre-Deux | a_creuser | — | — | tier v2 « a_creuser » (rang 145) — Entre-Deux |
| 22 | `97404000AC0011` | L'Étang-Salé | ecartee | micro-surface | — | exclusion étage 0 : micro-surface |
| 23 | `97404000AC1225` | L'Étang-Salé | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 230084) — L'Étang-Salé |
| 24 | `97404000AD0194` | L'Étang-Salé | ecartee | OSM faux positif | — | exclusion étage 0 : OSM faux positif |
| 25 | `97405000AB0001` | Petite-Île | ecartee | zone A/N inconstructible | — | exclusion étage 0 : zone A/N inconstructible |
| 26 | `97405000AD0728` | Petite-Île | ecartee | eau/hydrographie | — | exclusion étage 0 : eau/hydrographie |
| 27 | `97405000AR1779` | Petite-Île | chaude | — | — | tier v2 « chaude » (rang 263) — Petite-Île |
| 28 | `97406000AB0001` | La Plaine-des-Palmistes | ecartee | pente forte | — | exclusion étage 0 : pente forte |
| 29 | `97406000AC0506` | La Plaine-des-Palmistes | ecartee | prescription PLU (ER/EBC) | — | exclusion étage 0 : prescription PLU (ER/EBC) |
| 30 | `97406000AW1250` | La Plaine-des-Palmistes | a_creuser | — | — | tier v2 « a_creuser » (rang 590) — La Plaine-des-Palmistes |
| 31 | `97407000AB0009` | Le Port | ecartee | foncier public | — | exclusion étage 0 : foncier public |
| 32 | `97407000AB0046` | Le Port | ecartee | OSM faux positif | — | exclusion étage 0 : OSM faux positif |
| 33 | `97407000AV0096` | Le Port | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 230857) — Le Port |
| 34 | `97408000AB0007` | La Possession | ecartee | PPR/aléa fort | — | exclusion étage 0 : PPR/aléa fort |
| 35 | `97408000AB0157` | La Possession | ecartee | emprise linéaire (délaissé) | — | exclusion étage 0 : emprise linéaire (délaissé) |
| 36 | `97408000AP1610` | La Possession | chaude | — | — | tier v2 « chaude » (rang 3) — La Possession |
| 37 | `97409000AB0011` | Saint-André | ecartee | eau/hydrographie | — | exclusion étage 0 : eau/hydrographie |
| 38 | `97409000AB0119` | Saint-André | ecartee | micro-surface | — | exclusion étage 0 : micro-surface |
| 39 | `97409000AR1260` | Saint-André | brulante | — | — | tier v2 « brulante » (rang 98) — Saint-André |
| 40 | `97410000AB0010` | Saint-Benoît | ecartee | prescription PLU (ER/EBC) | — | exclusion étage 0 : prescription PLU (ER/EBC) |
| 41 | `97410000AB0343` | Saint-Benoît | ecartee | emprise routière | — | exclusion étage 0 : emprise routière |
| 42 | `97410000CD0926` | Saint-Benoît | a_creuser | — | — | tier v2 « a_creuser » (rang 2721) — Saint-Benoît |
| 43 | `97411000AB0006` | Saint-Denis | ecartee | PPR/aléa fort | — | exclusion étage 0 : PPR/aléa fort |
| 44 | `97411000AB0007` | Saint-Denis | ecartee | foncier public | — | exclusion étage 0 : foncier public |
| 45 | `97411000HK0083` | Saint-Denis | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 231103) — Saint-Denis |
| 46 | `97412000AB0001` | Saint-Joseph | ecartee | zone A/N inconstructible | — | exclusion étage 0 : zone A/N inconstructible |
| 47 | `97412000AB0002` | Saint-Joseph | ecartee | pente forte | — | exclusion étage 0 : pente forte |
| 48 | `97412000CP0462` | Saint-Joseph | brulante | — | — | tier v2 « brulante » (rang 41) — Saint-Joseph |
| 49 | `97413000AC0083` | Saint-Leu | ecartee | emprise linéaire (délaissé) | — | exclusion étage 0 : emprise linéaire (délaissé) |
| 50 | `97413000AC0115` | Saint-Leu | ecartee | micro-surface | — | exclusion étage 0 : micro-surface |
| 51 | `97413000CR0344` | Saint-Leu | a_creuser | — | — | tier v2 « a_creuser » (rang 148) — Saint-Leu |
| 52 | `97414000CH0586` | Saint-Louis | ecartee | prescription PLU (ER/EBC) | — | exclusion étage 0 : prescription PLU (ER/EBC) |
| 53 | `97414000CI0800` | Saint-Louis | ecartee | emprise routière | — | exclusion étage 0 : emprise routière |
| 54 | `97414000CV0772` | Saint-Louis | chaude | — | — | tier v2 « chaude » (rang 99) — Saint-Louis |
| 55 | `97415000AH0410` | Saint-Paul | ecartee | OSM faux positif | — | exclusion étage 0 : OSM faux positif |
| 56 | `97415000AI0155` | Saint-Paul | ecartee | eau/hydrographie | — | exclusion étage 0 : eau/hydrographie |
| 57 | `97415000BW1132` | Saint-Paul | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 229778) — Saint-Paul |
| 58 | `97416000CD0006` | Saint-Pierre | ecartee | zone A/N inconstructible | — | exclusion étage 0 : zone A/N inconstructible |
| 59 | `97416000CD0011` | Saint-Pierre | ecartee | PPR/aléa fort | — | exclusion étage 0 : PPR/aléa fort |
| 60 | `97416000EY1406` | Saint-Pierre | brulante | — | — | tier v2 « brulante » (rang 27) — Saint-Pierre |
| 61 | `97417000AC0003` | Saint-Philippe | ecartee | pente forte | — | exclusion étage 0 : pente forte |
| 62 | `97417000AC0004` | Saint-Philippe | ecartee | foncier public | — | exclusion étage 0 : foncier public |
| 63 | `97417000BC0150` | Saint-Philippe | a_creuser | — | — | tier v2 « a_creuser » (rang 893) — Saint-Philippe |
| 64 | `97418000AC0003` | Sainte-Marie | ecartee | emprise routière | — | exclusion étage 0 : emprise routière |
| 65 | `97418000AC0149` | Sainte-Marie | ecartee | micro-surface | — | exclusion étage 0 : micro-surface |
| 66 | `97418000AT2542` | Sainte-Marie | chaude | — | — | tier v2 « chaude » (rang 13) — Sainte-Marie |
| 67 | `97419000AC0076` | Sainte-Rose | ecartee | emprise linéaire (délaissé) | — | exclusion étage 0 : emprise linéaire (délaissé) |
| 68 | `97419000AD0155` | Sainte-Rose | ecartee | eau/hydrographie | — | exclusion étage 0 : eau/hydrographie |
| 69 | `97419000AH0201` | Sainte-Rose | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 233639) — Sainte-Rose |
| 70 | `97420000AB0291` | Sainte-Suzanne | ecartee | OSM faux positif | — | exclusion étage 0 : OSM faux positif |
| 71 | `97420000AB1549` | Sainte-Suzanne | ecartee | prescription PLU (ER/EBC) | — | exclusion étage 0 : prescription PLU (ER/EBC) |
| 72 | `97420000BD0643` | Sainte-Suzanne | chaude | — | — | tier v2 « chaude » (rang 280) — Sainte-Suzanne |
| 73 | `97421000AB0001` | Salazie | ecartee | zone A/N inconstructible | — | exclusion étage 0 : zone A/N inconstructible |
| 74 | `97421000AB0003` | Salazie | ecartee | pente forte | — | exclusion étage 0 : pente forte |
| 75 | `97421000AV0815` | Salazie | brulante | — | — | tier v2 « brulante » (rang 308) — Salazie |
| 76 | `97422000AB0001` | Le Tampon | ecartee | foncier public | — | exclusion étage 0 : foncier public |
| 77 | `97422000AB0002` | Le Tampon | ecartee | PPR/aléa fort | — | exclusion étage 0 : PPR/aléa fort |
| 78 | `97422000AS0911` | Le Tampon | a_creuser | — | — | tier v2 « a_creuser » (rang 197) — Le Tampon |
| 79 | `97423000AB0019` | Les Trois-Bassins | ecartee | OSM faux positif | — | exclusion étage 0 : OSM faux positif |
| 80 | `97423000AB0023` | Les Trois-Bassins | ecartee | emprise routière | — | exclusion étage 0 : emprise routière |
| 81 | `97423000AH0901` | Les Trois-Bassins | reserve_fonciere | — | — | tier v2 « reserve_fonciere » (rang 232670) — Les Trois-Bassins |
| 82 | `97424000AC0060` | Cilaos | ecartee | micro-surface | — | exclusion étage 0 : micro-surface |
| 83 | `97424000AC0252` | Cilaos | ecartee | prescription PLU (ER/EBC) | — | exclusion étage 0 : prescription PLU (ER/EBC) |
| 84 | `97424000AH0971` | Cilaos | chaude | — | — | tier v2 « chaude » (rang 229) — Cilaos |

---
## STOP — validation Vic

Valide (ou amende) cette liste **ligne à ligne**. Après ton accord, j'exécute l'**étape 2** :
intégration au format de `qa/golden_check.py` (32 d'origine inchangés + additions validées), passage du
golden élargi **N/N** sur `q_v6_m8`, et branchement comme préambule obligatoire de l'arène. Aucune
attendue n'est gelée avant ta validation.
