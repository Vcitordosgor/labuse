# SYNTHÈSE M5 — Surface produit scoring v2 (P×C)

Branche `feat/m5-surface-produit`, aucun merge. Modèle M3.6 gelé
(sha256 `00a58008143d…`, manifeste `FREEZE-scoring2026.json` créé au lot 0),
AUCUN ré-entraînement, aucun re-binning. Seed 974. Étage 0, moteur PLU/Q (axe C),
calcul V et veille_succession INTACTS ; V sorti du ranking (0,51× hors copro),
ses événements datés restent des badges.

## Lot 1 — Pipeline production ✅

`labuse score-v2` : sha256 vérifié (refus si mismatch, testé), features as-of via
le builder ext M3.6 importé, recalage d'intercept sur 2025 (politique documentée
dans pipeline.py : re-train complet = décision humaine annuelle), écriture
versionnée `parcel_p_score_v2` + `p_score_v2_runs` (run_id unique, refus
d'écrasement testé), snapshot `m5-2026-07-12` gelé (mécanisme M1, label unique).
**Run réel : 431 663 parcelles en 153 s.** Affichage produit = ×N vs moyenne +
percentile + rang (p_raw stocké, jamais montré — saturation isotonique).

## Lot 2 — Statuts v2 + hystérésis ✅ (churn : verdict nuancé)

Tiers du run du 12/07/2026 : **brûlante 119 · chaude 1 032** (=1 151, cible
1 100-1 200 ✓) · réserve foncière 4 547 · à creuser 83 680 · écartée 342 285
(étage 0 q_v2). N_entrée calibré = 2 445 (rang hors copro), N_sortie = 3 423
(1,4×). Plancher C proposé et documenté : SDP résiduelle > 0 OU surface ≥ 600 m²
en U/AU. Bypass événement daté < 6 mois : implémenté + testé (synthétique).

**Churn simulé 2024→2025 (churn-simulation.csv) : 50-56 %, cible < 15 % NON
tenue, même à N_s = 1,8 × N_e.** Diagnostic honnête : c'est STRUCTUREL, pas un
réglage — les signaux de tête du modèle (`permis <2a`, `tenure <1`) expirent
par construction dans un hasard à 12 mois ; le top se renouvelle avec le
millésime. Doctrine retenue et documentée : l'hystérésis (1,4×, gardée) protège
les recalculs INTRA-année (rafraîchissements de données, censure B0) ; la
bascule annuelle de millésime est un ÉVÉNEMENT DE RÉGIME, à présenter comme un
nouveau millésime de scoring — jamais comme un recalcul silencieux.

## Lot 3 — Brûlante v2 ✅

Définition : chaude ∧ contribution D ≥ 1,421 (calibrage mécanique, garde-fou
[30-120] → **119 brûlantes**) ∧ (événement daté < 12 mois OU top décile D).
Sensibilité ± 0,1 : effectif 117-122 (stable). Doctrine « un contexte seul ne
franchit jamais un seuil » : testée (événement sans D suffisante ≠ brûlante).

**Delta vs v1.3 (delta-brulantes-v2.csv) : 0 gardée / 120 sorties / 119
entrées, motif ligne à ligne.** Sorties : essentiellement « rang P hors top »
— les brûlantes v1.3 étaient sélectionnées sur la détresse vendeur (V), pas sur
la probabilité de mutation. **Changement de produit assumé et documenté** :
v1.3 = qui DOIT vendre (PM en difficulté) ; v2 = ce qui VA muter (foncier).
Les événements v1.3 restent visibles (badges datés + bypass + critère brûlante).

## Lot 4 — UI / API ✅ (additif strict)

API : router `/v2` (score/{idu}, liste avec toggle copro, brulantes,
reserve-fonciere, modele) — lecture précalculée uniquement, réponses
observées en millisecondes en local (cible P95 < 200 ms tenue avec marge).
Matrice historique toujours servie, marquée deprecated. UI React : bloc
« Pourquoi ce score » sur la fiche (auto-porté, absent si pas de run), module
Outils « Scoring v2 (P) » (3 onglets + toggle copro), bloc modèle + avertissement
censure sur la page Sources. `tsc` + `vite build` verts.

## Lot 5 — Monitoring forward ✅

Snapshot `m5-2026-07-12` gelé aux côtés de v1.2/v1.3. `labuse monitor-forward`
opérationnel (rapport 2026-07 généré : 0 hit — gel du jour, attendu ; sonde faux
négatifs : 1 parcelle détectée dès le premier run). Niveaux jugés à l'édition
N+2 uniquement (protocole B0 rappelé dans chaque rapport).

## Lot 6 — Tests & docs ✅

13 tests v2 (8 statuts/hystérésis synthétiques dont oscillation sans churn et
bypass événement ; 5 API/idempotence) + suite existante. COMMANDES.md créé
(score-v2, monitor-forward, séquence démo). CHECKLIST-DEMO.md : 10 vérifications
visuelles pour Vic.

## Réserves explicites

1. Churn < 15 % intenable à la bascule de millésime (structurel, cf. lot 2) —
   décision produit à valider par Vic : présentation « nouveau millésime ».
2. Le run du jour utilise les features as-of 01/01/2026 avec les données
   présentes en base ; DVF 2025-2026 encore censuré (~40 % / quasi 0) — les ×N
   affichés sont fiables en ORDRE, provisoires en niveau (avertissement partout).
3. COMMANDES.md créé (n'existait pas) plutôt que « mis à jour ».
