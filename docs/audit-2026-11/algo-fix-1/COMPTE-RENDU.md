# ALGO-FIX-1 — compte rendu

**Mandat** ALGO-FIX-1 — l'Analyse LABUSE par scénario, honnête sur l'inconnu.
**Branche** `fix/algo-fix-1` (worktree `~/Desktop/labuse-algofix`). **Aucun merge, aucun accès
production, aucune modification du run servi.** Calcul et API seulement ; aucun fichier du front
touché. Instantané de travail : run servi **`q_v20`** (base locale, 433 229 parcelles).

Références normatives : `docs/audit-2026-11/algo-fix-1/LABUSE_DOSSIER_V2/01_SPECIFICATION_ALGORITHME.md`
(§4, 5, 7, 8, 9, 10, 12, 13.2) et les **décisions de Vic D1–D10** du mandat (qui prévalent sur la
spécification là où elles diffèrent). État de l'existant : `docs/audit-2026-11/algo-lecture-1/ALGO.md`.

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
| **D4** une inconnue ne fabrique pas une bande | `_bande_sensible_a_inconnue` : pente non mesurée → test de sensibilité (config) ; si la bande bascule → `TO_VERIFY`, **bande provisoire au détail** |
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
  `ScenarioRecord` : `records_for_parcels` (cache / `enrich` live C,E), diagnostic géométrique
  `terrain_exigu`, relais Signal ; `analyse_scenarios_payload` (contrat §2.2/§2.1/§10).
- `tests/test_algofix1_contrat.py` — **26 tests de contrat** du §13.2, adaptés (moteur pur).
- `tests/test_algofix1_protections.py` — **4 protections + 2 bonus** sur parcelles réelles q_v20.
- `tests/test_algofix1_signal_intact.py` — preuve **Signal intact** (structurelle + comportementale).
- `scripts/algofix1_avant_apres.py` — comparaison avant/après (génère `AVANT-APRES.md`).

**Modifié** (seul fichier existant touché) :

- `src/labuse/api/app.py` — un endpoint **lecture seule** `GET /analyse/scenarios`
  (commune|idus, mode, scenario, sort, enrich, pagination). Aucun autre chemin modifié.

**Caches historiques :** aucun écrasé. **Aucune écriture SQL** dans les modules V2 (test structurel
`test_cover_le_module_v2_n_importe_aucune_ecriture_signal`). La V2 lit `parcel_residuel`,
`score_labuse`, `parcels` et calcule C/E live quand on demande la reconstruction.

---

## 5. Avant / après sur le même univers (Entre-Deux, q_v20)

Voir `AVANT-APRES.md` pour les tableaux complets. Faits saillants :

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
| `test_algofix1_contrat.py` (26 contrats §13.2, moteur pur) | **35 passed** |
| `test_algofix1_protections.py` (4 protections + 2 bonus, réel q_v20) | **6 passed** |
| `test_algofix1_signal_intact.py` (Signal intact) | **3 passed** |
| Import `labuse.api.app` + route `/analyse/scenarios` + boot uvicorn :9970 + curl | **OK** (health, rebuild D_net signé, sale, 400) |

**Validations encore manquantes** (honnêtes) :

- La **réussite des tests pédagogiques n'est pas une validation produit** (rappel du mandat). Le
  moteur pur valide le contrat arithmétique et les statuts ; il ne valide ni le SIG ni le modèle ML.
- La **reconstruction à l'échelle de l'île** n'est pas persistée : C/E sont calculés live
  (≈ 80 ms/parcelle). Pour servir la reconstruction pour toutes les parcelles, un run parallèle
  (batch enrichi vers une table V2 dédiée) est l'étape d'activation — non faite ici (pas de prod).
- Les **coefficients pente/forme/accès restent NON validés** (conservés provisoirement, D1) : la
  bande hérite de leur incertitude. Le plan de validation est en §10.
- Le **banc de cohérence complet** et la suite unitaire entière n'ont pas été rejoués dans ce
  compte-rendu (env Python projet ; venv `~/Desktop/labuse/.venv` utilisé pour les tests ciblés).

---

## 9. Activation et retour arrière (cohérents avec le processus projet)

1. **Geler la référence** : l'instantané q_v20 et les résultats servis restent intacts (la V2 ne
   touche rien).
2. **Calcul parallèle** : `scripts/algofix1_avant_apres.py` et `/analyse/scenarios?enrich=1`
   produisent la V2 sans bascule ; comparer identifiants, capacités, statuts, effectifs sur le même
   instantané (fait pour Entre-Deux).
3. **Persistance (activation)** : un batch V2 (à écrire) peuplerait une table dédiée
   `parcel_scenario_v2_runs` (C, E, R, cause, AU, géométrie) depuis `compute_residuel`, sans toucher
   `parcel_residuel_runs` ni `score_labuse`. L'endpoint lirait alors la table au lieu de calculer
   live.
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
