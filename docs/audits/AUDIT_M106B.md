# AUDIT M106-B — transport : complétude, lisibilité, axes structurants

Mesuré et livré le 17/08/2026. Branche `feat/m106b-transport`.

## 1. Complétude des réseaux (Phase 1 — aucun manquant, pas de STOP)

| réseau (AOM) | présent | arrêts | lignes tracées | millésime GTFS |
|---|---|---|---|---|
| Car Jaune (Région, interurbain) | ✓ | 319 | 16 | 11/08/2026 |
| Citalis (CINOR) | ✓ | 1 618 | 71 | 16/07/2026 |
| Papang (CINOR, téléphérique) | ✓ | 10 | tracé OSM | 29/12/2025 |
| Kar'Ouest (TCO) | ✓ | 2 268 | 64 | 17/07/2026 (rafraîchi à l'ingestion du jour) |
| Alternéo (CIVIS) | ✓ | 2 375 | 57 | 17/08/2026 |
| Carsud (CASUD) | ✓ | 2 145 | 43 | 16/08/2026 |
| Estival (CIREST) | ✓ | 1 206 | 37 | 27/01/2026 |

**Couverture géographique : les 24 communes ont des arrêts** (minimum mesuré :
Bras-Panon, 85 arrêts ; maximum : Saint-Paul, 1 077). AUCUNE zone blanche par
commune — ni de terrain, ni d'ingestion. À l'intérieur des communes, les Hauts
non desservis (Mafate…) sont la réalité du terrain : la fiche la DIT par la
distance (« arrêt à 14,6 km »), jamais par un silence.
**Transports scolaires et à la demande : hors périmètre** — ils ne figurent pas
dans les 7 GTFS publiés (le PAN est exhaustif de ce que les AOM publient).

## 2. La couleur dit le réseau, la forme dit le type (Phase 2)

Tokens par thème (mapTheme.transportReseaux), critère M105-B mesuré (trait ≥ 3:1) :

| réseau | sombre (vs fond) | clair (vs terre) |
|---|---|---|
| Car Jaune — or | `#E3B93C` (9,46) | `#8A6D08` (4,39) |
| Citalis — rose | `#E87BB0` (6,62) | `#B01E63` (5,84) |
| Kar'Ouest — azur | `#6FA8E8` (7,08) | `#1D5FC2` (5,41) |
| Alternéo — turquoise | `#45D0B8` (9,20) | `#0B7D68` (4,52) |
| Estival — orange | `#E8935A` (6,71) | `#A34A00` (5,30) |
| Carsud — olive | `#B8C24A` (9,11) | `#667000` (4,83) |
| pôle d'échange — neutre | `#E8EFEA` (15,1) | `#14181A` (15,9) |
| axes — bleu-gris | `#8FA6C4` (7,06) | `#33506B` (7,50) |

Ni mint, ni mauve, ni `#F5C518` (l'or Car Jaune `#E3B93C` est volontairement
moins saturé que le jaune Pages Jaunes, qui ne vit pas sur la carte). Papang =
couleur Citalis (même réseau CINOR), le TIRETÉ dit « téléphérique ». Formes :
tracé = trait · arrêt = petit point (minzoom 12) · pôle OSM = disque plein
neutre (Sourcé) · pôle dérivé = anneau (Estimé). La légende nomme réseaux et
formes en clair — aucun code interne.

**Regroupement (Phase 2.4, PROPOSÉ, non imposé)** : à l'échelle île les six
couleurs restent distinguables (capture) ; si Vic juge la carte chargée, l'option
serait un second toggle « interurbain seul » (Car Jaune) vs « réseaux urbains »
— à arbitrer, rien d'imposé.

## 3. Axes structurants (Phase 3)

