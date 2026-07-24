# M12 — Lot C-bis · Spin-off : retrait de « Vues »

Retrait du **moteur de segments « Vues »** du code actif de LABUSE. Les trois modèles
extérieurs (Pergolistes / Paysagistes / Piscinistes) sont la future marque
« Plein Sud » / « Soley » : **rien n'est perdu**, tout est archivé avant toute suppression.

Branche : `fenetre/m12-spinoff` (isolée, **non mergée**). Base : `main` (`5e50113`).

## 1. Archive AVANT toute suppression (irréversibilité zéro)

- **Tag d'archive** : `archive/vues-m12-5e50113` → pointe sur l'état `main` intact
  (Vues complet, les 3 modèles extérieurs, presets, validation ortho).
  Poussé sur `origin` : `git show archive/vues-m12-5e50113`.
- **Branche pré-suppression** poussée tôt (avant le moindre `git rm`) :
  `origin/fenetre/m12-spinoff` (état = `main`) — l'historique complet reste sur GitHub.
- **Aucune donnée touchée** : aucune table droppée, aucune ligne supprimée, aucune
  réécriture d'historique.

Restauration future : `git checkout archive/vues-m12-5e50113 -- <chemin>` ramène
n'importe quel fichier Vues à l'identique.

## 2. Retiré (code actif)

### Front
- `frontend/src/components/segments/SegmentsPage.tsx` (page + Builder + BarreNL) — supprimé.
- `frontend/src/components/Rail.tsx` : entrée de rail `{ key: 'segments', label: 'Vues' }`
  + son icône (cible à 3 anneaux).
- `frontend/src/App.tsx` : import `SegmentsPage`, rendu `{view === 'segments' && …}`,
  alias d'URL `#pg=vues` / `pg=segments` (lecture + écriture).
- `frontend/src/store/useApp.ts` : `'segments'` retiré du type `View`.
- `frontend/src/lib/api.ts` : bloc « Moteur de segments Habitat » entier — `getSegments`,
  `querySegment`, `exportSegmentCsv`, `exportPublipostage`, `getGabarits`,
  `createSegmentPreset` / `updateSegmentPreset` / `deleteSegmentPreset`,
  `refreshSegmentCounts`, `nlSegmentsSearch` + tous les types associés
  (`SegmentFiltre*`, `SegmentPreset`, `SegmentsHome`, `SegmentQuery*`, `NlSegmentsRep`).

### Back
- `src/labuse/api/segments.py` (routeur `/segments`) — supprimé ; désenregistré d'`app.py`
  (import, `include_router`, `ensure_tables`).
- `src/labuse/api/ia.py` : route `POST /ia/segments-search` + modèle `SegmentsSearchIn`
  + helper `_nl_log` retirés. Import `Request` (devenu inutile) retiré. **Le fichier
  `ia.py` reste** (routeur IA partagé) ; `/ia/search` intact.
- `src/labuse/ai/nl_segments.py` — supprimé.
- `src/labuse/segments/` (package entier : `engine`, `registry`, `presets`,
  `publipostage`, `residuel_bati`, `catnat`, `__init__`) — supprimé.
- `src/labuse/api/ortho.py` : routes `/ortho/validation*` retirées (page HTML de
  qualification + API suivante/vignette/valider). **`/ortho/equipements/{idu}` conservé**
  (badges de la fiche). Fichier réécrit minimal (imports `cv2`/`numpy` retirés avec les
  vignettes).
- `src/labuse/cli.py` : commandes `segments-seed`, `segments-counts`, `segments-residuel`,
  `ingest-catnat`, `nl-eval` retirées.
