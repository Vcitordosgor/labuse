# OUTILS-FIX-5 — Les 17 outils lisent la même donnée que la fiche

**Exécuté par :** CC (Opus), 20/09/2026.
**Branche :** `feat/outils-audit-2`, rebasée sur **`edcebed7`** (main, contient REBRANCHEMENT-1 : correctif N/Nerl).
**Départ :** `6f4c3f44` (rapport OUTILS-AUDIT-2) → rebasé → `445ef6b9`. **Sept commits, un par lot.**
**Environnement :** API `:8065` (.venv du checkout principal, PYTHONPATH worktree), Vite `:5265`, `LABUSE_API_DEV` dessus. Parcelle témoin **97410000AN0347** (Saint-Benoît, zone N, COMMUNE DE SAINT BENOIT).

Le principe : un chiffre affiché par un outil est le même que celui de la fiche parcelle sur la même parcelle — même id du registre, même valeur, même libellé. À la fin, un verrou (V5f) l'impose.

## Les cinq divergences de l'audit → 0

| # | Divergence (audit OUTILS-AUDIT-2) | État avant | État après | Lot |
|---|---|---|---|---|
| 1 | Taux TA communal (AN0347) | fiche 5 % public / outil « à saisir », total null | outil sert **5 % public**, total **6 690 €/100 m²** = fiche §7 = Financier (même `taux_communal_public(idu[:5])`) | 2 |
| 2 | Étiquette zone (AN0347) | fiche « Nerl » (confetti 7 m²) / outil « N » | fiche + Faisabilité + Comparer + Risques = **« N »** (token, REBRANCHEMENT-1) — zéro confetti | 3 |
| 3 | Propriétaire (entrée IDU du Scan) | fiche COMMUNE DE SAINT BENOIT / Scan « pas de PM » | Scan lit `proprietaire_moral.siren` (id fiche §1) → **COMMUNE DE SAINT BENOIT 219740107** ; PP → « pas de PM » ; adresse → LE CONVIVIAL | 1 |
| 4 | Neuf VEFA Évolution | 1 304 €/m² sur 6 ventes / « — » ailleurs | seuil `neuf_vefa_seuil()`=8 appliqué → **« — » (6 < 8)** des deux côtés | 5 |
| 5 | « Dormants » commune | 103 (fiche, pc_caducs) vs 651 (outil, point mort) sous le même mot | **un seul id** : la fiche commune sert désormais `permis_point_mort` (point_mort_n), le MÊME que l'outil → même mot « Permis dormants », même chiffre. Vocabulaire RETOURS-17 préservé | 5 |

## Les sept lots

