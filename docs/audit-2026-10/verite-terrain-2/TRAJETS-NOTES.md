# VERITE-TERRAIN-2 — volet B : temps de trajet & distances

Audit de ce que LABUSE **sert comme temps de trajet** vers les équipements d'une zone, face à un
routeur d'itinéraire **indépendant**. Le volet A compare les *règles* (PLU) ; ce volet-ci compare les
*temps d'accessibilité*. Lecture seule : aucune écriture en base, aucun appel au code existant qui
mute (`zone.isochrone()` n'est pas appelé — il insère en cache base) ; les isochrones et itinéraires de
référence sont mis en cache **sur disque** (`cache/trajets/`, non commité).

Fichiers du volet : `TRAJETS.csv` (1473 paires comparées), `echantillon_trajets.csv` (les 300
parcelles tirées), module `src/labuse/verite_terrain_trajets.py` (méthode).

---

## 1. Ce que LABUSE sert réellement

Lu dans `src/labuse/zone.py` et reproduit fidèlement par le comparateur :

- LABUSE ne sert **jamais une distance en mètres** pour ces POI, ni un temps continu. Il sert une
  **bande d'isochrone** parmi `_BANDES = (2, 4, 6, 8, 10, 15)` minutes. Pour un POI donné, le
  « temps_min » affiché est la **plus petite bande dont l'isochrone contient le POI**
  (`zone._bande_min`, copié à l'identique dans `bande_min_disque`). C'est donc une **borne haute
  quantifiée** : un POI réellement à 1 min est servi « 2 min » ; un POI à 4 min 30 est servi « 6 min ».
- Ce temps_min est porté par `equipements_proches`, `concurrents_zone`, `entreprises_zone`.
- `generateurs_flux` (arrêts de transport / pôles d'échange) sert un **COMPTE** d'arrêts, sans aucun
  temps ni distance — **non comparable** comme temps (cf. § Limites).
- Mode : l'étude de zone accepte `voiture` (profil car) ou `pied`. On traite la **voiture** (seul mode
  avec une référence gratuite fiable) et on documente le piéton (cf. § Limites).

---

## 2. Méthode

### 2.1 Échantillon stratifié — 300 parcelles

Tirage déterministe (`setseed` sur la graine partagée `verite_terrain.GRAINE`, puis
`ORDER BY random()`), **75 parcelles par strate**, 4 strates :

| strate     | règle de rattachement |
|------------|------------------------|
| **cirques**   | parcelle dans Cilaos (97424), Salazie (97421) ou Entre-Deux (97403) — communes d'accès de cirque routier |
| **Hauts**     | hors cirques, à **plus de 5 km** du trait de côte **OU** dans La Plaine-des-Palmistes (97406) / Le Tampon (97422) |
| **littoral**  | hors cirques/Hauts, à **moins de 1,5 km** du trait de côte |
| **mi-pentes** | tout le reste (entre côte et Hauts) |

**Proxy d'altitude = distance au trait de côte** (couche `spatial_layers kind='trait_de_cote'`, servie
et complète). Choix assumé : le MNT `rgealti` en base ne couvre que 2 dalles de test, pas l'île → non
utilisable comme altitude par parcelle. La distance à la côte est le proxy robuste retenu. Mafate n'a
pas de route → écarté du stratum cirques (on garde les 3 communes-cirques routières).

Résultat : **75 / 75 / 75 / 75** — N=300 atteint.

### 2.2 POI comparés

Pour chaque parcelle, on reproduit `equipements_proches` : l'équipement **le plus proche par domaine
BPE** (base permanente des équipements INSEE), dans l'isochrone 15 min servie, pour les 5 domaines :

- **A** Services aux particuliers · **B** Commerces · **C** Enseignement · **D** Santé et action
  sociale · **F** Sports, loisirs et culture.

Soit jusqu'à 5 POI par parcelle → **1473 paires** (certaines parcelles n'ont pas d'équipement dans un
domaine donné dans les 15 min).

