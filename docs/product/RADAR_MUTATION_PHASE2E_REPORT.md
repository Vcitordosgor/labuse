# Radar Mutation — Phase 2E/2F : calque carte, polish UX, QA, docs

> Mission journée **sans risque DB** (lecture seule métier). Base de départ `main = a81c9bf`.
> Rédigé le **2026-06-27**. Garde-fous respectés : aucune écriture DB, aucun index, aucune
> migration, aucun re-cascade, scoring & verdicts intacts, pas de refonte, V1 non cassée.

## Synthèse

| Axe | Résultat |
|---|---|
| Calque carte Radar Mutation | **branché** (overlay violet, OFF par défaut, lazy, légende dédiée, clic→fiche) |
| Filtre sidebar niveau | **Prioritaire / Forte** (chips) — « surveiller » différé (vide via le top) |
| UX / wording | cohérent sidebar/fiche/carte, **0 terme interdit**, prudent partout |
| QA responsive | **390 / 768 / 1440 px** : 0 overflow, 0 erreur console locale |
| Perf froide | **plan sérieux mesuré** (`RADAR_MUTATION_PERF_PLAN.md`) ; rien d'imposé |
| Tests | **50 passés** ; `node --check` OK (Phase 2E = frontend, backend inchangé depuis 2D) |
| DB métier | **inchangée** (431 663 / 1 132 371 / 9 103 / 0 stale / cascade 8 997 413) |

---

## 1 · Ce qui a été implémenté

### Calque carte (frontend additif)
- Overlay **« Radar Mutation (potentiel) »** ajouté au **contrôle de calques existant** (à côté de
  Permis / Zones de veille) — **OFF par défaut** (défaut prudent).
- **Chargé à la demande** (`overlayadd`) : appelle `/map/mutation.geojson` pour **prioritaire +
  forte** (limit 80 chacun, en parallèle), borné (~153 polygones), **jamais** au chargement initial.
- Polygones **violets** (prioritaire `#8B7FD6`, forte `#A99BE0`) — **distincts** des couleurs de
  verdict. Tooltip « Radar Mutation · X/100 — potentiel à étudier ». **Clic → fiche existante**.
- **Légende dédiée** `#radar-legend` (violette) affichée seulement quand le calque est actif,
  **empilée au-dessus** de la légende verdict (sans chevauchement). États : analyse / vide / erreur.

### Polish UX (frontend additif)
- **Filtre niveau** sidebar : chips **Prioritaire / Forte** (rechargement + cache serveur).
- Cohérence **sidebar ↔ fiche ↔ carte** : même violet, même wording « potentiel à étudier ».
- Conserve l'**état de chargement** (2D) et les **messages doux** (vide/erreur).

## 2 · Ce qui a été refusé (documenté, non forcé)

- **« À surveiller » dans la sidebar** : le top ne remonte que prioritaire/forte (présélection
  biaisée vers le haut du panier) ⇒ un onglet « surveiller » serait **vide**. Nécessite un pool plus
  large (coût perf) → différé (cf. perf plan / matérialisation).
- **Optimisation du froid** (réécriture SQL une passe, départage, index, matérialisation) :
  **analysée et chiffrée** dans `RADAR_MUTATION_PERF_PLAN.md`, mais **non implémentée** (la SQL
  change le top-8 → décision produit ; l'index est une migration → GO DB). Rien d'imposé.
- **Refonte carte / clustering** : hors périmètre (additif uniquement).

## 3 · Screenshots (livrés, non versionnés)

- `qa2e_map_layer.png` — carte + calque violet **+ deux légendes distinctes** (Radar / Verdict).
- `qa2e_mapclick_fiche.png` — **clic carte → fiche** : Radar « Prioritaire 88/100 » **+** verdict « À creuser ».
- `qa2e_sidebar_forte.png` — sidebar, filtre **Forte** actif (3 signaux).
- `qa2e_home_390.png` / `qa2e_home_768.png` / `qa2e_home_1440.png` — **responsive**.
- `qa2e_mobile_fiche.png` — fiche plein écran **mobile**.

## 4 · QA

| Vérification | Résultat |
|---|---|
| `healthz` / `readyz` | 200 / 200 (`ready:true`, schema+data ok) |
| Calque : défaut OFF, 0 couche, légende cachée | ✅ |
| Calque activé : 153 parcelles, légende visible, état « potentiel à étudier » | ✅ |
| Clic calque → fiche **+ bloc mutation + verdict** coexistent | ✅ (DM/AB : Radar + « À creuser ») |
| Toggle OFF → légende re-cachée | ✅ |
| Filtre sidebar Prioritaire (8) ⇄ Forte (3) | ✅ |
| Wording interdit (DOM rendu, 3 largeurs) | **AUCUN** |
| Erreurs console **locales** | **0** (tuiles CartoDB/IGN = bruit environnemental, distingué) |
| Overflow horizontal 390/768/1440 | **aucun** |

## 5 · Perf

- Calque : `/map/mutation.geojson` **~8 ms à chaud** (cache), froid ~4,7 s (1ʳᵉ activation, async).
- Sidebar : inchangée (cache 2D, ~0–9 ms à chaud).
- **Plan froid mesuré** (`RADAR_MUTATION_PERF_PLAN.md`) : single-pass SQL **1,2 s** (×3,9, prototypé
  non commité), index estimé ~0,5–1 s. Recommandations claires, rien d'imposé cette nuit.

## 6 · DB inchangée

Avant/après : `parcels=431 663`, `parcel_evaluations=1 132 371`, `opportunités=9 103`, `stale=0`,
`cascade_results=8 997 413`. Aucune écriture, aucun index, aucune migration.

## 7 · Recommandations suivantes (Phase 2F)

1. **Décision produit perf froide** : adopter ou non le **single-pass + départage** (×3,9,
   reproductible, top-8 des ex-æquo change) — sinon viser l'**index** `cascade_results` (GO DB).
2. **« À surveiller »** dans la sidebar/carte : nécessite un pool élargi ou la **matérialisation**.
3. **Calibrage multi-communes** (au-delà de Saint-Paul) une fois la perf froide tranchée.
4. **Carte** : éventuel réglage fin du `limit` et option « prioritaire seul » selon retours démo.

## 8 · Conclusion

> Phase 2E/2F livrée **sans risque** : le calque carte Radar Mutation est branché proprement
> (additif, OFF par défaut, violet distinct, clic→fiche), l'UX est cohérente et prudente, la QA
> responsive est verte, le pack démo et le plan perf sont écrits. **Scoring, verdicts, DB intacts**,
> V1 non cassée, 50 tests verts. Les leviers perf à fort impact mais à arbitrer (SQL/ index/
> matérialisation) sont **documentés**, pas forcés.
>
> **→ Validation humaine requise.**
