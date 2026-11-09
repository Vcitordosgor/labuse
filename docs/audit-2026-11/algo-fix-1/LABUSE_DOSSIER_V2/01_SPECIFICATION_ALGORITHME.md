# Analyse LABUSE V2 — spécification proposée

Version : **ALGO-LABUSE-2 / proposition 1.0 — 9 novembre 2026**.

Destinataires : propriétaire de LABUSE et Claude Code. Ce document est la référence normative du dossier. La maquette et le moteur de référence illustrent ces règles sur des données fictives. Ils ne remplacent ni le moteur géométrique ni le modèle statistique de LABUSE.

## 0. Périmètre et décision de navigation

Le parcours validé est conservé : **filtres actuels → « Voir les parcelles » OU « Analyser avec LABUSE »**.

- Les filtres, leurs fonctions et leurs critères métier existants restent disponibles.
- « Voir les parcelles » fournit une liste descriptive sans classement algorithmique implicite.
- « Analyser avec LABUSE » ouvre l’analyse de cette même sélection.
- Aucun nouvel onglet Recherche/Analyse, aucune rubrique principale Analyse et aucun nouveau parcours obligatoire ne sont demandés.
- Dans l’analyse, l’objectif choisi est visible : **Prospection vente** ou **Potentiel foncier**. Dans le second cas, le scénario est explicite.
- Les captures du produit montrent que le choix d’usage existe déjà. Il faut le rendre cohérent avec les résultats, pas reconstruire toute la navigation.

**Périmètre technique de cette proposition :** architecture de classement, sens des quantités, statuts, explications, contrats de données, conditions de validation et migration. Les chemins et versions cités dans le rapport utilisateur sont des points de départ à vérifier dans le dépôt. Aucun accès au code source ou à la production de LABUSE n’a été effectué pour rédiger ce dossier.

## 1. Décision centrale : supprimer le verdict immobilier universel

LABUSE sert agents, apporteurs d’affaires, promoteurs, lotisseurs, aménageurs et autres professionnels. La capacité à produire du logement ne représente pas à elle seule l’intérêt d’un bien pour ces utilisateurs.

La V2 proposée **ne calcule pas une nouvelle note globale de 0 à 100**. Elle remplace la note universelle par :

1. un **Signal de mutation** dans son périmètre statistique validé ;
2. des **capacités et conclusions par scénario** ;
3. un **tri nommé**, décrivant exactement la grandeur classée ;
4. les **données manquantes, les points de vigilance et les raisons** du résultat.

Les bandes historiques Excellente/Bonne/À étudier/Faible ne doivent pas être réutilisées comme appréciation générale dans cette nouvelle analyse. Le calcul historique peut rester disponible en parallèle pendant la migration, avec sa version et son périmètre « logement » explicites.

### Pourquoi ce choix

Les coefficients 0,85/0,80/0,65 du rapport sont des heuristiques. En proposer de nouveaux sans données de validation produirait une précision artificielle. La première V2 doit être exacte sur ce qu’elle mesure, reproductible et auditable. Un indice synthétique par scénario pourra être étudié ultérieurement ; sa calibration constitue un autre travail.

**Conséquence assumée :** un tri « SDP supplémentaire décroissante » privilégie le volume de SDP, pas la meilleure affaire. L’interface doit nommer ce tri. Les points de vigilance restent immédiatement visibles et peuvent faire l’objet de filtres explicites. Une grande parcelle difficile ne reçoit pas automatiquement le mot « Excellente ».

La profession peut mémoriser une préférence d’affichage. Elle ne change ni le règlement, ni les faits, ni les probabilités. L’objectif sélectionné commande l’analyse.

## 2. Architecture commune

```text
Filtres existants
  → instantané de recherche S0 : identifiants uniques + critères + versions
  → faits et provenance, une ligne par parcelle de S0
      → liste simple, sans classement implicite
      → analyse
          → Signal de mutation : chaîne historique et domaine vérifiés
          → scénario foncier : règles, géométrie, capacités, statut local
  → tri explicite, filtres de résultats, carte, détail et export cohérents
```

### 2.1 Contrat de sélection

Soit `S0` l’ensemble des identifiants retournés par les filtres pour un instantané donné.

```text
IDs(liste_simple) = IDs(analyse_complète) = S0
N_selection = somme des effectifs des statuts exclusifs de l’analyse
```

L’analyse ajoute des statuts. Elle ne retire pas silencieusement les parcelles sans potentiel logement, les signaux non évalués, les erreurs ou les données manquantes.

Un filtre explicite dans les résultats peut réduire l’affichage. Il faut alors distinguer `N_selection`, `N_affichables_apres_filtres` et `N_sur_la_page`. « Tous » signifie tous les statuts de la sélection, y compris les cas à vérifier et hors projet.

### 2.2 Instantané et versions

Chaque réponse contient au minimum :

```json
{
  "analysis_version": "ALGO-LABUSE-2",
  "query_snapshot_id": "opaque",
  "criteria_hash": "opaque",
  "candidate_ids_hash": "opaque",
  "candidate_count": 0,
  "facts_snapshot_id": "opaque",
  "scenario_engine_version": "opaque",
  "signal_model_version": "opaque-or-null",
  "signal_feature_schema_version": "opaque-or-null",
  "signal_run_id": "opaque-or-null",
  "as_of": "ISO-8601"
}
```

