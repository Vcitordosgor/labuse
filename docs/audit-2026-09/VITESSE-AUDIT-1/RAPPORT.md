# VITESSE-AUDIT-1 — Où LA BUSE est lente, où elle ne l'est pas, comment l'accélérer

> **Audit de vitesse, LECTURE SEULE.** Aucun correctif, aucun merge, aucune donnée/chiffre/géométrie
> modifié. Ce rapport produit la carte des lenteurs et l'ordre des mandats `VITESSE-FIX-n`.

## En-tête — cadre de mesure

| | |
|---|---|
| Branche / worktree | `audit/vitesse-1` · `~/Desktop/labuse-vitesse` |
| Commit `main` de départ | `4811596d` (Merge branch 'audit/comparer-1') |
| Run servi | **`q_v11_m137`** (vérifié : baké dans `dist/assets/index-*.js`) |
| Base | **PostgreSQL 18.4** aarch64 (`localhost:5432/labuse`) — **unique et partagée** |
| Machine de mesure | **MacBook Air M1** (`MacBookAir10,1`, 8 cœurs), macOS 13.0.1, **1 worker uvicorn** |
| Front mesuré | **build de PROD** (`npm run build`), servi par **FastAPI `StaticFiles` `/socle/`** + `GZipMiddleware` (chemin prod hors Caddy). Jamais le dev-server Vite. |
| Prod (référence) | **6 vCores / 5 workers**, **Caddy** (gzip, HTTP/2, assets 1 an). La mesure locale mono-worker est **indicative** : latence par requête, pas la concurrence à 5 workers. |
| Outillage | sonde de timing jetable (`harnais/sonde_app.py`) + harnais rejouable (`harnais/harness.mjs`, Playwright chromium-1217). CSV bruts dans `MESURES/`. |

> **Réserve de fidélité (cf. §9).** La base locale est partagée avec des **runs résiduels réels**. Un
> a été actif ~15 min pendant l'audit (transaction longue tenant un `AccessShareLock` sur `parcels`),
> gonflant les temps SQL absolus. **Les mesures « à froid » retenues comme lentes ont été RECONTRÔLÉES
> en fenêtre calme** (run résiduel `idle`) : les 🔴/🟠 ci-dessous **persistent** hors charge (ex. la
> fiche reste 13–15 s). Un cas s'est révélé être du **bruit** et non un défaut (le check de version de
> tuile `max(created_at)` : 3,2 s sous charge → **0,3 ms indexé** au calme) — il est écarté.

---

## 1. Cinq chiffres en tête

1. **Parcours mesurés : 14 familles** — dont les **55 couches** balayées une à une (île z9 + rue z14)
   et **17 outils** par leur endpoint de résultat.
2. **🔴 (> 10 s) : 1** — la **fiche parcelle (13–15 s)**, et par extension le **Scan patrimoine full**
   (CBO 1 833 parcelles, ~25 s connu ; paginé à 200 = 2,3 s).
3. **🟠 (3–10 s) : 6** — listing du vivier (~5 s), Gabarit (~4,4 s), **tuile île z9 À FROID** (3,8 s),
   couches froides lourdes (alea_mvt 3,3 s), Comparateur communes à froid (3,2 s, caché ensuite),
   solaire (2,5 s) / patrimoine 200 (2,3 s) en limite.
4. **Écran le plus lent : la fiche parcelle, 13–15 s**, dont **une seule requête SQL = 8,4 s**
   (`ST_Area(ST_Intersection(parcelle, couche))` sur SUP/DPU/PEB/prescription).
5. **Part du temps : le SQL/PostGIS domine largement le chemin lent.** Fiche = **95 % SQL** (148
   requêtes) / 5 % Python. Les seules lenteurs **côté Python** : la sérialisation GeoJSON du Permis
   carte (6,45 Mo) et l'exposition (calcul MNT externe). Le **front est rapide au premier pixel**
   (FCP ~0,6 s) mais **jank ~2 s de long-tasks** au boot (bundle monolithe + init maplibre).

---

## 2. Méthode et règle « à résultat identique »

Trois étages sur chaque parcours : **réseau | serveur Python | SQL | rendu navigateur**.

