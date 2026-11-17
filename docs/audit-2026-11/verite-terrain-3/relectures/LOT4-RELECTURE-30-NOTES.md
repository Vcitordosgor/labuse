# VERITE-TERRAIN-3 — LOT 4, relecture des 30 « permis réels sous-classés » (lecture seule)

Date : 2026-11-15 · Base : labuse (SELECT seulement) · Moteur rejoué : `labuse.scoring.score_labuse.score_batch`
(code de la branche, caches servis du jour) + `labuse.faisabilite.db.parcel_faisabilite` pour les bande 0.
Les scores du CSV incluent le malus accès du run de cascade servi (`q_v19_sources`) ; le rejeu sans cascade
donne les mêmes chiffres au facteur `acces=PASS` (×0,85) près.

## Lecture d'ensemble

Le classement n'est PAS un verdict de constructibilité : la bande D « Faible » signifie « peu d'intérêt
promoteur » (SDP résiduelle < 200 m² ⇒ 15-35 points de capacité, avant facteurs). Or les 25 parcelles D de la
cohorte ont toutes reçu un permis pour **1 maison individuelle** (2 logements pour 2 d'entre elles) : une bande
D est donc COMPATIBLE avec ces permis dans la moitié des cas (le résiduel LABUSE contient la surface autorisée).
Le vrai sujet est ailleurs : (a) dans 10 cas la SDP résiduelle est INFÉRIEURE à la surface habitable réellement
autorisée — le moteur de capacité (reculs séparatifs systématiques, % d'emprise, niveaux) sous-estime sur les
petites parcelles urbaines bâties en limite ; (b) les 5 « bande 0 » sont pour 3 d'entre elles des CACHES
PÉRIMÉS (le moteur actuel ne dit plus `terrain_exigu`).

## Tableau — parcelle par parcelle

Décomposition : score = points(SDP) × f_pente × f_forme × f_accès × f_bâti (plancher 0,4).
« SDP < permis ? » compare `sdp_residuelle_m2` à `surf_hab` autorisée (la SDP devrait être ≥ surf. habitable).

| idu | bande (score) | SDP rés. | surf_hab permis | facteurs appliqués | raison du sous-classement | verdict |
|---|---|---|---|---|---|---|
| 97420000BH2087 | 0 | 0 | 211 (2 lgt) | — | zone A 100 % (GPU PLU 2025-09-29, vérifié par intersection) ; moteur actuel idem (`zone_transition`→A) | **permis atypique / contradiction** — permis 2026-04 (REY-UNION INVEST, 2 lgt) POSTÉRIEUR au PLU 2025 en zone A pleine : dérogation agricole peu plausible, rattachement cadastral Sitadel ou zonage à re-vérifier sur pièce |
| 97421000AB0337 | 0 | 0 | 117 | f_pente 0,6 (33 %) | zone Aba 80,5 % — libellé GPU « **Milieu rural habité** » ; LABUSE la ferme par famille A générique ; aucun extrait Aba dans `plu_reglement_extrait` (Salazie : A, N, U, UT, AUE seulement) | **règle non ingérée (donnée LABUSE incomplète)** — un secteur « milieu rural habité » (type STECAL) admet normalement l'habitat ; le permis 2025 le confirme |
| 97406000AW0822 | 0 | 0 | 53 | — | cache `parcel_residuel` (21/10) dit `terrain_exigu` sur… **3 294 m²** (Ur 100 %, PPR B3 prescription seulement) ; le moteur ACTUEL rend `assiette_a_verifier` (= NC « Analyse incomplète », jamais bande 0) | **donnée LABUSE fausse (cache périmé)** — la bande 0 servie contredit le propre moteur ; le permis (maison 53 m²) confirme le doute |
| 97414000EM0999 | 0 | 0 | 126 | — | idem : cache `terrain_exigu` sur 316 m² plats (pente 2,5°, 1AUb2 100 %) ; moteur actuel = `assiette_a_verifier` | **donnée LABUSE fausse (cache périmé)** — devrait être NC, pas « Non retenue » |
| 97422000BN1868 | 0 | 0 | 65 | f_pente 0,6 (99 %!) | cache `terrain_exigu` ; le moteur actuel calcule **~33 m² de SDP** (assiette 24 m² hors PPR rouge) ; PPR R1+R2 interdiction ≈ 74 % de la parcelle + Nco 19 % + pente 44,7° | **donnée périmée, fermeture partiellement défendable** — le 0 servi est faux (moteur : 33 m² → D), mais le fond (PPR rouge aux 3/4, pente extrême) rend le permis de 65 m² surprenant |
| 97405000AZ0999 | D (14) | 11 | 124 | ×0,9 bâti 3 % | parcelle 135 m² : reculs + emprise ⇒ 11 m² résiduels, alors que le permis autorise 124 m² habitables (construction en limite, multi-niveaux) | **barème sévère** — sous-estimation ×11 ; cas extrême du modèle reculs sur micro-parcelle urbaine |
| 97407000AS1092 | D (15) | 78 | 135 | aucun malus | 215 m², plat : capacité gabarit 78 m² < 135 m² réalisés | **barème sévère** (emprise/niveaux prudents) |
| 97413000BD0242 | D (9) | 47 | 89 | ×0,6 pente 31 % | 715 m² mais SDP gabarit 47 m² seulement + malus pente | **barème sévère** — 47 m² sur 715 m² est anormalement bas, à instruire côté gabarit |
| 97423000AK0487 | D (9) | 36 | 74 | ×0,6 pente 31 % | 258 m², SDP 36 < 74 autorisés | **barème sévère** |
| 97419000AR0818 | D (12) | 62 | 90 | ×0,8 forme (lame) | 334 m², SDP 62 < 90 | **barème sévère** |
| 97422000AY1569 | D (9) | 68 | 98 | ×0,85 pente ×0,8 bâti ×0,85 accès | 192 m², SDP 68 < 98 | **barème sévère** |
| 97413000BM0837 | D (8) | 79 | 114 | ×0,6 pente 36 % ×0,85 accès | 469 m², SDP 79 < 114 | **barème sévère** |
| 97412000CH0446 | D (15) | 41 | 78 | aucun malus | 205 m² (1AU5ru), SDP 41 < 78 | **barème sévère** |
| 97416000HY1658 | D (13) | 72 | 107 | ×0,85 pente 22 % | 453 m², SDP 72 < 107 | **barème sévère** |
| 97404000AD1585 | D (25) | 123 | 156 (2 lgt) | ×0,85 pente ×0,85 accès | SDP 123 < 156 ; sans le malus accès le score serait 30 (= C) | **barème sévère** (et effet de seuil accès, cf. synthèse) |
| 97401000AM1949 | D (21) | 90 | 94 | ×0,6 pente 36 % | écart 4 % — le résiduel colle au permis ; la bande D vient de la pente réelle (36 %) + petite capacité | **justifié (limite)** |
| 97413000CY1464 | D (15) | 72 | 74 | aucun malus | écart 3 % | **justifié (limite)** |
| 97405000AR1914 | D (10) | 44 | 47 | ×0,85 pente ×0,9 bâti ×0,85 accès | écart 6 % | **justifié (limite)** |
| 97413000DK0574 | D (21) | 90 | 96 | ×0,6 pente 31 % | écart 6 % | **justifié (limite)** |
| 97405000AR1731 | D (17) | 126 | 26 | ×0,6 pente 37 % ×0,8 forme | permis = petite construction 26 m² ; résiduel 126 m² la contient 5× | **justifié** — « Faible » = 1 maison possible, aucun intérêt promoteur ; le permis réel (26 m²) le confirme |
| 97413000AV2186 | D (9) | 60 | 34 | ×0,6 pente 37 % | résiduel ≥ permis | **justifié** |
| 97416000HY1705 | D (21) | 189 | 100 | ×0,6 pente 31 % | résiduel ≥ permis | **justifié** |
| 97411000DY0272 | D (13) | 75 | 62 | ×0,85 pente 22 % | résiduel ≥ permis | **justifié** |
| 97403000AP2309 | D (8) | 78 | 64 | ×0,6 pente 34 % ×0,9 bâti | résiduel ≥ permis | **justifié** |
| 97401000AP0301 | D (24) | 182 | 113 | ×0,85 pente ×0,8 bâti | résiduel ≥ permis | **justifié** |
| 97415000DT0809 | D (23) | 128 | 80 | ×0,85 pente ×0,9 bâti ×0,85 accès | résiduel ≥ permis | **justifié** |
| 97413000BH1151 | D (21) | 111 | 57 | ×0,6 pente 36 % | résiduel ≥ permis | **justifié** |
| 97416000IA1906 | D (25) | 90 | 76 | ×0,85 pente ×0,85 accès | résiduel ≥ permis ; sans malus accès = 30 (C) | **justifié** (effet de seuil accès) |
| 97415000EO0830 | D (25) | 88 | 61 | ×0,85 pente ×0,85 accès | résiduel ≥ permis ; sans malus accès = 30 (C) | **justifié** (effet de seuil accès) |
| 97423000AK1793 | D (13) | 74 | 72 | ×0,85 pente 29 % | résiduel ≥ permis | **justifié** |

## Synthèse par motif (30 parcelles)

| motif | n | parcelles |
|---|---|---|
| **Justifié** — bande D cohérente : SDP résiduelle ≥ surface autorisée, « Faible » = 1 maison, pas d'opportunité promoteur | 11 | AR1731, AV2186, HY1705, DY0272, AP2309, AP0301, DT0809, BH1151, IA1906, EO0830, AK1793 |
| **Justifié (limite)** — écart SDP/permis < 10 % | 4 | AM1949, CY1464, AR1914, DK0574 |
| **Barème/moteur sévère** — SDP résiduelle < surface habitable réellement autorisée (reculs séparatifs systématiques, emprise/niveaux prudents sur petites parcelles bâties en limite ; sous-estimation ×1,2 à ×11) | 10 | AZ0999, AS1092, BD0242, AK0487, AR0818, AY1569, BM0837, CH0446, HY1658, AD1585 |
| **Donnée LABUSE fausse (cache `parcel_residuel` périmé)** — bande 0 servie alors que le moteur actuel rend « assiette à vérifier » (NC) ou une SDP > 0 | 3 | AW0822 (3 294 m² dits « exigus » !), EM0999, BN1868 |
| **Règle non ingérée** — sous-zone Aba « Milieu rural habité » fermée par famille A générique | 1 | AB0337 |
| **Permis atypique / contradiction à instruire** — zone A 100 % au PLU en vigueur (2025), permis investisseur 2 lgt postérieur | 1 | BH2087 |

### Trois constats transverses
1. **Les 3 caches `terrain_exigu` de bande 0 sont périmés** (calcul du 21/10) : rejoués au moteur du jour,
   aucun ne rend `terrain_exigu`. La bande « Non retenue » servie est fausse pour AW0822/EM0999 (devrait être
   NC « Analyse incomplète ») et pour BN1868 (devrait être D). C'est exactement le motif C3-04/C3-05 déjà
   traité côté score — mais le stock résiduel, lui, n'a pas été rejoué.
2. **Le malus pente domine la bande D** : 19/25 parcelles D portent un malus pente (0,85 ou 0,6), sur des
   pentes réelles (MNT) de 15-37 %. Les permis prouvent qu'on y construit : le facteur est un a priori de
   prospection défendable, pas une erreur de donnée.
3. **Effet de seuil accès** : AD1585, IA1906, EO0830 ne sont D (25) que par le malus `acces=PASS` (×0,85) du
   run `q_v19_sources` ; sans lui, score 30 = bande C « À étudier ».
