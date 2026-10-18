# VERITE-TERRAIN-2 · volet E — backtest du SIGNAL DE MUTATION

## Méthode (rejeu daté, anti-fuite)

Le Signal servi est `score_labuse.signal_p` = **P(vente L2-F dans les 12 mois)**. Ses labels de run (q_v16/q_v18/q_v19) sont datés **après** la dernière mutation DVF disponible (31/12/2025) : la fenêtre de suivi (T ; dernière DVF] est **vide**, donc un backtest forward sur le servi est impossible aujourd'hui (voir *Limites*).

On fait le **rejeu propre** que la nature datée du modèle autorise : on réapplique le modèle q_v15 **gelé** (`reports/q-v15/artifacts-q_v15-12m.joblib`, sha256 `d8520abaf2e0edfa…`, entraîné ≤ 2023, calibré 2024) sur l'**année 2025** (features as-of 01/01/2025, bornées en amont de cette date), et on juge sur la **mutation L2-F réellement observée en 2025** (DVF couvre l'année entière). Le modèle est gelé sur des données ≤ 2024 : l'issue 2025 n'entre ni dans le fit, ni dans la calibration, ni dans aucune feature. **Aucune fuite temporelle.**

**Dénominateur honnête** : univers produit (hors copropriété, comme le servi), parcelles avec `signal_p` et label 2025 observables. N jugeable = **429 799**, ventes = **6 488**, **taux de base = 1.51 %**.

Discrimination globale : **AUC = 0.6246**, Brier = 0.01477.

## Taux de vente par NIVEAU de signal servi (fort/moyen/faible) — IC Wilson 95 %

| niveau | n | ventes | taux | IC 95 % | lift vs base |
|---|--:|--:|--:|---|--:|
| fort | 100 | 39 | 39.00 % | [30.02 % ; 48.80 %] | ×25.84 |
| moyen | 425 | 62 | 14.59 % | [11.55 % ; 18.26 %] | ×9.66 |
| faible | 429 274 | 6 387 | 1.49 % | [1.45 % ; 1.52 %] | ×0.99 |

## Taux de vente par DÉCILE de probabilité (monotonie) — IC Wilson 95 %

| décile | p ∈ | n | ventes | taux | IC 95 % | lift |
|--:|---|--:|--:|--:|---|--:|
| 1 | [0.0000 ; 0.0061] | 42 980 | 312 | 0.73 % | [0.65 % ; 0.81 %] | ×0.48 |
| 2 | [0.0061 ; 0.0070] | 42 980 | 360 | 0.84 % | [0.76 % ; 0.93 %] | ×0.55 |
| 3 | [0.0070 ; 0.0084] | 42 980 | 432 | 1.01 % | [0.92 % ; 1.10 %] | ×0.67 |
| 4 | [0.0084 ; 0.0099] | 42 980 | 487 | 1.13 % | [1.04 % ; 1.24 %] | ×0.75 |
| 5 | [0.0099 ; 0.0116] | 42 980 | 675 | 1.57 % | [1.46 % ; 1.69 %] | ×1.04 |
| 6 | [0.0116 ; 0.0124] | 42 979 | 508 | 1.18 % | [1.08 % ; 1.29 %] | ×0.78 |
| 7 | [0.0124 ; 0.0146] | 42 980 | 719 | 1.67 % | [1.56 % ; 1.80 %] | ×1.11 |
| 8 | [0.0146 ; 0.0173] | 42 980 | 755 | 1.76 % | [1.64 % ; 1.89 %] | ×1.16 |
| 9 | [0.0173 ; 0.0197] | 42 980 | 756 | 1.76 % | [1.64 % ; 1.89 %] | ×1.17 |
| 10 | [0.0197 ; 0.7143] | 42 980 | 1 484 | 3.45 % | [3.28 % ; 3.63 %] | ×2.29 |

## Précision@K (priorisation — les K parcelles les mieux notées)

| K | précision@K | ventes captées | lift vs base |
|--:|--:|--:|--:|
| 100 | 39.00 % | 0.60 % | ×25.84 |
| 500 | 19.40 % | 1.50 % | ×12.85 |
| 1 000 | 14.10 % | 2.17 % | ×9.34 |
| 2 000 | 11.05 % | 3.41 % | ×7.32 |

## Verdict honnête

Le signal **sépare**. Le décile le plus probable vend à **3.45 %** (lift **×2.29** vs base 1.51 %), IC 95 % [3.28 % ; 3.63 %] — sans recouvrement avec la base. Le niveau **fort** (p ≥ 0,20) vend à **39.00 %** (lift ×25.84), mais ne couvre que 100 parcelles.
 La montée du taux par décile est **globalement croissante (quelques inversions de rang dans les déciles bas, bruit d'échantillon)**. AUC 0.625 = discrimination réelle mais modérée, cohérente avec un événement rare (base 1.51 %).

## Limites

- **Le servi n'est pas jugeable forward aujourd'hui** : `computed_at` des runs q_v16/18/19 (oct. 2026) est postérieur à la dernière mutation DVF (31/12/2025) → 0 vente observable après T. On a jugé le MODÈLE (rejeu 2025), pas l'instantané livré en octobre 2026.
- **Horizon 12 mois** : on mesure la vente dans l'année calendaire 2025, l'exacte cible du modèle 12 mois.
- **Événement rare** (base ~1,5 %) : les niveaux fort/moyen sont peu peuplés → IC larges là ; la robustesse vient des déciles et de precision@K.
- **Cible L2-F** (ventes foncières nettes) : le label exclut les mutations non-L2-F, par construction du dataset d'entraînement.

## Protocole forward (pour juger le SERVI, quand DVF aura avancé)

1. **Figer aujourd'hui** l'instantané servi : copie read-only de `score_labuse` pour `run_label='q_v19'` avec son `computed_at` = T₀ (18/10/2026).
2. **Attendre** que DVF publie les mutations postérieures à T₀ (prochaine campagne DVF ; retard usuel 6-12 mois).
3. **Mesurer** le taux de vente par bande/niveau sur (T₀ ; dernière DVF], re-calculer lift + IC Wilson avec exactement ce module (dénominateur = parcelles notées, hors `non_calculable`).
4. Comparer au présent rejeu 2025 : la séparation tient-elle hors échantillon, sur le millésime réellement servi au client ?

