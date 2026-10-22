# Études d'architectes — données extraites (source du tableau d'écarts & du contrôle de calibrage PLU)

Extraction manuelle des 4 PDF de `docs/design/maquettes/etude-v6/etudes-archi/` (lus le 2026-10-21).
Colonne « archi » = ce que les architectes affichent. Colonne « LABUSE » = à remplir après exécution du moteur v6.
Statut de chaque chiffre archi : **transcrit du PDF** (aucune valeur recalculée ici).

---

## Vérification des IDU en base (`parcels` + `parcel_zone_plu` + `parcel_geometrie`)

| IDU | Commune | Zone | Contenance base | Σ groupe (base) | Σ archi | Polsby-Popper | Largeur inscr. |
|---|---|---|---|---|---|---|---|
| 97404000AW0099 | L'Étang-Salé | UA | 501 | **1 746** | 1 746 ✓ | 0,767 | 21,9 m |
| 97404000AW0451 | L'Étang-Salé | UA | 586 | | | **0,262** ⚠ irrég. | 12,1 m |
| 97404000AW0624 | L'Étang-Salé | UA | 274 | | | 0,664 | 12,0 m |
| 97404000AW0625 | L'Étang-Salé | UA | 385 | | | 0,559 | 13,5 m |
| 97409000AX0255 | Saint-André | UC | 3 078 | **4 163** | 4 181 (**+18**) | 0,769 | 51,6 m |
| 97409000AX0256 | Saint-André | UC | 1 085 | | | 0,520 | 26,5 m |
| 97411000DL0247 | Saint-Denis | Ui | 790 | **1 580** | 1 580 ✓ | 0,590 | 16,3 m |
| 97411000DL0248 | Saint-Denis | Ui | 790 | | | 0,552 | 15,1 m |
| 97413000AC0261 | Saint-Leu | UD | 12 219 | — | 12 261 (**+42**) | **0,361** ⚠ irrég. | 85,5 m |
| 97413000AC0264 | Saint-Leu | UD | 9 979 | — | 9 979 ✓ | 0,665 | 73,9 m |

Écarts de contenance à conserver (NE PAS corriger) :
- **Saint-André** : base 4 163 m² vs archi 4 181 m² (+18 m²).
- **Saint-Leu AC261** : base 12 219 m² vs archi 12 261 m² (+42 m²).
Aucune parcelle disparue. Deux géométries irrégulières à signaler en Étape 1 (AW451, AC261).

---

## 1. L'Étang-Salé — AW99/451/624/625 — zone UA — collectif
**Cabinet** : OCEANIS / i ARCHITECTES (réf. 26024, indice B, 14/10/2026). Phase « Étude capacitaire ».
**Base PLU citée** : PLU d'Étang-Salé du 22 juin 2017, modifié le 4 décembre 2024.
Assiette : 1 746 m². Adresse : 156B-158-158B av. Raymond Barre.

### Règles PLU citées par l'archi (⇒ contrôle de calibrage LABUSE zone UA Étang-Salé)
| Thème | Règle archi |
|---|---|
| Recul voies/emprises publiques | retrait de l'alignement, **recul min 4,00 m** |
| Limites séparatives | sur 1 ou 2 limites si linéaire ≥15 m (hab) / 20 m (commerce) ; si retrait >3 m (hors balcons sur 1 m + protection solaire) |
| Constructions sur même terrain | **3 m** |
| Emprise au sol (CES) | **70 %** |
| Épannelage (hauteur) | **12 m égout – 15 m faîtage – 13 m acrotère** |
| Stationnement | 1 pl. jusqu'au T2 ; **1,5 pl. jusqu'au T4** ; 2 pl. T5 ; cellule commerciale 1 pl. si <100 m² ; 1 arbre / 2 pl. ; perméable 50 % |
| Local 2-roues/poussettes | 1 m² jusqu'au T2 ; 1,5 m² au-delà |
| Espaces verts | **20 %** hors stationnement, engazonnés ; 1 arbre / 50 m² EV ; marge plantée 2 m sur 75 % du linéaire sauf mitoyenneté |
| Perméabilité | **30 %** |
| Mixité sociale | projet >1 000 m² SDP habitation ⇒ **20 % logement aidé** (PLS+LLI 80 % T2 / 20 % T3, ou 100 % T2) |

