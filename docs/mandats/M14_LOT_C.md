# M14 — LOT C : Bouton « Projet » multi-projets (QA-59)

Branche : `fix/m14-c-projet-multi` (base `main` 35febbb). Worktree isolé, **non mergée**.
Zéro touche au scoring. Backend `projets.py` **inchangé** (déjà correct).

## 1. Comportement actuel diagnostiqué (sur main)

Le code présent sur `main` est **M12-F7** (le « grisé » de M13-E3 n'est PAS mergé). Diagnostic
du composant `ProjetButton` (`frontend/src/components/fiche/Fiche.tsx`) et du backend
`src/labuse/api/projets.py` :

- Backend **déjà conforme** :
  - `GET /projets/pour-parcelle/{idu}` renvoie **tous** les projets actifs du compte qui
    contiennent la parcelle (SEC-IDOR : borné au compte).
  - `POST /projets/{pid}/ajouter` → `_upsert_proposee` en `ON CONFLICT (projet_id, parcel_id)
    DO NOTHING` : **doublon interdit au sein d'un même projet**, mais rien n'empêche d'ajouter
    la même parcelle à un **autre** projet. Multi-projet supporté côté serveur.
  - Le front applique déjà le grisé **par projet** : `deja = dejaIds.has(p.id)` — les autres
    projets restent actifs. Pas de blocage global.

- **Le bug (logique inversée / UX bloquante)** était à la ligne du `onClick` du bouton principal :

  ```
  if (attaches.length === 1) setOpenProjet({ id: attaches[0].id, nom: attaches[0].nom })
  else setOpen((o) => !o)
  ```

  Quand la parcelle était dans **exactement un** projet, cliquer « Projet » **sautait
  directement dans ce projet** et **n'ouvrait jamais le menu**. Résultat : impossible d'ajouter
  cette parcelle à un **second** projet via le bouton — alors que le titre du bouton promettait
  « ouvrir / rattacher à un autre ». Le multi-projet était donc **de facto bloqué** dès qu'une
  parcelle appartenait à un projet.

## 2. Le fix

`frontend/src/components/fiche/Fiche.tsx` (front only) :

1. Le bouton principal ouvre **toujours** le menu (`onClick={() => setOpen((o) => !o)}`) —
   plus jamais de saut direct. Le menu montre donc **tous** les projets à chaque clic.
2. Les projets qui **contiennent déjà** la parcelle sont **grisés, non cliquables**
   (`disabled`, `aria-disabled`, `cursor-not-allowed opacity-50`, « ✓ dedans ») : double rôle —
   empêcher le doublon dans un même projet + montrer où elle est déjà rangée.
3. Les **autres** projets restent **actifs** (« + ») → l'ajout à un second projet marche.
4. L'action « ouvrir » (perdue par la suppression du saut direct) est rapatriée dans une
   section « DÉJÀ DANS — OUVRIR » du menu, qui liste les projets attachés et les ouvre.

Aucun blocage global : une parcelle déjà dans un projet reste ajoutable ailleurs.

## 3. Preuve (app réelle, headless Playwright)

Setup : 2 projets actifs distincts créés (`Projet Alpha` #33 Saint-Denis, `Projet Beta` #34
Saint-Paul) ; parcelle `97423000AB1908` (1re fiche du deep-link `#f=1&v=1`) ajoutée à Alpha
uniquement. Script : `qa/m14/C/prove.mjs`.

- `qa/m14/C/c1_liste_grise_et_active.png` — menu ouvert : **Projet Alpha grisé « ✓ dedans »**
  (déjà dedans, non cliquable) ET **Projet Beta actif « + »** (cliquable) + autres projets
  actifs. **Un grisé, un actif → exigence remplie.**
- `qa/m14/C/c2_les_deux_grises.png` — après clic sur Beta : **Alpha ET Beta tous deux grisés
  « ✓ dedans »** → l'ajout au 2e projet a marché, la parcelle est bien dans **deux** projets.

Confirmation backend post-ajout :
`GET /projets/pour-parcelle/97423000AB1908` → `[{id:34 Beta}, {id:33 Alpha}]`.

## 4. Verify

- `npm run build` → **0 erreur TS** (132 modules).
- `pytest tests/test_projet_m2.py` → **4 passed** (backend inchangé, non-régression).
- Golden : `qa/golden_check.py` → **116/116 PASS, 0 FAIL**.

## 5. Livraison

Commit `[M14-C] …` sur `fix/m14-c-projet-multi`. **Ne PAS merger** (mandat séparé).
