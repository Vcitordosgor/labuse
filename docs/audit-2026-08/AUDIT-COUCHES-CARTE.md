# AUDIT — Couches de la barre latérale carte

**Date** : 2026-08-24 · **Branche** : `audit/couches-carte` · **Type** : audit seul (aucune modification de code, requêtes Postgres en lecture uniquement).
**Périmètre** : les couches togglables du panneau « Couches » de la carte (tuyauterie + donnée, pas le design).
**Méthode** : registre front (source de vérité) → sources/layers MapLibre → endpoints → tables Postgres, croisé avec la base locale (`SELECT` seuls : comptes, `max(created_at)`, `ST_IsValid`, jointures `data_sources`).

> App en cours d'exécution (uvicorn:8000 + vite) laissée intacte ; aucun process tué, aucun re-run, aucune écriture.

---

## 0. Nombre de couches — **23, pas ~21**

La source de vérité est `LayerToggles` / `layers` dans `frontend/src/store/useApp.ts:11` (défaut ligne 535). Elle déclare **23 interrupteurs**, tous rendus et tous branchés à un endpoint ou aux tuiles :

`zonage · zonage_parcelle · parcelles · ppr · parc · znieff · limites · anru · equipements · equipements_bpe · communes · cinquante_pas · alea_inondation · alea_mvt · transport · lignes_ht · axes · renouv · couleurs_verdict · qpv · tva_primo · zfang · frr`

`LAYER_INFO` (`lib/layers.ts:60`) porte exactement les 23 mêmes clés. Aucun toggle orphelin (chaque clé a une couche MapLibre + un flux), aucune couche rendue sans toggle. L'écart avec « ~21 » vient de deux interrupteurs qui sont des **modes** plus que des couches : `zonage_parcelle` (colore la couche Parcelles, qu'il auto-active) et `couleurs_verdict` (palette des tiers sur Parcelles) — aucun des deux n'ajoute une source propre.

---

## 1. Tableau des couches

Fraîcheur : **affichée** = ce que voit l'utilisateur (badge « intégré le… » = `max(created_at)` d'ingestion, OU millésime en dur dans le texte « i », OU rien) ; **réelle base** = `max(created_at)` de la table ; **amont** = `data_sources.source_millesime`.

