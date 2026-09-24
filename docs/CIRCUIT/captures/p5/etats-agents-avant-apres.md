# CIRCUIT-P5 tâche 2 — les 12 « jamais vérifiées », avant / après les agents

Base réelle `labuse`, `labuse agent source` sur les 12 sources en état « jamais vérifiée » (lot 1
de CIRCUIT-P4). Contrôle daté du **2026-09-24**. Coût jetons **2,78 € (21 appels)** ; web_search
facturé à part par Anthropic (~0,01 $/recherche, hors ledger).

## Avant (12 « jamais vérifiée »)

| id | source | veille |
|---|---|---|
| 148 | Communes La Réunion — contours (IGN) | — |
| 31 | INPI RNE (dirigeants) | — |
| 19 | OpenStreetMap / Overpass | — |
| 25 | INPN / patrinat — espaces protégés | — |
| 40 | NPNRU (DEAL Réunion / ANCT) | rappel |
| 43 | RTAA DOM (textes réglementaires) | rappel |
| 117 | DEAL — cartes de bruit stratégiques (CBS) | — |
| 41 | INSEE RP Logement 2023 | rappel |
| 131 | Coût de construction (EPTB SDES + choix LABUSE) | rappel |
| 72 | ZFANG (Légifrance) | — |
| 48 | PVGIS (Commission européenne) | rappel |
| 73 | FRR ex-ZRR (Légifrance) | — |

**12 jamais vérifiée.**

## Ce que chaque agent a trouvé, et l'état après

| id | source | verdict | ce que l'agent a trouvé | état après |
|---|---|---|---|---|
| 43 | RTAA DOM | **a_jour** | Arrêté du 17 avril 2009 modifié — en vigueur depuis le 14/01/2016 | **à jour** (contrôlé 24/09) |
| 48 | PVGIS | **a_jour** | PVGIS 5.3 (patch 2025-03-29, modèle PPM 2025-09-05) | **à jour** (contrôlé 24/09) |
| 72 | ZFANG | **a_jour** | Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18) | **à jour** (contrôlé 24/09) |
| 41 | INSEE RP Logement 2023 | **nouvelle** | RP2023 — géographie au 01/01/2026, correctif 17/09/2026 | **nouvelle version** (vanne) |
| 117 | DEAL — CBS | **nouvelle** | CBS 4e échéance — arrêté préfectoral 2023-610 du 28/03/2023 | **nouvelle version** (vanne) |
| 31 | INPI RNE | introuvable | API RNE v3.0 **mais sans extrait daté** → anti-invention (6.2) | jamais vérifiée |
| 19 | OpenStreetMap / Overpass | introuvable | flux continu (planet hebdo + diffs) — **aucune version datée** | jamais vérifiée |
| 131 | Coût de construction | introuvable | donnée **interne** (choix LABUSE) — pas de producteur amont | jamais vérifiée |
| 148 | Communes IGN | introuvable | sortie du modèle non-JSON (pas d'objet exploitable) | jamais vérifiée |
| 25 | INPN / patrinat | introuvable | sortie du modèle non-JSON | jamais vérifiée |
| 40 | NPNRU | introuvable | sortie du modèle non-JSON | jamais vérifiée |
| 73 | FRR ex-ZRR | introuvable | sortie du modèle non-JSON | jamais vérifiée |

## Après (distribution sur les 12)

**à jour : 3 · nouvelle version : 2 · jamais vérifiée : 7**  (3 + 2 + 7 = 12)

- **5 sources ont une réponse datée** : 3 confirmées « à jour » (avec la date du contrôle),
  2 avec une version plus récente → « nouvelle version » (la vanne d'injection apparaît).
- **7 restent « jamais vérifiée »**, chacune pour une raison honnête : 2 n'ont pas de version datée
  (OSM en flux continu, INPI qui expose v3.0 sans date → règle anti-invention 6.2), 1 est interne
  (Coût de construction), 4 sur une sortie du modèle non exploitable en JSON (un nouveau passage
  pourrait les résoudre — le parseur robuste de ce lot a déjà récupéré INPI/PVGIS/CBS d'un run où
  ils tombaient « JSON invalide »).