- **A — Navigateur** : Playwright (chromium-1217) sur le build prod servi `/socle/`. TTFB/FCP/LCP,
  long tasks, poids (HAR/req). 1× froid + 2× chaud. `harnais/harness.mjs` (volet navigateur).
- **B — Serveur** : sonde ASGI + listeners SQLAlchemy `before/after_cursor_execute` → `MESURES/sonde/
  sonde_requests.csv` (total | SQL | Python | n_requêtes | octets par requête HTTP) et `sonde_sql.csv`
  (chaque exécution SQL). **Jamais dans `src/`**.
- **C — Base** : `EXPLAIN (ANALYZE, BUFFERS)` en fenêtre calme → `MESURES/EXPLAINS.txt`.

**Règle d'or.** Chaque levier ci-dessous porte un **risque sur le résultat** : `nul` (cache, index,
parallélisation, compression, en-têtes) ou `à prouver` (réécriture SQL, matérialisation) + la preuve
d'identité à exiger dans le FIX. **Interdits jamais proposés** : simplification/ré-échantillonnage de
géométrie, tout paramètre du tuyau de tuiles (extent/buffer/tolérance/zoom/filtre), toute
agrégation/arrondi changeant un chiffre, tout retrait de champ affiché.

---

## 3. Tableau des parcours (verdict)

Temps **serveur** (sonde) sauf mention ; froid = 1er hit après démarrage / LRU miss ; chaud = médiane.

| # | Parcours / écran | Froid | Chaud | Décomposition | Verdict |
|---|---|---|---|---|---|
| 1 | Boot accueil (page) | FCP 0,59 s · load 0,66 s · **14 long-tasks ≈2,1 s** · 3,9 Mo | idem | réseau+rendu ; JS monolithe | 🟡 (FCP vert, jank) |
| 2 | Carte vue île — tuile parcelles z9 | **3,8 s** (0,57 Mo) | **0,12 s** | SQL build MVT (LRU miss) | 🟠 froid / 🟢 chaud |
| 2 | Carte z11 / rue z14 | 1,3 s / 0,17 s | 0,20 s / 0,09 s | idem | 🟡 / 🟢 |
| 3 | 55 couches (une à une) | la plupart < 1 s ; alea_mvt 3,3 s, batiment 2,5 s, ppr 1,8 s | **tous < 0,25 s** | SQL build ; LRU | 🟢 chaud / 🟠 froid (lourdes) |
| 4 | Filtre + listing 200 | ~5,0 s | ~4,6 s | **SQL** (page multi-jointures + tri rang) | 🟠 |
| 4 | Compteur vivier / filtres | < 0,3 s | < 0,1 s | SQL | 🟢 |
| 5 | Omnibox (adresse/IDU/réf/SIREN) | 0,02–0,07 s | 0,02 s | SQL indexé | 🟢 |
| 6 | **Fiche parcelle (tête)** | **13–15 s** | **13–15 s** | **95 % SQL** (148 req, 1 = 8,4 s) | 🔴 |
| 6 | Fiche sous-sections (lazy) | exposition 0,7–1,5 s (Python) · zone 0,7 s (49 req) · mon-secteur 0,27 s | — | mixte | 🟡 |
| 7 | Fiche commune / liste communes | 0,012 s | 0,012 s | caché | 🟢 |
| 7 | Comparateur communes | **3,2 s** (48 req N+1) | **0,008 s** (cache 1 h) | SQL N+1 | 🟠 froid / 🟢 chaud |
| 8 | Outil Gabarit | ~4,5 s | ~4,4 s | **SQL** (ST_Intersection au vol) | 🟠 |
| 8 | Scan patrimoine (CBO, 200) | 2,7 s | 2,0 s | SQL + N+1 communes | 🟡 (full 1833 ≈ 🔴) |
| 8 | Solaire / Successions / Piscines-pts | 2,8 / 2,4 / 0,9 s | 2,2 / 1,7 / 0,08 s | SQL | 🟡 |
| 8 | Permis carte | 0,93 s (**6,45 Mo**) | 1,0 s | **Python** (sérial. GeoJSON) | 🟡 (poids) |
| 8 | Assemblage voisines / PLU annuaire / Communes | 0,01–0,27 s | idem | SQL | 🟢 |
| 13 | Exposition (tuile fiche) | 0,68 s | 1,5 s | **Python** (MNT/gdaldem, 0 SQL) | 🟢/🟡 |