| # | Toggle | Kind / table servie | Source amont | Fraîch. affichée | Réelle base (ingest) | Amont (millésime) | Verdict | Constat |
|---|--------|--------------------|--------------|------------------|----------------------|-------------------|---------|---------|
| 1 | zonage | `plu_gpu_zone` (5 845) · + MVT `mvt_overlays` | GPU/PLU API Carto | — (statique) | 2026-07-03 | GPU/PLU par commune | ✓ | 23/24 communes (SP RNU géré). Voie MVT dépend de `build-mvt`. |
| 2 | zonage_parcelle | tuiles `mvt_parcels.zone_fam` | (dérivé cadastre) | — | (run servi) | — | ✓ | Mode : auto-active Parcelles. Repli île honnête si `zone_fam` absent. |
| 3 | parcelles | `mvt_parcels` / `parcels` (431 663) | DGFiP | — | (run servi) | cadastre | ✓ | 0 géométrie invalide, 0 geom NULL. Couche de travail. |
| 4 | ppr | `ppr` (164) · + MVT | DEAL PPR/aléas | — | 2026-07-03 | PPR/PPRL 2011–2026 | ✓ | 24 communes. Voie MVT dépend de `build-mvt`. |
| 5 | parc | `parc_national` (3) | Parc National INPN | « 2021 » (en dur, « i ») | 2026-06-28 | millésime 2021 | ✓ | En dur mais **conforme** à l'amont. |
| 6 | znieff | `znieff` (162) | INPN/MNHN | « 2025 » (en dur) | 2026-08-21 | màj 29/08/2025 | ✓ | Conforme amont. |
| 7 | limites | contour `parcels` | DGFiP | — | (run servi) | cadastre | ✓ | Trait seul, toute l'île. |
| 8 | anru | `anru` (8) | DEAL/ANCT | « intégré le… » (dyn.) | 2026-07-08 | NPNRU gén. 2024 | ✓ | 8 emprises / 6 communes = exact en base. Toast si vide. |
| 9 | equipements | `amenite` (15 214, **tcsp+sport filtrés serveur** → ~8 750 servis) | OSM/Overpass | — | 2026-08-10 | OSM (live) | ✓ | Sous le plafond 20 000 ; toast tronqué présent (jamais atteint). |
| 10 | equipements_bpe | `amenite_bpe` (**35 546**) | BPE INSEE | « 36 821 » (en dur) | 2026-08-21 | millésime 2025 | ⚠ | **Tronqué 20 000/35 546 en île, SANS toast** + compte « i » faux. Voir §2.1. |
| 11 | communes | frontières 24 communes | IGN geo.api.gouv | — | — | — | ✓ | Repérage. |
| 12 | cinquante_pas | `cinquante_pas` (163) | 50 pas DEAL | — | 2026-07-10 | cadastre 1877 (géoréf.) | ✓ | Île entière (commune NULL). Toast « sans littoral ». |
| 13 | alea_inondation | `georisque_alea`/inondation (76) | DEAL aléas | « intégré le… » (dyn.) | 2026-07-05 | (cf. PPR) | ✓ | 24 communes. Fetch partagé avec 14. |
| 14 | alea_mvt | `georisque_alea`/mvt (917) | DEAL aléas | « intégré le… » (dyn.) | 2026-07-05 | (cf. PPR) | ✓ | 23 communes (SD non couvert) = exact base, dit dans « i ». |
| 15 | transport | `transport_ligne` (300) + `transport_arret` (9 956) + `telepherique` (7) | GTFS 7 réseaux · OSM | « GTFS · … » (dyn.) | 2026-08-17 | 7 jeux PAN → 2026-08-17 | ⚠ | Sain, mais le « i » **revendique les pôles d'échange** qui sont câblés sur *Axes*. Voir §2.4. |
| 16 | lignes_ht | `ligne_ht` (48) | BD TOPO IGN | « BD TOPO · … » (dyn.) | 2026-08-17 | BD TOPO V3 (édition non pinée) | ✓ | Aériennes seules, dit dans « i ». |
| 17 | axes | `axe_structurant` (3 481) + `pole_echange` (61) | BD TOPO IGN · OSM | « BD TOPO · … » (dyn.) | 2026-08-17 | BD TOPO V3 | ⚠ | Porte les pôles (non documentés dans son « i ») ; **19/61 pôles sans source**. Voir §2.4. |
| 18 | renouv | `parcel_renouvellement` (`/renouvellement.geojson`) | Analyse LABUSE | « maj » = `computed_at` (dyn.) | (run servi) | — (dérivé) | ✓ | Top-rangs, toast de troncature honnête. |
| 19 | couleurs_verdict | palette tiers sur `parcels` | (run servi) | — | (run servi) | — | ✓ | Mode : peint tout le classement. Pas de source propre. |
| 20 | qpv | `qpv` (57) | QPV 2024 ANCT | « intégré le… » (dyn.) | 2026-07-05 | génération 2024 | ✓ | 57 quartiers / 13 communes = exact base + « i ». Toast si vide. |
| 21 | tva_primo | `tva_primo` (13) | **— (dérivé QPV+500 m)** | « Estimé » (« i ») | 2026-08-20 | — | ✓ | Sans source amont mais **honnêtement déclaré Dérivé/Estimé**. |
| 22 | zfang | `zfang` (24) | — (aucune ligne source) | texte légal en dur | 2026-08-20 | — | ⚠ | `data_source_id` NULL → millésime non catalogué. Voir §2.3. |
| 23 | frr | `frr` (23) | — (aucune ligne source) | texte légal en dur | 2026-08-20 | — | ⚠ | `data_source_id` NULL → millésime non catalogué. Voir §2.3. |

**Santé géométrique (toutes couches)** : `ST_IsValid` = **0 invalide** sur les 45 kinds de `spatial_layers` ET sur `parcels` (431 663) ; `geom` en `NOT NULL`. Aucune géométrie cassée servie.

---

## 2. Détail (là où il y a quelque chose à dire)

### 2.1 — `equipements_bpe` : troncature silencieuse + compte affiché faux ⚠ (le point le plus sérieux)

