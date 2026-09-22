# RAPPORT M55-D — stage 4 : L'Entonnoir (section Filtres en deux étages)

Branche `feat/m55-d-stage4` (base `main` = stage 3 mergé). Front seul, moteur/endpoints non touchés.
tsc 0, vitest 31/31, build vert.

## Structure livrée
- **ÉTAGE ① — Le terrain** (faits, toujours actifs, sobres, ordonnés par usage) : Surface ·
  Zonage (famille U/AU/A/N + zone exacte) · État du sol · Contraintes de secteur (50 pas, Parc,
  pollution/ICPE/risques).
- **ÉTAGE ② — Le regard LABUSE** (interrupteur « Afficher l'analyse LABUSE », mint, **éteint par
  défaut**). Éteint → « N parcelles · tri factuel », zéro critère d'opinion affiché. Allumé →
  verdict/tiers, déclassement, potentiel ≥, SDP, capacité, BODACC, veille + tiroirs éco/mutation/
  proprio/niches ; **compteur en transition « parc → retenues »** ; la section **se replie**
  (accordéon) pour laisser la carte.
- **ÉTAGE ③ — Raccourcis** : pré-réglages marqués (qui **allument l'interrupteur** s'ils portent
  de l'opinion), Mes vues, « Puis-je construire ? » en note discrète.

## Cohérence d'état (le bug mesuré, corrigé)
Avant : `verdict` défaut **false** mais `filters.analyseLabuse` défaut **true** → « Analyse active »
s'affichait alors que rien n'était allumé. Désormais **biunivoque** :
- interrupteur = `filters.analyseLabuse` (persisté) ⟺ `verdict` (carte), les deux ensemble ;
- `EMPTY_FILTERS.analyseLabuse = false` (éteint par défaut, tri factuel) ;
- `hasOpinion(filters)` : un critère d'opinion (tier, potentiel, SDP…) **allume** ; le terrain seul
  (surface, zonage, état du sol, contraintes) reste **éteint** ;
- persistance `al=1` = allumé ; un **vieux lien portant un tier** ouvre allumé et **affiche
  l'analyse** (App.tsx) ;
- **Reset** = réinitialise les DEUX étages ET éteint l'interrupteur (état vierge).

## Détails
- **Accroche adaptée** : éteint « Filtrez les N parcelles de La Réunion » / allumé « Affinez parmi
  les N analysées par LABUSE » (N = parc du run servi, dynamique). Plus de « Verdict » en double
  (les rapides du stage 3 fusionnés dans les étages).
- **Chips** : sélectionné = rempli menthe, texte franc ; disponible = fond léger + survol menthe
  (fin du tout-gris qui ne guidait pas l'œil).
- Pavés (« Les écartées ne sont jamais masquées… ») → notes courtes / tiroirs.

## Non-régression (vert)
- **Compte /filtre identique** sur les 5 combinaisons, état reproduit (interrupteur allumé si
  tiers) : 9822 · 188 · 1710 · 3770 · 51129 — tous OK.
- **Vieux lien** `#f=1&tv=chaude&smin=2000` → 17, interrupteur **allumé**.
- Interrupteur **OFF par défaut** (`aria-pressed=false`) ; section **repliée** post-allumage
  (drawer count 0). Pré-réglage d'opinion → interrupteur allumé.
- Persistance : test `filters.test.ts` (terrain→éteint, tier→allumé, `hasOpinion`) 31/31.
- Captures `s4_eteint`, `s4_etage2_deplie`, `s4_replie_post_allumage`, `s4_preset`, `s4_mobile`.

CC ne merge jamais.
