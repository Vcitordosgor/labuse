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
