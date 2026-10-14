# PLU-CALIBRAGE-8 (oct. 2026) — Lot A · Inventaire des zones sans gabarit servable

Branche `feat/plu-calibrage-8` · worktree `~/Desktop/labuse-plu8` · base main `3f473aa3`. Lecture seule, aucune écriture. Point de départ : `docs/audit-2026-10/chasse-calculs-1/LOT5-GABARIT-INCOMPLETS.md` (39 % des Gabarits incomplets = zones PLU non calibrées).

## Méthode

`scripts/plu8_inventaire.py` (lecture seule) énumère, pour chaque `(commune, zone_lib)` portée par des parcelles en famille **U/AU** (les seules qui reçoivent un Gabarit), et **reproduit à l'identique la décision de blocage AU NIVEAU ZONE du moteur `gabarit/builder.py`** — la seule part « donnée PLU » (E-C2), indépendante de la géométrie par parcelle (façade, limites non qualifiées, multi-zone, parcelle enclavée : ces causes-là, 47 % du LOT5, ne relèvent PAS de la calibration PLU et ne figurent donc pas ici).

Une zone est **servable** (gabarit non bloqué au niveau zone) ssi : `resolve_zone` ≠ None, pas de `regle_non_validee` (feuille SDP `propose` portant une valeur), `calibree=True`, pas de silence total, **hauteur exploitable** (faîtage OU égout chiffré, OU faîtage validé non chiffré) ET **emprise exploitable** (CES chiffré OU silence prouvé `absent`). Les reculs, eux, ne bloquent jamais le gabarit (builder.py ne les érige pas en gate).

« À potentiel » = `sdp_residuelle_m2 > 0` dans le run servi **q_v18** (bandes A–D). Règlements : `data/plu_reglements/` est vide dans le dépôt ; les PDF sont retéléchargeables du GPU (URL + md5 dans le `meta` de chaque YAML — md5 vérifié sur un échantillon, HTTP 200).

## Résultat

**111 zones** U/AU ne produisent pas de gabarit servable, couvrant **25207 parcelles** dont **17474 à potentiel**. La liste dépasse 60 zones → **STOP, Vic choisit le périmètre** (règle du mandat).

### Par cause (taxonomie du mandat)

| Cause | Zones | Parcelles | À potentiel |
|---|--:|--:|--:|
| forme non modélisée | 33 | 20795 | 15409 |
| renvoi AU→U non résolu | 63 | 2750 | 1688 |
| zone absente du YAML | 5 | 517 | 257 |
| silence total du règlement | 7 | 857 | 120 |
| feuille `propose` (non validée) | 3 | 288 | 0 |

### Par nature (calibrable avec le schéma actuel ?)

| Nature | Zones | Parcelles | À potentiel | Lecture |
|---|--:|--:|--:|---|
| ✅ calibrable (schéma actuel) | 92 | 6395 | 3477 | cible Lot B : renvoi AU→U à câbler, CES à transcrire, feuille `propose` à valider |
| ⛔ structurel (hors schéma actuel) | 17 | 15304 | 13207 | hauteur en table graphique / prospect / silence total / OAP — exigent une **extension de schéma** (décision Vic séparée) : hors de ce mandat tel que cadré |
| 🟡 à vérifier (renvoi AVAP/doc annexe) | 2 | 3508 | 790 | Saint-Denis Uavap : le règlement renvoie INTÉGRALEMENT à l'AVAP annexée (doc patrimonial séparé) — rien de chiffré à transcrire depuis le règlement |

> ⚠️ Nuance sur les 63 « renvoi AU→U non résolu » : une zone AU n'est réellement calibrable que si sa zone U de rattachement est (ou devient) servable. Celles dont le parent U est structurel (ex. Saint-Benoît AUb19 → Ub en table graphique) héritent du blocage → à re-trancher zone par zone en Lot B.

## Périmètre recommandé (à l'arbitrage de Vic)

1. **Structurel (17 z / 13207 pot.)** — NE PAS calibrer dans ce mandat : table graphique (Saint-Benoît Ua/Ub/Ue…), prospect, silence total (Le Port Uv/Up…), OAP. Rendement = 0 sans extension de schéma, que le mandat interdit sans STOP dédié. Rapportées « non calculable : hauteur hors schéma / silence du règlement ».

2. **Uavap (Saint-Denis, 790 pot.)** — renvoi intégral à l'AVAP annexée : rien à transcrire du règlement, laisser en l'état.

