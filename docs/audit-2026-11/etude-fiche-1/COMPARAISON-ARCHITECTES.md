# LABUSE Étude de faisabilité vs 4 études d'architecte

Rejeu de l'endpoint `POST /modules/etude` (backend local `127.0.0.1:7300`) sur les **mêmes parcelles et le même programme** que 4 études capacitaires d'architecte réelles (La Réunion, oct. 2026). Réponses brutes archivées dans `replays/`.

## SYNTHÈSE

**LABUSE sous-estime systématiquement la capacité des grands collectifs, et surestime (légèrement) celle du lotissement.** Sur les 3 cas collectifs/RPA, LABUSE propose 18 à 48 % du nombre de logements de l'architecte (Étang-Salé 28 vs 29 ≈ parité ; Saint-André 18 vs 48 ; Saint-Denis 12 vs 22). La cause dominante est **géométrique** : LABUSE n'implante qu'une (ou deux) **barre(s) de profondeur fixe 13 m** sur la seule *zone d'implantation* restant après reculs, là où l'architecte remplit la parcelle avec plusieurs bâtiments, des L et des redans. S'ajoutent deux amplificateurs : (1) LABUSE **tient compte du PPR** (zone rouge + bleue) que les plans d'architecte ignorent ou traitent comme aménageable — spectaculaire à Saint-André (3 745 m² de zone bleue retirés → zone d'implantation ramenée à 2 006 m² sur 4 163) ; (2) un **plafond de hauteur réglementaire** strict (12 m faîtage = R+3 à Étang-Salé, 9 m égout = R+2 à Saint-André). Pour le lotissement (Saint-Leu), le pavage déterministe de LABUSE découpe **36 lots** contre **30** à l'architecte, car il densifie au `lot_cible` 450 m² sans les contraintes de desserte/pente réelles. Verdict LABUSE : jamais « ne tient pas » au sens bloquant, mais « À compléter / Exploitable sous hypothèses » avec un déficit de logements affiché.

---

## Cas 1 — Étang-Salé (collectif 29 logts) · AW99/451/624/625 · zone UA · 1 746 m²

Programme architecte : 29 logts (23 T2 dont 13 T2bis + 6 T3 sociaux) + 1 commerce 98 m², R+3, **31 places dont 1 aérien (reste en sous-sol -1)**.
Rejeu LABUSE en `saisi` (23 T2 + 6 T3) et `propose`. Commerce et sous-sol non modélisés (`stationnement: aerien`).

| Grandeur | LABUSE (saisi) | Architecte | Écart | Cause probable |
|---|---|---|---|---|
| Logements | **28** (24 T2 + 4 T3 ; tiennent 23 T2 + 4 T3) | 29 | −1 (2 T3 « manquent ») | Quasi-parité ; les 2 T3 ne rentrent pas dans la barre, limités par la hauteur R+3 |
| Places stationnement | **30** | 31 (dont 1 aérien) | −1 | LABUSE aérien seul 536 m² ; archi met le parking en **sous-sol -1** (non modélisé) |
| Surface de plancher | **2 190 m²** (SDP plancher dessinée) | 2 368 m² (y/c coursives+varangues) ; SHAB 1 653 m² | −178 m² | Périmètres différents : LABUSE = plancher hors varangues ; SDP *autorisée* calculée 4 884 m² (1 221 × R+3) jamais atteinte |
| Emprise au sol | **614 m²** (bilan) | 710 m² (projet ; max régl. 1 222 m²) | −96 m² | Barre 13 m de profondeur < emprise réelle du projet ; CES 70 % laisse 607 m² mobilisables non utilisés |
| Hauteur (R+n) | **R+3** (plafond 12 m égout) | R+3 | 0 | Accord : LABUSE lit UA 2.5.2 = 12 m égout / 15 m faîtage |

