# Candidat SCORING-2 du 03/09/2026 — note de version

**Rien de servi ne change : ceci décrit un CANDIDAT d'arène. Le run servi reste `q_v11_m137`.**

## Ce qui change dans le candidat (champion K4 bis)
- censoring : détention et permis à couverture 100 % (valeur connue OU bin censuré explicite « ≥ N ans », jamais un inconnu muet) ;
- 4 variables mortes retirées (ndvi, canopée, accès équipements, friche) + doctrine M35 (5 `retired` hors de tout nouveau fit) ;
- résiduel lu à 100 % (zéros M125 + cause explicite, hors_plu seul inconnu) ;
- architecture GLOBALE conservée : les 4 modèles segmentés ont été mesurés (K4) — calibration meilleure mais discrimination moindre (la mise en commun des 3 M de lignes gagne) ; l'isotonique par segment reste la piste ;
- voisinage et marché as-of (ventes 150/400 m, permis 100 m, PA 400 m, marché communal, PM vendeur actif) — test de fuite dédié : passé.

## Les chiffres (protocole année vierge : train ≤2023, cal 2024, test 2025)
- précision@100 par commune (médiane) : 0.060 → 0.075 ;
- Priorité : 13.7% de ventes réelles sur 73 parcelles → 6.6% sur 91 (effectif ×1.2) ;
- À suivre : 10.1% sur 643 → 10.7% sur 608 ;
- lift du décile supérieur : 2.06 → 2.11 ;
- AUC global : 0.613 → 0.610 (bâti 0.584, nu 0.657, PM 0.681, copro 0.610) ;
- ECE global : 0.0012 ;
- churn top-1158 vs le run servi : 45.3%.

## Le challenger (gradient boosting, monotonie métier)
- AUC 0.607, préc@100 méd 0.070, Priorité 19.7% (76), lift décile 1.93 ;
- règle de promotion satisfaite : NON (promotion NON appliquée — décision Vic).
