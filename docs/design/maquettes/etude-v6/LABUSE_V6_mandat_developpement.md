# LABUSE — V6 « Étude de faisabilité » — Interface épurée
## Mandat produit, réglementaire et technique pour ANTON / Codex

**Version :** 21 octobre 2026  
**Intention :** remplacer l'ancien outil par un parcours ultra-simple de **trois étapes exactement**, avec une expertise maximale dans le résultat.  
**DA :** conserver l'univers LABUSE noir/vert, sobre, premium et lisible.  
**Périmètre :** uniquement des terrains nus. Aucun choix « conserver le bâti », aucun faux bouton « bientôt », aucun programme imposé par LABUSE.

> Le fichier `LABUSE_faisabilite_V6_sans_icones.html` est une maquette front-end autonome, démonstrative. Il contient des parcelles inventées et des hypothèses illustratives ; **il n'est pas un moteur de faisabilité réglementaire**. Le moteur de production doit remplacer toutes les hypothèses fictives, et ne jamais qualifier le résultat de « conforme » sur cette seule base.

---

## 1. Parcours obligatoire : trois étapes, aucune autre

### Étape 1 — Choix des parcelles

- Recherche par **adresse, référence cadastrale ou IDU** ; sélection par champ de recherche et références cadastrales ; de 1 à 8 parcelles dans la maquette. **Aucune vue cartographique interactive dans le formulaire V6.**
- Afficher par parcelle : commune, référence, section, surface cadastrale, surface de référence retenue, source, millésime, géométrie et qualité géométrique.
- Calculer l'union géométrique de l'assiette, son périmètre, sa surface réelle géométrique, l'aire cadastrale reportée et les écarts de mesures.
- **Refuser toute sélection non contiguë**, avec un message précis : « Ces parcelles ne partagent pas de limite commune. Choisissez des parcelles contiguës ou lancez deux études. »
- Ne pas considérer un contact en un seul point comme une contiguïté ; les deux géométries doivent partager une **portion de frontière de longueur non nulle** au-delà d'une tolérance métrique documentée.
- Tester la connexité du **graphe complet des parcelles**, et non seulement leur proximité à la dernière parcelle ajoutée. Réévaluer la connexité après suppression d'une parcelle.
- Règles spécifiques : frontières communes entre communes, zones PLU différentes, traversée par une emprise publique / ravine, parcelle enclavée ou séparation de fait. Ne pas assimiler automatiquement « parcelles contiguës » à « opération constructible ».
- Prévenir lorsque plusieurs propriétaires sont identifiés ou présumés, sans prétendre disposer de ces informations si LABUSE n'y a pas légalement accès. La contiguïté ne prouve ni le même propriétaire ni la maîtrise foncière.
- Ne jamais utiliser la distance entre centroïdes comme critère de contiguïté.

**Proposition géométrique :** PostGIS `ST_IsValid`, normalisation de topologie, `ST_Intersection(ST_Boundary(A), ST_Boundary(B))` et test de longueur de segment positif dans le CRS métrique adapté (tolérance connue), puis composantes connexes du graphe d'adjacence. Les géométries non résolues ou litigieuses passent en « à compléter », jamais en « validées ».

### Étape 2 — Type de projet

**Exactement quatre choix textuels compacts, sans icônes ni dessins :**
1. Résidence étudiante ;
2. Résidence senior ;
3. Logement social ;
4. Lotissement.

La sélection doit faire apparaître **sans intervention supplémentaire** :
- les règles de stationnement du PLU effectivement applicable, **l'article et la version** ;
- l'unité de calcul (place par logement, tranche de surface, chambre, lot, surface commune, etc.) ;
- les exceptions / taux particuliers / arrondis et obligations de stationnement visiteurs, vélos, PMR lorsque pertinentes ;
- les éventuels plafonds nationaux applicables **sous condition d'éligibilité**, et leurs conséquences sur l'exigence locale ;
- l'état de fiabilité : « règle vérifiée », « clause ambiguë », « document manquant ».

