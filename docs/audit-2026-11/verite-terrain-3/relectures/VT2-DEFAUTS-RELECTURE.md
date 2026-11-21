# VT2-DEFAUTS-RELECTURE — relecture des défauts hérités de VERITE-TERRAIN-2 (VT-3, 15/11/2026)

Audit **lecture seule stricte** (DB `read_only`, moteur rejoué en lecture, aucun écrit hors `relectures/`).
Sources : `PERMIS-VS-CAPACITE-NOV.csv` (rejeu VT-3) vs `docs/audit-2026-10/verite-terrain-2/PERMIS-VS-CAPACITE.csv`
(VT-2, commit `f1dfeb950` du 18/10/2026) ; cache `cache/capacite/<idu>.json` ; moteur `parcel_faisabilite` +
`build_gabarit_input`/`compute_gabarit` rejoués le 15/11 (traces : `_v1_moteur.json`, `_v1_setbacks.json`) ;
règlements : table `plu_reglement_extrait` (verbatim + page PDF) et citations des YAML `config/plu_destinations/`.

---

## Volet 1 — les 21 régressions (« ≤ capacité » en octobre → « densité > calibrage » aujourd'hui)

### 1.0 Constat transversal — la prémisse « le PLU modélisé a changé de millésime » est RÉFUTÉE

* Le **millésime PLU est identique** dans les deux CSV pour chacun des 21 permis (ex. La Possession
  `2025-12-17` des deux côtés, Saint-Joseph `2025-12-10`, Sainte-Rose `2019-05-04`).
* Les **YAML des 6 communes n'ont pas changé** depuis le run d'octobre :
  `git diff f1dfeb950..HEAD -- config/plu_destinations/{97402,97406,97408,97412,97414,97419}_*.yaml` = **0 ligne**.
* Ce qui a changé, c'est le **code du moteur**. Cause identifiée :
  **FAISA-REGLES-1 (D-024), commit `3cf76e039` du 31/10/2026** (postérieur au run VT-2 du 18/10),
  `src/labuse/gabarit/builder.py` ≈ l.273-290 : quand le règlement lie le recul séparatif à la hauteur
  (« H/2, minimum N m »), le recul retenu devient `max(minimum, h × fraction)` avec
  **`h = FAÎTAGE maximal de la zone`** (`_h_ref = haut if haut is not None else egout`).
  En octobre, le moteur appliquait le **minimum** (3–4 m).
* **Reconstruction numérique** (preuve du mécanisme) :
  * `97408000AO1919` (La Possession UA, 579 m²) — octobre : inset uniforme 3 m = 311 m²
    (`SELECT ST_Area(ST_Buffer(geom_2975,-3)) FROM parcels WHERE idu='97408000AO1919'` → 311) ;
    311 × 45 % × 4 niveaux = **560 ≈ 564 (capacité oct.)**. Novembre : recul appliqué **8,0 m = 16 m (faîtage UA)/2**
    → assiette 40 m² ; 40 × 45 % × 4 = **72 ≈ 73 (capacité nov.)**.
  * `97412000BO0496` (Saint-Joseph U3, 403 m²) — octobre : inset 3 m = 196 m² ; 196 × 45 % × 3 = **264,6 ≈ 264**.
    Novembre : recul **6,5 m = 13 (faîtage U3)/2** → assiette 60 m² ; 60 × 45 % × 3 = **81 = 81**.
* Les valeurs CALIBRÉES des YAML (hauteurs, CES, pleine terre, reculs minimaux, stationnement) ont été
  confrontées une à une au verbatim `plu_reglement_extrait` pour les 14 zones concernées : **toutes retrouvées
  conformes** (seules exceptions : extraits absents de la base pour Saint-Louis UD 6/7/12 — mais UD 10
  « 6 m égout / 10 m faîtage » et UD 9 CES 40 % retrouvés p.62). **L'erreur n'est pas dans les YAML, elle est
  dans l'application du recul par le builder.**

