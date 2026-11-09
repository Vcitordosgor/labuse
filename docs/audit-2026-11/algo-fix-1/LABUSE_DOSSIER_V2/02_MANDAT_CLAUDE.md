# Mandat à transmettre à Claude Code

Lis intégralement `01_SPECIFICATION_ALGORITHME.md` et examine `03_MAQUETTE.html`. La spécification est la référence normative. Le moteur de référence est pédagogique : il n’exécute ni le SIG ni le modèle de mutation réels.

## Objectif

Faire évoluer l’Analyse LABUSE afin qu’elle serve plusieurs métiers sans confondre potentiel de logement et probabilité de vente, et sans perdre des parcelles de la sélection.

Le parcours utilisateur est fixé : **filtres existants → Voir les parcelles OU Analyser avec LABUSE**. Les suggestions précédentes de nouveaux onglets Recherche/Analyse ou d’une nouvelle catégorie principale ne sont pas retenues.

## Décisions à respecter

1. Même univers de parcelles entre liste simple et analyse complète ; toutes les causes restent consultables.
2. En prospection, le Signal est principal ; une capacité additionnelle nulle ne supprime pas mécaniquement le bien.
3. Le modèle de mutation reste limité à sa cible et à son domaine vérifiés. Une population nouvellement visible ne reçoit pas une probabilité extrapolée sans validation.
4. Aucune réactivation de Priorité, aucun changement de recette, seuils, calibration, prétraitement ou définition de feature à l’occasion de cette refonte.
5. En potentiel foncier, distinguer conservation, reconstruction et préétude de division pour logement.
6. Conservation : marge arithmétique `max(0, capacité − existant)`, identifiée comme théorique tant que l’insertion n’est pas contrôlée ; aucun malus de démolition complète.
7. Reconstruction : capacité totale, existant et différence nette **signée**, calculés pour toutes les parcelles concernées ; pas uniquement les saturées.
8. Division : repérage et informations, aucun nombre de lots ni certification sans moteur dédié.
9. Donnée absente, donnée nulle, incompatibilité, horizon différé et erreur technique sont des états distincts.
10. La V2 ne remplace pas les anciens poids par de nouveaux coefficients prétendument calibrés. Elle ne sert pas de note globale 0–100 ; elle expose statuts, quantités, points de vigilance et tris nommés.

## Première étape : vérifier l’existant réel

Avant les modifications, cartographie le chemin complet filtres → requête → cascade → caches → calculs → groupes → liste/carte/détail/export.

Identifie et rapporte :

- les versions actives du moteur, du modèle et du run ;
- le prédicat exact de la cible L2-F, les univers d’entraînement/calibration/application et leurs exclusions ;
- le sens exact des colonnes `p_raw`, probabilité calibrée et valeur effectivement servie ;
- les mappings Fort/Moyen/Faible/Priorité et les verrous actifs ;
- les entrées critiques et les causes produites par chaque chemin ;
- le dénominateur des pourcentages d’emprise ;
- les dépendances et l’état réel de RESIDUEL-1 et des tâches de déploiement mentionnées dans l’ancien rapport ;
- les endroits où une exclusion logement retire un bien de la prospection ;
- les endroits où une valeur absente devient zéro, où une cause manque et où les compteurs diffèrent de l’univers réel.

Les chemins du rapport sont des pistes. Adapte-toi à la structure effective du dépôt. Si un constat du rapport est devenu obsolète, documente-le et applique les contrats de la spécification au code réel.

## Mise en œuvre recommandée

Travaille dans une branche isolée selon les conventions du projet. Conserve les modifications de présentation, les contrats de scénario et les features historiques du Signal dans des chemins/versionnements compatibles.

1. Ajoute un instantané de recherche et des contrats de sortie traçables.
2. Ajoute les statuts et causes par scénario, sans écraser les caches historiques du Signal.
3. Corrige les anomalies démontrées et fournis les preuves géométriques des cas sensibles.
4. Branche les tris explicites et le maintien de tout l’univers de sélection.
5. Adapte l’interface actuelle en conservant filtres, deux sorties et choix d’usage.
6. Vérifie carte, liste, détail, pagination et export sur le même instantané.
7. Calcule V1/V2 en parallèle et fournis une comparaison avant changement du service.

Ne transforme pas les constantes pédagogiques, identifiants EX-xxx, probabilités fictives ou hypothèses de la maquette en configuration de production.

Ne remplace pas le correctif « terrain exigu » par une règle de taille >500 m². Ne nomme pas les 139 causes vides « saturation en hauteur » sans preuve. Ne remplace pas les seuls zéros par `capacité table rase ×0,65`.

Si une donnée ou un domaine n’est pas disponible, implémente le statut et la cause appropriés. Ne crée pas un résultat vraisemblable pour remplir une fiche. Les parties indépendantes peuvent avancer pendant la clarification d’un point critique.

## Validation et livraison

Exécute la recette de la spécification et les vérifications pertinentes du dépôt. La réussite des tests pédagogiques n’est pas une validation du produit réel.

Le compte rendu final doit contenir :

- l’état de référence et les divergences factuelles avec le rapport initial ;
- les fichiers et contrats modifiés ;
- les résultats avant/après sur le même univers, avec effectifs par statut et causes ;
- la préservation des artefacts et features du Signal, ou l’identification de toute modification requérant une validation séparée ;
- les cas géométriques vérifiés et leurs preuves ;
- les tests réellement exécutés, leurs résultats et les validations encore manquantes ;
- la procédure d’activation et de retour arrière cohérente avec le processus du projet.

Ce mandat ne demande pas de modifier le run servi, de déployer, de réentraîner, d’élargir le domaine ML ou de réactiver un tier sans instruction et validation adaptées. Il demande une implémentation isolée, vérifiable et prête à être revue.