Les noms sont un contrat logique, à adapter aux conventions du dépôt. La clé de cache doit distinguer recherche, instantané, objectif, scénario, versions des règles, géométrie et modèle. Les préférences de tri n’autorisent pas à mélanger des résultats de versions différentes.

Le Signal possède en plus un manifest immuable, ou des champs équivalents, reliant artefact, prétraitement, calibration, définition de domaine et politique de service. Conserver `scored_at`, `prediction_window_start` et `prediction_window_end`. Le `as_of` de la requête ne rajeunit pas une prédiction ancienne : douze mois depuis son calcul ne signifie pas automatiquement douze mois à partir d’aujourd’hui.

Si une actualisation intervient pendant l’analyse, terminer sur l’instantané figé ou recommencer explicitement. Ne pas afficher des compteurs issus d’un run et des fiches issues d’un autre.

### 2.3 Parcelle, unité foncière et assemblage

La V2 de base travaille à la parcelle, comme l’existant décrit. Elle annonce ce périmètre.

Une unité foncière ou un assemblage est un objet distinct, identifié par la liste de ses parcelles et par les preuves disponibles. Ne pas additionner simplement leurs scores ou leurs capacités individuelles : les limites, les reculs, les accès et les contraintes doivent être recalculés à l’échelle de l’ensemble. Ne pas fusionner des terrains sur une simple ressemblance de nom de propriétaire.

Une petite parcelle peut rester utile dans un assemblage. Une limite de surface servant à une recherche de logement autonome n’est pas une absence générale d’intérêt foncier.

## 3. Trois familles de sorties séparées

### 3.1 Faits

Surface, géométrie, zonage par portion, usages connus, bâti estimé, contraintes, topographie, desserte observée, transactions et permis. Chaque donnée critique porte source, date de validité ou d’observation, date d’ingestion, version et statut de disponibilité.

### 3.2 Résultat de scénario

Le scénario possède son propre statut, ses causes, ses quantités, ses hypothèses et ses vérifications restantes. Une hauteur manquante ne rend pas automatiquement toutes les autres analyses impossibles.

### 3.3 Signal

Le Signal conserve sa cible, son échéance, son domaine et sa chaîne statistique. Il ne se multiplie pas par la capacité foncière. Les deux familles peuvent partager des variables : ne pas les présenter comme statistiquement indépendantes.

## 4. Données et unités : contrat minimal

| Champ logique | Unité / état | Usage |
|---|---|---|
| `parcel_area_m2` | m² de terrain | Description et tri de surface |
| `parcel_geometry` | géométrie et SRID explicites | Intersection, assiette, reculs |
| `geometry_status` | valide / suspecte / non disponible | Vérifier la fiabilité des calculs géométriques |
| `zone_parts` | zones et portions géométriques | Appliquer les règles à la bonne portion |
| `housing_eligibility` | compatible dans le périmètre outillé / incompatibilité établie / inconnue | Scénarios de logement seulement |
| `eligibility_proof` | règle, source, version, portion et date | Justifier une incompatibilité |
| `availability_horizon` | actuel / différé / inconnu | Séparer capacité et échéance |
| `capacity_rebuild_sdp_m2` | nombre ≥ 0 ou null | Capacité théorique du scénario de reconstruction |
| `existing_sdp_m2` | nombre ≥ 0 ou null | SDP existante, sur une base compatible |
| `additional_layout_sdp_m2` | nombre ≥ 0 ou null + méthode | Capacité additionnelle avec insertion contrôlée, si le moteur la fournit |
| `capacity_bounds`, `existing_bounds` | bornes documentées ou absentes | Enveloppes d’hypothèses ; jamais inventées |
| `slope`, `road_observation`, `shape`, `built_presence` | valeur + source + disponibilité | Points de vigilance distincts |
| `signal` | statut, probabilité servie, cible et versions | Prospection uniquement dans le domaine validé |

**NULL ≠ 0.** Un nombre non fini, une unité incohérente, un taux impossible ou un conflit critique produit un état à vérifier. Une valeur absente ne devient pas la meilleure hypothèse.

Ne pas confondre :

- surface de parcelle ;
- emprise bâtie / surface de parcelle ;
- emprise bâtie / plafond d’emprise autorisé ;
- surface de plancher.

Un taux de 158 % du plafond autorisé peut être cohérent. Il ne signifie pas forcément que le bâti couvre physiquement 158 % du terrain. Le dénominateur doit être explicite partout.

L’approximation « emprise × niveaux » est une méthode d’estimation, pas une preuve de SDP réglementaire exacte. Capacité et existant doivent utiliser des définitions compatibles avant soustraction.

## 5. Statuts de scénario et ordre des décisions

Les statuts sont exclusifs **pour un scénario et un instantané donnés**.

| Code | Libellé client | Sens |
|---|---|---|
| `ESTIMATED` | Capacité théorique estimée | Une quantité positive est calculable dans le périmètre outillé |
| `PRESTUDY` | Préétude à mener | Repérage d’une division/aménagement pour logement ; aucun lot calculé |
| `TO_VERIFY` | Analyse à compléter | Donnée critique manquante, incohérence, anomalie ou hypothèses déterminantes non résolues |
| `DEFERRED` | À différer | Caractère différé établi, notamment AU fermée identifiée ; distinct d’un horizon simplement inconnu |
| `NO_MARGIN` | Aucun ajout identifié / aucune capacité identifiée | Résultat nul du scénario selon ses hypothèses, sans verdict immobilier général |
| `OUTSIDE_OBJECTIVE` | Hors de ce projet | Incompatibilité du projet concerné établie et sourcée |