### Résultat archi (proposition)
- **29 logements** : 23 T2 + 6 T3 (0 T4). Répartition 79 % T2 / 21 % T3. Plan masse : « 10 T2 + 13 T2 bis + 6 T3 sociaux ».
- Dont **5,8 logements sociaux** (20 %).
- **R+3** + 1 commerce 98 m² (SU 95 m²).
- SP (y/c coursives + varangues) = **2 368 m²** (+ 95 m² SU commerce). SHAB+varangue = **1 653 m²**.
- Emprise au sol **projet 710 m²** (réglementaire max 1 222,20 m² = 70 % × 1 746).
- Perméabilité projet 710 m² (min régl. 523,80 m² = 30 %).
- **Stationnement : 31 places** (dont 1 commerce) ; régl. 30. Local vélos 32 m². SHOB parking 670 m² (sous-sol).
- Hauteurs de coupe : niveaux 2,50 / 2,75 / 2,75 / 3,02 m ; accès +38,22 NGF.

---

## 2. Saint-André — AX255/256 — zone UC — collectif
**Cabinet** : ARCHI CREATIONS (Stéphanie Jammes), réf. OCEANIS, 13/10/2026. Phase FAISABILITE.
Assiette archi : 4 181 m² (base 4 163). **Aucune table de règles PLU dans le PDF** (pas de recul/CES/hauteur cités) → calibrage UC non vérifiable par ce document, seulement les surfaces.

### Résultat archi
- **48 logements collectifs**, R+2 (RDJ + R+1 + R+2).
- Répartition : **T2 = 17 (35,42 %)**, **T3 = 22 (45,83 %)**, **T4 = 9 (18,75 %)**.
- Détail niveaux :
  - RDJ : 5 T2 (48 m²) + 8 T3 (54 m²) + 3 T4 (64 m²) = 16 ; intérieur 864 m² ; jardins ~338 m².
  - R+1 : 6 T2 + 7 T3 + 3 T4 = 16 ; intérieur 852 m² ; terrasses ~222 m².
  - R+2 : idem R+1 ; intérieur 852 m² ; terrasses ~222 m².
  - **Total intérieur 2 568 m²** ; jardins ~338 m² ; terrasses ~444 m².
- **Stationnement : 48 places — 1 place / logement.**
- Extérieurs privatifs ~782 m² (jardins + terrasses).
- Mention archi : « surfaces hors circulations communes… ne constitue pas une validation réglementaire ».

---

