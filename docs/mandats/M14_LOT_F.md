# M14 — LOT F · Vocabulaire et nettoyage

Branche `fix/m14-f-vocab` (worktree isolé, **non mergée**). Base : `main` (35febbb).
Affichage seulement — **aucune touche au scoring**, aucune clé technique modifiée.

## F1 — Retirer « v2 » des verdicts (QA-65)

`« Brûlante v2 » → « Brûlante »`, `« Chaude v2 » → « Chaude »`, et plus largement tout
« v2 » **visible client** dans le vocabulaire de verdict/scoring. **Seuls les `label`
d'affichage changent** : les clés techniques (`brulante`/`chaude`, type `TierV2`,
`tier_v2`/`rang_v2`/`mult_v2`, `key: 'scoring-v2'`, endpoints `/v2/...`, `model_version`,
run-name `q_v2_demo`) sont **inchangées**.

Surfaces touchées (labels/textes visibles) :

| Fichier | Avant | Après |
| --- | --- | --- |
| `lib/status.ts` (`TIER_V2_META`) | `Brûlante v2` / `Chaude v2` | **`Brûlante` / `Chaude`** (source unique des chips de verdict : cartes résultat, filtre multi, légende, CRM, fiche) |
| `components/header/Header.tsx` | panneau « + Filtre » : `Verdict · Scoring v2 (multi)` | `Verdict · Scoring (multi)` |
| `components/map/Legend.tsx` | en-tête légende `Verdict · Scoring v2` | `Verdict · Scoring` |
| `components/panel/ResultsSection.tsx` | tooltip carte `Verdict scoring v2 (P×C)` ; entonnoir + tooltips « brûlantes v2 + chaudes v2 » ; compteur « brûlantes v2 » ; export CSV « tier v2 » | v2 retiré (`scoring`, `brûlantes + chaudes`, `brûlantes`, `verdict`) |
| `components/fiche/Fiche.tsx` | 2 tooltips `scoring v2 (P×C)` + réf. « P v2 » | `scoring (P×C)`, réf. « Probabilité de mutation » |
| `components/fiche/ScoreV2Block.tsx` | 3 titres `Probabilité de mutation (P v2)` + « run du modèle v2 » | `Probabilité de mutation (P)`, « run du modèle » |
| `components/outils/ScoringV2.tsx` | onglet `Brûlantes v2`, message d'erreur `Scoring v2 indisponible` / `Aucun run v2`, tooltip `(P v2)` | v2 retiré |
| `components/outils/registry.ts` | `label: 'Scoring v2 (P)'` + desc « brûlantes v2 » (`key: 'scoring-v2'` gardée) | `Scoring (P)`, « brûlantes » |
| `components/sources/SourcesPage.tsx` | `Modèle de scoring v2 :` (avant `{model_version}` intact) | `Modèle de scoring :` |

Restes intentionnels (non client / techniques) : commentaires de code (`// … tier v2 …`),
clés/endpoints, `q_v2_demo` (nom de run = donnée), `PLANIGNV2` (couche IGN), le JSDoc de
`ScoringV2.tsx`.

**Grep de contrôle** : plus aucun « Brûlante(s)/Chaude(s) v2 » dans un libellé affiché ;
`TIER_V2_META` = `Brûlante`/`Chaude`/`À creuser`/`Réserve foncière`/`Écartée`.

**Preuve** : `qa/m14/F/f1_verdicts_sans_v2.png` — panneau « + Filtre » titré
« VERDICT · SCORING (MULTI) », chips « Brûlante / Chaude / Réserve foncière / À creuser /
Écartée » sans v2 ; à gauche, cartes de résultat et compteur « 120 brûlantes · 1031
chaudes · … » sans v2. (Confirmé aussi sur `f2_sans_chercher_plus.png` : chips de cartes
projet « Brûlante » / « Chaude » / « À creuser ».)

## F2 — Supprimer « + Chercher plus » (QA-52, 3e demande)

Le bouton devait partir en M13-E2 (non mergé sur main). Retiré des deux surfaces projet :

- `components/projets/ProjetKanban.tsx` : bouton `+ Chercher plus` supprimé ; mutation
  `elargir` (appel `chercherPlus`) + state `msg`/`setMsg` retirés ; import `chercherPlus`
  retiré ; texte de colonne vide « Rien à trier — « Chercher plus » » → « Rien à trier pour
  l'instant ». **Remplacé** par la phrase (via `strings.ts`).
- `components/projets/ParcoursTinder.tsx` : bouton `+ Chercher plus` et son panneau
  (`Élargir la recherche` + ajout IDU manuel, mutations `elargir`/`ajouter`, states
  `plusOpen`/`iduInput`/`plusMsg`, effet clic-carte) supprimés ; imports `chercherPlus`/
  `ajouterParcelle` retirés. **Remplacé** par la phrase.

**Phrase (nouvelle clé `CLIENT.projet.ajouterDepuisFiche` dans `lib/strings.ts`)** :

> « Une parcelle en tête ailleurs ? Ajoutez-la à ce projet à tout moment depuis sa fiche,
> avec le bouton « Projet ». »

Note : les fonctions API `chercherPlus`/`ajouterParcelle` (`lib/api.ts`) et les endpoints
backend restent en place (aucun retrait serveur demandé) ; elles ne sont simplement plus
appelées côté front.

**M13-E1 (peuplement des colonnes)** : sur main, l'ouverture d'un projet appelle déjà
`proposerProjet(pid)` (idempotent, `ProjetKanban`/`ParcoursTinder`) → les colonnes se
peuplent au lancement. Vérifié en pratique : « Projet Beta » affiche 25 parcelles dans « À
trier » sans aucune action « chercher plus ». **Le manque signalé au mandat n'est donc pas
observé sur cette base.**

**Preuve** : `qa/m14/F/f2_sans_chercher_plus.png` — kanban « Projet Beta » : en-tête
sans « + Chercher plus » (seuls Exporter / Renommer / Archiver), phrase affichée sous le
titre, colonne « À trier · 25 » peuplée.

## Vérification

- `npm run build` (`tsc -b && vite build`) → **0 erreur TS**, bundle servi = build de ce
  worktree (`index-DtetgQ18.js`).
- Golden (`qa/golden_check.py`, API 8043) → **116/116 PASS, 0 FAIL**.

## Captures

- `qa/m14/F/f1_verdicts_sans_v2.png`
- `qa/m14/F/f2_sans_chercher_plus.png`
- scripts : `qa/m14/F/shots.mjs`, `qa/m14/F/shots_f1.mjs`