### 5.1 Priorité des règles

```text
1. Vérifier identifiant, unités et qualité géométrique nécessaire au scénario.
   Une anomalie critique non résolue → TO_VERIFY.
2. Chercher une preuve suffisante d’incompatibilité pour CE projet.
   Si preuve valide et correctement localisée → OUTSIDE_OBJECTIVE.
   Une simple famille de zone ou une absence de donnée n’est pas cette preuve.
   Si l’éligibilité du programme reste inconnue → TO_VERIFY.
3. Vérifier l’horizon.
   Si caractère différé établi → DEFERRED.
   Si l’horizon nécessaire est inconnu → TO_VERIFY.
4. Vérifier les entrées critiques propres au scénario.
   Si une manque ou se contredit → TO_VERIFY.
5. Calculer les quantités et éventuelles enveloppes documentées.
6. En conservation, si R_min = 0 < R_max → TO_VERIFY,
   en conservant les quantités provisoires et l’enveloppe dans le détail.
   En reconstruction, un intervalle de gain net contenant zéro ne rend pas
   à lui seul inconnue une capacité totale positive et calculable.
7. Conservation avec capacité additionnelle nulle → NO_MARGIN.
   Reconstruction avec capacité totale nulle → NO_MARGIN.
8. Division pour logement en simple repérage → PRESTUDY.
9. Sinon → ESTIMATED.
```

Une preuve d’interdiction indépendante d’une donnée manquante non pertinente peut suffire à conclure. En revanche, une intersection sur une géométrie douteuse ne devient pas une preuve certaine. L’adaptateur doit qualifier la suffisance de la preuve.

Une erreur technique reste une ligne `TO_VERIFY`, avec `processing_status=ERROR` et sa cause. Elle ne disparaît pas des comptes. Des erreurs massives ou une rupture de contrat empêchent la publication de l’analyse concernée ; l’ancienne version reste utilisable.

## 6. Mode Prospection vente

### 6.1 Question

« Parmi les biens de ma sélection pour lesquels le modèle est applicable, lesquels présentent le signal estimé de mutation le plus élevé à douze mois ? »

Ce mode ne promet ni prise de mandat, ni volonté déclarée de vendre, ni vente certaine. Il n’implique pas que tous les types de ventes immobilières soient couverts.

### 6.2 Référence historique à vérifier

Le rapport utilisateur décrit un modèle `q_v15`, entraîné jusqu’à 2023, calibré sur 2024, rejoué sur 2025, puis re-scoring servi sous un run `q_v20`. Claude doit lire les versions effectives dans le dépôt et l’artefact ; le rapport ne prouve pas que ces versions sont toujours actives.

La cible annoncée est `L2-F`. Avant toute généralisation commerciale, extraire du code son prédicat exact, ses exclusions, son unité d’observation et le traitement des ventes à plusieurs parcelles. Ne pas inventer une définition détaillée de L2-F à partir du sigle.

### 6.3 Domaine et états

| État | Conséquence |
|---|---|
| `AVAILABLE` | Probabilité valide dans un domaine vérifié ; classement autorisé selon la politique servie |
| `TO_VERIFY` | Donnée/artefact/version incohérents ; pas de probabilité classante |
| `NOT_AVAILABLE` | Prédiction non calculée ou intrants nécessaires indisponibles ; pas de zéro imputé |
| `OUT_OF_SCOPE` | Type de bien ou population non couverts par le domaine validé ; bien toujours consultable |

Retirer une exclusion de logement ne rend pas automatiquement le modèle applicable à un nouveau type de bien. Si les anciennes exclusions déterminaient aussi l’univers d’entraînement, de calibration ou d’application, il faut une validation spécifique avant de servir ces nouvelles probabilités.

Une probabilité classante doit être finie et appartenir à `[0,1]`. Une valeur hors bornes, NaN, infinie ou une incohérence de manifest donne `TO_VERIFY`. Ne pas écrêter silencieusement une valeur pour la rendre valide. Une absence simple donne `NOT_AVAILABLE`, pas une probabilité zéro.

Un résiduel nul, un bâti dense ou un zonage N ne deviennent pas automatiquement « ne se vendra pas ». Si le modèle ne couvre pas ce cas, afficher **Signal non évalué**, avec sa raison.

### 6.4 Chaîne statistique conservée

Préserver ensemble : variables et définitions, millésimes, traitements des absences, transformations WoE, ordre des features, coefficients, intercept, calibration, politiques de service et seuils.

La V2 n’entraîne pas un nouveau modèle et ne change pas les poids du modèle existant. Le tri utilise la **probabilité effectivement servie et validée après la chaîne de transformations applicable**, jamais un mélange improvisé de `p_raw`, logits, score normalisé et probabilité calibrée. Si la signification de ces colonnes est ambiguë, la résoudre avant le branchement.

Les seuils rapportés sont Fort ≥ 0,20 ; Moyen ≥ 0,10 et < 0,20 ; Faible < 0,10. Ce dossier ne réactive pas de niveau actuellement désactivé. Le rapport emploie « Fort » et l’ancien tier « Priorité » et présente des résultats historiques non rapprochés : vérifier exactement leurs cohortes, définitions et correspondances actuelles. Conserver le verrou `PRIORITE_SERVIE=false` tant que son évolution ne fait pas l’objet d’une validation séparée.

