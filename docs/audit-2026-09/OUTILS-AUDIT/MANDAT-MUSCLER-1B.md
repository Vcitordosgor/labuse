# MANDAT OUTILS-MUSCLER-1B — Retouches de l'outil « Successions à venir »

**Rédigé par :** Fable, 06/09/2026. Suite de la recette Vic sur OUTILS-MUSCLER-1 (à merger dans `main` avant).
**Branche :** `fix/successions-1b`, créée depuis `main` à jour.
**Périmètre :** l'outil Successions uniquement. Six points, rien d'autre. Pas d'audit collatéral, pas de refonte, pas de retouche des autres outils.

## Étape 0

`pwd`, `git branch --show-current`, `git status -sb`. Conditions : branche `fix/successions-1b`, arbre propre, `main` contient le merge de `feat/outils-muscler-1`. Sinon : s'arrêter.

## Garde-fous

- DA existante, composants existants, aucun style nouveau.
- Rien d'autre que les six points ne bouge — ni dans cet outil, ni ailleurs.
- Capture avant / après dans `docs/audit-2026-09/OUTILS-MUSCLER-1B/`.
- `pytest tests/` (avec `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`), vitest, tsc — verts. Les tests qui portent l'ancien nom ou les gestes retirés sont mis à jour, pas supprimés en bloc.
- Un seul commit. Push, **pas de merge**.

---

## 1. Renommer l'outil

« Successions » devient **« Successions à venir »** partout où le nom apparaît : entrée du menu Outils, titre du panneau, bandeau, tiroir « Détail et méthode », libellés de fil de retour (« ← Successions à venir »), tests. Décision Vic du 06/09 : le signal est un radar patrimonial à 3-7 ans, pas une succession ouverte ; le nom doit porter le délai.

## 2. Retirer le geste « Assembler avec les voisines → »

Sur les cartes de l'outil. Le pont vers Assemblage disparaît de cet écran ; Assemblage et son endpoint voisines restent intacts par ailleurs.

## 3. Retirer le geste « Comparer (N) »

Sur cet écran seulement. La sélection reste, elle sert au point 6.

## 4. Retirer la mention du tri

Le libellé « triées par résiduel SDP décroissante » ne s'affiche plus. **L'ordre servi ne change pas** — la liste reste triée comme aujourd'hui, c'est l'étiquette qui disparaît, pas le tri. Si CC comprend l'inverse (retirer le tri lui-même), il s'arrête et demande avant d'écrire.

## 5. Retirer la mention du filtre

La phrase « choisi ici — pas hérité du filtre global » ne s'affiche plus. Le comportement du filtre ne change pas.

## 6. Déplacer « Préparer les courriers »

Le geste passe **en bas de panneau, à droite, sur la même ligne que « Détail et méthode »**. Il garde son compteur, son pont vers Courrier et son fil de retour. Même composant de bouton qu'aujourd'hui.

---

## Compte-rendu

≤ 10 lignes : le commit, les captures avant / après, ce qui a résisté avec `fichier:ligne`, le résultat des tests.
