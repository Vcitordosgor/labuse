# CDC GABARIT — Cahier des charges « Gabarit réglementaire » (texte de Vic, 22/09/2026)

Fait foi sur le fond. Le mandat GABARIT-1 fait foi sur la méthode et sur ce qui est réel vs fictif.

---

Je veux que tu implémentes dans l'application LABUSE un outil nommé « Gabarit réglementaire ».

Travaille directement dans le projet existant et livre une implémentation fonctionnelle, testée et intégrée.

## PRINCIPE ABSOLU

Dans cet outil, le flux doit toujours être :

SOURCE → VALIDATION → CALCUL → AFFICHAGE

Jamais :

SUPPOSITION → ESTIMATION → AFFICHAGE

LABUSE Gabarit doit uniquement traduire graphiquement et mathématiquement des données réglementaires sourcées et vérifiées.

Il est strictement interdit de calculer ou d'afficher :

- un nombre de logements ;
- un nombre d'étages supposé ;
- une surface de plancher estimée ;
- un coût ;
- une valeur immobilière ;
- un potentiel immobilier estimatif ;
- toute autre donnée déduite sans règle réglementaire explicitement fournie.

## OBJECTIF MÉTIER

Répondre uniquement à cette question :

« Selon les règles réglementaires effectivement connues et intégrées dans LABUSE, où et jusqu'où une construction peut-elle être implantée sur cette parcelle ? »

## 1. INSPECTION AVANT MODIFICATION

Avant de coder :

- inspecte l'architecture existante ;
- identifie le framework, la bibliothèque cartographique, les composants UI, les conventions de typage et les design tokens ;
- repère les utilitaires géospatiaux déjà présents ;
- réutilise impérativement les composants, tokens et conventions existants ;
- ne redesign pas LABUSE ;
- ne crée pas une nouvelle architecture si l'existant peut être étendu ;
- si un prototype Gabarit existe déjà, fais-le évoluer au lieu de créer un second outil parallèle.

## 2. CONTRAT D'ENTRÉE UNIQUE

Toutes les données, fictives ou réelles, doivent passer par un seul objet d'entrée.

Utilise une structure équivalente à :

```ts
type RegulatorySource = {
  document: string;
  zone?: string;
  article?: string;
  versionDate?: string;
  provider?: string;
};

type GabaritInput = {
  parcel: {
    id: string;
    geometry: GeoJSON.Polygon;
    areaM2: number;
    source: RegulatorySource;
  };

  setbacks: Array<{
    id: string;
    ruleId: string;
    type: "road" | "side" | "rear";
    geometry: GeoJSON.LineString;
    setbackM: number;
    source: RegulatorySource;
  }>;

  maxFootprint: {
    ruleId: string;
    percent: number;
    source: RegulatorySource;
  };

  maxHeight: {
    ruleId: string;
    meters: number;
    source: RegulatorySource;
  };

  exclusions: Array<{
    id: string;
    ruleId: string;
    type: string;
    label: string;
    geometry: GeoJSON.Polygon;
    source: RegulatorySource;
  }>;

  applicableRules: Array<{
    id: string;
    label: string;
    category:
      | "setback"
      | "maxFootprint"
      | "maxHeight"
      | "exclusion"
      | "other";
    integrationStatus: "integrated" | "not_integrated";
    detail?: string;
    source: RegulatorySource;
  }>;

  sources: RegulatorySource[];
};
```

Les propriétés peuvent être optionnelles au niveau TypeScript si cela est nécessaire pour représenter un chargement incomplet, mais le moteur doit effectuer une validation stricte avant tout calcul.

Chaque donnée calculatoire doit posséder :

- une valeur explicite ;
- un ruleId ;
- une source ;
- une règle correspondante dans applicableRules ;
- une source présente dans le catalogue sources.

La source de la valeur doit être cohérente avec celle de la règle applicable.

Une source doit au minimum avoir un champ document non vide.

Ne jamais inventer une source ou compléter automatiquement une métadonnée manquante.

## 3. VALIDATION ET FIABILITÉ

Avant le calcul, contrôler au minimum :

- identifiant, géométrie, surface et source cadastrale ;
- géométries des limites ;
- couverture du périmètre de la parcelle par les limites ;
- type de chaque limite ;
- valeur et source de chaque recul ;
- valeur et source du plafond d'emprise ;
- valeur et source de la hauteur ;
- géométrie, type, libellé et source de chaque exclusion ;
- présence de l'inventaire applicableRules ;
- présence du catalogue sources ;
- cohérence entre ruleId, catégorie, état d'intégration et source.