3. **Calibrable, par ordre de potentiel décroissant** — cible naturelle de Lot B, concentrée sur ~8 communes (le règlement se lit par commune) : les renvois AU→U dont le parent U est déjà servable, les zones « CES seule manquante » (hauteur déjà OK), et les 3 feuilles `propose` (dont U1pru = Lot C).

### Détail « calibrable » par commune

| Commune | Zones (potentiel) | Σ potentiel |
|---|---|--:|
| Saint-Paul | Usdu (845), AU3st (19), AU1st (8), AU5st (6), AU6st (3), U1pru (0), AU1est (0) | 881 |
| Saint-Leu | AUC (173), AUB (149), AUA (119), AUE (96), AUS (79), AUD (33), AUT (2) | 651 |
| Saint-Denis | AUm (255), AUh (163), AUj (85), AUx (39), Uip (16), AUa (0) | 558 |
| Saint-Louis | 1AUb2 (141), 2AUb2 (114), 1AUb1 (69), 2AUb1 (24), 1AUst (15), 2AUst (5), 1AUste (3), 2AUste (0) | 371 |
| Saint-Benoît | Uap (156), AUb19 (58), AUa5 (47), AUb7 (14), AUa8 (11), AUb6 (11), AUb14 (8), AUb15 (8), AUa18 (6), AUb2 (4), AUb12 (3), AUb10 (2), AUb11 (2), AUb16 (2), AUa9 (1), AUb13 (1), AUb17 (1), AUp1 (0), AUe3 (0) | 335 |
| La Possession | AUBm (170), UAv (41), AUAv (34), AUst (33), Up (1) | 279 |
| Saint-André | 1AUc (88), 2AUc (52), 1AUd (46), 1AUb (21), 1AUs (14), 2AUb (14), 1AUcr (6), 2AUd (6), 1AUe (6), 1AUt (4) | 257 |
| La Plaine-des-Palmistes | AUs2 (24), AUs1 (20) | 44 |
| Les Trois-Bassins | 1AUe (11), AUs (7), AUse (1) | 19 |
| Saint-Joseph | 3AU5vist (9), 3AU3st (6), 2AU5st (3), 3AU6ch (1), U5cvd (0), 3AU5st (0), 2AU6ch (0) | 19 |
| Saint-Pierre | AU02 (14), AU01 (4), AU0c-1 (0), AU03 (0), Uep (0) | 18 |
| Petite-Île | 2AU (13), AUF (2) | 15 |
| Entre-Deux | AUe (11), AUst (0) | 11 |
| Les Avirons | AUes (10) | 10 |
| L'Étang-Salé | AUs (4) | 4 |
| Cilaos | AUst (3) | 3 |
| Le Port | 1AUmut (2), 2AUp (0), 2AUmut (0), 1AUe (0), 1AUv (0) | 2 |
| Bras-Panon | AUst (0) | 0 |

## Inventaire complet (111 zones, tri potentiel ↓)

