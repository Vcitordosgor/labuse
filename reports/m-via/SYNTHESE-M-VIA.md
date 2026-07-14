# M-VIA — Viabilisation & raccordement (eau · assainissement · élec)

**Branche** `feat/m-via` · seed 974 · **aucun merge** · date 2026-07-14

> **Principe.** LABUSE ne peut PAS afficher le tracé des réseaux (eau/élec = données
> sensibles Vigipirate, rediffusion interdite). Ce mandat ne touche JAMAIS à cette
> donnée verrouillée : il construit le maximum LÉGALEMENT actionnable — dire *qui gère*,
> prouver la viabilisation par les **actes publics** (permis accordés à proximité), et
> estimer le coût de raccordement. **Couche de raisonnement, pas donnée brute.**
> L'indicateur est une **probabilité**, jamais une certitude ni un verrou de constructibilité.

---

## Lot 0 — Prérequis (tous VERTS)

| Prérequis | État | Détail |
|---|---|---|
| main à jour (M6.2 mergé) | ✅ | `8ef9934 merge M6.2` |
| Sitadel 2013+ en base | ✅ | `sitadel_permits` : **50 043** permis 2013→2026, **39 294 géolocalisés** (78 %) |
| Audit voirie M6 | ✅ | `spatial_layers kind='voirie'` : **235 643** tronçons, 24 communes, `geom_2975` |
| S3REnR (capacité réseau) | ✅ | `grid_capacity` : **24 postes sources** (⚠ non géolocalisés, cf. Lot 2.5) |
| BD TOPO bâti | ✅ | `spatial_layers kind='batiment'` : **817 506** bâtiments, 24 communes, `geom_2975` |

Bonus déjà en base : `parcel_zone_plu` (427 419 parcelles U/AU/A/N), `zonage_assainissement`
(258 polygones, **4 communes** seulement — SD, Le Port, SP, Étang-Salé), et un proxy réseau
**honnête préexistant** (`api/enrichment.py::networks()` — présomption proximité voirie +
renvoi DT-DICT, aucun tracé). M-VIA **formalise et score** ce proxy.

---

## Lot 1 — Mapping gestionnaires par commune

Table `commune → {compétence EPCI, opérateur eau, opérateur assainissement, EDF SEI}` pour
les **24 communes**, datée « à jour au **2026-07** », à revérifier annuellement.
Fichiers : `config/gestionnaires_via.yaml` (source de vérité) + `mapping-gestionnaires.csv`.

**Cadre (haute confiance).** Compétences eau + assainissement transférées aux **5 EPCI** le
01/01/2020 (loi NOTRe) : la commune ne détient plus la compétence → gestionnaire = EPCI (régie
communautaire) ou son délégataire (DSP/concession). **Électricité = EDF SEI partout** (ZNI, hors
Enedis). Marques : Runéo=Veolia ; CISE/Sudéau/SAUR Derichebourg=groupe SAUR ; Saphir=eau brute
(pas opérateur eau potable) ; Dionéo=CINOR+Runéo ; La Créole=régie TCO.

**Confiance** : 20/24 communes en HIGH sur les deux services. Les incertitudes portent sur des
**renouvellements 2025-2027 en cours** (concession globale CIVIS 2025, eau Le Port échue 31/12/2025,
Saint-Leu 2027), pas sur l'état actuel — signalées explicitement (`confidence: med/low`). Aucune
donnée fabriquée. Flags de contrats : CIREST→CISE unifié (roll-in échelonné 2025→2027), CASUD→Sudéau
2033, CINOR→Dionéo 2023, CIVIS concession 2025 (délégataire non confirmé).

Affichage fiche = bloc **« Gestionnaires (raccordement) »** : EPCI + eau + assainissement + SPANC +
EDF SEI, badge confiance, date, contact administratif — **aucune donnée sensible**.

---

## Lot 2 — Indicateur de viabilisation par FAISCEAU DE PREUVES

Score **0-100 + libellé** par parcelle, agrégé de 4 signaux pondérés, **calibrés sur données
réelles** (échantillon stratifié 4 000 parcelles / famille PLU, seed 974) — jamais décrétés.

### 2.1 Calibration du signal permis (le plus fort)

Le signal le plus fort : un permis **autorisé** à proximité prouve factuellement qu'on construit
ET raccorde dans le secteur. (Tous les permis en base ont une DATE_REELLE_AUTORISATION → tous
accordés ; `etat=6` = travaux **achevés**/DAACT = raccordement réalisé.)

**Distance au permis autorisé le plus proche** (mètres, EPSG:2975) :

| Zone | médiane | p75 | p90 |
|---|---|---|---|
| U (urbaine)     | 28  | 52  | 87 |
| AU (à urbaniser)| 22  | 59  | 118 |
| A (agricole)    | 116 | 221 | 372 |
| N (naturelle)   | 120 | 354 | 910 |

