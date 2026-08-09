# M54-EXPO-2 — Statut

Branche `feat/m54-expo-2` (worktree `~/Desktop/labuse-m54b`, base main 0592b959 = lot 1 mergé).
Un commit par item. Captures gitignorées `qa/m54b_captures/` (harnais `qa/m54b_capture.mjs`).

## FAIT & validé

| Item | Endpoint(s) | Commit | Validation |
|---|---|---|---|
| **Explain** (« Synthèse IA ») | `GET /parcels/{idu}/explain` | 344868f5 | Capture : synthèse **validée** (mock, sans badge) ET **stub** réel (badge « repli » + libellé de repli visibles) — validation #3 ✓ |
| **Volet C — statuts** | `/dossier/statut`, `/courrier/statut`, `/courrier/envois` | 9b4364a9 | Tuile Dossier = compteur quota (illimité en Intégral, chiffre en Essentiel) ou grisée si 501 ; M09 = ligne prestataire + journal des envois repliable. Barre 7 tuiles NON réordonnée |
| **Watch-zones — dédup** | `compute_alertes` (alertes.py) | 12ad9a06 | Kind `permit_near_followed` RETIRÉ (arbitrage Vic) ; **test JUMEAU** `test_permis_ne_passe_plus_par_ce_canal` : parcelle suivie + permis à 50 m → 0 alerte permis (clé absente). Tail permis de `test_idor_alertes_watch_zones_cloison` converti en preuve d'absence. 8 tests verts |
| **A6 — Marque blanche** | **NEW** `GET /moi/marque` + `/moi/logo`, `/moi/marque` | d6374834 | GET ajouté (round-trip fidèle) + widget upload dans le menu compte (réservé mode=compte). **Test round-trip** `test_marque_roundtrip_logo_relu` : upload → GET relit logo+champs ; suppression reflétée (validation #4 ✓, au niveau API car /moi/* exige un compte réel) |
| **A7 — Shortlist** | `GET /shortlist` | 3fc33376 | Toggle « ★ Shortlist du jour » dans l'en-tête RÉSULTATS ; capture : **8 sujets** cliquables (→ fiche) ✓ |

Build vert, `tsc` vert, 44 tests backend verts (alertes + audit_secu + marque).

## A9 — Filtres serveur : REDONDANT (à arbitrer, non branché)

**Mesure (comme division/compute au lot 1) :** le front a DÉJÀ une fonctionnalité de filtres
sauvegardés côté serveur — **« Mes vues » (`MesVues`, FiltreLabuse.tsx)** — qui enregistre/liste/
supprime/renomme des combos de filtres nommés via **`/events/searches`** (stockage = hash d'URL).
`/filters` (A9) fait la MÊME chose avec un `params` dict (lossless vs le hash lossy). Brancher un
2ᵉ bouton « Enregistrer ce filtre » créerait **deux UI concurrentes** de sauvegarde de filtres.

**Options (décision Vic) :**
1. **Ne rien brancher** — `/filters` est couvert fonctionnellement par « Mes vues ». (recommandé si on ne veut pas deux chemins)
2. **Migrer** « Mes vues » de `/events/searches` (hash lossy) vers `/filters` (params lossless) —
   vrai gain, mais `/events/searches` alimente aussi les veilles → découplage à cadrer.

Pas de duplication unilatérale : je m'arrête pour arbitrage (comme pour division/compute).

## RESTE À FAIRE (mappé, non branché)

| Item | État | Plan |
|---|---|---|
| **Watch-zones — UI** | backend **FAIT** (dédup) ; UI restante | Réutiliser l'outil de dessin polygone `zone` existant (MapView `tool==='zone'` → `setZone`, `onDbl` ferme le polygone) : au close, POST `/watch-zones {name, geometry:{type:'Polygon',coordinates:[[...zone,zone[0]]]}}` ; panneau « Mes veilles » (nouvelle `View 'veilles'` + entrée Rail façon `openSources`) listant `/watch-zones` + `/alertes?only_new` + `POST /alertes/ack` + `POST /alertes/refresh`. Helpers api.ts à ajouter. ⚠ l'outil `zone` est désactivé en « Toute l'île » (exige une commune — cohérent backend) |
| **A8 — Compare** | non commencé (le plus lourd) | Page/panneau comparaison : sélection de 2-3 parcelles (depuis fiche/shortlist) → `GET /compare` → rendu côte à côte en RÉUTILISANT les composants de fiche (pas de nouveau DS). Nouvelle `View 'compare'` + un store de sélection |

## Note
Backend sert `parents[3]/frontend/dist` (worktree) ; plan via `LABUSE_PLAN_DEFAUT`. Toujours
vérifier le hash servi après reboot (un backend périmé qui garde :8000 sert l'ancien dist).
