# L'Analyse LABUSE expliquée à plat

**Mandat ALGO-LECTURE-1** — audit en lecture seule, branche `audit/algo-lecture-1`.
Aucune correction, aucun accès production. Les chiffres viennent de la **base locale**,
run **servi `q_v20`** (pointeur `config/served_run.txt`), 433 229 parcelles.

Ce document explique, pour quelqu'un qui ne lit pas de code, **comment LABUSE décide**
de la couleur et des mots qu'il met sur une parcelle. Il y a **deux étiquettes** sur une
fiche, et elles répondent à deux questions différentes :

| Étiquette | Question | Valeurs |
|---|---|---|
| **Score LABUSE** | « Vaut-il la peine d'**étudier** ce terrain comme gisement de logement ? » | Excellente · Bonne · À étudier · Faible · **Non retenue** · Analyse incomplète |
| **Signal de mutation** | « Quelle est la probabilité que ce terrain **se vende** bientôt ? » | Fort · Moyen · Faible |

Le Score parle de **potentiel foncier** (la parcelle est-elle constructible, combien peut-on
y bâtir). Le Signal parle de **marché** (le propriétaire va-t-il vendre). Les deux sont
**indépendants** : aucune donnée de marché n'entre dans le Score, aucune donnée de
constructibilité n'entre dans le Signal. Le Signal ne sert qu'à **départager** des parcelles
de même bande de Score, jamais à ouvrir ou fermer une bande.

---

# Partie 1 — Le Score LABUSE

## 1.1 Ce que le Score répond, en une phrase

> « À quel point cette parcelle mérite-t-elle d'être étudiée comme opportunité foncière,
> orientée production de logement ? »
> *(`src/labuse/scoring/score_labuse.py:3`)*

Ce n'est **pas** une probabilité de vente (c'est le Signal, Partie 2). C'est un **chiffre de 0 à 100**
que l'on traduit ensuite en un **mot** (la « bande »). Le client ne voit jamais le chiffre brut,
seulement le mot et une couleur franche.

Les six bandes et leur seuil *(source unique : `config/score_labuse.yaml`)* :

| Bande (code) | Mot client | Seuil sur le score 0–100 |
|---|---|---|
| A | **Excellente** | 80 à 100 |
| B | **Bonne** | 50 à 79 |
| C | **À étudier** | 30 à 49 |
| D | **Faible** | 1 à 29 |
| 0 | **Non retenue** | exactement 0 (verdict ferme « rien à construire ») |
| NC | **Analyse incomplète** | score **non calculable** (on ne *sait* pas) |

Il existe une 7ᵉ catégorie technique, **HC (« Hors classement »)** : une parcelle que le calcul
croyait belle mais qu'une exclusion dure sort du jeu (voir §1.3). Elle est affichée à part, en fin
de liste.