**IMPORTANT — stationnement :** le Code de l'urbanisme prévoit à l'article L151-35 des plafonds légaux pour certaines catégories visées à L151-34. Les plafonds ne sont **pas des minima**, et les noms commerciaux « résidence étudiante » ou « senior » ne prouvent **pas** que le projet relève de la catégorie juridique éligible. Ne jamais préremplir arbitrairement « 1 place/logement » en la présentant comme la règle du PLU. Demander une précision de qualification juridique **dans le résultat ou un panneau d'alerte contextuel**, sans créer une quatrième étape obligatoire.

**Lotissement :** juridiquement une division foncière, pas un bâtiment collectif. En résultat, produire une vraie logique de **lots à bâtir**, emprise de voirie, raccordements, parties communes, obligations de stationnement applicables aux futures constructions, et régime procédural (à instruire). Les T1–T4 saisis à l'étape 3 sont des **hypothèses de logements futurs**, et non un calcul automatique du nombre de lots ou un droit de construire garanti.

### Étape 3 — Composition du programme

Le promoteur fixe les quantités **sans suggestion forcée** :

| Type | Surface totale saisie par logement | Varangue incluse | Intérieur indicatif par logement |
|---|---:|---:|---:|
| T1 | 30 m² | 6 m² | 24 m² |
| T2 | 56 m² | 9 m² | 47 m² |
| T3 | 70 m² | 12 m² | 58 m² |
| T4 | 80 m² | 14 m² | 66 m² |

Les quatre lignes compactes T1, T2, T3 et T4, avec compteurs +/− et saisie numérique, doivent mettre à jour en temps réel : nombre de logements, surfaces intérieures, surfaces de varangues, total du programme, stationnement calculé selon règles applicables, impact au sol, surfaces communes et besoins techniques.

**Prudence fondamentale :** ne pas utiliser ces surfaces commerciales comme équivalent automatique de SDP ou de SHAB. La SDP est définie par l'article R111-22 du Code de l'urbanisme (niveaux clos et couverts et déductions applicables). Gérer varangues ouvertes / fermées, noyaux, locaux techniques, circulations, escaliers et surfaces déductibles correctement.

**Pas d'autre étape.** Terrain nu implicite. Le stationnement, les risques et les diagnostics ne sont **pas des étapes d'entrée supplémentaires** : ils sont calculés et expliqués dans les résultats.

---

## 2. Le vrai résultat : « ce programme est-il faisable, et qu'est-ce qui reste ? »

### A. Une réponse intelligente, pas une interdiction rouge

Pour chaque programme, répondre dans cet ordre :
1. **Demande** : 10 T1 = 300 m² au total dont 60 m² de varangues, 240 m² intérieurs indicatifs.
2. **Capacité établie** : résultat du moteur d'implantation réellement **géométrique**, après règles vérifiées.
3. **Écart / réserve** : exemple « il reste 200 m² de programme à explorer » **uniquement si un scénario réel justifie ce montant** ; afficher l'étiquette « estimé » sinon.
4. **Facteur limitant** : recul / emprise / PLU / PPR / pente / parking / pleine terre / voirie / servitudes, classés par impact chiffré lorsque possible.
5. **Alternative concrète** : ex. répartition différente des typologies, bâtiment en barre vs plots, autre placement, mutualisation possible ou légalement impossible, nombre de logements revu, nécessité de vérifier un point auprès de la commune.

**Ne pas confondre** les m² restant sur la parcelle au sol, la surface d'emprise encore mobilisable, la SDP autorisée et les m² de logements/varangues envisageables. Ce sont quatre grandeurs différentes et elles doivent être labellisées séparément.

### B. Ne pas estimer un « maximum » par une simple règle de trois

Le surplus possible est **non linéaire** : ajouter un T1 peut déclencher une place de parking, un nouveau palier de locaux cycles, une circulation, une contrainte de manœuvre ou une augmentation d'emprise et donc annuler l'espace attendu.

