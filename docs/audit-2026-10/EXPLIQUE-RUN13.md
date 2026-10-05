# EXPLIQUE-RUN13 — run servi (q_v15) vs run 13 (q_v16)

**Audit lecture seule — aucun serve, aucun run, aucun merge.** Branche `audit/explique-run13`.
Base `labuse` (`postgresql://openclaw@localhost:5432/labuse`). Harnais SQL rejouable :
`scripts/audit/explique-run13/explique_run13.sql` (`PGUSER=openclaw psql -d labuse -f …`),
sortie brute `scripts/audit/explique-run13/raw_main.txt`.

## Ce qu'on compare

| | run_seq | label | calculé le | code_commit | couverture |
|---|---|---|---|---|---|
| **servi** | **10** | `q_v15 assiette gabarit` | 2026-09-25 15:18 | `babcc084` | 431 663 (île) |
| **q_v16** | **13** | `q_v16 lidar + exceptions PLU + oracle + chasse` | 2026-10-05 11:09 | `7cda6244` (= HEAD) | 431 663 (île) |

Source : `parcel_residuel_runs` (une ligne par `(run_seq, parcel_id)`). **Les deux runs couvrent les
431 663 parcelles.** La SDP ne vit que sur les parcelles **calculée** (cause vide/NULL) ; toute parcelle
à cause (`terrain_exigu`, `zone_non_constructible:*`, …) porte SDP = 0/NULL par construction.

> ⚠ Le run 13 est bien présent en base, calculé **aujourd'hui** sur le code courant. Il bundle les
> quatre jeux de correctifs mergés depuis le 25/09 (datation des commits plus bas) — exactement son
> libellé. Il n'est **pas servi** (`is_served=false` ; `q_v15`/run 10 reste servi).

**Total SDP : 79 543 072 m² (servi) → 93 530 496 m² (q_v16) = +13 987 424 m² ≈ +14 M.** (contrôle (0))

---

## (1) Matrice de transition par parcelle (famille de cause servi → q_v16)

Famille = `split_part(cause,':',1)` ; `calculee` = cause vide. **Seules 9 128 parcelles (2,1 %) changent
de famille** ; tout le reste est diagonal.

### Transitions non-diagonales (les seules qui bougent)

| servi → q_v16 | n | Δ SDP (m²) |
|---|--:|--:|
| **calculee → terrain_exigu** | **8 637** | **−1 873 818** |
| **calculee → regle_plu_non_validee** | **205** | **−241 808** |
| redhibitoire → terrain_exigu | 203 | 0 |
| terrain_exigu → regle_plu_non_validee | 77 | 0 |
| terrain_exigu → calculee | 5 | +92 |
| terrain_exigu → redhibitoire | 1 | 0 |

### Diagonale (famille inchangée)

| famille | n | Δ SDP (m²) |
|---|--:|--:|
| **calculee → calculee** | **252 819** | **+16 102 958** |
| zone_non_constructible | 82 449 | 0 |
| terrain_exigu | 62 412 | 0 |
| zone_non_resolue | 10 463 | 0 |
| redhibitoire | 5 073 | 0 |
| habitat_interdit | 5 042 | 0 |
| hors_plu | 4 244 | 0 |
| regle_plu_non_validee | 31 | 0 |
| hauteur_indispo | 2 | 0 |

Lecture : **tout le +14 M vient de la diagonale `calculee→calculee` (+16,1 M), amputée des sorties vers
`terrain_exigu` (−1,87 M) et `regle_plu_non_validee` (−0,24 M).** La famille `regle_plu_non_validee`
passe de 31 à 313 parcelles (205 depuis calculee + 77 depuis terrain_exigu) = les règles PLU déclarées
**fausses** par PLU-VERIF-1 et retirées du calcul (StJoseph `U5cvd`, StPaul `U1pru`).

### Décomposition de flux (contrôle (3a), somme exacte sur +14 M)

| flux | n | Δ SDP (m²) |
|---|--:|--:|
| **stayers** (calculée dans les deux) | 252 819 | **+16 102 958** |
| **leavers** (calculée → bloquée) | 8 842 | **−2 115 626** |
| **enterers** (bloquée → calculée) | 5 | +92 |
| **total** | | **+13 987 424** ✔ |

