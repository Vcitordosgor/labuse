# GPU-PILOTE — DIFF FINAL CONSOLIDÉ (ce qui décide du re-run)

> Trois colonnes par commune : **ce que le YAML/calibration actuel dit** · **ce que l'extraction dit**
> · **combien de parcelles SERVIES sont touchées** (run servi `q_v7_defisc`). L'écart cœur, transverse
> aux 23 communes : **les YAML ne portent PAS le statut d'OUVERTURE des zones AU** (dette #7). Le
> re-run se décide sur les parcelles servies EN TÊTE reposant sur des AU à ouverture subordonnée.
> Rien écrit en base, aucun YAML modifié. Saint-André (97409) hors périmètre (opposabilité bloquée).

## L'écart transverse (le vrai sujet)
| | YAML actuel | Extraction GPU-PILOTE |
|---|---|---|
| **Ouverture AU** | **NON portée** — une AU dotée d'articles dimensionnels est servie « constructible » | ouverture LUE : `conditionnelle_operation` (modification), `conditionnelle_etat_tiers` (phasage 2AU→1AU), ou `fermée` (AUs/AUst réserves). **AUCUNE n'est ouverte sans condition.** |
| **Planchers densité** | rarement portés | présents dans **13/23** communes (règlement, OAP, PLH ou tableau) — sous le seuil, une petite opération est inconstructible |
| **Dépendance de phasage** | absente | 6 communes : 2AU ne s'ouvre qu'après aménagement des 1AU |
| **VRD internes+externes** | absent | L'Étang-Salé + Saint-Leu (poste de coût) |

## Parcelles servies touchées (q_v7_defisc) — par commune
« Touchées » = servies en zone AU dont l'ouverture/plancher, désormais documentés, n'étaient PAS dans
le YAML. `tête` = brûlante+chaude+réserve (le risque de faux positif). Borne HAUTE (conditionnelle ≠
inconstructible : certaines AU sont ouvertes via opérations achevées).

| INSEE | commune | ouverture extraite | plancher | AU servies | **tête** | brûl. |
|---|---|---|---|---|---|---|
| 97415 | Saint-Paul | conditionnelle (modif) | délégué PLH | 740 | **120** | 10 |
| 97408 | La Possession | conditionnelle (modif) | 50 log/ha (SCOT/SAR) | 307 | **70** | 2 |
| 97413 | Saint-Leu | conditionnelle_operation | 30/15 + VRD | 405 | **40** | 0 |
| 97412 | Saint-Joseph | conditionnelle (modif) | — | 329 | **31** | 0 |
| 97406 | La Plaine | conditionnelle (modif) | 10 LLS | 120 | **29** | 1 |
| 97423 | Les Trois-Bassins | 2AU→1AU (phasage) | 35/30/20 | 221 | **27** | 8 |
| 97401 | Les Avirons | conditionnelle (modif) | 30/20 *(corrigé QC)* | 84 | **26** | 0 |
| 97416 | Saint-Pierre | conditionnelle (modif/rév) | OAP 50/60/80 | 86 | **26** | 0 |
| 97414 | Saint-Louis | 2AU→1AU (phasage) | OAP 30/50 | 363 | **24** | 0 |
| 97411 | Saint-Denis | AUx fermée (rév/modif) | — | 208 | **22** | 1 |
| 97419 | Sainte-Rose | phasage (hors 1AUc) | 20/10 *(corrigé QC)* | 123 | **19** | 0 |
| 97422 | **Le Tampon** | 2AU réserve (SAR) | 2AUc 20 / **2AUd 10** | 274 | **17** | 1 |
| 97403 | Entre-Deux | conditionnelle (modif/rév) | table 20/site | 66 | **16** | 0 |
| 97424 | Cilaos | AUst réserve | — | 68 | **15** | 0 |
| 97402 | Bras-Panon | 2AU→1AU (phasage) | 30→50 TCSP | 97 | **12** | 1 |
| 97421 | Salazie | conditionnelle (op. ens.) | par zone (a_verifier) | 55 | **11** | 0 |
| 97404 | L'Étang-Salé | condit. + AUs fermée | 50/30/15 + VRD | 103 | **9** | 0 |
| 97420 | Sainte-Suzanne | 2AU→1AU (phasage) | OAP 10/20/30 | 50 | **7** | 0 |
| 97407 | Le Port | 1AU condit. / 2AU fermée | OAP 50 | 41 | **5** | 0 |
| 97418 | Sainte-Marie | 1AU condit. / **2AU date-butoir 2031** | 50/25/25 | 56 | **5** | 0 |
| 97405 | Petite-Île | 1AU/2AU (a_verifier) | qualitatif | 88 | **3** | 0 |
| **TOTAL** | **21 communes** | — | — | **≈ 4 550** | **≈ 534** | **≈ 24** |

## Ce que le diff dit pour le re-run
1. **≈ 534 parcelles servies en tête** (≈ 24 brûlantes) reposent sur des zones AU dont l'ouverture est
   SUBORDONNÉE (modification/OAP/phasage) — fait absent des YAML. C'est la population à re-arbitrer :
   le mécanisme `declasse_au_statut_inconnu` (déjà en place) les traiterait, MAIS il ne lisait pas
   l'ouverture ; désormais on a le VRAI statut par zone → on peut déclasser à bon escient, pas « au
   statut inconnu ».
2. **Concentration** : Saint-Paul (120), La Possession (70), Saint-Leu (40) portent ~44 % des têtes.
   Les brûlantes se concentrent sur **Saint-Paul (10) et Les Trois-Bassins (8)**.
3. **Planchers** : 13 communes ont un plancher de densité — une 2ᵉ vague de faux positifs potentiels
   (petites parcelles/opérations sous le seuil), non quantifiée ici (nécessite la taille d'opération).
4. **Le Tampon 2AUd** : la golden brûlante `97422000AD1237` est sur une **2AUd réserve** (10 log/ha) —
   confirmé à la source. Cas fondateur clos.

## Reste hors diff
- **Saint-André** (97409) : bloqué opposabilité — 413 têtes / 7 brûlantes sur repli générique (voir
  GPU_PILOTE_PAQUETS_ETAT). À intégrer dès l'arbitrage mairie.
- **`a_verifier` d'outil** (poppler) : Saint-Benoît (2 colonnes), La Plaine + Cilaos (OAP image),
  Salazie (densités par zone). Ouverture captée partout ; seuls des planchers restent à confirmer.

**Décision qui revient à Vic** : ce diff (≈ 534 têtes / 24 brûlantes sur AU à ouverture subordonnée)
justifie-t-il le re-run + arène + MAJ golden sur l'état calibré ? C'est LUI qui tranche, pas l'extraction.
