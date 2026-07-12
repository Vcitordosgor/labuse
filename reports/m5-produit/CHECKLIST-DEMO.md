# CHECKLIST DÉMO M5 — 10 vérifications visuelles (validation Vic avant merge)

Préparation : `labuse api` (le run v2 du 12/07 est en base), ouvrir l'app.

1. **Fiche d'une brûlante** — ouvrir `97410000AS1425` : le bloc « Probabilité de
   mutation (P v2) » affiche **×22,0**, percentile 100, rang 16, chip « Brûlante v2 »,
   et les 5 contributions lisibles (permis <2a en tête, +1.30). AUCUNE probabilité
   brute nulle part.
2. **« Pourquoi ce score » en français** — sur la même fiche : chaque ligne =
   libellé métier + bin (ex. « ancienneté du dernier permis [<2a] »), signe coloré
   (+ chaud / − froid).
3. **Badge copro + exclusion du ranking** — ouvrir une parcelle copro (ex. via
   Outils → Scoring v2 → Top P avec toggle copro coché) : badge « copro », pas de
   rang, jamais dans les listes par défaut.
4. **Toggle copro** — Outils → « Scoring v2 (P) » → onglet Top P : cocher/décocher
   « inclure les copropriétés » change la liste (défaut : décoché).
5. **Vue Brûlantes v2** — onglet Brûlantes v2 : 119 lignes, triées par ×N, badge
   « évén. » sur celles à événement daté ; clic → la fiche s'ouvre.
6. **Vue Réserve foncière** — onglet Réserve foncière : bandeau bleu explicite
   « vitrine capacité, PAS un pipeline » ; les parcelles montrent un ×N faible.
7. **Page Sources & fraîcheur** — rail → Sources : bloc « Modèle de scoring v2 :
   m36-l2f-2026, sha 00a58008143d, gelé le 2026-07-12 » + avertissement censure
   (« les ventes récentes apparaissent dans DVF avec 1 à 3 ans de retard… »).
8. **Delta brûlantes** — ouvrir `reports/m5-produit/delta-brulantes-v2.csv` :
   0 gardée / 120 sorties / 119 entrées, un MOTIF par ligne (rang P, copro,
   D < seuil…). C'est un CHANGEMENT DE PRODUIT assumé : v1.3 = détresse vendeur,
   v2 = probabilité de mutation foncière.
9. **Axe C inchangé** — sur une fiche : SDP m² + € (faisabilité) identiques à
   avant ; Q/A/V toujours servis (deprecated côté API v2 seulement).
10. **Événement prime** — chercher une parcelle avec badge « événement <date> »
    (ex. dans Brûlantes v2) : vérifier que l'événement BODACC est daté < 12 mois
    et visible aussi dans le panneau Score V (cohérence v1.3 ↔ v2).

Rappels doctrine (si question en démo) : « à surveiller » n'existe plus →
« réserve foncière » ; V ne classe plus (0,51× hors copro, mort empiriquement)
mais ses ÉVÉNEMENTS restent des badges datés ; churn : l'hystérésis protège les
recalculs intra-année, la bascule de millésime (~50 %) est un événement de
régime présenté comme nouveau millésime (cf. SYNTHESE-M5 §churn).
