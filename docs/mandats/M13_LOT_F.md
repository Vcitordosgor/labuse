# M13 — LOT F : Sources, tri, scoreur

Branche : `fix/m13-f-lisibilite`, **partie depuis `origin/fix/m13-b-non-livre`** (LOT B) car
F4 réutilise l'autocomplétion BAN de B1 (`AddressAutocomplete`). **F embarque donc les
correctifs de B** — c'est voulu et consigné. Worktree isolé, **non mergé**.

Serveur de preuve : `http://127.0.0.1:8035/socle/` (build du worktree servi, hash JS vérifié).
Playwright : `qa/m13/F/shots.mjs`. Captures sous `qa/m13/F/` (git add -f).

---

## F1 — Sources : simplifier RADICALEMENT (QA-55) — **FAIT (prouvé)**

Réécriture de `components/sources/SourcesPage.tsx`. Tout le vocabulaire de statut a été
**retiré** : « Cadence non sondable », « fiabilité à confirmer », « manuel / grande passe —
non sondable… », « pas encore contrôlée manuellement », les badges de fraîcheur (À jour /
MAJ dispo / Cadence non sondable), le radar (auto/manuel), la ligne « prochaine MAJ »,
l'attribution, la précision mesurée. Supprimés du composant : `BADGE_META`, `fraicheur()`,
`CADENCE_PAR_SOURCE`, `FIABILITE_LABEL`, `attribution()`, `PRECISION_PAR_SOURCE`, la légende
des statuts, l'en-tête « fraîcheur ».

**Deux informations par source, pas plus**, une ligne lisible par source (plus de colonne
étroite, plus d'italique gris sur gris) :

1. **Version en service** — la date de la donnée effectivement en base : `derniere_donnee`
   (« données jusqu'au … ») → sinon le millésime publié par la source → sinon la date
   d'ingestion tracée. Jamais une valeur inventée.
2. **Dernier contrôle** — `source_checks.verified_at` UNIQUEMENT : quand LABUSE a vérifié pour
   la dernière fois que c'est bien la version la plus récente.

**Réponse F1 — date de dernier contrôle absente en base :** `source_checks` n'a jamais été
alimentée (le mandat d'audit data n'a pas tourné), donc `verified_at` est **NULL pour toutes
les sources**. Conformément à la consigne, on **affiche la version seule** et on porte
`Dernier contrôle : —` (jamais de date inventée). Preuve visible dans la capture : toutes les
lignes montrent « Dernier contrôle : — ». Dès que l'audit data alimentera `source_checks`, la
date réelle s'affichera automatiquement — l'intention (« la fraîcheur du contrôle rassure »)
est déjà câblée.

Conservés (non-statut, utiles) : nom de la source, producteur, licence (+ lien texte), lien
« Source officielle ↗ », et le bloc « modèle de scoring » (confiance / détail technique).

PREUVE : `qa/m13/F/f1_sources.png`.

## F2 — Supprimer le bloc « Ce que LABUSE mesure » (QA-56) — **FAIT (prouvé)**

Le bloc `data-sources-preuve` (BAN 99,99 %, jamais de SQL généré, signal ANC) est **retiré
de l'interface**. Contenu **conservé** dans `docs/ARGUMENTAIRE_PRECISION.md` (argumentaire
commercial). Vérification runtime : `data-sources-preuve` = 0 élément, texte « Ce que LABUSE
mesure » = 0 occurrence.

PREUVE : `qa/m13/F/f2_sources_sans_bloc.png` (le bloc a disparu).

## F3 — Barre de tri (QA-57) — **FAIT (prouvé)**

Fichier : `components/panel/ResultsSection.tsx` + libellés dans `lib/strings.ts` (`CLIENT.tri`).

**`×N` — 3 options étudiées, 1 retenue :**
1. **« mutation ×N »** ← **RETENU** (compact pour un bouton de tri ; dit ce que ×N multiplie —
   la propension à muter — sans pavé).
2. « probabilité de mutation » (plus explicite mais trop long pour un chip).
3. « ×N susceptibilité » (terme « susceptibilité » jugé moins immédiat).
Le `title` du bouton porte la sémantique complète : « Trie par le ×N : combien de fois la
parcelle est plus susceptible de muter que la moyenne de l'île ».

**`classement` — libellé du title (dit ce qui est classé) :**
« Classe les parcelles par ordre de priorité (n°1 = la plus prometteuse) — copropriétés en
queue ». (Le libellé du bouton reste « classement ».)

**`commune` — RETIRÉ** de la barre (demande explicite Vic). Retiré de `SORTS` et de
`CLIENT.tri`. Le type `SortKey` conserve `'commune'` côté API (le back le supporte encore ; on
ne casse pas le contrat serveur), mais l'option n'est plus proposée dans l'UI.

**Vérification d'exécution des tris restants** (script `/tmp/f3check.mjs`, top-3 IDU) :
- `classement` → `AB 1908, AP 1647, AP 1610`
- `surface`    → `CR 1231, AB 0785, AZ 0014`  ← **ordre distinct : le tri s'applique bien**
- `mutation ×N`→ `AB 1908, AP 1647, AP 1610`  (identique à `classement` car les 1res parcelles
  sont au plafond ×64 — top-rang = top-mult, comportement attendu et correct).

Runtime : options de tri = `[rang, mult, surface]`, `data-sort="commune"` = 0.

PREUVE : `qa/m13/F/f3_tri.png`.

## F4 — Scoreur « Scorer une adresse » : mise en valeur (QA-54) — **FAIT (prouvé)**

Fichier : `components/outils/ScoreurAdresse.tsx`. Les deux champs + le bouton sont désormais
**groupés dans une seule carte encadrée**, dans l'ordre de lecture :
texte d'aide court (une ligne) → champ adresse (autocomplétion BAN) → champ prix → bouton
pleine largeur « Scorer cette adresse ». Fini le grand vide et le bouton isolé en bas à droite.

**Autocomplétion B1 branchée et vérifiée** : `AddressAutocomplete` (le composant de B) est
bien actif dans le scoreur — saisir « 12 rue » ouvre la liste BAN (capture dédiée).

PREUVE : `qa/m13/F/f4_scoreur.png` + `qa/m13/F/f4_scoreur_autocomplete.png` (liste ouverte).

---

## Vérifications

- `npm run build` → **0 erreur TS** (tsc -b + vite build).
- Golden : `PYTHONPATH=…/worktree/src python qa/golden_check.py` → **116/116 PASS, 0 FAIL**.

## Notes

- F embarque B (autocomplétion) — voulu, cf. Setup.
- Aucune touche au scoring.
- `CLIENT.preuve` et `CLIENT.fraicheur` deviennent inutilisés par l'UI après F1/F2 ; laissés
  dans `strings.ts` (inoffensifs, référencés par l'argumentaire) — non supprimés pour limiter
  la surface de diff.
