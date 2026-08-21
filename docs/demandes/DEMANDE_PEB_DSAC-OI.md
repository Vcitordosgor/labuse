# Demande — PEB Roland-Garros (vecteur A/B/C/D) → DSAC-OI

- **Destinataire :** Direction de la Sécurité de l'Aviation Civile Océan Indien (DSAC-OI)
- **Copie :** DEAL Réunion
- **Statut :** 🟠 à envoyer
- **Suivi :** date d'envoi — · relance — · réponse —

## Contexte (audit)

Le PEB (Plan d'Exposition au Bruit) était **déclaré couvert** dans l'outil Servitudes / Risques
(`servitudes.py`, kind `peb`) alors que **0 ligne existe en base** — un « couvert-vide » qui produit
un faux « RAS » sur le bruit aérien. Corrigé (M137-T) : `peb` retiré des couvertes et **listé en NON
COUVERT**. Reste à obtenir la donnée pour réellement le servir.

Recherche de source (Phase 1, faite) : **aucune donnée ouverte, à jour et vectorielle** du PEB de La
Réunion n'est disponible dans les canaux standard —

- data.gouv.fr « Zonage des PEB » (dépôt communautaire) : **métropole seule**, **obsolète (2020)** ;
- IGN/Géoplateforme WFS (transports) : **pas de couche PEB** ;
- Géoplateforme WMS `DGAC-PEB_BDD_FXX` : **raster** + code **métropole** ;
- GPU WFS : ne sert que les **SUP** (T5 = dégagement aéronautique, pas le bruit) ;
- PEIGEO (régional) : **pas de jeu PEB** ;
- reunion.gouv.fr (préfecture) : **PDF uniquement** (arrêté + plan 25 Mo + rapport).

Donnée autoritaire : **DGAC**, édition nationale **03/10/2022** (Réunion listée). PEB Roland-Garros
approuvé par **arrêté préfectoral n° 2017-2123 du 17/10/2017** (communes Saint-Denis + Sainte-Marie,
CINOR). Le SIG existe forcément (il a produit le plan de l'arrêté) → demande directe au producteur.

**Ce que ça débloque :** sortir le PEB du NON COUVERT ; détecter le bruit aérien à l'échelle de la
parcelle sous le couloir Roland-Garros ; couche cascade candidate (à mesurer avant ajout).

---

## Lettre

**[Expéditeur — à compléter]**
LABUSE — [raison sociale / SIREN]
[adresse postale]
Courriel : kampusreunion@gmail.com — Tél. : [—]

[Lieu], le [date]

**Direction de la Sécurité de l'Aviation Civile Océan Indien (DSAC-OI)**
Aéroport de La Réunion Roland-Garros
97438 Sainte-Marie

*Copie :* Direction de l'Environnement, de l'Aménagement et du Logement (DEAL) de La Réunion — 2 rue Juliette Dodu, CS 41009, 97404 Saint-Denis Cedex

**Objet :** Demande de communication et de réutilisation de la donnée géographique (vecteur) du Plan d'Exposition au Bruit de l'aérodrome Roland-Garros
**Référence :** arrêté préfectoral n° 2017-2123 du 17 octobre 2017

Madame, Monsieur,

LABUSE édite un outil professionnel d'analyse foncière et d'urbanisme sur le territoire de La Réunion, à destination des opérateurs de l'aménagement (collectivités, aménageurs, promoteurs). L'outil agrège exclusivement des données publiques (cadastre, DVF, documents d'urbanisme via le Géoportail de l'Urbanisme, servitudes d'utilité publique) afin d'éclairer l'analyse d'une parcelle, chaque donnée étant restituée avec sa source et son millésime.

Nous souhaitons y intégrer le **Plan d'Exposition au Bruit de l'aérodrome Roland-Garros**, approuvé par l'arrêté cité en référence. Sa restitution cartographique publique (Géoportail) et les documents de l'arrêté sont accessibles, mais nous n'avons pu identifier de **donnée géographique vectorielle ouverte couvrant La Réunion** : les jeux nationaux ouverts (data.gouv.fr, Géoplateforme) sont limités à la métropole. Or le SIG des zones existe nécessairement, puisqu'il a servi à établir le plan annexé à l'arrêté.

Nous sollicitons donc la **communication du fichier vectoriel des zones A, B, C et D** du PEB Roland-Garros :

- **format SIG** (GeoJSON ou Shapefile), de préférence en RGR92/UTM40S (EPSG:2975) ou WGS84 ;
- accompagné de sa **source** et de son **millésime** (édition de la donnée) ;
- **sous Licence Ouverte (Etalab 2.0)**, ou toute licence de réutilisation équivalente.

**Usage prévu**, que nous nous engageons à respecter : affichage **informatif** de la zone PEB en tant que servitude d'urbanisme à l'échelle de la parcelle, avec **citation systématique de la source (DSAC-OI / DGAC) et du millésime**, et renvoi au certificat d'urbanisme pour la portée opposable. Aucune revente de la donnée brute ; aucune modification de la géométrie source.

Cette demande s'inscrit dans le **droit de réutilisation des informations publiques** (Code des relations entre le public et l'administration, art. L. 321-1 et suivants), les informations publiques étant réutilisables, par défaut sous Licence Ouverte (décret n° 2017-638).

Enfin, une question sur l'**aérodrome de Pierrefonds (Saint-Pierre)** : fait-il l'objet d'un **PEB approuvé mais non publié en ligne**, ou d'un **PEB en projet / en révision** ? Le cas échéant, nous serions intéressés par la même donnée, aux mêmes conditions.

Nous restons à votre disposition pour préciser le cadre technique ou signer tout engagement de réutilisation. En vous remerciant par avance de votre concours, je vous prie d'agréer, Madame, Monsieur, l'expression de ma considération distinguée.

**[Nom, qualité]**
LABUSE

---

## Notes pratiques

- **Vérifier les deux adresses** avant envoi (DSAC-OI à Roland-Garros / Sainte-Marie ; DEAL à
  Saint-Denis). Un envoi courriel (secrétariat DSAC-OI + service donnée DEAL) avec cette lettre en
  PDF est le plus rapide.
- Compléter les **[crochets]** (raison sociale/SIREN, adresse, signataire, date, lieu).
- À réception : consigner **licence + millésime + format** ici, puis ingérer au standard
  (`spatial_layers` kind `peb`, catalogue + radar) et **sortir le PEB du NON COUVERT**.
