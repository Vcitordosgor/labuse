# FIX LOT 1 — triviaux + fix run prioritaire

**Branche** : `feat/fix-lot1` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**5 commits séparés** (validation/revert isolés). Base : `main` (Surface C mergée).
Diagnostic source : `reports/pre-lancement/DIAGNOSTIC-OUTILS.md`.

| # | Commit | Fix | Fichier | Effort |
|---|---|---|---|---|
| A | `bea6b45` | run v2 servi épinglé au label | `app.py` | 1 ligne |
| B | `79fb05b` | baromètre PDF 500→200 | `moteurs.py` | 1 ligne |
| C | `fc7af10` | vrais comptes APER/tertiaire | `solaire.py` + `ModulePanel.tsx` | trivial |
| D | `3e1e127` | message patrimoine vide | `ModulePanel.tsx` | trivial |
| E | `70cf80f` | simulateur PLU cliquable | `moteurs.tsx` | trivial |

**Périmètre** : 5 fichiers. **Aucun fichier scoring/cascade/étage 0/engine touché** (`git diff --name-only main..HEAD`). Seul le Fix A est scoring-adjacent — et c'est un **no-op prouvé**.

---

## FIX A — Épingler le run v2 servi à `Q_A_RUN_LABEL` *(le fix de sécurité)*

**Cause (diagnostic)** : `_score_v2_run_id` résolvait « le dernier run v2 par `computed_at` », pas épinglé au label. Un run v2 futur d'un autre label deviendrait **silencieusement** la source des tiers servis — la dette exacte tuée à la bascule M8.

**Fix** (`app.py:1082-1083`) :
```python
# avant : SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1
# après : SELECT run_id FROM p_score_v2_runs WHERE run_id = :label LIMIT 1   (:label = Q_A_RUN_LABEL)
```
Un run futur d'un autre label ne devient jamais servi tant que `Q_A_RUN_LABEL` n'est pas changé (= décision explicite). Label absent → None → repli legacy (inchangé).

**Preuve de no-op (obligatoire)** :
- Run résolu après fix = **`q_v6_m8`** (inchangé).
- **Golden : 30/30 verts** (`test_communes_gold_standard.py`) · **Cohérence : 3/3 verts** (`test_run_serving_coherence.py`). Aucun tier ne bouge.
> Le fichier golden porte 30 cas (le « 32 » du mandat est nominal) ; ce qui compte : **zéro échec** et **run servi inchangé**.

---

## FIX B — Baromètre foncier PDF (500)

**Cause** : **PAS** un bug `Decimal` (les données sont correctes). `FPDFException: Not enough horizontal space` : les deux `multi_cell` finaux (`moteurs.py:327,331`) sans `new_x` → fpdf2 laisse le curseur X à la marge droite → le suivant démarre avec 0 mm.

**Fix** : `new_x="LMARGIN", new_y="NEXT"` sur les deux `multi_cell`.

**Preuve** : `GET /moteurs/barometre.pdf` → **HTTP 200**, PDF valide 1 page, footer inclus (« Périmètre DVF… 2007 mutations écartées », « Données publiques… © LABUSE »). Capture `fixB-barometre-pdf.png`.

---

## FIX C — Vrais comptes APER / toiture tertiaire

**Cause** : `total = len(items)` = longueur de la liste **après** le `LIMIT` d'affichage → « 500 » et « 300 » trompeurs.

**Fix** (`solaire.py`) : `total` = **vrai COUNT** (mêmes filtres, sans LIMIT) ; nouveau champ `affiches` = longueur rendue. Front (`ModulePanel.tsx`) : annonce le vrai total + « N affichés » quand la liste est tronquée.

**Preuve** (live + captures) :
- APER : **« 736 parkings assujettis · 24 échéance(s) dépassée(s) · 500 affichés »** (`fixC-aper-736.png`).
- Tertiaire : **« 9 635 toitures · 300 affichées »** (`fixC-tertiaire-9635.png`).
La liste reste tronquée à 500/300 pour le rendu (pas de liste infinie), le compteur dit la vérité.

---

## FIX D — Message scan patrimoine (état vide)

**Cause** : une recherche sans résultat (boîte absente des fichiers fonciers, ex. VISHOR MATERIAUX) laissait un **écran muet** → perçu « cassé » alors que c'est un 0 légitime.

**Fix** (`ModulePanel.tsx`, `data-m02-vide`) : branche « aucun résultat » quand `q.length≥2 && !isFetching && suggestions=0`, expliquant que les fichiers fonciers ne recensent que les **personnes morales** détentrices de foncier.

**Preuve** (captures) : « VISHOR MATERIAUX » → message clair (`fixD-patrimoine-vide.png`) ; « CBO » → **4 suggestions** (non-régression : une boîte avec foncier s'affiche normalement).

---

## FIX E — Simulateur PLU : liste cliquable

**Cause** : l'API renvoie `idu`+`geom`, mais le front M15 rendait chaque parcelle en **`<div>` inerte**, `select` jamais destructuré de `useApp` (`moteurs.tsx:25,54`). Seul moteur à parcelles sans handler.

**Fix** : brancher `select` + transformer le `<div>` en `<button onClick={() => select(i.idu)}>` (pattern M17/M22).

**Preuve** (capture) : clic sur un item de la liste → la **fiche de la parcelle 97411000EH0044 s'ouvre** (`fixE-simulplu-clic-fiche.png`).

---

## Non-régression
- Golden 30/30 + cohérence 3/3 (Fix A no-op).
- Surface A (ask), B (recherche/agrégat), C (faisabilité/explication), fiche, PDF fiche, dossier : intacts (endpoints testés en live pendant les mandats précédents ; aucun fichier partagé modifié hors les 5 ci-dessus).
- `tsc --noEmit` vert ; `ruff` vert sur les fichiers touchés.
- **Zéro touche scoring hors Fix A** (prouvé no-op).

*5 commits séparés sur `feat/fix-lot1`. Pas de merge. Maps/Cadastre/1950/radar = LOT 2 ; faisabilité programme = LOT 3.*
