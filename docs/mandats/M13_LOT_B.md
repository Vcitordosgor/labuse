# M13 — LOT B : « non livré » repris et prouvé

Worktree isolé, branche `fix/m13-b-non-livre` (base = `main`). Aucun merge.
App servie sur `http://127.0.0.1:8031/socle/` (dist reconstruit avant chaque capture).
Captures : `qa/m13/B/` (ajoutées de force, `git add -f`).

Golden : **116/116 PASS, 0 FAIL** (API rebootée après le changement backend).
Build frontend : `tsc -b && vite build` → **0 erreur TS**.
Tests backend ciblés : `test_crm_columns` + `test_ban_adresses` + `test_adresses_autocomplete` + `test_scoreur` → **22 passed**.
Aucun `window.prompt/confirm/alert` restant dans `frontend/src` (seuls des commentaires les mentionnent).

---

## B1 — Autocomplétion d'adresse (barre principale + « Scorer une adresse ») — **FAIT / PROUVÉ**

### Cause racine
1. L'omnibox (`Header.tsx` → `Omnibox`) n'utilisait PAS `AddressAutocomplete` : un `<input>` nu qui ne
   déclenchait la BAN que sur **Entrée** — aucune suggestion au fil de la frappe.
2. `AddressAutocomplete` faisait un **fetch navigateur** vers `https://api-adresse.data.gouv.fr`
   (peut échouer / être bloqué).
