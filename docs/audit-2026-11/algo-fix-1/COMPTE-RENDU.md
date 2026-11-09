# ALGO-FIX-1 — compte rendu

**Mandat** ALGO-FIX-1 — l'Analyse LABUSE par scénario, honnête sur l'inconnu.
**Branche** `fix/algo-fix-1` (worktree `~/Desktop/labuse-algofix`). **Aucun merge, aucun accès
production, aucune modification du run servi.** Calcul et API seulement ; aucun fichier du front
touché. Instantané de travail : run servi **`q_v20`** (base locale, 433 229 parcelles).

Références normatives : `docs/audit-2026-11/algo-fix-1/LABUSE_DOSSIER_V2/01_SPECIFICATION_ALGORITHME.md`
(§4, 5, 7, 8, 9, 10, 12, 13.2) et les **décisions de Vic D1–D10** du mandat (qui prévalent sur la
spécification là où elles diffèrent). État de l'existant : `docs/audit-2026-11/algo-lecture-1/ALGO.md`.

---

## 0. Suite ALGO-FIX-1 (2ᵉ passe)

Cinq ajouts de la 2ᵉ passe, sur la même branche :

1. **D4 complet.** La sensibilité d'une bande à une inconnue vaut désormais pour les **trois**
   facteurs physiques — pente, **forme** et **accès** —, pas seulement la pente : si la bande
   change en remplaçant un facteur inconnu par sa pire valeur de configuration → **À vérifier**,
   bande provisoire au détail (`scenarios_v2._inconnues_physiques`).
   **Distinction accès « non identifié » vs « inconnu » : tranchée par les données.** Dans le run
   servi, **chaque** parcelle porte un verdict de cascade `acces` (POSITIVE 366 506 / PASS 66 723,
   **zéro parcelle sans verdict**). « Non identifié » (PASS) est donc un fait **mesuré** (malus
   connu 0,85), pas une inconnue ; l'ensemble « inconnu » (aucun verdict) est **vide aujourd'hui**.
   Le moteur porte néanmoins un drapeau `access_known` : si une couche d'accès partielle apparaît
   un jour, l'accès inconnu suivra la règle de la pente sans changement de code.

2. **Persistance par le calcul du run.** Les scénarios (statut, cause, bande, score, **C, E,
   C_rebuild, D_net**, R, portion productive, vigilances) sont **écrits** dans une table de run
   dédiée `parcel_scenario_v2_runs` (additive, aucune table historique touchée) par
   `scenarios_v2_persist.compute_scenarios_v2_batch`. **L'endpoint LIT** cette table
   (`analyse_payload_persiste`) — il ne calcule plus à la volée (sauf trappe `enrich=1` ≤ 500
   parcelles). Le Signal reste relayé depuis `score_labuse` à la lecture (jamais stocké ni
   recalculé).

3. **Avant/après sur toute l'île**, par commune et par scénario, lu de la table de run (§5 et
   `AVANT-APRES.md`) : répartition des bandes V1 et des statuts V2 (conservation sur 433 k ;
   reconstruction chiffrée sur Entre-Deux + Saint-Denis), **top 20 des changements de bande avec la
   raison**.

4. **Les deux cas réels de Saint-Denis** (§6-bis) : `97411000EH0043` (22,7 ha) et `97411000EI0085`
   sont des parcelles **à cheval** dont la capacité servie « Bonne » vient d'une **portion
   minoritaire U/AU**. La V2 l'**expose** (D9) et **corrige** le cas faux.

5. Tests, hook et compte-rendu mis à jour.

---

## 1. Résumé — avant / après (tête du compte-rendu)

La V2 **ne remplace pas** la note 0–100 par une autre note : elle la double par des **statuts de
scénario** (exclusifs, avec leur cause), des **quantités nommées** (R ; ou C_rebuild, E, D_net
signé), des **bandes qui décrivent UN scénario** (barème actuel × pente × forme × accès, **sans le
coefficient bâti, sans le ×0,5 AU**), et le **Signal relayé tel quel**. Elle se calcule **en
parallèle** du service ; rien n'est basculé.

Sur **Entre-Deux** (6 341 parcelles, q_v20), là où la V1 sert une **bande unique** (dont **3 789 =
59,8 % en « 0 — Non retenue »**, muette), la V2 **conservation** nomme ce que « 0 » cachait :