- **Troncature muette.** `MapView.tsx:502` appelle `getMapLayer('amenite_bpe', 20_000)`. La table `amenite_bpe` compte **35 546** lignes (24 communes) ; l'endpoint `/map/layers.geojson` plafonne à `le=20000`. En **vue île**, ~15 500 points BPE disparaissent. Or le garde-fou « no-silent-caps » (`MapView.tsx:978`) ne teste QUE la couche OSM `amenite` — **aucun toast pour la BPE**. Le commentaire `MapView.tsx:501` reconnaît lui-même « 35 546 en base → tronqué en vue île » sans en avertir l'utilisateur. La couche est en outre re-filtrée par domaine A→G *côté client*, après le plafond, donc certains domaines sont sous-représentés sans le dire. En vue commune, chaque commune reste < 20 000 → la troncature ne mord qu'à l'échelle île.
- **Compte affiché faux.** `LAYER_INFO.equipements_bpe` (`lib/layers.ts:104`) annonce « **36 821** équipements géolocalisés » ; la base en sert **35 546** (Δ ≈ 1 275). Nombre en dur, divergent de la table.
- Le millésime « 2025 » et l'amont (`data_sources` #20, BPE 2025, `last_sync 2026-08-21`) concordent, eux.

### 2.2 — Fraîcheur servie = date d'ingestion, pas millésime amont ⚠ (transversal)