Facteur limitant déclaré : **stationnement aérien** (sans parking imposé : 36 logts possibles vs 28). C'est le cas le plus proche : parité à ±1 logement. L'écart résiduel vient de ce que LABUSE met **tout le stationnement en aérien** (536 m² mangés sur l'assiette) alors que l'architecte l'enterre au niveau −1, et de la profondeur de barre fixe qui plafonne l'emprise à 614 m² contre 710 m². La SDP diverge surtout par convention de mesure (varangues/coursives incluses côté architecte).

---

## Cas 2 — Saint-André (collectif 48 logts) · AX255/256 · zone UC · 4 163 m² (cad. archi : 4 181)

Programme architecte : 48 logts (17 T2 + 22 T3 + 9 T4), **R+2** (RDJ+R+1+R+2, 16 logts/niveau), 48 places (1/logt), SDP intérieure 2 568 m².
Rejeu LABUSE en `saisi` (17 T2 + 22 T3 + 9 T4).

| Grandeur | LABUSE (saisi) | Architecte | Écart | Cause probable |
|---|---|---|---|---|
| Logements | **18** (6 T2 + 9 T3 + 3 T4) | 48 | **−30 (37 %)** | Barre unique 608 m² sur zone d'implantation réduite ; archi remplit la parcelle de plusieurs bâtiments |
| Places stationnement | **27** | 48 (1/logt) | −21 | Découle du nombre de logts (barème UC 12.2 appliqué aux 18 seulement) |
| Surface de plancher | **1 627 m²** | 2 568 m² (intérieur, hors circulations) | −941 m² | Moins de logts × moins d'emprise ; conventions SHAB/SDP différentes |
| Emprise au sol | **608 m²** | ≈ non chiffrée (parcelle 4 181, extérieurs privatifs 782 m²) | — | LABUSE n'exploite que 608 m² d'une assiette constructible qu'il a lui-même ramenée à 2 006 m² |
| Hauteur (R+n) | **R+2** (plafond 9 m égout) | R+2 | 0 | Accord sur la hauteur (UC 10 : 9 m égout / 12 m faîtage) |

Message LABUSE : « *la hauteur réglementaire (9 m, soit R+2 atteint)* » ; facteur stationnement **non** limitant (18 = 18 sans parking). **Le vrai moteur de l'écart est double.** (1) LABUSE **voit le PPR** que l'architecte ignore : `ppr_bleue_m2 = 3 745` + `ppr_rouge_m2 = 399` sur 4 163 m², d'où une `zone_implantation_m2` effondrée à **2 006 m²** (48 % de la parcelle) — alors que le plan d'architecte bâtit sur toute l'emprise. (2) À hauteur égale (R+2), LABUSE n'implante **qu'une seule barre de 608 m²** quand l'architecte compose plusieurs plots/ailes totalisant bien plus d'emprise bâtie. Le ×2,7 de logements de l'architecte vient donc de la forme bâtie, amplifié par la prise en compte du risque.

---

## Cas 3 — Saint-Denis RPA/senior (22 logts, PPR) · DL247/248 · zone Ui · 1 580 m²

Programme architecte : 22 logts RPA + LCR (titre) ; le plan RDC annonce **27 logts T2 RPA LLTS** + LCR 51,58 m². T2+V 55,34 m². Emprise bâti **377 m² (24 %)**, perméable 984,60 m² (62 %), **8 places (1 pl/3 logts)**, hauteur max 18 m.
Rejeu LABUSE `senior`, `saisi` (22 T2) et `propose`.

| Grandeur | LABUSE (saisi 22 T2) | Architecte (titre) | Écart | Cause probable |
|---|---|---|---|---|
| Logements | **12** (12 T2) | 22 (plan : 27) | **−10 (−15)** | Barre unique 258 m² d'emprise sur zone d'implantation 649 m² (PPR + reculs) |
| Places stationnement | **12** (1/logt) | 8 (1 pl/3 logts dérogé RPA) | **+4** | LABUSE applique le barème **1 place/logement** (art. XVII), ignore la **dérogation RPA 1/3** |
| Surface de plancher | **920 m²** | ≈ 377 m² emprise × niveaux (≈ 1 220 m² SHAB T2) | − | Moins de logts ; conventions différentes |
| Emprise au sol | **258 m²** | **377 m² (24 %)** | −119 m² | Barre 13 m < emprise projet ; CES 60 % (Ui.9) laisse de la marge |
| Hauteur (R+n) | **R+3** (saisi) / **R+4** (propose) | ≈ R+3 (coupe, haut. max 18 m) | ~0 | Accord : LABUSE lit 18 m faîtage (Ui.10) |

Facteur limitant : **stationnement aérien**. Ici deux divergences propres. (1) LABUSE **surestime le stationnement exigé** : il impose 1 place/logt (art. XVII) là où l'architecte retient **1 place pour 3 logts** (régime dérogatoire RPA) — d'où 12 places LABUSE vs 8 architecte malgré moins de logements. (2) LABUSE **voit le PPR** (`ppr_rouge 548 m²` + `ppr_bleue 234 m²`, cohérent avec la zone rouge/bleue des plans), ramenant la `zone_implantation` à 649 m² sur 1 580, et sa barre unique (258 m² d'emprise) reste sous les 377 m² bâtis par l'architecte. Le `propose` descend même à 10 logts (T3/T4) en R+4 : LABUSE ne sait pas qu'il s'agit de petits T2 RPA de 55 m² et dimensionne des logements plus grands.

---

## Cas 4 — Saint-Leu (lotissement 30 lots) · AC261/262/264 · zone UD

**NOTE cadastre : la parcelle AC0263 est ABSENTE de la table cadastrale LABUSE** ; seules 3 des 4 parcelles existent (AC0261, AC0262, AC0264). Le rejeu a donc porté sur **3 parcelles**. L'étude d'architecte porte sur AC261 (12 261 m²) + AC264 (9 979 m²) = 30 lots (16 + 14).

Rejeu LABUSE `lotissement`, `propose`. Clé `lotissement` présente.

| Grandeur | LABUSE | Architecte | Écart | Cause probable |
|---|---|---|---|---|
| Lots | **36** (moy. 407 m², min 251 / max 450) | 30 (16 + 14) | **+6** | Pavage déterministe au `lot_cible` 450 m² sur net constructible 20 314 m² ; pas de desserte/pente réelle |
| Places stationnement | **2/lot** (total 72) + 29 visiteurs estimés | 2/lot + 13 + 12 = 25 visiteurs | +4 visiteurs | Barème UD 12 « logt individuel » 2 pl/lot concordant ; visiteurs = convention |
| Surface de plancher | non calculée (lotissement = découpage foncier) | non déclarée (lots de plain-pied T3/T4 68–96 m²) | — | LABUSE ne dimensionne pas les maisons en mode lotissement |
| Emprise au sol | CES 40 % (UD 9) servi, pleine terre 40 % « Réussi » | construction étagée, lots de plain-pied | — | Accord sur CES/pleine terre |
| Hauteur (R+n) | n/a (lots nus) | plain-pied / R+1 étagé | — | Non comparable |

Assiette LABUSE (3 parcelles) : `assiette_m2 = 23 734`, `net_constructible = 20 314`, voirie 2 404 m² « réseau en peigne (3 voies) », `ppr_rouge 2 130 m²`. **LABUSE découpe 36 lots** contre 30 à l'architecte. Deux causes : (1) LABUSE pave au `lot_cible` 450 m² et descend jusqu'à 251 m² (aucune superficie minimale servie au PLU UD, art. 5 supprimé par ALUR), là où l'architecte maintient 400–450 m² réels avec une trame de desserte plus lâche ; (2) la voirie LABUSE (2 404 m², 5 m, hypothèse) est bien plus légère que les ~2 400 + 4 900 m² de voirie principale+secondaire déclarés par l'architecte sur les deux parcelles, libérant du foncier pour plus de lots. LABUSE précise lui-même que c'est un « **pré-lotissement indicatif**, ni plan de géomètre ni droit à diviser ».

---

## Tableau de synthèse (logements/lots)

| Cas | Type | LABUSE | Architecte | Ratio LABUSE/archi |
|---|---|---|---|---|
| Étang-Salé | collectif | 28 | 29 | 0,97 |
| Saint-André | collectif | 18 | 48 | 0,38 |
| Saint-Denis | senior/RPA | 12 (propose : 10) | 22 (plan : 27) | 0,55 |
| Saint-Leu | lotissement | 36 lots | 30 lots | 1,20 |

**Causes récurrentes du sous-dimensionnement collectif** : (a) forme bâtie limitée à barre / deux_barres / L de **profondeur fixe 13 m** sur la seule zone d'implantation après reculs (ne remplit pas la parcelle comme un architecte) ; (b) **stationnement 100 % aérien** par défaut (mange l'assiette ; l'architecte enterre) ; (c) **prise en compte du PPR** rouge+bleue absente des plans d'architecte (décisif à Saint-André et Saint-Denis) ; (d) barèmes de stationnement PLU au pied de la lettre (ignore la dérogation RPA 1/3 à Saint-Denis) ; (e) hauteurs réglementaires strictes (concordantes avec l'architecte dans les 3 cas). Le lotissement, lui, est **sur**dimensionné car le pavage déterministe densifie sans les servitudes de desserte/pente réelles.
