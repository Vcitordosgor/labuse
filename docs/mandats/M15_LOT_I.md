# M15 — LOT I : merge B→G→C sur main + vérification post-merge

**Sur `main`** (7 lots M15 déjà mergés : a-casses, a3-matching, c3-menu-projet, d-outil19, e-scores,
f-noms, h-sources — base d2e2914). Merges effectués **dans l'ordre strict demandé**, **non poussés**
(Vic valide et pousse).

## Merges (dans l'ordre)
| Ordre | Merge | Commit | Conflit | Résolution |
|---|---|---|---|---|
| 1 | `fix/m15-b-plafonds` | 618f646 | ModulePanel M07 (bandeau) | bandeau **E3** (main) + compteur **B** (pagination) |
| 2 | `fix/m15-g-entrees` | eeff820 | ModulePanel M07 (bandeau) | bandeau **E3** + `CommuneScope` **G** (RG1) + compteur **B** |
| 3 | `fix/m15-c-faisabilite` | bd87384 | aucun (auto-merge propre) | registry : F-renames **et** rename C **et** entrée calculette tous gardés |

`build` **vert après chaque merge**. Backend (modules.py, models.py, `ensure_promesses_index`) auto-mergé.
Toutes les intentions gardées : tous les outils, tous les renommages, tous les plafonds « voir plus », RG1.

## Vérification sur main mergée (`:8060`, `LABUSE_DEV_MODE=1`)

### Golden
**116/116 PASS, 0 FAIL.**

### Recapture B/G/C (checklist LOT I)
- **B** — permis 300→600 (+ « 516 sans localisation précise »), promesses 1 000→2 000 / 9 141
  (1re page rapide + count parallèle), fantôme 300→600 / 6 261. « Voir plus » partout.
- **G** — 3 entrées (IDU/adresse/clic) sur Courriers + Due diligence ; adresse résout un IDU réel.
- **C** — Faisabilité 2 modes (toggle « Par critères » / « Par parcelle » → `FaisabiliteTab` porté,
  steps + calculette) ; Calculette foncière autonome (charge foncière + bloc sourcé, sortie fiche).

### RG1 sur un cas concret
Filtre commune **global = Saint-Denis**, on ouvre **Foncier fantôme** → périmètre outil **« Toute
l'île » / 6 261** (PAS 744 = le sous-ensemble Saint-Denis). Choix explicite Saint-Denis dans l'outil →
744. **L'héritage silencieux est bien coupé.** Idem Mode bailleur et Faisabilité (mode critères).

### Aucun lot écrasé
- **27 entrées registre** (24 outils + 3 groupes) ; **les 24 outils ont un composant** dans `COMPONENTS`
  (dont le nouveau `calculette-fonciere`). Aucun outil perdu.
- Signatures des 7 lots antérieurs présentes : **F** (Radar des mutations / Quoi de neuf / Contrôle
  avant achat), **E** (M01 « facilité à détacher », M07 « constructible mais fantôme », O6 €/m² neuf),
  **D** (`cmpLeft/cmpRight`, TimeMachine), **A3** (matching DÉMO/RÉEL), **H** (sources fraîcheur),
  **c3** (menu projet).
- Capture du tiroir Outils complet : `qa/m15/I/drawer_outils.png`.

## État
Prêt pour validation. `main` local = bd87384 (3 merges au-dessus de d2e2914), **non poussé**.