### 1.1 La nouvelle règle appliquée contredit le règlement verbatim (3 chefs de preuve)

Le moteur applique aujourd'hui, sur TOUTES les limites séparatives, un retrait fixe = **faîtage maximal de la zone ÷ 2**.
Les règlements disent autre chose :

1. **La règle ne vaut qu'« en cas de retrait »** — l'implantation **sur la limite** est expressément autorisée :
   * La Possession, ARTICLE UA 7 (p.15) et UB 7 (p.30) : « *Les constructions peuvent être implantées sur deux
     limites séparatives, sur une seule ou en retrait.* »
   * Bras-Panon, ARTICLE UB 7 (p.30) : « *Les constructions peuvent être implantées sur les deux limites
     latérales, sur une seule ou en retrait.* » ; UC 7 (p.43) : « *…en retrait ou sur une seule limite séparative
     latérale, sur une profondeur maximale de 20 mètres…* »
   * Saint-Joseph, ARTICLE U3 (p.48) : « *…sur les deux limites séparatives, sur une seule ou en retrait.* » ;
     U5 (p.78) : « *…sur une seule limite séparative ou en retrait.* »
   * Sainte-Rose, ARTICLE UA 7 (p.13) : « *…en retrait ou : sur les deux limites séparatives latérales pour les
     terrains dont la largeur sur voie est inférieure ou égale à 14 mètres…* » (UC 7 p.31 : seuil 12 m).
2. **Quand il y a retrait, H est la hauteur de la FAÇADE CONCERNÉE, pas le faîtage maximal de la zone** :
   * La Possession UA 7/UB 7 : « *…au moins égale à la moitié de la hauteur **à l'égout du toit** de la façade
     concernée (H/2) sans pouvoir être inférieure à 3 mètres.* » Le moteur applique 16/2 = 8 m (UA) et 12/2 = 6 m
     (UB) alors que, même au pire cas de son propre gabarit (égout retenu 13 m en UA), H/2 ≤ 6,5 m.
   * Bras-Panon UB/UC 7 : « *…moitié de la hauteur de la façade concernée (H/2)…* » (égout de zone 8 m → ≤ 4 m) ;
     le moteur applique 11/2 = 5,5 m.
   * Saint-Joseph U3/U5 7.2 : « *…moitié de la hauteur (H) de la façade concernée, avec un minimum de 3 mètres* »
     (égout U3 11 m → ≤ 5,5 m ; U5 7 m → ≤ 3,5 m) ; le moteur applique 6,5 m et 4,5 m.
3. **Conséquence mesurable** : la « capacité » servie est tombée SOUS la SDP de permis réellement accordés
   (19 cas ci-dessous), alors qu'en octobre elle les couvrait. Le permis réel est la contre-épreuve que
   l'enveloppe réglementaire dépasse la capacité servie.

NB : le coefficient d'occupation 45 % et le plafond de densité sont des hypothèses de modélisation déclarées
(« hypothèse occupation ») présentes AUSSI en octobre — ils n'expliquent pas la régression, le recul si.

### 1.2 Les 21 cas

