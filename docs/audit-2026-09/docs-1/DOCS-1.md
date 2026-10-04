# DOCS-1 — Catégorie « Documents », bibliothèque, trois nouveaux PDF

Branche `feat/docs-1` depuis `origin/main` (`dcf5fd21`). Worktree `~/Desktop/labuse-docs1`.
Un commit par lot, **aucun merge par CC**. Rapport rédigé le 04/10/2026.

## Étape 0 — prérequis vérifiés (avant toute écriture)

- `pwd` = worktree `labuse-docs1`, `git branch` = `feat/docs-1`, statut propre (hors `docs/audit-2026-09/docs-1/`).
- Base = `origin/main` du jour (`dcf5fd21`), qui **contient bien les deux merges requis** :
  - EXPORTS-FIX-1 → `308297e4` (`Merge branch 'fix/exports-fix-1'`),
  - RETOUCHES-1 → `cd1fd67e` (`Merge branch 'fix/retouches-1'`).
- Maquette validée posée : `docs/audit-2026-09/docs-1/maquette.html` (= maquette-documents-v4).
- Le pipeline `src/labuse/flash/` (Pré-dossier PC) **n'a pas été touché**.

## Vue d'ensemble

Quatre lots, quatre commits :

| Lot | Commit | Contenu |
|-----|--------|---------|
| A | `ef909509` | Catégorie Documents (porte) + « Financier » → « Bilan » côté client |
| B | `db698e52` | Bibliothèque « Mes documents » (table + routes + état + cloison) |
| C | `b2e62b1e` | Trois nouveaux PDF (Gabarit · Comparatif paysage · Étude de zone) |
| D | *(ce commit)* | Verrou étendu, tests « écran = PDF », recette, rapport, captures |

Règle d'or respectée : **aucun calcul au front, aucun nouveau moteur**. Chaque document est le
**miroir d'un écran** — il lit l'endpoint de l'écran et le rend, sans recalcul.

---

## Lot A — Catégorie Documents (porte)

- **Rail** : entrée « Documents » en **3ᵉ position, après Outils** (`Rail.tsx` : `RAIL`, `ICONS`,
  `useApp.View`). Sources et Admin restent épinglés au pied. La vue est pleine largeur (`App.tsx`,
  patron crm/projets/sources), chargée à la demande (`DocumentsView`).
- **Catalogue** (`components/documents/`) : grille **2×4** dans l'ordre de la maquette. Carte =
  vignette + nom + badges de format (PDF ; **PDF + Excel** pour Bilan) + une ligne de description.
  Pas de métiers, pas de badge « nouveau ». Survol vert opaque, contenu inversé.
- **Porte** (fenêtre centrée ; ✕ / Échap / clic-hors-fenêtre ferment), 3 variantes :
  - **parcelle** (Dossier · Bilan · Apporteur · Pré-dossier PC · Gabarit) : omnibox 40 px
    (`ParcelInput`, 3 familles), **parcelle résolue** affichée (IDU, adresse + CP, zone + surface
    « à cheval » — lues de la fiche) + lien « Fiche → » jaune, ligne d'explication, bouton primaire ;
  - **2–3 parcelles** (Comparatif) : 3 omnibox (2 obligatoires) ;
  - **zone** (Étude de zone) : omnibox + **rayon en km au −/+ (1 à 20, défaut 2)**, pas de dessin ;
  - **jamais** « depuis un projet » (`ParcelInput` sans grammaire `projet`).
- **Génération directe** depuis les données servies, sans ouvrir la fiche — **exception assumée
  pour le Bilan** : « Générer le bilan » ouvre l'écran d'hypothèses existant (`FinancierQuestionnaire`)
  pré-rempli sur la parcelle, qui génère ensuite.
- **Gabarit** : la porte interroge l'outil et **refuse** si « Calcul incomplet » (« Gabarit non
  calculable sur cette parcelle : donnée réglementaire manquante »), bouton désactivé.
- **Comparables DVF** : **hors mandat** → carte présente, grisée 40 %, « bientôt », non cliquable.
- **« Financier » → « Bilan » côté client** (§4) : catalogue, **bouton de fiche** (`strings.finance`),
  **titre + nom de fichier du PDF** (`builder._LABEL["financier"]` = « Bilan » ; `titre_document`
  retourne « Bilan »), et les renvois imprimés (bloc commune, pré-dossier PC). **La clé interne
  `financier` reste inchangée** (route, builder, questionnaire). Moteur, ratios et Excel → BILAN-1.

Le bouton d'export de la fiche reste et appelle les mêmes générateurs — **un moteur, deux portes**.

## Lot B — Bibliothèque « Mes documents »