---

## (2) calculée → terrain_exigu (8 637 ≈ les « ~8 800 »)

`terrain_exigu` se déclenche quand **l'emprise constructible au sol < `SEUIL_EXIGU_M2` = 5 m²**
(`engine.py:20,423`) — c'est une cause d'**assiette** (le contour s'est vidé), jamais de hauteur.

### Catégorisation des 8 637 bascules

| | n | % |
|---|--:|--:|
| **pur ré-étiquetage** (SDP servi = 0 déjà) | **4 515** | 52 % |
| perte de SDP réelle (SDP servi > 0) | 4 122 | 48 % — **−1 873 818 m²** |
| bâti saturé (taux emprise > 100 %) | 3 859 | 45 % |
| bâti partiel (0–100 %) | 3 388 | 39 % |
| nu (taux emprise = 0) | 1 390 | 16 % |

**La moitié (4 515) avaient déjà SDP = 0 en servi** : la bascule ne retire aucune capacité, elle
re-nomme un « calculée sdp 0 » en « terrain_exigu » — conséquence du verdict d'assiette vide ciblé
(`fd008cd0` RECETTE-1 A1).

### Cause du basculement, remontée au commit — c'est le PPR rouge

| test (sur les 8 637) | n | % |
|---|--:|--:|
| touche une zone **PPR INTERDICTION (rouge)** | **7 994** | **93 %** |
| porte une autre SUP (hors `pm1`) | 755 | 9 % |
| **rouge OU autre-SUP (union)** | **8 636** | **99,99 %** |

Mécanisme, tracé commit par commit entre `babcc084` (run 10) et `7cda6244` (run 13) :

- **`cc995f93` RETOUCHES-1 D.15 + `e762f210`/`a3de9cac` (source SUP au catalogue)** — le moteur gabarit
  **déduit désormais la SUP de la zone d'implantation** ; le résiduel lit cette assiette. Nouveau depuis
  le run 10.
- **`d5c90ea9` ORACLE-FIX-1 Lot B** — la SUP `pm1` (enveloppe PPR) n'est retirée **que si la parcelle
  touche du rouge INTERDICTION** (`gabarit/builder.py:405`, `sl.subtype<>'pm1' OR EXISTS(ppr INTERDICTION)`).
  Règle Vic assumée : *« si la parcelle touche du rouge, on préfère 0 à une incohérence gabarit↔verdict »*,
  avec un **chantier post-déploiement documenté** : les parcelles **partiellement** en rouge devront être
  calculées sur leur portion hors-rouge.
- **`81f21e53` fix(exigu)** — les zones AU numérotées (1AU/2AU/3AU) ratent plus le clip U/AU.

**Ce ne sont donc pas des bugs** : 93 % de ces parcelles touchent une zone rouge d'interdiction, et le
moteur applique la règle « 0 plutôt qu'incohérence ». La réserve réelle (point 4 et verdict) est la
capacité des parcelles **partiellement** rouges mises à 0 — borne haute = les 4 122 leavers à SDP>0
(−1,87 M), que le chantier post-déploiement récupérera sur la portion hors-rouge.

**20 exemples tirés au sort** (`ORDER BY md5(idu||'er13seed') LIMIT 20`) — tous `terrain_exigu` en q_v16,
assiette gabarit en servi ; échantillon : `97411000EZ0279` (Saint-Denis Um, SDP 0→0, relabel),
`97418000AE0204` (Sainte-Marie UB, 536→0), `97418000AE0198` (Sainte-Marie UB, 719→0),
`97409000BD1187` (Saint-André UB, 155→0), `97407000AM0134` (Le Port Ub, 0→0), … (requête complète et
liste intégrale dans le harnais `.sql`, section (2)).

---

## (3) Les +14 M m² de SDP ventilés

### (3b) Par commune (Δ SDP, décroissant)

| commune | Δ SDP (m²) | | commune | Δ SDP (m²) |
|---|--:|---|---|--:|
| Le Tampon | +4 305 974 | | Petite-Île | +283 321 |
| Saint-Denis | +1 564 670 | | Saint-Leu | +272 376 |
| Saint-Louis | +1 403 767 | | L'Étang-Salé | +235 506 |
| Saint-Benoît | +943 318 | | La Plaine-des-Palmistes | +224 290 |
| Saint-Pierre | +761 701 | | Saint-Joseph | +199 104 |
| La Possession | +694 177 | | Salazie | +119 412 |
| Sainte-Suzanne | +541 637 | | Cilaos | +117 428 |
| Saint-Paul | +534 999 | | Les Trois-Bassins | +89 176 |
| Les Avirons | +534 698 | | Entre-Deux | +72 339 |
| Sainte-Marie | +496 143 | | Sainte-Rose | +37 104 |
| Le Port | +343 587 | | Saint-Philippe | 0 |
| Bras-Panon | +326 130 | | **Saint-André** | **−113 433** |

Saint-André est la seule commune en recul net : 864 leavers (le plus fort volume de bascules
`terrain_exigu`, zones rouges denses) l'emportent sur ses gains bâti.

### (3c) Par famille de zone

| zone_fam | Δ SDP (m²) |
|---|--:|
| **U** | **+13 743 176** (98 %) |
| AU | +375 503 |
| A | −14 748 |
| N | −116 507 |

Le +14 M est quasi exclusivement **en zone U** (le parc densifiable). A/N ≈ nuls (parcelles bloquées).

### (3d) Par cause de changement — partition exclusive, somme exacte

**Test décisif (preuve du mécanisme dominant).** La diagonale stayers +16,1 M, décomposée par état bâti :

| stayers calculée↔calculée | n | Δ SDP (m²) |
|---|--:|--:|
| **bâti partiel** (emprise 0–100 %) | 125 393 | **+9 844 028** |
| **bâti saturé** (> 100 %) | 102 201 | **+6 367 243** |
| **nu** (emprise = 0) | 25 225 | **−108 313** |

→ **Tout le gain est sur les parcelles BÂTIES** (+16,2 M), les parcelles NU sont plates (−0,1 M), et
`pct_potentiel` (part déjà bâtie) baisse sur ~205 k d'entre elles. **Le +14 M est le recalcul du BÂTI
EXISTANT, pas de l'assiette ni du gabarit.** C'est la signature de **`a32e1a5c` DONNEES-FIX-1 lot C**
(committé 7 h après le run 10) :
- **niveaux du bâti existant dérivés de l'ÉGOUT LiDAR mesuré** (`max(1, round(égout/3,0))`, calibré
  75,7 % exact / 98,3 % à ±1 sur 229 615 bâtiments) au lieu du placeholder « 1 niveau » ;
