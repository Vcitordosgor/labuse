# M15 — LOT D : outil « Remonter le temps » — barre comparer sur le bandeau gauche

**Branche** : `fix/m15-d-outil19` · Build 0 erreur · Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuve `qa/m15/D/d1_barre_bandeau_gauche.png`.

**Constat** : la barre de comparaison « avant → après » (choix des deux fonds + Quitter) était posée **en surimpression sur la carte** (`TimeMachine.tsx`, `absolute top-4`).

**Correction** : les deux fonds choisis sont remontés dans le **store** (`cmpLeft`/`cmpRight`). Les sélecteurs « Avant / Après » + « Quitter » sont désormais rendus **dans le bandeau gauche** (M08, `ModulePanel.tsx`), comme les autres contrôles d'outil. Seule la **poignée de glissement** reste sur la carte (c'est son rôle). Le comparateur fonctionne toujours (caméras synchronisées, clip-path piloté par la poignée).

**Preuve** (Playwright) : sélecteur `data-cmp-left` à **X=149** (bandeau gauche 300 px), poignée de glissement toujours présente sur la carte, comparateur ortho 1950 ↔ aujourd'hui actif.