Dans le moteur de production :
- construire un **jumeau géométrique** de l'assiette ;
- soustraire les zones réellement interdites à la construction ;
- appliquer les bandes de recul, alignements, prospect et servitudes selon zone et orientation ;
- évaluer les gabarits réellement possibles en hauteur et volume ;
- réserver voies, accès et aires de manœuvre ;
- dessiner les places exactes, y compris PMR/visiteurs quand requises ;
- réserver les surfaces réglementaires non bâties, pleine terre, plantations et gestion des eaux ;
- affecter les logements par niveau avec noyaux, circulation et surfaces communes ;
- vérifier que le programme tient réellement dans les polygones construits ;
- relancer l'optimiseur en ajoutant ou retirant des logements jusqu'à trouver une **frontière de variantes faisables**.

Ne calculer « vous pouvez encore ajouter X m² » que depuis une variante **dessinée et vérifiée**, sinon l'annoncer comme « marge indicatrice non prouvée ».

### C. Variantes produites dans le résultat (pas une étape)

- **Variante 1 — Votre programme** : tester exactement ce qui est demandé.
- **Variante 2 — Optimisation** : meilleure occupation raisonnable, sans modifier le type d'opération choisi.
- **Variante 3 — Alternative** : changement de distribution/implantation en respectant le programme ou en explicitant très clairement toute modification.

Chaque variante présente les mêmes chiffres : nb T1/T2/T3/T4, SDP, intérieur/SHAB (si calculable), varangues, emprise, espaces verts, parkings exigés/dessinés, surfaces de voies, reculs et principales limites. **Une place annoncée = une place dessinée et manœuvrable.**

### D. Exemple de message attendu

> **Votre demande : 10 T1, soit 300 m² de programme varangues comprises.** La variante vérifiée accueille les 10 T1. Une réserve potentielle de **200 m²** subsiste après stationnement et espaces obligatoires. Cette réserve n'est pas nécessairement convertible en logements supplémentaires : l'optimisation teste notamment les places supplémentaires et les accès. [Voir les variantes] [Voir les calculs]

Si le programme dépasse les variantes explorées :

> **Votre programme dépasse les enveloppes testées, mais l'impossibilité n'est pas démontrée.** Avec la configuration A, 14 T1 seraient dessinables sur les 18 demandés ; quatre logements restent sans implantation admissible. L'accès et les places de parking sont les premiers points limitants. [Comparer les alternatives] [Réduire la quantité] [Voir les règles]

---

## 3. Couverture réglementaire et technique minimale

| Volet | Données / règles à charger | Preuve attendue |
|---|---|---|
| Géométrie | Cadastre PCI, dimensions, superficie réelle, limites, voies | Géométrie valide, niveau de précision, source/millésime |
| PLU/PLUi | Zone(s), règlement écrit et graphique, destinations, mixité | Texte exact, article, date d'opposabilité, zone/localisation |
| Emprise | Règle applicable + définition et exceptions | Emprise polygonale réelle et ratio, pas seulement un % supposé |
| Implantation | Reculs sur voie/fond/latéraux, alignements, prospects | Distances mesurées depuis géométrie bâtiment/limites |
| Hauteur | Égout/faîtage/hauteur absolue et relative | Altitude géoréférencée + coupe + comparaison de règles |
| Stationnement | Par destination et régime, PMR/vélos/visiteurs, dimensions | Obligation justifiée + places dessinées, girations et accès testés |
| PPR | Règlement et cartographie du bon PPR, aléas ciblés | Partie de parcelle touchée, nature des prescriptions/interdictions |
| Servitudes | SUP, ER, EBC, OAP et annexes | Surfaces/impacts localisés et justification de l'effet réel |
| Eau / pente | LiDAR, topographie, ravines, pluvial, eaux usées | Profil, hypothèses, étude complémentaire si besoin |
| Réseaux | Accès réseaux eau / électricité / assainissement | Donnée sourcée, absence de donnée = « à vérifier » |
| Surfaces | SDP, SHAB, annexes, varangues, pleine terre, emprise, voiries | Bilan clos, unités cohérentes, détails et déductions |
| Lotissement | lots, largeur voies, espaces communs, raccordements | Plan de division, tableau des lots et procédure à qualifier |

