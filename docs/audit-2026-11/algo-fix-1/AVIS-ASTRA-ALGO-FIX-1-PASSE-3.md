# ALGO-FIX-1 — revue de la troisième passe

9 novembre 2026. Lecture seule des trois rapports transmis, du worktree `/Users/openclaw/Desktop/labuse-algofix` au commit `9ce3c9102ae0a826d1ce5993dac3f24e87e08946`, et de la base locale `q_v20`. Aucun changement au code, aucun recalcul de capacité ou de géométrie, aucune écriture dans la base, aucun accès production.

**Décision proposée : direction conservée, activation encore à différer.** Les corrections sont réelles, mais le garde-fou legacy manque une population importante en reconstruction. La mesure du double retrait ne démontre pas encore son impact effectif. Plusieurs contrats API et contrôles numériques restent incomplets.

## 1. Corrections confirmées

- Le mode rapide ne présente plus les reconstructions non chiffrées comme estimées. `COMPUTE_PENDING` distingue correctement calcul en attente et donnée douteuse.
- Les effectifs utilisent maintenant la sélection IDU ∩ commune avant pagination. Des effectifs existent aussi en prospection.
- Les probabilités invalides du Signal persisté sont refusées : hors [0,1], NaN et infinis ne peuvent plus être disponibles et classés en tête.
- Lorsqu’un calcul live aboutit, sa cause, sa source d’assiette et ses quantités priment sur l’ancien cache.
- La géométrie invalide est contrôlée quelle que soit la cause. Multipolygone et compacité sont devenus des indices, sans être présentés comme des preuves d’erreur.
- L’AU explicitement inconnue n’est plus assimilée à une AU fermée.
- EH0043 est effectivement `TO_VERIFY / HORIZON_INCONNU`, avec bande et score fermes absents ; C 44 123, E 6 et gain +44 117 m² restent consultables.
- La décomposition du retrait bâti est désormais fournie : **75 523 promotions à entrées constantes, aucune baisse sur l’invariant contrôlé**. Cette hausse ne justifie pas de rétablir artificiellement le coefficient.

Les comptes insulaires du nouvel `AVANT-APRES.md` correspondent à la base locale :

| Statut | Conservation | Reconstruction |
|---|---:|---:|
| Capacité estimée | 151 451 | 4 342 |
| Calcul à compléter | 0 | 212 024 |
| À vérifier | 72 046 | 72 051 |
| À différer | 320 | 320 |
| Aucun ajout | 64 920 | 0 |
| Hors projet | 144 492 | 144 492 |
| Total | 433 229 | 433 229 |

Les 16,6 % « À vérifier » en conservation ne constituent toujours pas un taux d’erreur ni un objectif à atteindre. Causes principales : assiette douteuse 65 341 ; éligibilité 3 788 ; géométrie 1 586 ; sensibilité 790 ; horizon 510 ; hauteur 31.

## 2. [P1] Le garde-fou legacy manque les reconstructions saturées

**1 780 des 4 342 reconstructions encore estimées, soit 41,0 %, sont calculées sur une assiette legacy non qualifiée avec R = 0 et C > 0.**

La condition de l’[adaptateur, ligne 262](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:262) déclenche le doute uniquement si le résiduel conservation R est positif. Or un projet de reconstruction peut avoir une capacité positive alors que l’existant atteint ou dépasse cette capacité.

Exemples réels enrichis à Entre-Deux, tous `ESTIMATED`, `provenance=live`, `assiette_source=residuel_legacy` :

| IDU | C | E | Gain signé | R |
|---|---:|---:|---:|---:|
| 97403000AM0314 | 142 | 169 | −27 | 0 |
| 97403000AM0473 | 109 | 357 | −248 | 0 |
| 97403000AM0561 | 148 | 289 | −141 | 0 |

Un gain négatif reste un résultat admissible du scénario. Ici, le problème est la qualification de l’assiette. La règle doit porter sur **la capacité utilisée par chaque scénario : R en conservation, C en reconstruction**. Le statut reconstruction ne doit pas hériter d’un feu vert obtenu parce que R vaut zéro.

Ne pas reclasser automatiquement tous les anciens zéros : le contrôle doit rester propre au scénario et aux données effectivement calculées. Vérifier ensuite qu’aucune reconstruction estimée n’utilise une assiette non qualifiée, quelle que soit sa saturation.

## 3. [P1] Le contrôle AU reste dépendant du chemin d’exécution

Le garde-fou sur la portion AU utilise `zone_parts`. Pourtant le batch rapide appelle l’adaptateur avec `with_zone=enrich`, donc sans ces portions quand `enrich=False` ([persistance, ligne 150](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:150)).

Reproduction pure, capacité R = 500 inchangée, source gabarit, aucune classe AU :

- sans portions de zonage : horizon `now`, capacité estimée ;
- avec portion AUm/AU fournie : horizon `unknown`, à vérifier.

