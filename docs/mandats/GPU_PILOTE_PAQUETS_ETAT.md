# GPU-PILOTE — extension 23 communes : ÉTAT DES ARCHIVES (garde-fou avant extraction)

> Mapping INSEE→commune **autoritaire = `grid.title` du GPU (IGN)**, PAS le champ `commune` de la
> base (qui étiquetait à tort 97412 « Saint-Philippe » : c'est Saint-Joseph — corrigé sur signalement
> Vic). Garde-fou version : version LOCALE vs EN VIGUEUR (`?grid=<insee>`, effectiveStatus). Léger
> (métadonnées) ; byte-identité prouvée par sha256 sur L'Étang-Salé → le nom d'archive fait foi.
> **Rien extrait, rien écrit en base, aucun YAML modifié.**

## Matrice des 24 communes (noms GPU autoritaires)

| INSEE | commune | archive locale | garde-fou vs en vigueur | statut |
|---|---|---|---|---|
| 97401 | Les Avirons | 97401_PLU_20241206 | = 20241206 | **OK à jour** |
| 97402 | Bras-Panon | 97402_PLU_20260428 | = 20260428 | **OK à jour** |
| 97403 | Entre-Deux | 97403_PLU_20240924 | = 20240924 | **OK à jour** |
| 97404 | L'Étang-Salé | 97404_PLU_20250917 | = 20250917 | **FAIT (Phase 2)** |
| 97405 | Petite-Île | vide (0 o) | en vigueur 20230609 | à télécharger |
| 97406 | La Plaine-des-Palmistes | 97406_PLU_20230527 | = 20230527 | **OK à jour** |
| 97407 | Le Port | vide (0 o) | en vigueur 20241209 | à télécharger |
| 97408 | La Possession | vide (0 o) | en vigueur 20251217 | à télécharger |
| 97409 | Saint-André | absente | **aucun doc GPU (`[]`)** | RNU ? à confirmer |
| 97410 | Saint-Benoît | absente (PDF seul) | en vigueur 20200206 | à télécharger |
| 97411 | Saint-Denis | 97411_PLU_20240220 | **en vigueur 20260423** | **PÉRIMÉ** — retélécharger |
| 97412 | Saint-Joseph | 97412_PLU_20190626 | **en vigueur 20251210** | **PÉRIMÉ** — retélécharger |
| 97413 | Saint-Leu | absente | **aucun doc GPU (`[]`)** | RNU ? à confirmer |
| 97414 | Saint-Louis | vide (0 o) | en vigueur 20251218 | à télécharger |
| 97415 | Saint-Paul | 97415_PLU_20251217 | = 20251217 | **OK à jour** |
| 97416 | Saint-Pierre | 97416_PLU_20240625 | = 20240625 | **OK à jour** |
| 97417 | **Saint-Philippe** | absente | **aucun doc GPU (`[]`)** | **RNU — cohérent avec ta calibration** |
| 97418 | Sainte-Marie | absente (PDF seul) | en vigueur 20251126 | à télécharger |
| 97419 | Sainte-Rose | 97419_PLU_20190504 | = 20190504 | **OK à jour** |
| 97420 | Sainte-Suzanne | vide (0 o) | en vigueur 20250929 | à télécharger |
| 97421 | Salazie | vide (0 o) | en vigueur 20220524 | à télécharger |
| 97422 | Le Tampon | vide (0 o) | en vigueur 20230811 | à télécharger |
| 97423 | Les Trois-Bassins | 97423_PLU_20220602 | = 20220602 | **OK à jour** |
| 97424 | Cilaos | 97424_PLU_20240213 | = 20240213 | **OK à jour** |

## Correction Saint-Philippe (mon erreur, ta calibration valide)
J'avais interrogé 97412 (= Saint-Joseph) en croyant Saint-Philippe. Sur le **bon code 97417**, le GPU
renvoie `[]` — **aucun PLU publié**. C'est **cohérent avec « Saint-Philippe RNU, pas de PLU »** : ta
calibration n'est PAS contredite. (Saint-Joseph 97412, lui, a bien un PLU en vigueur 2025, et ma
copie locale de 2019 est périmée.)

## Les 14 communes à me fournir (liste pour ta vérification)

**A — PÉRIMÉES (retélécharger la version en vigueur)** — 2 :
| INSEE | commune | local | en vigueur |
|---|---|---|---|
| 97411 | Saint-Denis | 2024-02-20 | **2026-04-23** |
| 97412 | Saint-Joseph | 2019-06-26 | **2025-12-10** |

