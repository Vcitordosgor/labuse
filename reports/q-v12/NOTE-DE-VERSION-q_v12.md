Candidat q_v12 du 03/09/2026 — les gains sûrs de SCORING-2, produits par le pipeline réel.

Ce qui change : 4 variables mortes + 5 retired retirées (K2) · résiduel lu à 100 % (zéros M125, hors_plu seul inconnu — K3) · voisinage et marché as-of, architecture globale (K4 bis, fuite testée) · calibration isotonique par segment sur 2024 (seul apport de K4 retenu) · censoring explicite (détention/permis couverts à 100 %). Horizon 12 mois servi ; 24 mois calculé et stocké (p_24m), rien d'affiché.

Les chiffres (banc K0, année vierge 2025 : train ≤2023, cal 2024) :
- précision@100 par commune (médiane) : 0.060 → 0.080 ;
- Priorité : 13.7% sur 73 parcelles → 7.6% sur 79 (effectif ×1.1) ;
- lift du décile supérieur : 2.06 → 2.27 ;
- AUC global : 0.613 → 0.620 (nu 0.654, PM 0.673) ;
- ECE global : 0.0022 (par segment : bâti 0.0016, nu 0.0057, PM 0.0049, copro 0.0157) ;
- churn top-1158 vs le run servi : 48.4% (la garde de churn liste les sorties de Priorité au compte-rendu) ;
- horizon 24 mois (test 2024) : AUC 0.638, préc@100 méd 0.125 — colonne stockée.

Rien de servi ne change tant que la bascule n'est pas faite : `q_v11_m137` reste le run servi. La bascule est un geste manuel (Données › Circuit › Basculer), réversible (retour arrière tracé).