**Lot 1 (`d9821a04`) — Scan patrimoine.** `ScanPatrimoine.tsx:ownerDeIdu` lisait `f.owner_siren` à la RACINE du payload (inexistant : n'existe que sous `score_v`), le cast masquait l'erreur au compilateur → toute entrée IDU/adresse rendait « pas de PM ». Corrigé sur `f.proprietaire_moral.siren` = l'id de la fiche §1 (`app.py:3839`, registre `type_proprietaire`). Mesuré : IDU AN0347 → COMMUNE DE SAINT BENOIT 219740107 ; IDU PP → « pas de PM » ; adresse « 6 Rue Bagatelle » → LE CONVIVIAL 848600151.

**Lot 2 (`283ff0ed`) — Taxe d'aménagement.** Le prefill renvoie désormais `insee` + le taux communal PUBLIC daté, résolus par `taux_communal_public(db, idu[:5])` — le MÊME appel que la fiche §7 (`_taxe_amenagement_block`) et le Financier (`exports/builder.py:217`). Le front envoie `insee` : le back applique le taux public, total chiffré sans aucune saisie. Le champ « taux obligatoire » devient un affichage lecture seule ; la saisie manuelle ne reste qu'en repli (commune sans taux public).

**Lot 3 (`135a368a`) — Zone (vérification).** REBRANCHEMENT-1 (lot 0) a rebranché la fiche `_reglement_plu_block` sur le token (premier mot du libellé GPU = `faisabilite/zone_servie._TOK`), plus jamais par `subtype`+`max(libelle)`. Vérifié sur AN0347 (dominante N 99,8 % + confetti Nerl 0,2 %) : fiche règlement=N, Faisabilité=N, Comparer=N, Risques=N ; PLU/Étudier n'affichent pas d'étiquette de zone. Aucun lecteur au confetti ne subsiste → aucun rebranchement à faire (le mandat interdit refonte/extraction). Preuve reproductible `captures/outils-fix5/L3-zone-preuve.py` (VERT).

**Lot 4 (`088bbe62`) — Les quatre vestiges.** (a) *Étudier un bien* : lecture morte de `score_e` retirée (interrogée à chaque requête pour `prix_probable`, seul consommé dans la branche prix que le front n'atteint jamais). (b) *Faisabilité* : `fiscal.ta_note` « taux non ingéré » retirée (fausse depuis TA-1). (c) *Comparer* : `contrainte_majeure` REBRANCHÉE (calculée depuis `qv2.lines`, même id que la fiche, mais absente du payload depuis e6b7b5bb) → AN0347 « Exclue : PPR zone rouge (inconstructible) — 100 % ». (d) *Risques* : doublon ZNIEFF supprimé (append géométrique redondant avec la couche cascade) — gardé en REPLI (backfill cascade partiel), zéro doublon (AN0347=1), zéro régression (BC0103=2 ZNIEFF distinctes). Tests `test_scoreur` alignés.

**Lot 5 (`cca8310d`, revu en validation finale) — Deux divergences.** VEFA : `_barometre_data` applique le même `neuf_vefa_seuil()`=8 que le comparateur ; sous le seuil, « — » + le n dit. Dormants : **tranché pour l'unification (un seul id)** — la fiche commune (`fiche_commune.permis_bloc`) lit désormais `permis_point_mort` (point_mort_n), le MÊME moteur/id que l'outil Permis, au lieu de compter `pc_caducs`. Résultat : « Permis dormants » = même mot ET même chiffre des deux côtés (cœur d'OUTILS-FIX-5), le vocabulaire unique RETOURS-17 est préservé (le premier réflexe « deux mots caducs/dormants » a été abandonné : il créait deux vocabulaires et contredisait la décision produit RETOURS-17).

**Lot 6 (`3b8402ad`) — Successions (M28) + Blocs (M29) au registre.** Robinets `outil_successions`/`outil_blocs_fonciers` déclarés ; chiffres `n_successions_veille` (Score V, réservoirs PM+INPI RNE), `n_blocs_pm`/`n_parcelles_bloc` (nouveau moteur `blocs_fonciers`), + réutilisation `sdp_residuelle_m2`/`type_proprietaire`. Fiches de règle `regles/n_successions_veille.py`, `regles/n_blocs.py` (CIRCUIT-4). Effet : « INPI RNE » → Outil · Successions ; « DGFiP PM » → Outil · Blocs + Successions dans `/sources/rattachements`. Verrous V5b/V5c/CIRCUIT-4 verts (partages déclarés en NON_SONDES).

**Lot 7 (`ad520ffb`) — Verrou V5f.** « Tout chiffre affiché par un outil porte un id du registre. » Recensement `captures/outils-fix5/L7-recensement.txt` : 17 outils, 52 chiffres, tous des ids ; lectures partagées (`sdp_residuelle_m2`, `type_proprietaire`, prix/vélocité communes) portent leur raison NON_SONDES. Verrou `verrou_outils_registre` (registré dans VERROUS) : lit les 17 clés VISIBLES de `registry.ts`, vérifie que chacune a son robinet et que ce robinet ne sert que des chiffres déclarés. Prouvé CASSÉ sur une lecture directe construite, VERT sur les 17 outils.

## Preuves

`captures/outils-fix5/` : L1 (Scan PM/PP/adresse), L2 (Taxe 5 % public + total), L3 (fiche zone N + script), L4 (Comparer contrainte majeure, Risques, `L4-vestiges-preuve.txt`), L5 (VEFA « — », `L5-divergences-preuve.txt`), L6 (`L6-registre-preuve.txt`), L7 (`L7-recensement.txt`).

## Validations

- **tsc -b** : vert.
- **Tests ciblés** : `test_scoreur` 6✓, Lot 4 (85), Lot 5 (220), registre/CIRCUIT-4/V5 verts. Échecs restants (`exposition_versant` passe_plat sans table ; `Trace zone_plu_famille` dans Fiche.tsx) PRÉ-EXISTANTS sur `edcebed7` (vérifiés par checkout).
- **V5f** : cassé (lecture construite) → vert (17 outils), 12 tests V5.
- **labuse circuit verrous -w G8** : voir `docs/audit-2026-09/OUTILS-FIX-5-VERROUS.txt`.

## Note d'exploitation

Le redémarrage répété de l'API pendant les tests navigateur a laissé des connexions **idle-in-transaction** orphelines (requêtes fiche/zone en vol au moment du SIGTERM) qui, par un `ALTER` du lifespan sur la base partagée, ont formé un convoi de verrous bloquant le démarrage. Résolu par `pg_terminate_backend` ciblé sur les connexions **prouvées miennes** (owner = mes process uvicorn du jour, via lsof sur le port client), jamais par `kill -9` (qui aggrave l'orphelin — cf. mémoire). Leçon reprise : ne pas empiler les redémarrages d'API ; un seul, après confirmation que le port est libre.
