# QA — audit fonctionnel & suite E2E

Tests de bout en bout (Playwright) qui pilotent l'app **comme un utilisateur réel** :
chargement, KPIs, filtres, état vide + reset, audit à la demande, fiche parcelle
(ouverture / Escape / `inert`), navigation onglets, pipeline, démo guidée, santé
console/réseau, et deux garde-fous de régression (focus de la fiche fermée, repli
des KPIs si `/stats` tombe).

## Lancer

```bash
labuse api                 # démarre le backend sur http://127.0.0.1:8000
node qa/e2e.mjs            # exécute la suite (exit ≠ 0 si un scénario échoue)
BASE=http://127.0.0.1:8000/app/ node qa/e2e.mjs   # URL personnalisée
```

Playwright est résolu via le chemin absolu du module (`/opt/node22/...`) car il n'est
pas une dépendance npm du repo. Le **bruit des tuiles externes** (basemap, réseau
bloqué en CI) est filtré : seules les erreurs applicatives font échouer la suite.

Les captures d'écran d'audit vont dans `qa/shots/` (ignoré par git).

## Couverture

14 scénarios — voir `e2e.mjs`. Rapport d'audit complet et registre des bugs :
`../RAPPORT_QA.md`.