**Fraction de parcelles avec ≥1 permis dans le rayon R** :

| Zone | 50 m | 75 m | **100 m** | 150 m | 200 m | 300 m |
|---|---|---|---|---|---|---|
| U  | 73 | 87 | **93** | 98 | 99 | 100 |
| AU | 71 | 81 | **87** | 93 | 96 | 98 |
| A  | 23 | 34 | **45** | 60 | 71 | 85 |
| N  | 26 | 36 | **45** | 56 | 63 | 72 |

→ **Rayon primaire calibré R = 100 m** = échelle « même rue / îlot mitoyen » : capte 93 % des
parcelles U et 87 % des AU, contre ~45 % en A/N — **discriminant net**. Au-delà (≥300 m) tout le
monde a un permis → le rayon perd son pouvoir de séparation. **Comptage** retenu plutôt que binaire
(un permis isolé à 95 m est plus faible que 6 permis à 30 m) : médiane du nb de permis < 100 m =
**U 4 · AU 5 · A 0 · N 0**.

**Fenêtre N** : historique **complet depuis 2013** pour le signal de fond « le réseau existe »
(un permis achevé de 2014 prouve un raccordement durable — le réseau ne disparaît pas) ; sous-signal
de **récence (permis depuis 2022)** affiché comme « secteur en développement actif » (n'ajoute pas de
points, renforce la lecture).

### 2.2 Calibration de la façade sur voie *urbanisée*

Piège identifié : la façade sur voirie **seule** (≤ 5 m) est présente à **~75 % partout** (BD TOPO
inclut les chemins/pistes ruraux) → **non discriminante**. Le mandat exige « voie **urbanisée** » :
proxy calibré = **voirie au contact (≤ 10 m) ET bâti riverain (≤ 30 m)** = voie bordée de bâti = voie
urbanisée dont les réseaux enterrés desservent la parcelle.

| Zone | façade seule (≤5 m) | **façade urbanisée** (voie≤10 ∧ bâti≤30) |
|---|---|---|
| U  | 75 | **89** |
| AU | 71 | **77** |
| A  | 79 | **66** |
| N  | 58 | **39** |

→ le proxy « urbanisée » sépare U (89 %) de N (39 %), là où le brut était plat.

### 2.3 Calibration de l'adjacence au bâti (signal moyen)

Le bâti voisin est raccordé → réseau proche. Fraction avec bâti ≤ 10 m : **U 98 · AU 76 · A 62 · N 38**.
Bon signal moyen, surtout discriminant en zone N.

### 2.4-2.6 Modèle de score (somme = 100) et libellés

| Signal | Poids | Barème calibré |
|---|---|---|
| **S1 Permis < 100 m** | **40** | ≥6→40 · 3-5→30 · 1-2→18 · (0 mais ≥3 à 200 m)→8 · sinon 0 |
| **S2 Façade voie urbanisée** | **25** | voie≤10 ∧ bâti≤30→25 · voie≤10 seule→8 · voie≤75→4 · sinon 0 |
| **S3 Adjacence bâti** | **15** | ≤10 m→15 · ≤30 m→9 · ≤75 m→3 · sinon 0 |
| **S4 Zone PLU (fond)** | **20** | U→20 · AU→13 · A→4 · N→0 |

**Bandes → libellé** : ≥70 « **Viabilisation confirmée par les faits** » · 45-69 « **probable** » ·
25-44 « **incertaine — à vérifier** » · <25 « **lourde probable** ».

**Distribution obtenue** (validation échantillon, puis parc entier — cf. §Distribution parc) :

| Zone | moy. | confirmée | probable | incertaine | lourde |
|---|---|---|---|---|---|
| U  | 88 | 87 % | 13 % | 0 % | 0 % |
| AU | 78 | 75 % | 20 % | 4 % | 2 % |
| A  | 47 | 16 % | 34 % | 29 % | 21 % |
| N  | 31 | 11 % | 20 % | 22 % | 48 % |

**Comportement voulu** : le faisceau de preuves **prime sur l'étiquette de zone** quand les faits la
contredisent — ~16 % des parcelles N scorent « confirmée » car elles sont enclavées dans un secteur
bâti et permissionné (réseaux réellement devant). C'est la philosophie LABUSE : les faits > l'étiquette.
Inversement une parcelle U isolée peut scorer bas. **Indicateur, pas verrou.**

### Distribution sur le PARC ENTIER (431 663 parcelles, 24 communes, build 25 min)

| Bande | Parcelles | % parc | Score moyen |
|---|---|---|---|
| Viabilisation confirmée par les faits | 289 570 | **67,1 %** | 90 |
| Viabilisation probable | 74 489 | 17,3 % | 61 |
| Viabilisation incertaine — à vérifier | 35 760 | 8,3 % | 39 |
| Viabilisation lourde probable | 31 844 | 7,4 % | 12 |

