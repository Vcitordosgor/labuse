# FIX LOT 3 — faisabilité programme (point 28)

**Branche** : `feat/fix-lot3` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**3 commits séparés**. Backend (requête de l'outil) + front (affichage). Diagnostic : groupe 1-C.
**Zéro touche scoring/cascade/étage 0/run/engine** (git : 2 fichiers — `modules.py` requête outil, `M22Programme.tsx` front).

L'outil **n'était pas cassé** (le filtre agit, le compte varie) mais deux défauts réels le faisaient paraître figé. Corrigés — pas de refonte.

| # | Commit | Fix | Fichier |
|---|---|---|---|
| A | `4339843` | ordre filtres → tri → LIMIT | `modules.py` |
| B | `7b443f8` | compteur prominent & réactif | `M22Programme.tsx` |
| C | `c29f871` | « N = total », pas un plafond | `M22Programme.tsx` |

---

## Lot 0 — Constat (la requête réelle, confirmé avant de coder)
`POST /modules/programme` (`faisabilite_sens2`) : `WHERE sdp_residuelle_m2 >= sdp_min AND surface_m2 >= smin AND matrice_statut IN (chaude/a_surveiller/a_creuser) AND run_label = q_v6_m8` → `ORDER BY sdp_residuelle_m2 DESC` → **`LIMIT 300`**, PUIS **en Python** le filtre HAUTEUR (`resolve_zone` → `continue` si trop bas), PUIS `sort marge DESC`, PUIS `items[:200]`.
- **Le `LIMIT 300` est AVANT le filtre hauteur** ✓ (le défaut). `n = len(items)` était donc borné aux 300 plus grosses SDP.
- La saisie branche bien : `sdp_min = unités × m²/unité × 1,15` → filtres `sdp` (JOIN) + `smin` (WHERE). Le compte varie (Saint-Denis : 183→…→25 selon la saisie).
- Le tri marge DESC est appliqué en Python sur le lot (tronqué à 300).
- Le « **49** » = le **COUNT de correspondances** de la commune (n), lu à tort comme un plafond.
- Lit bien **q_v6_m8** (`run_label = :run`, `RUN = Q_A_RUN_LABEL` ; `s2.run_id = :v2run`).

## FIX A — ordre LIMIT / filtre *(le vrai bug)*
Le `LIMIT 300` sur SDP DESC coupait **avant** le filtre hauteur → des parcelles valides (hors des 300 plus grosses SDP) étaient jetées sans être examinées.
**Fix** : requête **LÉGÈRE** (sans la géométrie lourde) et **SANS LIMIT** → toutes les parcelles satisfaisant les filtres SQL sont ramenées, PUIS le filtre hauteur, PUIS le tri marge, PUIS la **troncature d'affichage** (top 200). `n` = le VRAI nombre de correspondances. Les géométries ne sont ramenées que pour les **200 affichées** (2e requête ; `item.geom` n'est utilisé nulle part ailleurs → même forme de réponse). `resolve_zone` mémoïsé par `(zone, commune)`.
**Preuve chiffrée** (île, 2 bât. × 8, sdp_min 1104) :
```
AVANT (LIMIT 300 puis filtre hauteur) : n = 300
APRÈS (filtre hauteur sur tout le lot)  : n = 4 620
→ 4 320 parcelles VALIDES récupérées
```
L'outil lit toujours q_v6_m8 (inchangé).

## FIX B — rendre l'effet du filtre visible
L'utilisateur croyait l'outil figé car le HAUT de liste (marges fortes) ne bouge pas. Or le filtre agit — le NOMBRE change.
**Fix** : compteur **prominent** (gros nombre mauve) **« N parcelles correspondent à vos critères [à {commune} / toute l'île] »**, qui **varie visiblement** avec la saisie. Le tri marge décroissante reste (légitime — on ne trafique pas le tri pour « faire bouger le haut »).
**Preuve** : `fixBC-programme-2bat.png` (**111** à Saint-Denis) vs `fixBC-programme-8bat.png` (**20**) — même écran, saisie différente, compteur + reste de liste différents.

## FIX C — clarifier le « 49 »
Le « 49 » (= n, le COUNT de correspondances) était lu comme un plafond de résultats.
**Fix** : sous le compteur, une note explicite — quand `n` dépasse le nombre affiché : **« Total des correspondances (pas une limite) — les {X} premières, par marge décroissante, sont affichées »** ; sinon « Triées par marge décroissante ».
**Preuve** : `fixBC-programme-ile-total.png` — « **4 619** parcelles correspondent… (toute l'île) — Total des correspondances (pas une limite) — les 200 premières… affichées ».

---

## Non-régression & garanties
- **Zéro touche scoring** : `git diff` = `modules.py` (requête de l'outil) + `M22Programme.tsx` (front). Aucun fichier scoring/cascade/étage 0/engine/p_v2. Pas de re-golden nécessaire.
- L'outil **lit toujours q_v6_m8** (prouvé : `run_label = :run` = `Q_A_RUN_LABEL`, `s2.run_id = :v2run`).
- Réponse de même forme (`criteres`, `bandeau`, `n`, `items` avec `geom` sur les 200 affichées) → `M22` et `projet_apercu` (seuls consommateurs, n'utilisaient pas `item.geom`) intacts.
- `tsc --noEmit` vert ; `ruff` : seul l'`E402` pré-existant subsiste.

*3 commits séparés sur `feat/fix-lot3`. Pas de merge.*
