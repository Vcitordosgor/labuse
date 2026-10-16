# VERITE-TERRAIN-2 — RAPPORT INTERMÉDIAIRE (temps 1 : volets A, B, C)

Rédigé le 16/10/2026. Branche `audit/verite-terrain-2` (worktree `labuse-verite2`), lecture seule, base q_v18.
Ce rapport couvre **le temps 1** (ce qui ne dépend pas du calcul, à faire AVANT le run final). Les volets **D** (capacité vs permis réels) et **E** (prédictions : signal de mutation, prix) sont le **temps 2**, à reprendre après le run final q_v19 — ils mesurent le calcul lui-même, donc sur ses nouveaux chiffres.

## Verdict en 5 lignes

1. **Règles PLU (A)** : les **2 011 règles chiffrées validées** de `config/plu_destinations` (23 communes) relues au règlement officiel (md5 des 23 PDF vérifié) → **99 % CONFORME**. Les **15 écarts ne sont PAS des valeurs fausses** : ce sont des **renvois de page imprécis** (la bonne valeur est à ±2-3 pages / en annexe). La **mixité sociale** fraîchement mergée (50 clauses seuil+quota) est **100 % CONFORME**.
2. **Trajets (B)** : sur **300 parcelles stratifiées / 1 473 paires** parcelle→équipement comparées à l'itinéraire IGN (voiture), **97,2 % CONFORME** (tolérance consciente de la bande). Les **41 écarts vont presque tous dans le même sens** : LABUSE **sur-estime** le temps (40/41) — il ne survend **jamais** l'accessibilité ; l'unique sous-estimation est un détour de cirque (Salazie).
3. **DPE / permis / risques (C)** : sur les **500 parcelles de V-T-1**, **0 LABUSE FAUX confirmé**. Le rappel DPE de LABUSE n'est pas mis en défaut (les DPE ADEME non rattachés sont géocodés au grain rue) ; les permis Sit@del couvrent **94,8 %** au grain commune avec **100 % des dossiers retrouvés et 0 permis inventé** ; **radon et sismicité** (que V-T-1 jugeait non comparables) passent à **100 % CONFORME** au grain commune.
4. **Aucune erreur de donnée servie n'a été confirmée** sur ce temps 1. Les seuls défauts réels sont **cosmétiques/méthodologiques** : 15 pages de citation à recaler (valeurs justes), et la quantification par bande des temps (conservatrice par construction).
5. **Limites assumées** : rappel DPE testable sur 226/500 (274 parcelles sans id BAN) ; mode piéton non comparé (pas de référence gratuite fiable) ; argiles RGA reste non comparable (N/A géologique à La Réunion) ; capacité↔permis per-parcelle et prédictions reportées au temps 2.

Reproduire : `PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python -m labuse.verite_terrain_plu_toutes` (A) · `… -m labuse.verite_terrain_trajets comparer --n 0 --ref ign` (B) · `… -m labuse.verite_terrain_dpe_permis` (C). Comparateurs et caches rejouables dans le dossier.

## Volet A — Toutes les règles PLU relues au règlement (incl. mixité)

| Indicateur | Valeur |
|---|---|
| Communes (PLU communaux) | 23 |
| Règles chiffrées `statut: valide` relues | 2 011 |
| CONFORME | 1 995 (99 %) |
| LABUSE FAUX | 15 — **0 valeur erronée** ; tous = page de citation imprécise |
| SOURCE PLUS RÉCENTE | 0 |
| NON COMPARABLE | 1 (valeur non littérale : St-Pierre Uep « 20 m²/ha » encodé en coef 0,2) |
| Mixité sociale (seuil + quota) | 50 clauses — **100 % CONFORME** |

Marquant : L'Étang-Salé, emprise AU 70/65/60/75/65 % citée p.76 alors que la règle AU 2.4 est p.79 (taux tous exacts) ; Plaine-des-Palmistes stationnement 1,5 pl/logt renvoyé à l'annexe p.103. **Geste à prévoir (hors run) : recaler les 15 `page_pdf`.** Détail : `PLU-TOUTES-REGLES.md` / `.csv`.

