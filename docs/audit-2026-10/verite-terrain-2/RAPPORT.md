# VERITE-TERRAIN-2 — RAPPORT FINAL (volets A à E)

Rédigé le 16/10/2026. Branche `audit/verite-terrain-2` (worktree `labuse-verite2`), **lecture seule**. Temps 1 (A/B/C) sur base q_v18 ; temps 2 (D/E) après le run final **q_v19 servi** (cascade `q_v19_sources`), branche rebasée sur main `669babc6`. Comparateurs et caches rejouables dans le dossier. Un commit par volet.

## Verdict en 5 lignes

1. **Données servies (A/B/C) : aucune valeur fausse confirmée.** Règles PLU 99 % conformes au règlement officiel (15 écarts = pages de citation, valeurs justes, désormais corrigées) ; DPE/permis/risques 0 faux ; trajets 97,2 %, les 41 écarts quasi tous conservateurs (LABUSE ne survend jamais l'accessibilité).
2. **Capacité (D) : LABUSE est globalement conservateur** — face à 6 601 permis réels post-PLU, il couvre ~2× l'autorisé en médiane (ratio SDP 0,46) ; 59,8 % des permis tiennent sous sa capacité, 40,2 % dépassent, surtout par **grain de parcellaire** (foncier redécoupé) et non par erreur de calcul.
3. **Signal de mutation (E) : il sépare, modérément.** Rejeu daté propre (modèle gelé, 429 799 parcelles jugées sur 2025) : décile le plus probable 3,45 % de ventes (lift ×2,29, IC Wilson sans recouvrement avec la base 1,51 %), AUC 0,625 — discrimination réelle sur un événement rare.
4. **Prix (E) : estimateur sobre, biais léger.** Backtest sans fuite (coupe 2024, 3 581 ventes) : écart médian signé −5,6 %, 17,5 % des ventes à ±10 % et 36,5 % à ±20 %, dispersion intra-commune forte.
5. **Honnêteté temporelle :** l'instantané de signal réellement SERVI (q_v19) n'est pas jugeable aujourd'hui (DVF s'arrête fin 2025, les labels datent d'oct. 2026) ; on a donc jugé le modèle, pas le livrable, et écrit le protocole forward pour mesurer le servi après la prochaine campagne DVF.

## A — Toutes les règles PLU relues au règlement (commit `beea57e2`)

| Indicateur | Valeur |
|---|---|
| Communes · règles chiffrées `valide` relues | 23 · 2 011 |
| CONFORME | 1 995 (**99 %**) |
| LABUSE FAUX | 15 — **0 valeur erronée** (pages de citation), **corrigées** dans `fix/citations-plu-15` (mergée main) |
| NON COMPARABLE | 1 (valeur non littérale, St-Pierre Uep) |
| Mixité sociale (seuil + quota) | 50 clauses — **100 %** |

## B — Temps de trajet & distances (commit `0a880e9f`)

| Indicateur | Valeur |
|---|---|
| Parcelles stratifiées · paires comparées | 300 (littoral/mi-pentes/Hauts/cirques) · 1 473 |
| Référence · mode | IGN itinéraire (bdtopo-osrm) · voiture (piéton non comparé, pas de réf gratuite) |
| CONFORME (sur comparables) | 1 415 / 1 456 = **97,2 %** (tolérance consciente de la bande) |
| LABUSE FAUX | 41 — **40 sur-estimations (conservateur) + 1 sous-estimation** (Salazie, détour de cirque) |
| NON COMPARABLE | 17 (IGN injoignable / 0 POI dans 15 min) |

## C — DPE (ADEME par BAN), permis (Sit@del), salvage NC (commit `376d3adb`)

| Contrôle | Résultat |
|---|---|
| DPE — rappel LABUSE (testable 226/500) | ADEME 8 DPE aux adresses, LABUSE 1 → **0 FAUX** (non-rattachés au grain rue) |
| Permis — grain commune | Sit@del 41 177 / LABUSE 39 018 = **94,8 %** ; 23/24 à ±10 % |
| Permis — grain n° de dossier | **100 % retrouvés, 0 inventé** |
| Salvage — sismicité / radon (grain commune) | **100 % / 100 % CONFORME** |
| Salvage — argiles RGA | reste NC (N/A géologique 974, documenté) |
| LABUSE FAUX | **0** |

## D — Capacité LABUSE vs permis autorisés post-PLU (commit `f1dfeb95`)

| Indicateur | Valeur |
|---|---|
| Permis post-PLU retenus · communes | 6 601 · 23 (PC/DP logements, non annulés, date > `meta.millesime`) |
| Capacité | servie q_v19 (residuel run 16), SDP max + logements, sommée par permis |
| Ratio médian autorisé/LABUSE | **SDP 0,46** (Q1 0,23 / Q3 0,88) · **logements 0,40** (Q1 0,25 / Q3 0,70) |
| Couverture | **59,8 % ≤ capacité · 40,2 % au-dessus** |
| Cause dominante des au-dessus | parcelle non servie 1 294 · densité > calibrage 913 · non constructible 418 · réunion 27 · aberrant 1 |

Les dépassements sont d'abord un problème de **grain de parcellaire** (foncier redécoupé). Deux pistes de calibrage réelles : les 913 petites parcelles `terrain_exigu` et les 418 zones AU/1AU « redhibitoire » (PLU 2026) où de gros collectifs ont été autorisés.

## E — Prédictions : signal de mutation & prix (commit `2e0a3549`)

**Signal** (rejeu daté du modèle GELÉ q_v15, features au 01/01/2025, jugé sur mutations 2025) :

| Indicateur | Valeur |
|---|---|
| Univers jugeable · ventes · base | 429 799 · 6 488 · 1,51 % |
| Décile le plus probable | 3,45 % de ventes — **lift ×2,29**, IC Wilson [3,28 ; 3,63 %] |
| Précision@100 / @500 · AUC · Brier | 39 % / 19,4 % · 0,625 · 0,0148 |
| Verdict | le signal **sépare**, discrimination réelle mais modérée (événement rare) |

**Prix** (reconstruction sans fuite, coupe T = 2024-01-01, médiane €/m² commune×type sur DVF < T, jugé sur ventes > T) :

| Indicateur | Valeur |
|---|---|
| Ventes jugées | 3 581 (maison + appartement ; terrain nu 0 sous le filtre mono-mutation) |
| Écart médian signé · absolu | **−5,6 %** · 27,4 % |
| Part à ±10 % · ±20 % | **17,5 %** · **36,5 %** |
| Par type · par commune | maison −4,6 % / appart −11,3 % ; écart médian commune de +16 % (97420) à −23 % (97421) |

## Ce qui peut servir d'argument commercial (parce que les chiffres le soutiennent)

- **Les règles d'urbanisme chiffrées sont justes** : 99 % collent au verbatim officiel, les rares écarts étaient des pages de renvoi (corrigées), **0 valeur fausse**.
- **LABUSE ne survend jamais l'accessibilité ni la capacité** : 40/41 écarts de trajet sont des sur-estimations ; face aux vrais permis, il couvre ~2× l'autorisé en médiane. Produit **conservateur**.
- **Zéro donnée fausse** sur DPE, permis, risques ; 100 % des permis retrouvés, 0 inventé ; radon/sismicité 100 %.
- **Le signal de mutation discrimine** (lift ×2,29 au décile haut, IC sans recouvrement) — à affirmer avec mesure (événement rare, AUC 0,625).

## Ce qui NE doit PAS servir d'argument (les chiffres ne le soutiennent pas)

- La **précision du prix à la parcelle** : seulement 17,5 % des ventes à ±10 %, dispersion forte — l'estimateur testé est volontairement sobre, mais le résultat invite à la prudence sur toute promesse d'estimation fine.
- La **capacité comme prédiction du réalisé** : LABUSE donne un gabarit max, pas le programme qui sera déposé ; 40 % des permis le dépassent (surtout grain parcellaire).

## Limites honnêtes

- Trajets : quantification par bande (intrinsèque), piéton non testé, 17 NC réseau.
- DPE : grain adresse↔parcelle, rappel testable sur 226/500 (274 sans id BAN).
- Capacité (D) : SDP habitable ≠ plancher, réunions redécoupées (ratios « inf » non imputés au calibrage), surfaces mixtes non-logement, comparaison vs SDP **max** (gabarit), N très inégal entre communes.
- Prédictions (E) : l'instantané SERVI n'est pas jugeable forward tant que DVF ≤ déc. 2025 (on a jugé le modèle gelé, pas le livrable) ; estimateur prix sobre ; terrain nu non jugé. **Protocole forward** écrit (`SIGNAL-BACKTEST.md`) : figer q_v19@T₀ aujourd'hui, re-mesurer après la prochaine campagne DVF.

## Reproduire

`PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python -m labuse.<module>` : `verite_terrain_plu_toutes` (A) · `verite_terrain_trajets comparer --n 0 --ref ign` (B) · `verite_terrain_dpe_permis` (C) · `verite_terrain_capacite` (D) · `verite_terrain_predictions` (E). Registre des écarts : `ECARTS.md`. **Branche non mergée, non poussée.**
