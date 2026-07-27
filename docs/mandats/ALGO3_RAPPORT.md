# ALGO-3 — Voisinage hyper-local · Rapport (LOT A — POINT D'ARRÊT)

**Clone dédié** `labuse-algo3` (règle n°1 — fin des collisions de sessions), branche
`feat/algo3-voisinage`. Champion `q_v7_defisc` INTOUCHÉ ; écritures préfixées `algo3_`
uniquement. **Note session : mandat « Modèle Fable », exécuté sur Opus 4.8.**

## A — Construction : COUVERTURE MESURÉE (27/07/2026)

**Temps de calcul total : 258 s (4 min 18)** — détail : centroïdes 2,3 s · mutations
géo 0,6 s · paires mutations 29,9 s · paires permis 16,3 s · densités 35,5 s ·
mitoyenneté 26,5 s · features (10 années) 146,9 s. Re-calculable à chaque run mensuel
sans douleur.

| Mesure | Valeur |
|---|---|
| Paires cible↔mutation ≤ 200 m (as-of, cible exclue ×2) | **11 620 136** |
| Paires cible↔permis ≤ 200 m | **5 083 955** |
| Paires mitoyennes (ST_Touches) | **2 228 412** (5,2 voisins directs/parcelle en moy.) |
| Voisins moyens dans 50 / 100 / 200 m | **10 / 36 / 123** parcelles |
| Parcelles SANS voisin à 100 m (bin « manquant ») | **9 219-11 779** (2,1-2,7 %) — catégorie DISTINCTE du « 0 vente » (leçon ALGO-2) |

**Distribution des ventes voisines (100 m / 24 mois, cible exclue)** :

| Année | sans voisin (NULL) | 0 vente | 1-5 ventes | > 5 ventes |
|---|---:|---:|---:|---:|
| 2020 | 11 779 | 210 003 | 201 010 | 8 871 |
| 2025 | 11 779 | 208 553 | 203 929 | 7 402 |