La maquette autorise des niveaux fictifs pour expliquer le fonctionnement. Ce n’est pas une instruction d’activation de ces niveaux en production.

### 6.5 Tri

```text
1. Prédictions AVAILABLE autorisées par la politique de service,
   triées par probabilité servie décroissante.
2. Prédictions TO_VERIFY / NOT_AVAILABLE / OUT_OF_SCOPE,
   dans des groupes explicitement nommés, sans probabilité artificielle.
3. Égalité exacte : identifiant normalisé croissant.
```

Le potentiel logement ne sert ni de multiplicateur ni de filtre caché ni de départage caché. Un filtre de potentiel explicitement demandé par le client reste possible et doit être affiché comme tel.

Les probabilités internes peuvent ordonner des biens tous étiquetés Faible. Il ne faut pas les considérer comme tous équivalents ni rebaptiser Faible en « Sans intérêt ».

### 6.6 Explications

Utiliser les contributions réellement calculées par le modèle ou une méthode d’explication validée. Ne pas générer après coup un récit de vente à partir d’un LLM. Une contribution est une association du modèle, pas une cause démontrée ni une intention personnelle.

Ne pas utiliser « raisonnement indépendant du potentiel » : plusieurs entrées foncières sont communes aux deux familles.

## 7. Mode Potentiel foncier — programme logement en V2 initiale

Le moteur décrit dans le rapport est orienté logement. Cette première V2 le reconnaît explicitement. Elle n’annonce pas un moteur validé pour bureaux, commerces, agriculture, photovoltaïque, location ou rentabilité de l’existant.

Tous les métiers gardent accès aux faits et aux recherches. Un autre programme pourra être ajouté avec ses règles et ses données propres, sans réutiliser aveuglément les exclusions logement.

### 7.1 Conservation du bâti

Soient `C` la capacité totale théorique de référence et `E` la SDP existante estimée, définies sur une même assiette et une base compatible.

```text
R_budget = max(0, C − E)
```

`R_budget` est une **marge théorique par différence**. Elle ne prouve pas qu’un bâtiment supplémentaire puisse s’insérer avec les bâtiments conservés.

- Si le moteur calcule une insertion avec conservation, conserver séparément `R_layout`, sa méthode et ses preuves.
- Ne pas annoncer `R_budget` comme une capacité spatiale vérifiée lorsque `R_layout` est absent.
- Pour la première V2, le tri de référence porte sur `R_budget`, à condition que ses deux entrées compatibles soient disponibles ; l’audit doit le vérifier. Sinon la ligne reste à vérifier. Le libellé du tri indique la méthode. Une migration vers `R_layout` exigera un contrat de comparabilité.
- Un résultat zéro produit « Aucun ajout identifié selon les hypothèses », pas « rien à construire de façon certaine ».
- **Aucun facteur de démolition complète dans ce scénario.**

Le bâti peut compliquer l’insertion. Cette difficulté est une information spécifique ; elle ne justifie pas de soustraire `E`, puis d’appliquer mécaniquement un malus de démolition au résultat.

### 7.2 Reconstruction

```text
C_rebuild = capacité totale théorique du nouveau projet
D_net = C_rebuild − E
```

Afficher les trois quantités : `C_rebuild`, `E`, `D_net`. La différence nette est **signée**. Une perte de 500 m² doit rester −500 m² et ne pas devenir zéro.

- Calculer le scénario pour toutes les parcelles pertinentes, pas uniquement les parcelles saturées.
- Si le terrain est déjà nu, le signaler : aucune démolition n’est nécessaire.
- Appliquer les règles propres à ce nouveau projet ; ne pas supposer que l’ensemble des droits historiques de l’existant sont réutilisables.
- Démolition, occupation, protection du bâti, pollution, relogement et coûts restent des vérifications selon les données disponibles.
- Un gain net nul ou négatif n’interdit pas un projet de remplacement. Il ne reçoit pas automatiquement une bonne ou mauvaise note économique.
- Si l’utilisateur trie par capacité totale, `C_rebuild` commande l’ordre au sein des groupes de statut. S’il trie explicitement par gain net, `D_net` commande l’ordre au sein de ces mêmes groupes, y compris lorsqu’il est négatif. L’intitulé indique « au sein des groupes de statut » ; il ne promet pas un tri numérique global traversant les groupes.

La V2 n’utilise pas `C_rebuild × 0,65` pour certifier une opportunité. Un coefficient sans estimation des coûts et des recettes ne constitue pas un bilan d’opération.

### 7.3 Division / aménagement pour logement : repérage

Cette vue est une **préétude documentaire**, pas une simulation de lotissement.

Entrées minimales : surface et géométrie exploitables, objectif logement, zonage et contraintes identifiés à un niveau suffisant pour ce repérage. La hauteur manquante qui empêche une SDP ne bloque pas automatiquement ce repérage.

Afficher : surface, parties admissibles connues, bâti, points de desserte observés et contraintes. Ne calculer ni nombre de lots, ni divisibilité, ni coût de viabilisation sans moteur et données dédiés.

Statut de base : `PRESTUDY`. Une anomalie géométrique ou une règle indispensable inconnue donne `TO_VERIFY`. Un caractère différé établi donne `DEFERRED`.

