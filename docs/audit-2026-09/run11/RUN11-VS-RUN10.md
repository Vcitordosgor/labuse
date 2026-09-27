# RUN 11 vs RUN 10 — audit comparatif (lecture seule)

**Branche :** `audit/run11` · **Date :** 2026-09-27 · **Aucune bascule, rien n'a été servi, aucune écriture en base.**

| Run | `run_seq` | Label | Servi ? |
|-----|-----------|-------|---------|
| **run 10** | 10 | `q_v15 assiette gabarit` | ✅ servi (`residuel_runs.is_served`, alimente la vue `parcel_residuel`) |
| **run 11** | 11 | `q_v15 lidar + ER/EBC` | ❌ non servi — hauteur LiDAR injectée au résiduel + SUP (ER/EBC) déduite |

Les deux runs couvrent le **même jeu de 431 663 parcelles** (0 parcelle présente d'un seul côté). La vue servie `parcel_residuel` pointe bien sur `run_seq = 10` (vérifié sur `pg_get_viewdef`).

> ⚠️ **Constat majeur, développé au §7 :** run 11 n'est *pas* seulement « run 10 + LiDAR + SUP ». Il embarque une **régression de couverture du moteur gabarit** : 73 609 parcelles perdent leur assiette gabarit et retombent sur l'assiette `residuel_legacy` (plus généreuse), dont des communes entières (Saint-André −93 %, La Plaine-des-Palmistes −100 %, Les Trois-Bassins −99 %, Saint-Denis −80 %). Cette régression, et non l'ajout LiDAR/SUP, explique ~43 % de la hausse de SDP et **inverse** le sens des deltas attendus par le mandat.

---

## 1. Parcelles calculées / avec cause / SDP totale

| Indicateur | run 10 (servi) | run 11 (non servi) | Δ |
|---|---:|---:|---:|
| Parcelles évaluées | 431 663 | 431 663 | 0 |
| — dont **sans cause bloquante** (capacité pleinement calculée) | 261 661 | 262 215 | **+554** |
| — dont **avec une cause** | 170 002 | 169 448 | **−554** |
| Capacité estimée (flag calibrage PLU, ≠ hauteur) | 19 850 | 19 850 | 0 |
| **SDP résiduelle totale** | **79 543 072 m²** | **84 692 001 m²** | **+5 148 929 m² (+6,5 %)** |
| Parcelles à SDP > 0 | 147 503 | 162 983 | **+15 480** |

Le flag `capacite_estimee` reste identique (19 850) : il porte l'incertitude de **calibrage de zone PLU**, pas l'ingestion de hauteur — l'injection LiDAR ne le touche pas.

---

## 2. Delta par cause

**Seules trois causes bougent** entre les deux runs ; **toutes les autres** (232 codes `zone_non_constructible:*`, `habitat_interdit:*`, `zone_non_resolue:*`, `hors_plu`, `hauteur_indispo`…) sont **strictement inchangées** — le zonage n'a pas été retouché.

| Cause | run 10 | run 11 | Δ (run 11 − run 10) |
|---|---:|---:|---:|
| `terrain_exigu` | 62 495 | 61 928 | **−567** |
| `redhibitoire` | 5 276 | 5 289 | **+13** |
| *(sans cause)* | 261 661 | 262 215 | **+554** |

**Flux réels (matrice de transition) :**
- **731 parcelles quittent `terrain_exigu`** → 716 deviennent calculables (SDP moyenne ≈ 24 m², dont 332 avec hauteur LiDAR) et 15 basculent en `redhibitoire`.
- **164 parcelles entrent en `terrain_exigu`** (depuis « sans cause »).
- **`redhibitoire` : +15 entrantes** (**toutes** venues de `terrain_exigu`), **−2 sortantes** → net +13.
- Bilan « sans cause » : +716 (ex‑exigu) +2 (ex‑redhibitoire) −164 (→ exigu) = **+554**.

### ⚠️ Réconciliation avec les chiffres du mandat (`terrain_exigu +821`, `redhibitoire −752`)

**Ces chiffres ne se reproduisent pas dans la base.** Les deltas réels (`run_seq 10` → `11`) sont d'un **ordre de grandeur plus petits et de sens contraire** :

| | Mandat (attendu) | Base (réel, run11−run10) |
|---|---:|---:|
| `terrain_exigu` | **+821** | **−567** |
| `redhibitoire` | **−752** | **+13** |

Le mandat anticipait que **déduire la SUP rétrécirait les assiettes** → **davantage** de parcelles exiguës/rédhibitoires. C'est l'inverse qui se produit, pour deux raisons cumulées :

1. **La hauteur LiDAR libère du résiduel.** Sur les parcelles bâties, la hauteur mesurée révèle souvent un bâti *plus bas* que le défaut prudent → SDP existante déduite plus faible → **plus** de SDP résiduelle → des parcelles jusqu'ici « exiguës » repassent au‑dessus du seuil (716 sortantes, SDP ~24 m²).
2. **L'assiette a *grossi*, pas rétréci** (cf. §7) : 73 447 parcelles reviennent à l'assiette `residuel_legacy` (inset uniforme, sans reculs par côté ni clip SUP), plus généreuse que le gabarit. La déduction SUP, censée dominer, est **masquée** par cette régression.

Le peu de mouvement vers `redhibitoire` (+15) confirme le sens : seules 15 parcelles déjà exiguës basculent au point de ne plus rien porter du tout.

---

## 3. Parcelles bâties dont la SDP baisse

Population « bâtie » = parcelles avec **hauteur d'égout LiDAR mesurée** (`hauteur_source = 'lidar'`) : **232 589 parcelles**.

| | Nombre |
|---|---:|
| SDP en **baisse** (run 11 < run 10) | **14 528** |
| SDP en hausse | 122 778 |
| SDP inchangée | 95 283 |
| **Médiane de la baisse** (parmi celles qui baissent) | **108 m²** |

La majorité des parcelles LiDAR **montent** (le bâti mesuré est plus bas que l'hypothèse prudente) ; une minorité baisse. Les baisses ci‑dessous combinent l'effet hauteur **et** le changement d'assiette (SUP / bascule d'assiette) — elles ne sont pas imputables à la seule hauteur.

**10 exemples (plus fortes baisses) :**

| IDU | Égout LiDAR (m) | Niveaux | SDP run 10 | SDP run 11 | Baisse (m²) |
|---|---:|---:|---:|---:|---:|
| 97416000ER0718 | 7,3 | 2 | 177 769 | 126 106 | 51 663 |
| 97422000BW3476 | 9,1 | 3 | 65 950 | 21 633 | 44 317 |
| 97416000DH1879 | 8,1 | 3 | 56 238 | 12 956 | 43 282 |
| 97410000BD0611 | 12,6 | 4 | 51 862 | 15 943 | 35 919 |
| 97411000AB0012 | 12,8 | 4 | 33 366 | 0 | 33 366 |
| 97411000DE0210 | 19,8 | 7 | 32 156 | 0 | 32 156 |
| 97409000AP0696 | 8,0 | 3 | 49 023 | 18 136 | 30 887 |
| 97411000BN0537 | 10,4 | 3 | 30 741 | 0 | 30 741 |
| 97422000BW2923 | 8,1 | 3 | 37 126 | 6 746 | 30 380 |
| 97422000BP0416 | 7,6 | 3 | 49 339 | 21 376 | 27 963 |

---

## 4. Bascules SDP nulle ↔ positive

| Transition | Nombre |
|---|---:|
| SDP **> 0 → 0** | **6 303** |
| SDP **0 → > 0** | **21 783** |
| **Net** | **+15 480** parcelles gagnent une SDP exploitable |

---

## 5. Distribution des écarts de SDP

Base = **147 503 parcelles ayant une SDP > 0 au run 10** (partition stricte, somme = 147 503) :

| Écart relatif | Nombre | Part |
|---|---:|---:|
| **\|Δ\| ≤ 10 %** (stable) | 87 851 | 59,6 % |
| **\|Δ\| 10–50 %** | 32 183 | 21,8 % |
| **\|Δ\| > 50 %** | 27 469 | 18,6 % |

Détail signé (même base) :

| Sens | Nombre |
|---|---:|
| hausse > 50 % | 18 208 |
| hausse 10–50 % | 27 927 |
| stable ±10 % | 87 851 |
| baisse 10–50 % | 4 256 |
| baisse > 50 % | 9 261 |

À part (hors base « SDP run10 > 0 ») : **21 783** parcelles passent de 0 à > 0, **6 303** de > 0 à 0 (cf. §4).

---

## 6. Dry-run des bandes q_v15 sur le run 11

### Méthode (exacte, non-écrivante)

Le Score LABUSE est déterministe : `score = min(100, round(barème_capacité(SDP) × coef_faisabilité))`. Le `coef_faisabilité` (pente, forme, accès, bâti) et le multiplicateur AU lisent des **caches identiques** dans les deux runs. J'ai **rejoué exactement la fonction de scoring en SQL** (barème `config/score_labuse.yaml`, paliers 80/200/400/1000/2000 m², seuils bandes A≥80 / B≥50 / C≥30 / D 1‑29 / 0 / NC) à partir des mêmes caches (`parcel_terrain`, `geom_2975`, `batiment_hauteur_lidar`, `parcel_au_statut`, cascade `q_v13_sources1`) en injectant la SDP et le `taux_emprise` de chaque run.

**Validation :** rejoué sur le run 10, il reproduit le q_v15 servi à **431 663 / 431 663 bandes** et **0 écart de score**. Le dry-run run 11 est donc exact (aucune approximation), pas une projection.

### Île entière

| Bande | run 10 (servi) | run 11 (dry-run) | Δ |
|---|---:|---:|---:|
| A — Excellente | 5 124 | 5 284 | **+160** |
| B — Bonne | 27 293 | 29 025 | **+1 732** |
| C — À étudier | 39 661 | 44 406 | **+4 745** |
| D — Faible | 75 425 | 84 268 | **+8 843** |
| 0 — Non retenue | 269 422 | 253 942 | **−15 480** |
| NC — Analyse incomplète | 14 738 | 14 738 | 0 |

Run 11 sort **15 480 parcelles de « Non retenue »** et les reclasse en bandes exploitables — surtout D (+8 843) et C (+4 745). L'ensemble A+B+C+D passe de 147 503 à 162 983 (= parcelles à SDP > 0). Le socle NC est **inchangé** (les causes de non-calculabilité — zone non résolue, hors PLU — n'ont pas bougé).

