Candidat q_v14 du 08/09/2026 — les deux améliorations combinées (gains de MODÈLE q_v12 + gains de DONNÉES q_v13_sources1), produites par le pipeline réel.

Ce qui change vs le servi : la recette q_v12 (4 mortes + 5 retired retirées, résiduel lu à 100 %, voisinage/marché as-of, calibration isotonique par segment) PLUS quatre variables reconstruites à la date de chaque ligne — l'état bâti/nu et la part bâtie du secteur (Sitadel + DVF), le permis déposé par un professionnel sur une parcelle de particulier, l'ancienneté du PLU, et la part des ventes du secteur parties à des sociétés.

Les données du jour et la cascade de q_v13_sources1 (dont 4 378 exclusions neuves fondées sur des servitudes réelles) entrent AU RUN, réutilisées sans rejeu — la cascade est orthogonale au modèle.

Les chiffres (banc K0, année vierge 2025 : train ≤2023, cal 2024) :
- précision@100 par commune (médiane) : servi 0.060 · q_v12 0.080 · q_v14 0.080 ;
- Priorité : servi 13.7% sur 73 → q_v14 30.5% sur 82 (effectif ×1.1) ;
- lift du décile supérieur : servi 2.06 · q_v12 2.27 · q_v14 2.27 ;
- AUC global : servi 0.613 · q_v12 0.620 · q_v14 0.626 (nu 0.664, PM 0.669) ;
- ECE global q_v14 : 0.0020 (bâti 0.0018, nu 0.0058, PM 0.0045, copro 0.0140) ;
- segments dont l'ECE se dégrade de plus de 0,01 vs q_v12 : aucun ;
- churn top-1158 vs le run servi : 51.3% (la garde de churn liste les sorties de Priorité au compte-rendu) ;
- horizon 24 mois (test 2024) : AUC 0.642, préc@100 méd 0.110 — colonne stockée.

Rien de servi ne change tant que la bascule n'est pas faite : `q_v11_m137` reste le run servi. La bascule est un geste manuel (`golden promote`), réversible.