- `src/labuse/api/ops.py` : entrée `catnat` retirée de `CRONS` (registre d'observabilité).

### Config / infra
- `config/segment_presets.yaml` — supprimé.
- `deploy/cron.d/catnat` — supprimé (cron mensuel qui appelait `ingest-catnat` +
  `segments-counts`, infra 100 % Vues).

### Tests (archivés — retirés du harnais actif)
Fichiers 100 % Vues, supprimés :
- `tests/test_segments.py`, `tests/test_nl_segments.py`, `tests/test_publipostage.py`,
  `tests/test_preset_parc_piscines.py`, `tests/test_audit_ui_fixes.py` (mentions export
  Vues + double-tir de la validation ortho `/validation`).
- Fixture `tests/nl_queries.txt` (jeu d'éval NL du moteur de segments, orpheline).

Fonctions de test Vues retirées chirurgicalement de fichiers par ailleurs non-Vues
(le reste du fichier — calcul ANC / végétation / BAN — est conservé et vert) :
- `tests/test_anc.py` : `test_presets_anc_valides`, `test_mention_legale_delai_un_an_au_cch`.
- `tests/test_vegetation.py` : `test_preset_elagage_valide`.
- `tests/test_ban_adresses.py` : `test_export_colonnes_ban` (testait l'ajout d'adresse BAN
  dans l'export du **seg_engine** ; l'ingestion/rattachement BAN restent couverts par
  `test_ingest_ban_rattachement` et `test_rattacher_copros_par_adresse`).
- `tests/test_ops_healthz.py` : assertions `catnat` retirées, alignées sur le nouveau
  `CRONS` (test conservé et vert).

Tous ces tests restent récupérables via `archive/vues-m12-5e50113`.

## 3. Conservé (partagé) — et pourquoi

- **Fiche / IA partagée** : `IAStub.tsx`, `useApplySearch.ts`, `api.ts:iaSearch` → `/ia/search`,
  `api.ts:getOrthoEquipements` → tous **conservés** (utilisés par la fiche, pas par Vues).
- **Backend `/ia/search`** + `nl_semantics.py` + `nl_aggregate.py` (routeur IA partagé) —
  conservés (aucune dépendance à `segments`, vérifié par grep).
- **`/ortho/equipements/{idu}`** dans `ortho.py` — conservé (lu par `Fiche.tsx:590`).
- **`moteurs.py`, `rarete.py`, `M22Programme.tsx`, `moteurs.tsx`** — conservés (panneau
  « Modules / Outils » de la fiche ; « moteur » est du marketing, pas un import Vues).
- **`plans.py`** (module partagé) — conservé intact, y compris la constante
  `FILTRES_INTEGRAL` (frozenset vide, documentaire) : retirer un symbole public d'un
  module partagé serait du gold-plating.
- **Toutes les tables socle** : `parcel_equipements`, `parcel_terrain`, `parcel_anc`,
  `parcel_signals`, `spatial_layers`, `dvf_mutations`, `parcel_p_score_v2` — intactes.
  `config/detection_ortho.yaml` et les scripts d'ingestion (`ortho_equipements.py`,
  `anc.py`, `pv_detection.py`, …) conservés (fiche + Flash en dépendent).
- **Tables laissées dormantes en base (code retiré, données intactes, non droppées)** :
  `segment_presets`, `segment_preset_counts`, `ortho_detections`, ainsi que
  `nl_query_log` / `catnat_arretes` / `parcel_residuel_bati` (leur `ensure_tables` et/ou
  DDL restent ; aucun `DROP`).

## 4. Ambigu — laissé en place + rapport

- **`ortho_detections`** est lu par la validation Vues (`/validation`, retirée) **ET** par
  le scoring expérimental `scoring/p_model` (SQL direct, `features.py` / `sql.py`).
  Vérifié : `p_model` lit la **TABLE** directement, jamais le routeur `ortho.py`. Retirer
  les routes `/validation` ne touche donc **ni** la table **ni** `p_model`. La table reste
  en base, intacte. **Résolution : garder la table, retirer seulement les routes** — aucun
  partage cassé.
- Aucun autre point de doute rencontré. Le principe « le doute se résout en gardant » a été
  appliqué (ex. `FILTRES_INTEGRAL`, tables dormantes, scripts socle `parcel_residuel`
  distincts de `parcel_residuel_bati`).

## 5. Vérifications

- **Grep résidus** (`frontend/src`) : `segments | SegmentsPage | nlSegmentsSearch |
  querySegment | Vues` → seules restent 3 lignes de **commentaires-tombstone** (App.tsx,
  api.ts). Aucune référence vivante. Résidus backend (`from .segments`, `nl_segments`,
  `api.segments`) → **0**.
- **Build front** : `npm run build` → `tsc -b && vite build` → **0 erreur TS**, build OK.
- **Import smoke back** : `python -c "import labuse.api.app"` → OK ;
  `import labuse.cli` → OK.
- **Routes (instance :8026)** : `/segments` → 404, `/ia/segments-search` → 404,
  `/ortho/validation` → 404 ; `/ortho/equipements/{idu}` → route présente (404 idu inconnu),
  `/ia/search` → 200.
- **pytest** (`-k "not segment"`, `.venv` + PYTHONPATH worktree) :
  **1113 passed, 18 skipped, 1 failed**. L'unique échec = `test_auth.py::
  test_local_par_defaut_tout_ouvert`, qui **passe en isolation** et **n'a aucun lien avec
  Vues** (grep segment → 0) : artefact d'ordre/pollution de cache de settings sous suite
  complète, **pré-existant et sans rapport avec ce retrait**.
- **Golden** : `qa/golden_check.py` sur :8026 → **116/116 PASS, 0 FAIL, 0 incohérence**.
  Données et scoring intouchés.

## 6. À NE PAS oublier (bascule future « Plein Sud » / « Soley »)

Tout le code Vues (3 modèles extérieurs, moteur, presets, publipostage, validation ortho)
vit à l'identique sous le tag **`archive/vues-m12-5e50113`**. C'est le point de départ du
futur produit dérivé.