3. Même quand la liste s'ouvrait, elle était **clippée** : le menu déroulant (`absolute`) était rogné par
   un ancêtre `overflow-hidden` (le conteneur de contenu sous l'en-tête). Diagnostic Playwright : `<ul>`
   présente au DOM (6 `<option>`), z-50, bg opaque, MAIS invisible à l'écran (clippée à ~10 px).

### Correctifs
- **Nouvel endpoint interne** `GET /adresses/autocomplete?q=…&limit=6` (`src/labuse/api/app.py`) :
  interroge la table `adresses` (BAN rattachée aux parcelles, ~339 920 lignes idu+geom). Match
  insensible casse ET accents via `translate()` (l'extension `unaccent` n'est pas installée sur ce
  serveur — vérifié). Chaque suggestion porte **label normalisé + lon/lat + idu** → atterrissage direct.
- `banAutocomplete` (`frontend/src/lib/api.ts`) appelle désormais l'endpoint interne (plus de fetch externe).
- `AddressAutocomplete` : dropdown **rendu en portal** (`createPortal` → `document.body`, `position: fixed`
  calculé sur le rect de l'input) → échappe à tout ancêtre `overflow-hidden`. `AddressSelection` porte l'`idu`.
- Omnibox (`Header.tsx`) : câblé sur `AddressAutocomplete`. Suggestion choisie → landing direct sur
  `sel.idu` (repli `parcelAt`). Entrée sans suggestion → repli commune → IDU (`onEnterRaw`). Raccourci « / » conservé.
- `ScoreurAdresse` : déjà branché sur `AddressAutocomplete` — bénéficie du portal + endpoint interne.

### Repro
- Barre principale : taper `general bigeard` → liste de 6 suggestions réelles sous le champ → clic → fiche `97422000BY0162`.
- Outils → « Scorer une adresse » : taper `rue leperlier` → 6 suggestions « Rue Leperlier, Entre-Deux (97414) ».

### Preuves
- `qa/m13/B/b1_omnibox_suggestions.png` — omnibox, 6 suggestions réelles visibles (au-dessus du contenu).
- `qa/m13/B/b1_scoreur_suggestions.png` — Scoreur d'adresse, 6 suggestions réelles visibles.
- (Landing vérifié en test : clic suggestion omnibox → fiche parcelle ouverte.)

---

## B2 — Voir tous les résultats — **FAIT / PROUVÉ**

### Cause racine (diagnostic)
La liste des résultats (île) est paginée serveur (200/page, « Charger plus ») ET **atteint bien le
dernier résultat** — l'accumulation par offset est correcte (vérifié : offsets 0…1000 = 1151 = total stats).
Le bug était le **compteur « … au total »** : il utilisait `stats.data.total` calculé sur `scopeOnly`
(les filtres de périmètre AVEC les tiers **retirés** — nécessaire pour les cartouches par tier). Résultat :
avec un filtre Brûlante/Chaude actif on affichait « **259 affichées / 51 129 au total** » — le total
ignorait le filtre tier, laissant croire que 50 000 résultats restaient cachés.

### Correctif
`ResultsSection.tsx` : quand un filtre tier est actif (île), on requête un total **avec les filtres
complets** (`filteredStats`, `getStats(filters)`) et `total` = ce total filtré ; sinon le total de
périmètre suffit (pas de requête supplémentaire).

### Repro
Deep-link `#f=1&tv=brulante,chaude&cs=Saint-Paul&v=1` (île, filtre Brûlante+Chaude, secteur Saint-Paul) :
- avant chargement : « 200 affichées / **259** au total » + « Charger plus » ;
- 1 clic « Charger plus » → « **259 affichées / 259 au total** », plus de bouton « Charger plus ».

### Preuves
- `qa/m13/B/b2_tous_affiches.png` — liste défilée au bout, compteur « 259 affichées / 259 au total ».
- `qa/m13/B/b2_compteur_zoom.png` — zoom du compteur (259/259, plus de « Charger plus », CSV seul).

---

## B3 — CRM personnalisable — **FAIT / PROUVÉ**

### Cause racine
Le backend `crm_columns.py` (create/rename/reorder/delete/reset) était **correct** et déjà câblé au
front (`/pipeline/meta` et les mutations lisent la même source `columns_for`). Les vrais défauts étaient
côté UI : l'ajout passait par `window.prompt` (INTERDIT) et le reset par `window.confirm`.

### Correctifs (`frontend/src/components/crm/Kanban.tsx`)
- Ajout de colonne : **champ inline** en DA LABUSE (Ajouter/Annuler, Entrée/Échap) — plus de `window.prompt`.
  La colonne apparaît immédiatement (`invalidateAll` sur `pipeline-meta` + `pipeline`) et persiste (base).
- Renommage en place (input mint, déjà présent) — conservé.
- Réordonnancement flèches ← → (déjà présent) — conservé, vérifié.
- Suppression : dialogue en DA avec **liste déroulante de destination pré-remplie et cliquable** (déjà
  présent) — conservé ; jamais de perte de carte (backend déplace avant suppression).
- Réinitialisation : **dialogue en DA LABUSE** (fond sombre, accent) — plus de `window.confirm`.

### Repro (mode édition : bouton « Personnaliser »)
- « + Colonne » → champ inline → saisir un nom → Entrée → la colonne apparaît en fin de kanban.
- Clic sur le libellé d'une colonne (mode édition) → input de renommage → Entrée.
- Flèches ← / → sur une colonne → l'ordre change.
- ✕ sur une colonne peuplée → dialogue avec « Déplacer les cartes vers » (select pré-rempli).
- « Réinitialiser » → dialogue de confirmation en DA → restaure les 8 colonnes par défaut.

### Preuves
- `qa/m13/B/b3_ajout_saisie.png` — champ inline « Ajouter/Annuler » (aucun window.prompt).
- `qa/m13/B/b3_ajout.png` — kanban après ajout (« À relancer 34 » créée, cartes intactes).
- `qa/m13/B/b3_renommage.png` — renommage en place (input mint actif dans l'en-tête de colonne).
- `qa/m13/B/b3_deplacement.png` — la colonne « À relancer 34 (renom) » déplacée avant « À abandonner ».
- `qa/m13/B/b3_suppression_destination.png` — suppression de « Contact à préparer » (21 cartes) :
  dialogue DA + select destination pré-rempli sur « Repérée ».
- `qa/m13/B/b3_reset_dialog.png` — dialogue de réinitialisation en DA (plus de window.confirm).
- `qa/m13/B/b3_reset_done.png` — retour aux 8 colonnes par défaut.

---

## Fichiers touchés
- `src/labuse/api/app.py` — endpoint `GET /adresses/autocomplete`.
- `frontend/src/lib/api.ts` — `banAutocomplete` → endpoint interne ; `BanFeature` (ajout `idu`).
- `frontend/src/components/AddressAutocomplete.tsx` — dropdown en portal ; `AddressSelection.idu`.
- `frontend/src/components/header/Header.tsx` — omnibox câblée sur `AddressAutocomplete`.
- `frontend/src/components/panel/ResultsSection.tsx` — total filtré (B2).
- `frontend/src/components/crm/Kanban.tsx` — ajout inline + dialogue reset en DA (B3).
- `tests/test_adresses_autocomplete.py` — 4 tests de l'endpoint interne.
- `qa/m13/B/*.png`, `qa/m13/B/shot*.mjs` — captures + harnais Playwright.
