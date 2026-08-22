# DETTE — Outil Faisabilité (« Par critères » / `faisabilite_sens2`)

Consignée à l'issue de **M133** (correction des faux positifs). Ce qui suit est
**hors périmètre M133** : nommé, non corrigé.

---

## 1. Cache `parcel_residuel` antérieur à M131 (A.2 — mandat data séparé)

La SDP consommée par l'outil vient du cache `parcel_residuel.sdp_residuelle_m2`
(`modules.py`, join du SQL de `faisabilite_sens2`), peuplé par la CLI
`compute-residuel` (`residuel.py:163`) — **sans `run_label`**, seulement un
`computed_at`. Mesuré (M132) : 431 663 lignes, `computed_at` du **2026-07-29 au
2026-08-19**, donc **antérieur au merge M131** (hauteurs Us/2AU gravées le
2026-08-22).

Conséquences :
- l'outil sert des SDP qui **ne voient pas** les hauteurs gravées en M131 (le
  résiduel a été calculé avant) ;
- preuve de dérive : le flag `capacite_estimee` du cache est incohérent avec
  `resolve_zone` courant (Saint-André : 143/1711 dans le cache vs 100 % en direct).
  **M133 a contourné** ce flag en lisant `resolve_zone(fine).calibree` en direct
  (B.5, `modules.py`) — le cache reste à rafraîchir pour la **SDP** elle-même.

**M134 — état des lieux (Phase A, cf. `RAPPORT_M134_PHASE_A.md`) :**
- La dérive n'est PAS « le cache ne voit pas M131 » : le cache **mélange trois
  états** — `computed_at` en 3 lots (2026-07-29 : 245 319 parcelles ; 08-05 : 8 032 ;
  08-19 : 178 312). Le lot 29/07 (57 %) précède **six** mandats d'entrée (M-N 08/08,
  M-PLU-REF 14/08, M-PLU-REF-B + M94 15/08, M130-12 + M131 22/08) ; le lot 19/08
  reflète M-N/M-PLU-REF/M94 mais **pas** M130-12/M131. Dérive **hétérogène par
  parcelle**.
- **Écrasable, pas versionné** : PK = `parcel_id` seul, aucun `run_id` ; UPSERT
  `ON CONFLICT (parcel_id)`. Un recalcul **écrase** la donnée servie → **aucun run
  neuf parallèle possible** sans changement de schéma (STOP du mandat M134). Éditer
  `served_run.txt` (bascule de run) **ne touche pas** ce cache : ce n'est pas une
  bascule mais un recalcul-écrasement.
- **Entrée du scoring ET de la cascade**, pas seulement des 3 écrans : `p_model`,
  `p_v2`, `cascade/context`, `etage0_ext` le lisent — un écrasement change les
  features du prochain run.
- **Aucun run neuf disponible** en attente : impossible à produire sans (2) une ligne
  de code pour rediriger vers une table de travail, ou (3) un backup+overwrite qui
  touche le service. Mesure de dérive faisable **read-only** par échantillon
  (`compute_residuel()` est pure) — à l'arbitrage de Vic.

**M134 — dérive MESURÉE (Phase C-échantillon, read-only, 0 écriture) :**
- **La dérive redoutée n'existe pas** : recalcul frais de `compute_residuel()` sur
  **5 583 parcelles** (7 ancres + 1027 zones M131 + 1497 lot×commune + 300 conso +
  3000 constructibles) → **0 changement** (borne haute < 0,05 %). Cause : diff YAML
  depuis le 29/07 = seuls ajouts M131 (`Us`, `2AUa-e`), tous **gelés** (résiduel 0) ;
  aucune zone constructible n'a vu hé/hf/emprise/recul bouger. M131 est **inerte sur
  le résiduel** (résultat attendu, pas échec), M130-12 aussi (4 m = hauteur sur gel).
- **A.3bis — le cache est une MOSAÏQUE de trois états de code** (lots 29/07 : 245 319 ;
  05/08 : 8 032, uniquement des constructibles ; 08-19 : 178 312). L'incohérence
  interne (computed_at étalé, code hétérogène) est **un constat d'hygiène EN SOI,
  séparé de la péremption** : aujourd'hui sans conséquence de VALEUR (les trois états
  produisent le même résiduel), mais un futur mandat qui changerait vraiment le calcul
  la rendrait dangereuse (drift hétérogène par parcelle selon son lot).
- **Coût d'un refresh** (mesuré) : île ≈ 127 min séquentiel (20,9 ms/constructible,
  16,1 ms/autre) ; par commune < 10 min.

**À faire (mandat data, arbitrage Vic — NON urgent, la valeur ne dérive pas)** : un
refresh peut attendre une **bascule planifiée**. Le vrai correctif d'hygiène = soit
versionner `parcel_residuel` par `run_id` (comparable/rafraîchissable, tue la
mosaïque), soit un recalcul atomique sur table de travail. **Ne touche pas** l'outil.

## 2. Deux systèmes de filtre « périmètre » (D.2 — dette structurelle)

