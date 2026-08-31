# PROJETS-V4 — pleine largeur, lignes compactes, fin du mode collant

**Dossier** `~/Desktop/labuse` · **branche** `feat/outils-1` · arbre propre au départ.
**Golden non touché** — mandat 100 % frontend : **0 fichier backend/scoring/qa modifié**
(`git status` : seuls `frontend/` + le store). Référence : `docs/maquettes/projets-v4.html`.
API + front redémarrés avant recette (uvicorn :8000 sert le build `frontend/dist` sous `/socle/`).

---

## V1 — LA LIGNE REMPLACE LA CARTE (colonne À trier)

`ProjetKanban.tsx` : la carte `TriCard` (≈150 px) est remplacée par `LigneParcelle` (≈42 px), en
**grille alignée** `16px 1fr 96px 74px 150px 68px` :
pastille de tier · adresse (**IDU + nu/bâti** en sous-ligne mono) · signal dominant · surface (à
droite) · marché commune (à droite) · deux gestes **✓ / ✕** (icônes 26 px, plus de boutons pleine
largeur). Un **en-tête de colonnes en mono** (`data-kanban-lhead`) coiffe la liste. Survol = fond
éclairci (`hover:bg-surface-2`). Clic = fiche ; glisser = décider (même mutation).
**Capture 1440p** (`01-kanban-1440p.png`) : ~20 lignes visibles (mandat : ≥ 10).

## V2 — LARGEURS

Les trois colonnes passent de `1.35/1/0.8` à **`2.2fr / 1fr / 1fr`** (À trier large). Retenues et
Écartées servent des **mini-lignes** (`MiniLigne` : pastille, adresse tronquée, bouton retour ↩) —
plus des cartes. Le pied de Retenues garde **« → CRM »** et **« ✉ Courrier (N) »**.

## V3 — EN-TÊTE DU PROJET (deux lignes)

(1) « ← Mes projets », nom, périmètre mono, puis à droite **PDF · Renommer · Archiver · « + Ajouter
des parcelles »** (vert). (2) la ligne **« Vivier : N parcelles, classées par probabilité de mutation ·
pourquoi ? · valeurs au JJ/MM (run) »**. La phrase « Une parcelle en tête ailleurs ? … » est RETIRÉE :
le bouton la remplace.

## V4 — ACCUEIL : UNE LIGNE PAR PROJET

`ProjetsPanel.tsx::ProjetRow` réécrit en **grille `1fr / 260px / 130px`** : à gauche titre + périmètre
mono + une ligne de contexte (**N parcelles · valeurs au JJ/MM · budget**) ; au centre la **barre de
progression avec son libellé sous elle** ; à droite le compteur **RETENUES**. Un projet à **vivier 0**
affiche **« aucune parcelle ne correspond à ce cadrage · modifier → »** (le lien ouvre le projet) à la
place de la ligne de contexte. Les lignes vivent dans un cadre unique.
**Capture** (`02-accueil.png`) : 4 projets dont « LABUSTRE TEST 2 » à vivier 0 (message + modifier →).

## V5 — FIN DU MODE COLLANT

**Cause** : PROJETS-FIX (F4) avait introduit un state `projetCible` — après « Ajouter des parcelles »,
la fiche « Projet » rattachait DIRECTEMENT à ce projet, même après avoir quitté Projets (mode collant).

**Correctif — un MENU, aucun état mémorisé** :
- `Fiche.tsx::ProjetButton` réécrit : le bouton ouvre TOUJOURS un menu **« Ajouter cette parcelle à… »**
  listant **tous les projets actifs (nom + taille du vivier)** + une entrée **« Nouveau projet avec cette
  parcelle »**. Le choix ajoute la parcelle aux **Retenues** du projet et affiche une **confirmation
  brève nommant le projet** (`data-projet-confirm`, ~2,8 s). Rien n'est retenu : la fiche suivante
  rouvre le même menu complet. (Un projet où la parcelle est déjà rangée s'ouvre au clic — « déjà ↗ ».)
- `« + Ajouter des parcelles »` (en-tête projet ET état vide) **ouvre simplement la carte** (`ouvrirCarte`),
  sans verrouiller aucun état.
- **`projetCible` / `setProjetCible` supprimés** partout. Grep de contrôle (avant → après) :
  ```
  store/useApp.ts:250,251,558,559   → supprimé (interface + implémentation)
  ProjetKanban.tsx:133 (ajouterDepuisCarte→ouvrirCarte)  → supprimé
  Fiche.tsx:541,564 (projetCible/cibleActive)            → supprimé
  ```
  `grep -rn "projetCible" frontend/src` après correctif = **2 mentions, toutes en COMMENTAIRE**
  (ProjetKanban.tsx:119 · Fiche.tsx:538, expliquant le retrait) — **aucune référence de code** ne
  subsiste (le state et son setter n'existent plus).

**Parcours filmé** (`03-ficheA-*`, `04-ficheB-*`) : fiche A (Saint-Denis) → menu complet (6 projets +
« Nouveau projet ») → ajout à **« tyty »** (confirmation) ; fiche B (Saint-Paul), SANS repasser par
Projets → menu complet à nouveau → ajout à **« touty »** (projet DIFFÉRENT → aucun collant).

---

## VÉRIFICATION

- `tsc -b` : **0**. `vite build` : **OK**. `vitest` : **108 passed**.
- `pytest` (projet, inchangé) : `test_projets_fix_vivier` + `test_projet_m120` = **13 passed**.
  Aucun fichier Python touché → suite backend inchangée par construction.
- **Golden intact** : 0 fichier scoring/qa touché (mandat 100 % frontend) ; `qa/golden_check.py`
  relancé contre l'API redémarrée = **119/119 PASS, 0 FAIL**, GARDE-RUN OK (431 663/431 663, q_v11_m137).
- Composants morts retirés : `TriCard`, `Badges`, `ProprioLine` (kanban), imports orphelins nettoyés.
- Captures `docs/PROJETS-V4/captures/` : kanban 1440p (≥10 lignes) · accueil (vivier 0) · parcours V5.

**Ne merge pas.**

### Commande de merge (à exécuter par Vic, en dernier, isolé)
```
git checkout feat/outils-1 && git merge --no-ff <ce commit>
```
