# L'ALGORITHME, ÉTAPES EXACTES — parcelle brute → tier servi

> Le document demandé depuis le 29/07 : « comment l'algo est créé ». Chaque étape avec sa
> source code (fichier:ligne, vérifiés le 04/08/2026 sur main) et un exemple réel qui la
> traverse. Écrit pour être lisible par un non-développeur : les phrases d'abord, le code
> en référence. Lecture seule — rien n'est modifié par ce document.

## Vue d'ensemble (une phrase)
Une parcelle brute traverse : **un filtre dur** (étage 0), **une grille de règles** (cascade
→ notes Q/A), **un modèle statistique** (score P), **un plancher de capacité** (C), **un
classement** (rangs), **des tiers** (brûlante/chaude/…), **des déclassements motivés**
(zone fermée, inconstructible, AU, bâtie révélée), **d'éventuelles exceptions journalisées**,
et finit **servie** sous un label épinglé.

---
## Étape 1 — ÉTAGE 0 : l'écartée dure
**Quoi** : ce qui ne peut PAS être une opportunité sort d'emblée — eau, cœur de parc, forêt
publique, zone A/N massive, pente > 60 %, risque fort, foncier public. C'est définitif pour
le run : l'étage 0 **prime sur tout** le reste (même un score parfait).
**Où** : les couches d'exclusion `cascade/layers/phase1.py:58-350` (eau :58, parc :87, forêt
:116, zonage A/N :207, prescriptions/ER :353, risques :527, pente :656…) ; verdict
`HARD_EXCLUDE` → statut `exclue`/`faux_positif_probable` ; consommé par le scoring en
`scoring/p_v2/pipeline.py:269-280` (lu sur le run SERVI).
**Exemple réel — 97413000CD0729 (Saint-Leu)** : score assez fort pour être brûlante (rang
~194) MAIS propriétaire public → `HARD_EXCLUDE foncier_public` → **écartée**, le rang n'est
jamais montré (parcelle ancre du golden, `reports/m6-audit/golden/`).

## Étape 2 — CASCADE : la grille de règles et les notes Q/A
**Quoi** : chaque parcelle passe devant ~20 « couches » (phase 1 = géométrie pour toutes ;
phase 2 = données coûteuses pour les survivantes : propriétaire, DVF, permis, BODACC, DPE,
âge du dirigeant). Chaque couche rend un verdict (exclut / signale / bonifie / neutre /
inconnu) avec un poids. Les poids s'additionnent en deux notes : **Q** (qualité du terrain)
et **A** (accessibilité du propriétaire).
**Où** : orchestrateur `cascade/engine.py:28-52` ; écriture `cascade/pipeline.py:56-137` et
`:195-245` (tables `dryrun_cascade_results`, `dryrun_parcel_evaluations`) ; matrice
`scoring/dryrun.py:15-67`.
**Seuils vivants** (`config/scoring_matrice.yaml`) : base 50 ; **chaude si Q ≥ 65 ET A ≥ 60
ET complétude A ≥ 50 %** (double verrou : on ne déclare pas « accessible » un propriétaire
qu'on ne connaît pas) ; écartée si Q < 50. Un événement BODACC daté (liquidation, cession)
force chaude quels que soient Q/A — doctrine « l'événement prime ».

## Étape 3 — SCORE P : le modèle statistique (probabilité de mutation)
**Quoi** : un modèle appris (régression logistique sur historique de mutations) note chaque
parcelle : « à quel point ce foncier est-il susceptible de bouger ? ». Ses ingrédients
(28 features) : prix et rotation du secteur, densité bâtie, ancienneté du dernier permis et
de la dernière mutation, canopée, pente, zone… Le modèle est **gelé** (empreinte sha256
vérifiée à chaque run, refus si différente) ; seul l'intercept (le niveau moyen) est recalé
chaque run — jamais les poids (re-train = décision humaine annuelle).
**Où** : `scoring/p_v2/pipeline.py:195-426` (`run_score_v2`) ; artifact :81-91 ; features
`p_model/ext_sql.py` ; libellés lisibles :45-75 ; recalage :217-225 ; prédiction :227-228.
**Modulation servie** : la **pondération au_sous_plancher** (option B, 04/08) multiplie p par
(1 − manque/seuil) pour les AU trop petites pour l'opération minimale — `pipeline.py`
`_pondere_au_sous_plancher` (même point de calcul que la mention de fiche).
**Exemple réel — 97413000CX2555** : 195 m² en AUB Saint-Leu (seuil 3 333 m²) → facteur 0,058
→ son p fort s'effondre → a_creuser rang ~427 000 (l'ex-exception manuelle, levée le 04/08).

## Étape 4 — PLANCHER C : pas de tête sans capacité
**Quoi** : un propriétaire très « mutable » sur un terrain sans capacité constructive n'est
pas une opportunité. Plancher : **SDP résiduelle > 0 OU (surface ≥ 600 m² en zone U/AU)**
(600 m² ≈ plancher d'une division R+1 locale ; branche RNU : dans la PAU estimée + même
seuil).
**Où** : `scoring/p_v2/statuts.py:55-70` (`plancher_c`) ; la SDP résiduelle vient de
`faisabilite/residuel.py:44-99` (capacité max du règlement − bâti existant), cache
`parcel_residuel` (matérialisé à la bascule v8).
**Limite consignée (chemin B, audit 6)** : pour une bâtie révélée, la SDP affichée reste
celle du terrain nu théorique tant que la chaîne résiduel n'est pas recalculée avec le bâti.

