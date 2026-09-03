# MANDAT SCORING-2 — Fondations du score v2

**Branche : `feat/scoring-2`**. Aucun sous-agent ne touche à git.
**Références** : `docs/audit-2026-09/SCORING-RAPPORT.md`, `docs/audit-2026-09/LABUSE-SCORE-V2-PLAN.md` (sections 2 et 3).
**Doctrine** : **rien de servi ne change.** Tout en arène, sur des runs candidats. `q_v11_m137` reste servi. Vic bascule plus tard si l'année vierge dit oui.
**Clôture** : tsc, build, tests 100 % verts, commit à la fin de CHAQUE lot K.

**Étape 0** : pwd, branche, arbre propre. Puis relire `scripts/audit/scoring/` : le harnais de SCORING-1 (validé à 1,7·10⁻⁷ de la prod) est **le** banc de mesure — le réutiliser, ne pas en écrire un second.

## K0 — Le banc de mesure, figé avant tout changement

1. **Protocole unique** : entraîner ≤ 2023 · calibrer 2024 · tester 2025 (année vierge, jamais touchée par la calibration). Dans `scripts/audit/scoring/protocole.py`, utilisé par chaque lot.
2. **Métriques à chaque lot**, sur 2025, **précision en haut de liste en tête** : précision@100 par commune (médiane sur 24) · précision réelle de Priorité et À suivre · effectif de Priorité · lift du décile supérieur · AUC global et par segment · ECE par segment · churn vs q_v11_m137.
3. **Hygiène de la cible**, avant toute mesure : une mutation multi-parcelles compte une fois par parcelle avec un indicateur « vente groupée » ; vérifier qu'aucune vente à un client LABUSE (courrier ou piste CRM antérieurs) n'est dans 2025 sans être marquée — les exclure de l'évaluation, les compter à part.
4. **Ligne de base** : le modèle actuel mesuré par ce protocole (SCORING-1 calibrait sur 2025 — on s'attend à un peu moins bien). C'est le chiffre à battre.

## K1 — Le censoring : l'absence est une information

1. **Détention** : « pas de mutation connue depuis le début de DVF » devient une valeur censurée explicite (`≥ N ans`, N = ancienneté de l'historique de la commune) + indicateur « censuré ». Couverture 100 %.
2. **Permis** : absence = 0, avec l'ancienneté du dernier permis connu si elle existe. Couverture 100 %.
3. **nu_constructible** : dépend de K3 ; en attendant, distinguer « non calculé » de « non constructible ».
4. Mesurer après K1 seul. Attendu : AUC +0,04 à +0,07.

## K1 bis — Deux horizons

Produire 12 et 24 mois par parcelle, mesurer les deux. L'horizon 24 mois a ~2× plus de positifs : vérifier s'il classe mieux. Rien d'affiché.

## K2 — Retirer les variables mortes

ndvi, canopée, accès équipements, friche sortent du candidat. L'AUC ne doit pas baisser, la stabilité (bootstrap) doit s'améliorer. Colonnes conservées en base, plus lues.

## K3 — Le résiduel à 100 %

Établir pourquoi 41,3 % restent vides (zonage non traduit ? PLU absent ? erreur ?), ventiler par cause, compléter tout ce qui est complétable. Ce qui ne l'est pas porte une cause explicite. Poste lourd (1 h 47) : mesurer et rendre incrémental si possible.

## K4 — Quatre segments, pas un

Un modèle par segment : **bâti individuel** · **terrain nu** · **personne morale** · **copropriété** (base 29 %, isolée du classement promoteur). Zone A hors apprentissage (écartée par la cascade). Mesurer par segment.

## K4 bis — Le voisinage et le marché (as-of, jamais avec le futur)

1. ventes DVF dans 150 m et 400 m sur 12 et 24 mois, et variation ;
2. permis Sitadel dans 100 m et opérations de promoteur (groupes de permis) dans 400 m ;
3. prix de secteur et volume de transactions communal sur l'année précédente, tendance 3 ans ;
4. personnes morales : le propriétaire a-t-il vendu une autre parcelle dans les 24 mois (via SIREN).
**Test de fuite dédié** : aucune variable ne doit contenir d'information postérieure à la date de référence. Mesurer.

## K5 — Le challenger en arène

1. **Gradient boosting** (LightGBM ou équivalent) avec **contraintes de monotonie** sur les variables métier, par segment, calibration isotonique 2024, test 2025.
2. Comparé au champion (après K1-K4 bis) dans l'arène : mêmes parcelles, même protocole, tableau côte à côte.
3. **Règle de promotion** (écrite, pas appliquée) : gagner sur la précision en haut de liste **et** l'AUC **et** ECE ≤ 0,01 par segment, sur 2025.
4. Rien n'est promu dans ce mandat.

## K6 — Trois raisons en français

Les trois contributions dominantes (SHAP) traduites en phrases courtes, sourcées, datées : « Détenue depuis plus de 15 ans (DVF) » · « Permis accordé en 2025 sur la parcelle voisine (Sitadel) » · « Zone UB, 640 m² de SDP résiduelle (PLU 2024) ». Table de traduction variable → phrase, relue pour le français. Ce lot produit la colonne, n'affiche rien.

## K7 — Ce que le run candidat enregistre

Protocole, segments, variables et couvertures, métriques K0, millésimes des sources, et la **note de version** en français (« candidat du 05/09 : censoring détention, 4 variables retirées, résiduel 94 % — précision@100 0,12 → 0,19, Priorité ×10 → ×9 sur un effectif ×2,4 »).

---

## Compte-rendu attendu

**Un seul tableau**, colonnes = ligne de base · K1 · K1 bis · K2 · K3 · K4 · K4 bis · challenger K5, lignes = les métriques K0. Puis : K3 la ventilation des 41,3 % · K4 bis le résultat du test de fuite · K5 le verdict de l'arène et si la règle de promotion est satisfaite · K7 la note de version du meilleur candidat. Recommandation en trois lignes : promouvoir, attendre PROPRIETAIRE-1, ou continuer.
