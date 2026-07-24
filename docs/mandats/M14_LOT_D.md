# M14 — LOT D — Recherche

Branche : `fix/m14-d-recherche` (isolée, NON mergée). Base : `main` (35febbb).

Cible : l'`Omnibox` (barre de recherche du haut) dans
`frontend/src/components/header/Header.tsx`, qui délègue la saisie au composant
réutilisable `frontend/src/components/AddressAutocomplete.tsx`.

---

## D1 — Placeholder (QA-60) — FAIT

Le champ de recherche affiche désormais exactement :

> **Rechercher : IDU, adresse exacte, commune…**

Avant : `Rechercher : commune · IDU (AB 0234) · adresse…`.

Modification : `Header.tsx`, prop `placeholder` de l'`AddressAutocomplete`.

PREUVE : `qa/m14/D/d1_placeholder.png` (capture de l'en-tête).
Test Playwright : lecture de l'attribut `placeholder` de `[data-omnibox]`
→ `"Rechercher : IDU, adresse exacte, commune…"` — `D1 match = true`.

---

## D2 — Moitié droite non cliquable (QA-61) — FAIT

### Cause racine

Le composant `AddressAutocomplete` enveloppe son `<input>` dans un `<div>`
`className="relative min-w-0 flex-1"` (position **relative**, donc bloc — pas un
conteneur flex). Ce wrapper prend bien toute la largeur disponible de la barre
(`flex-1`).

L'`<input>`, lui, reçoit sa `className` **entièrement** depuis l'appelant
(`Header.tsx`) — cette className **écrase** le défaut du composant
(`className={className ?? '…'}`). Or l'ancienne className passée était
`min-w-0 flex-1 bg-transparent …` : **sans `w-full`**. `flex-1` n'a aucun effet
ici car le parent (`div.relative`) n'est **pas** un flex-container. L'`<input>`
retombait donc sur sa **largeur intrinsèque** (~la taille par défaut d'un input),
bien plus étroite que le wrapper.

Conséquence : la moitié droite de la barre (l'espace vide du wrapper que
l'input ne recouvrait pas) n'avait **aucun élément focusable** dessous. Un clic
à droite tombait sur le `<div>` wrapper — sans handler, sans `<label>` — donc
sans focus de l'input. Seule la zone gauche (là où l'input existait réellement)
ouvrait la saisie. Ce n'était **ni** une superposition invisible, **ni** la
loupe, **ni** le portail d'autocomplétion : juste un input qui ne remplissait
pas son conteneur.

### Correctif

Dans `Header.tsx`, la className de l'`AddressAutocomplete` de l'omnibox passe de
`min-w-0 flex-1 …` à **`w-full min-w-0 …`**. L'input remplit désormais toute la
largeur du wrapper `flex-1` → toute la surface de la barre, bord à bord, est
occupée par l'input et donc cliquable/focusable.

### Preuve / test

Test Playwright (`qa/m14/D/d_test.mjs`) :
1. `boundingBox` de `[data-omnibox]` → **largeur 308 px** (l'input remplit
   maintenant tout le wrapper, entre `pl-3` et la loupe).
2. `document.activeElement` blur() puis vérif focus AVANT clic = `false`.
3. Clic souris à **`box.x + box.width - 8`** (extrême droite, x=517), y au centre.
4. Vérif focus APRÈS clic : `document.activeElement` porte `data-omnibox`
   → **`true`**.

Résultat loggé : `D2 focus AVANT = false` → `D2 focus APRÈS clic droite = true`
→ `D2_PASS=true`.

PREUVE visuelle : `qa/m14/D/d2_clic_droite.png` — pastille rouge au point de
clic (extrême droite du champ) + anneau mint de focus (`focus-within:border-mint`)
sur la barre.

---

## Vérifications

- `npm run build` → **0 erreur TS** (132 modules, build OK).
- Golden : `python qa/golden_check.py` → **116/116 PASS, 0 FAIL**
  (aucune touche au scoring ni au backend — ce lot est purement front).

## Fichiers touchés

- `frontend/src/components/header/Header.tsx` (placeholder + `w-full`).
- `qa/m14/D/d_test.mjs`, `qa/m14/D/d1_placeholder.png`, `qa/m14/D/d2_clic_droite.png` (preuves).
