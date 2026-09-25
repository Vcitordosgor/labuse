# q_v15 recalculé sur le résiduel run 10 — distribution des bandes

Branche `audit/run10`. **Aucune bascule** : `q_v11_m137` reste le score servi ; `q_v15` est un
run **candidat**. Chaîne exécutée (autorisée par Vic, sans promote) :
`residuel-serve 10` → purge de l'ancien `q_v15` → `run_qv15.py` (Signal, 431 663 en 294 s) →
`score-labuse --run q_v15 --signal-run q_v15` (bandes, 431 663 en 228 s).

Le résiduel servi est donc **run 10 (assiette gabarit)**. Le Signal (p-run q_v15) est gelé
(sha `d8520aba`) ; seule change l'assiette lue pour le Score.

---

## ⚠️ Ce que mesure (et ne mesure pas) la comparaison au 22/09

Le dry-run du 22/09 (`SCORING-7-QV15.md`) a scoré q_v15 sur le résiduel **run 5**. Ce run-ci
score sur **run 10**. Entre les deux, **deux couches** ont changé, pas une :

1. **run 5 → run 8** : recalibrage **PLU-8** (le run servi « post-plu8-clip-2shard »), + les
   règles PLU mergées sur `main` depuis le 22/09 (PLU-CALIBRAGE-4/5, PIEGES-RISQUES-2).
2. **run 8 → run 10** : l'**assiette gabarit** — l'objet du mandat GEOMETRIE-1.

**Le delta de bandes vs 22/09 mêle donc PLU-8 et géométrie.** On les sépare plus bas
(§ attribution) : la baisse spectaculaire de la bande 0 est du **PLU-8**, pas de la géométrie.

---

## 1. Distribution des bandes — île

| bande | 22/09 (run 5) | run 10 | Δ | mot client |
|---|--:|--:|--:|---|
| **0** | 271 502 (62,9 %) | **269 087 (62,3 %)** | **−2 415** | Sans potentiel |
| A | 5 080 (1,18 %) | 5 258 (1,22 %) | +178 | Excellente |
| B | 26 837 (6,22 %) | 27 439 (6,36 %) | +602 | (haut) |
| C | 39 222 (9,09 %) | 39 647 (9,19 %) | +425 | (moyen) |
| D | 74 291 (17,21 %) | 75 494 (17,49 %) | +1 203 | (faible) |
| NC | 14 731 (3,41 %) | 14 738 (3,41 %) | +7 | Analyse incomplète |
| **total** | 431 663 | 431 663 | 0 | |

En apparence : bande 0 recule de 2 415, toutes les bandes constructibles montent. **Mais
cette amélioration est presque entièrement une commune (Saint-Benoît) et relève du PLU-8**
(cf. §2-3). NC stable (+7), les seuils de bande sont inchangés.

## 2. Distribution par commune (Δ vs 22/09)

