# M15 — LOT C : Faisabilité 2 modes (C1) + Calculette foncière autonome (C2)

**Branche** `fix/m15-c-faisabilite` — **empilée sur `fix/m15-g-entrees`** (réutilise `CommuneScope` et le
motif 3-entrées de G). Prouvé, **non mergé**. ⚠ **ordre de merge : B → G → C.**

## Principe directeur (spec Vic)
Réutiliser le code des **fiches**, ne rien réimplémenter : la faisabilité et la calculette de charge
foncière sont **portées telles quelles** dans les outils ; seule **l'entrée** change.

## C1 — Faisabilité en 2 modes (outil M22, ex-« Faisabilité programme »)
Les 2 modes = **2 façons d'entrer une parcelle**, pas 2 analyses :
- **« Par critères »** (existant, SENS 2) : on décrit un programme → LABUSE propose les parcelles qui
  matchent. **RG1 appliqué** : le périmètre commune est **saisi dans l'outil** (`CommuneScope`, défaut
  « Toute l'île »), **plus hérité** du filtre carte global.
- **« Par parcelle »** (nouveau, SENS 1) : une barre **IDU / adresse / clic-carte** (`ParcelPicker`)
  désigne UNE parcelle → sa **faisabilité complète** s'affiche = le composant `FaisabiliteTab` **des
  fiches**, importé tel quel (capacité, calcul tracé étape par étape, explication IA, calculette).

Sélecteur de mode en tête ; libellé de l'outil renommé **« Faisabilité »** (desc couvre les 2 modes).

## C2 — Calculette foncière (nouvel outil autonome)
Nouvel outil `calculette-fonciere` (groupe *Analyser*, num M23). C'est **exactement** la
`Calculette` de charge foncière des fiches (même composant, même endpoint `/charge` — **zéro recalcul,
zéro divergence**). Seul ajout = l'entrée : le même `ParcelPicker` (IDU / adresse / clic-carte). Sortie
identique à la fiche : bloc **sourcé** (SDP vendable, prix de sortie, terrain) + hypothèses éditables
(coût, marge) + **charge foncière supportable** + verdict d'achat optionnel.

## Réutilisation sans divergence
- `Calculette` et `FaisabiliteTab` **exportés** depuis `fiche/Fiche.tsx` — diff = **2 mots-clés
  `export`, rien d'autre** (prouvé `git diff`). La fiche est inchangée.
- Nouveau `ParcelPicker` (`outils/ParcelPicker.tsx`) partagé C1-mode2 + C2 ; `CommuneScope` exporté
  depuis `ModulePanel.tsx` (réutilisé par C1-mode1). Pas de dépendance circulaire (la fiche n'importe
  pas les outils).
- Enregistrement : `registry.ts` (entrée `calculette-fonciere`) + `COMPONENTS` de `ModulePanel.tsx`.

## Preuve (`:8060`, `qa/m15/C/prove.mjs`, parcelle 97415000CW0658)
| Point | Résultat |
|---|---|
| **C1 toggle** | « Par critères » ✓ · « Par parcelle » ✓ |
| **C1 RG1** | filtre global = Saint-Denis → périmètre outil **« Toute l'île »** (pas hérité) |
| **C1 par parcelle** | picker ✓ → `FaisabiliteTab` rendu : « CAPACITÉ CONSTRUCTIBLE R+4… », **steps tracés** ✓, **calculette incluse** ✓ |
| **C2** | picker ✓ → `Calculette` rendue : **résultat charge foncière** ✓, bloc **sourcé** ✓ (sortie identique fiche) |
| **Fiche inchangée** | `git diff Fiche.tsx` = 2 `export` uniquement |

Captures : `c1a_criteres_RG1`, `c1b_parparcelle_faisa`, `c2_calculette_fonciere`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=:8060`). Aucune touche back / scoring
(les endpoints faisabilité/charge existants sont réutilisés à l'identique).

## Notes
- **C3 « menu projet »** était déjà livré (réécriture du menu ProjetButton, hors de ce lot).
- Empilée sur G : merger **B → G → C**. Rebase propre (C compose sur les artefacts de G).