- **`FiltreCriteres`** (`app.py:1200`) : point d'entrée unifié (~50 facettes) de la
  carte / liste / `export.csv` / **Projets** (`projets.py:3-8`).
- **`faisabilite_sens2`** : **SQL inline** (`modules.py`), un seul paramètre
  `commune`, aucune facette partagée.

Deux mécanismes parallèles pour la même notion. **À faire** : adosser l'outil à
`FiltreCriteres`. Hors périmètre M133 (« unification des filtres » exclue).

## 3. Stationnement non calibré (B.4 — issu du retrait du champ PARKING)

Le champ `PARKING` a été **retiré** du formulaire (M133) : il n'affectait que le
plancher `smin` (décoratif), et le convertir en emprise/SDP consommée exige un
**m²/place** qui n'est **SOURCÉ qu'à Cilaos** (`plu_cilaos.yaml:107`,
`place_m2_source_ref`) et **modélisé (25)** ailleurs (`plu_*.yaml: place_m2: 25.0`,
commentaire `plu_cilaos.yaml:106` : « ailleurs 25 est de la modélisation »). Une
valeur non lue au règlement est fabriquée — on ne l'applique pas.

Ce qui EST au PLU calibré mais **non consommé** : `stat_logement` (« 1 / 1,5 place
par logement ») **sourcé PAR ZONE** (`plu_le_tampon.yaml:79` etc.), exposé via
`ZoneRules.places_par_logement()` (`plu_rules.py:54`).

