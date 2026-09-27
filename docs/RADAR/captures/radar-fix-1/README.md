# RADAR-FIX-1 — captures

## `dashboard_apres.png` — dashboard Radar (Tour de contrôle → Radar)
Montre les deux ajouts du **Fix 3** (état réel de la base : dernière capture automatique le 26/09,
donc > 26 h → en retard) :
- bandeau **« Dernière capture automatique — 26/09 02:37 · 35 pages · 3 nouvelles · ⚠ rien depuis plus
  de 26 h — Déposer Radar »** ;
- ligne **À faire : « Déposer Radar — aucune capture automatique depuis plus de 26 h (Mac éteint ou
  extension bloquée) : déposer la page du jour à la main (⌘S) »**.

*Avant* : la même page, sans ces deux éléments (ils n'existaient pas — ajout de ce lot).

## Légende de la carte Radar (Fix 2) — non capturée en PNG
La légende vit dans la vue Radar (`#radar=1`), qui monte la carte **WebGL** (maplibre). En navigateur
**headless** (Playwright MCP), l'initialisation WebGL fait planter l'onglet (limite documentée « MCP
expire sur carte » des audits précédents). Les deux entrées ajoutées sont du **DOM pur** (aucune
dépendance au rendu WebGL), vérifiées par `tsc -b` (0 erreur), `vite build` (OK) et `vitest` (198/198) :

```
● Annonce rattachée à une parcelle
○ Annonce placée au quartier (adresse non fournie par le portail)
```

Ajoutées à la légende Radar existante (`data-radar-maplegend`, `MapView.tsx`), sous les deux pastilles
de statut « En vente / En vente longue », en réutilisant le même markup de pastille (rond plein
`bg-txt-mut` = rattaché ; rond creux `border` = quartier), miroir du rendu carte
(`circle-opacity` quartier→0 sinon 0,8).