Une valeur égale à zéro est valide si elle est explicitement fournie et sourcée.

Si une donnée nécessaire manque, est invalide ou n'est pas sourcée :

- ne produire aucune zone réglementaire ;
- ne produire aucune métrique ;
- ne proposer aucune vue 3D ;
- afficher exactement :

« Calcul incomplet — donnée réglementaire manquante »

Une règle applicable marquée not_integrated :

- ne doit jamais modifier le calcul ;
- doit apparaître dans « Règles non intégrées » ;
- doit être incluse dans le compteur correspondant ;
- doit elle-même être sourcée.

Ne considère pas automatiquement les risques comme intégrés parce que exclusions est un tableau vide.

Une analyse des risques explicitement sourcée doit être présente dans applicableRules.

## 4. MOTEUR GÉOSPATIAL

Le moteur doit rester pur, déterministe et indépendant de React et de la carte.

Il doit uniquement :

1. partir du polygone cadastral ;
2. appliquer les reculs associés aux limites road, side et rear ;
3. soustraire les zones d'exclusion ;
4. produire la zone finale d'implantation réglementaire ;
5. calculer sa surface ;
6. calculer séparément le plafond d'emprise :

maxFootprintM2 = parcel.areaM2 * maxFootprint.percent / 100

Ne jamais confondre :

- la surface de la zone d'implantation ;
- le plafond réglementaire d'emprise.

Ne jamais appliquer implicitement :

min(zoneImplantation, plafondEmprise)

Le résultat peut être un Polygon, un MultiPolygon ou une zone vide valide.

Réutilise les outils géospatiaux existants.

S'il n'existe rien d'adapté, utilise uniquement les modules Turf strictement nécessaires.

Le résultat du moteur doit également exposer :

- les règles effectivement appliquées ;
- leurs valeurs ;
- leurs sources ;
- les règles non intégrées ;
- la couverture réglementaire ;
- les géométries nécessaires à la carte.

## 5. TERMINOLOGIE

Utilise uniquement :

- « Gabarit réglementaire »
- « Zone d'implantation réglementaire »
- « Plafond d'emprise »
- « Hauteur réglementaire »
- « Couverture réglementaire »
- « Règles appliquées »
- « Règles non intégrées »

Supprime les formulations suivantes de l'interface :

- « Enveloppe constructible »
- « Gabarit constructible »
- « Données complètes »

Ne jamais laisser entendre qu'une construction finale est automatiquement possible sur toute la zone affichée.

## 6. PANNEAU DE RÉSULTATS

Conserve l'esthétique actuelle de LABUSE.

Le panneau principal doit rester très compact et premium.

Exemple :

```
GABARIT RÉGLEMENTAIRE

Surface parcelle
1 180 m²

Zone d'implantation
579 m²

Plafond d'emprise
472 m²

Hauteur réglementaire
10 m

Couverture réglementaire
4 familles vérifiées
2 règles non intégrées
```

Ajouter un contrôle accessible :

« Voir les règles appliquées »

La couverture doit afficher les quatre familles actuellement prises en charge :

- ✓ Reculs vérifiés
- ✓ Hauteur vérifiée
- ✓ Emprise vérifiée
- ✓ Risques intégrés

Important :

Le nombre « 4 familles vérifiées » correspond aux quatre familles de couverture réglementaire.

Il ne correspond pas au nombre de segments géométriques ni au nombre total d'articles PLU.

## 7. RÈGLES APPLIQUÉES

Afficher une section compacte générée directement depuis le résultat du moteur.

Aucune valeur ne doit être codée en dur dans l'interface.

Exemple :

```
RÈGLES APPLIQUÉES

✓ Recul voie : 5 m
  PLU fictif — Commune X — UC 6

✓ Limites séparatives : 3 m
  PLU fictif — Commune X — UC 7

✓ Emprise maximale : 40 %
  PLU fictif — Commune X — UC 9

✓ Hauteur maximale : 10 m
  PLU fictif — Commune X — UC 10

✓ PPR
  Zone rouge exclue
  PPR fictif — Commune X — version du 15/03/2024
```

Les segments partageant :

- le même ruleId ;
- la même valeur ;
- la même source ;

doivent être regroupés.

