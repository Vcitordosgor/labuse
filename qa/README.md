# QA — audit fonctionnel & suites E2E

Tests de bout en bout (Playwright) qui pilotent l'app **comme un utilisateur réel** :
fiche parcelle (M9), rate-limit 429, viabilisation, permis (M10), waves ortho/ANC…
Chaque suite `e2e_*.mjs` couvre le périmètre de son mandat.

> **Finding (revue UI/UX, session 1-2)** : l'ancienne suite générale `qa/e2e.mjs` a été
> RETIRÉE — elle pilotait l'UI statique pré-React (`#sheet`, `#kpi-total`, `.qf[data-status]`,
> `#map-empty`), sélecteurs qui n'existent plus dans l'app React (`frontend/src`). Elle était
> structurellement invalide (prouvé session 1 : échec au premier sélecteur, pas un test rouge
> mais un harnais mort). La couverture équivalente vit dans `e2e_m9_fiche.mjs` (fiche,
> onglets, pipeline) et `e2e_429.mjs` ; un parcours général React est à réécrire si besoin.

## Lancer

```bash
labuse api                        # démarre le backend sur http://127.0.0.1:8000
node qa/e2e_m9_fiche.mjs          # exemple — chaque suite sort en code ≠ 0 si échec
BASE=http://127.0.0.1:8000/app/ node qa/e2e_m9_fiche.mjs   # URL personnalisée
```

Playwright est résolu via le chemin absolu du module (`/opt/node22/...`) car il n'est
pas une dépendance npm du repo. Le **bruit des tuiles externes** (basemap, réseau
bloqué en CI) est filtré : seules les erreurs applicatives font échouer la suite.

Les captures d'écran d'audit vont dans `qa/shots/` (ignoré par git).

## Couverture

Voir chaque `e2e_*.mjs`. Rapport d'audit complet et registre des bugs :
`../RAPPORT_QA.md`. Atlas des surfaces : `qa/atlas.mjs`.
