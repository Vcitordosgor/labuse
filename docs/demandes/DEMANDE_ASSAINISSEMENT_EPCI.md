# Demande — Assainissement (zonage SIG + réseau collectif) → 5 EPCI

- **Destinataires :** les 5 EPCI de La Réunion (compétence assainissement) — **courrier type,
  personnalisable par EPCI** (tableau ci-dessous).
- **Statut :** 🟠 à envoyer
- **Suivi (par EPCI) :** CINOR — · TCO — · CIVIS — · CASUD — · CIREST —

## Contexte (audit)

Le projet porte une couche `zonage_assainissement` (`spatial_layers`) à **couverture partielle** (le
GPU ne sert l'assainissement que pour une minorité de communes). Or la distinction **raccordable au
réseau collectif** vs **assainissement non collectif (ANC) obligatoire** est un facteur réel de
**coût et de faisabilité** par parcelle — aujourd'hui mal couvert, donc à afficher en NON COUVERT là
où la donnée manque. Le **zonage d'assainissement** est un document public (obligatoire, annexé au
PLU — **art. L. 2224-10 CGCT**) ; le **tracé du réseau collectif** est une donnée patrimoniale du
service public d'assainissement, détenue par l'EPCI compétent.

**Ce que ça débloque :** compléter `zonage_assainissement` sur les 24 communes → critère
« raccordable / ANC » fiable dans l'analyse de faisabilité et de charge.

## Personnalisation par EPCI

Remplacer `{EPCI}`, `{PRÉSIDENT}`, `{SIÈGE}`, `{ADRESSE}` selon la ligne. **Adresses à vérifier
avant envoi.**

| `{EPCI}` | Communes | `{SIÈGE}` (commune) | `{ADRESSE}` |
|---|---|---|---|
| **CINOR** (Communauté Intercommunale du Nord de la Réunion) | Saint-Denis, Sainte-Marie, Sainte-Suzanne | Sainte-Clotilde (Saint-Denis) | [à compléter] |
| **TCO** (Territoire de la Côte Ouest) | Le Port, La Possession, Saint-Paul, Trois-Bassins, Saint-Leu | Le Port | [à compléter] |
| **CIVIS** (Comm. Intercomm. des Villes Solidaires) | Saint-Pierre, Saint-Louis, Cilaos, Étang-Salé, Les Avirons, Petite-Île | Saint-Pierre | [à compléter] |
| **CASUD** (Comm. d'Agglomération du Sud) | Le Tampon, Saint-Joseph, Saint-Philippe, Entre-Deux | Le Tampon | [à compléter] |
| **CIREST** (Comm. Intercomm. Réunion Est) | Saint-Benoît, Bras-Panon, Saint-André, Salazie, La Plaine-des-Palmistes, Sainte-Rose | Saint-Benoît | [à compléter] |

---

## Lettre type

**[Expéditeur — à compléter]**
LABUSE — [raison sociale / SIREN]
[adresse postale]
Courriel : kampusreunion@gmail.com — Tél. : [—]

[Lieu], le [date]

**Monsieur/Madame le Président de {EPCI}**
{ADRESSE}
{SIÈGE}

*À l'attention du service en charge de l'assainissement.*

**Objet :** Demande de communication et de réutilisation des données d'assainissement (zonage et réseau collectif) au format SIG

Madame, Monsieur le Président,

LABUSE édite un outil professionnel d'analyse foncière et d'urbanisme à La Réunion, à destination des opérateurs de l'aménagement. L'outil agrège exclusivement des données publiques et restitue chacune avec sa source et son millésime, afin d'éclairer l'analyse d'une parcelle — notamment sa desserte par les réseaux, déterminante pour la faisabilité et le coût d'un projet.

Au titre de la compétence assainissement de votre établissement, nous sollicitons la **communication et l'autorisation de réutilisation** des données suivantes, pour le territoire de {EPCI} :

1. le **zonage d'assainissement** (délimitation des zones d'assainissement **collectif** et **non collectif**), au **format SIG** (GeoJSON ou Shapefile) — document public annexé au PLU (art. L. 2224-10 du CGCT) ;
2. le **tracé du réseau d'assainissement collectif** (ou, à défaut de communication du tracé détaillé, la **desserte par secteur** : zones effectivement raccordées / raccordables).

Nous souhaitons ces données **avec leur source et leur millésime**, et **sous Licence Ouverte (Etalab 2.0)** ou licence de réutilisation équivalente.

**Usage prévu**, que nous nous engageons à respecter : affichage **informatif** de la situation d'assainissement à l'échelle de la parcelle (raccordable au collectif / ANC probable), avec **citation systématique de la source ({EPCI}) et du millésime**, à titre indicatif — la situation réglementaire opposable restant celle du certificat d'urbanisme et des règlements de service. Aucune revente de la donnée brute ; aucune modification de la géométrie source.

Cette demande s'inscrit dans le **droit de réutilisation des informations publiques** (Code des relations entre le public et l'administration, art. L. 321-1 et suivants), réutilisation par défaut sous Licence Ouverte (décret n° 2017-638).

Nous restons à votre disposition pour préciser le cadre technique ou signer tout engagement de réutilisation. En vous remerciant par avance, je vous prie d'agréer, Madame, Monsieur le Président, l'expression de ma haute considération.

**[Nom, qualité]**
LABUSE

---

## Notes pratiques

- **Vérifier l'adresse** du siège de chaque EPCI avant envoi ; adresser au **service assainissement**
  (ou à la direction de l'eau et de l'assainissement) via le Président.
- Le **tracé réseau** peut être jugé sensible par certains EPCI : la formulation propose un repli
  (« desserte par secteur ») — le **zonage seul** est déjà exploitable et suffit à la couche.
- Suivi par EPCI dans l'en-tête ; passer chaque ligne du tableau `README.md` au fur et à mesure
  (une demande = 5 envois, statut consolidé le plus prudent).