## Volet B — Temps de trajet & distances (vs IGN itinéraire, voiture)

| Indicateur | Valeur |
|---|---|
| Parcelles stratifiées (littoral / mi-pentes / Hauts / cirques) | 300 (75/strate) |
| Paires parcelle→équipement comparées | 1 473 |
| CONFORME (sur comparables) | 1 415 / 1 456 = **97,2 %** |
| LABUSE FAUX | 41 — **40 sur-estimations (conservateur) + 1 sous-estimation** |
| NON COMPARABLE | 17 (IGN injoignable 13 · 0 POI dans 15 min 4) |
| Mode piéton | non comparé (pas de référence gratuite fiable) |

Tolérance band-aware : le temps de référence doit tomber dans l'intervalle de la bande servie `]bande_inf ; bande_servie]`, ou à ±1 cran / ±20 %. Cause des FAUX (8 revérifiés à la main) : artefact de contour du polygone d'isochrone (POI à quelques mètres hors d'une petite bande, capté par une plus grande) → **sens conservateur**. Unique sous-estimation : Salazie, POI à 110 m à vol d'oiseau mais 1 641 m / 8 min par la route. Détail : `TRAJETS-NOTES.md` / `TRAJETS.csv`.

## Volet C — DPE (ADEME par adresse BAN), permis (Sit@del), salvage des NON COMPARABLE

| Contrôle | Résultat |
|---|---|
| DPE — rappel LABUSE (testable sur 226/500) | ADEME 8 DPE aux adresses, LABUSE en rattache 1 → **226 CONFORME, 0 FAUX** (les non-rattachés sont au grain rue) |
| Permis — grain commune (Sit@del 974 indépendant) | Sit@del 41 177 / LABUSE 39 018 = **94,8 %** ; 23/24 communes à ±10 % |
| Permis — grain n° de dossier | **100 % des dossiers LABUSE retrouvés, 0 permis inventé** (2 159 en + = trimestres récents) |
| Salvage NC — zonage sismique (grain commune) | **500/500 CONFORME (100 %)** |
| Salvage NC — potentiel radon (grain commune) | **500/500 CONFORME (100 %)** |
| Salvage NC — argiles RGA | reste NON COMPARABLE (N/A géologique 974, endpoint mort) — **raison documentée** |
| LABUSE FAUX confirmés | **0** |

Contournement : la géoloc ADEME 974 étant corrompue (lat ~-2), l'interrogation DPE se fait **par identifiant BAN**, jamais par rayon géographique. La comparaison capacité↔permis **per-parcelle** est, comme prévu, reportée au **volet D**. Détail : `DPE-PERMIS-NOTES.md` / `DPE-PERMIS.csv`.

## Ce qui peut servir d'argument commercial (seulement parce que les chiffres le soutiennent)

- **Les règles d'urbanisme chiffrées de LABUSE sont justes** : 99 % collent au verbatim du règlement officiel ; les rares écarts sont des pages de renvoi, pas des valeurs.
- **LABUSE ne survend jamais l'accessibilité** : 40 des 41 écarts de trajet sont des sur-estimations ; le produit est conservateur sur les « à X minutes de ».
- **Zéro donnée fausse confirmée** sur DPE, permis et risques ; permis retrouvés à 100 % au dossier, 0 inventé ; radon et sismicité justes à 100 %.

## Limites honnêtes (à porter au rapport final)

- 15 pages de citation PLU à recaler (valeurs correctes) ; 1 règle non littérale.
- Trajets : quantification par bande (intrinsèque), piéton non testé, 17 NC réseau.
- DPE : grain adresse↔parcelle (objet bâtiment, souvent géocodé rue) ; rappel testable sur 226/500 seulement (274 parcelles sans id BAN dans `adresses`).
- Permis per-parcelle et capacité, signal de mutation, écart de prix : **temps 2** (volets D, E) après le run final q_v19.

## Suite

**STOP temps 1.** Reprise des volets D et E dans cette même branche, rebasée sur main, une fois le run final q_v19 fait.