Point important de doctrine : **« Non retenue » (0) ≠ « Analyse incomplète » (NC)**.
Le 0 est une **réponse** (« on a calculé, il n'y a rien à bâtir »). Le NC est un **aveu**
(« il manque une donnée, on refuse d'inventer un chiffre »). Le code met un NC plutôt qu'un 0
dès qu'une entrée critique manque *(`score_labuse.py:163-194`)*.

## 1.2 La chaîne de calcul, dans l'ordre réel

La formule tient en une ligne *(`score_labuse.py:10`)* :

```
score = clip( barème_capacité(SDP résiduelle) × coefficient_de_faisabilité , 0 , 100 )
```

Mais pour la comprendre il faut suivre l'ordre réel, en amont et en aval.

### Étape 0 — Les sources sont ingérées (avant tout score)

Avant qu'un score existe, LABUSE a rempli des caches par parcelle, chacun depuis une source
officielle *(requête `score_labuse.py:310-353`)* :

| Donnée lue | Cache | Source |
|---|---|---|
| SDP résiduelle, emprise bâtie %, cause | `parcel_residuel` | moteur de faisabilité (voir plus bas) |
| Pente moyenne | `parcel_terrain` | RGE ALTI 5 m (modèle de terrain) |
| Hauteur de bâti (faîtage) | `batiment_hauteur_lidar` | LiDAR |
| Aire, périmètre | `parcels.geom_2975` | cadastre |
| Classe AU (zone à urbaniser) | `parcel_au_statut` | PLU / GPU |
| Accès à la voie | `dryrun_cascade_results` (couche `acces`) | cascade |

### Étape 1 — La capacité résiduelle (le cœur, calculé en amont)

Le vrai travail est fait **avant** le Score, par le moteur de faisabilité
*(`src/labuse/faisabilite/residuel.py`)*. Il croise deux choses :

- la **capacité maximale** autorisée par le PLU (emprise constructible × nombre de niveaux
  permis, après reculs/retraits réglementaires) → une **SDP max** (surface de plancher) ;
- le **bâti déjà debout** (BD TOPO + LiDAR + détection ortho CoSIA) → une **SDP existante**.

```
SDP résiduelle = max( 0 , SDP max − SDP existante )
```

C'est le gisement de logement **encore disponible** sur la parcelle, bâti conservé.
Si la zone est inconstructible, si le terrain est trop exigu après reculs, ou si le bâti sature
déjà le plafond, la SDP résiduelle vaut **0**, et le moteur grave une **cause** structurée
(voir §1.3). Si une donnée critique manque, la SDP vaut **NULL** (inconnue, ≠ 0).

### Étape 2 — Le barème de capacité (points saturants)

La SDP résiduelle (en m²) est transformée en **points de capacité** par paliers
*(`score_labuse.yaml › capacite`)* :

| SDP résiduelle | Points |
|---|---|
| ≤ 0 m² | **0** |
| < 80 m² | 15 |
| < 200 m² | 35 |
| < 400 m² | 55 |
| < 1 000 m² | 75 |
| < 2 000 m² | 90 |
| ≥ 2 000 m² | **100** (plafond) |

Le barème **sature** : au-delà de 2 000 m² on ne gagne plus de points (une très grande parcelle
ne « vaut » pas 10× une bonne parcelle, elle plafonne). **Modulateur** : si la parcelle est en
**zone AU fermée / différée**, les points sont **× 0,5** (capacité réelle mais repoussée dans le
temps — jamais exclue).

### Étape 3 — Le coefficient de faisabilité (ce qui fait descendre)

Les points de capacité sont ensuite **multipliés** par un coefficient ≤ 1 qui mesure la
difficulté physique de bâtir. C'est un **produit** de quatre facteurs, avec un **plancher
global de 0,40** *(`score_labuse.yaml › faisabilite`, `score_labuse.py:263`)* — c'est-à-dire
que la faisabilité ne peut jamais couper plus de 60 % des points.

| Facteur | Déclencheur | Poids réel |
|---|---|---|
| **Pente** | pente ≤ 15 % | × 1,00 |
| | 15 % < pente ≤ 30 % | × 0,85 |
| | pente > 30 % | × 0,60 |
| **Forme** | parcelle « en lame » (largeur < 8 m **et** allongement > 8) | × 0,80 |
| | sinon | × 1,00 |
| **Accès** | voie desservante ≤ 10 m **non identifiée** | × 0,85 |
| | sinon / inconnu | × 1,00 (neutre) |
| **Bâti à démolir** | nu (emprise 0 %) | × 1,00 |
| | emprise ≤ 20 % | × 0,90 (× 0,80 si bâti ≥ R+2) |
| | emprise ≤ 50 % | × 0,80 (× 0,65 si ≥ R+2) |
| | emprise > 50 % | × 0,65 |

Deux principes **constants** dans tout le code :

- **Une donnée absente = facteur neutre 1,0, jamais un malus** *(`score_labuse.py:23`, `120`)*.
  Ne pas connaître la pente ne pénalise pas la parcelle ; ça baisse seulement sa « couverture ».
- **Le bâti n'est JAMAIS une exclusion** *(`score_labuse.py:16`)* : il pèse sur le coefficient
  (démolition à prévoir), il ne retire pas la parcelle du jeu.

### Étape 4 — Clip, puis la bande

`score = min(100, round(points × coefficient))`, puis on lit la bande dans la table du §1.1
*(`score_labuse.py:197-209`)*. Le **0 est une bande à part** (jamais confondu avec « Faible »),
le **NC n'est jamais 0**.

### Étape 5 — Le garde-fou « Hors classement » (HC)

Dernier geste *(`score_labuse_combine.py:124-135`)* : si une parcelle a une belle bande
(A/B/C/D) **mais** qu'une exclusion dure de la cascade la frappe (route, forêt publique,
domaine public fluvial, cœur de Parc…), on la bascule en **HC** avec sa raison. Cela évite
qu'une parcelle « grande + zone U » affiche « Excellente » alors qu'elle est en réalité hors
marché. Les bandes 0 et NC, déjà non retenues, gardent leur libellé.

## 1.3 Les règles d'exclusion, avec leurs seuils

Il y a **trois familles** d'exclusion, à trois endroits différents de la chaîne.

### (a) Exclusions dures de la cascade — classe A → HC

Ces couches sortent la parcelle du classement **quelle que soit** sa capacité
*(`config/cascade_v2.yaml › classes`, `config/cascade_rules.yaml`)* :

| Couche | Seuil / définition |
|---|---|
| `eau` | hydrographie (cours d'eau, plan d'eau) |
| `dpf` | domaine public fluvial (marchepied L2131-2 CGPPP) |
| `foret_publique` | forêt publique (domaine inacquérable) |
| `parc_national` | cœur de Parc National |
| `ens` | espace naturel sensible |
| `surface` | **micro-parcelle < 40 m²** |
| `emprise_routiere` / `emprise_lineaire` | emprise de voirie / délaissé linéaire |
| `pente` | **> 100 % (falaise ≈ 45°)** — en deçà (30–100 %) ce n'est qu'un coefficient |
| `trait_de_cote` | recul du trait de côte |
| `osm_faux_positif` | équipement public (faux positif géométrique) |
| **Ventilées** (A si 100 %, B si partiel) : | |
| `zonage_plu_gpu` | zone A/N inconstructible **à 100 %** → A ; 90–99 % → simple pénalité B |
| `risques` | **PPR rouge** à 100 % → A ; partiel → assiette découpée (B) |
| `prescription_plu` | ER ≥ 50 % / **EBC ≥ 80 %** → A si total, sinon B |
| `peb` | zones A/B de bruit aéroport (L112-10) |

« Ventilée » veut dire : si la contrainte couvre **toute** la parcelle c'est une exclusion ;
si elle n'en couvre qu'une partie, la portion restante est valorisée (c'est une pénalité, pas
une mort).

### (b) Causes « certaines » du moteur de faisabilité → bande 0 (« Non retenue »)

Quand la SDP résiduelle vaut **0 de façon certaine**, le moteur nomme pourquoi
*(`src/labuse/faisabilite/engine.py:343`, `cause_libelle`)*. Ces causes donnent un vrai score 0 :

| Cause | Sens | Message client |
|---|---|---|
| `zone_non_constructible:<zone>` | zone A, N, Npnr… inconstructible au PLU | « Non retenue — zone X inconstructible au PLU » |
| `terrain_exigu` | contour après reculs **vidé (< 5 m²)** *(`engine.py:20`)* | « Non retenue — terrain trop étroit » |
| `habitat_interdit:<zone>` | règlement interdit le logement (zones d'activité, UEm…) | « Non retenue — habitat interdit en zone X » |
| `redhibitoire` | contrainte rédhibitoire couvrant toute la parcelle | « Non retenue — contrainte rédhibitoire » |
| `capacite_nulle` | capacité constructible nulle au règlement | « Non retenue — capacité nulle » |

### (c) Causes « d'ignorance » → bande NC (« Analyse incomplète »)

À l'inverse, quand on **ne sait pas**, le code refuse le 0 et met un NC
*(`score_labuse.py:163-194`, `engine.py:382`)* :

| Cause | Pourquoi on ne sait pas |
|---|---|
| `zone_non_resolue` / `hors_plu` | parcelle hors du PLU outillé |
| `regle_plu_non_validee` | règle de la zone pas encore validée |
| `hauteur_indispo` | hauteur de référence manquante |
| `surface_incertaine` | plan et cadastre ne concordent pas (< moitié) |
| SDP = NULL | capacité non calculée |
| toute cause non « certaine » | filet : « Analyse incomplète » plutôt qu'un faux 0 |

## 1.4 Un exemple chiffré par bande (vraies parcelles d'Entre-Deux, `q_v20`)

Chaque ligne a été recalculée à la main avec le barème ci-dessus — les nombres **tombent juste**.

| Bande | Parcelle (IDU) | SDP résid. | Points | Coefficient (détail) | Score | Mot |
|---|---|---|---|---|---|---|
| **A** | `97403000AP1053` | 2 553 m² | 100 | pente 13,5 %→1,0 · nu→1,0 · forme 1,0 = **1,00** | **100** | Excellente |
| **B** | `97403000AR0415` | 2 075 m² | 100 | pente 15,3 %→0,85 · emprise 5 %→0,90 = **0,765** | **76** | Bonne |
| **C** | `97403000AO0174` | 547 m² | 75 | pente 16,7 %→0,85 · emprise 2 %→0,90 · accès→0,85 = **0,650** | **49** | À étudier |
| **D** | `97403000AO0451` | 249 m² | 55 | emprise 60 %→0,65 · lame→0,80 = **0,52** | **29** | Faible |
| **0** | `97403000AB0001` | 0 m² | 0 | zone `Npnr` inconstructible → points 0 | **0** | Non retenue |
| **NC** | `97403000AH0337` | — | — | `surface_incertaine` : plan ≠ cadastre | — | Analyse incomplète |

Lecture de la ligne D : 55 points × 0,65 (bâti sur 60 %, démolition) × 0,80 (parcelle en lame)
= 28,6 → arrondi **29** → juste sous le seuil 30, donc « Faible ». Une parcelle qui « rate »
« À étudier » de 1 point à cause de sa forme en lame et de son bâti.

## 1.5 Ce que ça donne en vrai (distributions `q_v20`)

| Bande | Parc entier (433 229) | Entre-Deux (6 341) |
|---|---|---|
| 0 — Non retenue | 217 954 (50,3 %) | 3 789 (59,8 %) |
| D — Faible | 99 011 (22,9 %) | 1 229 (19,4 %) |
| C — À étudier | 50 913 (11,8 %) | 626 (9,9 %) |
| B — Bonne | 36 254 (8,4 %) | 464 (7,3 %) |
| NC — Analyse incomplète | 16 272 (3,8 %) | 4 (0,1 %) |
| HC — Hors classement | 6 659 (1,5 %) | 194 (3,1 %) |
| A — Excellente | 6 166 (1,4 %) | 35 (0,6 %) |

**La moitié du parc est « Non retenue »** — c'est attendu à La Réunion (relief, zones N/A,
PPR), mais ça mérite d'être dit clairement au client (voir Partie 4).

---

# Partie 2 — Le Signal de mutation

## 2.1 Ce que le Signal répond

> « Quelle est la probabilité que cette parcelle **se vende** (mutation foncière nette L2-F)
> dans les **12 mois** ? » *(`src/labuse/scoring/signal_mutation.py:1`)*

C'est une **probabilité**, traduite en trois niveaux. Elle ne regarde **que** le marché et le
propriétaire ; elle ignore totalement la constructibilité.

## 2.2 Le modèle, en langage simple

- **Famille** : une **régression logistique régularisée** sur un **codage « Weight of Evidence »**
  (WoE), qui produit un **log-hazard additif par bloc** *(`src/labuse/scoring/p_model/model.py:1`)*.
  En clair : c'est un **« scorecard »** — chaque caractéristique de la parcelle apporte un
  nombre de points (positifs ou négatifs), on additionne, et on convertit la somme en probabilité.
  Avantage revendiqué : chaque contribution est **traçable ligne à ligne** (coef × WoE), ce qui
  alimente le bloc « Pourquoi ce score » de la fiche.
- **Cible** : la **vente L2-F** (mutation foncière nette, source DVF) dans les 12 mois suivant la
  date du score. Les ventes non-L2-F sont exclues par construction.
- **Calibration** : ajustement isotonique sur la validation 2024 ; l'intercept est recalable sur
  l'année la plus récente sans toucher aux coefficients.
- **Deux blocs de features** *(`p_model/features.py:40-141`)* :
  - **Bloc Z (le secteur / contexte)** : rotation des ventes nu & bâti sur 36 mois (DVF),
    prix médians €/m² terrain et bâti, tendance des prix, densité et part de bâti du secteur,
    indicateurs socio-économiques Filosofi (niveau de vie, pauvreté, part de propriétaires),
    pente, accès aux équipements (OSM), zone PLU.
  - **Bloc D (la parcelle elle-même)** : terrain nu-constructible, surface, sous-densité,
    **SDP résiduelle** (le même gisement que le Score !), ancienneté de la dernière mutation
    (`tenure_bin`), ancienneté du dernier permis (`permis_bin`), canopée/NDVI (végétation),
    friche.
- **Piscine et photovoltaïque sont RETIRÉS** du modèle servi : la recette **q_v15 = q_v14
  moins `piscine` et `pv_candidat`** *(`signal_mutation.py:2`)*. D'autres features sont aussi
  « retired » (permis_24m_norm, filo_dens_pop, qpv, window_coverage, dormance_droits —
  jugées instables).

**Lignée des versions** (point qui prête à confusion) : le **modèle** est la recette **q_v15**,
un artefact **gelé** entraîné sur des données ≤ 2023, calibré 2024. Le **run servi** s'appelle
**`q_v20`** : c'est le **millésime de re-scoring** (mêmes coefficients, données rafraîchies).
Donc « q_v20 » = la date de la photo, « q_v15 » = l'appareil.

## 2.3 De la probabilité au niveau : Fort / Moyen / Faible

Seuils **absolus** (aucun quota, aucun percentile) *(`config/scoring_client.yaml › paliers`,
`signal_mutation.py:29-44`)* :

| Niveau | Probabilité de vente à 12 mois | Image |
|---|---|---|
| **Fort** | p ≥ 0,20 | ≈ une chance sur cinq |
| **Moyen** | 0,10 ≤ p < 0,20 | ≈ une chance sur dix |
| **Faible** | p < 0,10 | — |

**Lien avec la carte (« paliers »/tiers).** Sur la carte-matrice, les mêmes seuils produisent
les tiers **Priorité** (≥ 0,20), **À suivre** (0,10–0,20), **Sans signal** (< 0,10), plus
**Écartée** pour les parcelles sorties avant même d'être scorées (l'« étage 0 » : les mêmes
exclusions dures que §1.3-a). Nuance de prudence importante : le tier **« Priorité » n'est
PAS servi** aujourd'hui (`PRIORITE_SERVIE = false`, `frontend/src/lib/status.ts`) — jugé non
validé. Les ancres mesurées : l'ex-tier « brûlante » servi vendait à **2 ventes sur 118**
(`qa/audit-rr/c1_monotonie.csv`, RR × 1,12, IC [0,28 ; 4,42] incluant 1), churn forward ≈ 0,51
(`FREEZE-q_v15.json`), et sur l'univers gelé des 24 communes le tier « Priorité » comptait
**0 parcelle** (précision non mesurable) ; le commentaire du code « ×0,52, 1 vente sur 111 »
est la paraphrase de l'équipe de ces mêmes chiffres. Il est affiché comme « À suivre ». Décision
d'honnêteté réversible.