### 2.3 Routeur de référence

- **IGN itinéraire** — `data.geopf.fr/navigation/itineraire`, resource `bdtopo-osrm`, profil `car`,
  optimisation `fastest`. Temps de trajet **point-à-point** parcelle→POI.
- **Justification** : même socle de données routières (BD TOPO IGN) que l'isochrone Valhalla servi par
  LABUSE. La divergence mesurée n'est donc **pas un désaccord de réseau routier** mais essentiellement
  la **quantification de bande** et la forme du polygone d'isochrone.
- **Limite de la référence** : un routeur reste un modèle de vitesse ; sur le même fond (OSRM/Valhalla
  donnent des ordres de grandeur comparables), les temps bruts peuvent varier de quelques pourcents. La
  règle de tolérance (§ 2.4) absorbe ce bruit.

### 2.4 Règle de verdict — consciente de la bande (`verdict_trajet`)

Le temps servi étant la plus petite bande *contenant* le POI, l'intervalle « vrai » du POI est
`]borne_inférieure ; bande_servie]` (borne_inférieure = bande précédente, 0 pour la bande 2) :

- la référence tombe **dans** `]borne_inf ; bande_servie]` → **CONFORME** (`dans_bande=oui`) ;
- sinon, à **±1 cran de bande** OU **±20 % de la bande servie** (marge pour le bruit du routeur) →
  **CONFORME** (`dans_bande=non`, conforme par marge) ;
- plus loin → **LABUSE FAUX** ;
- POI hors de l'isochrone 15 min, ou référence injoignable → **NON COMPARABLE**.

---

## 3. Résultats

**Bilan global : CONFORME 1415 · LABUSE FAUX 41 · SOURCE PLUS RÉCENTE 0 · NON COMPARABLE 17** (N=300
parcelles, 1473 paires).

Taux de conformité **sur les paires comparables** (CONFORME+FAUX, hors NC) = **97,2 %** ;
sur l'ensemble des paires = 96,1 %.
Des 1415 CONFORME, **1210 tombent strictement dans la bande** et 205 sont conformes **par la marge**
(±1 cran / ±20 %).

### 3.1 Par strate

| strate     | paires | CONFORME | FAUX | NC | taux (comparables) |
|------------|-------:|---------:|-----:|---:|-------------------:|
| littoral   | 375 | 356 | 17 | 2  | 95,4 % |
| mi-pentes  | 375 | 366 | 7  | 2  | 98,1 % |
| Hauts      | 367 | 346 | 11 | 10 | 96,9 % |
| cirques    | 356 | 347 | 6  | 3  | 98,3 % |
| **total**  | **1473** | **1415** | **41** | **17** | **97,2 %** |

### 3.2 Par mode

| mode    | paires | CONFORME | FAUX | NC | taux |
|---------|-------:|---------:|-----:|---:|-----:|
| voiture | 1473 | 1415 | 41 | 17 | 97,2 % |

Seul le mode **voiture** est comparé (cf. § Limites pour le piéton).

### 3.3 Par type de POI (domaine BPE)

| domaine | paires | CONFORME | FAUX | NC | taux |
|---------|-------:|---------:|-----:|---:|-----:|
| A · Services aux particuliers      | 294 | 282 | 8  | 4 | 97,2 % |
| B · Commerces                      | 294 | 277 | 12 | 5 | 95,8 % |
| C · Enseignement                   | 294 | 289 | 4  | 1 | 98,6 % |
| D · Santé et action sociale        | 291 | 278 | 10 | 3 | 96,5 % |
| F · Sports, loisirs et culture     | 296 | 289 | 7  | 0 | 97,6 % |

