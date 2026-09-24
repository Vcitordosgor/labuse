# MANDAT DA-AUDIT-1 — audit de cohérence DA de toute l'app

**Modèle** : CC Fable (rapprochements sur tout le front). **Lecture seule** : aucune écriture dans `src/`, seulement `docs/`.
**Branche** : `audit/da-1` depuis `main`, worktree `~/Desktop/labuse-da`. **Livrable** : `docs/audit-2026-09/DA-AUDIT-1/RAPPORT.md` + captures.
**Référentiel** : `docs/audit-2026-09/DA-AUDIT-1/CHARTE-DA-1.md` (validée par Vic le 23/09/2026) + la planche `CHARTE-DA-1-planche.pdf`. On audite CONTRE la charte, pas selon le goût.

## Étape 0 (obligatoire, sinon stop)
`pwd`, `git branch --show-current`, `git status --porcelain` : bon worktree, bonne branche, arbre propre. Sinon on s'arrête et on signale sans rien écrire.

## Périmètre — toute l'app
17 outils · fiche parcelle · fiche commune · carte + panneaux (Couches, Filtre, Analyse, fonds) · Veille + cloche · Radar · Projets · CRM · Copilote · Compte · menu latéral. **Hors périmètre** : dashboard admin, exports PDF, tout le back.

## Ce qu'on produit

### A. La grille écran × règle (le cœur)
Une ligne par écran (un outil = une ligne par étape : entrée, résultat, détail), une colonne par règle de la charte (numérotées 1.1 → 8.2). Dans chaque case : ✓ conforme · ✗ écart · — sans objet. Chaque ✗ renvoie à une ligne de la partie B.

### B. Le registre des écarts
Pour chaque ✗ : `DA-xxx` · écran · règle · ce qu'on voit (une phrase) · fichier:ligne · capture. Pas de proposition de correctif ici — le constat seul.

### C. L'inventaire des composants
Pour chaque famille (bouton, chip, case, tri, retour, omnibox, ligne de liste, carte cliquable, badge, accordéon, tiroir, état vide/erreur/chargement, barre de défilement) : combien de variantes vivent dans le code, où (fichier), laquelle est dans `primitives.tsx` si elle y est. C'est ce qui décidera de l'ordre des DA-FIX.

### D. Cinq chiffres en tête du rapport
Écrans audités · écarts au total · écarts par règle (les 5 pires) · familles de composants avec ≥ 2 variantes · rayons distincts trouvés dans le CSS (valeur → nombre d'occurrences).

## Méthode
- Captures : chaque écran en repos + au survol du contrôle principal, dans un vrai navigateur (harnais existant), cadrage à 1440 px. Un écart déclaré sans capture n'existe pas.
- Le code fait foi pour C (grep des `border-radius`, `:hover`, `transition`, classes de bouton), la capture fait foi pour A/B.
- Règle 4 (entrée d'outil) : dire pour chacun des 17 outils s'il offre omnibox / clic carte / les deux / aucun.
- Règle 3 (retour) : dire pour chaque outil et chaque étape quel composant de retour est rendu et où il est placé.

## Ce qu'on ne fait PAS
Pas de correctif, pas d'extraction de composant, pas d'audit collatéral (données, calculs, textes), pas de proposition de nouvelle règle : un cas que la charte ne couvre pas se note en fin de rapport sous « Non couvert par la charte », une ligne, et c'est Vic qui tranche.

## Fin
Un commit `docs: DA-AUDIT-1 rapport + captures` sur `audit/da-1`, poussé, **pas de merge**. Puis un message de 10 lignes max : les cinq chiffres de D et les 3 familles de composants les plus éclatées.