Une incompatibilité de logement donne `OUTSIDE_OBJECTIVE` **pour une opération de division destinée au logement**. Elle ne signifie pas qu’une division foncière quelconque est juridiquement impossible.

Le tri par défaut est la surface du terrain décroissante, avec l’intitulé explicite « Surface du terrain — repérage, pas divisibilité ».

## 8. Incertitude et fraîcheur

### 8.1 Absences critiques et non critiques

La liste des entrées critiques est propre au scénario et versionnée. La recette de traitement des absences du Signal reste celle de son artefact ; ne pas lui appliquer celle du moteur foncier.

Une pente inconnue :

- ne reçoit pas un facteur 1 qui transformerait implicitement l’inconnue en terrain plat ;
- ne reçoit pas non plus une pente défavorable inventée ;
- figure comme inconnue dans les points à vérifier ;
- n’empêche pas nécessairement l’estimation arithmétique de SDP si elle n’est pas une entrée critique de cette méthode.

La capacité demeure théorique ; la qualité et les limites restent visibles. Aucune étiquette « Excellente » ne récompense une parcelle moins documentée.

### 8.2 Enveloppes disponibles

Uniquement si de véritables bornes compatibles sont disponibles :

```text
R_min = max(0, C_min − E_max)
R_max = max(0, C_max − E_min)
D_min = C_min − E_max
D_max = C_max − E_min
```

Valider les bornes, leurs sources et leur cohérence avec les estimations centrales. Un seul champ borné ne permet pas d’inventer les bornes de l’autre.

Ces enveloppes ne sont pas des intervalles de confiance statistiques, sauf méthode démontrée. Sans bornes, afficher « Estimation ponctuelle ; incertitude non quantifiée ». Ne pas fabriquer ±10 %, `[x;x]` ou une fiabilité de 95 %.

Quand `R_min=0<R_max`, l’absence d’ajout n’est pas établie : état à vérifier, estimation et enveloppe conservées.

### 8.3 Temps

Tracer les dates par famille de données. Deux photos différentes ne doivent pas être présentées comme un instantané parfaitement cohérent. Si le décalage compromet le calcul, retenir un état à vérifier ; sinon le signaler avec les dates réelles. Les seuils de péremption sont définis source par source à partir des contrats de mise à jour, pas inventés globalement dans cette refonte.

## 9. AU fermée, contraintes partielles et géométrie

### 9.1 AU fermée/différée

Remplacer le facteur opaque ×0,5 par un groupe **À différer**. L’utilisateur voit séparément la disponibilité actuelle et une éventuelle capacité conditionnelle.

Ne pas inventer une date d’ouverture. Une capacité conditionnelle doit indiquer les règles ou hypothèses utilisées ; elle n’est pas une capacité actuellement mobilisable et n’entre pas dans le classement courant de la même façon.

Si cette quantité future facultative est absente ou invalide, ne pas la servir ; conserver le caractère différé lorsqu’il est établi, avec une cause et un avertissement pour la quantité. Les tris de résiduel ou de gain net ne la remplacent pas par cette capacité future totale : leur valeur de tri reste `null` (absente), jamais zéro, puis départage par identifiant. Un tri explicite de surface reste possible.

### 9.2 Contraintes partielles

Si le moteur sait traiter l’assiette restante : découper réellement les portions, appliquer leurs règles et conserver les preuves. Réunir les surfaces de contraintes qui se chevauchent avant soustraction. Ne pas soustraire deux fois la même portion ni appliquer ensuite un malus de surface pour la même raison.

Afficher les différents zonages. Une fiche indiquant uniquement « zone N » et 7 000 m² de SDP doit permettre de comprendre immédiatement quelle partie et quelle règle produisent cette capacité. Le zonage majoritaire n’est pas nécessairement celui de la portion productive.

Les seuils historiques de recouvrement doivent être audités avec leur justification. Cette proposition ne remplace pas automatiquement toutes les règles locales par un nouveau seuil de 99 %, 80 % ou 50 %.

### 9.3 Revue de `terrain_exigu`

Après vérification de la livraison effective de RESIDUEL-1, remesurer les cas identifiés dans le rapport. Le lien causal avec ce correctif reste à prouver.

Enregistrer, avec unités et SRID : géométrie initiale, parties admissibles, union des contraintes, limites qualifiées, retraits appliqués, surfaces et géométries intermédiaires, assiette finale, versions et cause terminale.

Contrôler notamment : géométries invalides, multipolygones, unités, doubles retraits, reculs appliqués aux bonnes limites, limites internes d’un ensemble, parties de zonage ou de risque traitées à tort comme limites séparatives, et chevauchement des masques.

Une grande surface n’est pas une preuve d’exploitabilité. Une petite surface n’est pas une preuve d’erreur ou d’impossibilité. **Ne pas créer la règle « plus de 500 m² → NC »** comme solution générale.

Si le calcul est douteux : `TO_VERIFY`, quelle que soit la surface. Si l’assiette nulle est réellement démontrée dans le scénario : cause précise, par exemple « Aucune assiette obtenue après application des retraits identifiés », avec les preuves accessibles. Ne pas déduire « terrain trop étroit » de toute géométrie vide.

Les 139 cas de causes vides ne deviennent pas automatiquement « saturation en hauteur ». Vérifier les valeurs qui permettent réellement d’établir cette cause.

