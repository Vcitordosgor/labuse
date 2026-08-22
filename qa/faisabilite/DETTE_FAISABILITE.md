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

**À faire (mandat data)** : recalculer `parcel_residuel` après chaque bascule PLU
(lier au run servi, ou exposer une péremption). **Ne touche pas** l'outil.

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

## 7. Divergence de zone sens1 ↔ sens2 sur parcelle multi-zones (M133 vérif V2)

Les deux onglets lisent la zone à deux endroits DIFFÉRENTS :
- **sens1** (« Par parcelle », `parcel_faisabilite` → `parcel_context`,
  `db.py:32-36`) : zone du polygone PLU le PLUS PETIT contenant le **centroïde**
  (`ST_Contains` + `ORDER BY ST_Area(z.geom) ASC LIMIT 1`).
- **sens2** (« Par critères », M133) : `parcel_zone_plu.zone_lib` (une ligne par
  parcelle — table mono-zone, 0 multi).

Pour une parcelle qui **chevauche deux zones** dans l'espace, les deux sources
peuvent DIVERGER. Cas mesuré : `97422000CN1677` — sens1 (centroïde) = **Uc**
(constructible, R+2, SDP brute 6071) ; `parcel_zone_plu` = **Nco** (naturelle, non
constructible). sens2 l'affiche donc « **Nco · estimée · 5900 m²** » : un chiffre de
SDP issu de la lecture **Uc** (le cache résiduel vient du chemin sens1), servi sous
l'étiquette **Nco**. Le flag « estimée » est correct (Nco non calibrée) mais la
parcelle est un **conflit de source de zone**.

À trancher (amont, hors périmètre outil) : quelle source fait foi pour
l'attribution mono-zone — majorité de surface, centroïde, ou part U/AU dominante ?
Consigné, **non corrigé** (mandat : « tout écart = divergence à remonter »). Sur la
capture, **0** parcelle à zone NULL et 1/200 « estimée » à Le Tampon (ce CN1677).