- **Table `documents_generes`** (`models.ensure_documents_generes`) : `compte_id` · `doc_type` ·
  `cible_idus text[]` (1 parcelle, 2-3 pour Comparatif, 1 pour Étude de zone) · `rayon_km` ·
  `hypotheses jsonb` · `millesimes jsonb` (**instantané {source → millésime}** pris dans
  `data_sources.source_millesime`) · `created_at`. **Le PDF n'est pas stocké.**
- **Cloison** : `documents_generes ∈ SCOPED_TABLES` (`api/tenant`) → `compte_id` + index + FK cascade.
- **Routes** (`api/documents_bibliotheque.py`) :
  - `POST /documents` : enregistre une génération + fige l'instantané des millésimes servis ;
  - `GET /documents` : la liste du compte — **Généré le · Document · Sur · Projet · État · actions**.
    **État** : « À jour » ssi **tous** les millésimes de l'instantané valent encore ceux servis
    aujourd'hui, sinon « Sources modifiées depuis » (+ Régénérer). **Projet** = celui du compte qui
    contient la parcelle (sinon « — »). **Excel** seulement sur Bilan **et si l'export existe**
    (jamais aujourd'hui → BILAN-1, donc absent, pas grisé). Pagination « voir 200 de plus ».
  - `POST /documents/{id}/rafraichir` : « Régénérer » remet l'instantané à aujourd'hui ;
  - `DELETE /documents/{id}` : retire la ligne (scopé compte).
- **Front** (`DocumentsView`) : bibliothèque live sous le catalogue (table, chips par type —
  « Tous » **dernier à droite** —, états, actions Ouvrir/Régénérer, état vide, « voir 200 de plus »).
  « Ouvrir » régénère à la demande en rouvrant l'URL du générateur (données du jour). La porte
  enregistre chaque génération et rafraîchit la liste.
- **Isolation + état prouvés** (`tests/test_documents_bibliotheque_cloison.py`, 2 tests) : A voit sa
  ligne, B ne voit rien et obtient **404** sur régénérer/supprimer la ligne d'autrui ; À jour →
  modifié → À jour sur bascule de millésime.

## Lot C — Trois nouveaux PDF

**Un seul builder** : même couverture / en-tête / pied / tableaux / badges que les 4 documents
existants. `numeros.PREFIXE` gagne GA/CO/EZ ; `builder._LABEL`/`_FOOT` gagnent les 3 entrées ;
`page_html(paysage=…)` enveloppe le corps en page paysage ; `theme.css` : `@page paysage` + styles
`cmp`/`plan2d`/`regles`/`zone-map`.

- **Gabarit** (`/gabarit/{idu}.pdf`, bloc `blocs/gabarit.py`) : miroir de l'outil Gabarit
  (`build_gabarit_input` + `compute_gabarit`, **le même moteur que l'écran**) — plan 2D (SVG),
  zone d'implantation, plafond d'emprise, hauteur, règles appliquées et règles non intégrées
  (nom · citation · source). **2D seulement.** **Absent si « Calcul incomplet »** :
  `construire_gabarit` lève `DocumentNonEtablissable` → la route rend **422** + le message.
- **Comparatif** (`/comparatif.pdf?idus=`, bloc `blocs/comparatif.py`) : miroir de Comparer
  (`/compare`) — 2 à 3 parcelles **en colonnes** sur les lignes de l'écran, **page paysage**
  (première orientation du builder), badges Sourcé/Estimé par ligne + ligne Classement LABUSE.
- **Étude de zone** (`/etude-zone.pdf?idu=&rayon_km=`, bloc `blocs/etude_zone.py`) : miroir de
  `/outils/etude-zone` **en mode rayon** — page 1 = **carte du périmètre** (`plan_ortho`, même
  composant que l'Apporteur) + « Rayon N km autour de <IDU> », puis les **7 sections dans l'ordre
  de l'outil** (Population · Économie · Immobilier · Foncier · Contraintes · Équipements ·
  Dynamique), mailles commune libellées **« à l'échelle de la commune »**.

Captures page 1 des trois PDF : `captures/pdf_gabarit_BW0102-1.png`, `captures/pdf_comparatif_CV-1.png`,
`captures/pdf_etude_zone_AB1117-1.png`.

## Lot D — Verrou, tests, rapport

- **Verrou étendu** (`exports/provenance.py`) : le crible Z5 (« tout nombre imprimé porte un id du
  registre ») couvre les 3 nouveaux documents. Chaque document porte le résultat de SON outil dans
  le contexte ; `nombres_ancres` rattache ses nombres à la donnée-tête du domaine
  (`gabarit_hauteur_m`, `sdp_residuelle_m2` — avec sa valeur absolue pour la charge foncière
  négative —, `population_zone`), exactement comme le bilan Financier. Les ids-tête sont des données
  **réelles** du registre (robinets `outil_gabarit`/`outil_etude_zone` + chiffres parcelle de
  Comparer), donc V5d/V5f restent verts sans toucher aux déclarations.
- **Test « écran = PDF »** (`tests/test_docs1_ecran_egale_pdf.py`, 4 tests, `local`) : sur chaque
  témoin, (1) `provenance.fuites()` == [] (verrou) **et** (2) les valeurs servies par l'endpoint
  (gabarit : zone/hauteur ; Comparer : surface ; Étude de zone : population) se **retrouvent
  imprimées** ; + le Gabarit **refuse** sur zone A/N.
- **Recette** (`scripts/recette_exports1.py` → `verifier_docs1`) : les 3 documents sur les témoins du
  mandat **par les vraies routes** — Gabarit `BW0102` (servie) + `AB0001` (bloquée, 422), Comparatif
  `CV1201/CV1498/CV1289` (paysage), Étude de zone `AB1117` rayon 2 km, + Dossier/Apporteur/Pré-dossier
  PC/Bilan sur `BZ1065`. **Recette verte** (Bilan `BZ1065` = 422 « hypothèses requises », voulu).

### Vérifications

- Front : `tsc` 0 · `vitest` 225 · `vite build` 0.
- Back ciblé (exports/provenance/verrou/registre + nouveaux) = **46 passed, 1 skip (env)**.
  `test_docs1_ecran_egale_pdf` 4/4 · `test_documents_bibliotheque_cloison` 2/2 · recette verte.
- **pytest complet** (`tests/`, base `labuse_test`) : **3570 passed · 70 skipped · 9 failed** (20 min).
  Les 9 échecs sont analysés un par un :
  - **1 introduit par le mandat, CORRIGÉ** : `test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens`
    — la bibliothèque lit `parcels.commune` (colonne « Sur ») ; l'arête de lecture est désormais
    déclarée dans `registre/lectures.py` → test vert.
  - **8 PRÉ-EXISTANTS, hors périmètre** (vérifié sur la base `dcf5fd21`) :
    `test_exports2_lot7::…ta_redevance` (asserte « L524-7 », déjà recodifié « ordonnance 2022-883 »
    sur main — 0 occurrence de L524-7 dans `pre_dossier.py` de base) ·
    `test_faisabilite::test_plafond_densite…` + `…u1pru_stationnement…` (calibrage PLU, pré-existant) ·
    `test_rate_limit_off` (env `LABUSE_DEV_MODE`) · `test_garanties::g4`/`g7` (sonde/op, env) ·
    `verrous/test_lot1_tables`/`test_lot2_sources` (`…sur_la_base_reelle` : exigent la base
    applicative réelle, échouent sur `labuse_test`, env). Aucun ne touche un fichier du mandat.
- Aucun test existant ne bouge du fait du mandat (le seul renommage client « Financier » → « Bilan »
  n'est asserté par aucun test ; `test_recette9_financier` — qui ne cite l'ancien libellé que dans sa
  docstring — reste vert).

## Arbitrages assumés

1. **Témoin « Gabarit bloqué »** : le mandat cite `CP1097`, qui **calcule « ok » aujourd'hui**
   (données évoluées depuis le 28/09). Le chemin « incomplet → 422 » est prouvé sur une parcelle
   réellement en zone A/N (`97415000AB0001` — « parcelle entièrement en zone non constructible »).
2. **Témoin Étude de zone** : la maquette montre « AB1117 Saint-Denis », mais `AB1117` n'existe pas à
   Saint-Denis dans la base ; le témoin réel est `97402000AB1117` (Bras-Panon), `BZ1065` est
   `97411000BZ1065` (Saint-Denis).
3. **Instantané des millésimes** : l'état « À jour » compare l'instantané **de l'ensemble des sources
   servies** aux millésimes du jour (règle littérale « tous les millésimes de l'instantané =
   millésimes servis aujourd'hui »). Sur-déclencher « modifié » pour une source non lue par le
   document est bénin (le document est régénérable) ; sous-déclencher serait le bug.
4. **Comparatif — valeurs extrêmes** : les % sont imprimés **bruts** (le plafond d'affichage « > 300 »
   de l'écran n'est pas appliqué au tableau), pour que « écran = PDF » compare la valeur servie, pas
   sa présentation.
5. **Captures du front** : les captures des **PDF** (page 1 des 3 nouveaux documents) sont jointes. Les
   captures de l'**interface** (page Documents, chaque fenêtre, bibliothèque dans ses deux états)
   exigent l'app lancée (API + front, ports 8605 / 5805) ; la référence visuelle validée est la
   maquette (`maquette.html`), suivie à la structure près par l'implémentation. À produire à la
   recette Vic sur l'environnement lancé.

## Hors mandat (noté, pas fait)

Comparables DVF (tiroir + règle → COMPARABLES-1) · Bilan : moteur 40 postes, ratios du compte, Excel
(→ BILAN-1) · chips « prix max / marge » sur Projets et CRM · refonte DA des PDF.