## Étape 5 — RANGS : le classement
**Quoi** : toutes les parcelles hors copropriété sont classées par p décroissant ; les
égalités sont départagées par un tirage **déterministe** (graine 974 — reproductible, mais
voir audit saturation : un ex aequo au sommet reste un ex aequo).
**Où** : `pipeline.py:256-266` (tri, rangs, percentiles ; copro = jamais classée).

## Étape 6 — TIERS : brûlante, chaude, à creuser, réserve
**Quoi** :
- **Chaude** : rang ≤ n_entrée (calibré pour ~1 150 chaudes, continuité produit) ET plancher
  C — avec **hystérésis** anti-clignotement : une déjà-chaude reste chaude jusqu'à
  ~1,4 × n_entrée ; un événement daté < 6 mois fait entrer sans attendre.
- **Brûlante** : chaude ET contribution D (le « contexte dynamique » du modèle) au-dessus d'un
  seuil calibré mécaniquement pour tenir l'effectif dans [30-120] — doctrine « un contexte
  seul ne franchit jamais un seuil » ; un événement < 12 mois peut l'activer.
- **Réserve foncière** : très grosse capacité (top décile SDP) mais P sous la médiane —
  vitrine, jamais pipeline. — **À creuser** : le reste.
**Où** : `statuts.py:73-145` (`assign_tiers`) ; calibrages :148-171 (brûlante) et :174-181
(n_entrée) ; hystérésis appliquée `pipeline.py` (prev = dernier run servi).
**Exemple réel — 97403000AR1423 (Entre-Deux)** : 298 m² zone U, permis récent → chaude rang
~27 ; à la pondération du 04/08, le pool des chaudes s'épure → son contrib_D franchit le
seuil recalibré → **brûlante rang 22** (entrée mécanique, validée au golden — enquête
`qa/au_ouverture/enquete_ar1423.py`).

## Étape 7 — DÉCLASSEMENTS : sortis de la tête, mais VISIBLES avec motif
**Quoi** : cinq familles, hiérarchisées (la plus spécifique prime) ; une déclassée n'est pas
supprimée — elle est servie avec son motif :
- **A zone fermée** / **B non constructible** (`parcel_constructibilite`,
  `faisabilite/constructibilite.py:61-76`) ;
- **C non vérifiable** : PLU non calibré → SIGNAL de fiche, jamais un déclassement ;
- **D AU** : fermée ou phasage inconnu (`parcel_au_statut`, `faisabilite/au_ouverture.py`,
  calibré commune par commune — `au_sous_plancher` reste SERVIE, cf. étape 3) ;
- **E bâtie révélée** (04/08) : couche BD TOPO < 20 m² MAIS max(BD TOPO, CoSIA 2025) ≥ 40 m²
  → le bâti que l'image voit et que les couches vectorielles ratent
  (`faisabilite/bati_revele.py:24-56`, motif daté sourcé ; bande 20-40 = adjudication
  humaine, jamais automatique).
**Où (application)** : `statuts.py:130-143` — ordre : étage 0 > A/B > D > E.
**Exemple réel — 97414000CH1893 (Saint-Louis)** : maison invisible de TOUTES les sources
vectorielles (BD TOPO 9 m², ni piscine ni DVF ni DPE) — d'abord exception manuelle (04/08
matin), puis **couverte par la règle E** (CoSIA 139 m²) : aujourd'hui
`declasse_bati_revele`, motif « bâti détecté CoSIA (PVA juil.-août 2025), 139 m² ».

## Étape 8 — EXCEPTIONS : l'override humain, journalisé
**Quoi** : un arbitrage humain peut écraser un tier — toujours journalisé
(`served_run_exceptions` : origine, servi, motif, date). Les exceptions ne survivent PAS à
un re-score : elles sont ré-appliquées au geste de bascule ou remplacées par une règle
(les 17 du 04/08 sont toutes devenues la règle E ; il en reste UNE : CY0104, bâtie connue
en attente du filtre client bâti).

## Étape 9 — SERVI : label épinglé, tuiles, snapshot
**Quoi** : le produit lit UNIQUEMENT le run du label servi `Q_A_RUN_LABEL`
(`score_v_constants.py:46`, env `LABUSE_SERVED_RUN`) — un nouveau run ne devient jamais
servi sans décision explicite (`api/app.py:1304-1313`). Les tuiles carte (MVT) embarquent le
tier et se rebuildent à chaque bascule ; chaque run est gelé dans un snapshot au label unique
(protocole M1 : jamais d'écrasement, suffixe si collision). Toute bascule passe les
**6 gardes** (`bascule_gardes.py`) : anti-écrasement, disque, sauvegardes, complétude,
péremption AU, golden régénéré dans le même geste.

---
## Les seuils vivants, en un tableau
| seuil | valeur | source |
|---|---|---|
| Chaude (matrice) | Q ≥ 65 · A ≥ 60 · compl. A ≥ 50 % | config/scoring_matrice.yaml |
| Effectif chaude cible | ~1 150 (n_sortie ≈ ×1,4) | statuts.py:174 |
| Brûlante | garde-fou effectif [30-120], seuil D calibré | statuts.py:148 |
| Plancher C | SDP > 0 OU ≥ 600 m² U/AU | statuts.py:48 |
| Bâtie révélée (E) | couche < 20 ET max ≥ 40 (20-40 = adjudication) | bati_revele.py |
| Pondération AU | ×(1 − manque/seuil) | au_ouverture.facteur_ponderation |
| ER exclusion | ≥ 50 % d'emprise | cascade phase1.py:415 |
| Événements | bypass < 6 mois · brûlante < 12 mois | statuts.py:49-50 |
