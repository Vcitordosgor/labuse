# VERITE-TERRAIN-2 — ECARTS (registre consolidé des 5 volets)

Rédigé le 16/10/2026. Tout écart relevé par les comparateurs, revérifié, classé par nature et par statut. Rien n'est caché : les écarts conservateurs comme les vrais trous y figurent.

## Synthèse par nature

| Nature | Volet | Nombre | Statut |
|---|---|---|---|
| Erreur de **valeur de donnée servie** confirmée | A, B, C | **0** | — |
| Page de citation PLU imprécise (valeur juste) | A | 15 | **CORRIGÉ** (branche `fix/citations-plu-15`, mergée dans main) |
| Écart de temps de trajet (artefact de bande) | B | 41 | Documenté — 40 conservateurs, 1 réel (détour) |
| Permis réel au-dessus de la capacité LABUSE | D | 2 653 / 6 601 | Expliqué un-par-un, cause classée |
| Performance de prédiction (signal / prix) | E | — | Mesuré, limites datées |

**Il n'existe, sur A/B/C, aucune erreur de valeur servie confirmée.** Les 15 « LABUSE FAUX » du volet A étaient des pages de renvoi fausses (la valeur réglementaire, elle, était juste) et sont désormais corrigées. Les écarts de D et E ne sont pas des « faux » de donnée : ce sont, respectivement, des dépassements de capacité expliqués et des mesures de performance prédictive.

## A — Règles PLU : 15 écarts, 0 valeur fausse (CORRIGÉS)

Chaque écart = la valeur réglementaire était exacte mais la `page_pdf` citée pointait à côté. Corrigés dans `fix/citations-plu-15` (page exacte relue au PDF officiel + citation fidèle, valeurs inchangées, V6a verte).

| Commune | Règle | Zones | Valeur (juste) | page_pdf 76/… → exacte |
|---|---|---|---|---|
| L'Étang-Salé | emprise CES | AUa/AUb/AUc/AUe/AUt | 70/65/60/75/65 % | 76 → **79** |
| La Plaine-des-Palmistes | stationnement | Ua/Ub/Uc/Ur/AUb/AUc/AUr | 1,5 pl/logt | 21/33/45/57 → **103** (annexe NORMES) |
| Saint-Louis | retrait limites latérales | UC2/1AUc/1AUc2 | 3 m | 44 → **46** |

## B — Trajets : 41 écarts (sur 1 473 paires)

40 sur-estimations (LABUSE sert une bande de temps plus grande que le temps point-à-point réel) = **sens conservateur**, cause = contour de polygone d'isochrone (POI à quelques mètres hors d'une petite bande, capté par une plus grande). 1 sous-estimation réelle : **Salazie**, POI à 110 m à vol d'oiseau mais 1 641 m / 8 min par la route (détour de cirque). Aucun ne fausse une donnée chiffrée servie ; tous relèvent de la quantification par bande, intrinsèque au produit. Détail ligne à ligne : `TRAJETS.csv`, hand-recheck dans `TRAJETS-NOTES.md`.

## C — DPE / permis / risques : 0 écart

Aucun « LABUSE FAUX ». Les seuls candidats (DPE ADEME non rattachés par LABUSE) se sont avérés géocodés au grain rue (non assignables à une parcelle) → pas une erreur. Permis : 100 % des dossiers LABUSE retrouvés dans Sit@del indépendant, 0 permis inventé. Détail : `DPE-PERMIS.csv` / `DPE-PERMIS-NOTES.md`.

## D — Permis au-dessus de la capacité LABUSE : 2 653 / 6 601 (40,2 %), classés

Ce ne sont pas des erreurs de donnée mais des cas où un permis réel a autorisé plus que la capacité max que LABUSE calcule pour la ou les parcelles. Cause classée :

| Cause | Nombre | Lecture |
|---|---|---|
| Parcelle **non servie** (foncier redécoupé depuis) | 1 294 | grain : le permis porte sur un parcellaire différent de l'état servi — pas un défaut de calibrage |
| Densité réelle > calibrage (petites parcelles `terrain_exigu`) | 913 | **piste de calibrage réelle** |
| Non constructible chez LABUSE (dont 1AU/AU « redhibitoire » PLU 2026 où de gros collectifs ont été autorisés) | 418 | **piste de calibrage / phasage AU** |
| Réunion de parcelles incomplète | 27 | grain de rattachement |
| Surface source Sit@del aberrante | 1 | bruit source |

Médiane du ratio autorisé/LABUSE : **SDP 0,46 · logements 0,40** → sur l'ensemble, LABUSE couvre typiquement ~2× l'autorisé (conservateur), mais 40 % des permis dépassent, surtout par grain de parcellaire. Détail : `PERMIS-VS-CAPACITE.csv` / `-NOTES.md`.

## E — Prédictions : performance mesurée, pas un « faux »

- **Signal de mutation** : l'instantané SERVI (q_v16/18/19, `computed_at` oct. 2026) n'est pas jugeable forward aujourd'hui (DVF s'arrête au 31/12/2025). Rejeu daté propre du modèle GELÉ q_v15 (features au 01/01/2025, jugé sur les mutations 2025, N = 429 799) : **le signal sépare** mais modérément (décile haut 3,45 %, lift ×2,29, IC Wilson [3,28 ; 3,63 %] ; AUC 0,625 ; Brier 0,0148 ; événement rare, base 1,51 %).
- **Prix** : estimateur sobre reconstruit sans fuite (coupe 2024-01-01, médiane €/m² commune×type sur DVF < T, jugé sur ventes > T, N = 3 581) : **écart médian signé −5,6 %** (absolu 27,4 %), **±10 % = 17,5 %**, **±20 % = 36,5 %** ; léger biais à la sous-estimation, forte dispersion intra-commune.

Détail : `SIGNAL-BACKTEST.md`, `PRIX-BACKTEST.csv` / `PRIX-BACKTEST-NOTES.md`.

## Ce qui reste à faire (hors périmètre audit, lecture seule)

1. ~~Recaler les 15 pages de citation PLU~~ → **FAIT** (`fix/citations-plu-15` mergée).
2. Calibrage D : examiner les 913 « densité > calibrage » (petites parcelles) et les 418 « non constructible » (phasage AU/redhibitoire PLU 2026) — pistes réelles, à instruire au moteur PLU.
3. Prédictions E : figer un instantané daté q_v19@T₀ aujourd'hui, re-mesurer taux/lift/IC et l'écart de prix après la prochaine campagne DVF (protocole forward dans `SIGNAL-BACKTEST.md`).
