# Avis sur ALGO-FIX-1 — 9 novembre 2026

**Conclusion : je conserve la direction produit et les décisions D1–D10, mais je ne recommande pas l’activation en l’état.** La hausse des bandes n’est pas, à elle seule, une dérive. Les problèmes prioritaires concernent la signification de « Capacité estimée », la provenance des calculs et les preuves qui permettent de sortir de « À vérifier ».

Audit en lecture seule de `COMPTE-RENDU.md`, `AVANT-APRES.md`, du worktree `/Users/openclaw/Desktop/labuse-algofix`, et de la base locale correspondant à `q_v20`. Branche `fix/algo-fix-1`, commit `d3cf313b85cce29e405a2eca254ec54a6a423082`, propre au moment de la lecture. Aucun changement au code, aucun accès à la production. Les chiffres ci-dessous sont ceux de cette base locale ; ils ne décrivent pas un déploiement.

Des comportements de fonctions ont aussi été reproduits isolément, sans écriture. Ce travail ne constitue ni une validation terrain d’EH0043, ni une nouvelle exécution de toute la suite de tests.

## 1. Hausse des bandes : effet attendu, attribution encore à isoler

Les effectifs exacts donnent :

| Bande | V1 | V2 conservation | Évolution |
|---|---:|---:|---:|
| Excellente | 6 166 | 10 197 | +65,4 % |
| Bonne | 36 254 | 55 920 | +54,2 % |

La matrice locale explique ces mouvements :

- Les 10 197 A V2 sont 5 462 anciennes A et 4 735 anciennes B. 704 anciennes A passent à vérifier.
- Les 55 920 B V2 sont 29 294 anciennes B et 26 626 anciennes C.
- 40 949 anciennes D deviennent C.
- Cela représente **72 310 promotions entre bandes**, et deux déclassements B → C parmi les résultats encore estimés.
- Aucune ancienne 0, NC ou HC ne devient `ESTIMATED` en conservation dans cet instantané.

Retirer un multiplicateur bâti inférieur ou égal à 1 fait mécaniquement monter ou maintenir le score, à capacité et autres entrées identiques. Le bâti est déjà pris en compte dans `R = max(0, C − E)` ; enlever un second malus bâti est cohérent avec le scénario conservation. La difficulté d’insertion doit toutefois rester explicitement distincte de cette marge arithmétique.

**Je ne rétablirais pas le coefficient pour retrouver artificiellement l’ancienne distribution.** Une bande n’a pas à contenir un quota fixe de parcelles. En revanche, cette hausse ne prouve aucune augmentation du potentiel physique réel et ne valide pas les coefficients physiques restants.

La comparaison actuelle ne mesure pas uniquement l’effet du coefficient : elle mélange aussi des capacités recalculées. Les deux B → C l’illustrent :

| IDU | Ancien R | Nouveau C | Nouveau E | Nouveau R | Bande |
|---|---:|---:|---:|---:|---|
| 97403000AM0514 | 445 | 343 | 89 | 254 | B → C |
| 97403000AO0631 | 636 | 506 | 138 | 368 | B → C |

Ces baisses de 191 et 268 m² ne viennent pas du retrait d’un malus. Il faut produire un avant/après à entrées constantes, puis isoler séparément le retrait du bâti, celui d’AU, les recalculs de capacité et les changements de statut.

Le « top 20 » actuel ne répond pas à cette question : son script exclut précisément les changements entre deux bandes encore estimées ([script, ligne 109](/Users/openclaw/Desktop/labuse-algofix/scripts/algofix1_avant_apres.py:109)).

Invariant de contrôle : à R, pente, forme, accès, configuration et arrondi identiques, retirer seulement le coefficient bâti ne doit jamais diminuer le score ni la bande.

## 2. Legacy : présomption de vérification tant que le calcul servi n’est pas qualifié

**Mon arbitrage opérationnel : une capacité legacy positive sans preuve suffisante de son calcul ne doit pas être présentée comme une capacité estimée validée par la V2.** Elle reste consultable, avec son chiffre provisoire, sous « À vérifier — assiette à confirmer ». Son Signal de vente reste indépendant et visible.

