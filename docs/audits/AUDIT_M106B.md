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
