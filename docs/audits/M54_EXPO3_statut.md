# M54-EXPO-3 — Le dernier lot (watch-zones UI + Compare)

Branche `feat/m54-expo-3` (worktree `~/Desktop/labuse-m54c`, base main 0def0f60 = expo-2 mergé,
précondition vérifiée). Un commit par item. Captures gitignorées `qa/m54c_captures/`.

## FAIT & validé

| Item | Endpoints | Commit | Validation |
|---|---|---|---|
| **Watch-zones UI** | `/watch-zones` (GET/POST/**PATCH new**/DELETE), `/alertes*` | 20b9f4d1 | Entrée Rail « Veilles » → panneau en surimpression (carte conservée) : dessin via l'outil `zone` de MapView → POST /watch-zones ; liste zones (renommer/supprimer) ; nouveautés `dvf_in_zone` (rafraîchir + accusé). Capture `veilles.png` (1 zone + alertes). Tests : e2e create→DVF→alerte→ack + **rename** (PATCH → GET reflète, 404 inconnu). 8 verts |
| **A8 Compare** | `GET /compare` | e78ddf47 | Panneau côte à côte (max 3), lignes = chiffres clés RÉUTILISANT les idiomes de fiche (verdictMeta = verdict client, €/m²) : surface, zone, capacité, SDP max/résiduelle, charge foncière, marché (CA), contraintes. Entrées : fiche « ⇄ Comparer » + shortlist (⇄). Capture `compare.png` (3 colonnes). Backend `_compare_row` expose tier_v2/etage0 |

Build vert, `tsc` vert, **38 tests backend verts** (alertes + audit_secu).

## Nouveautés backend (périmètre front + routes app.py)
- `PATCH /watch-zones/{id}` (rename, SEC-IDOR) + `alertes.rename_watch_zone` — le panneau demande de renommer.
- `_compare_row` : ajout `tier_v2`/`etage0`/`rang_v2` (le verdict CLIENT dérive du tier côté front).

## A9 — /filters : SUPERSEDED (arbitrage appliqué, non branché)
`GET/POST /filters` + `DELETE /filters/{id}` restent **orphelins par décision** : la
fonctionnalité « filtres sauvegardés serveur » est déjà couverte par **« Mes vues »**
(`FiltreLabuse.MesVues` → `/events/searches`). Brancher `/filters` créerait une 2ᵉ UI concurrente.
**Statut : superseded, candidat au retrait futur** (ou migration de « Mes vues » vers `/filters`
pour un stockage lossless — décision Vic, hors de ce lot). Non touché.

## Bilan M54 (INV → EXPO 1/2/3)
Le front est désormais entièrement atteignable ; côté backend, les orphelins user-facing du
rapport M54-INV sont branchés (one-pager, SPF, pré-dossier ZIP, feedback, explain, statuts
dossier/courrier, marque blanche, shortlist, compare, watch-zones) ; les faux orphelins ont été
requalifiés INTERNE (division/compute, admin ops) ou SUPERSEDED (/filters). Reste volontairement
fermé : API v1, rails retirés.