Ne fusionne jamais des règles dont la valeur ou la source diffère.

Afficher ensuite les règles connues mais non intégrées :

```
⚠ 2 règles applicables non intégrées

- Stationnement
- Espaces libres
```

## 8. CARTE ET 3D

Conserve la carte actuelle et ses conventions visuelles.

Afficher sobrement :

- le contour cadastral ;
- les retraits réglementaires ;
- les exclusions ;
- la zone d'implantation réglementaire.

Les couches réglementaires calculées ne doivent être affichées qu'après validation réussie.

La légende doit utiliser :

« Zone d'implantation réglementaire »

Conserve la bascule 2D / 3D si elle s'intègre correctement à l'existant.

En 3D :

- extrude uniquement la géométrie réglementaire calculée ;
- utilise exclusivement la hauteur sourcée retournée par le moteur ;
- n'utilise aucun fallback ou nombre supposé ;
- ne représente jamais un bâtiment réel ;
- présente la vue comme :

« Enveloppe réglementaire selon les règles intégrées »

En cas de donnée manquante ou de calcul incomplet, la vue 3D doit être indisponible.

## 9. DONNÉES DE DÉMONSTRATION

Pour le moment, créer ou conserver une parcelle fictive avec :

- surface cadastrale : 1 180 m² ;
- recul voie : 5 m ;
- recul des limites séparatives : 3 m ;
- plafond d'emprise : 40 %, soit 472 m² ;
- hauteur réglementaire : 10 m ;
- une exclusion PPR rouge ;
- stationnement et espaces libres comme règles applicables non intégrées.

Toutes les sources doivent être clairement marquées comme fictives.

Les mocks doivent utiliser exactement le même contrat que les futures données réelles.

Il ne doit exister aucune logique spécifique aux données fictives dans le moteur.

## 10. TESTS OBLIGATOIRES

Ajouter des tests couvrant au minimum :

- calcul nominal ;
- distinction zone d'implantation / plafond d'emprise ;
- valeurs explicitement égales à zéro ;
- exclusion partielle ;
- exclusion totale produisant une zone vide ;
- entrée non mutée ;
- géométrie invalide ;
- limite ne suivant pas la parcelle ;
- périmètre insuffisamment couvert ;
- valeur manquante ;
- source manquante ;
- document de source vide ;
- source absente du catalogue ;
- source différente de celle de la règle applicable ;
- règle utilisée mais marquée non intégrée ;
- règle non intégrée supplémentaire ne modifiant jamais les métriques ;
- analyse des risques absente ;
- exclusion sans type ou sans libellé ;
- regroupement des segments partageant un ruleId ;
- absence de tout champ estimatif dans le résultat.

Lancer ensuite :

- vérification TypeScript ;
- tests ;
- build de production ;
- recette navigateur du clic « Générer le gabarit » ;
- recette du détail des règles ;
- recette 2D / 3D ;
- recette de réinitialisation.

## 11. BRANCHEMENT DES FUTURES DONNÉES RÉELLES

Prévoir un point de raccordement unique pour remplacer les mocks.

Correspondances futures :

- cadastre → parcel
- PLU → setbacks, maxFootprint, maxHeight
- PPR et servitudes → exclusions
- analyse documentaire des règlements → applicableRules
- dossier documentaire / métadonnées → sources

Le remplacement des mocks par les vraies données ne doit nécessiter aucune réécriture :

- du moteur ;
- de la carte ;
- du panneau ;
- de la vue 3D.

## 12. LIVRAISON

Implémente réellement les changements.

Ne t'arrête pas à une proposition ou à un plan.

À la fin, indique précisément :

- l'architecture existante identifiée ;
- les fichiers créés ou modifiés ;
- la structure de données finale ;
- le fonctionnement du moteur ;
- les règles actuellement prises en charge ;
- les règles fictives non intégrées ;
- l'emplacement exact où brancher les données PLU / PPR / cadastre ;
- les commandes de validation exécutées ;
- le résultat de chaque validation.

## RÈGLE FINALE

Ne redesign pas LABUSE.

Ne crée aucune règle réglementaire absente.

Ne complète aucune donnée par intuition.

Ne génère aucune estimation.

Si une décision réglementaire nécessaire n'est pas explicitement fournie et sourcée :

BLOQUE LE CALCUL.

La fiabilité de LABUSE est prioritaire sur la quantité d'informations affichées.
