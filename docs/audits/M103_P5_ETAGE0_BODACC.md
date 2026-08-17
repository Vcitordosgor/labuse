# M103 Phase 5 — l'étage 0 BODACC : la mesure du coût, deux issues, arbitrage Vic

Le défaut (M100 n°2, le vrai « invisible » du lot) : 37 parcelles ont un propriétaire dont
la DERNIÈRE annonce BODACC est en liste rouge, mais aucune ligne bodacc — écartées à
l'étage 0, l'étage 2 ne tourne jamais pour elles. La facette Événement ne peut
structurellement pas les voir (comptabilité M100 : 41 avec événement + 37 sans = 78).

**Aucune implémentation — STOP, mesure seule.**

## Option A — l'étage 2 tourne aussi pour les écartées

Volumes mesurés (run q_v9_m81) :

| grandeur | mesure |
|---|---|
| écartées étage 0 | **340 752** parcelles (79 % du parc) |
| écartées avec propriétaire PM (seules candidates à la couche bodacc) | **69 868** |
| écartées PM effectivement sous pression BODACC (bénéficiaires réels) | **417** |
| dont dernière annonce en liste ROUGE (le gain visible à la facette) | **37** (M100) |
| lignes cascade moyennes par parcelle évaluée | ~34 |

Coût si l'étage 2 COMPLET tourne pour toutes les écartées : +340 752 parcelles × ~34
lignes ≈ **+11,6 M lignes** dans `dryrun_cascade_results` (la table du run) et un
allongement de grande passe du même ordre que la population ré-évaluée (+79 % de parcelles
en étage 2) — pour un gain visible de 37 parcelles aujourd'hui.

Variante A' (ciblée) : ne faire tourner QUE la couche bodacc, QUE pour les écartées à
propriétaire PM sous pression (417 parcelles) — coût marginal (~417 lignes, quelques
secondes de passe), gain identique (les 37 rouges + les 380 autres états
orange/gris/neutre tracés). C'est une entorse au principe « l'étage 2 ne s'évalue qu'après
l'étage 0 » : la couche bodacc deviendrait une exception nommée (comme le signal
`cession`, qui lit déjà BODACC hors cascade pour toutes les parcelles via
`bodacc_annonces_owner` — le précédent existe).

## Option B — l'exclusion est assumée et DITE (patron M89)

Aucun recalcul. La facette Événement (et la ventilation) annonce son périmètre :
« Les parcelles écartées au filtre de tête ne portent pas d'événement BODACC — l'événement
n'est évalué que sur les parcelles classées. » Une phrase au point unique (aide de la
facette + docstring du filtre), coût nul, cohérent avec le périmètre par défaut (hors
écartées) — mais l'angle mort reste en voie manuelle : un utilisateur qui coupe l'analyse
et filtre « Événement » ne verra jamais les 37.

## Proposition (à trancher par Vic)

**A' (ciblée)** est le meilleur rapport gain/coût : 417 lignes marginales, le vrai
invisible disparaît, et le précédent architectural existe (signal cession). **B** est
honnête et gratuit si l'angle mort de la voie manuelle est jugé acceptable. **A complet**
coûte ~11,6 M lignes pour le même gain visible que A' — déconseillé par la mesure.

**STOP — Phases 6-7 continuent, la Phase 5 attend l'arbitrage.**

---

## Arbitrage rendu (Vic) et exécution

**A' retenue** (A complète disqualifiée par sa propre mesure), **B en filet**.

- **A'** : exception NOMMÉE dans `cascade/engine.run_cascade` — après la phase 2 des promues,
  la couche bodacc s'évalue aussi pour les non-promues dont `ctx.bodacc(pid)` est renseigné
  (préchargé depuis `v_foncier_sous_pression` pour tout le lot : zéro requête ajoutée,
  ~417 lignes marginales). Test moteur dédié (`test_m103_a_prime_bodacc_evalue_les_
  ecartees_sous_pression`) : l'écartée sous pression porte l'événement rouge, l'écartée sans
  pression n'est pas évaluée, la promue est inchangée. **Effet au PROCHAIN run de
  classement** — les tables du run servi restent intouchables (doctrine), les 37 invisibles
  apparaîtront à la bascule.
- **B (filet)** : le périmètre restant est DIT — l'aide du signal « Procédure collective »
  (strings.ts) précise que l'événement n'est évalué que sur les classées et, de façon
  ciblée, sur les écartées à propriétaire sous procédure ; une écartée sans procédure connue
  ne porte jamais d'événement (exclusion délibérée, patron M89).
