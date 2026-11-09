# ALGO-FIX-1 — compte rendu

**Mandat** ALGO-FIX-1 — l'Analyse LABUSE par scénario, honnête sur l'inconnu.
**Branche** `fix/algo-fix-1` (worktree `~/Desktop/labuse-algofix`). **Aucun merge, aucun accès
production, aucune modification du run servi.** Calcul et API seulement ; aucun fichier du front.
Instantané de travail : run servi **`q_v20`** (base locale, 433 229 parcelles).

Références normatives : `LABUSE_DOSSIER_V2/01_SPECIFICATION_ALGORITHME.md` (§4, 5, 7, 8, 9, 10, 12,
13.2), les **décisions de Vic D1–D10**, et les deux revues d'Astra
(`AVIS-ASTRA-ALGO-FIX-1.md`, `AVIS-ASTRA-ALGO-FIX-1-PASSE-3.md`) intégrées. État de l'existant :
`docs/audit-2026-11/algo-lecture-1/ALGO.md`. Ce document est **le bilan unique** : il ne contient
que l'état courant du dépôt (aucune valeur des passes antérieures).

---

## 1. Ce que fait la V2

La V2 **ne remplace pas** la note 0–100 par une autre note universelle : elle sert, par parcelle
et par scénario, un **statut** (avec sa cause), des **quantités nommées**, une **bande** qui décrit
UN scénario, des **points de vigilance**, et le **Signal relayé** tel quel. Elle se calcule **en
parallèle** du service historique (`/parcels`, `/stats`, Signal) — aucune bascule.

