# PLU-CALIBRAGE-9 — mixité sociale, 24 communes

> **Mandat** : brancher la clause de mixité sociale des règlements PLU (seuil → quota de
> logements aidés) pour que la capacité la sorte « N logements aidés imposés (Sourcé) » ou
> « non imposé » / « sans objet ».
> **Branche** `feat/plu-calibrage-9`, worktree `~/Desktop/labuse-plu9`, ports 8801 / 6001.
> **Modèle** Opus. **Livrable** : ce RAPPORT + `SONDAGE-10.md`.
>
> **ÉTAPE 0** ✅ — `pwd` = worktree, branche = `feat/plu-calibrage-9`, arbre propre,
> PLU-8 présent dans `main` (merge `f9f5c2e0`, ancêtre de HEAD = `main` = `495b0a88`).
> Pas de merge, pas de run résiduel, pas de residuel-serve, pas d'élargissement.

---

## LOT A — POURQUOI (lecture seule)

### Méthode

FAISA-ETUDE-AUDIT-1 (Q2, e — mixité sociale) a classé les 23 communes à PLU par lecture
directe des YAML `config/plu_destinations/*.yaml` (règlements transcrits, chaque clause
portant déjà `article` + `page_pdf` + `citation` verbatim) : **1 structurée** (bloc
`regles.<zone>.mixite` déjà posé, St-Denis), **16 en texte**, **6 introuvables** → trouvable
17/23. Le moteur (`faisabilite/engine.py:813-841`) *consomme déjà* `rules.mixite` quand le
statut est `valide` — le travail est de la **transcription + validation**, pas du code.

Relecture PLU-9 (extraction ciblée des 23 YAML + requêtes lecture seule sur les prescriptions
GPU `spatial_layers` en base) → taxonomie **affinée** : **1 structurée + 14 texte + 8
introuvables**. Divergence avec l'audit (16/6) **assumée et prouvée** : l'audit avait compté
Petite-Île et Saint-Benoît comme « texte », or leur seule mention de logement aidé est une
**règle de stationnement** (LLTS exempté de place à Petite-Île ; « 1 place pour 2 logements
aidés » à Saint-Benoît) — **aucune obligation de produire un % de logements aidés** : ce sont
donc des silences de mixité (cf. détail ci-dessous).