## 3. Saint-Denis — DL247/248 — zone Ui — RPA + LCR — PPR
**Cabinet** : URBAN ARCHITECTES, octobre 2026. Phase FAISA.
**⚠ Incohérences dans le PDF à SIGNALER sans corriger :**
- Cartouche des plans FAISA01/02/03 : « **Parcelle CS 0452 – Construction de 48 logements – Le Tampon** » (mauvaise commune + mauvais n° + mauvais nb de logts : vestige d'un autre dossier).
- Page de titre : « **22 logements** RPA + LCR » ; **note du plan RDC : « 27 logements T2 de type RPA LLTS »**. Titre 22 ≠ plan 27.

### Règles PLU citées par l'archi (⇒ contrôle de calibrage LABUSE zone Ui Saint-Denis)
| Thème | Règle archi |
|---|---|
| Hauteur | **Hauteur max 18 m** |
| Recul voie | **4,00 m** (+ alignement opposé à 10 m, contre-allée 7,60 m) |
| Prospect limite | **L ≥ H** |
| PPR | parcelle 247 = **PPR zone rouge** (inconstructible) ; bande **PPR zone bleue** (constructible sous conditions). Bâti implanté hors PPR, côté Est/rue. |

### Résultat archi
- **22 / 27 logements** (voir incohérence) — tous **T2+V 55,34 m²** (RPA = résidence pour aînés).
- **LCR 51,58 m²** (local collectif résidentiel).
- Emprise bâti **377 m² = 24 %** de l'emprise foncière.
- Espace perméable **984,60 m² = 62,31 %**.
- EV : 849,35 m² (dans l'emprise PPR) + 135,25 m².
- **Stationnement : 8 places (1 pl. / 3 logements)** — ratio réduit RPA.
- Local OM 22,55 m². Ravine du Butor en limite Ouest.

---

## 4. Saint-Leu — AC261 + AC264 — zone UD (Ud) — lotissement
**Cabinet** : i ARCHITECTES / OCEANIS PROMOTION (réf. 25023, indice 2, 02/06/2026). Phase « Étude capacitaire ».
Adresse : 50-66 rue Leconte Delisle. **Deux études séparées, une par parcelle.** Division foncière (lotissement), maisons individuelles de plain-pied/étagées.

### AC 261 — 12 261 m² (archi) / 12 219 m² (base)
- **16 lots** (« de plain pied », mention « construction étagée »). Lots majoritairement 450 m² (quelques 400 m²).
- **Stationnement : 2 places / lot + 13 places visiteurs (mini).**
- Bilan sol : cheminement piéton 751,70 m² · pavés joints enherbés 1 197,78 m² · **pleine terre commun 2 391,98 m²** · **pleine terre privatif 7 011,61 m²** · voirie principale 1 609,84 m² · voirie secondaire 814,26 m².
- EBC en partie Sud de la parcelle.

### AC 264 — 9 979 m² (archi = base ✓)
- **14 lots** (plain pied / étagée). Lots 400–450 m².
- **Stationnement : 2 places / lot + 12 places visiteurs.**
- Bilan sol : cheminement piéton 1 230,43 m² · pavés joints enherbés 664,75 m² · **pleine terre commun 3 085,82 m²** · **pleine terre privatif 5 313,16 m²** · voirie principale 1 519,14 m² · voirie secondaire 4 466,26 m².

### Total lotissement : 30 lots (16 + 14)
### Types de logements (plans fournis, communs aux 2 parcelles)
T3a 68,63 · T3b 81,38 · T3c 68,62 · T4a 95,82 · T4b 89,00 m² (varangues ~9–12 m², cellier/carport).

---

## Squelette du tableau d'écarts final (LABUSE à remplir après moteur v6)

| Parcelle | Grandeur | Archi | LABUSE v6 | Écart | Statut LABUSE |
|---|---|---|---|---|---|
| Étang-Salé UA | Logements | 29 | — | — | mesuré/dérivé |
| | SDP (SP) | 2 368 m² (+95 commerce) | — | | |
| | Emprise | 710 m² (max 1 222) | — | | |
| | Hauteur | R+3 / 12-15 m | — | | |
| | Recul voie | 4 m | — | | |
| | Stationnement | 31 pl. | — | | |
| Saint-André UC | Logements | 48 | — | | |
| | Intérieur | 2 568 m² | — | | |
| | Stationnement | 48 pl. (1/logt) | — | | |
| | Niveaux | R+2 | — | | |
| Saint-Denis Ui | Logements | 22 / 27 (incohér.) | — | | |
| | Emprise | 377 m² (24 %) | — | | |
| | Stationnement | 8 pl. (1/3 logt RPA) | — | | |
| | Hauteur | 18 m | — | | |
| | PPR | rouge+bleu, bâti hors PPR | — | | |
| Saint-Leu AC261 | Lots | 16 | — | | |
| | Pleine terre | 9 403 m² (priv.+commun) | — | | |
| | Stationnement | 2/lot +13 vis. | — | | |
| Saint-Leu AC264 | Lots | 14 | — | | |
| | Pleine terre | 8 399 m² (priv.+commun) | — | | |
| | Stationnement | 2/lot +12 vis. | — | | |

## Points de calibrage PLU à confronter à LABUSE (couche règlement calibré)
1. **UA Étang-Salé** : recul 4 m · CES 70 % · 12/13/15 m · stat. 1 pl.→T2, 1,5→T4 · EV 20 % · perméa 30 % · mixité >1000 m²→20 %.
2. **UC Saint-André** : archi ne cite aucune règle → vérifier la calibration UC LABUSE indépendamment.
3. **Ui Saint-Denis** : hauteur 18 m · recul 4 m · prospect L≥H · PPR rouge/bleu.
4. **Ud Saint-Leu** : (règles non détaillées par l'archi côté texte) — lotissement, 2 pl./lot + visiteurs, pleine terre importante.