Cela ne signifie pas que toutes les parcelles doivent obligatoirement passer par le moteur gabarit : un repli peut être recevable si l’on prouve qu’il traite correctement les règles applicables à ce cas. En revanche, l’absence de PPR rouge/EBC dans les motifs n’apporte pas cette preuve.

Les intersections exactes sont :

| Legacy avec R > 0 | Effectif |
|---|---:|
| Encore `ESTIMATED` | 32 955 |
| Déjà `TO_VERIFY` | 6 396 |
| Hors projet | 2 816 |
| À différer | 372 |
| **Total** | **42 539** |

Il ne faut donc pas ajouter 42 539 aux 30 438 « À vérifier ». Si aucune des 32 955 capacités encore estimées ne pouvait être qualifiée immédiatement, le total conservatoire serait **63 393, soit 14,63 % de l’île**, à autres décisions inchangées. Ce n’est ni un objectif, ni une estimation du taux d’erreur.

L’enjeu touche la tête du classement : ces 32 955 comprennent **3 292 Excellente** et **12 708 Bonne**, respectivement 32,3 % et 22,7 % de leurs bandes V2.

**Le compte rendu donne une explication trop catégorique du legacy.** Le code actuel retire déjà ER/EBC, puis PPR et d’autres contraintes certaines, même en repli ([db.py, ligne 598](/Users/openclaw/Desktop/labuse-algofix/src/labuse/faisabilite/db.py:598)). Il faut distinguer le cache ancien, sa version de calcul, et le repli calculé aujourd’hui. `residuel_legacy` ne veut pas dire intemporellement « aucune découpe ».

Un défaut amont est néanmoins confirmé par lecture : le repli soustrait séparément `union(ER,EBC)` puis `union(PPR,PEB,DPF,ravine,50 pas)`. Si ces ensembles se recouvrent, leur intersection est soustraite deux fois ([db.py, ligne 629](/Users/openclaw/Desktop/labuse-algofix/src/labuse/faisabilite/db.py:629)). Exemple : assiette 1 000 m², EBC et PPR parfaitement superposés sur 200 m² → 600 m² au lieu de 800. Ce défaut peut **sous-estimer** le potentiel et produire de faux zéros ; le risque n’est donc pas uniquement la surestimation. Le nombre réel de parcelles touchées reste à mesurer.

Action : qualification par version et opérations réellement appliquées, avec union globale des contraintes ou soustractions géométriques successives sur le reliquat. Examiner aussi les **9 087 legacy actuellement `NO_MARGIN`**, sans les reclasser automatiquement : certains zéros peuvent dépendre de ce défaut.

## 3. EH0043 : je ne valide pas le statut sur les preuves présentes

La table locale confirme, pour les deux scénarios, `ESTIMATED`, bande B, score 60 ; C = 44 123 m², E = 6 m², R/gain net = 44 117 m². La portion affichée est AUm, 89 365 m². L’enrichissement est effectivement réalisé sur cette parcelle.

Deux précisions importantes après lecture des caches : **aucune ligne `parcel_au_statut` n’existe pour EH0043**, et l’adaptateur retient alors l’horizon `now` par défaut. Cela ne prouve pas que la zone est fermée ; cela ne démontre pas non plus que ses conditions sont satisfaites. La pente utilisée par le Score vient de `parcel_terrain.pente_moy_deg` : **17,5°, soit environ 31,5 %**. Le motif de cascade affiche pour sa part « pente forte ~91 % ». Ce sont deux métriques à rapprocher : la couche de cascade retient un maximum de `slope_pct` parmi ses intersections, tandis que le Score lit une moyenne issue d’un autre jeu de données. Le champ de stockage nommé `recouvrement_pct` contient ici cette pente de 91 %, extraite du texte ; ce n’est pas une preuve que 91 % de la parcelle serait en forte pente. Ne pas confondre pente, moyenne, maximum et taux de couverture.