Pour les introuvables, recherche **hors du texte** menée comme demandé : dispositions
générales des YAML, puis prescriptions GPU en base — **secteurs de mixité sociale** (CNIG
`typepsc=17`, L.151-15) et **emplacements réservés logement** (`typepsc=05` au libellé
« logement » / « mixité », L.151-41 4°), et renvois **OAP**. (Note : `typepsc=16`, que
`config/cascade_rules.yaml` range dans `mixite_sociale_typepsc`, est en base « bâtiment
pouvant changer de destination » / « bâtiment agricole » — **pas** de la mixité ; seul `17`
l'est, et uniquement à Saint-Paul : 188 polygones « Clause logements aidés ».)

### Les 24 communes

| # | INSEE | Commune | Statut mixité | Où la règle a été cherchée / trouvée | Zones | Nb zones calibrées (Lot B) |
|---|-------|---------|---------------|--------------------------------------|-------|------|
| 1 | 97401 | Les Avirons | **TEXTE** | `sous_destinations.logement` (U 2.2 5., p.8) — 1 000 m² SDP → 40 % aidé | Ua·Ub·Uc·Ud | 4 |
| 2 | 97402 | Bras-Panon | **TEXTE** | `sous_destinations.logement` (UA/UB 2.2 (3.), p.13/26) — 4 000/2 000 m² SDP → 25 % | Ua·Ub | 2 |
| 3 | 97403 | Entre-Deux | **INTROUVABLE** | Silence : zones U/AU sans article de mixité ; seule clause voisine = **densité** 20 log/ha (≠ aidé). Hors-texte : **aucun** secteur 17 / ER logement en base | — | 0 |
| 4 | 97404 | L'Étang-Salé | **TEXTE** *(témoin)* | `sous_destinations.logement` (UA/UB 1.3 (1), p.17/27) — 1 000 m² SDP → 20 % aidé | UA·UB | 2 |
| 5 | 97405 | Petite-Île | **INTROUVABLE** | Silence de mixité : « LLTS » n'apparaît qu'en **stationnement** (exempté de place) ; renvois OAP (pièces non ingérées). Hors-texte : **aucun** secteur/ER en base | — | 0 |
| 6 | 97406 | La Plaine-des-Palmistes | **INTROUVABLE** | Silence : articles destinations sans seuil/quota ; `meta.structure` « silence lu zone par zone ». Hors-texte : **aucun** | — | 0 |
| 7 | 97407 | Le Port | **INTROUVABLE** | Silence au **règlement** : la mixité, si elle existe, est renvoyée aux **OAP** (Uoap → OAP Portes de l'Océan / Mascareignes, pièces écrites distinctes non ingérées). Hors-texte : aucun secteur 17 / ER logement en base | — | 0 |
| 8 | 97408 | La Possession | **TEXTE** | `sous_destinations.logement` (UA 2.2 7°, p.11 ; UB 2.2 4°, p.27) — 1 500 m² SDP → 20 % (hors secteurs UAm/UAv, UBa/b/c) | UA·UB | 2 |
| 9 | 97409 | Saint-André | **TEXTE** | `sous_destinations.logement` (UB/UC/UD 2.2, p.24/35/46) — 2 000 m² SDP → 40 % (hors QPV) | UB·UC·UD | 3 |
| 10 | 97410 | Saint-Benoît | **INTROUVABLE** | Silence de mixité : « logements aidés » n'apparaît qu'en **stationnement** (1 place / 2 logts aidés) ; « forte densité » = libellé de fiche. Hors-texte : **aucun** secteur/ER en base | — | 0 |
| 11 | 97411 | Saint-Denis | **STRUCTURÉ** | `regles.<zone>.mixite` **déjà posé et validé** (7 zones : Uavap, Up, Ud, Uu… Art. X.2, p.27) — 30 logts → 15 % | 7 zones | 0 *(déjà fait)* |
| 12 | 97412 | Saint-Joseph | **TEXTE** | `notes` de zone (U2/U3/U5 2.2 (4), p.30/45/74) — 2 000 m² SDP → 20 % LLS (le transcripteur avait noté « pas seuil_m2 » car condition de programme, pas plafond de destination) | U2·U3·U5 | 3 |
| 13 | 97413 | Saint-Leu | **TEXTE** | `sous_destinations.logement` (UA/UB/UC/UD 2 (2.2), p.19/29/39/49) — 600 m² SHON → 20 % logement social, **dans la zone de déficit** aux documents graphiques | UA·UB·UC·UD | 4 |
| 14 | 97414 | Saint-Louis | **TEXTE** | `sous_destinations.logement` (UA/UB/UC/UD 2.2, p.13/27/41/56) — 2 000/1 500/1 500/1 000 m² SDP → 30/30/30/20 % | UA·UB·UC·UD | 4 |
| 15 | 97415 | Saint-Paul | **TEXTE** + **secteur 17** | `sous_destinations.logement` (U1a, Art. 2.2 (3), p.14 ; U2a-h Art. 2.2, p.67) — ≥ 1 800 m² SDP → 30 % ; **confirmé hors-texte** : 188 polygones GPU « Clause logements aidés » (typepsc 17, L.151-15) | U1a·U2a·U2b·U2c | 4 |
| 16 | 97416 | Saint-Pierre | **INTROUVABLE** *(hors-texte partiel)* | Silence au **règlement de zone** (Ucv/Ud/Ug : tableau destinations sans mixité) ; renvois OAP. Hors-texte : **ER « logement social » ×2 en base** (typepsc 05, L.151-41 4° — géométrique, parcelle précise, pas une règle de zone) | — | 0 |
| 17 | 97418 | Sainte-Marie | **TEXTE** | `sous_destinations.logement` (U3, p.17) — 2 500 m² SDP → 20 % logement social (UA/UB/UC ; UC1/UC2 exclus) | UA·UB·UC | 3 |
| 18 | 97419 | Sainte-Rose | **TEXTE** | `sous_destinations.logement` (UA/UB/UC 2.2 4°, p.11/20/29) — 2 000 m² SDP → 40 % prêt aidé | UA·UB·UC | 3 |
| 19 | 97420 | Sainte-Suzanne | **TEXTE** | `sous_destinations.logement` (U3, p.11) — 4 000 m² SDP → 40 % aidé (UA/UB/UC) | UA·UB·UC | 3 |
| 20 | 97421 | Salazie | **INTROUVABLE** *(hors-texte partiel)* | Silence au **règlement** : seule clause voisine = **densité** (20/10 log/ha), renvois OAP. Hors-texte : **ER « logement social / mixité sociale » ×8 en base** (typepsc 05, L.151-41 4° — géométrique) | — | 0 |
| 21 | 97422 | Le Tampon | **TEXTE** | `sous_destinations.logement` (Ua/Ub/Uc 2.2 3°, p.13/28/43) — 3 000/1 000/1 000 m² SDP → 30 % aidé | Ua·Ub·Uc | 3 |
| 22 | 97423 | Les Trois-Bassins | **TEXTE** | `notes` de zone (Ua/Ub/Uc/AU 2.2, p.11/26/40/66) — 1 000 m² SDP → 40 % dont 25 % LLS ; opérations ≥ 1 200 m² → 40 % global | Ua·Ub·Uc·1AU* | 4 |
| 23 | 97424 | Cilaos | **INTROUVABLE** | Silence total : aucune mention mixité/aidé/social/LLS dans toutes les zones. Hors-texte : **aucun** secteur/ER en base | — | 0 |
| 24 | 97417 | Saint-Philippe | **SANS OBJET — RNU** | Aucun PLU (`config/plu_destinations/rnu.yaml`, communes `["97417"]`) : pas de zonage, donc pas de clause de mixité de zone opposable | — | 0 |

**Totaux** : 1 structurée (déjà servie) · 14 texte **à calibrer (Lot B)** · 8 introuvables
(dont 2 — Saint-Pierre, Salazie — avec un **ER logement géométrique** hors règlement de zone) ·
1 RNU. **≈ 51 zones** à calibrer sur les 14 communes texte.

### Issue par commune (synthèse)

- **Règle trouvée (où)** : 14 communes portent la clause dans `sous_destinations.logement`
  (champ `condition` + parfois `seuil_m2`/`seuil_type`) ou dans les `notes` de zone, chacune
  avec `article` + `page_pdf` + `citation` verbatim déjà présents → transcriptibles en
  `regles.<zone>.mixite` sans ré-ouvrir les PDF. Saint-Paul est de surcroît couverte par un
  **secteur graphique** L.151-15 (typepsc 17) en base.
- **Silence prouvé** : 6 communes (Entre-Deux, Petite-Île, Plaine-des-Palmistes, Le Port,
  Saint-Benoît, Cilaos) — règlement sans clause, hors-texte sans secteur/ER logement. 2
  communes (Saint-Pierre, Salazie) : silence du **règlement de zone**, mais ER logement
  géométrique en base (L.151-41 4°) — qui s'applique **à la parcelle réservée**, pas en
  servitude de zone, et reste donc hors du périmètre d'un `regles.mixite` (déjà déduit comme
  overlay). → servies « **mixité non imposée par le règlement de zone** », jamais 0.
- **Saint-Philippe** : « sans objet — RNU ».