- **`coef_sdp_existante = 0,95`** (emprise toit BD TOPO → emprise plancher, `engine.py:95`).

Les deux **réduisent `sdp_existante`**, donc **augmentent `sdp_résiduelle = max(0, sdp_max − sdp_existante)`**
sur les parcelles bâties. Les parcelles nu (pas de `sdp_existante`) ne bougent pas : preuve que l'assiette
max et la hauteur de zone n'ont **pas** changé — donc **ORACLE lot B pm1 (élargit l'assiette) et lot A
AU→U n'ont quasi aucun effet sur la SDP résiduelle** (voir ci-dessous).

**Attribution finale (somme = +13 987 424) :**

| cause de changement | commit(s) | n | Δ SDP (m²) |
|---|---|--:|--:|
| **Recalcul bâti existant — hauteur LiDAR à l'égout + emprise plancher** | `a32e1a5c` | 227 594 | **+16 211 271** |
| parcelles nu (assiette/hauteur-max + exceptions PLU + pm1 : nets) | `84e29554` `d5c90ea9` | 25 225 | −108 313 |
| **→ terrain_exigu** (SUP/PPR rouge déduit de l'implantation) | `cc995f93` `d5c90ea9` `81f21e53` | 8 637 | **−1 873 818** |
| **→ regle_plu_non_validee** (PLU-VERIF règles fausses retirées) | PLU-VERIF-1 | 205 | **−241 808** |
| **enterers** (ORACLE AU→U / CHASSE au_differe) | `3e70a6b8` `0e842f75` | 5 | +92 |
| **TOTAL** | | | **+13 987 424** ✔ |

Détail des levier « nus » (net −108 313, somme sur les buckets du harnais) : **exceptions PLU appliquées**
= Bras-Panon `Ub`/`1AUb` ≥ 2 000 m² (majoration hauteur R+1→R+2, `plu_exceptions_effet.json`, 4 entrées
`applique`), mesuré **+220 192 m²** sur 1 925 parcelles — c'est le seul effet « exceptions PLU » chiffrable
(témoin PLU-CALIBRAGE-5). ORACLE pm1 (182 527 parcelles touchées par la SUP pm1, 42 % de l'île)
n'agit sur le résiduel qu'au travers de la règle rouge ci-dessus ; son effet « enveloppe du score » est
un correctif d'affichage (S10), hors SDP résiduelle.

> **Note de méthode.** `parcel_residuel_runs` ne stocke que `sdp_résiduelle`, `taux_emprise_pct`,
> `pct_potentiel` — pas `sdp_max` ni les niveaux. On ne peut donc pas *additionner* séparément « part
> hauteur » et « part emprise » (le même correctif LiDAR change les deux : emprise plancher ×0,95 **et**
> niveaux). Le test bâti/nu ci-dessus **isole** la cause dominante sans ambiguïté ; le bucket « EMPRISE »
> du harnais (`taux_emprise_pct` bougé) est un **co-symptôme** du recalcul bâti, pas l'assiette gabarit.

---

## (4) Les 30 témoins SCORING-5 — SDP servi (run 10) vs q_v16 (run 13)

`reports/scoring-5/TEMOINS.csv`. (La colonne SDP du CSV datait du run 2 / août ; ici on compare bien
**servi = run 10** vs **q_v16 = run 13**.) **24/30 varient de ≤ 30 % (dont 16 à ±1 %)**. Les 6 écarts > 30 % :

| idu | commune / zone | servi → q_v16 | Δ | explication |
|---|---|---|--:|---|
| `97406000AM0664` | Plaine / AUc | 23 → 79 | +243 % | bâti : `pct_potentiel` 98→93 (LiDAR, petit absolu +56 m²) |
| `97401000AI0166` | Avirons / AUd | 1 794 → 2 858 | +59 % | bâti : emprise & potentiel baissent (LiDAR + 0,95) |
| `97402000AH1389` | **Bras-Panon / Ub** | 4 932 → 7 652 | +55 % | **exceptions PLU** (Ub ≥ 2 000 m², R+1→R+2) |
| `97406000AV0888` | Plaine / AUs1 | 102 → 171 | +68 % | bâti (LiDAR) |
| `97401000AL0505` | Avirons / Uc | 0 → 87 | (de 0) | bâti sur-saturé recalculé (te 167→59 %) |
| `97404000AX0047` | **L'Étang-Salé / UA** | 2 694 → 1 213 | **−55 %** | **PPR rouge** : pm1 (1 124 m²) déduit, touche du rouge |
| `97409000AY0786` | **Saint-André / UC** | 2 243 → **0 (terrain_exigu)** | **−100 %** | **PPR rouge** : pm1 (4 732 m²) déduit, touche du rouge |

Les deux reculs (`AX0047`, `AY0786`) sont des **parcelles touchant une zone PPR INTERDICTION** : le moteur
applique la règle « 0 plutôt qu'incohérence » (§2). Leur étiquette « bonne » dans `TEMOINS.csv` **précède**
la déduction de l'enveloppe PPR du résiduel — ce sont des **témoins périmés**, pas une erreur du moteur. Les
28 autres sont cohérents (gains bâti LiDAR, exception PLU Bras-Panon, ou inchangés). Deux témoins restent
`terrain_exigu` dans les deux runs (`97413000CU0703`, `97411000BN0496`) et deux `non_calculable zone non
résolue` inchangés (`97415000AC0070/0109`).

---

## Verdict

**Servable — le +14 M est intégralement expliqué et dominé par un correctif légitime (hauteur LiDAR à
l'égout, DONNEES-FIX-1 lot C) ; à corriger avant bascule : les parcelles PARTIELLEMENT en PPR rouge mises
à 0 par la règle « 0 plutôt qu'incohérence » (chantier post-déploiement déjà identifié, borne ≤ 4 122
parcelles / −1,87 M) et la ré-constitution des 30 témoins (2 « bonnes » périmées car antérieures à la
déduction de l'enveloppe PPR).**