(4 paires NC sans domaine = parcelles sans aucun équipement dans l'isochrone 15 min.)

Conformité homogène (95,8 – 98,6 %) : aucun domaine n'est un point faible structurel.

---

## 4. Le sens des écarts — quasi exclusivement une SUR-estimation

Sur les **41 FAUX, 40 sont des sur-estimations** (LABUSE sert une bande **plus grande** que le temps
point-à-point de référence) et **1 seule est une sous-estimation**.

**Implication commerciale** : dans 40 cas sur 41, l'erreur est **conservatrice** — LABUSE annonce un
accès *plus lent* que la réalité ; il ne survend donc quasiment jamais l'accessibilité d'une zone. La
nuance honnête est qu'il existe **un** cas inverse (§ 4.2), et qu'il faut le signaler : l'affirmation
« LABUSE ne survend JAMAIS » est vraie à 40/41, pas à 41/41.

Répartition des FAUX par strate : littoral 17 · Hauts 11 · mi-pentes 7 · cirques 6.

### 4.1 Mécanisme de la sur-estimation (40 cas) — artefact de polygone d'isochrone

Vérifié géométriquement (ST_Contains + distance du POI au bord de chaque bande). Exemple type,
**Saint-Philippe `97417000AS0274` → école primaire** (bande servie 15, référence 3,8 min / 1291 m par
la route) :

| bande | contient le POI ? | distance du POI au bord |
|------:|:-----------------:|------------------------:|
| 2  | non | 366 m |
| 4  | non | 116 m |
| 6  | non | 52 m |
| 8  | non | 42 m |
| 10 | non | **3 m** |
| 15 | **oui** | 0 m |

Le POI est **à 3 m** du bord de l'isochrone 10 min mais n'y entre pas : il n'est capturé qu'à 15 min,
alors que le router l'atteint en 3,8 min. Les polygones sont **monopièces, non fragmentés** et
croissent normalement — ce n'est donc pas un isochrone « troué ». La cause est la **résolution /
généralisation du polygone d'isochrone** : son contour sous-atteint le long de l'axe routier précis où
se trouve le POI (POI en bout d'impasse ou sur un épi routier que le contour ne contourne pas), si bien
que `_bande_min` « saute » la bande juste et retient une bande bien plus grande. Même signature sur
**Le Tampon `97422000BR1004`** (POI 33 m hors de la bande 8, 34 m hors de la 10, pris à 15 ; ref 4,1
min) et **Le Port `97407000AE0168` → base nautique** (44 m hors de la 2, 16 m hors de la 4–6, pris à 8 ;
ref 1,1 min). **Conclusion : limite connue de la méthode de bande, pas un bug de LABUSE** — et elle joue
dans le sens prudent.

### 4.2 Le cas unique de SOUS-estimation (1 cas) — piège de topologie de cirque

**Salazie `97421000AL0373` → BFB CONSTRUCTION** : bande servie **2 min**, référence IGN **8,0 min**.
Le POI est à **~110 m à vol d'oiseau** de la parcelle et se trouve donc **à l'intérieur même de
l'isochrone 2 min** (contenu dans les 6 bandes). Mais l'itinéraire routier réel fait **1641 m** (lacets
de descente/remontée à travers la ravine, typique du fond de cirque) → **8 min**. La **containment
spatiale ≠ accessibilité routière** : le polygone d'isochrone enveloppe géographiquement un point que la
route ne dessert qu'au prix d'un long détour. **Conclusion : vraie sous-estimation servie, mais c'est
le pendant inverse du même artefact de bande, circonscrit à la topologie des cirques** — 1 cas sur 1473.
Ce point mérite d'être tracé : c'est l'unique situation où l'accessibilité servie est *optimiste*.

### 4.3 Échantillon revérifié à la main (8 paires, live IGN)

Reprise parcelle→POI, nouvel appel au service IGN espacé (ou relecture du cache `cache/trajets/ref_ign`)
— **les 8 reproduisent la valeur du CSV au dixième de minute** :

| parcelle | commune (strate) | POI | bande servie | réf. (CSV) | réf. (live) | cause |
|----------|------------------|-----|:-----------:|:----------:|:-----------:|-------|
| 97421000AL0373 | Salazie (cirques)       | BFB CONSTRUCTION    | 2  | 8,0 | 8,0 (1641 m) | **sous-estimation** réelle, détour cirque |
| 97417000AS0274 | Saint-Philippe (littoral)| école primaire      | 15 | 3,8 | 3,8 (1291 m) | POI 3 m hors bande 10, artefact contour |
| 97422000BR1004 | Le Tampon (Hauts)       | sect. enseignt pro. | 15 | 4,1 | 4,1 (1429 m) | POI 33 m hors bande 8/10, artefact contour |
| 97407000AE0168 | Le Port (littoral)      | base nautique       | 8  | 1,1 | 1,1          | POI 16 m hors bandes 4–6, artefact contour |
| 97411000IN0278 | Saint-Denis (Hauts)     | OP MECA             | 4  | 0,6 | 0,6 (270 m)  | POI très proche, contour sous-atteint |
| 97424000AE0387 | Cilaos (cirques)        | DIJOUX FLORINE      | 4  | 0,9 | 0,9 (216 m)  | POI très proche, contour sous-atteint |
| 97407000AZ0143 | Le Port (mi-pentes)     | VOGUE               | 4  | 0,2 | 0,2 (114 m)  | POI quasi mitoyen, contour sous-atteint |
| 97418000AP3315 | Sainte-Marie (Hauts)    | LE PLAT MAURICIEN   | 10 | 5,6 | 5,6 (2315 m) | POI juste hors bande voisine, artefact |

**Verdict de cause, franc** : 7/8 (et 40/41 sur l'ensemble) sont une **limite de la méthode de
quantification par bande d'isochrone**, jamais une erreur de calcul de LABUSE, et toujours dans le sens
**conservateur**. 1/8 (le cas Salazie, 1/1473) est une **vraie sous-estimation** due au fait que le
polygone d'isochrone contient géographiquement un POI que la route ne rejoint qu'après un long détour de
cirque — à signaler, bornée aux topologies de fond de cirque.

---

## 5. Limites honnêtes

- **Quantification de bande** : LABUSE ne sert pas un temps continu mais une des 6 bandes
  `(2,4,6,8,10,15)`. L'écart « temps exact vs bande » est intrinsèque au produit, pas une erreur ; la
  règle de verdict en tient compte (bande + marge). C'est la source dominante des 41 FAUX (§ 4).
- **Mode piéton non traité** : aucune référence gratuite et fiable n'a été retenue pour le profil
  piéton (OSRM/IGN piéton peu stables sur ce fond). Honnêtement laissé **non comparé** plutôt que
  comparé contre une référence douteuse.
- **Arrêts de transport servis en COMPTE** : `generateurs_flux` sert un nombre d'arrêts/pôles, pas un
  temps ni une distance → **non comparable** comme temps, donc hors de ce volet.
- **17 NON COMPARABLE** : 13 = temps de référence IGN injoignable au moment du run (service
  intermittent, échec jamais mis en cache — on ne substitue jamais une valeur inventée) ; 4 = aucune
  parcelle n'a d'équipement BPE du domaine dans l'isochrone 15 min servie (vivier réel, surtout dans les
  Hauts : 10 des 17 NC y sont). Aucun NC n'est masqué en « conforme ».
- **Routeur unique en référence primaire** : IGN `bdtopo-osrm`. Même socle que Valhalla → mesure
  surtout la quantification. Un contrôle croisé OSRM démo (`ref_itineraire_osrm`) est disponible dans le
  module mais n'a pas servi à ce run (fond OSM, utile seulement en recoupement d'ordre de grandeur).
- **Proxy d'altitude** : strates fondées sur la distance à la côte faute de MNT complet en base
  (§ 2.1) — proxy robuste mais non égal à l'altitude.
- **N=300 atteint**, 75 par strate, tirage reproductible.
