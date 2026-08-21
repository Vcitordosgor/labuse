# Audit — Simulateur ZAN (21/08/2026)

Mesure rendue avant correction (points 2-4) ; le point 1 (couverture) est réparé immédiatement car la
cause EST un LIMIT. Branche `audit/simulateur-zan`. Ne merge pas.

## 1. Couverture — pourquoi pas 24/24 ? → un LIMIT d'affichage caché (RÉPARÉ)

| Maillon | Communes | Verdict |
|---|---|---|
| Donnée amont `commune_conso_enaf` | **24/24** (24 lignes, 24 INSEE) | complète |
| Endpoint `/moteurs/zan` → `indicateurs` (`_zan_indicateur`, pas de LIMIT SQL) | **24** | complet |
| Frontend `M17` (moteurs.tsx) | **8** | `.slice(0, 8)` |

**Cause = un LIMIT d'affichage `.slice(0, 8)` côté front** (moteurs.tsx), exactement le motif du baromètre.
Ni trou Cerema, ni filtre SQL. **Réparé** : slice retiré → les 24 communes, dans un conteneur qui défile ;
l'en-tête DIT « les 24 ». (Chaque ligne montre en plus son % consommé, cf. l'ajout ci-dessous.)

## 2. Signal parcelle « Aligné ZAN » — véridique ? → repose sur un PROXY, non dit (CORRIGÉ) + DOUBLON fiche

- « Sol déjà artificialisé (OCS-GE) » (`moteurs.py:zan_parcelle`) repose sur `spatial_layers kind='ocs_ge'`.
- **OCS-GE est un PROXY** : l'OCS GE 974 natif n'est pas exposé en WFS ; la couche servie est
  `BDCARTO_V5:occupation_du_sol` (IGN BD CARTO V5), confirmé `layers_ingest.py:649` + `seed_sources.py:301`
  (« PROXY : OCS GE 974 natif non exposé… »). Le signal disait « (OCS-GE) », **tagué Sourcé (vert)**, sans
  dire le proxy — alors que la **ligne cascade de la fiche le dit** (`phase1.py:746` : « occupation du sol
  BD CARTO V5 »). Le signal était donc MOINS honnête que la fiche. **Corrigé** : la raison dit désormais
  « occupation du sol BD CARTO V5, proxy OCS-GE ».
- **DOUBLON** : `ocs_ge` EST une couche cascade (`phase1.py:726`) → le fait « sol artificialisé » est
  **déjà servi sur la fiche parcelle** (et plus honnêtement). Le signal de l'outil duplique ce fait.

## 3. Enveloppe communale — véridique ?

- **Cohérence arithmétique : OUI.** Saint-Paul : conso 2011-21 = 434,9 ha → budget = ×0,5 = **217,5 ha** ;
  reste = 217,5 − 90 (conso 2021-24) = **127,5 ha**. Vérifié en base et à l'écran.
- **Lisible comme un droit à construire : OUI, risque réel.** « Budget » + « Reste théorique » + le nouvel
  affichage en % (« 59 % restant ») se lisent vite comme un droit ferme. Le caveat de bas de bloc ne suffit
  pas à l'instant de lecture du chiffre. **Corrigé** : caveat ESTIMÉ **adjacent au %** (« pas un droit à
  construire », règle -50 %, SAR non territorialisé) ; « Reste » gagne « (théorique) » ; le caveat long reste
  en bas. On ne change pas le calcul (honnête), on empêche la sur-lecture.

## 4. Utile ? — la valeur unique VIVANTE = l'enveloppe communale (améliorée en %) ; le reste est faible

Décomposition des 3 briques de l'outil :

| Brique | État | Unique ? |
|---|---|---|
| Enveloppe communale (conso + budget/reste, désormais en %) | **vivante**, améliorée ce mandat | **OUI** (tant qu'elle n'est pas passée dans « Communes ») |
| Signal parcelle (« Aligné ZAN ») | vivant | **NON — déjà sur la fiche** (couche cascade `ocs_ge`), et l'outil le disait moins bien |
| Liste « parcelles alignées ZAN » (surlignage carte) | **MORTE** | — |

- **La liste `zan_compatibles` est structurellement VIDE** : elle filtre `ocs_ge AND weight_applied > 0`,
  or dans le run servi `ocs_ge` a un poids NULL (366 408 lignes) ou **−5** (65 255, une pénalité) — **jamais
  > 0**. Elle affiche donc « 0 parcelles » en permanence (mesuré live : 0). Fonction morte.
- **Réponse au 4** : l'outil n'est PAS à ranger aux dormants aujourd'hui — sa brique unique et vivante est
  l'enveloppe communale (que ce mandat améliore en %). MAIS **si l'enveloppe part dans « Communes »**, il ne
  resterait que (a) le signal parcelle, **déjà sur la fiche** (doublon), et (b) la liste **morte** → il
  rejoindrait alors les dormants. Recommandation : retirer ou reconstruire la liste `zan_compatibles`
  (morte) ; décider du sort du signal parcelle (doublon fiche) — non touché ici, en attente d'arbitrage.

## Ajout mandat — budget en POURCENTAGE (fait)

Le budget parle mieux en % qu'en ha bruts. Backend `_zan_indicateur` : `pct_consomme` = round(100 ×
conso_2021_24 / budget), `pct_restant` = 100 − pct_consomme (± ; négatif = dépassé). Front : le % EN PREMIER
(gros, coloré), les ha à côté (donnée source), le caveat ESTIMÉ **collé au %**. Idem sur la liste : chaque
commune dit son % consommé (+ ha conso/budget). Saint-Paul : **41 % consommé · 59 % restant**.

## Vérif
Captures (`qa/audit-zan/`) : signal (proxy dit), enveloppe (% + caveat adjacent), liste 24 communes avec %.
Backend : `/moteurs/zan` → 24 indicateurs, pct 41/59 · golden 119/119 · garde-run 431 663=431 663 · tsc 0 · build.
