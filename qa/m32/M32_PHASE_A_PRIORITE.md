# M32 — PHASE A RÉVISÉE : TABLEAU DE PRIORITÉ DE RÉ-EXTRACTION

Arbitrage Vic (a) : intégrer + compléter, jamais repartir de zéro. Priorité de ré-extraction =
**nb de parcelles en TÊTE SERVIE (brûlantes + chaudes) par commune**, sur le run servi `q_v8_calibre`.
Ré-extraction sur la **version OPPOSABLE GPU** uniquement, idurba + date d'approbation ancrés au yaml.

## Tête servie par commune (run q_v8_calibre) × statut de calibration

| Rang tête | Commune | INSEE | Brûl. | Chaud. | Tête | Statut calibr. | Action M32 |
|---|---|---|---|---|---|---|---|
| 1 | Saint-Paul | 97415 | 24 | 189 | **213** | PART (moteur, ouverture seule) | **RIEN à ré-extraire** — planchers délégués PLH (non publiés) |
| 2 | La Possession | 97408 | 7 | 105 | 112 | EXH (moteur partiel) | → Phase C (compléter social OAP) |
| 3 | Saint-Pierre | 97416 | 12 | 98 | 110 | **EXH** | → Phase C (intégration) |
| 4 | Le Tampon | 97422 | 6 | 98 | 104 | **EXH** | → Phase C (intégration) |
| 5 | Saint-Denis | 97411 | 13 | 90 | 103 | **NÉG** (Sourcé, v2026) | consigné — rien à calibrer (voir §négatifs) |
| 6 | Saint-Leu | 97413 | 6 | 76 | 82 | **EXH** (moteur) | déjà intégré |
| 7 | Saint-Joseph | 97412 | 6 | 58 | 64 | **NÉG** (Sourcé, v2025) | consigné — rien à calibrer |
| **8** | **Saint-Louis** | **97414** | 9 | 43 | **52** | **PART — écart de version** | **RÉ-EXTRACT #1** (v20250926 extraite ≠ v20251218 opposable) |
| 9 | Saint-Benoît | 97410 | 7 | 41 | 48 | spécial (19 fiches graphiques) | report v2 (arbitrage d) |
| 10 | Sainte-Marie | 97418 | 3 | 34 | 37 | **EXH** | → Phase C (intégration) |
| 11 | La Plaine-des-Palmistes | 97406 | 6 | 29 | 35 | PART (OAP graphique) | **RÉ-EXTRACT #6** — limité (OAP graphique non OCR) |
| 12 | Saint-André | 97409 | 2 | 28 | 30 | **BLOQ** | attente opposabilité (arbitrage c) — servi étiqueté |
| 13 | L'Étang-Salé | 97404 | 3 | 23 | 26 | **EXH** | → Phase C (intégration) |
| **14** | **Le Port** | **97407** | 4 | 21 | **25** | **PART** | **RÉ-EXTRACT #2** (OAP % social, détail par site) |
| 15 | Petite-Île | 97405 | 0 | 23 | 23 | **PART** (ouverture a_verifier) | **RÉ-EXTRACT #3** (statut ouverture + phasage) |
| 16 | Cilaos | 97424 | 3 | 15 | 18 | **NÉG** (Sourcé, v2024) | consigné — OAP graphique `non_extrait` (pas sans_objet) |
| 17 | Sainte-Suzanne | 97420 | 1 | 17 | 18 | **PART** | **RÉ-EXTRACT #4** (valeurs densité à re-confirmer) |
| 18 | Les Avirons | 97401 | 3 | 14 | 17 | **PART** | **RÉ-EXTRACT #5** (OAP par site) |
| 19 | Entre-Deux | 97403 | 1 | 11 | 12 | **EXH** | → Phase C (intégration) |
| 20 | Les Trois-Bassins | 97423 | 2 | 7 | 9 | **EXH** (moteur) | déjà intégré |
| 21 | Sainte-Rose | 97419 | 0 | 5 | 5 | **PART** | **RÉ-EXTRACT #7** (phasage 1AU complexe) |
| 22 | Salazie | 97421 | 1 | 3 | 4 | **PART** | **RÉ-EXTRACT #8** (valeurs densité) |
| 23 | Bras-Panon | 97402 | 0 | 3 | 3 | **PART** | **RÉ-EXTRACT #9** (densité TCSP + phasage inter-zones) |
| 24 | Saint-Philippe | 97417 | 0 | 2 | 2 | **RNU** | hors calibration AU |

