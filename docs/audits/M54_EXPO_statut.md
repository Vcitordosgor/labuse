# M54-EXPO — Statut d'avancement

Branche `feat/m54-expo` (worktree, STOP review Vic — CC ne merge jamais). Un commit par endpoint.
Preuves visuelles : `qa/m54_captures/` (gitignoré) via `qa/m54_capture.mjs` (rejouable).

## FAIT & validé (captures jointes)

| Item | Endpoint | Commit | Où | Validation |
|---|---|---|---|---|
| **B — mesure** | — | d2aa2c4a | `docs/audits/M54_EXPO_voletB_mesure.md` | explain=différent→brancher ; watch-zones=complémentaire→UI proposée, STOP Vic |
| **A1 One-pager** | `GET /parcels/{idu}/export?format=onepager` | 7eaf95d4 | rangée « documents » sous la barre 7 tuiles (non réordonnée) | capture `fiche-exports-integral.png` ✓ |
| **A2 Courrier SPF** | `GET /parcels/{idu}/spf-letter` | 1e301b12 | tiroir Propriétaire, là où l'UI promettait « workflow SPF/CERFA » (personne physique) | capture `fiche-spf-phys.png` ✓ |
| **A3 Pré-dossier PC** | `GET /pre-dossier/{idu}.zip` | 45f42964 | rangée documents, **gaté Intégral** (getMoi) | Intégral=lien actif ; Essentiel=tuile grisée + backend **403** vérifié — captures integral/essentiel ✓ |
| **A4 Feedback** | `POST /feedback` | a304179f | bande discrète sous les exports (idu+verdict good_lead/not_interested/false_positive + mot) | capture `fiche-feedback-integral.png` ✓ |

Chaque commit : helper api.ts + libellés `strings.ts` + composant, `tsc` vert, `npm run build` vert.
Test plan (mandat) : compte Essentiel vs Intégral sur le ZIP = **concluant** (grisé + 403 côté serveur).

## CORRIGÉ — reclassé, NON branché (respect des Interdits)

- **A5 « Division compute » (`POST /modules/division/compute`)** : **PAS un orphelin — c'est de
  l'INTERNE/ops**. L'endpoint est `exiger_admin(request)` et sa docstring dit mot pour mot :
  « écrivain lourd (DELETE+INSERT PostGIS commune entière), **aucun appelant front — c'est un
  recalcul d'ops, pas une action client** » (modules.py:81). Le rapport M54-INV l'avait rangé en
  ORPHELIN à tort (le gate admin est un `exiger_admin` dans le corps, pas un `Depends`). Les
  Interdits du mandat interdisent de toucher aux INTERNES → **non branché, à requalifier INTERNE**.

## RESTE À FAIRE (mappé, prêt — pas encore branché)

| Item | Endpoint | Effort | Point d'insertion repéré |
|---|---|---|---|
| **A6 Marque blanche** | `POST/DELETE /moi/logo`, `POST /moi/marque` | moyen — ⚠ **il manque un GET** pour relire logo/marque (préremplir/prévisualiser) : à ajouter côté backend d'abord | widget upload dans le menu compte (Header.tsx AccountMenu ~479) ; « reliquat UI upload » M23 |
| **A7 Shortlist** | `GET /shortlist` | moyen | onglet/entrée dans les résultats (panneau liste) |
| **A8 Compare** | `GET /compare` | page (le plus lourd) | nouvelle surface comparaison, entrée depuis fiche/shortlist |
| **A9 Filtres serveur** | `GET/POST /filters` + `DELETE /filters/{id}` | moyen | « Enregistrer ce filtre » dans le panneau filtres (FiltreLabuse) ; URL=partage, serveur=mes filtres (coexistence) |
| **B′ explain** | `GET /parcels/{idu}/explain` | petit-moyen | bouton « Synthèse IA » sur la fiche (prose IA + repli règles). ⚠ caveats : appel Anthropic (coût) + **pas de gate quota** aujourd'hui — à aligner avec Vic sur la porte IA avant expo |
| **C Partiels** | `/dossier/statut`, `/courrier/statut`, `/courrier/envois` | petit | afficher l'état (en cours/prêt/échec) là où les boutons existent déjà |
| **B watch-zones/alertes** | `/watch-zones*`, `/alertes*` | **BLOQUÉ** | UI minimale proposée dans le rapport B — **arrêt pour arbitrage Vic** (dédup permis vs cloche) |

## Note technique
Piège rencontré : un backend M-W périmé tenait `:8000` (bind refusé) → il servait l'ancien
`frontend/dist` (sans les boutons). Toujours vérifier le hash servi (`grep One-pager` sur le
bundle) après reboot. Le backend sert `parents[3]/frontend/dist` (worktree), plan via
`LABUSE_PLAN_DEFAUT=essentiel|integral`.
