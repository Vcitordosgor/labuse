# M12 — LOT D · Recherche & adresse

Branche : `feat/m12-d-adresse` (worktree isolé, base = `main` @ `5e50113`).
Périmètre : brancher l'autocomplétion d'adresse BAN, l'ajouter à la recherche
principale, et déplacer « Scorer une adresse » dans les Outils. **Zéro touche scoring,
zéro changement de données.**

## Note de départ (état git)
La branche avait été créée depuis un HEAD stale (1099 commits avant `main`, **sans** le
dossier `frontend/` qui n'existait pas encore à ce commit). Fast-forward propre vers `main`
(`git reset --hard main`, HEAD ancêtre de main → pas de divergence) pour récupérer le front.

## Fait

### D1 — Composant d'autocomplétion réutilisable (MUTUALISÉ)
`frontend/src/components/AddressAutocomplete.tsx` (unique, utilisé par D2 **et** D3).
- Suggestions au fil de la frappe, adossées à la **BAN**.
- Sélection → **adresse normalisée + coordonnées** via `onSelect({ label, lon, lat })` —
  **jamais** une chaîne libre.
- Navigation clavier ↑ ↓ Entrée Échap ; a11y ARIA combobox/listbox
  (`role`, `aria-expanded`, `aria-activedescendant`, `aria-controls`).
- Debounce 220 ms + `AbortController` (annule la requête précédente) ; clic-extérieur ferme.
- Helper API `banAutocomplete()` ajouté dans `frontend/src/lib/api.ts` (+ type `BanFeature`).

**Endpoint utilisé — l'API BAN PUBLIQUE** `https://api-adresse.data.gouv.fr/search/?q=…&limit=6&autocomplete=1`.
Justification : il n'existe **aucun** endpoint interne d'autocomplétion. Le back n'a qu'un
géocodage `limit=1` interne à `scoreur.py` (`_geocode`, non exposé en route). Le back
lui-même appelle déjà cette même BAN publique pour `/scoreur-adresse` — on reste cohérent
avec l'existant (Étalab, gratuit, sans clé).

### D2 — « Scorer une adresse » : autocomplétion branchée
`frontend/src/components/outils/ScoreurAdresse.tsx` : l'ancien `<input>` texte libre est
remplacé par `<AddressAutocomplete>`. La valeur envoyée à `/scoreur-adresse` est désormais
le **label normalisé BAN** (le back re-géocode `limit=1`, inchangé). `data-scoreur-adresse`
conservé (porte sur l'input interne) → captures QA préservées.

### D3 — Barre de recherche principale : entrée « adresse »
`frontend/src/components/header/Header.tsx` (`Omnibox.onEnter`) : après les branches
existantes commune / IDU (intactes), 3e branche **adresse** — si la saisie contient des
lettres, géocodage BAN (`banAutocomplete`) → `parcelAt(lon, lat)` → `select(idu)`, landing
sur la parcelle contenant le point. Toast honnête si géocodé mais hors base.
Placeholder mis à jour : `« Rechercher : commune · IDU (AB 0234) · adresse… »` (3 entrées),
title itou.

### D4 — Déplacement dans Outils
- Entrée `scoreur-adresse` (O2, groupe `analyser`, phare) ajoutée à
  `frontend/src/components/outils/registry.ts` et au dispatch `COMPONENTS` de
  `frontend/src/components/outils/ModulePanel.tsx`.
- `ScoreurAdresse` réécrit en **corps de module** (`() => JSX.Element`) : plus de wrapper
  flottant ni de prop `onClose` (l'en-tête/fermeture viennent du panneau). Le lien
  « ouvrir la fiche » fait `setModule(null)`.
- **Retiré de l'en-tête** : import, state `scoreurOpen`, bouton `⌖ Scorer une adresse`, mount.
- **Liens vérifiés** : plus aucune référence à `ScoreurAdresse`/`data-scoreur-open`/
  `data-scoreur-close` hors du nouveau chemin. Scripts de capture (hors golden) mis à jour
  vers le nouveau chemin (rail Outils → carte) : `qa/atlas.mjs`, `qa/captures.mjs`.

## Vérifications
- **Build** : `cd frontend && npm run build` → **0 erreur TS**, build vite OK (132 modules).
- **Golden** : API sur `:8033`, `qa/golden_check.py` → **116/116 PASS**, 0 FAIL, 0 incohérence.
  (Note : port 8022 initialement bloqué sur le verrou advisory de schema-heal tenu par un
  serveur d'un autre lot M12 tournant en parallèle ; relancé sur :8033 une fois le verrou
  libéré, boot propre en 4 s.)

## Non fait / laissé (consigné)
- **Aucun endpoint BAN interne créé** : décision assumée de réutiliser la BAN publique
  (identique au back existant). Si un jour un proxy interne `/adresse/autocomplete` est
  souhaité (cache, offline, quota), `banAutocomplete()` est le seul point à réadresser.
- Pas de nouveau test unitaire front (le repo n'a pas de harnais de test composant React ;
  la couverture de non-régression passe par build TS + golden + captures visuelles).