| commune | 0 (22/09) | 0 (run10) | Δ0 | ΔA | ΔB | ΔC | ΔD | ΔNC |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Bras-Panon | 4958 | 4996 | **+38** | -1 | +1 | -5 | -33 | 0 |
| Cilaos | 4761 | 4769 | **+8** | 0 | -7 | 0 | -1 | 0 |
| Entre-Deux | 4096 | 4128 | **+32** | 0 | -30 | -27 | +25 | 0 |
| L'Étang-Salé | 6019 | 6118 | **+99** | 0 | -37 | -49 | -13 | 0 |
| La Plaine-des-Palmistes | 4781 | 4807 | **+26** | 0 | -8 | +8 | -26 | 0 |
| La Possession | 6691 | 6660 | **-31** | +4 | +2 | +20 | +5 | 0 |
| Le Port | 7384 | 7249 | **-135** | +34 | +30 | +27 | +44 | 0 |
| Le Tampon | 24584 | 25287 | **+703** | +2 | -238 | -335 | -132 | 0 |
| Les Avirons | 6754 | 6881 | **+127** | 0 | -12 | -20 | -95 | 0 |
| Les Trois-Bassins | 3947 | 3947 | **0** | +1 | +7 | -3 | -5 | 0 |
| Petite-Île | 11024 | 11069 | **+45** | +4 | +6 | -12 | -43 | 0 |
| Saint-André | 9988 | 10739 | **+751** | -33 | -289 | -382 | -47 | 0 |
| Saint-Benoît | 13953 | 9259 | **-4694** | +179 | +1512 | +1490 | +1513 | 0 |
| Saint-Denis | 28893 | 28730 | **-163** | -2 | +30 | +58 | +77 | 0 |
| Saint-Joseph | 20396 | 20431 | **+35** | +17 | +24 | -20 | -56 | 0 |
| Saint-Leu | 15586 | 15767 | **+181** | -4 | -86 | -89 | -2 | 0 |
| Saint-Louis | 21199 | 21313 | **+114** | +10 | -8 | -15 | -101 | 0 |
| Saint-Paul | 18036 | 18300 | **+264** | +4 | -88 | -168 | -12 | 0 |
| Saint-Philippe | 9 | 9 | **0** | 0 | 0 | 0 | 0 | 0 |
| Saint-Pierre | 29981 | 29949 | **-32** | +16 | +4 | +29 | -24 | +7 |
| Sainte-Marie | 10405 | 10318 | **-87** | 0 | -7 | +27 | +67 | 0 |
| Sainte-Rose | 3947 | 4175 | **+228** | -59 | -173 | -98 | +102 | 0 |
| Sainte-Suzanne | 8760 | 8837 | **+77** | +7 | -8 | -22 | -54 | 0 |
| Salazie | 5350 | 5349 | **-1** | -1 | -23 | +11 | +14 | 0 |
| **ÎLE** | 271502 | 269087 | **-2415** | +178 | +602 | +425 | +1203 | +7 |

**Saint-Benoît (−4 694) porte tout le solde île.** Sans lui, les 23 autres communes font
**+2 279 en bande 0** : la géométrie run 10 augmente légèrement la bande 0 ailleurs.

## 3. Attribution — géométrie (run 8→10) vs PLU-8 (run 5→8)

Le net des bascules SDP > 0 ↔ 0 entre **run 8 et run 10** (l'effet géométrie pur, tiré de
RUN10-VS-RUN8) recolle presque au parcel près sur le Δ bande 0 :

| commune | pertes géo | gains géo | **net géo** | **Δ0 observé** | lecture |
|---|--:|--:|--:|--:|---|
| Saint-André | 752 | 1 | **+751** | **+751** | 100 % géométrie (petits lots, recul de voie) |
| Le Tampon | 819 | 101 | **+718** | +703 | géométrie |
| Saint-Paul | 386 | 80 | **+306** | +264 | géométrie |
| Saint-Louis | 190 | 57 | **+133** | +114 | géométrie |
| Saint-Leu | 76 | 14 | **+62** | +181 | géométrie + PLU |
| Sainte-Rose | 47 | 4 | **+43** | +228 | géométrie + PLU |
| Saint-Denis | 57 | 268 | **−211** | −163 | géométrie **gagne** (grosses parcelles réparées) |
| **Saint-Benoît** | 0 | 0 | **0** | **−4 694** | **0 % géométrie — 100 % PLU-8** |

Conclusion : l'**assiette gabarit (run 10) fait *monter* la bande 0 d'environ +2 300** (petits
lots pavillonnaires vidés par le recul de voie par côté, concentrés Saint-André / Le Tampon /
Saint-Paul), sauf à Saint-Denis où elle la fait baisser (réparation des grandes parcelles que
run 8 zappait). L'amélioration nette de l'île vient d'ailleurs (PLU-8, Saint-Benoît).

## 4. Bande 0 décomposée par cause (île, 269 087)

| catégorie | n | part |
|---|--:|--:|
| **bâti saturé / assiette fermée** (calculée, SDP = 0) | 114 446 | 42,5 % |
| **zone non constructible** (`zone_non_constructible:*` + `habitat_interdit:*`) | 87 491 | 32,5 % |
| **terrain exigu** | 61 107 | 22,7 % |
| **redhibitoire** (PPR rouge / contrainte totale) | 6 041 | 2,2 % |
| autre (zone/règle non résolue résiduelle) | 2 | 0,0 % |