Le cas EH0043 est correctement traité après enrichissement, mais le garde-fou n’est donc pas uniformément appliqué à la population insulaire.

La base contient **230 conservations estimées non enrichies**, sans portion productive enregistrée et sans ligne `parcel_au_statut`, alors que leur cascade comporte une portion AU. Exemples : `97401000AI0330`, `97401000AI0331`, `97401000AI0382` aux Avirons. Cela établit une différence de contrôle ; cela ne prouve pas que ces 230 zones soient fermées ou que leur ouverture soit inconnue.

Il faut également éviter l’autre erreur : une zone peut être documentée ouverte sans avoir de ligne dans un cache qui sert à signaler des exceptions. **L’absence de `parcel_au_statut` ne constitue pas à elle seule une preuve de régime inconnu.** Lire la preuve de régime applicable à la portion qui porte la capacité, et appliquer la même décision dans les chemins rapide et enrichi.

## 4. [P1 sur la conclusion d’audit] DOUBLE-RETRAIT mesure une exposition brute

Le défaut algébrique du moteur est réel : deux ensembles de contraintes retirés séparément peuvent faire compter leur intersection deux fois.

En revanche, le nouveau script ne mesure pas la population effectivement affectée :

1. Il prend **toutes les prescriptions** `plu_gpu_prescription`, sans filtre des sous-types ER/EBC ([script, ligne 47](/Users/openclaw/Desktop/labuse-algofix/scripts/algofix1_double_retrait.py:47)). Le moteur filtre ces sous-types.
2. Il mesure le chevauchement sur la **parcelle entière**, sans reculs et sans restriction à l’assiette U/AU utilisée par le repli ([ligne 53](/Users/openclaw/Desktop/labuse-algofix/scripts/algofix1_double_retrait.py:53)). Un chevauchement situé hors assiette productive ne contribue pas au double retrait de cette assiette.
3. Il ne compare pas les emprises obtenues par l’ancien calcul et par une union correcte ; il ne propage pas leur différence jusqu’à C et R.
4. Il ne démontre aucun passage réel de R = 0 à R > 0 après correction.

Les **131/1 500, 261 m² médians et ≈4 709 parcelles** décrivent donc un chevauchement brut potentiel. Les **30 zéros** sont des cas à examiner ; l’extrapolation **≈1 078 faux zéros potentiels** n’est pas une mesure de faux zéros imputables au défaut.

Le script classe aussi un résiduel NULL dans le groupe « zéro », car le test SQL `R > 0` devient indéterminé puis est traité comme faux dans Python ([ligne 76](/Users/openclaw/Desktop/labuse-algofix/scripts/algofix1_double_retrait.py:76)). L’existence de tels cas dans les 30 n’a pas été établie ici : vérifier leurs valeurs et séparer explicitement R positif, R nul et R absent.

La mention « majorant » dans le rapport ne suffit pas à soutenir les titres « parcelles touchées » et « surface doublement soustraite ». Il faut renommer les résultats en exposition à examiner, ou refaire la mesure sur l’assiette exacte avec les mêmes filtres, unités et sources que le calcul servi.

Mesure d’impact à produire, sans écraser les résultats historiques : mêmes données de départ, emprise selon ancien calcul, emprise avec union globale, C avant/après, E inchangé, R avant/après. Séparer les cas d’augmentation géométrique, de capacité inchangée après plafonds, et de résiduel redevenu positif. Les contraintes hors PPR doivent aussi être incluses si l’objectif annoncé est tout le double retrait.

Le correctif amont peut rester un chantier distinct si les résultats non qualifiés sont effectivement isolés entre-temps. La faille des 1 780 reconstructions doit d’abord être fermée pour que cette protection soit complète.

## 5. [P2] Arrondis, quantités provisoires et échec live

**Le problème d’arrondi n’est pas réglé.** L’amont arrondit C, E et R séparément ; la V2 soustrait ensuite C/E déjà arrondis et ignore le R fourni. Exemple : C brut 384,4 et E brut 184,6 donnent R arrondi 200, mais 384 − 185 = 199. Le barème change de palier.

Le nouveau test n’emploie que des entiers et ne couvre pas ce cas. Fixer une convention commune, propager la précision nécessaire au calcul/scoring et arrondir les valeurs d’affichage après calcul. Sources : [résiduel, ligne 244](/Users/openclaw/Desktop/labuse-algofix/src/labuse/faisabilite/residuel.py:244), [scénario, ligne 558](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2.py:558).

**La bande provisoire utilise encore R en reconstruction.** Dans la [branche provisoire, ligne 438](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2.py:438), reconstruction C = 2 100, E = 2 100, R = 0 et horizon inconnu donnent une bande provisoire « 0 ». La quantité de classement de ce scénario est C ; la bande provisoire doit suivre la même règle que la bande ferme.