## 10. Classement déterministe

### 10.1 Règle commune

Le classement est un ordre de consultation, pas une estimation de rentabilité. Aucun score caché fondé sur la profession, aucun quota de meilleurs terrains et aucun reclassement par percentile ne sont introduits.

Un tri de quantité s’applique **à l’intérieur de groupes de statut et d’horizon comparables**.

Ordre des groupes fonciers en vue Tous :

```text
ESTIMATED ou PRESTUDY
TO_VERIFY
DEFERRED
NO_MARGIN
OUTSIDE_OBJECTIVE
```

Les inconnues et les différées sont des files de travail distinctes, pas des estimations de moindre valeur. Les boutons de statut permettent de les consulter directement. Cette hiérarchie est affichée par les groupes, pas dissimulée dans une note.

### 10.2 Tris disponibles

| Contexte | Tri initial explicite | Autres tris possibles |
|---|---|---|
| Prospection vente | Probabilité servie décroissante, domaine et politique vérifiés | Surface ; identifiant, si le client le choisit |
| Conservation | SDP supplémentaire théorique décroissante (`R_budget`) | Surface ; identifiant |
| Reconstruction | Capacité totale théorique décroissante (`C_rebuild`) | Gain net signé décroissant ; surface ; identifiant |
| Division / aménagement logement | Surface décroissante | Identifiant |
| Liste simple | Ordre existant explicite ou identifiant normalisé | Tris descriptifs existants |

Les valeurs nulles sont classées après les valeurs connues dans leur groupe, jamais converties en zéro. Les égalités exactes sont départagées par l’identifiant normalisé croissant, de façon stable entre pages et exports.

Ne pas arrondir avant de trier. Une petite valeur strictement positive ne doit pas être affichée « 0 m² » par simple arrondi ; utiliser une précision adaptée ou « <1 m² ».

Un « chevauchement d’intervalles = égalité » n’est pas un comparateur de tri sûr : il peut être non transitif. Les enveloppes restent des informations ; le tri initial utilise l’estimation centrale documentée et le statut.

### 10.3 Difficultés physiques

La pente, la forme, la desserte et le bâti sont des points de vigilance sourcés. Ils restent visibles sur la fiche et dans les filtres qui les proposent déjà. Ils ne sont pas multipliés dans une nouvelle note non calibrée.

Le libellé du tri doit empêcher l’erreur « premier = meilleure opération ». Exemple : une parcelle de 2 400 m² supplémentaires et en forte pente peut être première dans le tri de volume ; sa pente est affichée dès la carte de résultat. L’utilisateur peut adapter ses filtres. Une future priorité multicritère nécessitera des arbitrages métier et une validation propres.

## 11. Explications et interface

### 11.1 Contrat d’une fiche de résultat

Afficher seulement les informations qui servent la vue :

1. identifiant, type de bien, commune, surface et zonages utiles ;
2. résultat principal lié à l’objectif ;
3. une cause ou un point de vigilance déterminant ;
4. accès au détail des quantités, sources, dates et vérifications.

En prospection, le Signal domine visuellement ; la SDP est secondaire. En potentiel foncier, la capacité du scénario domine ; le Signal est secondaire.

### 11.2 Libellés à remplacer

| À éviter | À employer selon le contexte |
|---|---|
| Va se vendre | Prospection vente / Signal de mutation à 12 mois |
| Excellente, sans précision | Capacité théorique estimée + grandeur et scénario |
| Non retenue, comme verdict général | Aucun ajout identifié / À vérifier / Hors de ce projet, avec cause |
| 154 constructibles, sur la seule base du score | 154 résultats pour cette analyse, avec répartition des statuts |
| Sans signal, pour tout p<0,10 | Signal faible |
| Divisible / X lots, sans simulation | Préétude à mener / Nombre de lots non calculé |
| Aucune contrainte | Aucune contrainte détectée dans le périmètre vérifié |

### 11.3 États et transitions

- Les critères et l’univers restent identiques en revenant de l’analyse à la liste.
- Changer d’objectif change résultat principal, tri, légende et explications ; cela ne change pas les critères en secret.
- Changer de scénario réinitialise un filtre de statut devenu incompatible.
- Si une parcelle sélectionnée disparaît des résultats visibles, sélectionner la première parcelle de la page courante ou vider clairement le détail.
- La fiche visible, le marqueur actif, les compteurs, la pagination et l’export doivent désigner le même univers.
- En cas de zéro résultat, garder les critères et proposer leur modification. Ne pas élargir automatiquement la recherche.
- En cas d’analyse partiellement échouée, conserver les lignes et afficher le bilan complet. Ne pas montrer uniquement les succès comme si tous avaient été traités.
- Ne pas attribuer aux non évaluées la couleur des mauvaises opportunités. Donner une légende de statut propre à la vue.

La maquette du dossier ne réimplémente qu’un petit sous-ensemble de filtres pour démontrer les transitions. Le produit conserve tous ses filtres existants.

## 12. Protection du modèle de mutation

La SDP résiduelle est une feature du modèle historique. **Ne jamais remplacer son contenu par une capacité de reconstruction en gardant le même nom.**

Créer de nouvelles sorties de scénario, avec de nouveaux champs et versions. Conserver la définition historique attendue par le modèle tant que cet artefact est servi.

