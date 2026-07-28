# AUDIT DES CALIBRAGES EXISTANTS — SAINT-PAUL & SAINT-DENIS

> Demandé par Vic avant le lancement de la commune n°2 (Le Tampon), avec la grille de qualité
> du pilote Saint-Pierre. **Audit en lecture seule — AUCUNE correction appliquée.**
> Exécuté le 27/07/2026 (branche `feat/plu-saint-pierre`).

---

## 1 · Couverture réelle (manifeste × YAML × pool servi)

Méthode : chaque libellé distinct du manifeste de zonage passé dans `resolve_zone(lib, commune)` ;
pool servi = run épinglé `q_v7_defisc`, tiers non écartés, jointure spatiale point-dans-zone.

### Saint-Paul (67 libellés, 765 polygones, mode `strict`)

| Catégorie | Libellés | Pool servi |
|---|---|---|
| Calibrés chiffrés | 49 (tous les U/AU des 6 bassins + Usdu) | **12 839 parcelles ≈ 97,6 %** |
| Calibrés gel (AU*st) | 5 | 187 |
| Calibré sans hauteur exploitable | 1 (AU1lec, tout `a_verifier`) | 1 |
| Non résolus (strict → « non calculable ») | 12 — familles A/N (A, Acu, An, N, Ncor, Ncu, Nerl, Ni, Nrh, Nto, Ntoa, Ntol) | 127 (~1 %) |

Le « non calculable » strict sur A/N est produit-équivalent à non-constructible — cohérent.

### Saint-Denis (33 libellés, 259 polygones, mode `progressif`)

| Catégorie | Libellés | Pool servi |
|---|---|---|
| Calibrés chiffrés | 20 | **4 437 parcelles ≈ 92,3 %** |
| Repli générique — familles A/N | A, Ac, N, Npf, Ntc, Ntn | 18 (verdict repli correct : non constructibles) |
| **Repli générique — zones U/AU** | **Uavap (302 servies !), AUx (44), Uat (4), Upi (2), Udo (0), Uma (0), Upr (0)** | **352** |

Détail des 352 : Uavap = « non calibrable par nature » (AVAP, acté au YAML — mais 302 parcelles
servies en R+2 estimé) ; AUx = zone d'activités « non réglementé » partout → repli **optimiste**
(44 parcelles servies en R+2 estimé, habitat vraisemblablement interdit — cas exact du
« repli optimiste » mesuré au pilote) ; Upi/Upr = TODO documenté (hauteur dans un tableau-IMAGE
p.34, lecture manuelle jamais faite).

## 2 · Sourçage article + page (exigence mandat-cadre)

Comptage automatique sur les champs de valeur (he/hf, emprise, reculs, stationnement,
pleine terre, habitat) vs champs `_src` :

| Fichier | Valeurs portées | CHIFFRÉES sans source | Chiffrées sans n° de page | `a_verifier` |
|---|---|---|---|---|
| plu_saint_paul.yaml | 250 | **3** (recul_limites 3 m sur U1ec, U2e, U3e) | **48** (« Art. 7 », « Art. 6, zone U2a »… sans page) + nombreuses pages `~` approximatives | 63 (25 %), dont 25 sans `_src` |
| plu_saint_denis.yaml | 189 | **0** | **0** | 44 (23 %), tous sourcés |
| (référence pilote : plu_saint_pierre.yaml) | 196 | 0 | 0 | 7 (3,6 %) |

Saint-Denis est exemplaire sur la forme. Saint-Paul a un déficit de forme (pages absentes ou
approximatives sur ~1 valeur chiffrée sur 5 ; 3 valeurs chiffrées sans source du tout —
vraisemblablement le motif transverse Art. 7 « retrait 3 m » appliqué aux zones e sans citation).

## 3 · Le `emprise_sol_pct: null` massif de Saint-Paul — VÉRIFIÉ SUR PIÈCES : lecture réelle

Règlement téléchargé depuis l'URL du YAML (413 p., édition mars 2026 — lien vivant). Contrôle
demandé sur 3 zones, étendu à un scan complet des Article 9 :

- **U1** (PDF 23) : « Article 9 - Emprise au sol des constructions — **Il n'est pas fixé de
  règle.** » ✓ conforme au YAML (`null` + citation).