`/map/layers.geojson` renvoie `millesime_integration = max(created_at)` (`app.py:3334`), c.-à-d. la date d'**INSERT** en base, consommée par `Legend.tsx:55` (`mill()`) pour le badge « intégré le JJ/MM/AAAA » (aléas, transport, HT, axes, qpv, anru). C'est honnête dans le mot (« intégré le »), mais ce **n'est pas la date de la source amont** que réclame la doctrine. Le vrai millésime amont existe (`data_sources.source_millesime`) mais n'est **pas surfacé par couche** — il ne vit que dans la page `/sources`. Résultat : provenance de fraîcheur **hétérogène** sur les 23 — badge « intégré le » (ingestion) pour les unes, millésime en dur dans le « i » pour d'autres (parc 2021, znieff 2025, BPE 2025, qpv 2024), rien pour d'autres. Aucun faux positif (les valeurs en dur vérifiées concordent avec l'amont), mais risque de dérive : un « i » en dur ne suivra pas une mise à jour de source.

### 2.3 — `zfang` / `frr` : couches sans source amont ⚠

Toutes les lignes de `zfang` (24) et `frr` (23) ont `data_source_id = NULL` (vérifié en base). Leurs « i » citent des textes légaux datés (décret 2026-421 du 29/05/2026 ; art. 44 quindecies A CGI) mais **aucune ligne `data_sources`** ne les porte → leur millésime est en dur et **absent du catalogue `/sources`** ; la doctrine « fraîcheur = date de la source amont » n'a rien où s'accrocher. Ingérées le 2026-08-20, elles sont postérieures au backfill de rattachement des sources (M-H). À distinguer de `tva_primo` (aussi `data_source_id` NULL) qui, lui, est **correctement déclaré Dérivé/Estimé** dans son « i » : conforme à la doctrine.

### 2.4 — Pôles d'échange : câblage sur *Axes*, documentés sur *Transport* ⚠

`pole_echange` est rendu sous l'interrupteur **Axes** : `MapView.tsx:1136` (`ov-pole` visibilité = `layers.axes`, commentaire « M137-X — pôles sur Axes ») et `MapView.tsx:511` / `Legend.tsx:46` (`enabled: layers.axes`). Or le « i » de **transport** (`lib/layers.ts:110`) décrit toujours « les pôles d'échange (gares routières…) » comme faisant partie de Transport, tandis que le « i » d'**axes** (`:111`) ne les mentionne pas. Un utilisateur qui active Transport pour voir les pôles ne les verra pas ; qui active Axes voit des pôles non documentés. Incohérence texte/câblage (pas un bug de donnée). Par ailleurs **19 des 61** `pole_echange` ont `data_source_id` NULL (42 sourcés OSM/GTFS).

### 2.5 — Cycle de vie au toggle off (précision, RAS)

Contrairement à une lecture rapide, le toggle off **ne démonte pas** la couche : toutes les couches d'overlay sont ajoutées une fois à l'init (visibilité `none`) puis basculées par `setLayoutProperty(..., 'visibility', …)` (`MapView.tsx:216`), et le flux est coupé par `enabled: layers.<clé>` (react-query GC les données). Pattern **sain et sans fuite** — mais « démontage » = masquage, pas `removeLayer/removeSource`. Aucun overlay fantôme observé dans le code (visibilité pilotée par un unique effet, `MapView.tsx:1088+`).

### 2.6 — Doubles voies zonage/PPR + dépendance rebuild (contexte, RAS)

`zonage` et `ppr` sont servis en **GeoJSON** (`/map/layers.geojson`, mode commune) ET en **MVT** (`mvt_overlays`, mode île). `mvt_overlays` est un `CREATE TABLE AS SELECT … FROM spatial_layers WHERE kind IN ('plu_gpu_zone','ppr')` : même donnée source, pas un doublon de donnée. À noter : la voie MVT (comme `mvt_parcels`) est **matérialisée** — sa fraîcheur dépend d'un `labuse build-mvt` rejoué après tout rafraîchissement de `spatial_layers`. Risque de péremption silencieuse partagé, non spécifique aux couches.

---

## 3. Classement des problèmes par gravité

| Gravité | # | Problème | Impact |
|---------|---|----------|--------|
| **Moyenne** | P1 | `equipements_bpe` tronqué 20 000/35 546 en vue île **sans toast** (§2.1) | Points manquants sans avertissement = mensonge visuel (viole la règle no-silent-caps maison). |
| **Faible-moyenne** | P2 | Compte « i » BPE « 36 821 » vs 35 546 servis (§2.1) | Chiffre en dur faux affiché au client. |
| **Faible** | P3 | Fraîcheur par couche = date d'ingestion, pas millésime amont ; provenance hétérogène (§2.2) | Pas de faux positif aujourd'hui, mais dérive possible des « i » en dur. |
| **Faible** | P4 | `zfang` / `frr` sans `data_source_id` (§2.3) | Millésime hors catalogue `/sources`, non rattaché à l'amont. |
| **Faible** | P5 | Pôles d'échange sur *Axes* mais décrits sur *Transport* ; 19/61 sans source (§2.4) | Incohérence texte/câblage ; provenance partielle. |

Aucune couche cassée, aucune géométrie invalide, aucun toggle orphelin, aucune table morte servie, aucun run périmé détecté. Les comptes servis concordent avec les « i » (anru 8/6, qpv 57/13, alea_mvt 23 comm, parc 3) — **sauf** le compte BPE (P2).

---

## 4. Correctifs candidats à mandater (non faits)

1. **P1 — Toast de troncature BPE.** Dupliquer le garde `MapView.tsx:978` pour `equipBpe` (`equipBpe.data.features.length >= 20_000` → toast). Ou, plus propre : relever le plafond BPE côté endpoint, ou paginer/filtrer par domaine *avant* le plafond (fetch par domaine actif).
2. **P2 — Corriger le compte BPE.** Remplacer « 36 821 » (`lib/layers.ts:104`) par la valeur réelle (35 546), ou mieux, la dériver dynamiquement (compte servi) au lieu d'un nombre en dur.
3. **P3 — Surfacer le millésime amont par couche.** Faire renvoyer par `/map/layers.geojson` le `data_sources.source_millesime` (en plus du `max(created_at)`), et l'afficher dans la légende à la place / à côté de « intégré le… » ; retirer les millésimes en dur des « i » au profit de la valeur sourcée (aligne les couches sur la doctrine `/sources`).
4. **P4 — Rattacher `zfang` / `frr` à une source.** Créer les lignes `data_sources` (textes légaux / Région ODS) et back-fill `data_source_id`, comme la garde M-H l'a fait pour les 6 kinds orphelins précédents ; sinon les marquer explicitement « Dérivé » comme `tva_primo`.
5. **P5 — Réconcilier pôles d'échange.** Décider : soit déplacer la phrase « pôles d'échange » du « i » de *transport* vers celui d'*axes* (aligner le texte sur le câblage M137-X), soit re-câbler les pôles sur *transport*. Et rattacher/expliquer les 19 pôles sans `data_source_id`.

---

## 5. Synthèse

**23 couches** (registre `LayerToggles`), toutes branchées et rendues. Tuyauterie globalement saine : géométries 100 % valides, comptes cohérents, toggles sans orphelin, cloison RGPD propriétaire respectée (île → propriétaire NULL), toasts « couche vide » honnêtes. **Cinq écarts** à mandater, dont un seul de gravité moyenne (troncature BPE silencieuse) ; les quatre autres sont des questions de provenance/fraîcheur et de cohérence texte↔câblage, sans faux positif servi à ce jour.