≈ 49 % des parcelles ont AU MOINS une vente voisine dans les 24 mois — la feature vit
sur la moitié du frame (contre 19 % pour le bloc propriétaire d'ALGO-2) ; 76 416
parcelles (18 %) ont un MITOYEN DIRECT muté sous 36 mois en 2025.

## ANTI-FUITE (règle 4) — exécuté AVANT tout entraînement : **PASS ✓**

1. Paires où la cible porte elle-même la mutation : **0** (niveau 1) ;
2. Paires « permis rattaché à la cible » : **0** (niveau 2 permis) ;
3-4. **Recompte MANUEL indépendant** (ST_DWithin direct sur les sources, sans passer
   par les tables de paires) : 12 parcelles × 3 années (2020/2023/2025), ventes ET
   permis normalisés → **36/36 exacts, 0 écart**. Aucune mutation ≥ 01/01/Y ne peut
   entrer par construction du recompte (fenêtres recalculées à la main).

## ⛔ POINT D'ARRÊT A — attendu : feu vert Vic avant le LOT B

Features prêtes (10 années, 431 663 parcelles) : ventes_50/100/200m_24m (densités
normalisées), delai_derniere_vente_voisine, permis_100m_24m/permis_200m_36m
(accordés seulement — caveat conservé) + distance_permis_recent,
voisin_direct_mute_36m + nb_voisins_directs, **ecart_rotation_local_secteur**
(le différentiel « ça bouge ici plus qu'alentour »).
LOT B prévu : protocole champion à l'identique (6 folds, seed 974, C=5, isotonique),
ablations par FAMILLE et par RAYON, RR par commune (les 4 cibles), churn, permutation,
Δ apparié vs champion — anti-fuite déjà verrouillé.

---

# LOT B — CHALLENGER (exécuté sur feu vert Vic, 3 réserves intégrées)

Protocole champion à l'identique : 6 folds walk-forward (train ≤ F−2, calibration
isotonique F−1, test F), seed 974, C = 5.0, 5 interactions gelées, WoE min 200/bin,
bin « manquant » distinct du « 0 vente ». Δ appariés (bootstrap 1000, IC95) contre les
scores hors-échantillon du champion fold 2025 (`reports/m36-foncier/scores-2025-fold-final.csv`,
RR 6,73). Artefacts : `reports/algo3/{correlations,ablations,rr-commune}-2025.csv`,
`walk-forward.csv`, `synthese.json`.

## Réserves 1-2 : corrélations (Spearman, fold 2025) — l'information EST nouvelle

| Feature | rot_nu | rot_bati | dens_bati_secteur | pct_bati_secteur |
|---|---:|---:|---:|---:|
| ventes_50m_24m | 0,07 | 0,16 | 0,11 | 0,10 |
| ventes_100m_24m | 0,12 | 0,28 | 0,20 | 0,18 |
| ventes_200m_24m | 0,19 | **0,38** | 0,25 | 0,23 |
| ecart_rotation_local_secteur | **−0,12** | **−0,01** | 0,05 | 0,05 |
| permis_100m_24m | 0,08 | 0,11 | 0,17 | 0,14 |

- **Colinéarité (réserve 1)** : max 0,38 (ventes_200m ↔ rot_bati) = corrélation modérée,
  pas une redite du bloc Z. L'écart différentiel est quasi orthogonal (−0,12 / −0,01) :
  c'est bien de l'information NOUVELLE.
- **Proxy d'urbanité (réserve 2)** : ventes_100m ↔ densité bâtie = 0,20 seulement.
  Le piège « la feature mesure juste la ville » est écarté.

Conclusion des réserves : le bloc V apporte une information génuinement nouvelle…
dont il reste à prouver qu'elle PRÉDIT. C'est là que ça casse.

## Walk-forward FULL (champion + bloc V complet)

| Fold | RR FULL [IC95] | ECE |
|---|---|---|
| 2020 | 11,79 [10,34 ; 13,05] | 0,0012 |
| 2021 | 9,97 [8,75 ; 11,14] | 0,0029 |
| 2022 | 10,35 [9,36 ; 11,68] | 0,0021 |
| 2023 | 7,92 [7,00 ; 9,38] | 0,0033 |
| 2024 | 8,83 [7,63 ; 10,34] | 0,0032 |
| 2025 | 7,18 [5,99 ; 8,19] | 0,0014 |

**Δ île fold 2025 (apparié) : +0,46 [−0,52 ; +1,44] — NON significatif.**
Calibration saine (ECE ≤ 0,0033 partout).

## Ablations fold 2025 (appariées vs BASE = champion re-fit, RR 6,73)

| Variante | RR | Δ vs BASE [IC95] |
|---|---:|---|
| +VENTES (4 features) | 6,27 | −0,46 [−1,05 ; +0,63] |
| +PERMIS (3) | 6,84 | +0,11 [−0,80 ; +0,96] |
| +MITOYEN (2) | 6,84 | +0,11 [−0,73 ; +0,91] |
| **+ECART (1, le test le plus informatif — réserve 1)** | 6,56 | **−0,17 [−0,95 ; +0,73]** |
| +V50 | 6,21 | −0,51 [−1,34 ; +0,40] |
| +V100 | 6,50 | −0,23 [−1,06 ; +0,62] |
| +V200 | 6,44 | −0,29 [−1,03 ; +0,51] |
| FULL (tout) | 7,18 | +0,46 [−0,52 ; +1,44] |

- **Aucune famille, aucun rayon, ne sort du bruit.** Les rayons pris isolément sont
  tous légèrement NÉGATIFS.
- **+ECART, le juge de paix promis en réserve 1** (seule feature orthogonale au bloc Z),
  est à −0,17 ns : le signal différentiel « ça bouge ici plus qu'alentour », une fois la
  rotation secteur déjà dans le modèle, n'ajoute AUCUNE discrimination hors-échantillon.
  C'est la réfutation la plus propre de l'hypothèse de contagion à cette granularité.
- Le +0,46 du FULL n'est porté par aucune famille identifiable — signature d'un artefact
  d'ensemble, pas d'un signal.
- **Stabilité des signes : 32/39** — et parmi les instables… `ventes_100m_24m` elle-même :
  le signe de la feature vedette CHANGE selon les folds.

## RR par commune (réserve 3 : qui paye quoi) — bilan COMPLET, Δ appariés

Les 4 communes cibles du mandat (celles qu'ALGO-1b montrait faibles) :

| Commune | RR champion | RR FULL | Δ [IC95] | Verdict |
|---|---:|---:|---|---|
| **Le Tampon** (97422) | 3,06 | 2,04 | **−1,02 [−2,53 ; +0,53]** | penche NÉGATIF |
| **Saint-Joseph** (97412) | 2,47 | 2,47 | 0,00 [−3,18 ; +4,03] | plat |
| **Saint-Philippe** (97417) | 11,99 | 11,99 | 0,00 [−22,4 ; +11,9] | plat (11 cibles — inexploitable) |
| **Saint-Denis** (97411) | 3,76 | 4,39 | +0,63 [−2,66 ; +3,11] | plat |

**L'hypothèse fondatrice du mandat n'est PAS confirmée : les communes pour lesquelles
le bloc a été conçu ne bougent pas — et le Tampon penche vers le bas.**

Le cas séparé demandé par Vic (« île plate MAIS les 4 montent sans compensation ») ne
s'applique donc pas : les 4 sont plates ou en baisse.

Ailleurs (aucun Δ significatif, mais le MOTIF compte) : les hausses apparentes se
concentrent sur de petites communes (Sainte-Suzanne +13,0 ns, Salazie +6,1 ns, Le Port
+3,8 [0,00 ; +7,08] borne basse à zéro) et sont payées par les GROSSES : Saint-Benoît
−3,51 [−9,58 ; 0,00], Les Avirons −2,86 [−6,31 ; 0,00], Saint-Pierre −1,16, Saint-Paul
−0,84, Saint-Louis −1,02 ns. C'est exactement le schéma de REDISTRIBUTION que la
réserve 3 interdit de vendre comme un gain — ici doublé d'un churn qui le confirme.

## Garde-fous

- **Churn top-1158 : 42 %** — budget mandaté 25 % : **EXPLOSÉ**. Même à Δ nul, le bloc
  remue 487 parcelles du top pour rien.
- **Permutation (features V mélangées) : RR 0,57** ≈ hasard ✓ — le harnais ne fabrique
  pas de signal.
- **Boussole (proxy)** : 1 hit = 97423000AB1341 — vérifié : `etage0: true` dans le
  golden, statut servi « écartée ». Même artefact rang-brut-vs-étage-0 que documenté
  en ALGO-2 : dans le pipeline réel l'étage 0 prime. Pas une violation.
- **Champion intouché** : aucune écriture hors tables `algo3_` ; tiers du run servi
  `q_v7_defisc` revérifiés post-run **au bit près** : 120 / 1 031 / 3 587 / 72 980 /
  353 945 ✓.

---

# LOT C — VERDICT : **NE PAS PROMOUVOIR**

1. **Δ île : +0,46 [−0,52 ; +1,44], non significatif** — la règle du mandat (« pas de
   promotion sans ΔRR franchement significatif ») tranche seule.
2. **Les 4 communes cibles ne bougent pas** (Tampon penche négatif) : le bloc échoue
   précisément là où il devait servir.
3. **Churn 42 % > budget 25 %** : coût opérationnel pur, sans contrepartie.
4. **Signe instable de ventes_100m_24m** entre folds : le modèle ne sait même pas dans
   quel SENS la feature agit.
5. Les mouvements communaux sont une redistribution petites-communes ← grosses-communes,
   pas un gain (réserve 3 appliquée).

**Lecture honnête du null** : les corrélations prouvent que l'information hyper-locale
est NOUVELLE (écart différentiel orthogonal au bloc Z) — mais nouvelle ≠ prédictive.
Une fois la rotation secteur dans le modèle, la contagion spatiale à 50-200 m n'améliore
pas l'identification du top-1158 hors-échantillon. L'hypothèse « le secteur est trop
grossier dans les communes denses » est REJETÉE en l'état : soit la contagion opère à
l'échelle du secteur (déjà capturée), soit elle est trop bruitée à ≤ 200 m avec ~10-123
voisins pour émerger dans une logistique WoE.

## Ce qu'il resterait à essayer (exigé par le mandat)

1. **L2-OP (multi-parcelles d'une même opération)** : la contagion la plus dure est
   peut-être INTRA-opération (assemblages), pas inter-voisins — le NOT EXISTS qui
   protège de la fuite écarte aussi ce signal ; il faudrait le réintroduire PROPREMENT
   (opération datée antérieure, parcelles distinctes).
2. **Multi-horizon** : 24/36 mois sont peut-être trop courts pour un cycle foncier
   réunionnais ; tester 5-8 ans (le délai médian dépôt→autorisation seul fait ~9 mois).
3. **Effets fixes communaux** : reste LA piste ouverte par ALGO-1b — les 4 communes
   faibles le sont structurellement (calibration, pas features). Ni ALGO-2 ni ALGO-3
   n'ont trouvé de feature qui les remonte : la correction est peut-être dans
   l'INTERCEPT par commune, pas dans les X.
4. (Hérité d'ALGO-2, toujours valable) : B2 tenure fine (+0,34 ns, 100 % du frame) à
   retester au prochain re-train annuel.

**Compteur mandats algo sans victoire : ALGO-2, ALGO-3.** Deux blocs de features
neufs, deux protocoles propres, deux nulls — le prochain essai devrait changer de
LEVIER (calibration/structure) plutôt que d'ajouter des X.

*Tables `algo3_*` conservées en base (préfixées, hors pipeline) ; suppression sur
un mot de Vic.*