- **Qualification = la hiérarchie de la BD TOPO elle-même**, jamais inventée :
  champ `importance` IGN, niveaux 1-2 → **3 481 tronçons** (N1 — dont la route
  des Tamarins, type autoroutier —, N2, N6, D400…). Nom (cpx_numero/toponyme),
  nature et nombre de voies voyagent en attrs. PIÈGE mesuré : le cql_filter
  Géoplateforme veut la BBOX en ordre LAT/LON — l'ordre lon/lat rend 0 en silence.
- **Le libellé porte les deux faces** (fiche, tiroir Réseaux et accès) :
  « accessibilité (desserte rapide) ET nuisances potentielles (bruit, pollution ;
  recul le long des axes classés, art. L. 111-6 — non cartographié en donnée
  ouverte, à vérifier au PLU). Le classement sonore, lui, est évalué au tiroir
  Risques. » — Vérifié : les reculs L. 111-6 n'ont PAS de couche dédiée (6
  « bande de recul » marginales en prescriptions GPU) → dits non cartographiés ;
  le classement SONORE (cat. 1-5, 1 004 secteurs) est DÉJÀ évalué par la cascade
  (couche bruit_route) → pointé, pas dupliqué.
- **Proximité, jamais appartenance** : distance + nom + nature servis
  (`proximites.axe`).

## 4. Pôles d'échange de l'axe (Phase 3.4) — SIGNALEMENT

Le long de la N1, les pôles majeurs sont détectés : gares de Saint-Paul,
Pierrefonds, Saint-Louis (OSM, Sourcé) ; Zac Avenir (14 lignes), Gare Routière
Saint-Paul (31), Lycée Schoelcher (14)… (dérivés, Estimé).

**MAIS le seuil de 12 écarte des pôles manifestement structurants** — signalé
pour arbitrage, AUCUN ajustement fait :
- **« Savanna »** (pôle d'échanges réel de la route des Tamarins) : 9 lignes
  Kar'Ouest → écarté, et AUCUNE station OSM de rattrapage à moins de 3 km ;
- cause mesurée : le comptage est PAR RÉSEAU — un même lieu desservi par
  plusieurs réseaux n'est jamais cumulé (Gare de Saint-Pierre : 5 Alternéo,
  hors comptage Car Jaune ; Gare Saint-André : 6 Estival) ; la plupart sont
  rattrapés par les pôles OSM, PAS Savanna.
- piste pour l'arbitrage : cumul inter-réseaux par grappe spatiale (~150 m)
  avant seuil — change la calibration, donc décision de Vic.

### 4-bis. ARBITRAGE APPLIQUÉ : le cumul par grappe, recalibré (17/08/2026)

La dérivation cumule désormais les lignes DISTINCTES (`réseau:ligne`, union —
jamais une somme qui double-compte) d'une grappe spatiale DBSCAN. Seuil ET rayon
en config avec leur raison ; le critère complet voyage avec la donnée jusqu'à la
légende (« arrêts groupés à ≤ 150 m desservis par ≥ 14 lignes, tous réseaux
cumulés »).

