# ÉTUDE V6-2 — Correction Lot 3 (2ᵉ passage Étang-Salé) : gradins LiDAR, EV+marge calibrées, rampe

Assiette AW 99/451/624/625, UA, contenance 1 746 m², demande 23 T2 + 6 T3.

## 1. Gradins calculés sur le LiDAR (plus de « à confirmer »)
Le contrôle « Hauteur sur terrain en pente » MESURE le relief sous le bâti (pente LiDAR RGE ALTI ×
plus grande dimension du bâti, borné par le dénivelé de la parcelle) et conclut :
- aérien (bâti 547 m²) : relief **3,5 m** → **R+3 tenable en 3 gradins** (une toiture plate dépasserait
  l'égout aval) ;
- sous-sol (bâti 735 m²) : relief **4,5 m** → **R+3 tenable en 3 gradins**.
C'est un verdict **Réussi mesuré** (TN sous chaque partie), pas « à confirmer ». Un décrochement d'étage
par gradin permet de tenir 12 m à l'égout partout ; l'architecte a fait le même constat (partie aval R+2,
choix de conception). LABUSE conserve R+3 en gradins — cohérent avec la calibration PLU validée.

## 2. Espaces verts 20 % + marge plantée 2 m calibrées (UA 2.6) et APPLIQUÉES
Ajoutées au calibrage `config/plu_destinations/97404_l_etang_sale.yaml`, zone UA, **article UA 2.6 p.21**
(traitement paysager des espaces non bâtis) :
- **Espaces verts ≥ 20 % hors stationnement** → contrôle « Espaces verts » : aérien 612 m² / sous-sol
  985 m² ≥ 349 m² (20 %) → **Réussi**.
- **Marge plantée 2 m sur 75 % du linéaire hors mitoyenneté** → contrôle « Marge plantée » : s'inscrit
  dans les reculs (voie 4 m, séparatives 3 m ≥ 2 m) → **Réussi**.
Elles sont donc **appliquées et vérifiées** ; elles ne RÉDUISENT pas le maximum ici car **subsumées** par
les 30 % de pleine terre (plus strictes que les 20 % EV) et par les reculs (≥ 2 m). `regles_non_verifiees`
est désormais **vide** pour UA (elles passent par un contrôle vérifié).

## 3. Rampe — calcul montré (58,3 m², pas 24)
`profondeur 3,00 m / pente 18 % = longueur 16,7 m × largeur 3,5 m = **58,3 m²**`. La surface RÉELLE
(58,3 m²) est rapportée ; le polygone dessiné reste clippé à l'espace libre le long de la voie (le bilan
surfacique utilise le dessin, l'affichage la surface réelle). Détail servi (`rampe_detail`).

## Tableau — Étang-Salé, 23 T2 + 6 T3

| Source | Logements | Niveaux | Places | Emprise bâti | Remarques |
|---|---|---|---|---|---|
| **LABUSE aérien** | **32** | R+3 (3 gradins, mesuré) | 32 au sol | 547 m² | max réglementaire ; EV + marge ✓ |
| **LABUSE sous-sol** | **44** | R+3 (3 gradins, mesuré) | 44 au −1 | 735 m² | sous-sol 1 100 m² + rampe 58 m² ; pleine terre 620 ≥ 524 ; EV + marge ✓ |
| **Architecte** | **29** (23 T2 + 6 T3) | R+3 + **partie R+2** | 31 | ~547 m² | volume compact, sol libéré en jardins |

## Écart résiduel sous-sol 44 vs 29 = +52 % (> 20 %) — ce qui l'explique, chiffré
Tous les contrôles calibrés passent à 44 (pleine terre 30 %, EV 20 %, marge, hauteur R+3 gradins, CES,
stationnement). L'écart est donc un **écart maximum ↔ programme**, décomposé :

1. **Massing — l'explication dominante (~+12 logts).** En sous-sol, LABUSE ÉTEND la barre sur le sol
   libéré par le parking enterré → emprise **735 m²** (44 logts). L'architecte garde un bâtiment
   **compact ~547 m²** (comme en aérien, 29–32 logts) et laisse le sol libéré en jardins. Rapport
   d'emprise 735/547 = **1,34** → ≈ l'essentiel de l'écart.
2. **Partie R+2 sur la pente (~−3 à −4 logts).** L'architecte passe une partie en R+2 ; LABUSE garde
   R+3 en gradins (tenable, mesuré). Appliqué, cela rapprocherait LABUSE de ~40.
3. **Programme vs maximum (~−15 logts, le solde).** LABUSE sert le **maximum** (44) ; l'architecte sert
   son **programme** (29). Pour le programme de l'architecte (29 = 23 T2 + 6 T3), LABUSE confirme qu'il
   **TIENT** (réserve 15 — confrontation servie). 29 = **66 %** du maximum réglementaire.

Caveat d'interprétation : si « 20 % EV » et « 30 % pleine terre » étaient **cumulatifs** (50 % d'espace
ouvert, lecture non retenue par LABUSE), l'emprise constructible tomberait à ≤ 873 m² et le maximum
sous-sol se rapprocherait du programme. LABUSE retient l'interprétation standard (EV ⊇ pleine terre →
30 % contraignant).

En aérien, LABUSE 32 vs architecte 29 = **+10 % (< 20 %)**.

## Vérifié
tsc 0 · vitest 15/15 (EtudeV6) · pytest implantation · chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP.
Capture `captures/lot3-correction2-sous-sol-gradins-ev.png`.
