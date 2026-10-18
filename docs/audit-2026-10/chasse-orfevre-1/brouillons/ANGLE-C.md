# CHASSE-ORFEVRE-1 — Angle C : les coins du calcul

Audit du 18/10/2026, worktree `~/Desktop/labuse-orfevre` (audit/chasse-orfevre-1 = main), base `labuse`
(rôle `openclaw`), **lecture seule** (aucune écriture ; sondes API via `TestClient` SANS `with` → le
lifespan/`ensure_schema` n'est PAS exécuté, aucun DDL ; aucune requête POST).
Tout est rejouable : `scripts/angle_c_calcul.py` (exécution de référence : 0 erreur).

**Corrections d'hypothèses du mandat (constatées en base) :**
- `labuse_hauteur_lidar_m` et `labuse_zone_famille` **SONT en base ici** (`\df labuse*`) — le mandat
  disait la première absente. Les hauteurs servies via la fonction sont donc bornées (≤0 ou >60 → NULL).
- Le run score **servi est q_v19** (`config/served_run.txt`), pas q_v18 ; run résiduel servi = 16 (confirmé).

Gravités : BLOQUANT / GÊNANT / COSMÉTIQUE / À SURVEILLER. Aucune correction appliquée.

---

## C-01 — « bâti existant sur 19 569 % de la parcelle » : la phrase du score N'EST PAS bornée (le chiffre brut de A-02 atteint l'écran)
- **Constat** : la contribution de score servie au client porte le taux d'emprise BRUT :
  « bâti existant sur **19569** % de la parcelle — démolition à prévoir ».
- **Preuve base** : `score_labuse` run **q_v19 (SERVI)**, `contributions` JSONB :
  `regexp_match(libelle, 'bâti existant sur (\d+) %')` → 232 371 phrases, dont **61 555 > 100 %**,
  **9 714 > 300 %**, max **19 569 %** (parcelle `97411000AY0015`, le cas n°1 de l'angle A A-02).
- **Preuve code** : `src/labuse/scoring/score_labuse.py:281-283` — la phrase est fabriquée avec
  `round(emp or 0)` **sans aucune borne**, puis FIGÉE dans `contributions` au moment du run.
- **Preuve servie** : `GET /parcels/97411000AY0015` (TestClient) → le JSON de la fiche contient la
  phrase telle quelle ; le front l'affiche **verbatim** (`frontend/src/components/panel/ResultsSection.tsx:374-388`,
  liste ▲/▼ « pourquoi ce score », aucun formatteur).
- **Pourquoi c'est passé au travers** : toute la doctrine CHASSE-INVARIANTS-FIX-1 (E-01) borne les
  **champs** (`fmtTauxEmprise`, `fmt_taux_emprise`, `fmtPctConsomme` → « Saturé … » au-delà de 100),
  mais cette phrase-ci est un **texte pré-cuit au scoring** : les formatteurs de lecture ne la voient
  jamais.
- **Gravité** : **GÊNANT** (61 555 parcelles du run servi peuvent montrer un pourcentage absurde dans
  « Pourquoi ce score », à l'écran et dans tout export qui reprend les contributions).
- **Correction proposée (non appliquée)** : dans `score_parcelle`, borner la phrase (ex. > 100 % →
  « bâti existant au-delà du plafond d'emprise du PLU (saturé) — démolition à prévoir »), même rendu
  que `fmt_taux_emprise` ; effet au prochain run (ou reprise SQL des libellés du run servi).

## C-02 — Parts de sol CoSIA servies > 100 % (jusqu'à 199,3 %)
- **Constat** : la fiche §Le bien sert « Part imperméabilisée : **199,3 %** ».
- **Preuve base** : `parcel_cosia_couverture` × `parcels` — avec le dénominateur du code
  (`round(surface_m2)` dessin) : **11 180 parcelles** ont au moins une part > 100 % (max 199,3) ;
  **9 151** ont la SOMME des 3 parts > 100,5 %. Pires : `97420000BH1222` (CoSIA 389 m² / dessin 154 m²),
  `97411000AW0565` (95/40), `97420000AC0262` (896/605).
- **Preuve code** : `src/labuse/bati.py:212-214` — `round(100.0 * imper / surface, 1)` **sans clamp** ;
  seul le cas `surface <= 0` est gardé (ligne 190). Le docstring (l. 180) dit « les trois parts ne
  somment donc pas 100 % (résidu dit honnête) » — il prévoit un résidu POSITIF, pas un dépassement.
- **Preuve servie** : `GET /parcels/97420000BH1222` → `le_bien.cosia_couverture.part_impermeabilisee_pct = 199.3` ;
  front `frontend/src/components/fiche/leBien.tsx:199` affiche `toLocaleString('fr-FR')` **brut**.
- **Cause** : CoSIA est un raster 20 cm agrégé à la parcelle ; ses m² par classe débordent le dessin
  cadastral (bordures, sur-détection) — le même phénomène que l'emprise > 100 % de l'angle A.
- **Gravité** : **GÊNANT** (une « part » > 100 % est une impossibilité logique visible client, 2,6 %
  du parc couvert).
- **Correction proposée** : normaliser au service — dénominateur = `max(surface, Σ classes CoSIA)` (les
  parts redeviennent des parts), ou borner chaque part à 100 avec mention « mesure CoSIA > surface
  cadastrale » ; ne pas réécrire la table.

## C-03 — Parts de zonage commune : 9/24 communes ne somment pas à 100 % (promesse du docstring)
- **Constat** : `/communes/{c}/contexte` → `repartition_zonage.familles[].pct` somme à 99,9 ou 100,1.
- **Preuve** : appel direct du moteur (`registre/moteurs/zonage.py::parts_zonage_surface`) sur les 24
  communes → **9 hors 100,0** : Bras-Panon 99,9 · L'Étang-Salé 99,9 · La Plaine-des-Palmistes 99,9 ·
  Les Trois-Bassins 99,9 · Saint-Benoît 100,1 · Saint-Denis 100,1 · Saint-Joseph 100,1 · Saint-Paul
  100,1 · Saint-Pierre 99,9. Vérifié servi : `GET /communes/Saint-Denis/contexte` → U 22,2 + AU 1,7 +
  A 7,2 + N 69,0 = **100,1**.
- **Preuve code** : `src/labuse/registre/moteurs/zonage.py:46` — `round(100 * m2 / total, 1)` par
  famille, indépendamment ; le docstring (l. 15) affirme pourtant « les parts somment à 100 % ».
- **Gravité** : **COSMÉTIQUE** (arrondi classique) — mais la promesse écrite du module est fausse.
- **Correction proposée** : méthode du plus fort reste (largest remainder) sur la dernière décimale,
  ou corriger le docstring (« somment à 100 % ± 0,1 ») et l'affichage front le dire.

## C-04 — Division par zéro SQL déclenchable par paramètre client (mode B, /filtre)
- **Constat** : `GET /filtre?source=q_v19&mode_b_rentable=true&modeb_rendement_pct=0` → le SQL exécute
  `… / (:f_rend / 100.0)` avec f_rend=0 → **erreur Postgres 22012 (division_by_zero)**, interceptée
  en **422 « Paramètre invalide ou hors bornes. »** (log : `DataError→422 (22012) sur GET /filtre`).
- **Preuve code** : `src/labuse/api/app.py:1949-1952` — `params["f_rend"] = modeb_rendement_pct if …`
  sans borne ; le dataclass `FiltreCriteres` (l. 2012) et `filtre_from_hash` n'imposent **aucun ge/le**,
  alors que l'endpoint jumeau `/parcels/{idu}/mode-b` (l. 5581-5585) borne `rendement_cible_pct`
  à `ge=1, le=20`. Le front (`useApp.ts:176`) part de 6 — mais tout client API peut envoyer 0.
  Même trou pour un cadrage de projet (`api/projets.py:223`, `modebRendementPct` non borné).
- **Comportement** : dégradé proprement (422, pas de 500, transaction avortée puis rollback) — mais le
  message générique masque la cause, et c'est la SEULE voie trouvée où une entrée client atteint un
  opérateur `/` SQL non protégé par NULLIF.
- **Gravité** : **À SURVEILLER** (pas de crash ; incohérence de validation entre deux endpoints du même
  calcul).
- **Correction proposée** : mêmes bornes que `/parcels/{idu}/mode-b` (`ge=1 le=20`) sur FiltreCriteres
  + `NULLIF(:f_rend, 0)` en ceinture-bretelles.

## C-05 — taux_emprise_pct / pct_potentiel bruts dans les JSON servis (bornés à l'affichage seulement)
- **Mission reçue de l'angle A (A-02)** : suivre les 61 555 `taux_emprise_pct` > 100 (max 19 569) du
  run servi 16 jusqu'à l'écran. **Verdict : les valeurs ATTEIGNENT le JSON servi, brutes ; tous les
  lecteurs CONNUS les bornent à l'affichage ; UNE seule fuite réelle = la phrase C-01.**
- **Chemins vérifiés** :
  - `/compare` sert `taux_emprise_pct: 19569` **brut** (prouvé TestClient ; code `app.py:8118`) → front
    `fmtTauxEmprise` (`frontend/src/lib/format.ts:52-56`) rend « Saturé : le bâti existant dépasse… »
    au-delà de 100 ; PDF comparatif via `fmt_taux_emprise` (`exports/blocs/comparatif.py:99`) idem.
  - fiche `potentiel_transformation.pct_consomme` : servi brut (20 140 possible) → front
    `fmtPctConsomme` affiche « > 300 » (`format.ts:44-45`) ; moteur de secours legacy : pct > 100
    **supprimé au service** (`app.py:6240-6243`).
  - `residuel.libelle` (texte du moteur) passe par `fmt_taux_emprise` (résiduel) — conforme.
- **Gravité** : **À SURVEILLER** — tout NOUVEAU consommateur du JSON (partenaire API, export ad hoc,
  copilote) reçoit 19 569 sans garde-fou ; la doctrine actuelle repose sur la discipline des lecteurs
  (C-01 montre qu'elle casse).
- **Correction proposée** : rien d'urgent au-delà de C-01 ; à terme, servir AUSSI un champ borné
  (`taux_emprise_affiche`) ou documenter le contrat (« peut dépasser 100, borner à l'affichage »).

## C-06 — parcel_filtre_bati.ratio_pct : plafond 300 avec poussière flottante (300.0000000064857)
- **Preuve base** : `select … from parcel_filtre_bati` → **20 536** ratio_pct > 100 ; plafonné ~300
  mais en float : **22 lignes = 300 exactement, 10 lignes > 300** (max `300.0000000064857`, ex.
  `97413000DG0115` : emprise 29,820164… m² ≈ 3 × aire 29,82 m² au bruit flottant près).
- **Preuve code** : construit par `faisabilite/filtre_bati.py:106` (`100.0 * emprise / NULLIF(aire,0)`,
  plafond amont sur l'emprise p_model_bati) ; servi arrondi `round(ratio_pct, 1)` → 300.0
  (`api/app.py:1404`, badges M28 — servis si `LABUSE_M28_BADGES=1`). Les motifs texte stockés disent
  « ratio 300 % » (round entier, pas de fuite de décimales).
- **Comportement** : tout filtre/égalité strict `ratio_pct <= 300` raterait les 10 lignes ; l'arrondi
  au service absorbe l'affichage.
- **Gravité** : **COSMÉTIQUE** (plafond technique non net ; aucun écran constaté ne fuit).
- **Correction proposée** : `LEAST(…, 300.0)` explicite au build (ou plafonner l'emprise source).

## C-07 — 391 parcelles ≤ 1 m² (min 0,027 m²) : calcul sain, mais la fiche sert « surface_m2: 0 »
- **Preuve base** : `parcels` → **391** vivantes à `surface_m2 <= 1` (min 0,0270 m², `97401000AR1644`,
  contenance 1 m²) ; côté run servi 16 : toutes neutralisées (`terrain_exigu` 192, `surface_incertaine`
  175, zones N/A…, SDP 0) ; bandes : 212 × « 0 », 179 × NC. **Aucune n'a de potentiel inventé.**
- **Mais** : `GET /parcels/97401000AR1644` sert `"surface_m2": 0` et `"surface_dessin_m2": 0`
  (arrondi entier d'un 0,027) — un 0 à la place d'une quasi-absence, contraire à la doctrine « jamais
  un zéro menteur » ; `surface_terrain_m2: 1` (contenance) sauve l'affichage principal.
- **Gravité** : **COSMÉTIQUE**.
- **Correction proposée** : servir la surface dessin < 1 m² avec une décimale ou `< 1 m²`.

## C-08 — 81 parcelles ≥ 200 ha (max 2 817 ha, `97417000BN0004` Saint-Philippe) : RAS
- Résiduel run 16 : toutes `zone_non_constructible:*` (Npnr 54, Nr 9, N 7, Npf 2), `hors_plu` 6,
  `zone_non_resolue:N` 3 ; score q_v19 : 72 × bande 0 (score 0), 9 × NC. Fiche HTTP 200, formats sains.
- **Verdict : SAIN** (aucune géante servie avec un potentiel).

## C-09 — 2 parcelles GEOMETRYCOLLECTION (polygone + débris LINESTRING)
- **Preuve base** : `97409000BR0171` (Saint-André, 23 988 m²) et `97411000HP0491` (Saint-Denis,
  197 m²) : `GeometryType(geom) = GEOMETRYCOLLECTION`, composition POLYGON + LINESTRING (`st_dump`).
- **Comportement** : tout l'aval tient — `ST_Area` 2975 correcte, résiduel calculé
  (`terrain_exigu` / `redhibitoire`), score bande 0, fiche 200 OK. Le trigger geom_2975 et les
  `ST_Intersects` acceptent la collection.
- **Gravité** : **À SURVEILLER (théorique)** — un futur code exigeant un (MULTI)POLYGON strict
  (`ST_CollectionExtract` absent) ou un export KML/geojson typé pourrait casser sur ces 2 lignes.
- **Correction proposée** : au prochain chargement cadastre, `ST_CollectionExtract(geom, 3)`.

## C-10 — Zones PLU « tordues » : rien en base, resolve_zone robuste (SAIN)
- **Base** : `spatial_layers` kind `plu_gpu_zone` (5 841) : **0** subtype NULL/''/espaces/minuscule ;
  `labuse_zone_famille(subtype)` ne classe **aucune** zone en « autre » (U 1 875 / A 1 689 / N 1 457 /
  AU 820). `parcel_zone_plu` (430 320) : **0** zone_lib vide/espaces/minuscule, **0** zone_fam vide.
- **Calibrage** : scan exhaustif des `config/calibrage/calibration_*.yaml` → **aucune** règle
  hauteur/emprise/retrait/stationnement/pleine_terre à 0 ; aucune valeur vide servie comme contrainte.
- **Code** : `resolve_zone` normalise (`zone_norm.normalize_key` : minuscules/accents/séparateurs) —
  `'u1'`/`' U1 '` → zone calibrée U1 ; `''` → None ; `'ZZZZ'`/`'   '` → non constructible générique
  (jamais un « constructible » inventé). Micro-incohérence sans déclencheur : `''` → None mais
  `'   '` → ZoneRules(code='') — purement théorique (0 ligne en base).

## C-11 — DEUX définitions de « famille de zone » qui divergent (piège latent, 0 déclencheur aujourd'hui)
- **Constat code** : la fonction SQL `labuse_zone_famille` (`models.py:1193`) matche `AU%`/`U%` et
  `A`/`N` **exacts** : `'1AUb'` → « autre », `' U1'` → « autre », `'Nco'` → « autre », NULL → « autre ».
  Le Python `zone_norm.famille_normalisee` (l. 37-42), lui, **retire le préfixe de phasage** (`2AUc` →
  AUC). Le clip d'assiette du résiduel (`faisabilite/residuel.py:95`, `_BATI_ASSIETTE`) repose sur la
  fonction SQL appliquée à `spatial_layers.subtype`.
- **Preuve d'innocuité actuelle** : les subtypes GPU en base sont le vocabulaire standard (zéro
  « autre », cf. C-10) — aucun subtype ne commence par un chiffre ni ne porte d'espace. Les `name`
  à chiffre (`1AUb`) existent mais `_BATI_ASSIETTE` lit `subtype`, pas `name` (leçon EXIGU-GRANDES).
- **Gravité** : **À SURVEILLER (théorique)** — si une commune publie un jour `subtype='1AUb'` ou
  `' U1'` au GPU, la famille retombe sur « autre » → la portion sort de l'union U/AU → assiette et
  bâti retranché faux, EN SILENCE (c'est exactement la forme du bug des « 8 communes à name littéral »).
- **Correction proposée** : aligner la fonction SQL sur `famille_normalisee` (strip `^[0-9]+`, btrim)
  + un verrou/banc « 0 zone famille=autre » pour sonner si le vocabulaire GPU bouge.

## C-12 — Divisions par zéro : les dénominateurs à 0/quasi-0 existent, les gardes tiennent (SAIN)
- **Dénominateurs réels vérifiés en base** → garde code en face :
  - DVF `surface_reelle_bati` : 55 105 NULL, min **1 m²** (24 ventes 1-9 m² > 100 k€, ex.
    `97418000BD0371` local 5 750 500 € pour 1 m² = 5,75 M€/m² potentiel) → les « ventes proches » de
    la fiche filtrent `surface_reelle_bati >= 20` + `NULLIF` (`marche_service.py:254-261`) ; médianes
    secteur : bornes saines (cf. angle A A-05c).
  - Filosofi : min(men)=0,2 min(ind)=1 → `NULLIF(f.ind,0)` + `if carreau["men"] else None`
    (`app.py:4446-4472`).
  - ZAN : 0 ligne `conso_2021_2024_m2 <= 0`, et garde `rythme <= 0 → None` (`app.py:2425`).
  - Résiduel : `taux_emprise = … if emprise_max else None`, `pct_potentiel = … if sdp_max else None`
    (`residuel.py:217-218`) ; couverture score `if total else 100` (`score_labuse.py:236`) ;
    scénarios `if sdp_enveloppe <= 0: return 0,0` (`scenarios.py:36-40`) ; charge foncière
    `if cf and surface` (`assemblage.py:272`) ; hypothèses éditables bornées min 20 m²/logement
    (`engine.py:172-199`) ; écart annonce `if act and act > 0` (`app.py:4968`).
  - SQL : usage systématique de `NULLIF(…, 0)` (`bati.py:120`, `dvf_mediane.py:60`, `zone.py:160-194,
    608, 649`, `app.py:4446, 4677, 4798, 4815`…).
- **Seule voie non protégée trouvée** : C-04 (paramètre client mode B).

## C-13 — NaN / Infinity : 0 partout (SAIN)
- 9 familles de colonnes float des tables servies testées (`batiment_hauteur_lidar`, `dpe_records`,
  `dvf_mutations_parcelle`, `filosofi_carreaux_200m`, `parcel_p_score_v2`, `parcel_vegetation`,
  `parcels`, `score_labuse` [signal_p], `parcel_filtre_bati`) : **0** NaN, **0** ±Infinity.
- Bonus bornes : `canopee_*_pct` et `ocsge.part_artif_pct` tous dans [0, 100].

## C-14 — Tri et accents : collation C mais aucun déclencheur servi (SAIN / théorique)
- **Fait** : la base est en `datcollate = C` (tri par octets UTF-8 : toute initiale accentuée — É =
  0xC389 — trierait APRÈS « z »).
- **Déclencheurs cherchés, non trouvés** : 0 dénomination/nom à initiale accentuée dans
  `parcelle_personne_morale`, `sirene_etablissements`, `annuaire_services`, `anru_quartiers` (les
  référentiels INSEE/MAJIC sont en majuscules sans accents). Les communes (`ORDER BY nom`) tombent
  juste : « L'Étang-Salé » commence par « L' » (l'accent est en 3e position, et l'apostrophe 0x27 le
  place avant « La … » — ordre affiché correct).
- **Gravité** : **À SURVEILLER (théorique)** — toute future donnée triée commençant par É/À (nom de
  quartier, programme promoteur…) sortira en fin de liste. Correction : `COLLATE "fr-x-icu"` sur les
  ORDER BY d'affichage, ou tri côté front (`localeCompare('fr')`).

## C-15 — Formats d'affichage JSON (quasi SAIN)
- **Longues décimales** : sur toutes les fiches sondées, seules `terrain.pente_moy_deg` /
  `pente_max_deg` sortent brutes (ex. `16.12502`) — le front formate via `pente_texte`/1 décimale
  (`pente_fmt.py`, `Fiche.tsx:925`). COSMÉTIQUE (contrat JSON), rien à l'écran.
- **Notation scientifique** : 57 lignes `score_labuse.signal_p` ∈ (0, 1e-4) en base (ex.
  `97404000AT0722` = 1e-05) qui sérialiseraient « 1e-05 » — mais **aucune fiche sondée ne sert ce
  float brut** (le signal est servi en niveau/percentile). 0 occurrence de `e-` numérique dans les
  JSON testés.
- **-0** : 0 occurrence dans les JSON sondés (les `round(x, 1)` Python peuvent produire -0.0 en
  théorie ; aucun déclencheur trouvé).
- **Fourchettes** : `logements_au_sol` lo ≤ hi par construction (`floor×ratio` ≤ `ceil×ratio`,
  `scenarios.py:30-42`) ; compteurs `/filtre` et `/stats/entonnoir` : total = Σ tiers (vérifié,
  432 350 = 142+662+279 142+152 404).

---

## Synthèse des gravités
| # | Cas | Gravité |
|---|-----|---------|
| C-01 | phrase score « bâti sur 19 569 % » servie (61 555 parcelles q_v19) | **GÊNANT** |
| C-02 | parts CoSIA > 100 % servies (11 180 parcelles, max 199,3 %) | **GÊNANT** |
| C-03 | parts zonage commune ≠ 100 % (9/24) vs promesse docstring | COSMÉTIQUE |
| C-04 | mode B rendement 0 → division par zéro SQL (422 gracieux, bornes absentes) | À SURVEILLER |
| C-05 | taux/pct bruts (19 569) dans les JSON ; lecteurs connus OK | À SURVEILLER |
| C-06 | ratio_pct plafond 300 flottant (10 lignes > 300) | COSMÉTIQUE |
| C-07 | parcelles 0,027 m² → `surface_m2: 0` servi | COSMÉTIQUE |
| C-08 | géantes ≥ 200 ha | SAIN |
| C-09 | 2 GEOMETRYCOLLECTION | À SURVEILLER (théorique) |
| C-10 | zones PLU tordues / règles à 0 | SAIN |
| C-11 | 2 définitions de famille de zone divergentes | À SURVEILLER (théorique) |
| C-12 | divisions par zéro | SAIN (hors C-04) |
| C-13 | NaN/Infinity | SAIN |
| C-14 | tri accents (collation C) | À SURVEILLER (théorique) |
| C-15 | formats JSON | quasi SAIN |

## Pièges notés pour les angles suivants
- `TestClient(app)` **sans** `with` = pas de lifespan = pas d'`ensure_schema` (DDL) : c'est LA façon
  de sonder l'API en lecture seule ; `/filtre`, `/compare`, `/stats/entonnoir` exigent `?source=q_v19`.
- **⚠ EFFET DE BORD DÉCLARÉ** : les GET `/parcels/{idu}` passent par le quota (`api/protection.py`)
  qui INSÈRE dans `consultation_log` — mes sondes ont écrit **23 lignes** (18/10 17:27→17:44+04,
  15 idu : AR1644, AY0015, BN0004…). C'est la seule écriture de l'audit, involontaire et inhérente à
  l'app. Purge (NON exécutée, à faire valider) :
  `DELETE FROM consultation_log WHERE ts BETWEEN '2026-10-18 17:27:00+04' AND '2026-10-18 17:45:00+04';`
  Rejouer `angle_c_calcul.py` ré-écrira ~10 lignes du même type.
- `labuse_zone_famille` prend un **subtype GPU**, pas un libellé de zone : toute comparaison avec
  `zone_lib` « diverge » normalement (30 915 lignes) — ce n'est PAS une anomalie en soi (cf. C-11).
- Les contributions de score sont des **phrases figées au run** : corriger un formatteur de lecture ne
  les répare pas ; il faut re-scorer ou reprendre les libellés en base.
- Le run servi est **q_v19 / résiduel 16** (le mandat citait q_v18 : périmé).