Une correction géométrique peut modifier les features même si leurs noms sont inchangés. Comparer alors les distributions, les probabilités, les niveaux et les résultats de validation avant service. « Modèle gelé » n’empêche pas une dérive induite par les données ou leur définition.

La compatibilité modèle/features/prétraitement/calibration est un contrat versionné. En cas d’incompatibilité, retenir un Signal non évalué ou maintenir l’ancien chemin cohérent, plutôt que servir une probabilité non validée.

## 13. Validation requise

### 13.1 Audit du dépôt avant implémentation

Vérifier au minimum les fichiers ou équivalents cités dans le rapport :

- `src/labuse/scoring/score_labuse.py` ;
- `src/labuse/scoring/score_labuse_combine.py` ;
- `src/labuse/faisabilite/residuel.py` et `engine.py` ;
- `src/labuse/scoring/signal_mutation.py` et `p_model/` ;
- `config/score_labuse.yaml`, `scoring_client.yaml`, `cascade_v2.yaml`, `cascade_rules.yaml` ;
- `frontend/src/lib/status.ts` ;
- pointeur du run servi, artefacts, manifests et tests ;
- chemins des requêtes, compteurs, pagination, carte, détail et export.

Les noms sont issus du rapport fourni. S’ils diffèrent du dépôt, documenter le chemin réel. Ne pas créer des fichiers en doublon pour faire correspondre artificiellement la structure.

### 13.2 Tests de contrat et contre-exemples

La recette doit couvrir au minimum :

1. mêmes identifiants en liste et analyse ;
2. tous les statuts inclus dans les comptes et dans Tous ;
3. parcelle bâtie sans marge additionnelle restant visible en prospection ;
4. borne exacte des niveaux du Signal et politique de service respectée ;
5. probabilité absente distincte de zéro et de Faible ;
6. domaine non validé sans probabilité extrapolée ;
7. aucune modification des variables historiques du modèle ;
8. conservation : calcul arithmétique et limite d’insertion expliquée ;
9. reconstruction : capacité totale, existant et gain net signés cohérents ;
10. `C=2 100, E=2 099` puis `E=2 100` : même scénario de reconstruction, aucune bascule de formule ;
11. `C=2 500, E=3 000` : gain net −500 visible ;
12. capacité absente jamais assimilée à zéro ;
13. inconnue non critique conservée et visible sans bonus ni malus inventé ;
14. hauteur manquante bloquant une SDP sans bloquer automatiquement le repérage division ;
15. bornes documentées traversant zéro ; bornes invalides ; bornes absentes ;
16. grande et petite géométrie suspectes toutes deux à vérifier ;
17. contrainte partielle, masques superposés, assiette restante et reculs sans double application ;
18. AU fermée dans un groupe différé, sans ×0,5 ni date inventée ;
19. terrain nu dans le scénario reconstruction, sans démolition fictive ;
20. division sans nombre de lots ni certification ;
21. volumes >2 000 m² toujours départageables dans un tri de volume ;
22. tris stables, valeurs nulles explicites et export identique ;
23. sélection de fiche cohérente après filtre, tri, pagination et changement d’objectif ;
24. zéro résultat, traitement partiel, erreur technique, changement d’instantané ;
25. zonage mixte : la portion qui produit la capacité est identifiable ;
26. données et versions désalignées signalées ou résultat non servi.

Les tests unitaires de la référence du dossier vérifient le contrat arithmétique et les statuts. Ils ne valident ni SIG ni modèle ML réel.

### 13.3 Validation du potentiel

Constituer un panel documenté couvrant les 24 communes à l’échelle de la validation finale, et des cas de terrain nu, bâti conservé, bâti saturé, existant supérieur aux règles actuelles, pente, parcelle découpée, contraintes partielles, AU, petites parcelles et assemblages.

Faire revoir les mêmes intentions de projet par agents/apporteurs, lotisseurs/aménageurs et promoteurs. Mesurer d’abord les capacités plausibles, les causes erronées et les faux rejets. Les ventes ne calibrent pas directement la faisabilité d’un projet.

Une revue sur un petit échantillon est une étape de recette, pas une preuve statistique pour toute l’île. Rapporter les effectifs, les cas non jugeables et les désaccords ; ne pas inventer une précision commerciale globale.

### 13.4 Validation du Signal

Rejouer à information réellement disponible à la date historique : définition de cible, publication des données, encodages et calibration sans utilisation de l’année test. Documenter aussi la date de choix de la recette.

Rapporter AUC, calibration par groupes (moyenne prédite contre fréquence observée), Brier contre un modèle constant, précision@100/@500/@1 000 et lift. Rapporter les résultats sur l’univers réellement prospectable, en plus de toute l’île.

Calculer le taux de base et le lift avec le dénominateur propre à chaque univers historique évalué. L’éligibilité doit être reconstruite avec les informations disponibles à cette date ; ne pas appliquer rétroactivement le masque actuel sans justification. Publier les effectifs et événements de chaque univers.

Traiter les parcelles d’une même mutation comme événements potentiellement dépendants. Ne pas compter 39 parcelles vendues comme 39 opérations indépendantes sans contrôle.

Le rapport présente 2/118 puis 1/111 comme des reformulations, et ailleurs 39/100. Identifier les cohortes, dates, modèles, unités et politiques d’affichage : ces chiffres ne sont pas des paraphrases interchangeables.

