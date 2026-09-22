# RAPPORT M55-D — stage 3 : les Filtres dans le panneau gauche (forme « Couches »)

Branche `feat/m55-d-filtres-panneau` (base `main` = stage 2 mergé). Front seul, `filters` unique,
moteur non touché. tsc 0, vitest 29/29, build vert.

## Livré
- **Section « Filtres »** (panneau gauche, sous « Couches ») — MÊME carrosserie : titre + badge
  **« N actifs »** (même style/espacement que Couches, M55-C-bis) + **chevron fermé→gauche /
  ouvert→bas** (patron M55-C, boîte h/w 7, group-hover, rotation douce).
  - Ouverte : **3 rapides** (Verdict / Surface / SDP) + **« Tous les filtres → »** qui déplie le
    **panneau expert** (FiltreLabuse, contenu du stage 2 inchangé).
  - **Accroche honnête** (strings.ts, `CLIENT.filtres.accroche(N)`) : « Filtres experts — affinez
    parmi les **N** parcelles déjà analysées par LABUSE ». **N = trame entière du run servi,
    dynamique** : 51 129 à Saint-Paul, 431 663 à l'île. (Les filtres TRIENT — mesuré phase 1 — donc
    « affiner », jamais « générer ».)
- **Header vestige-free** : `AddFilter` (bouton « Filtres (N) »), `NumField` et les **chips**
  retirés. Ne restent que le sélecteur de commune et le bouton Contexte (pas des filtres).
- **ResultsSection** : `FiltreLabuse` retiré (la liste de résultats seule).
- **Robustesse layout** : accordéon Couches↔Filtres (colonne à hauteur fixe jamais débordée) ;
  tiroir Filtres plafonné + scrollable (52 vh) ; hero `overflow-hidden` (plus d'overlap).
- **vite.config** : `/filtre` ajouté au proxy dev — **manquait** (seul `/filters`), le compteur
  était 404 en `npm run dev` (pré-existant).

## À TRANCHER (Vic, sur image) — placement
Capturé les deux ordres, même carrosserie :
- `s3_placement_below.png` — **Couches puis Filtres** (défaut posé).
- `s3_placement_above.png` — Filtres puis Couches.
Un seul mot de ta part et je pose l'ordre retenu.

## Non-régression (vert)
- **Compte /filtre identique sur les 5 combinaisons** (piloté par URL → app → /filtre, Saint-Paul) :
  9822 · 188 · 1710 · 3770 · 51129 — tous OK.
- **URL ancienne compatible** : `#f=1&tv=chaude&smin=2000` → 17 (les deux clés historiques).
- **Header** : `data-filtres-btn` = 0, `data-chips` = 0 (aucun vestige). Badge section
  « FILTRES 2 actifs ».
- Mobile vérifié (panneau utilisable en 390 px). Captures `s3_header_apres`, `s3_filtres_ferme`,
  `s3_filtres_ouvert`, `s3_expert_deplie`, `s3_mobile`, `s3_placement_below/above`.

CC ne merge jamais.
