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

## 4. Champ TYPE retiré (contrôle 8)

`TYPE` (logements / étudiant / bureaux) n'entrait dans **aucun** calcul de
`faisabilite_sens2` — champ décoratif, **retiré** (M133, `ProgrammeIn` +
`M22Programme.tsx`). **À calibrer pour le réintroduire** : normes **par type**
(surface utile/unité, coefficient circulations, ratio stationnement) — non
fabriquées ici. Tant qu'elles n'existent pas, un sélecteur de type ne ferait que
promettre une différence que le calcul ne produit pas.

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