| # | Permis | Commune | Zone | SDP autorisée (m²) | Capacité oct. | Capacité nov. | Niveaux nov. | Assiette gabarit nov. (recul séparatif appliqué) | Verdict |
|---|--------|---------|------|-----|-----|-----|----|---------------------------------------------------|---------|
| 1 | 97440226A0026 | Bras-Panon | Uc (U) | 113 | 185 | 80 | 2 | AD0387: sép 5.5 m, assiette 83.6 m² | `erreur_calibrage_nouveau` |
| 2 | 97440226A0029 | Bras-Panon | Ub (U) | 167 | 223 | 100 | 2 | AH1916: sép 5.5 m, assiette 111.0 m² | `erreur_calibrage_nouveau` |
| 3 | 9744062510042 | La Plaine-des-Palmistes | AUr (AU) | 78 | 103 | 67 | 1 | AP0422: sép 3.5 m, assiette 146.2 m², 41.0 % exclu PPR | `regle_nouvelle_correcte` |
| 4 | 9744082500116 | La Possession | UBc (U) | 136 | 170 | 86 | 2 / None | AC3753: sép 5.0 m, assiette 95.4 m² ; AC3757: gabarit non servi (Limites de la parcelle non qualifiées (v…) | `erreur_calibrage_nouveau` |
| 5 | 9744082500149 | La Possession | UBc (U) | 147 | 176 | 90 | 2 | AC3429: sép 5.0 m, assiette 100.1 m² | `erreur_calibrage_nouveau` |
| 6 | 9744082500151 | La Possession | UB (U) | 172 | 403 | 152 | 3 / 3 | AN1382: sép 6.0 m, assiette 15.3 m² ; AN1912: sép 6.0 m, assiette 97.7 m² | `erreur_calibrage_nouveau` |
| 7 | 9744082600033 | La Possession | AUB (AU) | 122 | 275 | 97 | 3 / None / None | AS0457: sép 6.0 m, assiette 71.7 m² ; AS0498: sép 6.0 m, assiette 0.0 m² ; AS0583: sép None m, assiette 0.0 m² | `erreur_calibrage_nouveau` |
| 8 | 9744082600037 | La Possession | UA (U) | 191 | 564 | 73 | 4 | AO1919: sép 8.0 m, assiette 40.1 m² | `erreur_calibrage_nouveau` |
| 9 | 9744082600045 | La Possession | UBc (U) | 125 | 201 | 92 | 2 / None | AB0302: sép 5.0 m, assiette 102.1 m² ; AB0333: sép 5.0 m, assiette 0.0 m² | `erreur_calibrage_nouveau` |
| 10 | 9744082600051 | La Possession | UBc (U) | 108 | 175 | 87 | 2 | AC3538: sép 5.0 m, assiette 96.2 m² | `erreur_calibrage_nouveau` |
| 11 | 9744082600068 | La Possession | UBc (U) | 158 | 174 | 85 | 2 | AC3540: sép 5.0 m, assiette 93.8 m² | `erreur_calibrage_nouveau` |
| 12 | 9744082600090 | La Possession | AUB (AU) | 102 | 233 | 74 | 3 | AS0606: sép 6.0 m, assiette 55.5 m² | `erreur_calibrage_nouveau` |
| 13 | 9744122500228 | Saint-Joseph | U3 (U) | 145 | 264 | 81 | 3 | BO0496: sép 6.5 m, assiette 60.1 m² | `erreur_calibrage_nouveau` |
| 14 | 9744122500242 | Saint-Joseph | U5 (U) | 112 | 115 | 85 | 2 | CT0213: sép 4.5 m, assiette 95.6 m² | `erreur_calibrage_nouveau` |
| 15 | 9744122600034 | Saint-Joseph | U3a (U) | 165 | 175 | 115 | 2 | CD0348: sép 4.5 m, assiette 130.8 m² | `erreur_calibrage_nouveau` |
| 16 | 9744122600085 | Saint-Joseph | U3a (U) | 106 | 131 | 64 | 2 | CD0857: sép 4.5 m, assiette 66.8 m² | `erreur_calibrage_nouveau` |
| 17 | 9744122600093 | Saint-Joseph | U5ma (U) | 121 | 150 | 83 | 2 / 2 | BK1935: sép 4.5 m, assiette 78.2 m² ; BK1938: sép 4.5 m, assiette 15.8 m² | `erreur_calibrage_nouveau` |
| 18 | 97441425A0266 | Saint-Louis | UD1 (U) | 147 | 163 | 132 | None / 2 / None | CH1873: gabarit non servi (Limites de la parcelle non qualifiées (v…) ; CH1877: sép 3.0 m, assiette 144.8 m², 24.0 % exclu PPR ; CH1879: sép 3.0 m, assiette 0.0 m² | `regle_nouvelle_correcte` |
| 19 | 9744191900024 | Sainte-Rose | 1AUc (AU) | 236 | 223 | 167 | 2 | AS0725: sép 4.5 m, assiette 193.9 m² | `erreur_calibrage_nouveau` |
| 20 | 9744192200037 | Sainte-Rose | 1AUa (AU) | 140 | 158 | 83 | 3 | AL1122: sép 6.0 m, assiette 61.4 m² | `erreur_calibrage_nouveau` |
| 21 | 9744192200041 | Sainte-Rose | 1AUa (AU) | 143 | 157 | 46 | 3 | AL1109: sép 6.0 m, assiette 34.1 m² | `erreur_calibrage_nouveau` |

Lecture du tableau : « sép N m » = retrait séparatif appliqué par le gabarit aujourd'hui (fichier `_v1_setbacks.json`,
rejouable) ; l'assiette d'octobre se reconstruit avec un inset ~3 m (cf. §1.0). Capacités en m² de plancher.

### 1.3 Les deux cas `regle_nouvelle_correcte`

* **9744062510042 (La Plaine-des-Palmistes, AUr→Ur, parcelle AP0422)** — retrait appliqué 3,5 m = verbatim
  ARTICLE Ur 7 (p.52, règle fixe 3,50 m) : conforme. La baisse (103 → 67) vient de la **découpe PPR nouvellement
  appliquée** : 41,5 % de la parcelle en zonage PPR `INTERDICTION` (mesure SQL :
  `SUM(ST_Area(ST_Intersection(s.geom_2975,p.geom_2975)))/ST_Area(p.geom_2975)` sur `spatial_layers kind='ppr'
  subtype='INTERDICTION'` = 41,5 %). Appliquer l'inconstructibilité PPR est une règle réelle, pas une erreur ;
  le permis (78 m²) a pu s'implanter hors zone rouge. Le permis reste légal, la capacité prudente est défendable.
* **97441425A0266 (Saint-Louis, UD1, CH1873/1877/1879)** — retrait appliqué 3,0 m (pas de formule H/2 calibrée
  en UD) ; verbatim ARTICLE UD 7 (p.60) : « *…au moins égale 3 mètres* » : conforme. Baisse (163 → 132) due à la
  découpe PPR (24 % de CH1877 exclu ; 37,4 % mesuré en `INTERDICTION`) et aux deux éclats CH1873 (42 m²) et
  CH1879 (5 m²) réellement vides à 3 m d'inset. Capacité 132 vs autorisé 147 : écart modeste et motivé.

### 1.4 Verdicts volet 1

| Verdict | Nombre |
|---------|--------|
| `erreur_calibrage_nouveau` (retrait séparatif = faîtage/2 appliqué en entier, contredit l'art. 7 verbatim) | **19** |
| `regle_nouvelle_correcte` (découpe PPR réelle, retraits conformes au verbatim) | **2** |
| `indetermine` | 0 |

Attention de lecture : il ne s'agit PAS d'une « nouvelle règle PLU » (aucun millésime ni YAML n'a bougé) mais d'un
nouveau mode d'application du moteur (commit `3cf76e039`, D-024). Les 19 permis anciens restent légaux ; c'est la
capacité LABUSE d'aujourd'hui qui les sous-couvre.

---

## Volet 2 — les 219 restés « non constructible LABUSE »

### 2.0 Population et tirage

219 permis sont « non constructible LABUSE » dans les DEUX CSV (418 en octobre → 219 aujourd'hui).
Classement par la cause des parcelles du cache VT-3 (en ignorant « parcelle absente du cadastre servi ») :
**zone_non_constructible 136, terrain_exigu 69, autres 14** — l'énoncé du mandat (137/71/11) diffère de ±3 cas
(permis mixtes au bord des classes) ; le tirage reste à graine fixe et reproductible :
tri `md5(permit_id || 'VT3-219')`, 10 premiers de chaque groupe (`_v2_sample.json`).

### 2.1 Groupe « terrain_exigu » (10 cas)

| # | Permis | Commune | Zone | Parcelle(s) (surface ; bâti) | Permis (SDP pl. ; lgts ; état) | Inset −3 m (SQL) | Verdict |
|---|--------|---------|------|------------------------------|-----------------------------|------------------|---------|
| E1 | 97440921A0264 | Saint-André | UB | BI0220 (234 m² ; bâti 166 m²) | 219 m² ; 5 ; achevé | **57,7 m² (NON vide)** | `erreur_labuse` |
| E2 | 97441313A0168 | Saint-Leu | UD | AC0847 (43 m² ; 0) | 113 m² ; 1 | 0 | `decalage` |
| E3 | 97441626E0410 | Saint-Pierre | Ud | DS0780 (131 m² ; bâti 119 m² = 91 %) | 179 m² ; 2 | 0 | `decalage` |
| E4 | 97440922A0157 | Saint-André | UB | BI0198 (158 m² ; bâti 157 m² = 100 %) | 147 m² ; 1 ; achevé | 0 | `decalage` |
| E5 | 97442224A0459 | Le Tampon | Ub | BS0575 (ABSENTE du cadastre servi) + BS1568 (10 m²) | 117 m² ; 1 | 0 | `decalage` |
| E6 | 97441323A0068 | Saint-Leu | UB | CN0467 (95 m² ; bâti 61) + CN0304 (61 m² ; bâti 38) | 68 m² ; 1 ; achevé | 0 / 0 | `indetermine` |
| E7 | 9744192100030 | Sainte-Rose | Ua | AL1149 (160 m² ; bâti 46) | 70 m² ; 1 | 0 | `erreur_labuse` |
| E8 | 97441313A0195 | Saint-Leu | UD | CN0182 (ABSENTE) + CN0587 (134 m² ; 0) | 147 m² ; 1 | 0 | `decalage` |
| E9 | 9744122500222 | Saint-Joseph | U3 | BT0712 (43 m²) + BT0711 (833 m², **cadastre_disparue_le 2026-09-01**) | 74 m² ; 1 | 0 | `decalage` |
| E10 | 9744082600041 | La Possession | UB | AR1343 (42 m²) + AR1356 (192 m² ; 0) | 115 m² ; 1 | 0,1 / 0 | `erreur_labuse` |

**Preuves des erreurs confirmées :**

* **E1 — BI0220 (Saint-André UB)** : `SELECT ST_Area(ST_Buffer(geom_2975,-3)) FROM parcels WHERE
  idu='97409000BI0220'` → **57,7 m² > seuil d'exigu (5 m²)**. Le règlement de Saint-André (PLU 2019, pièce
  officielle citée au YAML `97409_saint_andre.yaml`, extraits non chargés en base) fixe : UB 7 p.27 « *En cas de
  retrait de la construction, la distance […] doit être au moins égale 3 mètres* » ; UB 8 p.28 « *Non réglementée,
  sous réserve que la distance minimale entre les ouvertures en vis-à-vis […] soit de 8 mètres* » ; l'article 5
  (superficie minimale) est supprimé par la loi ALUR — **aucun minimum parcellaire**. Avec les retraits du
  règlement (3 m), la parcelle N'EST PAS vide : le verdict « terrain trop exigu compte tenu des reculs (3 m) »
  est produit par les reculs sur-appliqués du gabarit (même racine D-024 que le volet 1). Permis réel : 5
  logements, 219 m², achevé.
* **E7 — AL1149 (Sainte-Rose Ua, 160 m², largeur < 14 m)** : verbatim ARTICLE UA 7 p.13 : « *Les constructions
  peuvent être implantées […] sur les deux limites séparatives latérales pour les terrains dont la largeur sur
  voie est inférieure ou égale à 14 mètres* ». Le règlement organise précisément la constructibilité des terrains
  étroits en autorisant l'implantation EN LIMITE ; le modèle LABUSE impose 3 m partout et déclare la parcelle
  inconstructible. Pas de minimum parcellaire. Permis réel : 70 m², 1 logement.
* **E10 — AR1356 (La Possession UB, 192 m²)** : verbatim ARTICLE UB 7 p.30 : « *Les constructions peuvent être
  implantées sur deux limites séparatives, sur une seule ou en retrait* » (retrait, s'il y en a un : H/2 à
  l'égout, min 3 m). La bande de 192 m² s'annule sous un retrait uniforme (inset −3 m = 0) mais le règlement
  n'impose PAS ce retrait. Permis réel : 115 m², 1 logement, état avancé.

Les `decalage` : parcelles micro-découpées (43, 10, 5 m²), parcelles 100 % couvertes par le bâti issu du permis
lui-même (BI0198, DS0780), parcelle porteuse disparue du cadastre servi (BT0711, redécoupage 09/2026) ou
jamais retrouvée (BS0575, CN0182) : la capacité « parcelle seule, état d'aujourd'hui » ne compare pas la même
chose que le permis (assiette d'origine, terrain nu d'alors). E6 `indetermine` : 95 + 61 m² réellement minuscules,
règlement de Saint-Leu non chargé en base (pas de verbatim opposable).

### 2.2 Groupe « zone_non_constructible » (10 cas)

| # | Permis | Commune | Zone | Parcelle (surface ; bâti) | Permis (SDP pl. ; lgts ; état) | Verdict |
|---|--------|---------|------|---------------------------|-----------------------------|---------|
| Z1 | 97440919A0280 | Saint-André | Aba | BN0418 (426 m² ; bâti 259) | 138 m² (hab. 120) ; 1 | `erreur_labuse` |
| Z2 | 97441026A0024 | Saint-Benoît | N | AK0001 (1 181 m² ; 0) | 89 m² ; 1 | `indetermine` |
| Z3 | 97441021A0281 | Saint-Benoît | Ns34 | CL0965 (438 m² ; bâti 109) | 138 m² ; 1 | `erreur_labuse` |
| Z4 | 97442124A0056 | Salazie | Aba | AT0111 (1 428 m² ; bâti 160) | 91 m² ; 1 | `erreur_labuse` |
| Z5 | 97440921A0058 | Saint-André | A | AV1228 (763 m² ; 0) | 156 m² ; 1 | `indetermine` |
| Z6 | 97442025A0093 | Sainte-Suzanne | A | BH2087 (1 229 m² ; 0) | 243 m² ; 2 | `indetermine` |
| Z7 | 97442123A0022 | Salazie | Aba | AB0010 (4 674 m² ; bâti 107) | 75 m² ; 1 | `erreur_labuse` |
| Z8 | 97441021A0312 | Saint-Benoît | Ns46 | BN0445 (297 m² ; 0) | 87 m² ; 1 | `erreur_labuse` |
| Z9 | 97441021A0214 | Saint-Benoît | Ns21 | AC0670 (501 m² ; bâti 171) | 114 m² ; 1 | `erreur_labuse` |
| Z10 | 97441623A0473 | Saint-Pierre | Us | HX0656 (908 m² ; bâti 82) | 116 m² ; 2 | `exception_legale` |

**Preuves des erreurs confirmées** (le moteur rend « Construction neuve non autorisée en zone X » — rejouées le
15/11, `_v2_moteur.json`) :

* **Z3/Z8/Z9 — Saint-Benoît, secteurs Ns*** : verbatim `plu_reglement_extrait` 97410, Article N-2 (p.42) :
  « *Dans les zones Ns : toute construction nouvelle, **à l'exception des constructions à usage d'habitation**,
  des hébergements touristiques et des activités non polluantes, constituant un hameau intégré à
  l'environnement…* » — l'habitat neuf y est ADMIS (STECAL « hameaux ») ; le règlement fixe même l'emprise :
  « *En zone Ns et Nta : l'emprise au sol des constructions ne peut excéder 70 % du terrain* » (Section 2, p.46).
  Dire ces secteurs « fermés » est une règle existante non ingérée — les 3 permis (87–138 m², 1 logement) y sont
  réguliers de plein droit du règlement.
* **Z4/Z7 — Salazie, secteur Aba** : verbatim 97421, ARTICLE A2 (p.41) : « *Dans le secteur Aba, les
  constructions nouvelles à usage d'habitation [sont admises] dès lors qu'elles s'intègrent dans leur
  environnement […] dans la limite totale de **150 m² de surface de plancher*** » (secteur L.151-13 du code de
  l'urbanisme, présenté comme STECAL en milieu rural habité). Permis de 91 et 75 m² ≤ 150 m² : conformes à la
  lettre du règlement ; la zone n'est pas « non constructible ».
* **Z1 — Saint-André, secteur Aba** : règlement officiel 2019 cité au YAML (`A2.2 (11)`, p.106) : « *Dans le
  secteur Aba, les constructions nouvelles à usage d'habitation […] admises dans la limite totale de 120 m² de
  surface de plancher* ». Permis : 120 m² habitables (1 logement). La fermeture totale de la zone est fausse ;
  extraits 97409 absents de `plu_reglement_extrait` (citation portée par le YAML, document officiel mairie).

**Autres verdicts :**

* **Z10 — Saint-Pierre Us** : verbatim ARTICLE Us1 (p.129) : interdits sauf « *l'extension ou la transformation
  des constructions existantes dans leur destination actuelle…* ». Parcelle déjà bâtie (82 m²) ; permis 2
  logements/101 m² habitables : compatible avec une transformation/extension admise → `exception_legale`
  (le « non constructible pour du neuf » de LABUSE n'est pas contredit, mais le permis est légalement possible).
* **Z2 (N Saint-Benoît), Z5 (A Saint-André), Z6 (A Sainte-Suzanne)** : zones effectivement fermées à l'habitat
  ordinaire (N-2 p.42 ; A1.2 p.104 Saint-André ; Sainte-Suzanne A2 2.2 : seule « *l'habitation principale d'un
  exploitant agricole […] dans la limite totale de 120 m² de surface de plancher* » est admise — le permis Z6
  fait 243 m², au-delà). Logement d'exploitant possible mais non démontrable depuis les données (pétitionnaire
  vide dans Sit@del) → `indetermine` (exception légale plausible, preuve manquante).

### 2.3 Verdicts volet 2

| Verdict | Nombre | Cas |
|---------|--------|-----|
| `erreur_labuse` | **9** | E1, E7, E10, Z1, Z3, Z4, Z7, Z8, Z9 |
| `decalage` | 6 | E2, E3, E4, E5, E8, E9 |
| `exception_legale` | 1 | Z10 |
| `indetermine` | 4 | E6, Z2, Z5, Z6 |

Deux motifs d'erreur dominent : (a) **exigu fabriqué par les retraits sur-appliqués** (même racine que le volet 1 —
le règlement autorise l'implantation en limite et ne fixe aucun minimum parcellaire) ; (b) **STECAL/secteurs
habités (Aba, Ns*) traités comme zones fermées** alors que le règlement y admet l'habitat neuf sous plafond de
surface — règle existante, non ingérée par le moteur (le calibrage YAML de Saint-André la connaît pourtant :
`sous_destinations.logement.statut='sous_condition'`).

---

## Synthèse

* **Volet 1 (21 régressions)** : 19 `erreur_calibrage_nouveau`, 2 `regle_nouvelle_correcte`, 0 `indetermine`.
  Cause unique des 19 : depuis le commit `3cf76e039` (FAISA-REGLES-1 D-024, 31/10), le retrait séparatif
  « H/2 min 3 m » est appliqué avec **H = faîtage maximal de zone, sur toutes les limites, sans l'option
  d'implantation en limite** que les règlements accordent verbatim. Ni millésime ni YAML n'ont changé.
* **Volet 2 (20 cas tirés des 219)** : 9 `erreur_labuse`, 6 `decalage`, 1 `exception_legale`, 4 `indetermine`.
