# M15 — LOT C3 : menu « Rattacher à un projet » sans redondance

**Branche** : `fix/m15-c3-menu-projet` · Build 0 erreur · Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuve `qa/m15/C/c3_menu_dedoublonne.png`.

**Constat** (M14) : le menu affichait DEUX FOIS les projets contenant déjà la parcelle — grisés « ✓ dedans » en haut ET dans la section « Déjà dans » en bas.

**Correction** (`components/fiche/Fiche.tsx`, `ProjetButton`) :
- **Haut** = uniquement les projets où l'ajout est POSSIBLE (`ajoutables = candidats.filter(p => !dejaIds.has(p.id))`), **tous cliquables, aucun grisé**.
- **Bas** = section « Déjà dans — ouvrir » inchangée (les projets déjà rattachés, pour les ouvrir).
- Cas où tout est déjà rattaché : message « Cette parcelle est déjà dans tous vos projets actifs ».

**Règle de fond inchangée** : multi-projets autorisé, doublon dans un même projet interdit (backend `ON CONFLICT`). On ne change que l'affichage.

**Preuve** (Playwright, sur parcelle déjà dans 3 projets) : haut = **3 ajoutables, 0 grisé, aucun « ✓ dedans »** ; bas = **3 « déjà dans »**.