*(CSV bruts : `MESURES/sonde/`, `MESURES/couches_resume.csv`, `MESURES/parcours_browser.csv`,
`MESURES/har/`.)*

---

## 4. Déjà rapide — NE PAS toucher

1. **Tuiles vectorielles matérialisées** (`mvt_parcels`, 431 640 objets, `geom_3857` pré-projeté +
   GiST, statuts/zonage/score pré-joints). Coût de service **chaud 0,09–0,25 s**. Architecture juste.
2. **Cache tuiles LRU + en-têtes HTTP** (`max-age=3600, stale-while-revalidate=86400, ETag`) : les
   tuiles **chaudes** et les visites répétées sont excellentes. Zoom-simplify et `ST_Subdivide` sont
   **hors périmètre** (interdits).
3. **Omnibox** (adresse/IDU/réf courte/SIREN) : **20–70 ms**, index trigram/btree en place.
4. **Compteur du vivier, liste communes, PLU annuaire, v2/score, anti-fiche, assemblage voisines** :
   tous < 0,3 s, souvent cachés.
5. **Compression** (`GZipMiddleware` + Caddy gzip) et **assets immuables** (Caddy `max-age=1 an`).
6. **Découpage lazy partiel** (`MapView`/`RadarView`/`TimeMachine`), `pool_pre_ping`,
   `idle_in_transaction_session_timeout=600 s`.

---

## 5. Les 55 couches (synthèse ; détail : `MESURES/couches_resume.csv`)

Toutes servies en **MVT** depuis `spatial_layers` (2975) ou une table matérialisée
(`tuyau_subdivise`/`tuyau_sup`/`tuyau_piscines`/`mvt_parcels`/`mvt_communes`). **Chaud : toutes
< 0,25 s.** À froid (LRU miss, build ST_AsMVT) :

| Couche (route front) | z9 froid | z9 poids | Remarque |
|---|---|---|---|
| **parcelles** (route dédiée `/map/tiles/{z}/{x}/{y}.pbf`) | 3,8 s | 0,57 Mo | couche reine, simplifiée par zoom |
| alea_mvt | 3,3 s | 0,97 Mo | risque, gros polygones |
| batiment | 2,5 s | 0,41 Mo | GeoJSON+bbox |
| alea_inondation | 2,0 s | 0,44 Mo | |
| ppr | 1,8 s | 0,77 Mo | |
| plu_gpu_zone | 1,0 s | 0,38 Mo | |
| ~40 autres couches | < 1 s | < 0,35 Mo | 🟢 |