Avec les chiffres du rapport, le Brier constant vaut environ 0,01487, proche de 0,0148. Le Brier isolé ne suffit donc pas à démontrer une bonne calibration. Les niveaux Fort et Moyen captent une petite part des ventes ; ils sont utiles pour une prospection ciblée, pas pour annoncer une couverture de toutes les ventes.

Figer les scores, données, versions et dates de service pour la validation future à douze mois. L’absence immédiate de résultat forward sur un run récent n’est pas une défaillance du modèle.

## 14. Migration et retour arrière

1. **Cartographier l’existant** : versions actives, filtres réels, univers, cause des exclusions, dépendances de RESIDUEL-1 et état des verrous.
2. **Geler une référence** : instantané, résultats servis et cas d’audit. Préserver les données et artefacts nécessaires au retour arrière.
3. **Ajouter les sorties V2 séparées** : contrats, causes, scénarios et clés de cache. Ne pas écraser les features historiques du Signal.
4. **Calculer en parallèle sans changer le service** : comparer identifiants, capacités, catégories, compteurs et probabilités sur le même instantané.
5. **Revoir les divergences** : corriger les incohérences, produire les preuves géométriques et les explications métier.
6. **Brancher l’interface derrière un indicateur de version** : mêmes filtres et deux sorties, pas de nouvelle navigation.
7. **Recette de bout en bout** : recherche → liste/analyse → détail/carte/export ; scénarios, erreurs et petits écrans.
8. **Activation selon le processus de déploiement du projet** : une activation UI ne réactive pas Priorité, n’élargit pas un domaine ML et ne change pas les règles réglementaires de sa propre initiative.
9. **Retour arrière** : rétablir ensemble interface, chemin de calcul et manifest compatibles. Une seule bascule de version ne doit pas laisser une moitié V1 et une moitié V2.

Ne pas supposer qu’ALGO-FIX-1, RESIDUEL-1 ou DEPLOY-GROUPE-3 sont encore les mêmes tâches ou déjà livrées. Vérifier leurs états et dépendances effectifs.

## 15. Ce qui reste hors périmètre

- nouveau modèle général de prise de mandat ou de vente de tous les biens ;
- note de rentabilité, sous-évaluation ou prix d’acquisition sans données adaptées ;
- estimation de l’état intérieur, de l’occupation ou des coûts de démolition à partir du seul bâti ;
- calcul de nombre de lots ou de divisibilité sans simulation dédiée ;
- programme non logement sans règlement et contrat propres ;
- changement de tous les seuils de risques, règles de PLU ou catégories juridiques par simple refonte UX ;
- nouveau classement personnalisant la « vérité » selon la profession.

## 16. Références et niveau de preuve

### Source produit

Le document utilisateur **ALGO-LECTURE-1**, les retours Claude et les captures de cette discussion décrivent l’existant. Ils ne constituent pas une inspection du dépôt, ni une confirmation de ses versions actuelles. La maquette antérieure et ses classements manuels sont remplacés par les règles de ce dossier.

### Sources officielles consultées pendant l’étude

- [PropStream — indicateurs et usages selon les professionnels](https://updates.propstream.com/propstream-intelligence-ai-real-estate-data) : mêmes caractéristiques interprétées selon l’objectif ; pas une formule à recopier pour La Réunion.
- [LightBox Vision](https://www.lightboxre.com/data/lightbox-vision) : recherche cartographique, données et assemblages.
- [KelFoncier](https://www.kelfoncier.com/application/) : recherche multicritère, foncier d’une ou plusieurs parcelles et préfaisabilité.
- [LandInsight — filtres](https://support.land.tech/en/articles/14121953-fact-sheet-site-sourcing-tool-filters-explained) : usages, état, contraintes et paramètres distincts.
- [Esri — limites des analyses multicritères pondérées](https://pro.arcgis.com/en/pro-app/latest/help/analysis/spatial-analyst/suitability-modeler/evaluate-environment-in-suitability-modeler.htm) : contributions, hypothèses, unité de décision et validation terrain.
- [Scikit-learn — calibration](https://scikit-learn.org/stable/modules/calibration.html) : probabilités prédites et fréquences observées ; limites d’une métrique isolée.
- [Cerema — parcelle et unité foncière](https://doc-datafoncier.cerema.fr/doc/guide/ff/le-foncier-non-bati-parcelle-suf-unite-fonciere-tup) : importance de l’unité de travail.
- [Code de l’urbanisme — L151-12](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031211181/) : exemple de dispositions relatives à l’existant en A/N ; ne pas transformer une famille de zone en affirmation universelle sans le règlement applicable.

Les pages des éditeurs décrivent leurs produits. Elles ne publient pas les formules complètes ni une validation indépendante de tous leurs scores. L’architecture de scénarios proposée ici est une recommandation pour LABUSE, pas une copie démontrée d’un algorithme concurrent.

## 17. Résultat attendu de Claude

Un compte rendu vérifiable : correspondance entre cette spécification et le dépôt, divergences factuelles constatées, contrats ajoutés, définition exacte du domaine du Signal, liste des modifications, tests exécutés, comparaison avant/après et risques encore ouverts.

Le dossier ne demande pas « rendre les scores plus beaux ». Il demande de rendre les calculs, les exclusions, le classement et les mots **cohérents avec l’objectif choisi**, sans perdre de biens de la sélection.