| # | Commune | Zone | Fam | Parcelles | À pot. | Nature | Cause | Détail moteur | Règlement (millésime) |
|---|---|---|---|--:|--:|---|---|---|---|
| 1 | Saint-Benoît | Ub | U | 10143 | 9384 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur en plage / table graphique par secteur (hors schéma) | 97410_reglement_20200206.pdf (2020-02-06) |
| 2 | Saint-Benoît | Ua | U | 3762 | 3288 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur en plage / table graphique par secteur (hors schéma) | 97410_reglement_20200206.pdf (2020-02-06) |
| 3 | Saint-Paul | Usdu | U | 1318 | 845 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
| 4 | Saint-Denis | Uavap | U | 3507 | 790 | 🟡 | forme non modélisée | calibrée partielle, repli générique — aucune hauteur au règlement transcrit | 97411_reglement_20260805.pdf (2026-08-05) |
| 5 | Saint-Benoît | Ue | U | 301 | 259 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur en plage / table graphique par secteur (hors schéma) | 97410_reglement_20200206.pdf (2020-02-06) |
| 6 | Saint-Denis | AUm | AU | 386 | 255 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUm (estimation générique, zone absente du YAML) | 97411_reglement_20260805.pdf (2026-08-05) |
| 7 | Saint-Leu | AUC | AU | 208 | 173 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUC (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 8 | La Possession | AUBm | AU | 241 | 170 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur en feuille propose (non validée) | 97408_reglement_20251217.pdf (2025-12-17) |
| 9 | Saint-Denis | AUh | AU | 205 | 163 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUh (estimation générique, zone absente du YAML) | 97411_reglement_20260805.pdf (2026-08-05) |
| 10 | Saint-Benoît | Uap | U | 301 | 156 | ✅ | zone absente du YAML | PLU non calibré pour la zone Uap (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 11 | Saint-Leu | AUB | AU | 290 | 149 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUB (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 12 | Saint-Louis | 1AUb2 | AU | 220 | 141 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97414_reglement_20251218.pdf (2025-12-18) |
| 13 | Saint-Leu | AUA | AU | 190 | 119 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUA (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 14 | Saint-Louis | 2AUb2 | AU | 144 | 114 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97414_reglement_20251218.pdf (2025-12-18) |
| 15 | Saint-Leu | AUE | AU | 140 | 96 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUE (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 16 | Saint-André | 1AUc | AU | 129 | 88 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUc (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 17 | Saint-Denis | AUj | AU | 109 | 85 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUj (estimation générique, zone absente du YAML) | 97411_reglement_20260805.pdf (2026-08-05) |
| 18 | Le Port | Uoap | U | 111 | 80 | ⛔ | zone absente du YAML | PLU non calibré pour la zone Uoap (estimation générique, zone absente du YAML) | 97407_reglement_20241209.pdf (2024-12-09) |
| 19 | Saint-Leu | AUS | AU | 124 | 79 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUS (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 20 | Saint-Louis | 1AUb1 | AU | 77 | 69 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97414_reglement_20251218.pdf (2025-12-18) |
| 21 | Saint-Benoît | AUb19 | AU | 65 | 58 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb19 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 22 | Le Port | Uv | U | 177 | 57 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 23 | Saint-André | 2AUc | AU | 70 | 52 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97409_reglement_2019.pdf (2019-02-28) |
| 24 | Saint-Pierre | AUdma | AU | 60 | 52 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur validée mais non chiffrée (prospect L≥H / forme) | 97416_reglement_20240625.pdf (2024-06-25) |
| 25 | Saint-Benoît | AUa5 | AU | 83 | 47 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUa5 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 26 | Saint-André | 1AUd | AU | 65 | 46 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUd (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 27 | La Possession | UAv | U | 172 | 41 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur en feuille propose (non validée) | 97408_reglement_20251217.pdf (2025-12-17) |
| 28 | Saint-Denis | AUx | AU | 91 | 39 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUx (estimation générique, zone absente du YAML) | 97411_reglement_20260805.pdf (2026-08-05) |
| 29 | Petite-Île | UF | U | 81 | 37 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97405_reglement_20230609.pdf (2023-06-09) |
| 30 | La Possession | AUAv | AU | 94 | 34 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur en feuille propose (non validée) | 97408_reglement_20251217.pdf (2025-12-17) |
| 31 | La Possession | AUst | AU | 89 | 33 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97408_reglement_20251217.pdf (2025-12-17) |
| 32 | Saint-Leu | AUD | AU | 40 | 33 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUD (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 33 | La Plaine-des-Palmistes | AUs2 | AU | 50 | 24 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97406_reglement_20230527.pdf (2023-05-27) |
| 34 | Saint-Louis | 2AUb1 | AU | 29 | 24 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97414_reglement_20251218.pdf (2025-12-18) |
| 35 | Saint-André | 1AUb | AU | 27 | 21 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUb (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 36 | La Plaine-des-Palmistes | AUs1 | AU | 41 | 20 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97406_reglement_20230527.pdf (2023-05-27) |
| 37 | Saint-Paul | AU3st | AU | 156 | 19 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
| 38 | Saint-Denis | Uip | U | 100 | 16 | ✅ | zone absente du YAML | PLU non calibré pour la zone Uip (estimation générique, zone absente du YAML) | 97411_reglement_20260805.pdf (2026-08-05) |
| 39 | Saint-Louis | 1AUst | AU | 44 | 15 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97414_reglement_20251218.pdf (2025-12-18) |
| 40 | Saint-Benoît | Up | U | 19 | 15 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur en plage / table graphique par secteur (hors schéma) | 97410_reglement_20200206.pdf (2020-02-06) |
| 41 | Saint-Pierre | AU02 | AU | 37 | 14 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97416_reglement_20240625.pdf (2024-06-25) |
| 42 | Saint-André | 1AUs | AU | 19 | 14 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUs (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 43 | Saint-André | 2AUb | AU | 15 | 14 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97409_reglement_2019.pdf (2019-02-28) |
| 44 | Saint-Benoît | AUb7 | AU | 15 | 14 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb7 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 45 | Petite-Île | 2AU | AU | 67 | 13 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97405_reglement_20230609.pdf (2023-06-09) |
| 46 | Le Port | Uppp | U | 52 | 13 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 47 | Entre-Deux | AUe | AU | 16 | 11 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUe (estimation générique, zone absente du YAML) | 97403_reglement_20240924.pdf (2024-09-24) |
| 48 | Les Trois-Bassins | 1AUe | AU | 14 | 11 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUe (estimation générique, zone absente du YAML) | 97423_reglement_20220602.pdf (2022-06-02) |
| 49 | Saint-Benoît | AUa8 | AU | 13 | 11 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUa8 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 50 | Saint-Benoît | AUb6 | AU | 13 | 11 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb6 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 51 | Les Avirons | AUes | AU | 15 | 10 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97401_reglement_20241206.pdf (2024-12-06) |
| 52 | Saint-Joseph | 3AU5vist | AU | 20 | 9 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97412_Reglement_20251210.pdf (2025-12-10) |
| 53 | Saint-Paul | AU1st | AU | 189 | 8 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
| 54 | Saint-Benoît | AUb14 | AU | 13 | 8 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb14 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 55 | Saint-Benoît | AUb15 | AU | 8 | 8 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb15 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 56 | Les Trois-Bassins | AUs | AU | 11 | 7 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97423_reglement_20220602.pdf (2022-06-02) |
| 57 | Le Port | Up | U | 96 | 6 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 58 | Saint-Joseph | 3AU3st | AU | 26 | 6 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97412_Reglement_20251210.pdf (2025-12-10) |
| 59 | Saint-Paul | AU5st | AU | 12 | 6 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
| 60 | Saint-André | 1AUcr | AU | 9 | 6 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUcr (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 61 | Saint-André | 2AUd | AU | 8 | 6 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 2AUd (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 62 | Saint-André | 1AUe | AU | 7 | 6 | ✅ | forme non modélisée | calibrée partielle, repli générique — hauteur non exploitable | 97409_reglement_2019.pdf (2019-02-28) |
| 63 | Saint-Benoît | AUa18 | AU | 6 | 6 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUa18 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 64 | Saint-Louis | 2AUst | AU | 9 | 5 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97414_reglement_20251218.pdf (2025-12-18) |
| 65 | Le Port | Ue | U | 440 | 4 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 66 | Saint-André | 1AUt | AU | 10 | 4 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone 1AUt (estimation générique, zone absente du YAML) | 97409_reglement_2019.pdf (2019-02-28) |
| 67 | Saint-Denis | Udo | U | 8 | 4 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur en plage / table graphique par secteur (hors schéma) | 97411_reglement_20260805.pdf (2026-08-05) |
| 68 | L'Étang-Salé | AUs | AU | 4 | 4 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97404_reglement_20250917.pdf (2025-09-17) |
| 69 | Saint-Benoît | AUb2 | AU | 4 | 4 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb2 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 70 | Saint-Leu | UFe | U | 4 | 4 | ⛔ | zone absente du YAML | PLU non calibré pour la zone UFe (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 71 | Saint-Pierre | AU01 | AU | 4 | 4 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97416_reglement_20240625.pdf (2024-06-25) |
| 72 | Saint-Paul | AU6st | AU | 13 | 3 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
| 73 | Saint-Louis | 1AUste | AU | 11 | 3 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97414_reglement_20251218.pdf (2025-12-18) |
| 74 | Saint-Joseph | 2AU5st | AU | 7 | 3 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97412_Reglement_20251210.pdf (2025-12-10) |
| 75 | Cilaos | AUst | AU | 5 | 3 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97424_reglement_20240213.pdf (2024-02-13) |
| 76 | Saint-Benoît | AUb12 | AU | 3 | 3 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb12 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 77 | Le Port | 1AUmut | AU | 20 | 2 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 78 | Saint-Benoît | AUb10 | AU | 6 | 2 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb10 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 79 | Les Avirons | Ub5 | U | 3 | 2 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97401_reglement_20241206.pdf (2024-12-06) |
| 80 | Saint-Benoît | AUb11 | AU | 3 | 2 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb11 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 81 | Petite-Île | AUF | AU | 2 | 2 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97405_reglement_20230609.pdf (2023-06-09) |
| 82 | Saint-Benoît | AUb16 | AU | 2 | 2 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb16 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 83 | Saint-Leu | AUT | AU | 2 | 2 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUT (estimation générique, zone absente du YAML) | 97413_reglement_2007.pdf (2007-02-26) |
| 84 | Petite-Île | UFcim | U | 8 | 1 | ⛔ | silence total du règlement | sans règles d'implantation propres (silence total / renvoi non résolu) | 97405_reglement_20230609.pdf (2023-06-09) |
| 85 | Saint-Joseph | 3AU6ch | AU | 4 | 1 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97412_Reglement_20251210.pdf (2025-12-10) |
| 86 | Saint-Benoît | Ut | U | 2 | 1 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur en plage / table graphique par secteur (hors schéma) | 97410_reglement_20200206.pdf (2020-02-06) |
| 87 | Les Trois-Bassins | AUse | AU | 2 | 1 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97423_reglement_20220602.pdf (2022-06-02) |
| 88 | La Possession | Up | U | 1 | 1 | ✅ | zone absente du YAML | PLU non calibré pour la zone Up (estimation générique, zone absente du YAML) | 97408_reglement_20251217.pdf (2025-12-17) |
| 89 | Saint-Benoît | AUa9 | AU | 1 | 1 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUa9 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 90 | Saint-Benoît | AUb13 | AU | 1 | 1 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb13 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 91 | Saint-Benoît | AUb17 | AU | 1 | 1 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUb17 (estimation générique, zone absente du YAML) | 97410_reglement_20200206.pdf (2020-02-06) |
| 92 | Saint-Joseph | U5cvd | U | 221 | 0 | ✅ | feuille `propose` (non validée) | règle PLU non validée (propose) : retraits.limites_separatives | 97412_Reglement_20251210.pdf (2025-12-10) |
| 93 | Saint-Paul | U1pru | U | 55 | 0 | ✅ | feuille `propose` (non validée) | règle PLU non validée (propose) : retraits.limites_separatives | 97415_reglement_20251217.pdf (2025-12-17) |
| 94 | Saint-Denis | Uma | U | 37 | 0 | ⛔ | forme non modélisée | calibrée partielle, repli générique — hauteur validée mais non chiffrée (prospect L≥H / forme) | 97411_reglement_20260805.pdf (2026-08-05) |
| 95 | Saint-Paul | AU1est | AU | 32 | 0 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
| 96 | Saint-Pierre | AU0c-1 | AU | 31 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97416_reglement_20240625.pdf (2024-06-25) |
| 97 | Saint-Pierre | AU03 | AU | 30 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97416_reglement_20240625.pdf (2024-06-25) |
| 98 | Le Port | 2AUp | AU | 12 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 99 | Saint-Pierre | Uep | U | 12 | 0 | ✅ | feuille `propose` (non validée) | règle PLU non validée (propose) : emprise_sol.ces | 97416_reglement_20240625.pdf (2024-06-25) |
| 100 | Saint-Benoît | AUp1 | AU | 10 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97410_reglement_20200206.pdf (2020-02-06) |
| 101 | Saint-Joseph | 3AU5st | AU | 10 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97412_Reglement_20251210.pdf (2025-12-10) |
| 102 | Entre-Deux | AUst | AU | 7 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97403_reglement_20240924.pdf (2024-09-24) |
| 103 | Le Port | 2AUmut | AU | 6 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 104 | Saint-Louis | 2AUste | AU | 6 | 0 | ✅ | forme non modélisée | emprise (CES) non réglementée / non validée | 97414_reglement_20251218.pdf (2025-12-18) |
| 105 | Saint-Joseph | 2AU6ch | AU | 5 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97412_Reglement_20251210.pdf (2025-12-10) |
| 106 | Le Port | 1AUe | AU | 4 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 107 | Saint-Denis | AUa | AU | 3 | 0 | ✅ | renvoi AU→U non résolu | PLU non calibré pour la zone AUa (estimation générique, zone absente du YAML) | 97411_reglement_20260805.pdf (2026-08-05) |
| 108 | Bras-Panon | AUst | AU | 2 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97402_reglement_20260428.pdf (2026-04-28) |
| 109 | Saint-Benoît | AUe3 | AU | 2 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97410_reglement_20200206.pdf (2020-02-06) |
| 110 | Le Port | 1AUv | AU | 1 | 0 | ✅ | renvoi AU→U non résolu | sans règles d'implantation propres (silence total / renvoi non résolu) | 97407_reglement_20241209.pdf (2024-12-09) |
| 111 | Saint-Paul | AU1lec | AU | 1 | 0 | 🟡 | forme non modélisée | hauteur réglementaire non validée (aucune hauteur au règlement transcrit) ; emprise (CES) non réglementée / non validée | 97415_reglement_20251217.pdf (2025-12-17) |
