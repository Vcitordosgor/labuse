# BLOC B — LA CONSOLIDATION FINALE DU SPRINT TECH (rapport vivant)

**Branche `tech/bloc-b` · Partie 1 autonome → STOP mi-course (maquettes S45-S50) →
Partie 2 sur verdict → STOP final · Vic merge.** DA verrouillée (tokens de la revue),
wording boussole partout.

## ⟪ CURSEUR ⟫ Partie 1 en cours — B1 (perf)

---

## B1 · Top 5 perf — le tableau des mesures

| # | Fix | Avant (mesuré Bloc A) | Après (mesuré) | Statut |
|---|---|---|---|---|
| 1 | Cache-Control assets hashés | aucun `Cache-Control` sur /assets/* (etag seul) | `public, max-age=31536000, immutable` sur /assets/*, `no-cache` sur le shell — **vérifié en prod** (déployé immédiatement : config seule, réversible, .bak conservé) | ✅ |
| 2 | Liste île top-N (index rang) | 2,5 s | — | à faire |
| 3 | Tuiles 1er écran (LCP mobile) | 2,9 Mo · LCP 4,0 s | — | à faire |
| 4 | O6 / O7 cache TTL | 1,9 s / 1,1 s | — | à faire |
| 5 | PDF banquier async + cache | 9,3 s bloquants | — | à faire |

## B2 · Le coup de propre

_(à venir : vieille UI archivée puis retirée, branches mergées purgées, deps mortes,
caveat weasyprint unifié/documenté)_

## B3 · Le radar des sources

_(à venir)_

## B4 · Les minis

_(à venir : lien Pages Jaunes neutre, majuscules PPR à l'affichage)_

## Garde-fous — état

Golden après chaque lot touchant requête/serving · archive avant suppression ·
zéro hex local · jamais dev_mode · restart jamais pendant un backup.