**À calibrer pour réintroduire un PARKING qui agit** : (a) `place_m2` **par
commune** (sourcé au règlement, pas 25 par défaut) ; (b) surface vs souterrain
(consomme l'emprise ou non) ; (c) brancher `places_par_logement × place_m2 ×
logements` sur l'emprise/SDP. Alors le champ pourra revenir.

## 4. TYPE de programme — fonctionnalité à CONSTRUIRE (arbitrage Vic A)

`TYPE` (logements / étudiant / bureaux) n'entrait dans **aucun** calcul de
`faisabilite_sens2` — champ décoratif, **retiré** (M133, `ProgrammeIn` +
`M22Programme.tsx`). En contrepartie, l'outil **annonce explicitement** qu'il porte
sur du **logement** (intro `M22Programme.tsx`).

Ce n'est PAS un champ mort à oublier mais une **fonctionnalité à construire** :
étendre la recherche au **commerce / activité / bureaux / résidence étudiante**.
Chantier : brancher des normes PAR destination — surface utile/unité, coefficient
utile→SDP, ratio de stationnement (ex. « stationnement ≥ 50 % SHON » pour le
commerce, `plu_cilaos.yaml:93`), destinations admises par zone (`ZoneRules.habitat`
/ tableaux d'affectation). Alors TYPE pilotera un calcul différencié — sourcé, pas
fabriqué — et le champ reviendra avec un sens.

## 5. Zone cascade grossière (corrigé côté outil, subsiste en amont)

`dryrun_cascade_results.detail` émet la **famille grossière** « U » (289 600
parcelles), jamais la sous-zone fine « Ua/Uc/… ». `resolve_zone('U')` retombe donc
sur l'estimation générique (he 9). **M133 a corrigé l'outil** en lisant la zone
fine depuis `parcel_zone_plu.zone_lib` (mono-zone). **Reste en amont** : la sortie
cascade elle-même est grossière — tout autre lecteur qui parse `detail` pour une
hauteur/gabarit héritera du même biais. Cascade = **hors périmètre** (moteur).

## 6. Emprise : test de SURFACE seulement, pas de FORME (B.3)

Le contrôle d'emprise ajouté (B.3, `modules.py`) teste que l'emprise du programme
au gabarit demandé **tient en surface** dans l'emprise bâtissable résiduelle
(algébriquement lié au plafond de gabarit B.2). Il ne teste **pas** la **forme** :
une parcelle en lanière étroite peut avoir l'aire suffisante mais pas la largeur
pour y poser un bâtiment. Ce test géométrique exige de rejouer le moteur
(`parcel_faisabilite`, `_EMPRISE`) — **hors périmètre outil**. À traiter le jour
où l'outil rejoue le moteur par parcelle (coûteux) ou consomme une empreinte
géométrique cachée.

## 7. Conflit de source de zone étiquette ↔ SDP (M133 vérif V2 — chiffre étranger NEUTRALISÉ)

Les deux sources de zone diffèrent :
- l'**étiquette** servie par « Par critères » = `parcel_zone_plu.zone_lib` (mono-zone,
  0 multi) ;
- la zone qui a **produit la SDP** du cache résiduel = celle du **centroïde**
  (`parcel_context`, `db.py:32-36` : polygone PLU le plus petit contenant le
  centroïde), qui est aussi celle de « Par parcelle » (sens1).

Pour une parcelle qui **chevauche deux zones** dans l'espace, les deux divergent.
Cas mesuré : `97422000CN1677` — centroïde = **Uc** (constructible, R+2, SDP 6071) ;
étiquette = **Nco** (naturelle, non constructible). Le cache sert donc une SDP issue
de **Uc** sous l'étiquette **Nco** — un **chiffre étranger sous une étiquette juste**
(la forme exacte du 4 m de M130-12) ; le flag « estimée » aggravait en donnant l'air
d'un traitement maîtrisé.

**Correctif M133 (local à l'outil, appliqué) :** le cache résiduel n'est POSITIF que
si la zone du centroïde est constructible. Donc si l'étiquette résout en NON
constructible (ou ne résout pas) alors que le résiduel est positif, la SDP est
étrangère → la parcelle **ne sert plus de SDP**, elle sort **« à instruire »** (même
sort que les parcelles sans étiquette — 0 servable). **Sans trancher** laquelle des
deux sources a raison (c'est l'inconnu). Portée mesurée (run servi `q_v10_m129`,
univers servable tier + résiduel>0 = 130 370) : **250 parcelles neutralisées**
(0,19 %) — étiquettes `N` (110), `A` (85), `Nco` (44)… Faible → appliqué sans stop.
Les zones GELÉES (Us/2AUc) ont, elles, un résiduel 0 : déjà écartées, gel intact.

### Les 38 non captées — un chiffre potentiellement étranger encore servi

Divergence résolue TOTALE (run servi `q_v10_m129`, univers servable 130 370) =
**288** parcelles, dont **250 neutralisées** par la règle ci-dessus (étiquette
non-constructible) et **38 NON captées**.

**Mécanisme des 38** : étiquette ET centroïde sont **tous deux CONSTRUCTIBLES**,
mais de **sous-zones différentes** (ex. étiquette `Uc` hé 16 / centroïde `Ud` hé 22 ;
`Ud` hé 15 / `Ug` hé 7 ; `U1`/`U2` ; couples mesurés : `Ud→Ug` ×7, `Uc→Ud`, `Ub→Uc`,
`Uav→Ua`…). La règle locale ne les voit pas (elle ne teste que la constructibilité
de l'étiquette, qui est vraie). Elles **servent donc aujourd'hui une SDP** bâtie sur
le résiduel de la zone du **centroïde** mais plafonnée sur le `niveaux_max` de
l'**étiquette** — le même vice que CN1677, en plus discret : chiffre d'une zone,
étiquette d'une autre.

**Borne haute de l'erreur** (calculable HORS runtime, mesure ponctuelle) : sur les
38, le rapport `niveaux_max(centroïde)/niveaux_max(étiquette)` va de 1,0 à **5,0**
(médiane 1,5). La SDP servie peut donc être **jusqu'à ~5× trop haute ou trop basse**
selon laquelle des deux sous-zones fait foi. 38 sur 130 370 (0,03 %) ne justifient
pas les ~60 s d'une requête spatiale de centroïde PAR PARCELLE au runtime — donc non
neutralisées pour l'instant.

**Correctif de fond (le seul vrai)** : l'**attribution de zone amont** — décider
quelle source fait foi (`parcel_zone_plu` vs polygone-centroïde `parcel_context`),
majorité de surface / centroïde / part U-AU dominante. Il règle d'un coup les 250 ET
les 38, et supprime la divergence à la racine plutôt que de la neutraliser en aval.

## 8. Piège `max(run_id)` — tri LEXICAL sur les labels de run (mécanisme, pas incident)

Les `run_id` / `run_label` sont des **chaînes** (`q_v9_m81`, `q_v10_m129`), pas des
entiers. Un `MAX(run_id)` (ou `ORDER BY run_id DESC LIMIT 1`, ou un `sorted()` Python)
fait un tri **LEXICOGRAPHIQUE** : `'q_v9_m81' > 'q_v10_m129'` car le caractère `'9'`
est supérieur à `'1'` à la 5ᵉ position. **`MAX(run_id)` rend donc `q_v9_m81`, PAS le
run le plus récent `q_v10_m129`.**

Le run SERVI ne se lit JAMAIS par `MAX(run_id)`. Il se lit par le point de vérité :
- SQL/analyse : la constante `Q_A_RUN_LABEL` (`scoring/score_v_constants.py`) ;
- scoring v2 : `_score_v2_run_id()` (`api/app.py`, exposé `_v2run` dans `modules.py`).

**Où ça a déjà mordu (incident M133)** : des mesures QA en SQL direct joignaient
`parcel_p_score_v2 ... run_id = (SELECT MAX(run_id))` → elles portaient sur
`q_v9_m81` au lieu du run servi. D'où un C2 faux (`8479→7478` au lieu de
`23812→19342`) et un comptage de divergence sur le mauvais univers. Le CODE de
l'outil était juste (l'endpoint passe par `_v2run`) — seul le harnais de mesure
était piégé.

**Le mécanisme rejouera** partout où un run le plus récent est cherché par tri :
requête QA, script d'analyse, futur audit, dashboard. Règle : **ne jamais** dériver
le run servi d'un `MAX`/`ORDER BY DESC` sur le label ; toujours passer par
`Q_A_RUN_LABEL` / `_score_v2_run_id`. (Correctif de fond éventuel, hors périmètre :
un `run_seq` entier monotone, ou un flag `is_served`, pour qu'un tri redevienne sûr.)