- **U2a** (PDF 74) : idem, mot pour mot. ✓
- **U3** (PDF 114) : idem. ✓
- Scan complet : **17 des 22 Article 9 du document disent « Il n'est pas fixé de règle »** ;
  les 4 chapitres Usdu disent « Dans la limite des surfaces perméables imposées » — et le YAML
  les porte justement en `a_verifier` avec note « règle propre ≠ pas de règle », PAS en `null`.

**Conclusion : le `null` massif est une lecture fidèle du règlement, pas une paresse de
gravure.** La distinction null / a_verifier y est correctement appliquée.

## 4 · Chantiers « ÉTAPE A » / « lot 1 » — complétés ?

- **Saint-Paul : OUI.** `dd75fc1` (10/06 08:22, « zone U1 ») puis `68f0bdd` (08:33, « extraction
  complète des 6 bassins ~30 zones ») le même jour, suivis d'enrichissements successifs
  (géométrie réelle + exemption U1pru, plafond densité, habitat interdit zones e — `a4ac967`,
  mixité sourcée). L'état actuel n'est PAS celui du premier lot.
- **Saint-Denis : OUI pour les lots annoncés** — lot 1 (`10da465`), lot 2 (`7cbe43a` : Ua, Uv,
  AUm/AUh/AUj/AUa), puis prospect par parcelle (`f660477`) et Uavap acté non calibrable
  (`4a9f042`). **MAIS le TODO d'en-tête n'a jamais été soldé** : « Reste à finir : Upi/Upr
  hauteur (tableau image p.34, lecture manuelle) » — toujours vrai aujourd'hui (2 parcelles
  servies concernées).

## 5 · Écart repli vs calibré (même protocole que le pilote : 400 parcelles, seed 42, moteur complet)

| Commune | Perdent constructibilité | Delta SDP médian | Quartiles | hausse/baisse/égal |
|---|---|---|---|---|
| Saint-Pierre (pilote, référence) | 15/400 (0 gagnée) | **-33 %** | -38 / -33 % | 58 / 299 / 0 |
| **Saint-Paul** | 11/400 (0 gagnée) | **-33,2 %** | -33,3 / 0 % | 35 / 196 / 126 |
| **Saint-Denis** | 25/400 (0 gagnée) | **-52,9 %** | -81,1 / -29,4 % | 29 / 297 / 27 |

Les deux calibrages APPORTENT massivement — aucun n'est creux. Les 126 « égal » de Saint-Paul
sont légitimes : zones où le hé calibré vaut justement 9 m (= le générique) et où l'emprise est
réellement non réglementée (vérifié §3). Le -53 % de Saint-Denis confirme, sur une 3e commune,
que **le repli générique surestime structurellement** (ici surtout via l'absence d'emprise :
les caps 30-80 % de Saint-Denis mordent fort).

## 6 · ⚠ Découverte hors grille — millésime du RÈGLEMENT de Saint-Denis

