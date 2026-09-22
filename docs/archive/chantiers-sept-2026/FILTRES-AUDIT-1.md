# FILTRES-AUDIT-1 — Chaque filtre filtre-t-il ce qu'il annonce ?

**Branche** `feat/filtres-audit-1` depuis `main` HEAD `15cffe08`. Session dédiée API `:8105` / front `:5305`.
**Lecture seule** — aucune correction, aucun regard sur le scoring/classement. Un commit (ce rapport).
Moteur servi : **`q_v11_m137`** (`config/served_manifest.json`). Base réelle `labuse` (431 663 parcelles).

## Les trois chiffres

| | |
|---|---|
| **N filtres** (panneau Carte › Filtres, rendus à l'écran) | **14** |
| **M qui lisent le même moteur que la fiche** | **14 / 14** |
| **K dont le test parcelle échoue** | **1** (Surface — côté borne basse) |

> Le panneau Filtres actuel n'a **plus de section « avancés »** : les tiroirs pédagogiques, la
> section « Propriétaire » (KF1) et la section « Le bien » ont été retirés du front (`FiltreLabuse.tsx`,
> décisions Vic M55-G / RETOURS-1 / FILTRE). Les « filtres avancés » du mandat = les prédicats
> backend conservés **sans contrôle au panneau** — traités dans les listes plus bas.

## Les deux témoins

| | Témoin A `97410000AN0347` | Témoin B `97406000AM0643` |
|---|---|---|
| Commune | Saint-Benoît | La Plaine-des-Palmistes |
| Surface cadastre | 4 500,50 m² (**fiche affiche « 4 501 m² »**) | 1 307 m² |
| Zone PLU (dominante surface) | **N** (exacte `N`) | **U** (exacte `UC`) |
| État du sol | terrain **nu** (emprise inconnue < 5 %) | terrain **bâti** (emprise 62 %) |
| SDP résiduelle | 0 (cause `zone_non_constructible:N`) | 143 m² |
| Propriétaire | **public** — Commune de Saint-Benoît (groupe DGFiP 4) | personne physique (absente `parcelle_personne_morale`) |
| ZFANG / FRR | renforcé / partie | renforcé / totalité |
| Tier servi (q_v11_m137) | **écartée** (`d.status = exclue`, étage 0) | `a_creuser` (retenue) |

A est délibérément une parcelle **écartée** (elle n'apparaît qu'en *tri factuel*, pas dans la vue
d'analyse) ; B est une parcelle **simple retenue**. Preuves reproductibles :
`captures/filtres-audit1/preuve-filtre-live.txt` (17 requêtes `/filtre` réelles).

---

## Tableau par filtre

Colonnes : **libellé exact** · **id registre / source lue** · **prédicat SQL** (`_q_v2_where`, `app.py`) ·
**même moteur que la fiche** · **test parcelle** (valeur de la fiche → ressort ; à côté → disparaît) ·
**surfaces qui le consomment**.

| # | Libellé panneau | id registre · table.colonne | Prédicat exécuté | = fiche ? | Test parcelle | Consommé par |
|---|---|---|---|:--:|:--:|---|
| 1 | **1 · Communes** (24 codes postaux) | *(pas de chiffre-registre)* · `parcels.commune` | `p.commune = ANY(:communes)` | oui | ✅ A=Saint-Benoît ressort / Saint-Pierre disparaît | carte, liste, compteur, veille (`cs`), projet |
| 2 | **Surface parcelle** min–max (m²) | `surface_m2` (« cadastre ») · `parcels.surface_m2` | `p.surface_m2 >= :min` / `<= :max` | oui (même colonne) | ❌ **min=4501 (=fiche) → A disparaît** ; min=4500 → ressort | carte, liste, compteur, veille (`smin/smax`), projet |
| 3 | **Zonage** — famille (U/AU/A/N) | `zone_plu` · `parcel_zone_plu.zone_fam` | `EXISTS zone_fam = ANY(upper(:zonage))` | oui (zone **dominante par surface**, `parcel_zone_plu`, la même que `zone_dominante` de la fiche) | ✅ A fam=N ressort / U disparaît | carte, liste, compteur, veille (`zf`), projet |
| 4 | **Zonage** — zone exacte (UA, UC, 2AU…) | `zone_plu_libelle` · `parcel_zone_plu.zone_filtre` | `EXISTS zone_filtre = ANY(upper(:zone_plu))` | oui (même table) | ✅ B exacte=UC ressort / UB disparaît | carte, liste, compteur, veille (`zpx`), projet |
| 5 | **État du sol** — Terrain nu / bâti | *(prédicat dérivé, pas de chiffre-registre)* · `parcel_residuel.taux_emprise_pct` | nu = `NOT EXISTS emprise ≥ 5 %` ; bâti = `EXISTS emprise ≥ 5 %` | oui (même emprise que la fiche) | ✅ A=nu ressort / bâti disparaît ; B=bâti ressort / nu disparaît | carte, liste, compteur, veille (`es`), projet |
| 6 | **ZFANG — zone franche** (Renforcée / Standard) | `zfang_regime_commune` · `territoire_fiscal_commune.zfang_regime` (jointure INSEE = `left(idu,5)`) | `EXISTS tfc.zfang_regime = ANY(:zfang)` | oui (même source que carte + fiche commune) | ✅ A=renforce ressort / standard → 0 | carte, liste, compteur — **PAS veille/URL/badge** (voir liste D) |
| 7 | **FRR — ruralités** (Totalité / En partie / Hors) | `frr_classement_commune` · `territoire_fiscal_commune.frr_classement` | `EXISTS tfc.frr_classement = ANY(:frr)` | oui (même source) | ✅ A=partie ressort / hors → 0 | carte, liste, compteur — **PAS veille/URL/badge** (voir liste D) |
| 8 | **3 · Signaux — Détenu par une société** (`pm_privee`) | *(dérivé)* · `parcelle_personne_morale.groupe` | `EXISTS pmm.groupe = 0` (société **privée**) | oui (même table que propriétaire §1 de la fiche) | ✅ A public → n'apparaît PAS (correct) ; 33 921 privées à l'île | carte, liste, compteur, veille (`sv`), projet |
| 9 | **Signaux — Procédure collective** (`procedure`) | *(dérivé)* · `bodacc_procedures` via `siren` | `EXISTS pmm JOIN bodacc_procedures ON siren` | oui | (aucun témoin porteur) | carte, liste, compteur, veille (`sv`), projet |
| 10 | **Signaux — Permis actif** (`permis_actif`) | *(dérivé)* · `parcel_signaux_vie.signal` | `EXISTS sv.signal = 'permis_actif'` | oui (table pré-calculée `build-signaux-vie`) | (aucun témoin) ; 7 002 à l'île | carte, liste, compteur, veille, projet |
| 11 | **Signaux — Permis abandonné** (`permis_caduc`) | *(dérivé)* · `pc_caducs` | `EXISTS pc_caducs` | oui | (aucun témoin) ; 2 161 à l'île | carte, liste, compteur, veille, projet |
| 12 | **Signaux — Friche recensée** (`friche`) | *(dérivé)* · `parcel_signaux_vie.signal` | `EXISTS sv.signal = 'friche'` | oui | (aucun témoin) ; 1 801 à l'île | carte, liste, compteur, veille, projet |
| 13 | **Signaux — Sortie de défisc** (`defisc`) | *(dérivé)* · `defisc_fenetres.fenetre_active` | `EXISTS defisc_fenetres AND fenetre_active` | oui | (aucun témoin) ; 797 à l'île | carte, liste, compteur, veille, projet |
| 14 | **Signaux — Succession** (`succession`) | *(dérivé)* · `parcel_veille_succession.parcelle_id` | `EXISTS parcel_veille_succession` | oui | (aucun témoin) ; 7 129 à l'île | carte, liste, compteur, veille, projet |

**Zone = dominante ou centroïde ?** → **dominante par surface** (`parcel_zone_plu`, une ligne par
parcelle, PK `idu`, bâtie par `tiles.build_parcel_zone_plu`). La fiche lit la **même** table
(`faisabilite/zone_servie.py::zone_dominante` — « la MÊME que l'écran, jamais deux vérités »). Le
drapeau *à-cheval* (parcelle à cheval sur deux zones) est identique côté fiche et côté filtre.
**Surface = cadastre ou géométrie ?** → cadastre (`parcels.surface_m2`), jamais la géométrie.
**Propriétaire = même id que §1 ?** → oui, `parcelle_personne_morale` clé `idu`, la table du bloc
propriétaire de la fiche.

---

## Combinaisons

- **ET entre filtres**, **OU à l'intérieur d'un groupe** à choix multiple (tiers, signaux, état du
  sol, familles de zonage, zones exactes). C'est **dit** au panneau : « une parcelle correspond si
  **au moins un** des signaux cochés est présent » (§3) ; le sous-titre Communes dit « tout coché =
  toute l'île ». Vérifié dans `_q_v2_where` (chaque groupe = `(… OR …)`, joints par `AND`).
- **Un filtre vide ne filtre pas** : `filterParams` (front) n'émet que les champs non vides et
  `_q_v2_where` n'ajoute une clause que si le paramètre est présent. `communes` vide = toute l'île.
- **Zonage famille (`zonage`) et zone exacte (`zone_plu`) se cumulent en ET** (verrou
  `tests/test_filtres_cumul.py`). L'UI (ZoneSelector) les rend **mutuellement exclusifs** pour éviter
  un ET inter-familles qui renverrait 0 en silence ; un deep-link peut porter les deux (intersection
  assumée).

## Où va le résultat — le même ensemble partout ?

Un **seul** point d'entrée : `FiltreCriteres.where()` → `_q_v2_where`, partagé par la carte
(`getFiltreIdus`), la liste (`_q_v2_list`), le compteur (`getFiltreCount`), le cadrage projet
(`_run_cadrage`) et la veille (`parcelles_matchant_hash`). **Le compteur affiché = le nombre réel** :
front SB+nu = **10 991** == `/filtre` SB+nu (jeu de tiers front complet) = **10 991** (preuve jointe).
Seule **réserve** : ZFANG/FRR filtrent la carte/le compteur mais **ne suivent pas** dans l'URL /
« Mes vues » / la veille / le badge « Filtres (N) » (liste D).

---

## Les quatre listes

### A. Filtres qui divergent de la fiche
1. **Surface parcelle (borne min).** `parcels.surface_m2` est un **flottant** (A = 4 500,50 m²) ; la
   fiche l'**arrondit** à l'affichage (`fmtM2`→`fmtInt`=`Math.round` → « 4 501 m² »). Le filtre
   compare le **brut** : `4500.50 >= 4501` est faux → **régler la surface minimale sur la valeur lue
   sur la fiche fait DISPARAÎTRE la parcelle.** Prouvé live (ligne 8 de la preuve). Même famille de
   piège pour les parcelles ≥ 1 ha, que la fiche affiche en hectares (« 2,50 ha ») — aucune valeur m²
   n'est même dérivable pour la saisie. *(Constat seul — aucune correction.)*

> Les 13 autres filtres passent le test parcelle **exactement** (valeur de la fiche → ressort ;
> valeur adjacente → disparaît), sur les deux témoins.

### B. Filtres morts (prédicat backend sans aucun appelant : ni panneau, ni URL/veille, ni cadrage projet)
Atteignables **uniquement** par un `GET /filtre?…` fabriqué à la main :
1. **`defisc_active`** — doublon mort du signal `defisc` (même table `defisc_fenetres`).
2. **`pc_caduc`** — doublon mort du signal `permis_caduc` (même table `pc_caducs`).
3. **`marge_min`** (`score_e.marge_estimee`) — jamais dans `filterParams`, ni le hash, ni `_CADRAGE_MAP`, ni le type `Filters`.
4. **Branches de signaux `nu_pm` et `cession`** de `_SIG_SQL` — retirées de `SIGNAUX_KEYS` **et** de
   `SIGNAUX_VALIDES` (`filtersFromHash` les jette) : plus aucune entrée UI ni hash.

### C. Filtres sans id (de registre)
Prédicats dérivés qui ne lisent **pas** un chiffre-registre nommé (booléen/catégorie calculé sur une
table), par opposition aux filtres adossés à un chiffre-registre (Surface `surface_m2`, Zonage
`zone_plu`, ZFANG `zfang_regime_commune`, FRR `frr_classement_commune`) :
- **État du sol** (dérivé de `parcel_residuel.taux_emprise_pct`, seuil 5 %).
- **Les 7 Signaux de vie** (chacun un `EXISTS` sur une table d'événements).
- **Communes** (égalité brute `parcels.commune`).

### D. Dimensions de veille non évaluées
Le constat CONNEXIONS-1 (« 35 dimensions sérialisées, 5 évaluées ») est **périmé** : `filtre_from_hash`
mappe désormais ~toutes les clés du hash → `FiltreCriteres.where()`, **le même moteur que la carte**
(`parcelles_matchant_hash`, appelé par la notif de veille `events.py:621`). Une veille créée depuis les
filtres réévalue donc les **mêmes prédicats**. Restent **trois angles morts** :
1. **ZFANG / FRR** — jamais sérialisés (`filtersToHash` n'a pas de clé `zfang`/`frr`, cf. `filters.ts`
   `CSV_KEYS`). Une veille (ou une « Mes vues », ou un lien partagé) créée avec ZFANG/FRR cochés les
   **perd silencieusement**. **Aggravant** : `countActiveFilters` **ne les compte pas** non plus → si
   ZFANG/FRR sont les **seuls** filtres posés, le compteur vivant **et** le bloc « Créer une veille »
   (tous deux sous `nActifs > 0`) **ne s'affichent pas**. (Sur la carte le prédicat marche : preuve
   `zfang=standard → 0`, `frr=totalite → 0`.)
2. **`mm` (multiplicateur min)** — **appliqué** par le matcher (`filtre_from_hash` a une branche
   `mult_min` explicite) mais **absent** de `DIMENSIONS_VEILLE_EVALUABLES` → l'aperçu
   « cette veille surveille… » le range en **« non retenu (non évaluable) »** alors qu'il **est**
   évalué. Étiquetage à contre-emploi (l'inverse du bug historique).
3. Clés retirées de l'UI (`nu_pm`, `cession`, `ev` legacy) — correctement filtrées par
   `filtersFromHash` (jamais un filtre fantôme invisible).

---

## Points connus, tranchés

- **Filtres retirés du front, backend conservé.** La section **Propriétaire** (`pm_denom`, `pm_siren`,
  `pm_forme`, `pm_ape`, `pm_dirig_min/max`) et la section **Le bien** (`droits_residuels`,
  `proprietaire_type='public'`) ne sont plus rendues.
  - `droits_residuels`, `proprietaire_type`, `etat_societe`, `copro`, `constructibilite`,
    `capacite_min`, `sous_densite`, `renouvellement`, `npnru`, `adresse_absente`, `sdp_min/max`,
    `mult_min`, `rang_max`, `budget/charge/prix_marche/ca/mode_b`, `marche_fiable`, `evenement`,
    `veille`, `hors_copro`, `personne_morale`, `flags/flags_exclus`, `division_or` restent
    **appelables** — par la **veille** (clés `_HASH_*`) et/ou le **cadrage projet** (`_CADRAGE_MAP`).
    `division_or` n'est atteignable **que** par le cadrage projet ; `pm_*` que par la veille/URL.
  - Donc « morts » au sens strict = liste B seulement ; les autres sont **dormants mais vivants**
    par une autre surface (documenté ici pour lever l'ambiguïté).
- **Filtres lisant une donnée calibrée (zone, ZFANG, FRR).** Le zonage lit `parcel_zone_plu` (zone
  **dominante par surface**), la table servie par `tiles.build_parcel_zone_plu`, que
  `faisabilite/zone_servie.py` réutilise pour la fiche — **une seule vérité**. Le filtre familles plie
  la casse en PG (`upper()`), comme la table (accents locale C préservés) — pas de 0 silencieux sur
  « NDé » (Cilaos). ZFANG/FRR lisent `territoire_fiscal_commune`, la table qui peint la carte
  (`dispositifs.py`) et alimente la fiche commune — jointure par l'INSEE `left(idu,5)`.

## Preuve

`captures/filtres-audit1/` :
- `preuve-filtre-live.txt` — 17 requêtes `/filtre` réelles (moteur servi), une par ligne du test
  parcelle, sur les deux témoins (attendu vs obtenu).
- `preuve-panneau-temoinA.json` — état DOM du panneau réglé sur le témoin A (hash, compteur vivant).

> **Captures pixel** : l'aperçu image passe par le pont MCP plafonné à 5 s ; la carte MapLibre (WebGL,
> markers repositionnés à chaque frame) empêche la stabilisation → **capture pixel indisponible dans
> cette session** (limite environnementale déjà consignée COUCHES-1 / DASHBOARD-2). La preuve est donc
> portée par les requêtes `/filtre` réelles (reproductibles, moteur servi) et l'état DOM lu en direct —
> le compteur du panneau (10 991) est vérifié **égal** au SQL. Pixels à shooter par Vic si requis.

## Verdict

Tous les filtres rendus lisent **la source même de la fiche** (14/14) ; 13/14 filtrent **exactement**
ce qu'ils annoncent, sur les deux témoins. Le seul écart de comportement (K=1) est l'**arrondi de la
Surface** (borne min sur valeur affichée). L'anomalie structurante n'est pas un mauvais prédicat mais
une **demi-connexion de ZFANG/FRR** : ils filtrent le live mais échappent au hash (persistance, veille,
badge, compteur-si-seuls). Aucune correction apportée (lecture seule).