Répartition réelle des tiers (`q_v20`, 433 229 parcelles) :

| Tier | n | p_raw min–max |
|---|---|---|
| sans_signal | 279 144 | — |
| **ecartee** (étage 0) | 153 283 | — |
| a_suivre | 659 | — |
| priorite | 143 | — |

Les niveaux « Fort » et « Moyen » sont donc **très rares** : à peine 800 parcelles sur 433 000.

## 2.4 Fiabilité MESURÉE — VERITE-TERRAIN-2, volet E

Source : `docs/audit-2026-10/verite-terrain-2/SIGNAL-BACKTEST.md`. **Méthode anti-fuite** : on
rejoue le modèle **gelé** (≤ 2024) sur l'**année 2025** (features connues au 01/01/2025), et on
juge sur les ventes **réellement observées en 2025** (DVF couvre l'année). L'issue 2025 n'entre
ni dans l'entraînement, ni dans la calibration, ni dans aucune feature.

- **Univers jugeable** : 429 799 parcelles, **6 488 ventes**, **taux de base = 1,51 %**.
- **Discrimination globale** : **AUC = 0,6246**, Brier = 0,0148.

**Taux de vente observé par niveau servi** (IC Wilson 95 %) :

| Niveau | n | ventes | taux observé | IC 95 % | lift vs base |
|---|---:|---:|---:|---|---:|
| **Fort** | 100 | 39 | **39,0 %** | [30,0 ; 48,8] | **× 25,8** |
| **Moyen** | 425 | 62 | **14,6 %** | [11,6 ; 18,3] | × 9,7 |
| **Faible** | 429 274 | 6 387 | 1,49 % | [1,45 ; 1,52] | × 0,99 |

**Par décile de probabilité** (le test de monotonie) : le décile le plus probable vend à
**3,45 %** (lift × 2,29, IC [3,28 ; 3,63] — sans recouvrement avec la base), contre 0,73 % au
décile le plus bas. La montée est globalement croissante (quelques inversions de rang dans les
déciles bas = bruit d'échantillon).

**Précision@K** (si on ne garde que les K mieux notées) : @100 → 39 %, @500 → 19,4 %,
@1 000 → 14,1 %, @2 000 → 11,05 %.

**Verdict honnête du rapport, repris tel quel** : *le signal sépare réellement, mais modérément*.
Un AUC de 0,625 est une discrimination réelle mais modeste, cohérente avec un **événement rare**
(1,5 % de base). Là où le Signal brille (« Fort », × 25,8), il ne couvre que **100 parcelles** —
l'intervalle de confiance y est large. Le gros du parc (« Faible ») vend au taux de base : le
Signal n'y apporte **rien**, ce qui est normal — sa valeur est d'**isoler la petite tête**.

**Limites consignées par l'équipe (à garder en tête) :**

1. **Le millésime réellement servi n'est pas jugeable « forward » aujourd'hui** : les runs servis
   (oct. 2026) sont postérieurs à la dernière mutation DVF (31/12/2025). On a jugé **le modèle**
   (rejeu 2025), **pas l'instantané livré au client**. Un protocole forward est écrit pour quand
   DVF aura avancé.
2. Niveaux Fort/Moyen **peu peuplés** → IC larges ; la robustesse vient des déciles et de
   precision@K.
3. Cible **L2-F** uniquement (ventes foncières nettes).

---

# Partie 3 — Les « Non retenues » d'Entre-Deux

## 3.1 Combien, et de quoi parle-t-on

« Non retenue » = la **bande 0** du Score LABUSE (score exactement 0, verdict ferme « rien à
construire »). Sur Entre-Deux (INSEE 97403, 6 341 parcelles), run `q_v20` :

> **3 789 parcelles en bande 0** — soit **59,8 %** de la commune.

*(Le mandat cite « 3 781 » ; l'écart de 8 tient à un recalcul du run — je rapporte le chiffre
exact mesuré ce jour sur `q_v20`. À part : 194 parcelles « Hors classement » et 4 « Analyse
incomplète », qui sont d'autres formes de non-rétention, hors de ce décompte.)*

## 3.2 Répartition par raison d'exclusion

Chaque parcelle bande 0 a été croisée avec la **cause** gravée par le moteur
(`parcel_residuel.cause`). Trois familles, et **rien d'autre** :

| Raison | Parcelles | Part | Nature |
|---|---:|---:|---|
| **Zone inconstructible au PLU** (`zone_non_constructible`) | 2 465 | 65,1 % | verdict ferme |
| **Terrain trop exigu** (`terrain_exigu`) | 715 | 18,9 % | verdict ferme |
| **Bâti saturé** (cause vide, SDP calculée = 0) | 609 | 16,1 % | déjà construit au max |
| **Total** | **3 789** | 100 % | |

Détail de la 1ʳᵉ famille (zones) : A (agricole) 871, N (naturel) 850, Npnr (parc national) 363,
Nr 333, Aba 35, et quelques micro-zones (Nstep, AUst, Nci).

## 3.3 Trois parcelles tirées au hasard par raison, avec la preuve

Tirage reproductible (`ORDER BY md5(idu)`), preuve = données indépendantes (zone PLU portée par
la cause, surface réelle `ST_Area`, emprise bâtie mesurée).

### Raison 1 — Zone inconstructible au PLU

| IDU | Zone (cause) | Surface réelle | Preuve que l'exclusion est juste |
|---|---|---|---|
| `97403000AN0088` | A (agricole) | 499 m² | zone **agricole** : pas de logement, correct |
| `97403000AI0002` | Npnr (parc national) | 32 963 m² | **cœur de Parc National** : inconstructible, correct |
| `97403000AS0278` | Nstep (station d'épuration) | 202 m² | zone **naturelle d'équipement** : correct |

→ **Exclusions justes.** La zone PLU est une donnée réglementaire opposable ; une parcelle A ou N
n'accueille pas de logement, par le règlement lui-même.

### Raison 2 — Terrain trop exigu

| IDU | Surface réelle | Preuve |
|---|---:|---|
| `97403000AO0519` | **52 m²** | minuscule : après reculs il ne reste rien de constructible, correct |
| `97403000AP0237` | 245 m² | petit : le contour inséré est vidé, plausible |
| `97403000AP1395` | 433 m² | contour après reculs < 5 m², à vérifier au cas par cas |

→ **Justes pour les petites parcelles.** Mais cette raison a un **angle mort** sérieux (voir §3.4).

### Raison 3 — Bâti saturé (cause vide, SDP = 0)

| IDU | Emprise bâtie | Surface | Preuve |
|---|---:|---:|---|
| `97403000AP1634` | **158 %** | 188 m² | le bâti dépasse déjà le plafond d'emprise : plus de droits, correct |
| `97403000AS1521` | **123 %** | 212 m² | bâti au-delà du plafond PLU, correct |
| `97403000AP1673` | **102 %** | 222 m² | emprise saturée, correct |

→ **Exclusions justes** : ces parcelles sont « déjà construites au maximum » (emprise moyenne de
la famille : **188 %** du plafond, 470 des 609 au-dessus de 100 %). Le message juste serait
« déjà bâti au maximum — démolition/reconstruction », plutôt qu'un silence.

## 3.4 Raisons qui me paraissent discutables

**(A) `terrain_exigu` sur de GRANDES parcelles — le plus gênant.**
Le test d'« exiguïté » ne porte **pas** sur la surface de la parcelle, mais sur le **contour
inséré après reculs** (vidé si < 5 m², `engine.py:20`). Résultat : sur les 715 `terrain_exigu`
d'Entre-Deux, **166 font plus de 1 000 m²**, et le plus grand fait **113 832 m² (11,4 ha)**,
avec une largeur moyenne de **62 m** — tout sauf « étroit ».

| IDU | Surface | Largeur approx. | Libellé affiché |
|---|---:|---:|---|
| `97403000AL0258` | **113 832 m²** | 62 m | « terrain trop étroit » |
| `97403000AO0297` | 56 099 m² | 97 m | « terrain trop étroit » |
| `97403000AR0994` | 41 484 m² | 90 m | « terrain trop étroit » |

Ces parcelles ont des **contours très découpés** (périmètre 3 à 4× celui d'une forme compacte :
ravines, concavités). L'exclusion est peut-être **mécaniquement correcte** (le contour utile est
réellement vidé par les reculs sur une géométrie tourmentée), mais **le mot est faux** et masque
la vraie cause. Un propriétaire d'une parcelle de 11 ha à qui on dit « terrain trop étroit » n'y
croira pas — et aura raison de douter. **À investiguer** : s'agit-il d'un recul trop agressif, d'un
artefact géométrique, ou d'un vrai terrain inexploitable ? Le libellé ne permet pas de trancher.

**(B) Les 139 « bâti saturé » à emprise < 100 %.**
Parmi les 609 cause-vide, **139 ont une emprise bâtie INFÉRIEURE à 100 %** (ex. 75–96 %) tout en
ayant une SDP résiduelle de 0. C'est **plausiblement juste** (un bâtiment à plusieurs niveaux peut
consommer toute la SDP max alors que son emprise au sol reste sous le plafond), mais c'est
**opaque** : la cause est **vide**, aucun message n'explique au client pourquoi un terrain bâti à
76 % est « Non retenue ». Le Score devrait nommer cette cause (« SDP déjà consommée en hauteur »).

**(C) La frontière 0 / NC repose entièrement sur la justesse de la donnée amont.**
Une zone mal résolue bascule en NC (bien), mais une zone **mal classée comme A/N** (erreur de
couche PLU) deviendrait un « Non retenue » définitif et **silencieux**. La qualité de la couche
GPU/zonage est donc un point unique de confiance pour 65 % des Non retenues d'Entre-Deux.

---

# Partie 4 — Faiblesses de l'algorithme (ma liste, sans correction)

Classées par importance. Aucune n'est corrigée — ce sont des constats d'audit.

1. **Le libellé `terrain_exigu` ment sur les grandes parcelles** (§3.4-A). 166 parcelles > 1 000 m²
   (dont une de 11 ha) affichent « terrain trop étroit ». Le test porte sur le contour après
   reculs, pas sur la taille ; le message devrait dire *pourquoi* le contour est vidé. Risque de
   perte de confiance client sur des cas visiblement faux.

2. **Le Score et le Signal partagent une entrée (la SDP résiduelle), ce qui crée une
   corrélation cachée.** La SDP résiduelle est à la fois le **cœur du Score** et une **feature du
   Signal** (bloc D). Les deux étiquettes sont vendues comme « indépendantes » (foncier vs marché),
   mais elles bougent ensemble via cette variable commune. Ce n'est pas faux, c'est **non dit**.

3. **Fiabilité du Signal réelle mais modeste, et jamais mesurée sur le millésime servi** (§2.4).
   AUC 0,625. Le niveau « Fort » (× 25,8) ne repose que sur **100 parcelles**. Et le backtest juge
   *le modèle rejoué sur 2025*, pas *l'instantané livré en octobre 2026* — par construction, on ne
   peut pas encore prouver que le produit servi tient. Le protocole forward existe mais n'a pas
   encore tourné.

4. **Barème de capacité « saturant » qui écrase le haut du marché.** Au-delà de 2 000 m² de SDP
   résiduelle, tout plafonne à 100 points. Une parcelle à 2 100 m² et une à 20 000 m² sont
   « égales » côté capacité. Pour un acteur du logement collectif, c'est une perte d'information
   réelle (le gisement décuple, le score non).

5. **Seuils et poids « gravés » mais peu calibrés.** Les coefficients de faisabilité (0,85 / 0,80 /
   0,65…) et les seuils de pente (15 / 30 %) portent des commentaires « NON CALIBRÉ » dans la
   config (`cascade_rules.yaml:229`). Le barème de bande a été « gravé à l'identique » sur
   **30 parcelles témoins** (`score_labuse.yaml`), ce qui valide l'ordre mais pas finement les
   frontières. Un terrain à 29 vs 30 (§1.4, bande D vs C) bascule sur des poids non mesurés.

6. **La moitié du parc est « Non retenue » sans nuance d'échéance.** 50,3 % du parc (59,8 % à
   Entre-Deux) tombe en bande 0. C'est factuellement correct, mais mélange des réalités très
   différentes (zone N définitive vs bâti saturé démolissable vs terrain exigu douteux) sous un
   seul mot froid. Le détail existe en cause mais la bande les aplatit.

7. **Causes « vides » non expliquées** (§3.4-B). 609 parcelles « Non retenue » à Entre-Deux ont une
   cause vide ; le client voit « aucune SDP résiduelle exploitable » sans savoir si c'est de la
   saturation (actionnable par démolition) ou autre chose.

8. **Dépendance à une seule donnée pour 65 % des exclusions** (§3.4-C) : la couche de zonage PLU.
   Une erreur de classement A/N y produit un « Non retenue » définitif et silencieux, sans le
   garde-fou NC qui protège les zones *non résolues*.

9. **Le tier « Priorité » du Signal est désactivé** (`PRIORITE_SERVIE = false`) faute de
   validation. C'est une décision d'honnêteté, mais cela veut dire que la **tête la plus chaude du
   marché est repliée dans « À suivre »** : le produit sous-affiche volontairement son meilleur
   signal. À assumer ou à re-valider.

10. **Dette de millésime entre Score et Signal.** Le Score lit `parcel_residuel` (recalculé par
    run), le Signal lit un modèle gelé q_v15 re-scoré en q_v20. Si les deux caches ne sont pas
    rafraîchis au même instant, une fiche peut afficher un Score et un Signal **de dates
    différentes** sans que rien ne le signale à l'écran.

---

*Fin du document. Audit en lecture seule — aucune donnée de production touchée, aucune valeur
d'algorithme modifiée.*