**Fait de qualité (aucune action).** Aucune couche ne sert de géométrie « appauvrie » stockée : la LOD
est calculée au vol par le tuyau (interdit d'y toucher). **Deux couches hors-registre servent des
tuiles lourdes par la route `kind` — `limites_parcelles` (4,5 s / 2,2 Mo) et `zonage_parcelle` (2,9 s
/ 2,5 Mo) — mais LE FRONT NE LES UTILISE PAS** : `MapView.tsx:613` rend parcelles+zonage depuis la
route dédiée `mvt_parcels` (simplifiée, 0,57 Mo). Ces routes `kind` sont donc servies mais mortes côté
carte — à signaler à Vic (pas une action de vitesse).

---

## 6. Registre VIT-xxx

### VIT-001 · 🔴 · Fiche — requête d'intersection servitudes (8,4 s à elle seule)
- **Parcours 6.** Fiche 13–15 s (froid ≈ chaud), **95 % SQL, 148 requêtes**. **UNE requête = 8,4 s.**
- **Décomp** : SQL 95 % / Python 5 % / rendu (le shell rend en < 1 s ; la donnée gate l'usage).
- **Cause** : `app.py:3672` `_q_v2_fiche`, requête `SELECT sl.kind … ST_Area(ST_Intersection(p.geom_2975,
  sl.geom_2975)) …` sur `spatial_layers` (dpu/peb/sup/plu_gpu_prescription). **EXPLAIN** (`MESURES/
  EXPLAINS.txt`) : l'index GiST `idx_spatial_layers_geom_2975` **est utilisé** (Bitmap → 184 candidats →
  14 lignes en 240 ms). **Le coût (8,2 s) est la projection `ST_Intersection` (aire) sur 14 gros
  multipolygones dissous** (SUP 417, prescription 10 490 lignes ; table 4,16 Go). **Ce n'est PAS un
  index manquant.**
- **Levier principal** : **matérialiser la part de recouvrement parcelle×couche au build du run**
  (table `parcel_servitude_part` run-scopée, comme `parcel_zone_plu`) ; la fiche LIT. `à prouver`
  (diff `part` à l'euro sur 3 témoins).
- **Levier second** : intersecter contre la géométrie **déjà subdivisée** (`tuyau_subdivise`/`tuyau_sup`,
  ≤ 256 sommets) + `GROUP BY` (somme d'aires = aire identique). `à prouver`.
- **Gain** : 13–15 s → ~1–2 s · **effort M** · **risque à prouver**.

### VIT-002 · 🔴 · Fiche — 148 requêtes SQL en série
- **Parcours 6, même handler.** Au-delà de VIT-001, ~147 requêtes en série (`marche_dvf` ≈ 10, PM
  état+identité en 2, DVF dernier+secteur+détail **exécutés même terrain vierge**, RNIC, Radar,
  Filosofi, RPLS…). `marche_dvf` est aussi rappelé dans `/modules/faisabilite` (double calcul).
- **Levier principal** : paralléliser les requêtes indépendantes (`asyncio`/threads) — `nul`. **Second** :
  fusionner les 2 requêtes PM, sortie anticipée terrain vierge, réutiliser `marche_dvf` — `à prouver`.
- **Gain** : −1 à −2 s après VIT-001 · **effort M** · **dépend de VIT-001** (même handler).

### VIT-003 · 🟠 · Filtre / listing du vivier (~5 s)
- **Parcours 4.** `/parcels?limit=200` ≈ 5 s. La sous-CTE permis `pro_pc` **isolée = 84 ms** (EXPLAIN,
  déjà optimisée cf. `app.py:3235`) → **PAS le coût**. Coût = assemblage de la CTE `page` (8 `LEFT JOIN`
  sur l'île évaluée + tri `rang_v2`). `_q_v2_list` `app.py:3155`.
- **Levier** : EXPLAIN **paramétré** dans le FIX pour trancher **index** `parcel_p_score_v2(run_id, rang)`
  (`nul`) vs réécriture d'une jointure en seq-scan (`à prouver`). Pagination serveur déjà en place.
- **Gain** : 5 s → ~1 s · **effort M** · **risque nul→à prouver**.

### VIT-004 · 🟠 · Gabarit — ST_Intersection au vol (4,8 s)
- **Parcours 8.** `/outils/gabarit` = 4,4 s, **1 requête** `ST_AsGeoJSON(ST_CollectionExtract(
  ST_Transform(ST_Intersection(…))))` = 4,8 s. **Même cause que VIT-001** (géométrie lourde au vol).
- **Levier** : idem VIT-001 (matérialiser ou géométrie subdivisée). **Dépend de / même FIX que VIT-001.**
- **Gain** : 4,4 s → ~0,5 s · **effort M** · **à prouver**.

### VIT-005 · 🟠 · Tuiles FROIDES — pas de cache partagé entre workers
- **Parcours 2/3.** Chaud 0,09–0,25 s (LRU) ; **froid** île z9 3,8 s, alea_mvt 3,3 s, batiment 2,5 s,
  ppr 1,8 s. Le LRU (4096) est **par worker et en mémoire** (perdu au reboot/`build-mvt`) ; **Caddy ne
  cache pas les tuiles** (`reverse_proxy` direct). → un utilisateur neuf ou l'après-déploiement paie le
  froid, **× 5 workers**.
- **Levier** : **cache tuiles PARTAGÉ/persistant** (disque partagé entre workers, ou pré-chauffe au
  build des tuiles île, ou directive de cache au reverse-proxy) — **bytes identiques → risque NUL**.
- **Gain** : élimine 3–4 s au premier affichage · **effort M** · **risque nul** (hash de tuile identique).

### VIT-006 · 🟠→🟢 · Comparateur communes — N+1 (48 requêtes), masqué par cache
- **Parcours 8.** Froid 3,2 s = **2 requêtes DVF × 24 communes** (`WITH parc…` + `WITH mut…`) ; chaud
  **8 ms** (cache 1 h par pondération). `comparateur.py`.
- **Levier** : batcher les 48 en 1 requête groupée par commune. `à prouver`. **Priorité basse** (le
  cache masque en usage courant ; ne mord qu'au miss).

### VIT-007 · 🟡 · Outils moyens + Scan patrimoine full (N+1 communes)
- **Parcours 8.** Solaire 2,5 s, patrimoine(200) 2,3 s, successions 1,9 s. **Patrimoine full** (CBO
  1 833 parcelles) = le **~25 s connu** : boucle Python **par commune** `ligne2_terrain_zone()` +
  géométrie sérialisée par parcelle (`modules.py:268`).
- **Levier** : batcher la boucle communes en 1 requête ; index/pagination géométrie. `à prouver`.

### VIT-008 · 🟡 · Permis carte — 6,45 Mo de GeoJSON sérialisé en Python
- **Parcours 8.** `/modules/permis` (carte) = 0,9 s serveur mais **6,45 Mo** (`ST_AsGeoJSON` × jusqu'à
  60 000 lignes, sérialisation Python). `modules.py:562`.
- **Levier** : construire le GeoJSON **en SQL** (agrégation) ou servir en **tuiles** ; gzip déjà là.
  **Risque nul** (mêmes objets). **Effort S/M.**

### VIT-009 · 🟡 · Fiche /zone (isochrone) — 49 requêtes SQL
- **Parcours 6 (lazy « Autour »).** `/parcels/{idu}/zone` = 0,7 s, **49 requêtes** (N+1). Levier :
  batcher. `à prouver`. **Même famille N+1 que VIT-006/007.**

### VIT-010 · 🟡 · Front boot — 14 long-tasks ≈ 2 s (bundle monolithe)
- **Parcours 1.** FCP 0,59 s (bon) mais **14 long-tasks ≈ 2,1 s** bloquent l'interactivité (INP). Le
  chunk d'entrée **`index` = 262 Ko gzip** embarque **les 17 outils + fiche + filtre + analyse + CRM**
  (seuls MapView/Radar/TimeMachine sont sortis) ; **maplibre (202 Ko gz) est `modulepreload` au boot**.
- **Levier** : découper les 17 outils en `lazy()` par catégorie (rendu identique) ; différer l'init
  maplibre hors du chemin critique de peinture. **Risque nul** (capture identique).

### VIT-011 · structurel · Pool DB par défaut + pas de `statement_timeout` global
- `db.py:74` : `create_engine` **sans `pool_size`/`max_overflow`** → défauts **5 + 10** par worker.
  **Nuance** : les 97 routes `def` (sync) tournent dans le **threadpool** Starlette (~40 threads) — elles
  ne bloquent **pas** la boucle d'événements ; **le plafond réel de concurrence est le pool DB** (15
  connexions/worker face à 40 threads). Les 2 routes `async` (`/login`) font, elles, des appels DB
  bloquants dans la boucle (rare). Pas de `statement_timeout` global (seul `idle_in_transaction`).
- **Levier** : `pool_size`/`max_overflow` explicites (alignés sur les threads) + `statement_timeout` +
  `pool_recycle`. **Risque nul.** **Effort S.**

---

## 6.5 Top requêtes SQL (temps cumulé sur le balayage — `MESURES/sonde/sonde_sql.csv`)

| Cumulé | n | max | Requête | VIT |
|---|---|---|---|---|
| 96,4 s | 7 | 9,7 s | `SELECT sl.kind … ST_Intersection` (fiche servitudes) | VIT-001 |
| 38,3 s | 9 | 4,8 s | `ST_AsGeoJSON(…ST_Intersection…)` (gabarit) | VIT-004 |
| 33,8 s | 6 | 6,8 s | `WITH pro_pc … page …` (listing vivier) | VIT-003 |
| 29,4 s | 116 | 1,0 s | `WITH b AS (ST_TileEnvelope…)` (build tuile tuyau) | VIT-005 (froid) |
| 10,9 s | 6 | 3,2 s | `SELECT max(created_at) FROM spatial_layers` | **écarté** (0,3 ms indexé au calme ; 3,2 s = charge résiduel) |
| 5,8 s | 78 | 98 ms | `WITH parc… id_mutation` (DVF par commune) | VIT-006 (N+1) |

EXPLAIN complets : `MESURES/EXPLAINS.txt`.

---

## 7. Bundle front — chargé à l'accueil

| Chunk | Brut | Gzip | Boot ? |
|---|---|---|---|
| `index` (app + **17 outils** + fiche + filtre + analyse + CRM) | 1 011 Ko | **262 Ko** | oui (entry) |
| `maplibre` | 768 Ko | **202 Ko** | **oui — `modulepreload`** |
| `vendor` (react, react-query, zustand) | 169 Ko | 53 Ko | oui |
| `index.css` / `maplibre.css` | 81 / 63 Ko | 16 / 9 Ko | oui |
| `MapView` / `RadarView` / `TimeMachine` | 44 / 29 / 13 Ko | 14 / 8 / 4 Ko | différés |

**≈ 535 Ko gzip de JS au boot.** L'accueil monte la carte → maplibre est **utilisé** (pas « chargé pour
rien »), mais son `modulepreload` le met sur le chemin critique. Le **monolithe `index` (262 Ko gz)**
est la cible front (VIT-010) : sortir les 17 outils en `lazy()` allège l'éval initiale (~2 s de
long-tasks). Rien d'inutilisé n'est chargé à l'accueil au-delà de ça.

---

## 8. Ordre proposé des mandats `VITESSE-FIX-n` (regroupés par cause commune)

| FIX | Cible (cause commune) | VIT | Gain × usage | Risque | Preuve d'identité à exiger | Harnais à rejouer |
|---|---|---|---|---|---|---|
| **FIX-1** | **Intersections parcelle×géométrie au vol → matérialiser/subdiviser** | VIT-001 + VIT-004 | **très fort** (fiche = usage n°1 ; gabarit) | à prouver | diff JSON `part` servitudes + géométrie Gabarit **à l'euro** sur 3 témoins (AN0347, CV1201, AC0024) | fiche + gabarit du sweep |
| **FIX-2** | **Cache tuiles partagé/persistant** (froid une fois, pas par worker) | VIT-005 | fort (carte = usage n°1) | **nul** | **hash pbf identique** avant/après, mêmes en-têtes | sweep tuiles île z9/z11/rue |
| **FIX-3** | **Fiche : paralléliser + dédupliquer les ~147 requêtes** (réutiliser `marche_dvf`) | VIT-002 | fort | nul→à prouver | **diff JSON fiche complet** (tous champs) sur 3 témoins | fiche |
| **FIX-4** | **Listing vivier** (EXPLAIN paramétré → index rang ou réécriture) | VIT-003 | moyen-fort | nul→à prouver | diff JSON liste **+ ordre** (200 + « voir 200 ») | filtre |
| **FIX-5** | **N+1 → 1 requête groupée** (comparateur, patrimoine communes, /zone) | VIT-006 + VIT-007 + VIT-009 | moyen | à prouver | valeurs par commune/parcelle identiques | comparateur, patrimoine, zone |
| **FIX-6** | **GeoJSON en SQL / tuiles** (permis carte 6,45 Mo) | VIT-008 | moyen | **nul** | mêmes objets (mêmes IDs, mêmes géométries) | permis carte |
| **FIX-7** | **Front code-split** (17 outils en lazy) + différer maplibre | VIT-010 | moyen | **nul** | capture identique même cadrage ; mêmes bytes servis | boot + fiche (navigateur) |
| **FIX-8** | **Réglages serveur** (`pool_size`/`max_overflow`/`pool_recycle`/`statement_timeout`) | VIT-011 | assurance concurrence prod | **nul** | aucune (config), non-régression suite | — |

**Logique de priorité** = gain × usage / risque. FIX-1/FIX-2/FIX-3 attaquent les deux écrans les plus
utilisés (carte, fiche) et le 🔴 unique. FIX-8 est quasi gratuit (risque nul) et protège la prod à 5
workers — peut passer en premier comme « quick win » sans risque.

---

## 9. Doutes et limites de la mesure

- **Base partagée sous charge réelle** (run résiduel ~15 min pendant l'audit) : les temps absolus SQL
  sont bruités **à la hausse**. Contre-mesure appliquée : re-contrôle en fenêtre calme des lenteurs
  retenues (les 🔴/🟠 persistent ; un faux positif — `max(created_at)` — écarté). Cache Postgres et
  `last_analyze` non maîtrisés.
- **Mono-worker local vs 5 workers prod** : la mesure ne capture pas la file `QueuePool` sous
  concurrence — VIT-011 est un raisonnement de code, pas une mesure de charge.
- **Contention de démarrage rencontrée** : le heal DDL du lifespan (`ALTER parcels`, `IF NOT EXISTS`,
  no-op sur schéma à jour) s'est mis en file `ACCESS EXCLUSIVE` derrière le run résiduel, bloquant la
  base partagée. L'instance d'audit a démarré **best-effort** (`schéma=ÉCHEC(verrou/ensure_schema)`,
  sans effet fonctionnel — schéma déjà à jour) avec un **`lock_timeout` court** posé **uniquement sur
  l'instance d'audit** (sonde, non commité) pour ne **jamais** bloquer la base partagée. Les lectures
  de service prennent un `AccessShareLock` (compatible run résiduel) → non affectées. **C'est en soi un
  signal** : le heal DDL au boot peut se coincer derrière un run de fond (à surveiller côté prod).
- **Fiche — vitals navigateur** : le shell de la fiche rend vite (FCP ~0,7 s) mais la **donnée** (13–15
  s serveur) gate l'usage réel ; les métriques navigateur **sous-estiment** le « temps jusqu'à
  utilisable » de la fiche — le chiffre qui compte est le temps serveur.
- **Auth désactivée en local** (`env=local`) : le parcours `/login` réel de la prod (POST + 2FA
  éventuel) n'est pas mesuré.
## §P — Prod (lecture seule)

`ssh labuse-vps` **répond**. Confirmé, **sans rien déployer/redémarrer** :
- **6 vCores** (`nproc`), **uptime 77 j**, **load average 0,08** (prod au repos au moment du relevé).
- **uvicorn `labuse` actif, `--workers 5`** (aligne le mandat 6 vCores / 5 workers).
- `deploy/Caddyfile.prod` : `encode gzip` (pas de brotli/zstd), **tuiles `reverse_proxy` vers uvicorn
  (non cachées par Caddy)**, assets `/assets/*` `max-age=1 an immutable`, `index.html` `no-cache`.
- **Journal d'accès Caddy présent** (`/var/log/caddy/access.log`, 9,4 Mo, JSON avec `duration`) **mais
  non lisible par l'utilisateur SSH** (`caddy:caddy`, mode 600). **L'audit N'ESCALADE PAS** (lecture
  seule) → **p50/p95 par route non extraits**. Pour un `VITESSE-FIX`, exécuter (avec l'accès idoine, en
  lecture seule) le calcul de percentiles par route sur 7 j : le script est dans le §9 du présent dépôt
  (bloc python `duration`/`request.uri`), à lancer côté serveur.

## 9 (suite). Autres doutes et limites

- **Prod non chiffrée** : voir §P (log Caddy non lisible sans escalade, déclinée).
- **Bug harnais corrigé pendant l'audit** : un re-run `SKIP_SWEEP` réécrivait l'en-tête du CSV de
  sweep ; le harnais n'écrase plus un CSV existant. Les données serveur (sonde, append-only) sont
  restées intactes ; le tableau des couches a été reconstruit depuis la sonde.