### Matrice de transition des bandes (run 10 → run 11)

| ↓10 \ 11→ | A | B | C | D | 0 | NC | total |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** | 5 074 | 44 | 1 | 1 | 4 | 0 | 5 124 |
| **B** | 193 | 26 075 | 651 | 81 | 293 | 0 | 27 293 |
| **C** | 4 | 2 163 | 34 589 | 1 796 | 1 109 | 0 | 39 661 |
| **D** | 1 | 303 | 6 395 | 63 829 | 4 897 | 0 | 75 425 |
| **0** | 12 | 440 | 2 770 | 18 561 | 247 639 | 0 | 269 422 |
| **NC** | 0 | 0 | 0 | 0 | 0 | 14 738 | 14 738 |

Mouvement net **vers le haut** (enrichissement), mais avec des **déclassements** non négligeables : 1 796 C→D, 1 109 C→0, 4 897 D→0, 651 B→C. La colonne « 0 » du run 11 gagne 6 303 parcelles ex‑scorées, en même temps qu'elle en cède 21 783.

### Par commune (Δ parcelles scorées A→D, tri décroissant)

| Commune | scorées 10 | scorées 11 | Δ scorées | A+B 10 | A+B 11 | Δ A+B |
|---|---:|---:|---:|---:|---:|---:|
| Le Tampon | 17 566 | 19 547 | +1 981 | 5 057 | 5 361 | +304 |
| Saint-Pierre | 12 274 | 14 204 | +1 930 | 2 164 | 2 278 | +114 |
| Saint-André | 11 695 | 13 480 | +1 785 | 2 886 | 3 322 | +436 |
| Saint-Paul | 22 366 | 23 898 | +1 532 | 4 897 | 5 135 | +238 |
| Saint-Joseph | 8 555 | 9 681 | +1 126 | 1 356 | 1 458 | +102 |
| Saint-Louis | 8 048 | 9 152 | +1 104 | 1 388 | 1 459 | +71 |
| Saint-Benoît | 12 412 | 13 387 | +975 | 3 865 | 4 029 | +164 |
| Saint-Leu | 7 101 | 7 785 | +684 | 833 | 878 | +45 |
| Sainte-Marie | 6 501 | 7 160 | +659 | 1 370 | 1 469 | +99 |
| La Possession | 6 678 | 7 262 | +584 | 1 408 | 1 516 | +108 |
| Saint-Denis | 9 408 | 9 885 | +477 | 1 762 | 1 701 | **−61** |
| Le Port | 2 953 | 3 349 | +396 | 653 | 690 | +37 |
| Sainte-Suzanne | 3 687 | 4 075 | +388 | 848 | 875 | +27 |
| L'Étang-Salé | 2 952 | 3 211 | +259 | 571 | 600 | +29 |
| Les Trois-Bassins | 1 385 | 1 622 | +237 | 223 | 240 | +17 |
| Petite-Île | 1 981 | 2 197 | +216 | 271 | 277 | +6 |
| Entre-Deux | 2 138 | 2 350 | +212 | 473 | 509 | +36 |
| Sainte-Rose | 2 053 | 2 242 | +189 | 489 | 508 | +19 |
| Les Avirons | 1 730 | 1 917 | +187 | 276 | 294 | +18 |
| Bras-Panon | 1 035 | 1 207 | +172 | 175 | 185 | +10 |
| Cilaos | 1 665 | 1 821 | +156 | 333 | 342 | +9 |
| La Plaine-des-Palmistes | 1 643 | 1 773 | +130 | 495 | 514 | +19 |
| Salazie | 1 677 | 1 778 | +101 | 624 | 669 | +45 |
| Saint-Philippe | 0 | 0 | 0 | 0 | 0 | 0 |