Par famille PLU (parc entier — **confirme la calibration sur échantillon**, écarts < 1 pt) :

| Zone | n | moy. | confirmée | probable | incertaine | lourde |
|---|---|---|---|---|---|---|
| U  | 306 630 | 87,3 | 87 % | 13 % | 0 % | 0 % |
| AU | 10 537  | 75,4 | 71 % | 21 % | 7 % | 2 % |
| A  | 73 946  | 44,5 | 12 % | 31 % | 33 % | 23 % |
| N  | 36 306  | 36,2 | 16 % | 23 % | 25 % | 37 % |

67 % du parc « confirmée » est cohérent : 71 % des parcelles sont en zone U (déjà urbanisée et
desservie). L'indicateur ne « gonfle » pas — il reflète la réalité d'un territoire majoritairement bâti.

### 2.5 Capacité élec du poste source (S3REnR) — volet PV

⚠ **Limite honnête.** Les 24 postes sources `grid_capacity` **ne sont PAS géolocalisés** en base
(0 géométrie) et affichent **tous 0 MW** de capacité d'accueil (EDF SEI, MAJ 2026-04). Deux
conséquences : (a) impossible d'attribuer un poste par parcelle sans fabriquer une proximité fausse —
on **ne le fait pas** ; (b) le message est **uniforme à l'échelle de l'île**. → exposé comme une
**note PV de niveau île** sur chaque fiche : *« Capacité d'accueil PV nulle sur les 24 postes sources
de La Réunion (S3REnR) → toute injection PV en file d'attente réseau »*, hors du score 0-100.
**Backlog** : géolocaliser les postes sources pour une attribution par secteur (les noms — St-Paul,
Le Gol, Moufia… — sont mappables mais ne changent pas le message tant que tout est à 0).

### 2.7 Contribution tracée

La fiche montre **POURQUOI** (comme le bloc P v2) : chaque signal listé avec ses points et son détail
— ex. *« +40 Permis accordés à proximité — 10 permis < 100 m · 5 depuis 2022 · 3 achevés (DAACT) »*.

---

## Lot 3 — Estimation du coût de raccordement (qualitatif)

Dérivée du faisceau — **jamais chiffrée en euros** (trop variable) :

- **confirmée** → « Raccordement a priori SIMPLE (réseaux en façade/voirie, secteur desservi) »
- **probable** → « Raccordement probable, coût standard — à confirmer »
- **incertaine** → « Viabilisation à étudier (extension possible, surcoût) »
- **lourde** → « Extension de réseau probable, surcoût significatif »

**Rattachement zonage assainissement** (M8, où disponible — 4 communes) : parcelle en zonage **non
collectif** → « filière autonome à prévoir (surcoût + emprise) » ; **collectif** → « raccordement au
réseau à confirmer » ; en secteur peu dense sans zonage → « probable filière autonome (ANC) ».

---

## Lot 4 — Signaux publics annexes

- **Taux de desserte communal** (SISPEA/RPQS) : non ingéré ce lot — le zonage assainissement en base
  (4 communes) et les gestionnaires datés couvrent l'essentiel. **Reconnaissance** : SISPEA expose des
  indicateurs de desserte par service ; ingestion possible en backlog (pondération de fond S4-bis).
- **Schémas directeurs d'assainissement** (zones d'extension prévue) : non trouvés en open data
  exploitable ce lot — **backlog** (reconnaissance seulement, comme demandé).

---

## Architecture livrée

| Couche | Fichier |
|---|---|
| Scoring pur (poids calibrés, contributions, coût, gestionnaires) | `src/labuse/faisabilite/viabilisation.py` |
| Batch SQL (miroir exact des poids Python) | `src/labuse/faisabilite/viabilisation_build.py` → table `parcel_viabilisation` |
| CLI | `labuse viabilisation [--commune X]` |
| Config gestionnaires daté | `config/gestionnaires_via.yaml` |
| API (fiche premium) | `_viabilisation_block` + `_gestionnaires_block` dans `api/app.py` → payload `/parcels/{idu}?source=q_v*` |
| Front | `ViabilisationBlock.tsx`, `GestionnairesBlock.tsx` (dans `Fiche.tsx`) |
| Tests | `tests/test_viabilisation.py` (14, dont parité poids SQL↔Python) |

## Critères du mandat

- ✅ **Aucun tracé réseau** ingéré ni affiché (uniquement signaux déjà en base + géométries publiques).
- ✅ **Seuils calibrés et documentés** (§2.1-2.4), jamais décrétés ; aucun poids manuel non justifié.
- ✅ **Indicateur = probabilité**, jamais un verrou — le faisceau prime sur la zone, bandes lisibles.
- ✅ **Disclaimer présent partout** (« à confirmer auprès du gestionnaire / DT-DICT »).
- ✅ **Aucun merge** (branche `feat/m-via`).