| V1 (bande servie) | V2 — conservation (bâti conservé) |
|---|---|
| **0** (Non retenue) : 3 789 | **Hors de ce projet** (preuve zone A/N, Parc, cascade dure) : 3 054 |
| D : 1 229 · C : 626 · B : 464 · A : 35 | **Aucun ajout identifié** (saturé/capacité nulle) : 814 |
| HC (hors classement) : 194 | **Analyse à compléter** (dont diagnostic `terrain_exigu`) : 142 |
| NC : 4 | **Capacité estimée** (bande A/B/C/D nommée) : 2 331 |

Et en **reconstruction** (calculée pour toutes les parcelles), **2 881 (45,4 %)** obtiennent une
**Capacité estimée** — soit **+550 par rapport à la conservation** : ce sont les parcelles saturées
que la V1 déclarait mortes et que le remplacement rend lisibles, avec leur **gain net signé**
(souvent négatif — la démolition perd de la SDP, et c'est dit, pas écrasé à 0). **577 parcelles**
changent ainsi de verdict.

Le détail complet (répartitions, croisement bande V1 → statut V2, reconstruction, liste des
parcelles qui changent) est dans **`AVANT-APRES.md`** (généré par `scripts/algofix1_avant_apres.py`).

Quatre bascules concrètes, vérifiées sur parcelles réelles (test `test_algofix1_protections.py`) :

| IDU | V1 | V2 | Ce que ça corrige |
|---|---|---|---|
| `97403000AP1634` (emprise 158 %, saturée) | **0** muette | reconstruction **Capacité estimée**, bande C, **D_net = −9 m²** signé | D2 : la reconstruction est calculée pour les saturées, gain net signé |
| `97403000AL0258` (11,4 ha, `terrain_exigu`) | **0** « terrain trop étroit » | **Analyse à compléter** + diagnostic « contour très découpé (compacité 0,11)… "trop étroit" serait trompeur » | D5 : la cause réelle est nommée, sans règle de taille |
| `97403000AN0088` (zone A) | **0** | **Hors de ce projet** (preuve : zone A inconstructible au PLU) | la famille de zone devient une preuve sourcée, pas un verdict muet |
| `97403000AM0092` (bâti 45 %) | **D** | conservation **C** (bande remonte) | D2 : le malus bâti disparaît, la démolition devient une vigilance |

---

## 2. État de référence réel (cartographie) et divergences avec ALGO-LECTURE-1

Chemin vérifié dans le dépôt (les chemins du rapport sont des pistes — ici les chemins RÉELS) :

| Brique | Fichier réel | Fait vérifié |
|---|---|---|
| Capacité PLU **C = sdp_max** | `faisabilite/engine.py:686` (`estimate_capacity`) → `faisabilite/residuel.py:177` | `fourchette["surface_plancher_m2"]` ; **calculée live**, PAS persistée au run |
| Existant **E = sdp_existante** | `residuel.py:205-207` (`emprise_batie × niveaux × coef`) | **calculé live**, PAS persisté |
| Résiduel **R = max(0, C−E)** | `residuel.py:208` ; cache `parcel_residuel_runs.sdp_residuelle_m2` (vue `parcel_residuel`) | **seul R est persisté** au run servi |
| Causes moteur | `residuel.py:119-147` ; `engine.py:354-397` (`cause_libelle`) | `terrain_exigu` / `zone_non_constructible:<z>` / `habitat_interdit:<z>` / `redhibitoire` / `capacite_nulle` / `hors_plu` / `zone_non_resolue:<z>` / `regle_plu_non_validee:<z>` / `surface_incertaine` / `hauteur_indispo` |
| `terrain_exigu` | `engine.py:20` `SEUIL_EXIGU_M2 = 5.0` | teste le **contour après reculs**, pas la surface — confirme l'angle mort d'ALGO-LECTURE-1 §3.4 |
| Barème + coefficients | `score_labuse.py:104-209` ; `config/score_labuse.yaml` | barème saturant (plafond 2 000 m²), `pente × forme × accès × bâti`, plancher 0,40, ×0,5 AU |
| Signal servi | `score_labuse_combine.py` (table `score_labuse` : `signal_p`, `signal_niveau`, `cascade_exclue`) ; seuils `signal_mutation.py:29-44` + `config/scoring_client.yaml` | **probabilité servie** = `signal_p` (calibrée) ; seuils Fort ≥ 0,20 / Moyen ≥ 0,10 ; verrou `PRIORITE_SERVIE=false` (`tiers_client.py`, `frontend/.../status.ts`) |
| Cible **L2-F** | `p_model/ext_sql.py` | natures `('Vente','Vente terrain à bâtir')` **moins** l'immeuble < 4 appartements (`exclue_l2f`) — prédicat lu dans le code, pas inventé du sigle |

**Divergences factuelles avec ALGO-LECTURE-1 :** aucune contradiction de fond. Précisions
mesurées ce jour : (a) la cause `terrain_exigu` porte un `exigu_raison` (ppr_rouge / ER / EBC /
reculs / contraintes / portion_reduite) exploité par le diagnostic ; (b) **C et E ne sont PAS
persistés** au run servi — seul R l'est — ce qui conditionne l'architecture (§4) ; (c) la « HC »
d'ALGO-LECTURE (bande belle + exclusion dure) correspond exactement au cas que la V2 range en
**Hors de ce projet** avec la preuve de cascade.

---

## 3. Décisions de Vic → implémentation

| Décision | Où, et comment |
|---|---|
| **D1** bandes conservées, barème actuel × pente/forme/accès | `scenarios_v2._coef_physique` + `_bande_pour` réutilisent `score_labuse._f_pente/_f_forme/_f_acces`, `_bareme_capacite`, `bande_de_score` (source unique des coefficients, gravés) |
| **D2** deux scénarios, **sans coef bâti**, **sans ×0,65 démolition**, D_net signé, calculé pour toutes | `_finish_keep` (R = max(0,C−E)) / `_finish_rebuild` (C_rebuild, E, D_net signé) ; aucun `_f_bati` ; saturées incluses |
| **D3** statuts exclusifs, AU fermée → **À différer avant toute bande** | `evaluate` §5.1 : `DEFERRED` testé à l'étape horizon, AVANT toute bande ; plus de ×0,5 |
| **D4** une inconnue ne fabrique pas une bande | `_bande_sensible_a_inconnue` + `_inconnues_physiques` : pente/forme/accès inconnus → test de sensibilité (config) ; si la bande bascule → `TO_VERIFY`, **bande provisoire au détail** (accès : « inconnu » = aucun verdict, ensemble vide aujourd'hui ; PASS = mesuré) |
| **D5** `terrain_exigu` diagnostiqué, sans règle de taille | `scenarios_v2_build._diagnostic_geometrie` : validité, multipolygone, **compacité** ; `suspect → TO_VERIFY` ; sinon cause précise « aucune assiette après retraits » |
| **D6** Signal protégé, état exposé | Signal **relayé** depuis `score_labuse` (`_signal_state`) ; **aucun fichier du Signal modifié** (test structurel) ; `mode=sale` sert le Signal, le foncier n'entre pas |
| **D7** hors périmètre (division/préétude, versions, interface) | `scenario=divide` = `PRESTUDY` documentaire (aucun lot) ; aucun nouveau système de versions ; aucun fichier front |
| **D8** valeurs invalides interceptées | gardes `_finite/_nonneg` partout → `TO_VERIFY` avec cause, jamais un score |
| **D9** contrat de sortie par parcelle + effectifs | `analyse_scenarios_payload` : statut+cause, bande+score, quantités, vigilances, portion productive, Signal+état ; `effectifs()` par statut et par bande |
| **D10** tri déterministe | `order` : groupe de statut → (potentiel) **bande d'abord** puis quantité ; nulles après les connues, jamais zéro ; égalité → IDU |

---

## 4. Fichiers et contrats — ajoutés / modifiés

**Ajoutés** (calcul + API, isolés) :

- `src/labuse/scoring/scenarios_v2.py` — **moteur PUR** (aucune base, aucun SIG) : `evaluate`,
  `order`, `effectifs`, `ScenarioRecord`, `ScenarioResult`. Miroir fidèle du moteur de référence
  `04_MOTEUR_REFERENCE.cjs` + couche bandes (D1/D2/D4).
- `src/labuse/scoring/scenarios_v2_build.py` — **adaptateur** (lecture seule) des caches réels vers
  `ScenarioRecord` : `records_for_parcels` (cache / `enrich` live C,E ; `with_zone` = portion
  productive), diagnostic géométrique `terrain_exigu`, contraintes partielles (PPR rouge / EBC /
  pente), correction `residuel_legacy`, relais Signal ; `analyse_scenarios_payload` (calcul live).
- `src/labuse/scoring/scenarios_v2_persist.py` *(2ᵉ passe)* — **table de run**
  `parcel_scenario_v2_runs` (DDL) + `compute_scenarios_v2_batch` (ÉCRIT C,E,C_rebuild,D_net,statut,
  cause,bande/scénario) + `read_scenarios`/`analyse_payload_persiste` (l'endpoint LIT).
- `tests/test_algofix1_contrat.py` — **26 tests de contrat** du §13.2 + D4 complet (moteur pur).
- `tests/test_algofix1_protections.py` — **4 protections + 2 bonus** sur parcelles réelles q_v20.
- `tests/test_algofix1_signal_intact.py` — preuve **Signal intact** (structurelle + comportementale).
- `tests/test_algofix1_persist.py` *(2ᵉ passe)* — écrit = calculé ; l'endpoint-lecture rend le
  contrat + effectifs + Signal relayé, sans recalcul.
- `scripts/algofix1_avant_apres.py` — avant/après île (lit la table de run) ; `AVANT-APRES.md`.
- `scripts/algofix1_persist_run.py` *(2ᵉ passe)* — peuple la table de run (île + enrich 2 communes).

**Modifié** (seul fichier existant touché) :

- `src/labuse/api/app.py` — un endpoint **lecture seule** `GET /analyse/scenarios` qui **LIT** la
  table de run (trappe `enrich=1` live ≤ 500). Aucun autre chemin modifié.
- `tests/test_proxy_dev_couvre_routes_api.py` — `/analyse` ajouté à l'allowlist serveur (front non
  encore câblé).

**Caches historiques :** aucun écrasé. Le moteur pur et l'adaptateur n'écrivent RIEN (test
structurel) ; **seul** `scenarios_v2_persist` écrit, et uniquement dans la table **neuve**
`parcel_scenario_v2_runs`. La V2 lit `parcel_residuel`, `score_labuse`, `parcels`.

---

## 5. Avant / après (toute l'île + Entre-Deux, q_v20)

`AVANT-APRES.md` donne les tableaux complets **par commune et par scénario**, lus de la table de
run. **Île entière (433 229 parcelles)** :

| | V1 (bande servie) | V2 conservation | V2 reconstruction |
|---|---|---|---|
| Actionnable | A/B/C/D : 192 344 (44,4 %) | **ESTIMATED 184 432 (42,6 %)** | **ESTIMATED 269 455 (62,2 %)** |
| Aucun ajout | — | NO_MARGIN 85 480 (19,7 %) | NO_MARGIN 0 |
| À vérifier | NC : 16 272 | TO_VERIFY 30 438 (7,0 %) | TO_VERIFY 30 895 (7,1 %) |
| À différer | — | DEFERRED 782 | DEFERRED 782 |
| Hors projet | — | OUTSIDE 132 097 (30,5 %) | OUTSIDE 132 097 (30,5 %) |
| Non retenue (muette) | **0 : 217 954 (50,3 %)** + HC 6 659 | *(réparti ci-dessus)* | *(réparti ci-dessus)* |

Lecture : la **moitié muette** de la V1 (« 0 ») se répartit en statuts nommés ; en
**reconstruction**, **62,2 %** de l'île reçoit une « Capacité estimée » (un projet de remplacement
existe dès que la zone autorise le logement), avec son **D_net signé**. Les bandes V2 conservation
(parmi les 184 432 estimées) : A 5,5 % · B 30,3 % · C 34,1 % · D 30,0 %. Le **top 20 des changements
de bande** (avec la raison) est dans `AVANT-APRES.md`.

**Entre-Deux (6 341)** — faits saillants :

- **Conservation** — les 3 789 « 0 » de la V1 se répartissent en statuts nommés : **Hors de ce
  projet** (3 054, preuve), **Aucun ajout identifié** (810, saturé/capacité nulle), **Analyse à
  compléter** (142, dont les `terrain_exigu` douteux avec diagnostic). **2 335** parcelles reçoivent
  une **Capacité estimée** avec une bande A/B/C/D qui décrit le scénario conservation.
- **Reconstruction** (C/E calculés live, run enrichi sur les 6 341 parcelles) — statuts :
  **ESTIMATED 2 881 (45,4 %)** · OUTSIDE_OBJECTIVE 3 054 (48,2 %) · TO_VERIFY 406 (6,4 %) ·
  **NO_MARGIN 0** (en reconstruction, dès que la zone autorise le logement il existe une capacité de
  projet, même saturé). Soit **+550 parcelles** « Capacité estimée » par rapport à la conservation.
  Sur un échantillon de 80 parcelles « 0 » saturées, **67 obtiennent un scénario**, **tous à gain
  net négatif** (ex. `97403000AM0016` : C_rebuild 5 135, E 7 497, **D_net −2 362 m²** — la
  démolition-reconstruction perd de la SDP, affichée **signée**, pas écrasée à 0).
- **Effectifs par statut** : chaque parcelle de la sélection a UN statut ; la somme des statuts
  exclusifs = N_selection (6 341). Aucune parcelle n'est silencieusement retirée (spec §2.1).
  _(note : la conservation lit le R caché du run ; l'enrichissement recalcule C/E live, d'où un
  écart de 4 parcelles sur les statuts conservation entre run caché et run enrichi — attendu.)_

---

## 6. Cas géométriques sensibles — preuves (D5)

Le diagnostic (`_diagnostic_geometrie`) ne conclut JAMAIS « terrain trop étroit » d'une taille
(interdit mandat/§9.3). Il mesure : `ST_IsValid`, `ST_NumGeometries` (multipolygone), **compacité
4πA/P²** (1 = disque, → 0 = contour très découpé).

- `97403000AL0258` — 113 832 m², compacité **0,11** → contour très découpé → les reculs peuvent
  vider l'assiette utile sans que la parcelle soit « étroite » → **À vérifier**, le mot faux est
  explicitement récusé (« "trop étroit" serait trompeur »).
- Règle appliquée : géométrie suspecte (invalide / multipolygone / compacité < 0,25) ⇒ **TO_VERIFY**
  quelle que soit la surface ; géométrie saine mais assiette réellement vidée ⇒ cause précise
  « Aucune assiette obtenue après application des retraits identifiés » (jamais déduite d'une
  géométrie vide). Les 139 causes vides ne sont **pas** renommées « saturation en hauteur ».

---

## 6-bis. Les deux cas réels de Saint-Denis (zonage à cheval, D9 + correction)

Les deux parcelles nommées par le mandat sont **à cheval** : majoritairement zone N, mais la
capacité servie vient d'une **portion minoritaire U/AU**. Mesures sur q_v20 :

| IDU | Surface | Zonage (parts) | Capacité servie | Portion productive | Assiette | pente |
|---|---|---|---|---|---|---|
| `97411000EH0043` | 226 815 m² (22,7 ha) | N 56,6 % · **AUm 39,4 %** · Uh 3,8 % | V1 « Bonne » (B), R = 44 117 m², SDP C = 44 123 | **AUm ≈ 89 365 m²** (part AU) ; emprise clippée 49 026 m² | **gabarit** (PPR rouge 64 % découpé) | 91 % |
| `97411000EI0085` | 199 431 m² | N 86,0 % · **Um 8,2 %** · AUm 5,1 % | V1 « Bonne » (B), R = 11 368 m², SDP C = 12 976 | **Um ≈ 16 353 m²** (part U) | **residuel_legacy** (NON découpé) | 87 % |

**EH0043 — réelle mais à rendre transparente (pas fausse).** L'assiette est calculée par le
**gabarit** : le PPR rouge (64 % « HARD_EXCLUDE ») et l'EBC sont **découpés** ; l'emprise tombe à
49 026 m² (21,6 % de la parcelle), sur la portion **AUm**. La capacité est **théorique et
correctement clippée** ; le problème est l'**opacité** du produit servi (« zone N » + « Bonne » +
« aléa rédhibitoire » sans dire d'où vient la capacité). La V2 **expose** (D9) : `zone_productive =
{AUm, 89 365 m²}` et trois vigilances sourcées — « PPR zone rouge ~64 % — exclu de l'assiette
(découpé au gabarit) », « EBC — construction interdite sur l'emprise boisée », « pente ~91 % —
terrassement majeur, pas une exclusion ». Statut V2 : **Capacité estimée**.

**EI0085 — capacité SURESTIMÉE, corrigée.** L'assiette vient du chemin de **repli**
(`residuel_legacy`), qui **n'est pas découpé** au gabarit (reculs + PPR rouge + EBC) malgré un PPR
rouge sur 47 % et un EBC sur 39 %. Signe mesuré : l'emprise (14 417 m²) couvre **88 % de la portion
Um** (16 353 m²), contre ~50 % pour EH0043 (gabarit) — le repli **sous-découpe**. La V2 **corrige** :
`residuel_legacy` + contrainte rédhibitoire partielle ⇒ **calcul d'assiette douteux** → **Analyse à
compléter** (À vérifier, cause `CALCUL_ASSIETTE_DOUTEUX`), au lieu de servir « Bonne » sur un chiffre
non fiable. La vigilance nomme la cause : « assiette de repli non découpée + contrainte rédhibitoire
partielle — surface productive et capacité à confirmer ».

**Cause racine, portée.** 53 923 parcelles du run servi (42 539 constructibles avec capacité)
portent `assiette_source = residuel_legacy` — le gabarit n'a pas été calculé pour elles (gap de
couverture RESIDUEL-1). La **correction de fond** (recalcul du gabarit pour ces parcelles) est un
geste **au niveau du run** (moteur de faisabilité), hors de ce mandat « calcul + API isolé » ; la V2
**refuse** entre-temps de servir le chiffre douteux comme une capacité sûre — exactement ce que
demande la spec §9.3. Les parcelles `residuel_legacy` **sans** contrainte rédhibitoire restent
« Capacité estimée » avec une vigilance « assiette de repli — à confirmer ».

## 7. Préservation du Signal de mutation (D6, spec §12)

- **Structurel** : aucun des 14 fichiers de la chaîne du Signal (modèle gelé, WoE, features,
  calibration, seuils `scoring_client.yaml`, `tiers_client.py`, `frontend/.../status.ts`) n'est
  modifié par la branche — vérifié par `test_aucun_fichier_du_signal_modifie` (git vs merge-base).
- **Comportemental** : la V2 **relaie** `signal_p` et `signal_niveau` servis sans les recalculer
  (`test_signal_relaye_a_l_identique` sur 50 parcelles réelles) ; une probabilité absente reste
  « non évalué » (≠ zéro, ≠ Faible) ; hors-bornes → « à vérifier » sans écrêtage.
- **Verrou Priorité** : inchangé (`PRIORITE_SERVIE=false`), non réactivé.
- En **prospection vente**, une parcelle sans potentiel garde son Signal et reste visible (D6) :
  `mode=sale` n'applique aucune exclusion foncière à la prédiction servie
  (`test_vente_ne_reapplique_pas_exclusions_logement`).

---

## 8. Tests exécutés et validations manquantes

| Suite | Résultat |
|---|---|
| `test_algofix1_contrat.py` (26 contrats §13.2 + D4 complet, moteur pur) | **39 passed** |
| `test_algofix1_protections.py` (4 protections + 2 bonus, réel q_v20) | **6 passed** |
| `test_algofix1_signal_intact.py` (Signal intact) | **3 passed** |
| `test_algofix1_persist.py` (écrit = calculé ; endpoint-lecture, réel q_v20) | **4 passed** |
| Import `app` + route + boot uvicorn :9970 + curl (lecture persistée + enrich) | **OK** |

**Validations encore manquantes** (honnêtes) :

- La **réussite des tests pédagogiques n'est pas une validation produit** (rappel du mandat). Le
  moteur pur valide le contrat arithmétique et les statuts ; il ne valide ni le SIG ni le modèle ML.
- **Reconstruction chiffrée (C/E/C_rebuild/D_net)** : persistée sur **Entre-Deux + Saint-Denis**
  (enrich ≈ 80 ms/parcelle). Sur le reste de l'île, la **conservation** est persistée exactement et
  le **statut** de reconstruction est dérivé ; les **quantités** de reconstruction y sont à
  `enriched=false` — leur calcul île entière (~10 h mono-cœur) est le run de nuit (activation).
- La **cause racine `residuel_legacy`** (gabarit non calculé pour 53 923 parcelles) se corrige au
  niveau du moteur de faisabilité (hors de ce mandat isolé) ; la V2 refuse entre-temps de servir le
  chiffre douteux (§6-bis).
- Les **coefficients pente/forme/accès restent NON validés** (D1) ; plan de validation en §10.
- Le **banc de cohérence complet** et la suite unitaire entière n'ont pas été rejoués ici (env
  Python projet ; venv `~/Desktop/labuse/.venv` pour les tests ciblés ; seul échec hors périmètre :
  `test_compte2_brevo` real-API, marqueur `local`).

---

## 9. Activation et retour arrière (cohérents avec le processus projet)

1. **Geler la référence** : l'instantané q_v20 et les résultats servis restent intacts (la V2 ne
   touche rien).
2. **Calcul parallèle** : `scripts/algofix1_avant_apres.py` et `/analyse/scenarios?enrich=1`
   produisent la V2 sans bascule ; comparer identifiants, capacités, statuts, effectifs sur le même
   instantané (fait pour Entre-Deux).
3. **Persistance** *(fait)* : `scripts/algofix1_persist_run.py` peuple la table **neuve**
   `parcel_scenario_v2_runs` (C, E, C_rebuild, D_net, statut, cause, bande/scénario) depuis
   `compute_residuel`, sans toucher `parcel_residuel_runs` ni `score_labuse`. **L'endpoint LIT** la
   table. Activation île entière = lancer l'enrichissement de nuit (conservation déjà île-entière).
4. **Interface** : derrière l'indicateur de version (mandat d'écran suivant) ; mêmes filtres, deux
   sorties, aucun nouvel onglet.
5. **Retour arrière** : supprimer l'endpoint et la table V2 ; le service historique
   (`/parcels`, `/stats`, Signal) n'a jamais été modifié → bascule triviale, jamais de moitié V1 /
   moitié V2.

---

## 10. §13.3 — plan du panel de validation des coefficients

Les coefficients `pente (15 %/30 % → 1,0/0,85/0,60)`, `forme (lame < 8 m & allongement > 8 →
0,80)`, `accès (PASS → 0,85)` et le barème de capacité (plafond 2 000 m²) sont **conservés
provisoirement et NON validés** (D1, spec §1). Proposer de nouveaux coefficients « calibrés » sans
données produirait une précision artificielle (spec §1). Plan de validation, à mener **avant** toute
re-calibration :

**a. Panel documenté (couverture).** Constituer un échantillon couvrant les **24 communes** à
l'échelle de la validation finale, stratifié sur les familles sensibles : terrain nu · bâti conservé
· bâti saturé · existant supérieur aux règles actuelles · pente (3 classes) · parcelle découpée
(à cheval) · contraintes partielles (PPR/ER/EBC) · AU fermée · petites parcelles · assemblages. Pour
chaque parcelle : géométrie, zonage par portion, C/E/R, pente, accès, cause, statut V2, bande V2.

**b. Triple revue métier.** Faire revoir les **mêmes intentions de projet** par trois profils —
agents/apporteurs, lotisseurs/aménageurs, promoteurs. Mesurer **d'abord** : capacités plausibles,
causes erronées, faux rejets (notamment les ex-`terrain_exigu` et les saturées en reconstruction).
Les ventes **ne calibrent pas** la faisabilité d'un projet (ne pas réutiliser le Signal ici).

**c. Métriques, par univers.** Rapporter, séparément pour chaque strate : taux de capacités jugées
plausibles, taux de faux rejets, taux de causes erronées, désaccords inter-juges (κ). **Effectifs,
cas non jugeables et désaccords publiés** ; aucune précision commerciale globale inventée (une revue
sur petit échantillon est une recette, pas une preuve statistique pour l'île).

**d. Protocole de re-calibration (seulement si b/c le justifient).** Chaque coefficient candidat est
rattaché à une hypothèse testable (ex. « la pente > 30 % réduit la SDP constructible réelle d'un
facteur mesuré sur terrain »). Une re-calibration modifie `config/score_labuse.yaml` → **nouveau
hash → nouvelle `score_version`** (le versionnement existant suffit, D7) ; la V2 est recalculée en
parallèle et re-comparée (avant/après) avant tout service.

**e. Sensibilité des bandes aux inconnues (déjà outillée).** La protection D4 (`_bande_sensible_a_
inconnue`) fournit, par parcelle, le fait « la bande dépend d'une donnée inconnue » : le panel doit
quantifier **combien** de parcelles basculent en « À vérifier » pour cette raison, par commune, afin
d'orienter l'effort de mesure (pente en priorité).

**Hors de ce travail** (rappel, spec §13.4) : la validation du Signal (forward, AUC, calibration par
groupes, lift, effectifs par univers prospectable) est un chantier distinct ; ALGO-FIX-1 ne touche
pas le Signal et ne le re-valide pas.

---

*Fin du compte rendu. Branche `fix/algo-fix-1`, non mergée, run servi intact, Signal intact.*
