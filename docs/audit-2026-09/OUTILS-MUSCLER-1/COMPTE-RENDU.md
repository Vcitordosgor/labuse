# OUTILS-MUSCLER-1 — compte-rendu (06/09/2026)

**A0.** Servable telle quelle à condition de ne jamais dire « en succession » : `parcel_veille_succession` (7 129 parcelles,
24/24 communes, 0 perte de jointure) est un radar patrimonial 3-7 ans (dirigeant ≥ 70 ans 99,9 %, SCI dormante 7), calculé
le 09/08 sur un RNE du 06/07 ; manque : date par parcelle (impossible avec l'amont). Rafraîchissement proposé, **non
exécuté** (décision Vic) : `labuse score-v-compute`.

**Commits.** Lot A `0df2261c` (A0 + /modules/successions + outil front + 3 tests) · Lot B `303e14b8`
(/moteurs/assemblage/voisines + B1-B5 front + 3 tests) · recette (captures + ce CR).
**Captures** : `captures/avant-01..02`, `apres-01..08` (app réelle, base labuse — menu, île, sélection+tiroir, vide honnête
Cilaos ≥ 1 000 m², voisines, anneau 2, analyse, pont Courrier avec « ← Successions »).

**B6.** `/moteurs/assemblage/voisines`, 3 mesures HTTP par parcelle : AB0009 (Uavap) 59/18/27 ms · AC0024 (Acu) 33/9/8 ms ·
AE0003 (RNU) 11/16/8 ms — index GIST `idx_parcels_geom_2975` déjà en place.

**A résisté.** (1) Le retour B5 revenait avec une sélection VIDE : le cleanup GB-010 (`moteurs.tsx`, `setMsel([])` au
démontage) rejoue au montage sous React.StrictMode et effaçait le `msel` restauré → restauration par prefill consommé
(`useApp.ts:196` `mselPrefill`, idiome parcelPrefill). (2) `p_model_ext_dataset` non-ORM, absente sur base neuve → gardes
`to_regclass` dans les deux endpoints (même convention que `models.py:1075`). (3) Editable → `PYTHONPATH=<worktree>/src`.

**Décisions faute d'instruction.** Libellés réécrits d'après A0 (« approche une succession », jamais « en succession ») ;
« signal daté du [millésime] » porté au bandeau/tiroir, la carte porte le motif réel (« dirigeant N ans » / « SCI
dormante ») ; filtre résiduel = select à paliers (0/100/200/500/1 000 m²) ; B4 accumule les anneaux par départ (bloc par
départ, bandeau « N voisines de X ») ; sélecteur de commune = `CommuneScope` (périmètre explicite, pas le filtre global).

**Tests.** Back : 6 nouveaux verts ; suite 2 707 passed / 4 failed **pré-existants** (rejoués verts-identiques sur l'état
sans les changements : courrier_boucle, dashboard, front_reliquats ×2). Front : tsc 0 · vitest 187/187 · build OK.