**Recalibrage contre OSM (condition 1 de l'arbitrage)** — grille mesurée :

| rayon | seuil | pôles dérivés | confirmés OSM | taux | multi-réseaux |
|---|---|---|---|---|---|
| 100 m | 12 | 39 | 17 | 44 % | 15 |
| 100 m | 14 | 19 | 12 | 63 % | 11 |
| 100 m | 16 | 12 | 10 | 83 % | 9 |
| 150 m | 12 | 42 | 17 | 40 % | 16 |
| **150 m** | **14** | **19** | **11** | **58 %** | **11** |
| 150 m | 16 | 12 | 10 | 83 % | 9 |
| 150 m | 18 | 9 | 9 | 100 % | 8 |
| 200 m | 12 | 36 | 12 | 33 % | — (sur-fusion) |

**Le nouveau dénombrement refabrique des fantômes au seuil 12** (confirmation
40 % ; « Rue Frédéric Badré », « Paris », deux « Centhor », trois pôles à
Plateau Caillou — des corridors où beaucoup de lignes passent, pas des nœuds) →
**le seuil bouge avec le dénombrement, et on le dit : 12 → 14** (confirmation
58 % > l'étalon 53 % de l'ancien comptage ; les 19 retenus sont des gares, des
pôles nommés et des mairies-hubs, 11 multi-réseaux). Rayon : 200 sur-fusionne
(33 %), 100 et 150 quasi équivalents — **150 retenu** (une correspondance à pied
entre quais d'une gare dépasse souvent 100 m).

**CAS TÉMOIN RENVERSÉ PAR LA MESURE.** Savanna n'est PAS détecté — et ne peut
pas l'être par le cumul : sa grappe réelle (150 m) = 2 quais desservis par LES
MÊMES 9 lignes Kar'Ouest (l'union reste 9 ; Car Jaune ne s'y arrête pas — le
plus proche arrêt Car Jaune est « Pont de l'Étang », à 275 m, un nœud distinct).
La prémisse « Savanna = nœud multi-réseaux raté par le comptage » est donc
FAUSSE dans la donnée GTFS. Le prix pour le détecter par le seuil : **9 lignes →
88 pôles dont 75 % non confirmés par OSM** (mesuré). Constat de donnée, pas un
défaut du cumul — si Vic veut Savanna malgré ce prix, c'est un nouvel arbitrage
(ou une station OSM à faire relever sur le terrain, qui le rendrait Sourcé).

Trois tests gravent la définition (tests/test_transport_poles.py) : cumul
inter-réseaux dans une grappe · union jamais une somme (le cas Savanna) ·
pas de cumul hors grappe.

### 4-ter. Arbitrage final (Vic, 17/08/2026) — à ne pas redécouvrir

- **Seuil 14 retenu, Savanna NON détecté — décision assumée.** Savanna est un
  pôle d'échange RÉEL de la route des Tamarins que le critère ne détecte pas,
  et ce n'est PAS un bug : sa grappe GTFS réelle = deux quais desservis par les
  mêmes 9 lignes Kar'Ouest (union 9 < 14 ; Car Jaune ne s'y arrête pas — son
  arrêt le plus proche est un nœud distinct à 275 m). Forcer sa détection
  coûterait seuil 9 → 88 pôles dont 75 % non confirmés (trois pôles inventés
  sur quatre — le ratio qui avait disqualifié proba_anc en M88). REFUSÉ.
  Voie retenue : faire relever la station dans OSM (elle deviendra Sourcé,
  hors seuil) — action HORS DÉPÔT, à la main de Vic. Un futur audit qui
  retrouve « Savanna absent des pôles dérivés » lit ce paragraphe, pas un bug.
- **Le seuil 14 est calibré SUR LE COMPTAGE CUMULÉ** (grappe 150 m, union
  réseau:ligne). Si la définition du dénombrement change encore (rayon, mode
  d'union, nouvelle source), le seuil doit être RECALIBRÉ contre OSM avec la
  même grille — il n'a aucune valeur hors de cette définition.

## 5. Vérification (Phase 4)

- Captures clair + sombre, tous réseaux + axes actifs : réseaux distinguables
  entre eux et du fond dans les deux thèmes ; légende lisible seule.
- Recette : parcelle 97415000AC0016 (Saint-Paul, N1 à ~14 m — deux faces
  servies + arrêt Car Jaune 656 m) · réseaux couverts en fiche : Citalis
  (Stella 225 m), Alternéo (60 m / 4 m), Estival (7 m), Kar'Ouest (42 m),
  Car Jaune (656 m) — Carsud servi en base (2 145 arrêts), au point multi-réseaux
  testé l'arrêt le plus proche est Alternéo (4 m), honnête · zone sans desserte :
  Cilaos rural → « arrêt à 528 m, axe à 14,6 km » — l'absence est DITE par la
  distance, jamais muette.
- Golden 0 FAIL · suite complète · tsc 0 · build OK (cf. commit).
