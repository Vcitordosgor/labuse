# BLOC B — LA CONSOLIDATION FINALE DU SPRINT TECH (rapport vivant)

**Branche `tech/bloc-b` · Partie 1 autonome → STOP mi-course (maquettes S45-S50) →
Partie 2 sur verdict → STOP final · Vic merge.** DA verrouillée (tokens de la revue),
wording boussole partout.

## ⟪ CURSEUR ⟫ Partie 1 en cours — B1 TERMINÉ (5/5 mesurés) · suite : B2

---

## B1 · Top 5 perf — le tableau des mesures

| # | Fix | Avant (mesuré Bloc A) | Après (mesuré) | Statut |
|---|---|---|---|---|
| 1 | Cache-Control assets hashés | aucun `Cache-Control` sur /assets/* (etag seul) | `public, max-age=31536000, immutable` sur /assets/*, `no-cache` sur le shell — **vérifié en prod** (déployé immédiatement : config seule, réversible, .bak conservé) | ✅ |
| 2 | Liste île top-N (index rang) | 2,5 s prod · **1,10 s local** (mesure de travail) | **0,036 s local** (×30) — page servie par `ix_p_v2_run_rang` (top-N sans scan) + cluster même-proprio matérialisé (le planner le ré-exécutait par ligne) | ✅ |
| 3 | Tuiles 1er écran | 9,00 Mo / 4 tuiles (île desktop, re-mesuré : la tuile centrale z9 seule = 5,6 Mo) | **1,09 Mo** (×8) — paliers recalibrés au pixel (z9 60 m/ext.1024 · z10 30/1024 · z11 15/1024, z12+ intact) + `stale-while-revalidate=86400` ; trame visuellement identique (capture avant/après) | ✅ |
| 4 | O6 / O7 cache TTL | O6 2,5-3,6 s · O7 liste 2,5 s (re-mesurés) | **4,7 ms / 3,8 ms au 2ᵉ hit** — `_mem_cached` single-flight, TTL 1 h documenté (les données suivent les crons quotidiens + build post-run ; jamais plus d'1 h de retard) | ✅ |
| 5 | PDF banquier async + cache | 9,3 s bloquants (8,4 s re-mesuré local) | **clic → 202 en 4 ms** (génération en fond, thread + session DB propre), sonde 1,5 s, puis PDF servi du cache **~6 ms** ; cache LRU 32 × (idu, run), GET direct inchangé (compat liens/QA) ; bouton fiche à états (Loading DA → « prêt » mint → réessai) | ✅ |

**Garde-fou B1.2** : 8 jeux de filtres capturés sur l'ANCIEN code puis rejoués — 7 byte-identiques
(île défaut, offset 500×1000, tiers, commune+surface, hors_copro+sdp, tiers=ecartee, sort=mult) ;
le 8ᵉ (page chevauchant la frontière rang→NULL) : l'ancien code était LUI-MÊME non-déterministe
sur les égalités de queue (prouvé par double exécution) — vérifié : même ensemble d'IDU, préfixe
rangé identique, contenu par-ligne identique ; le nouveau chemin ajoute un tiebreaker `idu` qui
rend l'ordre TOTAL (amélioration). Golden 116/116 · suite 1088/0. Chemin rapide UNIQUEMENT si un
run v2 existe (sinon repli legacy inchangé) ; tris mult/surface/commune/v inchangés.

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
