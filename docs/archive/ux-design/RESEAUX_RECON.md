# RESEAUX_RECON — desserte eau / assainissement / électricité · La Réunion (974)

*Reconnaissance pour le TEMPS 1 « fiche promoteur » (portails open data réels). Aucune
cascade/scoring touché. Question : **peut-on, en open data, savoir si une PARCELLE est
desservie / proche d'un réseau (eau potable, assainissement, EDF) ?** Réponse :
**non — aucun tracé réseau exploitable par parcelle en 974.** On l'affiche honnêtement
→ « à vérifier auprès des concessionnaires (DT-DICT) », jamais un faux indicateur.*

## Méthode

Revue des portails publics : `donnees.eaureunion.fr/opendata`, `data.regionreunion.com`,
`opendata-reunion.edf.fr`, `opendata.enedis.fr`. On cherche **la géométrie du réseau**
(tracé des conduites BT/HTA, canalisations AEP/EU), pas des statistiques agrégées ni des
points d'installation. Sans linéaire géolocalisé, aucun indicateur « réseau à X m » n'est
calculable sans inventer une donnée.

## Récapitulatif

| Réseau | Source open data réelle | Contenu | Tracé exploitable par parcelle ? | Verdict |
|---|---|---|---|---|
| **Eau potable (AEP)** | `donnees.eaureunion.fr` ; Région ODS | qualité de l'eau, captages, **stations** | ❌ pas de canalisations | **DT-DICT** (Runéo, Créalis, Cilaos, régies) |
| **Assainissement (EU)** | `donnees.eaureunion.fr` | **stations de traitement (STEP)** (points) | ❌ pas de réseau de collecte | **DT-DICT** (service assainissement EPCI) |
| **Électricité** | `opendata-reunion.edf.fr` (*Lignes et postes électriques*) | **agrégats** : km BT/HTA/HTB, nb de postes | ❌ pas de `geo_shape` de ligne | **DT-DICT** (EDF SEI / SIDELEC) |
| *réf. métropole* | `opendata.enedis.fr` (réseau BT/HTA géolocalisé) | tracés BT/HTA, postes | ✅ mais **ne couvre PAS le 974** | hors périmètre (974 = EDF SEI) |

## Détail

- **Eau & assainissement** — Le portail dédié `donnees.eaureunion.fr/opendata` est orienté
  **suivi qualité** et **installations** (stations de traitement, captages), au format CSV.
  **Aucun jeu ne publie le tracé des canalisations** AEP ou EU. Desserte/raccordement →
  **DT-DICT** auprès du concessionnaire/régie.
- **Électricité — spécificité réunionnaise** — La Réunion est une **Zone Non
  Interconnectée** desservie par **EDF SEI** (Systèmes Énergétiques Insulaires), **hors
  périmètre Enedis**. Donc : l'open data **Enedis** (qui contient le **tracé géolocalisé**
  BT/HTA) **ne couvre pas le 974** ; et l'open data **EDF Réunion** ne publie que des
  **agrégats** (longueurs, nombre de postes), **sans coordonnées de tronçons** →
  inexploitable par parcelle.

## Conclusion (ce qui est codé)

`api/enrichment.networks()` renvoie, pour chacun des trois réseaux,
`disponible_open_data=False` + un message DT-DICT, sans **aucun** indicateur de desserte
fabriqué. Si un flux de tracé réseau 974 devient disponible (convention concessionnaire /
ouverture EDF SEI), il s'intégrera comme couche dédiée — sans rien changer à ce constat
tant qu'il n'existe pas.

## Sources

- [Données sur l'eau à La Réunion (open data)](https://donnees.eaureunion.fr/opendata)
- [Open Data La Réunion (Région)](https://data.regionreunion.com/)
- [Open Data EDF Réunion — Lignes et postes électriques](https://opendata-reunion.edf.fr/explore/dataset/lignes-et-postes-electriques/)
- [Enedis — cartographie des réseaux (métropole, hors 974)](https://opendata.enedis.fr/pages/cartographie)
- [Guichet unique DT-DICT](https://www.reseaux-et-canalisations.ineris.fr/)
