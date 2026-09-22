# DASHBOARD-4b — D3 complet : la source et tout ce qu'elle nourrit (rapport)

Branche `feat/dashboard-4b` depuis `origin/main` (`5baef194`, DASHBOARD-4 mergé). Un commit
par lot, branche poussée. Ports :8135/:5335. `.env` dry-run (Brevo/SMTP neutralisés).

D3 avait été coché sur CIRCUIT-SOURCES-1 (3 blocs : Couches · Fiche · **Ailleurs** fourre-tout).
Ce mandat exploite ce que V5d/V5e/V5f + le miroir permettent depuis le 20/09.

Commits : L1 `66017bc0` · L2 `fd399b19` · L3 (ce rapport + test).

## Lot 1 — Sept blocs distincts par source (plus jamais « Ailleurs »)
Le détail d'un réservoir montre **7 blocs toujours présents** (vide → « aucun ») :
Couches carte · Sections de la fiche parcelle (V5d) · Cartes de la fiche commune (V5e) ·
Outils (V5f) · Documents (Dossier · Financier · Apporteur · Pré-dossier) · Copilote · Radar.
Chaque ligne (hors couche) est **cliquable vers l'élément** (ouvre son détail robinet = ses
sources, sens inverse). `« Ailleurs »` a disparu.

- Backend `/sources/rattachements` → 6 blocs `{ligne, cible, rid}` (7e = couches via
  `/sources/couches`). `src/labuse/api/app.py:5578`. Catégorie de robinet → bloc ; surfaces
  internes (page_client/projets/crm/notification/admin) hors des 7 blocs client.
- Front `Detail.tsx:232` (composant `Bloc`), types `SourceRattLigne`/`SourceRattachements` (api.ts).
- **Preuve** `captures/dashboard4b/lot1-{dvf,ppr,cadastre,sitadel,cosia}.png` : 7/7 blocs, 0 « Ailleurs ».
  DVF : parcelle 23 · commune 7 · outils 16 · documents 9 · copilote 1 · couches 1 · radar 0.

## Lot 2 — Le sens inverse (élément → sources), par recherche
Depuis une couche · section de fiche · carte commune · outil (· document · copilote · radar) :
la liste de ses **sources**, cliquables vers leur détail. **Accessible par recherche** sur la
page Données (onglet Circuit), pas seulement par lien profond. Ce sens vit ICI seulement.

- Backend `/sources/par-element` → `{elements:[{id, nom, categorie, sources[]}]}` (`app.py:5644`) :
  inverse de rattachements (robinets) + inverse de `/sources/couches` (couches). **147 éléments**
  (54 couches · 32 outils · 22 sections parcelle · 21 cartes commune · 10 copilote · 7 documents · 1 radar).
- Front `SensInverse.tsx` (onglet Circuit, `Circuit.tsx:175`) : recherche → sources en pastilles,
  clic → détail réservoir (nom → id via `data.reservoirs`).
- **Preuve** `captures/dashboard4b/lot2-inverse-{outil,section,couche}.png` + `lot2-clic-source.png` :
  « Faisabilité » → 6 sources · « Zonage » → « Lettre de zonage » ← Urbanisme PLU/GPU · « Aléa
  inondation » → Géorisques · clic source → détail réservoir ouvert.

## Lot 3 — Cohérence (test)
`tests/test_dashboard4b_rattachements.py` (3 tests, **passés**) — pour DVF · PPR · cadastre ·
Sitadel · CoSIA :
1. `test_rattachements_7_blocs_egaux_aux_declarations` — chaque bloc AFFICHÉ == bloc RE-DÉRIVÉ
   indépendamment du registre (ensembles identiques, bloc par bloc).
2. `test_total_affiche_egal_total_calcule` — total des 7 blocs affiché == total calculé (> 0).
3. `test_par_element_est_l_inverse_de_rattachements` — forward/reverse cohérents (une source d'un
   élément côté forward est bien listée côté reverse).

## Vérifications finales
- **`tsc -b` vert.**
- **`pytest tests/`** : **3103 passed, 2 failed, 66 skipped** (16 min). Les 2 échecs sont
  PRÉ-EXISTANTS / environnementaux — `test_backup` (outillage pg local) et
  `tests/verrous/test_lot1_tables` (V1c : tables orphelines `score_labuse`/`score_labuse_runs`/
  `ingestion_delta` de la base DEV PARTAGÉE, absentes du code). Aucun dans le périmètre 4b (qui
  ne touche que `api/app.py` — 2 endpoints lecture seule — + le front Circuit + 1 test). Les 3
  tests `test_dashboard4b_rattachements` passent.
- **Forward « cliquable vers l'élément »** vérifié : depuis le détail DVF, clic sur la ligne
  « Charge foncière → Faisabilité » ouvre l'élément « Faisabilité » et ses 6 sources (BD TOPO ·
  Cadastre · CoSIA · DVF · Urbanisme PLU/GPU · RTAA DOM). `captures/dashboard4b/lot1-clic-element.png`.
- **`labuse circuit verrous -w G8`** : inchangé par 4b (aucune logique de verrou touchée) — seul
  V1c reste cassé (artefact base partagée, hors périmètre).
- « Ne merge pas ».