**B — VIDES (0 octet, à télécharger)** — 7 :
| INSEE | commune | en vigueur |
|---|---|---|
| 97405 | Petite-Île | 2023-06-09 |
| 97407 | Le Port | 2024-12-09 |
| 97408 | La Possession | 2025-12-17 |
| 97414 | Saint-Louis | 2025-12-18 |
| 97420 | Sainte-Suzanne | 2025-09-29 |
| 97421 | Salazie | 2022-05-24 |
| 97422 | Le Tampon | 2023-08-11 |

**C — ABSENTES mais PLU existe sur GPU (à télécharger)** — 2 :
| INSEE | commune | en vigueur |
|---|---|---|
| 97410 | Saint-Benoît | 2020-02-06 |
| 97418 | Sainte-Marie | 2025-11-26 |

**D — ABSENT du GPU (`[]`) → statut `a_verifier`, JAMAIS « RNU » par défaut** — 3 :
Le GPU n'est PAS exhaustif (arbitrage Vic) : une commune peut avoir un PLU OPPOSABLE non publié
(cas Saint-André : règlement 2019 dépublié, opposabilité inconnue, appel mairie en cours). Donc pour
ces 3 : **motif « absent du GPU, opposabilité à confirmer auprès de la commune ».**

| INSEE | commune | statut | parcelles servies (q_v7) | en tête | brûlantes |
|---|---|---|---|---|---|
| 97409 | Saint-André | **a_verifier** (PLU 2019 dépublié, opposabilité — appel mairie en cours) | 22 600 | **413** | 7 |
| 97413 | Saint-Leu | **Sourcé** (voir gravure ci-dessous) | 22 959 | 348 | 9 |
| 97417 | Saint-Philippe | **Sourcé — RNU calibrée** (voir gravure ci-dessous) | 4 162 | 0 | 0 |

### GRAVURE — Saint-Leu (tranché mairie)
**Document en vigueur = PLU 2007 (26/02/2007). Source = mairie. Statut = Sourcé.** La révision
repart en enquête publique après les élections (délai long) → le 2007 reste opposable. **Le
`a_verifier` tombe.** Les 348 têtes / 9 brûlantes reposent donc sur un **zonage VALIDE** (AGORAH,
idurba `97413_20070226`). **Réserve gravée** : les **règles chiffrées restent NON calibrées**
(`calibree=False` à 100% sur les têtes) — hauteurs/emprises = estimation générique, à calibrer depuis
le règlement 2007 si on veut sortir du repli. Zonage sûr, règles devinées.

### GRAVURE — Saint-Philippe (RNU calibrée)
**Statut = Sourcé, RNU.** `config/rnu_communes.yaml` l'établit avec preuves (GPU DU_97417=0,
CC_97417=0 ; AGORAH 0 enregistrement, live 26/07/2026). **Traitée par la branche PAU/RNU, pas par le
repli aveugle** : 0 `plu_gpu_zone` parasite ; `parcel_pau` = **2 373 / 4 162 parcelles dans la PAU**,
consommées par `plancher_c` (seules les parcelles en PAU peuvent être chaudes ; hors-PAU exclues) →
0 en tête, comportement RNU conservateur attendu. Les règles dimensionnelles = défaut national (RNU,
aucun zonage communal à calibrer) — correct. **Le `a_verifier` tombe.**

**BLOQUANT résiduel** : seul **Saint-André** reste ouvert — 413 têtes / 7 brûlantes sur PLU 2019
dépublié, opposabilité en attente de ta mairie. Saint-Leu résolu (zonage valide, règles à calibrer) ;
Saint-Philippe résolu (RNU). Total servi île de référence : 77 718.

→ **11 téléchargeables** (A+B+C, tu t'en occupes). Sur les 3 « aucun doc GPU » : **Saint-Leu = Sourcé**
(PLU 2007 opposable, mairie ; règles à calibrer), **Saint-Philippe = Sourcé RNU** (branche PAU),
**Saint-André = seul bloquant restant** (opposabilité mairie en cours).

## Les 9 déjà à jour — j'avance dessus (paquets de 4, ton feu vert)
97401 Les Avirons · 97402 Bras-Panon · 97403 Entre-Deux · 97406 La Plaine-des-Palmistes ·
97415 Saint-Paul · 97416 Saint-Pierre · 97419 Sainte-Rose · 97423 Les Trois-Bassins · 97424 Cilaos.

Paquet A (en cours) : **97401 · 97402 · 97403 · 97406**. Paquet B : 97415 · 97416 · 97419 · 97423.
Reste : 97424 (+ ce que tu retélécharges).