Le zonage servi est `97411_PLU_20260423` (modification approuvée **23/04/2026**, GPU concordant
— audit fraîcheur du pilote). Mais le YAML des règles est sourcé sur
`97411_reglement_20240220` (« Modification simplifiée n°8, **février 2024** »). Le ZONAGE est à
jour, les RÈGLES sont gravées sur un règlement de deux modifications antérieur. Si la procédure
d'avril 2026 a modifié le règlement écrit (hauteurs, emprises…), une partie des valeurs de
Saint-Denis est périmée — **à vérifier en diffant le règlement du document GPU 20260423 contre
celui de 2024** (non fait ici : hors périmètre d'audit, aucune correction). Saint-Paul n'a pas
ce problème (édition mars 2026 du règlement, postérieure à l'idurba 20251217).

---

## VERDICTS

| Commune | Verdict | Motifs |
|---|---|---|
| **Saint-Paul** | **COMPLET — dette de forme** | 97,6 % du pool en calibré chiffré ; null vérifié sur pièces ; chantier soldé ; écart -33 % = apport réel. Dette : 3 valeurs chiffrées sans source, 48 sans n° de page, 63 a_verifier (dont Usdu emprise/pleine-terre — 598 parcelles servies, 6e pool de la commune — et les stat/pleine-terre « à préciser » des U1). Rien qui exige une re-gravure ; un lot « consolidation des sources + résolution des a_verifier à fort pool (Usdu d'abord) » suffirait. |
| **Saint-Denis** | **PARTIEL — documenté, + risque millésime** | 92,3 % du pool ; forme exemplaire (0 valeur non sourcée) ; écart -53 % = apport majeur. Manques réels : Upi/Upr (TODO image jamais soldé), AUx servi optimiste (44 parcelles — sera couvert par le mandat « Repli non optimiste »), Uavap 302 parcelles en estimé (non calibrable par nature : acceptable mais 6,3 % du pool). SURTOUT : règles gravées sur le règlement 02/2024 alors que le zonage servi est du 23/04/2026 — le diff des règlements décide s'il faut re-graver. |
| (Aucune des deux) | **à re-graver : NON** | — sous réserve du diff de millésime Saint-Denis. |

**Recommandations (à arbitrer par Vic, rien d'engagé)** : (1) avant Le Tampon ou en parallèle :
diff règlement Saint-Denis 2024-02 vs 2026-04 (une heure, archive GPU) ; (2) lot court
« consolidation Saint-Paul » (sources + Usdu) à planifier, non bloquant ; (3) le mandat « Repli
non optimiste » couvrira AUx et consorts.

---

## ADDENDUM (même jour, arbitrages Vic reçus) — LES DEUX DIFFS SONT TRANCHÉS

**Saint-Denis — risque millésime LEVÉ.** Archive GPU du document en vigueur `97411_PLU_20260423`
téléchargée ; son règlement écrit (`97411_reglement_20260423.pdf`, 154 p.) porte la couverture
« Modification simplifiée n°8 — dossier approuvé FÉVRIER 2024 » : c'est LE règlement de la
gravure, re-stampé au nom du document 2026. Valeurs vérifiées aux pages citées par le YAML :
Um.9 emprise 50 % (p.68) ✓, Ui.9 60 % / Uicm 40 % (p.56) ✓, Uh 30 % + H 4,5 m (p.73) ✓,
prospect Ud (p.43-44) ✓, Uv.9/10 (p.84) ✓. **La procédure d'avril 2026 n'a pas modifié le
règlement écrit — les règles de Saint-Denis sont À JOUR.** Le verdict PARTIEL demeure (Upi/Upr,
Uavap, AUx), la re-gravure n'est PAS nécessaire.

**Saint-Paul — vérifié dans la foulée (la liste des DCM de l'édition mars 2026 s'arrête au
27/03/2025, antérieure à l'idurba 17/12/2025)** : le règlement du document GPU en vigueur
`97415_reglement_20251217.pdf` est **BYTE-IDENTIQUE (md5 `0aee7298…`) à l'édition mars 2026**
utilisée pour la gravure. Aucun écart ; la procédure du 17/12/2025 n'a pas touché le règlement
écrit.

**Application rétroactive du garde-fou (décision Vic)** : champ `source.reglement_grave`
(fichier, md5, millésime, document GPU, date de vérification) posé sur les TROIS YAML calibrés.
Saint-Denis y documente son cas d'alerte type 4 (millésime gravé 2024-02-20 < document
2026-04-23) avec le résultat du diff — l'alerte reste légitime et se réexamine à chaque
procédure.

**Lot « consolidation Saint-Paul » — PLANIFIÉ, non bloquant (décision Vic)** : (1) les 3
valeurs chiffrées sans source (recul_limites U1ec/U2e/U3e) ; (2) les 48 citations sans n° de
page + pages `~` ; (3) résolution des `a_verifier` à fort pool, **Usdu en tête (598 parcelles
servies : emprise « surfaces perméables » et pleine terre à trancher sur pièces)**, puis les
pleine_terre/stationnement « à préciser » des U1/U2. Source à utiliser : le PDF md5 `0aee7298…`
(GPU = mairie). À prendre quand une session se libère, APRÈS Le Tampon.

**Séquence actée** : ~~diff Saint-Denis~~ (fait) → **Le Tampon** → consolidation Saint-Paul ·
« Repli non optimiste » après merge O12.