Les 24 communes gagnent des parcelles scorées (le LiDAR est îlien). Saint-Philippe reste à 0 (pas de PLU exploité). **Saint-Denis perd de la bande A+B (−61)** : c'est une des communes les plus touchées par la régression gabarit (§7) — l'assiette legacy y déplace des parcelles sans les faire monter.

---

## 7. Verdict : **NON servable en l'état**

### Ce qui va bien
- **Composant hauteur LiDAR sain.** Sur les 133 858 parcelles restées en assiette **gabarit** (comparaison propre, à assiette constante), la SDP croît de **+1,99 M m²** (64 789 hausses / 6 846 baisses) — cohérent avec un bâti mesuré souvent plus bas que le défaut prudent. Le socle NC est intact, les bandes s'enrichissent proprement, l'effet est îlien.

### Le bloquant
- **Régression de couverture du moteur gabarit.** L'assiette `gabarit` chute de **207 467 → 133 858 parcelles (−73 609, −35 %)**. **73 447 parcelles** basculent `gabarit → residuel_legacy`, une assiette **plus généreuse** (inset uniforme, sans reculs par côté ni clip SUP). La régression est **concentrée sur des communes entières** :

  | Commune | gabarit run 10 | gabarit run 11 | perte |
  |---|---:|---:|---:|
  | Saint-André | 15 734 | 1 115 | **−93 %** |
  | La Plaine-des-Palmistes | 3 139 | 0 | **−100 %** |
  | Les Trois-Bassins | 2 345 | 30 | **−99 %** |
  | Saint-Denis | 18 806 | 3 657 | **−80 %** |
  | Sainte-Suzanne | 6 567 | 4 423 | −33 % |
  | Sainte-Marie | 8 910 | 6 526 | −27 % |