Cette branche vérifie seulement la présence de C/E avant soustraction. Reproductions pures : C texte provoque une exception, C infini est exposé dans les quantités, C négatif peut aussi être exposé. Le résultat à vérifier doit conserver uniquement des quantités valides et rester sérialisable.

**Un échec du calcul live retombe silencieusement sur le cache.** `records_for_parcels` capture toute exception et remplace le résultat par `None`, interprété ensuite comme un calcul live non demandé ([adaptateur, ligne 329](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:329)). Distinguer calcul non demandé, calcul réussi, calcul échoué et éventuel repli explicite. Le drapeau `enriched` est actuellement attaché au lot demandé ; il ne prouve pas la réussite du calcul de chaque parcelle. L’échec de lecture des portions ne doit pas supprimer silencieusement le contrôle AU.

## 6. [P2] Le contrat API reste différent entre lecture et enrichissement

- **Prospection :** le chemin persisté conserve le statut foncier dans `parcelles[*].statut`, mais ses compteurs portent sur les états du Signal. Le chemin live renvoie `SIGNAL_AVAILABLE`, etc. Reproduction sans base : même Signal disponible, `NO_MARGIN` en lecture persistée et `SIGNAL_AVAILABLE` en live. Définir les mêmes champs et clés de compteurs pour les deux chemins, avec le statut foncier dans un champ séparé si nécessaire. Sources : [lecture, ligne 243](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:243), [effectifs, ligne 301](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:301).
- **Tris :** `sort=id` reste ignoré par le tri persisté ; `sort=area` reçoit toujours une clé absente. Ces paramètres sont acceptés par l’API. Les implémenter correctement ou refuser explicitement les combinaisons non prises en charge ([ligne 258](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:258)).
- **Signal invalide :** la protection du classement est corrigée ; son état reste `NOT_AVAILABLE` en persisté et `TO_VERIFY` dans le moteur pur. Harmoniser l’explication et les compteurs.
- **Versions :** elles sont stockées, mais `_versions_servies` renvoie une seule ligne avec `LIMIT 1`, sans vérifier l’homogénéité de la sélection. Une sélection cache/live reçoit une provenance globale arbitraire. `analysis_version` provient encore du code courant et la recette du Signal est codée en dur ([ligne 325](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:325)). Restituer les métadonnées correspondant aux lignes ou annoncer explicitement un lot mixte.
- **Référence des entrées :** le label demandé ne fige toujours pas les vues courantes et les données live. La correction C/E/cause est réelle ; l’expression « instantané q_v20 figé » reste plus forte que ce que le chemin garantit. Utiliser les références existantes du manifeste ou nommer honnêtement le mélange : calculs actuels comparés au Signal q_v20.

## 7. Compte rendu : retirer les anciens chiffres

Le nouveau bilan insulaire est cohérent avec la base, mais `COMPTE-RENDU.md` contient toujours les paragraphes d’Entre-Deux des passes précédentes et plusieurs affirmations historiques non retirées.

Entre-Deux actuellement :

| Statut | Conservation | Reconstruction |
|---|---:|---:|
| Estimée | 2 041 | 2 602 |
| Sans ajout | 566 | 0 |
| À vérifier | 582 | 587 |
| Hors projet | 3 152 | 3 152 |
| Total | 6 341 | 6 341 |

Les 2 331/2 335 conservations, 2 881 reconstructions et l’écart expliqué par « quatre parcelles » ne décrivent plus ce batch. Le nouveau gain net d’effectif estimé est +561. Remplacer les anciennes valeurs et conclusions ; un ajout « troisième passe » ne suffit pas à rendre les autres paragraphes cohérents.

## 8. Retour court proposé à Claude

Les corrections P1/P6 et plusieurs éléments P2/P4 sont confirmés. Je conserve les décisions produit et le retrait du coefficient bâti. EH0043 est maintenant correctement retenue à vérifier.

Avant activation, terminer les corrections suivantes :

1. Fermer le garde-fou legacy en reconstruction : **1 780 estimées à assiette non qualifiée échappent encore au test R > 0**.
2. Appliquer la qualification AU de façon uniforme, avec preuve de régime sur la portion pertinente, dans les chemins rapide et enrichi.
3. Requalifier la mesure du double retrait ou démontrer son impact sur l’assiette et les capacités réelles.
4. Corriger précision/arrondis, quantité de la bande provisoire, validation numérique de cette branche et signalement des échecs live.
5. Aligner les contrats API persisté/live, les tris et la restitution des versions ; nettoyer le compte rendu.

Vérification de cette revue : 49 fonctions de tests purs existants exécutées avec création d’engines DB interdite, toutes passantes ; reproductions supplémentaires sans base pour les cas décrits ; agrégats et exemples réels obtenus par lectures de la base locale. Aucune nouvelle mesure SIG du double retrait ni campagne complète de validation terrain. Les tests passants ne couvrent donc pas encore les défauts confirmés ci-dessus.