## Ordre de ré-extraction retenu (partielles, par tête servie décroissante)

1. **Saint-Louis (97414)** — 52 têtes, écart de version à résoudre (v20251218 opposable). PRIORITÉ.
2. **Le Port (97407)** — 25.  3. **Petite-Île (97405)** — 23.  4. **Sainte-Suzanne (97420)** — 18.
5. **Les Avirons (97401)** — 17.  6. **La Plaine (97406)** — 35 têtes mais OAP graphique (limité).
7. **Sainte-Rose (97419)** — 5.  8. **Salazie (97421)** — 4.  9. **Bras-Panon (97402)** — 3.

(Saint-Paul 213 têtes : rien à ré-extraire — planchers délégués PLH. Exclu de la file.)

## Les 3 scans négatifs (arbitrage a : « calibrées de fait ») — DÉJÀ consignés Sourcé

| Commune | Version opposable | Consignation actuelle | Standard Vic atteint ? |
|---|---|---|---|
| Saint-Denis (97411) | 97411_PLU_20260423 (2026-04-23) | `planchers: sans_objet` + « aucun min log/densité au règlement 2026 (scan négatif) » | OUI (note « OAP publiée séparément ? à confirmer » honnête) |
| Saint-Joseph (97412) | 97412_PLU_20251210 (2025-12-10) | `sans_objet` + « aucun plancher (185 p., scan négatif) ni OAP » | OUI |
| Cilaos (97424) | 97424_PLU_20240213 (2024-02-13) | `sans_objet` règlement + « OAP graphique non_extrait, PAS sans_objet » | OUI (nuance honnête : OAP graphique non lisible) |

→ Les 3 sont déjà « scan négatif, règlement sans plancher » Sourcé avec version + date. **Rien à
réécrire** ; la nuance Cilaos/Saint-Denis (OAP non tranchée) est consignée honnêtement.

## Contrainte de ré-extraction (honnête, à cadrer)

Chaque ré-extraction = télécharger l'archive PLU opposable du GPU (**~270 Mo/commune**, ex.
`PACK_DU_97414_….zip`), en extraire le règlement + l'OAP, lire les articles AU (densité, min-log,
phasage) et les sites OAP avec **citation article + page**. Deux limites déjà rencontrées, à
respecter (jamais forcer) : **PDF 2 colonnes** (Saint-Benoît) et **OAP graphique** (Cilaos, La
Plaine) ne sont pas extractibles au texte → `non_extrait`, pas un plancher deviné. Le travail est
document-en-main, commune par commune, avec **point d'étape toutes les 3 communes** (arbitrage
séquencement). La file ci-dessus fixe l'ordre.

## Limites de modélisation à consigner (arbitrage : jamais approximées en v1)

- **Dépendance de phasage INTER-ZONES** (Bras-Panon, Sainte-Rose, Les Trois-Bassins) : l'ouverture
  d'une AU dépend de l'urbanisation d'une AUTRE zone. Le schéma `au_ouverture` v1 ne le porte pas →
  consigné comme limite datée du yaml + étiquette fiche si pertinent.
- **Date-butoir** (Sainte-Marie, 2AU ouvre en 2031) : le schéma v1 ne porte pas la date-butoir →
  même traitement (limite datée + étiquette).