- **Cette régression fabrique ~43 % de la hausse de SDP** — dans le mauvais sens :

  | Transition d'assiette | Parcelles | Δ SDP | Part de la hausse |
  |---|---:|---:|---:|
  | gabarit → gabarit (LiDAR/SUP pur) | 133 858 | +1 991 688 | 38,7 % |
  | **gabarit → residuel_legacy (régression)** | **73 447** | **+2 168 892** | **42,1 %** |
  | residuel_legacy → residuel_legacy (LiDAR) | 54 194 | +981 656 | 19,1 % |
  | (null) → residuel_legacy | 716 | +17 512 | 0,3 % |
  | gabarit → (null) | 162 | −10 819 | −0,2 % |

- **Conséquences :** (a) contredit frontalement l'unification GEOMETRIE-1 / RETOUCHES-1 sur *un seul moteur gabarit* ; (b) sert à Saint-André, Saint-Denis, La Plaine, Trois-Bassins une assiette **moins précise** que celle qu'ils ont *déjà* dans le run servi ; (c) **inverse le sens des deltas attendus** (§2) : la SUP censée rétrécir les assiettes est noyée sous l'élargissement legacy → `terrain_exigu` baisse au lieu de monter, à l'opposé du mandat.

### Recommandation
**Ne pas servir le run 11.** Rejouer le calcul avec la **couverture gabarit complète** (relancer le builder gabarit sur les communes tombées à zéro — Saint-André, La Plaine-des-Palmistes, Les Trois-Bassins, Saint-Denis en priorité) **puis** ré-appliquer par‑dessus l'injection hauteur LiDAR et la déduction SUP, et ré-auditer. Le composant LiDAR est validé et récupérable ; c'est l'assiette qu'il faut réparer avant toute bascule.

---

*Sources : `residuel_runs`, `parcel_residuel_runs` (run_seq 10 & 11), `score_labuse` (label `q_v15`), caches de scoring (`parcel_terrain`, `parcels.geom_2975`, `batiment_hauteur_lidar`, `parcel_au_statut`, `dryrun_cascade_results` label `q_v13_sources1`), barème `config/score_labuse.yaml`. Base `postgresql://openclaw@localhost:5432/labuse`, lecture seule. Dry-run bandes rejoué exactement en SQL et validé au bit près contre le run servi.*