> **Contrôle sain** : **0 parcelle** en bande 0 avec SDP résiduelle > 0. La bande 0 est bien
> « sans potentiel » au sens strict — aucune parcelle avec des droits ne s'y retrouve par erreur.

Rappel : `zone_non_resolue` et `regle_plu_non_validee` ne tombent pas en bande 0 mais en **NC**
(14 738), catégorie distincte.

## 5. Dix parcelles en bande 0 qui paraissent douteuses

Critère : grande parcelle (> 1 200 m²) en famille de zone constructible (U/AU), passée à 0 par
la **géométrie** (`terrain_exigu` / `redhibitoire` / assiette fermée), pas par une interdiction
de zone. **Les dix étaient déjà à 0 en run 8** (`sdp8 = 0`) — run 10 ne les a pas créées ; ce
sont des zéros hérités, à tracer un jour au sol.

| idu | commune | surface | zone | cause | run 8 | run 10 | mon doute |
|---|---|--:|---|---|--:|--:|---|
| 97409000AB0523 | Saint-André | 176 624 | 1AUt | redhibitoire | 0 | 0 | 17,7 ha en 1AU tourisme entièrement bloqué : PPR/ravine total ? à vérifier |
| 97409000AB0550 | Saint-André | 161 847 | 1AUt | redhibitoire | 0 | 0 | idem, voisine |
| 97411000EH0136 | Saint-Denis | 126 650 | AUa | **terrain_exigu** | 0 | 0 | **12,7 ha « terrain exigu » = contre-intuitif** : liseré AU minuscule ou artefact d'assiette |
| 97411000DP0425 | Saint-Denis | 108 866 | Uva | redhibitoire | 0 | 0 | Uva = vocation agricole en U ? sinon 10,9 ha à regarder |
| 97412000BM1142 | Saint-Joseph | 92 169 | U3 | redhibitoire | 0 | 0 | U3 résidentiel bloqué total : contrainte à confirmer |
| 97422000BZ0133 | Le Tampon | 83 468 | Uav | (assiette fermée) | 0 | 0 | Uav vocation agricole probable → sans doute légitime |
| 97415000AD0044 | Saint-Paul | 76 789 | U1pso | redhibitoire | 0 | 0 | sous-zone spéciale (pso) : à confirmer |
| 97411000CD1083 | Saint-Denis | 74 538 | Uh | (assiette fermée) | 0 | 0 | Uh 7,5 ha assiette fermée : bâti saturé plausible, à vérifier |
| 97407000BM0011 | Le Port | 72 704 | 1AUmut | **terrain_exigu** | 0 | 0 | **7,3 ha « terrain exigu »** en 1AU mutation : à tracer |
| 97411000HL0033 | Saint-Denis | 72 452 | Uu | (assiette fermée) | 0 | 0 | Uu 7,2 ha : à vérifier |

Les plus suspectes sont les **`terrain_exigu` sur plusieurs hectares** (AUa 12,7 ha ;
1AUmut 7,3 ha) : un terrain de cette taille étiqueté « trop petit » signale soit un liseré
constructible minuscule (légitime), soit un défaut d'assiette (à tracer). Les `redhibitoire`
sur grande parcelle sont plus plausibles (contrainte totale PPR). Aucune n'est une régression
de run 10 — toutes préexistent à run 8.

## 6. Verdict de cette relecture

- La bande 0 reste solide : **0 parcelle à droits > 0 mal classée**, seuils inchangés, NC stable.
- L'effet **propre de la géométrie run 10 sur les bandes est faible et légèrement défavorable**
  (~ +2 300 en bande 0, petits lots au recul de voie), sauf Saint-Denis (favorable). C'est le
  prix de l'exactitude déjà acté au rapport RUN10-VS-RUN8.
- L'« amélioration » apparente vs 22/09 (−2 415 en bande 0) est **du PLU-8, pas de la
  géométrie** (Saint-Benoît −4 694, géométrie nulle).
- À creuser hors de cette lecture : les `terrain_exigu` multi-hectares en zone AU (2 cas ci-dessus).

**Rien de bloquant. Toujours aucune bascule — `q_v11_m137` reste servi.**
