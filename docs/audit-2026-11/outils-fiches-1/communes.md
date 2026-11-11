# Communes

Clé interne : `communes` (num O6) · composant : `frontend/src/components/outils/Communes.tsx` · endpoints : `/communes`, `/communes/status`, `/communes/{commune}/contexte`, `/comparateur-communes`, `/communes/{commune}/acquisitions-pm`, `/moteurs/barometre`, `/moteurs/marche/{commune}`, `/moteurs/zan`, `/pipeline-rarete`

> **Note sur les « 5 chemins » du mandat.** Le briefing nomme Marché · Comparateur · Vélocité · Rareté · Évolution (+ Baromètre/`barometre`/M18). À l'écran, l'outil a été **restructuré** (`Communes.tsx` lignes 13-24) en **quatre portes** : *Comparaison communes*, *Évolution du marché* (= l'ex-Baromètre M18), *Marché des annonces (Radar)*, *Acquisitions récentes*. Les notions *Marché local*, *Vélocité* et *Rareté/ZAN* ne sont plus des onglets propres : elles ont été **transférées dans la fiche commune du Contexte** (`ContextePanel`, servie par `/communes/{commune}/contexte`) et dans des **colonnes** du comparateur. J'ai donc structuré la fiche par **chemin fonctionnel** (Comparateur, Évolution/Baromètre, Marché, Vélocité, Rareté/ZAN, Acquisitions), en disant pour chacun où il vit aujourd'hui.

---

## 1. À quoi il sert, et pour qui

Outil de reconnaissance territoriale pour un opérateur (promoteur, marchand de biens, investisseur) qui veut comparer les 24 communes de La Réunion avant de choisir où prospecter : prix, permis, délais d'instruction, pression ZAN, stock d'opportunités, et suivre l'évolution trimestrielle du marché. Il n'évalue aucune parcelle : il agrège des indicateurs **déjà en base** à la maille commune (« zéro donnée nouvelle »), chacun étiqueté *Sourcé* ou *Estimé*.

## 2. Le parcours

L'écran d'entrée affiche **quatre portes** (`Communes.tsx` 248-265). Chacune ouvre une section plein écran (overlay `absolute inset-0 z-40`) ou une sous-vue :

- **Comparaison communes** (`CommunesTablePanel`, 282-335) → tableau des 24 communes, une ligne par commune, 6 colonnes triables au clic sur l'en-tête (`O6Comparateur`, `blocB.tsx` 213). Cliquer une ligne ouvre la **fiche commune** (panneau droit `ContextePanel`, où vivent Marché/Vélocité/ZAN). Bouton « Légende » replié (308-321).
- **Évolution du marché : ventes et permis** (`EvolutionTablePanel`, 372-396) → le moteur **M18** (`moteurs.tsx` 637) : un tableau trimestriel (Ancien €/m² · Terrain €/m² · Permis), un sélecteur de périmètre (île entière ou une commune), le prix VEFA en référence.
- **Marché des annonces (Radar)** (`RadarTablePanel`, 341-367) → la table Radar par commune (`RadarMarche`), source distincte (annonces relevées à la main). *Hors périmètre de cette fiche — couvert par la fiche « Radar ».*
- **Acquisitions récentes** (`AcquisitionsRecentes`, 72-208) → sélecteur de commune + listing des changements de propriétaire **personne morale** (DGFiP), groupés par acquéreur (SIREN), filtrables par millésime d'arrivée, « Voir plus » par 200 ; clic sur une parcelle → sa fiche ; « Scan patrimoine → » vers l'outil Patrimoine.

L'utilisateur ne saisit presque rien : il clique une porte, trie des colonnes, choisit une commune dans un menu. Aucun formulaire de calcul.

## 3. Les données lues

Noms de catalogue (`/tmp/sources_catalog.tsv`), tables SQL réellement interrogées (code lu), millésime/cadence tels qu'en base (`data_sources`) :

| Chemin | Source (catalogue) | Table SQL lue | Millésime servi | Cadence |
|---|---|---|---|---|
| Comparateur / stock | *(run de scoring LABUSE servi)* | `parcel_p_score_v2` (run_id) | run servi (q_v…) | ~nocturne |
| Comparateur / vélocité | SITADEL (délais dérivés m10) | `m10_permit_delais` (valide, famille='logements') | dérivé SITADEL | — |
| Comparateur / permis · Évolution / permis | Sit@del (permis de construire) | `sitadel_permits` | **2026-08** | **mensuelle** |
| Comparateur / déficit SRU | Inventaire SRU (DHUP) | `commune_contexte_sru` | inventaire LLS 01/01/2024 · prélèvement 2025 | — (annuel) |
| Comparateur·Rareté·ZAN / pression | Consommation d'espaces NAF (Cerema) | `commune_conso_enaf` | conso ENAF **2021-2024** (publié 12/05/2025) | — (pluriannuel) |
| Comparateur·Évolution·Marché / prix ancien & neuf, terrain nu | DVF / valeurs foncières ; DVF terrain | `dvf_mutations`, `dvf_mutations_parcelle`, `dvf_prix_sortie_neuf` | géo-DVF Etalab **2026-S1** | **semestrielle** |
| Marché / annonces (Radar) | Radar LABUSE (pige) | `pige_biens`, `pige_annonces` | collecte humaine (dernière 29/10/2026) | manuelle |
| Marché / loyer | Loyers DHUP (carte des loyers) | via `build_marche_commune` | carte 2025 | annuelle |
| Marché logement / vacance, typologie | INSEE RP (recensement) | via `marche` du contexte | **RP 2023** (publié 25/06/2026) | annuelle |
| ZAN officiel (OCS GE) | OCS GE / portail artificialisation (IGN) | `parcel_ocsge` | diff artif 2017→2022 | pluriannuelle |
| Acquisitions | DGFiP — parcelles des personnes morales | `parcelle_personne_morale` (via `acquisitions_recentes`) | **panel 2019→2025** (1ᵉʳ janvier) | **annuelle** |

## 4. Les calculs

### 4a. Comparateur — composite « où investir »
Moteur `src/labuse/registre/moteurs/commune.py`. Indicateurs bruts (une requête, `_SQL_INDICATEURS` l.27-57), tous *Sourcé* :
- **stock** = nb parcelles `tier ∈ (brulante, chaude, priorite, a_suivre)` du run servi (l.29-32).
- **vélocité** = médiane (`percentile_cont(0.5)`) du `delai_mois` dépôt→autorisation des permis logements (`m10_permit_delais`, l.33-35), arrondie 0,1 (`comparateur.py` l.199-200).
- **permis** = nombre de `sitadel_permits` sur **5 ans glissants** (`CURRENT_DATE - INTERVAL '5 years'`, l.36-38).
- **déficit SRU** = `greatest(objectif_pct − taux_lls, 0)` (l.39), arrondi 0,1.
- **pression ZAN** = `conso_2021_2024_m2 / 10000` en ha (l.40), arrondie 0,1.
- **prix_neuf** = médiane VEFA live `neuf_vefa_commune`, servie seulement si `n ≥ seuil` (seuil=8, `comparateur.py` l.60-63) sinon `null`.
- **prix_ancien** (colonne, pas un axe) = `prix_ancien_communes` : médiane DVF `valeur_fonciere / surface_reelle_bati` des **ventes strictes** (`_BAROMETRE_RETENUE`), `HAVING count ≥ 100` (`moteurs.py` 804-817).
- **prix_terrain_nu** = médiane DVF terrain nu par zone PLU (U sinon AU, `ligne2_terrain_zone`), seuil cellule 10 ventes (`comparateur.py` 64-79).

**Composite** (`composite_communes`, l.66-97) : chaque axe normalisé **min-max [0-100]** sur les 24 communes selon sa direction (`+1` haut=mieux, `−1` bas=mieux) ; score = **moyenne pondérée des axes présents**, poids renormalisés sur les axes non nuls (`present_w`, l.91-93). Un axe manquant reste `null` (jamais 0) et sort du calcul. Borne dégénérée (min=max) → 50 neutre (l.82). Poids par défaut (réglables via query `w_*`) : stock 0,30 · vélocité 0,15 · permis 0,15 · déficit_sru 0,15 · pression_zan 0,10 · prix_neuf 0,15 (`comparateur.py` 222-224 ; mêmes valeurs dans `INDICATEURS` l.18-25). **« Composite de COMMODITÉ, non calibré »** (méthode servie telle quelle).

### 4b. Évolution / Baromètre (M18)
`_barometre_data` (`moteurs.py` 848-1025). **Ventes strictes** `_BAROMETRE_RETENUE` (l.799-801) : `nature='Vente'` ET `valeur_fonciere>1000` ET `€/m² ∈ [100, 12 000]` (écarte VEFA, prix symboliques, ratios aberrants). Axe de trimestres commun (`axis_min` = 8ᵉ trimestre récent ayant une vraie vente, l.902-915). Médiane €/m² bâti par trimestre (DVF), médiane €/m² terrain nu (dédupliquée par mutation, l.945-960), permis/trimestre (SITADEL). **Tendance %** = dernier trimestre complet vs même trimestre un an avant (glissement annuel, `_tendance_pct` 837-845). Trimestre **partiel** marqué si volume < 60 % de la médiane des 4 précédents (`_marque_partiel` 820-834, grisé, hors tendance). Neuf servi en **référence** (pas de série : VEFA trop rare), `null` sous le seuil de 8 ventes.

### 4c. Marché commune
`build_marche_commune` (lu via `/moteurs/marche/{commune}`) + `marche_annonces` (`fiche_commune.py` 38-78). **Écart demandé/acté** = `100 × (prix_demandé_Radar − prix_acté_DVF) / prix_acté`, affiché **seulement si** demande ET biens ≥ `SEUIL_N` (=5) (l.59-61) ; sinon masqué. Loyer = ligne du bloc marché (DHUP).

### 4d. Rareté / ZAN (Estimé)
`rarete.py` : `rythme = conso_2021_2024 / 3` (ha/an, Sourcé) ; `budget = 0,5 × conso_2011_2021` (**interprétation −50 % loi TRACE, Estimé**, l.8) ; `reste = budget − conso_2021_2024` ; `horizon = reste / rythme` années (l.54-62, `None` si rythme nul, `0` si dépassé). Statut : dépassé / non projetable / tension forte (≤5 ans) / modérée (≤15) / détendu (l.86-89). `pct_budget_consomme = 100 × (budget − reste) / budget`. `_zan_indicateur` (`moteurs.py` 648-706) ajoute rythmes annualisés et trajectoire « sous / au-dessus de la cible ». **Caveat servi partout** (rythme supposé constant, enveloppe = interprétation, épuisement ≠ interdiction).

### 4e. Acquisitions
`acquisitions_recentes` (`proprietaire_historique`) : changements de SIREN propriétaire d'un **millésime DGFiP** au suivant depuis 2022. Aucun calcul de prix — **constat**, pas une vente, hors scoring (note l.2959).

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé / Estimé |
|---|---|---|
| **Comparateur — Instruction (mois)** | médiane `m10_permit_delais.delai_mois` (SITADEL) | Sourcé |
| **Permis (5 ans)** | count `sitadel_permits` 5 ans glissants | Sourcé |
| **Déficit SRU (pts)** | `commune_contexte_sru` objectif−taux | Sourcé (DHUP) |
| **€/m² ancien** | médiane DVF ventes strictes commune entière (`prix_ancien_communes`, n≥100) | Sourcé |
| **€/m² VEFA** | médiane DVF VEFA live (`neuf_vefa_commune`, n≥8 sinon « — ») | Sourcé |
| **€/m² terrain nu** | médiane DVF terrain nu par zone U/AU (n≥10 sinon « — ») | Sourcé |
| **Score composite / rang** | moyenne pondérée min-max des axes | **Estimé** (commodité non calibrée) |
| **Évolution — Ancien/Terrain €/m², Permis (n) par trimestre** | DVF + SITADEL trimestriels | Sourcé |
| **Tendance /an (perimetre, interne)** | glissement annuel médianes | Sourcé (dérivé) |
| **Neuf : ~N €/m²** | référence VEFA live | Sourcé (sinon « — ») |
| **Marché — écart demandé/acté %** | (Radar demandé − DVF acté) / acté, si ≥5 biens | Sourcé (dérivé de 2 sources) |
| **Marché — loyer €/m²** | carte des loyers DHUP | Sourcé |
| **ZAN — conso 2011-21 / 2021-24 (ha), part habitat %** | `commune_conso_enaf` (Cerema) | Sourcé |
| **ZAN — budget / reste / horizon / % consommé / trajectoire** | dérivés règle −50 % | **Estimé** |
| **ZAN — OCS GE part artif %** | `parcel_ocsge` (IGN) | Sourcé |
| **Rareté — stock opportunités (ha)** | run servi | Sourcé |
| **Acquisitions — N changements, acquéreur avant→après** | millésimes DGFiP PM | Sourcé (constat, pas une vente) |

**Part Sourcé / Estimé :** l'immense majorité des chiffres sont **Sourcés** (DVF, SITADEL, Cerema, DHUP, DGFiP). Deux familles sont **Estimées** et clairement étiquetées : le **score composite/rang** du comparateur (normalisation non calibrée) et tout le volet **budget/reste/horizon ZAN** (règle −50 %). Estimation : ~80-85 % Sourcé, ~15-20 % Estimé.

## 6. Les limites

- **Score composite non calibré** : un rang « 1 » n'est pas un rendement — c'est une somme pondérée arbitraire d'axes hétérogènes normalisés sur 24 valeurs. Changer les poids change le classement.
- **Budget/horizon ZAN = interprétation** : la règle −50 % n'est pas la trajectoire légale territorialisée ; « % restant » n'est pas un droit à construire. Un horizon de « 1,1 an » (Saint-Denis) peut alarmer à tort (densification hors ENAF possible).
- **Prix VEFA / terrain nu « — »** fréquents sous seuil : Saint-André VEFA `null` (1 seule vente). L'absence n'est pas « pas de neuf », c'est « pas assez de ventes ».
- **Radar très mince** (collecte humaine, en pause) : l'écart demandé/acté repose sur peu d'annonces ; masqué sous 5 biens mais fragile au-dessus.
- **Acquisitions = personnes morales uniquement** (DGFiP ne publie pas les particuliers) et **constat de millésime**, pas une vente : un acquéreur apparent peut être une fusion/réorganisation, pas un achat.
- **Vélocité** dépend de `m10_permit_delais` dérivé de SITADEL : les permis récents sans décision finale ne comptent pas (survie seulement des `delai_mois ≥ 0`).

## 7. Les tests

- `frontend/src/components/outils/CommunesTable.test.tsx` (26-75) garantit : en-têtes honnêtes (« Instruction (mois) », « Permis (5 ans) » pas « 12 m »), « Fiche → » permanent vert sur chaque ligne, colonne « stock » retirée, meilleure valeur (instruction min) en vert, prix neutres (pas de faux signal bon/mauvais). **Ne teste pas** les valeurs calculées (fetch mocké) ni le tri/null-en-bas.
- `tests/test_comparateur.py` : directions (stock haut=mieux, vélocité bas=mieux), axe manquant → null + renormalisation, rang, borne dégénérée → 50, et `test_compute_24_communes_et_composite` sur la base.
- `tests/test_rarete.py` : horizon normal / rythme nul / budget dépassé / reste absent, présence du caveat, table absente → vide.
- `tests/test_barometre.py` : marquage partiel, tendance glissement annuel, non-levée, permis alignés sur la fenêtre DVF, **source unique prix ancien PDF vs comparateur** (73-100), commune inconnue → 400.
- **Aucun test ne vérifie** : l'onglet Acquisitions (front ni back), la cohérence des millésimes servis, que l'écart demandé/acté du Marché soit robuste, ni le pipeline ZAN officiel OCS GE.

## 8. Les documents liés (PDF, exports)

**Aucun export PDF n'existe pour cet outil.** L'export PDF du Baromètre a été **retiré** (décision produit, `moteurs.py` 1043-1046 : route `/barometre.pdf` et son générateur supprimés). Le seul pont cross-document est interne : le **« €/m² ancien »** du tableau Communes et celui qui alimenterait un rapport commune lisent **la même fonction** `prix_ancien_communes` (`moteurs.py` 804, vérifié par `test_prix_ancien_source_unique_pdf_vs_comparateur`) — donc pas de divergence de source. Les onglets ne produisent que de l'affichage écran.

## 9. Trois cas rejoués

Témoins adaptés : `97411000BZ1065`→**Saint-Denis**, `97409000AK0804`→**Saint-André**, `97415000DH0076`→**Saint-Paul** (le brief l'annonçait « Saint-Pierre/Joseph sud » mais `psql` résout `97415 = Saint-Paul`, la commune de référence « gold »). Sorties `curl` réelles (`127.0.0.1:7300`) :

**`/comparateur-communes`**
- Saint-Denis : rang 2, score 49,9 ; stock 196 · vélocité 9,0 (n=1975) · permis 1242 · déficit SRU 0,0 (conforme) · pression_zan 82,4 · €/m² ancien 2493 (n=8171) · VEFA 4878 · terrain nu 482 (zone U).
- Saint-André : rang 22, score 24,7 ; stock 18 · vélocité 9,0 · permis 758 · déficit SRU 0,0 · pression_zan 21,6 · ancien 1954 (n=979) · VEFA **null** (n=1, sous seuil) · terrain nu 264 (U).
- Saint-Paul : rang 3, score 47,0 ; stock 122 · vélocité 9,0 · permis 1922 · déficit SRU 6,7 (déficitaire) · pression_zan 90,0 · ancien 4297 (n=3388) · VEFA 4745 · terrain nu 479 (U).

**`/moteurs/barometre?insee=97411` (Saint-Denis)** : perimetre « Saint-Denis (DVF communal, Sitadel) » ; tendances ancien +3 %, terrain +44 %, permis +7 % ; neuf 4878 €/m² (n=355) ; dernier trimestre 2026T2 (183 ventes, 2872 €/m², **partiel**) ; écartées 468 (VEFA 357, autres 59, symboliques 1, ratio 51).

**`/pipeline-rarete`** : Saint-Denis horizon **1,1 an** (rythme 27,5 ha/an, budget 113,1, reste 30,7, 73 % consommé, tension forte, stock 52,6 ha) ; Saint-André 3,3 ans (7,2 / 45,5 / 23,9 / 48 %) ; Saint-Paul 4,2 ans (30,0 / 217,5 / 127,5 / 41 %).

**`/communes/Saint-André/acquisitions-pm?limit=5`** : insee 97409, depuis 2022, **213 changements** (5 chargés, tronqué). 1ʳᵉ : `97409000AB0966` 2024→2025, « SUCCESSION M ET MME ROBERT HONORAT » (U14250561) → « KT PLAZA » (891450264). Source « DGFiP — parcelles des personnes morales ».

**`/moteurs/marche/Saint-Denis`** : terrain nu U 482 €/m² (n=1254), AU 328 (n=35) ; prix sortie neuf 4275 €/m² (n=77) ; tendance 12 m +1,3 % « stable ». **`/communes/Saint-Denis/contexte`** (bloc `marche_annonces`) : 36 biens Radar, écart demandé/acté **+22,7 %** (demande 3060 vs acté 2493), dernière collecte 2026-10-29.

## 10. Tes doutes (par gravité)

1. **Le score composite peut induire une décision d'achat fausse.** « Rang 1 » est présenté comme « où investir » mais c'est une moyenne pondérée *non calibrée* d'axes incommensurables (un €/m² VEFA normalisé compte autant qu'un délai d'instruction). Les poids par défaut (stock 30 %) pèsent lourd et sont invisibles à l'écran. L'avertissement est servi, mais le mot « où investir » reste dans l'esprit de l'outil (`comparateur.py` docstring l.1).

2. **Horizon ZAN « 1,1 an » (Saint-Denis) est un chiffre alarmant bâti sur une règle −50 % qui n'est pas la loi.** Un utilisateur non averti lira « plus d'un an avant blocage ». Le caveat est servi mais le chiffre est très saillant (statut « tension forte »).

3. **Backend intermittent pendant l'audit.** Le serveur 7300 était par moments injoignable (« connection refused ») car saturé par une autre session (requêtes tuiles). Toutes mes sorties ci-dessus sont réelles, mais obtenues par relances ; un utilisateur réel pourrait voir des erreurs de chargement aux mêmes moments.

4. **Deux prix « neuf » coexistent** : le comparateur/baromètre sert **VEFA live** (Saint-Denis 4878, n=355) tandis que `/moteurs/marche` sert `dvf_prix_sortie_neuf` **4275** (n=77) sous le libellé « prix sortie neuf ». Mêmes mots, deux chiffres (~600 € d'écart) selon l'écran — risque de confusion non testé.

5. **Acquisitions non testées et potentiellement trompeuses** : aucun test front/back ; le libellé « Acquisitions récentes » sur un simple changement de millésime DGFiP (y compris successions, fusions) peut se lire comme « ventes récentes » malgré la mention — et l'effectif réel (213 à Saint-André) n'est paginable que par le front.

---

### Synthèse INDEX

Fiche écrite : `docs/audit-2026-11/outils-fiches-1/communes.md`. L'outil Communes (clé `communes`, O6) est une **fusion de 4 portes** (Comparaison 24 communes · Évolution/Baromètre M18 · Marché Radar · Acquisitions PM), les notions Marché/Vélocité/Rareté-ZAN ayant migré dans la **fiche commune du Contexte** et des colonnes. **Données** : DVF (`dvf_mutations`, 2026-S1) pour prix ancien/neuf/terrain et séries trimestrielles ; SITADEL (`sitadel_permits` 2026-08, `m10_permit_delais`) pour permis 5 ans et délais d'instruction ; Cerema ENAF (`commune_conso_enaf` 2021-2024) pour la pression/horizon ZAN ; DHUP (`commune_contexte_sru`, loyers) ; OCS GE IGN (`parcel_ocsge`) ; DGFiP PM (`parcelle_personne_morale`) pour les acquisitions ; run de scoring servi (`parcel_p_score_v2`) pour le stock. **Sourcé vs estimé** : ~80-85 % sourcé (les valeurs brutes), ~15-20 % estimé et dûment étiqueté — le **score composite/rang** du comparateur (normalisation min-max non calibrée) et tout le **budget/reste/horizon ZAN** (règle −50 % loi TRACE). Aucun PDF (export baromètre retiré) ; pont de cohérence `prix_ancien_communes` vérifié par test. Cas rejoués réels : comparateur St-Denis rang 2 / St-André rang 22 / St-Paul rang 3 ; horizon ZAN St-Denis 1,1 an ; 213 acquisitions PM à St-André. **Doute le plus grave** : le score « où investir » et l'horizon ZAN de 1 an sont des **estimations non calibrées présentées comme des verdicts**, susceptibles d'orienter une décision d'achat à tort malgré les avertissements servis.