**Le nombre 89 365 désigne une portion zonée, pas une assiette nette démontrée constructible.** Dans l’adaptateur, cette surface est calculée par pourcentage de zonage multiplié par surface parcellaire. Le caractère « constructible » est attribué à la famille U/AU ; cela ne prouve ni l’ouverture effective, ni l’application de toutes les contraintes ([adaptateur, ligne 246](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:246)).

Vérification externe : le [GPU officiel](https://www.geoportail-urbanisme.gouv.fr/document/by-id/eee143f619882c020cfb0fbd52e178b7) identifie le document `97411_PLU_20260805` en vigueur. Son [règlement écrit, pages 96–98](https://data.geopf.fr/annexes/gpu/documents/DU_97411/eee143f619882c020cfb0fbd52e178b7/97411_reglement_20260805.pdf) conditionne AUm aux équipements d’infrastructure, aux OAP et au régime d’aménagement applicable. L’article AUm.9 prévoit une emprise de 50 %, calculée selon la superficie de chaque zone lorsque l’unité foncière est multizone. Les conditions locales d’EH0043 ne sont pas établies par cet audit.

Trois preuves sont donc requises :

1. **Régime AUm** : règlement effectivement utilisé, OAP applicable, conditions d’équipement/aménagement et leur traitement dans le résultat. Ne pas assimiler automatiquement AUm à une zone fermée ; ne pas assimiler des règles dimensionnelles connues à une disponibilité actuelle prouvée.
2. **Assiette spatiale** : contour de la portion servie, contraintes retirées une seule fois, retraits, morceaux restants et desserte de ces morceaux. Le code peut effectuer des découpes réelles, mais le texte « PPR découpé/EBC soustrait » est généré à partir du nom du chemin ; ce texte n’est pas à lui seul une trace du calcul ([adaptateur, ligne 219](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:219)).
3. **Topographie pertinente** : origine, méthode, date et emprise des deux métriques de pente, puis pente sur la portion réellement productive. Une statistique sur toute la parcelle, majoritairement N, ne décrit pas nécessairement cette portion. Leur écart ne prouve pas à lui seul une erreur. Une pente élevée ne constitue pas à elle seule une preuve d’inconstructibilité ; elle ne valide pas non plus une capacité opérationnelle.

Les 64 % de PPR rouge sur toute la parcelle ne permettent pas de déduire la part rouge dans AUm. Il faut intersecter les géométries ; multiplier simplement la portion AUm par 36 % serait également faux.

**Décision proposée avec les preuves présentes : `TO_VERIFY`, capacité provisoire consultable, sans bande ferme.** `DEFERRED` seulement si le caractère différé est établi. Retour possible à `ESTIMATED` si les conditions pertinentes sont correctement qualifiées et le périmètre de l’estimation explicite. Ne pas conclure « hors projet » sur la seule pente ou le seul préfixe AU.

Le chiffre de 49 026 m² présenté comme emprise doit aussi être identifié précisément : enveloppe d’implantation, emprise maximale après CES, surface avant/après contraintes, contenance ou dessin. Il n’a pas été retrouvé dans les caches inspectés ; aucun recalcul géométrique n’a été lancé dans cet audit. Il ne suffit pas de le rapprocher de la portion AUm pour certifier le calcul ou affirmer une violation du CES.

## 4. Les 7 % ne sont pas un indicateur de justesse

En conservation, les 30 438 `TO_VERIFY` se répartissent par cause principale :

| Cause | Effectif |
|---|---:|
| Géométrie suspecte | 17 461 |
| Assiette douteuse | 8 219 |
| Éligibilité logement inconnue | 3 788 |
| Bande sensible aux inconnues | 939 |
| Hauteur critique absente | 31 |
| **Total** | **30 438** |

Ce sont 7,03 % des 433 229 parcelles, ou 10,11 % si l’on retire seulement les 132 097 hors projet du dénominateur. Aucun de ces taux ne mesure directement la précision du moteur.

À **Saint-Philippe : 3 331 / 4 173 = 79,82 % à vérifier**, tous issus de `hors_plu → ELIGIBILITE_LOGEMENT_INCONNUE` ; aucune capacité estimée. Ce signal impose de vérifier couverture, résolution des zones et lecture du règlement. Il ne démontre pas que 80 % du foncier communal serait problématique.

Les causes vont dans la bonne direction, mais sont encore incomplètes ou mal appliquées :

- La validité géométrique est mesurée pour tous, mais exploitée seulement lorsque la cause est `terrain_exigu`. Une géométrie invalide avec un résiduel positif peut encore sortir comme valide ([adaptateur, ligne 199](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:199)).
- Multipolygone ou faible compacité sont des indices d’investigation, pas des preuves d’erreur. Inversement, un contour compact valide ne prouve pas que l’assiette a été correctement vidée. Le diagnostic ne doit pas convertir un R absent en 0 ni affirmer des retraits vérifiés sans leurs étapes.
- `declasse_au_statut_inconnu` est transformé en `DEFERRED`. Un horizon inconnu doit rester inconnu ([adaptateur, ligne 192](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:192)).
- Le garde-fou legacy PPR/EBC ne traite pas l’ensemble des règles non modélisées pouvant changer le résultat.
- Un verdict d’accès `PASS` signifie « accès non détecté par cette méthode ». Le fait que chaque parcelle ait un verdict ne prouve pas la couverture locale du référentiel. De plus, un futur verdict explicite `UNKNOWN` serait actuellement considéré comme connu, car non nul. Aucune lacune effective de voirie n’a été démontrée ici.

Suivre les causes par commune et scénario, la couverture de calcul, les quantités réellement calculées et un panel de faux positifs/faux zéros. Ne pas choisir un taux cible d’« À vérifier » puis ajuster les règles pour l’atteindre.

## 5. Défauts supplémentaires à corriger avant activation

**A. « Capacité estimée » sans capacité en reconstruction — prioritaire.**

Sur 269 455 reconstructions `ESTIMATED`, **264 383, soit 98,12 %, ont `enriched=false` et C/E/gain net/bande nuls**. Seules 5 072 ont ces quatre champs calculés. Au total, 9 343 parcelles sont enrichies : Entre-Deux 6 341, Saint-Denis 3 000, et les deux cas ciblés. L’échantillon de Saint-Denis correspond aux premiers identifiants, pas à un tirage aléatoire ni à toute la commune.

Le chemin rapide déduit le statut reconstruction depuis la conservation, puis efface les quantités ([persistance, ligne 89](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:89), [ligne 150](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:150)). Cela peut aussi transformer un `terrain_exigu` en reconstruction estimée sans capacité positive établie.

Il faut calculer avant d’affirmer ce statut, ou garder explicitement « calcul à compléter » avec une cause distincte des problèmes de données. Le booléen `enriched` ne suffit pas à réparer la promesse visible du statut. Ne pas publier « 62,2 % de capacités estimées en reconstruction » à partir de ces déductions.

**B. Quantités et provenance peuvent appartenir à deux calculs différents.**

Même en enrichissement, la source d’assiette vient du cache ancien, tandis que C/E sont calculés en direct ([adaptateur, ligne 306](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_build.py:306)). Reproduction : nouveau calcul gabarit + ancien cache legacy + EBC → résultat marqué douteux à tort. Cause, horizon, quantités, source et règles doivent provenir du même calcul identifié.

Un `run_label=q_v20` ne fige pas les vues courantes du résiduel/cascade ni les calculs live. Utiliser les métadonnées et le manifeste existants pour rattacher toutes les composantes à leurs vraies versions ; aucun nouvel appareil de versions n’est nécessaire. La réponse doit annoncer les versions enregistrées avec le résultat, pas la configuration au moment de sa lecture.

**C. Effectifs faux pour une sélection par IDU.**

Les lignes sont filtrées par IDU, mais le calcul des effectifs ne reçoit pas ces IDU ([persistance, ligne 251](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:251)). Une sélection de deux parcelles peut donc annoncer les effectifs de toute l’île. Si commune et IDU sont fournis ensemble, la branche actuelle privilégie la commune au lieu d’appliquer leur intersection. En prospection, les effectifs par statut/bande sont laissés vides. Tout compte doit respecter exactement le même ensemble que la liste, avant pagination.

**D. La protection des valeurs invalides n’est pas appliquée au Signal persisté.**

Le moteur pur valide les probabilités ; le lecteur persisté marque disponible toute valeur non nulle ([persistance, ligne 193](/Users/openclaw/Desktop/labuse-algofix/src/labuse/scoring/scenarios_v2_persist.py:193)). Une valeur 1,2 serait disponible et pourrait se classer en tête ; NaN/infini ne reçoivent pas le bon état. Aucune présence actuelle de ces valeurs n’est établie ici. Appliquer la même validation au chemin réellement servi, sans recalculer ni modifier le Signal.

Les fichiers du Signal sont inchangés, mais cela ne garantit pas ses entrées lors d’un prochain run : le feature store relit le résiduel. Garder le résiduel de référence du Signal identifié et comparer les features/prédictions si l’amont change. Aucune modification actuelle de ses probabilités stockées n’est démontrée par cet audit.

**E. Les deux rapports ne décrivent pas un bilan cohérent.**

Entre-Deux dans la table locale et `AVANT-APRES.md` :

| Scénario | Estimée | Sans ajout | À vérifier | Hors projet |
|---|---:|---:|---:|---:|
| Conservation | 2 255 | 803 | 229 | 3 054 |
| Reconstruction | 2 794 | 0 | 493 | 3 054 |

Le compte rendu donne successivement 2 331 puis 2 335 conservations estimées et 2 881 reconstructions estimées. L’explication « quatre parcelles d’écart » ne couvre pas ces différences. Le gain net local est **+539 estimées**, pas +550.

Il confond aussi distribution communale et cohorte des anciens zéros : les 3 789 anciennes 0 deviennent exactement 2 860 hors projet, 799 sans ajout et 130 à vérifier. Les 3 054 hors projet de toute la commune incluent notamment 194 anciennes HC. Régénérer les tableaux depuis un même instantané et nommer les cohortes.

## 6. Retour proposé à Claude

Je valide les bandes contextualisées, le retrait du coefficient bâti, les deux scénarios, le gain signé et la séparation du Signal. Je ne demande pas une nouvelle refonte produit.

Avant activation :

1. Ne plus déclarer une reconstruction estimée sans capacité calculée.
2. Unifier quantité, provenance, cause, horizon et versions du même calcul.
3. Qualifier les legacy ; à défaut, retenir « À vérifier » pour les capacités non démontrées. Corriger ou isoler le double retrait amont, et mesurer les faux zéros potentiels.
4. Corriger géométrie invalide hors `terrain_exigu`, horizon AU inconnu et diagnostics non prouvés.
5. Instruire EH0043 sur son assiette et son régime AUm réels ; en attendant, résultat provisoire à vérifier.
6. Corriger les effectifs de sélection et la validation du Signal sur le chemin persisté.
7. Régénérer un bilan unique et une matrice complète ; isoler les effets des coefficients et des nouvelles capacités.

Vérifications ciblées : entrée B→C à quantité constante impossible après seul retrait bâti ; reconstruction sans C non estimée ; nouvelle provenance live prioritaire sur l’ancien cache ; invalidité géométrique traitée quelle que soit la cause ; AU inconnue distincte d’AU fermée ; contraintes superposées retirées une fois ; somme des effectifs égale à la sélection réelle avec IDU/commune/pagination ; probabilité Signal invalide jamais disponible. Ajouter un contrôle de précision des quantités aux paliers : l’amont arrondit C/E/R séparément et la V2 recalcule R depuis C/E arrondis ; cela peut produire un écart de 1 m² et franchir un seuil, même si ce n’est pas la cause des deux B→C observées.

Enfin, la calibration des coefficients doit distinguer **quantité de plancher**, **difficulté/coût de réalisation** et **intérêt pour prospecter**. Un coefficient de difficulté ne doit pas être présenté comme une règle de constructibilité ni validé seulement sur la SDP. Conserver les coefficients décidés provisoirement, puis les évaluer sur des cas documentés et plusieurs métiers ; ne pas les retoucher pour corriger une distribution jugée trop généreuse.