**Deux scénarios de potentiel** (D2), même formule pour toutes les parcelles :
- **Conservation** : R = max(0, C − E) ; aucun coefficient bâti (l'existant est déjà soustrait).
- **Reconstruction** : C_rebuild, E, D_net = C_rebuild − E **signé** ; aucun malus de démolition ;
  calculée pour TOUTES les parcelles, saturées comprises.

**Bande** (D1) = `barème(quantité) × pente × forme × accès` — **sans** le coefficient bâti et
**sans** le ×0,5 AU. Une inconnue (pente/forme/accès) qui ferait basculer la bande ⇒ **À vérifier**,
bande provisoire au détail (D4).

**Statuts exclusifs** par scénario : *Capacité estimée* · *Calcul à compléter* (quantités du
scénario pas encore chiffrées, distinct d'un problème de données) · *À vérifier* · *À différer* ·
*Aucun ajout identifié* · *Hors de ce projet* (avec preuve).

**Calcul en précision complète** : C, E et R gardés en flottant pour le barème/la bande ; arrondi
**seulement à l'affichage**. Les quantités servies sont valides (finies, ≥ 0 ; D_net signé) et
sérialisables.

---

## 2. État de référence réel (chemins vérifiés dans le dépôt)

| Brique | Fichier réel | Fait vérifié |
|---|---|---|
| C = capacité PLU | `faisabilite/engine.py` (`estimate_capacity`) → `residuel.py` `sdp_max_m2` | calculée live ; **non persistée** au run servi (seul R l'est) |
| E = existant | `residuel.py` (`emprise × niveaux × coef`) `sdp_existante_m2` | calculé live, non persisté |
| R = max(0, C−E) | `residuel.py` ; cache `parcel_residuel_runs.sdp_residuelle_m2` | **seul R est persisté** |
| Causes moteur | `residuel.py` `_cause_indisponible` ; `engine.py` `cause_libelle` | `terrain_exigu` / `zone_non_constructible:<z>` / `habitat_interdit:<z>` / `redhibitoire` / `capacite_nulle` / `hors_plu` / `zone_non_resolue` / `regle_plu_non_validee` / `surface_incertaine` / `hauteur_indispo` |
| Assiette | `residuel.py` `assiette_source` | `gabarit` (découpé) / `residuel_legacy` (repli non qualifié) |
| Barème + coefficients | `scoring/score_labuse.py` ; `config/score_labuse.yaml` | barème saturant (plafond 2 000 m²), `pente × forme × accès × bâti`, plancher 0,40 |
| Signal servi | table `score_labuse` (`signal_p`, `signal_niveau`, `signal_version`, `cascade_exclue`) ; seuils `signal_mutation.py` + `scoring_client.yaml` | probabilité servie = `signal_p` ; Fort ≥ 0,20 / Moyen ≥ 0,10 ; verrou `PRIORITE_SERVIE=false` |
| Accès | cascade `acces` | **tout parcel a un verdict** (POSITIVE 366 506 / PASS 66 723, 0 sans) → « non identifié »(PASS)=fait mesuré, « inconnu » vide |

---

## 3. Décisions de Vic → implémentation (D1–D10)

| Décision | Où |
|---|---|
| **D1** bandes = barème × pente/forme/accès | `scenarios_v2._coef_physique`/`_bande_pour` (réutilise les coefficients gravés de `score_labuse`) |
| **D2** deux scénarios, sans coef bâti ni ×0,65 démolition, D_net signé, toutes parcelles | `_finish_keep` / `_finish_rebuild` |
| **D3** statuts exclusifs ; AU fermée → À différer avant toute bande | `evaluate` §5.1 |
| **D4** inconnue (pente/forme/accès) qui bascule la bande → À vérifier, bande provisoire | `_bande_sensible_a_inconnue` + `_inconnues_physiques` |
| **D5** `terrain_exigu` diagnostiqué (indices, pas preuve), sans règle de taille | `scenarios_v2_build._diagnostic_geometrie` |
| **D6** Signal protégé, relayé, état exposé | `_signal_state` / `_signal_persiste` ; aucun fichier du Signal modifié |
| **D7** division = préétude ; pas de nouveau système de versions ; 0 front | `scenario=divide` → PRESTUDY |
| **D8** valeurs invalides → À vérifier, jamais un score | gardes `_finite/_nonneg` |
| **D9** contrat de sortie + effectifs par statut/bande | `_result_to_dict` / `effectifs` |
| **D10** tri déterministe (groupe → bande → quantité → IDU ; `id`/`area`/`gain` explicites) | `order` / `_trier` |

---

## 4. Les deux revues d'Astra, intégrées

**1ʳᵉ revue** (`AVIS-ASTRA-ALGO-FIX-1.md`), 7 points : (1) reconstruction non chiffrée ⇒ statut
**« Calcul à compléter »** ; (2) provenance unique (cause/assiette/quantités/**versions** du même
calcul) ; (3) legacy non qualifié ⇒ **À vérifier** ; (4) géométrie invalide traitée quelle que soit
la cause, AU au statut inconnu ⇒ horizon inconnu, pas de texte « découpé » dérivé du nom du chemin ;
(5) EH0043 ⇒ À vérifier ; (6) effectifs sur la sélection exacte, Signal persisté validé ; (7) bilan
unique + décomposition à entrées constantes.

**2ᵉ revue** (`AVIS-ASTRA-ALGO-FIX-1-PASSE-3.md`), corrections terminées :
- **Garde-fou legacy PAR SCÉNARIO** : la qualification porte sur la capacité **du scénario** — R en
  conservation, **C en reconstruction**. Une reconstruction saturée (R = 0, C > 0) sur assiette de
  repli n'hérite plus d'un feu vert : elle passe **À vérifier** (`ASSIETTE_A_CONFIRMER`).
- **Contrôle AU uniforme** : la famille de la portion productive est lue des **motifs de cascade**
  (chemin rapide COMME enrichi), pas de `zone_parts`. Une portion AU dont le **régime n'est pas
  établi** sur la portion (aucune classe AU connue — l'absence de `parcel_au_statut` ne prouve rien)
  ⇒ horizon inconnu, dans les deux chemins. Témoins : `97401000AI0330` et voisins.
- **Précision** : C/E/R en précision complète (ex. C = 384,4 / E = 184,6 → R = 199,8, palier < 200,
  pas 200) ; arrondi à l'affichage seul (`residuel.py` expose des champs `_precis`). **Bande
  provisoire** = quantité du scénario (C en reconstruction). Quantités **valides** (jamais ∞/NaN/
  négatif exposé) et sérialisables.
- **Échec du calcul live NON silencieux** : état **par parcelle** (`not_requested` / `ok` /
  `failed`) ; `enriched` devient par parcelle ; un échec de lecture de portion ne supprime pas le
  contrôle AU (porté par les motifs).
- **Contrat API unique persisté/live** : en prospection, **statut = état de Signal** (`SIGNAL_*`),
  statut foncier dans un champ séparé, compteurs sur les états de Signal — identiques dans les deux
  chemins ; tris **`id`** et **`area`** implémentés (surface persistée) ; **Signal invalide = même
  état `TO_VERIFY`** des deux côtés ; **versions lues** des lignes servies (lot mixte **annoncé**),
  `analysis_version` et recette du Signal **lues** (pas codées) ; la mention « instantané figé » est
  remplacée par « calculs V2 actuels comparés au Signal servi q_v20 ».
- **DOUBLE-RETRAIT** renommé **exposition brute à examiner**, R > 0 / R = 0 / R absent séparés,
  mesure d'impact réelle renvoyée à **RESIDUEL-2** (`DOUBLE-RETRAIT.md`).

---

## 5. Avant / après — bilan unique (q_v20)

**Île entière (433 229 parcelles)** — lu de la table de run `parcel_scenario_v2_runs` :

| Statut | Conservation | Reconstruction |
|---|---:|---:|
| Capacité estimée | 151 223 (34,9 %) | 2 562 (0,6 %, **chiffrées**, enrich) |
| Calcul à compléter | 0 | 211 759 (48,9 %) |
| À vérifier | 72 314 (16,7 %) | 74 096 (17,1 %) |
| À différer | 320 | 320 |
| Aucun ajout | 64 880 (15,0 %) | 0 |
| Hors de ce projet | 144 492 (33,4 %) | 144 492 (33,4 %) |
| **Total** | **433 229** | **433 229** |

Bandes V1 servies, pour mémoire : A 6 166 · B 36 254 · C 50 913 · D 99 011 · **0 217 954** ·
NC 16 272 · HC 6 659. La **moitié muette « 0 »** se répartit en statuts nommés ; la reconstruction
ne **publie que les 2 562 capacités réellement chiffrées** (enrich Entre-Deux + Saint-Denis), les
**211 759 autres restent « Calcul à compléter »** — jamais « estimées » par déduction. Le niveau
« À vérifier » (16,7 % conservation) n'est **ni un taux d'erreur ni un objectif** : il isole les
assiettes de repli non qualifiées et les portions AU au régime non établi, que la V2 refuse de
servir comme sûres.

**Entre-Deux (6 341 parcelles)** :

| Statut | Conservation | Reconstruction |
|---|---:|---:|
| Capacité estimée | 2 043 | 2 559 |
| Aucun ajout | 564 | 0 |
| À vérifier | 582 | 630 |
| Hors de ce projet | 3 152 | 3 152 |
| **Total** | **6 341** | **6 341** |

La reconstruction porte **+516** parcelles « Capacité estimée » de plus que la conservation (les
saturées à assiette **qualifiée** que le remplacement rend lisibles, avec D_net signé) ; les
saturées à assiette de repli sont, elles, en « À vérifier » (P1a).

**Décomposition à entrées constantes** (`AVANT-APRES.md`, 416 957 parcelles calculables, R tenu
constant) : **invariant tenu, 0 parcelle** voit son score baisser en retirant le seul coefficient
bâti ; les promotions de bande à R constant viennent du retrait du bâti (**D→C 42 166 · C→B 27 828 ·
B→A 5 529 = 75 523**) puis du ×0,5 AU (≈ 660) — effet des coefficients **isolé** du recalcul des
capacités et des changements de statut. `AVANT-APRES.md` donne aussi la **matrice complète** bande
V1 × statut/bande V2 (y compris bande→bande entre estimées) et les **cohortes nommées**.

---

## 6. Les cas sensibles, état courant

| IDU | Surface | V2 | Pourquoi |
|---|---|---|---|
| `97411000EH0043` | 22,7 ha | **À vérifier** (`HORIZON_INCONNU`) | capacité sur portion **AUm** au régime non établi ; provisoire consultable (C 44 123, E 6, R 44 117), `zone_productive={AUm}` ; vigilances PPR rouge 64 % présent / EBC / pente 31,5 % moy ≠ 91 % max. **49 026 m² = `emprise_constructible` du moteur**, pas une assiette nette démontrée |
| `97403000AM0314` | 302 m² | conservation **Aucun ajout** / reconstruction **À vérifier** | saturée (R=0) sur assiette de **repli** : conservation = zéro réel ; reconstruction C>0 → à confirmer (P1a) |
| `97411000EI0085` | 19,9 ha | **À vérifier** (`CALCUL_ASSIETTE_DOUTEUX`) | assiette de **repli** non qualifiée, R provisoire 11 368 consultable |
| `97403000AL0258` | 11,4 ha | **Hors de ce projet** | cœur de **Parc National** (UNESCO) + PPR rouge 100 % + forêt domaniale + pente 133 % ; « terrain trop étroit » était trompeur |

---

## 7. Préservation du Signal de mutation (D6, spec §12)

- **Structurel** : aucun des fichiers de la chaîne du Signal (modèle gelé, WoE, features,
  calibration, seuils, `tiers_client.py`, `frontend/.../status.ts`) n'est modifié (test
  `test_aucun_fichier_du_signal_modifie`, git vs merge-base). L'ajout de champs `_precis` à
  `residuel.py` est **additif** : le `sdp_residuelle_m2` arrondi servi au feature store du Signal est
  inchangé.
- **Comportemental** : la V2 **relaie** `signal_p`/`signal_niveau`/recette servis sans recalcul ;
  probabilité absente ⇒ non évalué (≠ zéro, ≠ Faible) ; hors-bornes/NaN/∞ ⇒ **`TO_VERIFY`** dans les
  deux chemins, jamais en tête ; verrou Priorité inchangé.

---

## 8. Tests exécutés

| Suite | Résultat |
|---|---|
| `test_algofix1_contrat.py` (26 contrats §13.2 + D4, moteur pur) | **39 passed** |
| `test_algofix1_astra.py` (vérifications ciblées des 2 revues, moteur pur) | **15 passed** |
| `test_algofix1_protections.py` (protections + cas réels q_v20) | **8 passed** |
| `test_algofix1_signal_intact.py` (Signal intact) | **3 passed** |
| `test_algofix1_persist.py` (écrit=calculé, contrat API, effectifs/sale/tris/versions, q_v20) | **10 passed** |
| `test_proxy_dev_couvre_routes_api.py` | **3 passed** |
| Régression (slice `score_labuse`/`api`/`scenario`/`combine`, hors DB/réel) | **73 passed** |
| Endpoint live (uvicorn :9970, curl : lecture persistée, enrich, sale, 400) | **OK** |

**Validations manquantes (honnêtes)** : la réussite des tests pédagogiques n'est pas une validation
produit ; la reconstruction chiffrée n'est persistée qu'à **Entre-Deux + Saint-Denis** (enrich ≈
80 ms/parcelle ; l'île est « Calcul à compléter », chiffrage = run de nuit) ; la **mesure d'impact
du double retrait** est renvoyée à RESIDUEL-2 ; les coefficients pente/forme/accès restent **non
validés** (plan §11) ; le banc de cohérence complet n'a pas été rejoué (venv `~/Desktop/labuse/.venv`
pour les tests ciblés ; seul échec hors périmètre : `test_compte2_brevo`, API Brevo réelle,
marqueur `local`).

---

## 9. Fichiers (ajoutés / modifiés)

**Ajoutés** : `src/labuse/scoring/scenarios_v2.py` (moteur pur), `…/scenarios_v2_build.py`
(adaptateur lecture seule), `…/scenarios_v2_persist.py` (table de run + lecture). Scripts :
`algofix1_persist_run.py`, `algofix1_avant_apres.py`, `algofix1_double_retrait.py`. Tests :
`test_algofix1_contrat.py`, `…_astra.py`, `…_protections.py`, `…_signal_intact.py`, `…_persist.py`.

**Modifiés** : `src/labuse/api/app.py` (endpoint lecture seule `GET /analyse/scenarios`),
`src/labuse/faisabilite/residuel.py` (champs `_precis` additifs), `tests/test_proxy_dev_couvre_
routes_api.py` (`/analyse` en allowlist serveur). **Aucune table historique écrasée** ; la seule
écriture est la table **neuve** `parcel_scenario_v2_runs`.

---

## 10. Activation et retour arrière

1. **Référence gelée** : q_v20 et les résultats servis intacts (la V2 ne touche rien).
2. **Calcul parallèle** : `algofix1_persist_run.py` peuple la table de run ; l'endpoint LIT.
   Conservation île-entière déjà persistée ; reconstruction chiffrée = enrichir au run de nuit.
3. **Interface** : derrière l'indicateur de version (mandat d'écran suivant) ; mêmes filtres, deux
   sorties, aucun nouvel onglet.
4. **Retour arrière** : supprimer l'endpoint et la table V2 ; le service historique n'a jamais été
   modifié → bascule triviale, jamais de moitié V1 / moitié V2.
5. **Chantiers amont distincts** : RESIDUEL-2 (gabarit pour les 53 923 `residuel_legacy` + correction
   du double retrait des contraintes superposées) ; validation des coefficients (§11). Tant qu'ils
   ne sont pas faits, la V2 **isole** les capacités non qualifiées en « À vérifier ».

---

## 11. §13.3 — plan du panel de validation des coefficients

Les coefficients `pente (15/30 % → 1,0/0,85/0,60)`, `forme (lame < 8 m & allongement > 8 → 0,80)`,
`accès (PASS → 0,85)` et le barème (plafond 2 000 m²) sont **conservés provisoirement et non
validés** (D1). Plan, avant toute re-calibration :

**a. Panel documenté** couvrant les 24 communes, stratifié : terrain nu · bâti conservé · bâti
saturé · existant > règles · pente (3 classes) · parcelle découpée · contraintes partielles · AU ·
petites parcelles · assemblages. Par parcelle : géométrie, zonage par portion, C/E/R, pente, accès,
cause, statut V2, bande V2.

**b. Triple revue métier** (agents/apporteurs, lotisseurs/aménageurs, promoteurs) sur les mêmes
intentions de projet. Mesurer d'abord capacités plausibles, causes erronées, faux rejets (ex-
`terrain_exigu`, saturées en reconstruction, portions AU, assiettes de repli). Les ventes ne
calibrent pas la faisabilité.

**c. Métriques par univers** : taux de capacités plausibles, faux rejets, causes erronées,
désaccords inter-juges (κ). Effectifs, cas non jugeables et désaccords **publiés** ; aucune précision
commerciale globale inventée.

**d. Re-calibration** (si b/c le justifient) : chaque coefficient rattaché à une hypothèse testable ;
une modification de `config/score_labuse.yaml` → nouveau hash → nouvelle `score_version` (le
versionnement existant suffit) ; recalcul parallèle et re-comparaison avant service. La calibration
doit distinguer **quantité de plancher**, **difficulté/coût de réalisation** et **intérêt pour
prospecter** : un coefficient de difficulté n'est ni une règle de constructibilité, ni validé sur la
seule SDP. Ne pas retoucher les coefficients pour corriger une distribution jugée trop généreuse.

**e. Sensibilité aux inconnues** (déjà outillée, D4) : quantifier, par commune, combien de parcelles
basculent « À vérifier » faute d'une donnée (pente en priorité).

*Hors périmètre : la validation du Signal (forward, AUC, calibration par groupes, lift) est un
chantier distinct ; ALGO-FIX-1 ne touche pas le Signal.*

---

*Fin du compte rendu. Branche `fix/algo-fix-1`, non mergée, run servi intact, Signal intact.*
