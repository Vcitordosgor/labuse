# MANDAT COHÉRENCE-RUN-1 — les tables annexes doivent suivre le run servi

**Nature** : diagnostic puis recalcul ciblé.
**Branche** : `feat/paliers-1` (worktree `~/Desktop/labuse-paliers1`), à la suite de BASCULE-1.
**Modèle CC** : Fable.
**Contexte** : `q_v14` est basculé en local. Cinq avertissements au promote signalent que des calculs annexes portent encore un autre run :
- `parcel_renouvellement` → `q_v11_m137` (67 260 lignes)
- `parcel_flags` → `q_v11_m137` (2 208 373 lignes)
- `score_e` → `q_v13_sources1` (285 781 lignes)
- `division_or_candidates` → `q_v13_sources1` (10) + `q_v10_m129` (23) — workflow de revue par commune, toléré
- `dryrun_parcel_evaluations` → pas de ligne `q_v14` (cascade réutilisée de `q_v13_sources1`)

**Interdits** : aucun merge, aucun rescoring du modèle P, aucune bascule (q_v14 reste servi en local), aucun élargissement hors des lots ci-dessous.

## Étape 0
`pwd` = `~/Desktop/labuse-paliers1`, branche = `feat/paliers-1`, arbre propre.

## Lot A — diagnostic, en lecture seule, avant tout recalcul
Pour chacune des cinq entrées :
1. **Qui la lit** — quels écrans, endpoints, exports ou outils servent cette table, et **que voit le client** aujourd'hui du fait de l'écart (un chiffre faux ? un manque ? rien de visible ?). Preuve `fichier:ligne`.
2. **Comment elle se recalcule** — la commande, sa durée mesurée ou estimée, ses dépendances.
3. **Est-ce vraiment un écart** — la cascade réutilisée est-elle une exception légitime (le run candidat pointe volontairement sur l'étage 0 de `q_v13_sources1`) ou l'avertissement révèle-t-il un vrai trou ? Si c'est légitime, la sonde ne devrait pas le signaler comme un écart : le dire.

**Rendre compte avant d'exécuter quoi que ce soit.** Si un recalcul dépasse une heure ou touche une table servie en production, s'arrêter et attendre l'arbitrage de Vic.

## Lot B — recalculer ce qui doit l'être
Sur la base du lot A, relancer les calculs annexes sur `q_v14`, du plus court au plus long, un commit par table. Après chaque recalcul, relancer `golden promote q_v14` (ou l'équivalent de vérification) pour constater la disparition de l'avertissement correspondant.

## Lot C — que ça ne se reproduise pas
Un run promu ne devrait pas laisser des tables annexes derrière lui sans qu'on le sache à l'avance. Proposer — **sans l'implémenter** — le geste juste : soit la bascule refuse tant que les annexes ne suivent pas, soit elle liste ce qui reste à recalculer avec la commande à lancer. Une demi-page, décision de Vic.

## Rapport
`docs/audit-2026-09/COHERENCE-RUN-1.md` : le tableau du lot A (table · qui la lit · ce que voit le client · commande · durée), ce qui a été recalculé, ce qui reste et pourquoi, la proposition du lot C.
