# A0-3 — Couverture : classer les 28 bloquées, débloquer par citation, mesurer 100+70

Lecture seule pour le lot A. Base PostGIS partagée, EPSG:2975. Captures ortho des 28 : réutilisées de
`docs/GABARIT/captures/gabarit-2/lim-<idu>.png` (mêmes parcelles, même classification) ; nouvelles
captures GABARIT-3 dans `captures/gabarit-3/`.

## Lot A — les 28 bloquées d'A0-2 par cause

Diagnostic géométrique par parcelle (voirie toute nature au contact ? parcelle-voirie collée ? voisin
chemin élancé sans bâti ? pour les non-qualifiées : distance de l'arête non classée à une voirie
carrossable et à une ravine/trait de côte).

| Cause | n | Définition |
|---|---|---|
| **E1 enclave vraie** | 14 | aucune voie BD TOPO (toute nature) ne touche la parcelle, ni parcelle-voirie collée |
| **P2 route à la marge** | 6 | arête non classée avec une voirie carrossable à ~5 m (juste au-delà du seuil A0-2) |
| **P1 emprise publique** | 5 | arête sans voisin ni route à portée (place, parking, domaine public non routier) |
| **P1 ravine / littoral** | 2 | arête non classée le long d'une ravine BD TOPO ou du trait de côte |
| **E2 chemin privé cadastré** | 1 | enclave desservie par un voisin chemin (élancé, sans bâti) hors BD TOPO |
| **Total** | **28** | |

Détail (idu → cause) :

- **E1 (14)** : 97411000CH0196, 97411000HK0106, 97411000CD1318, 97416000CW1762, 97415000EX0029,
  97411000AS0314, 97411000BE0689, 97411000DP0305, 97411000HO0180, 97407000AS0592, 97409000AC0746,
  97411000CD1504, 97407000AM1059, 97411000IT0415.
- **P2 (6)** : 97411000DL0527, 97407000AE0256, 97411000AH0137, 97407000AL0484, 97409000AH0235, 97409000AE0290.
- **P1 emprise publique (5)** : 97411000HP0606, 97415000CP1097, 97411000IE0026, 97411000AT0595, 97411000AZ0027.
- **P1 ravine / littoral (2)** : 97410000AN0347, 97422000BW1189.
- **E2 (1)** : 97411000DH0088.

### Levier de déblocage par cause

- **E1** → servie en séparatives seules (recul limites partout, recul voie « sans objet »). Lot B.
- **P1 (emprise publique + ravine/littoral, 7)** → servie SI la citation `retraits.voie` de la zone vise
  « voies **et emprises publiques** » (mesuré : couvert dans de nombreuses zones — Le Port Uem/Us,
  Saint-André UA/UB, Saint-Denis Ud, Saint-Joseph U1, Saint-Leu UF/UP, Saint-Paul U1b/c/d…). Sinon
  bloquée « emprise publique non routière : le règlement ne précise pas le recul ». Lot C.
- **P2 (6)** → remesure (surface de route absente en base → `largeur` + marge documentée). Beaucoup sont
  absorbées par le Lot C (arête ouverte = emprise publique si la citation la couvre). Lot D.
- **E2 (1)** → reste bloquée « accès par voie privée non qualifiée », sauf citation visant les voies
  privées (Saint-Benoît Ua/Ub). Lot B.

## Lot D — route à la marge (P2, 6 parcelles)

Surface de route BD TOPO **absente de la base** (voirie = axe LineString seulement) → fallback
`largeur/2 + marge`. Examen des 6 : 4 bloquent désormais sur le PLU (CES/zone non calibrée) en amont
des limites ; 2 atteignent l'étape limites (DL0527 Saint-Denis, AE0256 Le Port). Géométrie des arêtes
non classées vs axe carrossable : AE0256 = frontage parallèle constant à ~5,6 m ; DL0527 = route qui
s'éloigne en courbe (5→12 m, pas une façade franche).

**Décision** : marge portée de **3,5 → 4,0 m** — capte les frontages légèrement en retrait (AE0256),
**audité 0 faux-voie** sur les 70 d'A0-2 ET sur 100 parcelles tirées au sort. Pas d'élargissement
au-delà : DL0527 (route à 8–12 m au milieu) reste bloquée honnêtement (retrait réel, pas une façade) ;
seule la surface de route BD TOPO trancherait sans marge → recommandé pour GABARIT-4.

<!-- LOT-E -->
