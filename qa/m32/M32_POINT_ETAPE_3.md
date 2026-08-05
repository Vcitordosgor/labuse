# M32 — POINT D'ÉTAPE (3 communes ré-extraites)

Arbitrage Vic (a) : ré-extraction sur la **version OPPOSABLE GPU uniquement**, idurba + date
d'approbation ancrés. File de priorité par tête servie. Point d'étape obligatoire après 3.

## Méthode (rodée et reproductible)

Par commune : (1) résoudre le document `document.production` (EN_VIGUEUR) sur l'API GPU ; (2)
télécharger l'archive opposable (150–860 Mo) ; (3) extraire le **règlement** + l'**OAP** (texte) ;
(4) lire ouverture / phasage / densité / social / VRD, avec verbatim + source ; (5) ancrer idurba +
date. Limites respectées : OAP/règlement **graphiques** ou **scannés** = `non_extrait`, jamais
deviné.

## Les 3 ré-extractions

| # | Commune | Opposable | Résultat | Écart / nouveauté |
|---|---|---|---|---|
| 1 | **Saint-Louis** (97414) | 20251218 | ouverture conditionnelle_etat_tiers + phasage ; OAP 50/30 log/ha ; social non chiffré ; VRD sans_objet | **écart de version LEVÉ** — valeurs identiques au 20250926 extrait ; la modif déc. 2025 n'a pas touché l'AU |
| 3 | **Petite-Île** (97405) | 20230609 | 1AU opération d'ensemble ; 2AU phasage inter-zones ; densité non chiffrée (objectif SAR) ; OAP social 40-50%/site | **`a_verifier` ouverture LEVÉ** — verbatim capté au chapitre AU (le scan du 30/07 l'avait manqué) |
| 2 | **Le Port** (97407) | 20241209 | 1AU opération d'ensemble ; 2AU conditionnée à modif PLU ; OAP min 50 log/ha ; social non chiffré | valeurs **confirment** le 30/07, MAIS **PLU PARTIALLY_ANNULLED** — voir alerte ci-dessous |

## ⚠ Alerte Le Port — portée d'annulation NON RÉSOLUE (bloquant l'intégration)

Le Port est `PARTIALLY_ANNULLED` au GPU. Le **jugement** qui fixe la portée est un **scan image**
(13 p, 420 car. extractibles ; **OCR indisponible** sur le poste), et la portée n'apparaît en texte
ni au règlement ni à la procédure (203 p lus). **Je ne peux pas déterminer quelles parties du PLU
sont annulées** → la calibration Le Port est marquée **PROVISOIRE** et **ne doit PAS entrer au
moteur (Phase C)** tant que la portée n'est pas confirmée. **Demande à Vic** : lire le jugement (ou
fournir la portée) — l'annulation touche-t-elle les zones AU ?

## Découvertes transverses confirmées (limites schéma v1)

- **Dépendance de phasage INTER-ZONES** re-confirmée à Petite-Île (2AU n'ouvre qu'une fois TOUTES
  les 1AU urbanisées) — le schéma `au_ouverture` v1 ne la porte pas. Consignée par yaml.
- **Densité PAR SITE** = calque graphique OAP (Saint-Louis rouge/orange, Petite-Île, Le Port) →
  `non_extrait` au site près en v1 ; la valeur GLOBALE (log/ha) est servie, pas la ventilation site.
- **Densité = objectif SAR** (Petite-Île « devra tendre vers ») ≠ plancher dur → `sans_objet` densité.

## Contrainte de rythme (honnête)

Chaque commune = **150–860 Mo** d'archive GPU (une a dû être re-téléchargée, corrompue au resume).
Le débit est le facteur limitant (~15-25 min/commune). Les textes extraits sont conservés pour trace ;
les zips (~1,6 Go) supprimés après extraction.

## File restante (après ce point d'étape)

4. Sainte-Suzanne (97420, 18) · 5. Les Avirons (97401, 17) · 6. La Plaine (97406, 35 têtes mais OAP
graphique — limité) · 7. Sainte-Rose (97419, 5) · 8. Salazie (97421, 4) · 9. Bras-Panon (97402, 3).
Prochain point d'étape après 3 de plus. **Rien n'est intégré au moteur** (Phase C) sans GO Vic — et
Le Port reste bloqué sur la portée d'annulation.