**Principe PPR :** le rouge ne se supprime automatiquement de l'implantation que lorsque la prescription applicable interdit effectivement la construction projetée. Le bleu ne signifie pas « conforme » ; ses prescriptions doivent être satisfaites ou l'étude passe « à compléter ». Un risque absent d'une couche ou un règlement non analysé = « non vérifié », jamais « absent ».

**Parcelles multi-zones :** traiter chaque intersection géométrique terrain × zonage PLU/PPR/SUP et appliquer le corpus adapté au sous-secteur ; ne pas prendre arbitrairement la zone majoritaire.

---

## 4. États de confiance, blocs et messages

Séparer strictement :

- **État du contrôle individuel :** Réussi avec preuve / Échoué avec preuve / Non effectué / Non applicable / À confirmer (ambigüité de donnée ou de texte).
- **État de l'étude globale :** Exploitable sous hypothèses documentées / À compléter / Impossible pour une cause établie et déterminante.

Le fait que trois ou cinq règles aient réussi **ne suffit pas** pour qualifier l'étude d'exploitable si un PPR, l'accès, la voirie ou le stationnement restent indéterminés.

Aucun bouton ne doit être désactivé sans raison explicite : chaque contrôle interactif a une action réelle ; les fonctionnalités hors périmètre ne sont pas affichées. Les erreurs de géométrie et de données ont un message localisé et une proposition d'action.

---

## 5. Architecture proposée

### Services

1. **`parcel-service`** : géocodage, lookup IDU, géométries, contrôle de connexité, union, qualité topologique.
2. **`planning-data-service`** : PLU opposable, version, zonage, OAP, servitudes, lecture de règlement écrite, extraction avec preuve.
3. **`risk-service`** : PPR, aléas et pièces réglementaires, données multi-parcelles.
4. **`rules-engine`** : règles structurées conditionnelles par destination/zone et exceptions nationales ; statut + article + méthode.
5. **`site-envelope-engine`** : zones de recul, contraintes de construction, cotes et terrain/pente.
6. **`scenario-solver`** : implantation volumétrique réelle, programme T1–T4, accès/parking, optimisation et alternatives.
7. **`report-service`** : document multi-page avec chiffres identiques à ceux de l'interface, version des sources, légendes, limites, contrôles et annexes.

### Contrats attendus (schémas conceptuels)

- `POST /feasibility/sites` reçoit `parcel_ids` et renvoie union / continuité / surface / qualité / conflits.
- `POST /feasibility/programs/analyze` reçoit `site_id`, `project_type`, `mix {T1,T2,T3,T4}`, `unit_areas`, `verandas`, version de règles ; renvoie `study_id`, source lineage, `program_budget`, `constraint_checklist`, `variants[]`, `status`.
- `GET /feasibility/studies/:id` renvoie l'ensemble sourcé et le statut par contrôle.
- `GET /feasibility/studies/:id/report.pdf` génère depuis **la même donnée versionnée** (pas un second calcul divergent).

L'API doit retourner des valeurs numériques + unités + origine des données, et distinguer systématiquement `measured`, `derived`, `assumed`, `unknown`. Ne jamais envoyer `compliant=true` sans preuve technique et réglementaire.

### Sources officielles à prévoir

- Géoportail de l'Urbanisme : https://www.geoportail-urbanisme.gouv.fr/api/ (documentation renvoyant notamment à API Carto pour interrogation géographique, et aux exports pour les gros volumes).
- Code de l'urbanisme, stationnement : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000052866913
- Code de l'urbanisme, surface de plancher : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031721274
- Géorisques et les PPR en vigueur : https://www.georisques.gouv.fr/

Le moteur doit documenter les données de La Réunion, les PLU de chacune des 24 communes, les spécificités de leur réglementation et les PPR applicables. Vérifier la mise à jour et l'opposabilité avant tout calcul.

---

## 6. Critères d'acceptation (tests obligatoires)

1. Ajouter D-101 + D-102 (jeu fictif) : accepté car segment commun de longueur positive.
2. Ajouter D-900 après D-101 : refus clair « non contigu » ; sélection inchangée.
3. Ajouter D-101 puis D-105 seulement par contact de sommet : refus ; ne pas confondre proximité et contiguïté.
4. Supprimer une parcelle de liaison qui scinde l'ensemble : blocage ou proposition explicite de deux études.
5. Toutes les recherches, sélections de parcelles, compteurs, liens, onglets, boutons retour et export fonctionnent et donnent un retour d'erreur utile.
6. Le formulaire contient **exactement 3 étapes**, aucun choix du bâti / de parking en ouvrage / d'objectifs abstraits, et aucune carte interactive.
7. Aucun pictogramme dans les quatre choix de projet ; quatre lignes T1–T4 compactes ; pas de sélection initiale de type de projet ou de typologies au nom de l'utilisateur.
8. Programme `10 × T1` = **300 m² dont 60 m² de varangues**, **240 m² d'intérieur indicatif** ; ne pas appeler les 300 m² « SDP ».
9. Changer étudiant → social / senior / lotissement met à jour l'explication du stationnement et l'ensemble des calculs concernés, **sans** inventer le taux PLU local.
10. Ajouter des logements met à jour l'écart et peut faire émerger une contrainte discrète de stationnement.
11. PPR bleu et servitude partielle ne deviennent jamais « Réussi » sans lecture de la prescription.
12. Aucun coefficient de démonstration (35 %, 12 %, etc.) ne reste dans le calcul de production sans source et sans statut `assumed`.
13. Bilan surfacique clos : total du site = union exclusive de catégories cohérentes, aucune double-comptabilisation, zéro aire injustifiée dans la tolérance annoncée.
14. Chaque nombre de places annoncées est démontré par autant d'emplacements géométriques accessibles, pas seulement des étiquettes.
15. L'écart entre programme et scénario n'est jamais présenté automatiquement comme capacité maximale certaine.
16. Si un règlement manque, l'étude reste « à compléter » ; la génération du document peut continuer avec avertissements visibles et liste des pièces manquantes.
17. Une capture/rapport et une interface du même `study_id` affichent exactement les mêmes logements, surfaces et places.
18. Compatibilité mobile, clavier, lecteur d'écran ; contrôles accessibles par tabulation et annonces d'erreur explicites.
19. Tester les vrais cas réunionnais : zone multi-PLU, secteur PPR bleu, PPR rouge avec interdiction, terrain en pente, parcelles en bande, enclavement, accès étroit, forte obligation de pleine terre.
20. Chaque variante issue du vrai optimiseur respecte sa propre logique géométrique ; aucun bâtiment ne figure sur une parcelle non retenue.

---

## 7. Plan de livraison conseillé

**Lot A — Fondations fiables :** vraies parcelles + contiguïté + sources + qualification du statut + règle de stationnement locale. **Aucune promesse de constructibilité** à ce stade.

**Lot B — Réglementation spatialisée :** PLU/PPR/SUP, bandes de recul, emprise, pleine terre, hauteur, zones interdites et contraintes conditionnelles. Tests unitaires par commune et par zone.

**Lot C — Optimisation géométrique :** implantation réelle, accès, parking dessinable, enveloppes et scénarios, quantification des marges et facteurs limitants.

**Lot D — Rapport commercialisable :** plan masse métré, coupe cotée, 3 variantes, tableau de contrôles, sources et annexes, cohérence absolue des surfaces et indicateurs.

### Priorité absolue

**Ne pas chercher à faire paraître l'outil plus certain qu'il ne l'est.** Le différenciateur de LABUSE sera la combinaison de l'ambition algorithmique et de l'explication très lisible, pas le nombre de « feux verts » affichés.
