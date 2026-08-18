# LA DALLE — FONDATION DE L'ALGORITHME LABUSE

*Document de référence. Toute construction de l'algo s'y conforme ; tout
écart s'y arbitre et s'y écrit. Décisions de Vic, 18/08/2026.*

---

## 1. Ce que l'algorithme est

**UN score unique, pour tous les clients : la probabilité de vente sous 1 an.**
*(Fenêtre confirmée par l'audit du calcul : mutation L2 sous 12 mois.)*

- Pas de profils métier (promoteur/bailleur/lotisseur) : le client exprime
  son intention par SES FILTRES (le cadrage M120). Un lotisseur coche
  « terrain nu » — le produit n'a pas besoin de savoir qu'il est lotisseur.
- Pas de note fondue multi-critères : un score qui mélange deux questions
  ne répond plus à aucune. La valeur du lieu, la charge foncière, la
  surface sont des FAITS AFFICHÉS, triables, jamais fondus au score.
- Le nom servi au client : « probabilité de vente sous 1 an » — jamais de
  jargon (« mutabilité », « hasard », « q_score » sont morts à l'écran).
  Le produit présente par tier + rang + raisons ; le pourcentage brut
  n'est pas servi (saturation isotonique aux extrêmes).
- Référence marché : Reonomy « Likely to Sell » (54M propriétés, US) —
  même architecture : filtres client + un score unique + faits à côté.

## 2. L'architecture en couches

| Couche | Rôle | Chez LABUSE |
|---|---|---|
| 0 | Feature store | UN run unique, versionné, daté — tous les juges lisent la même donnée |
| 1 | Candidate generation | LA CASCADE : exclusions dures, chacune avec son motif |
| 2 | Scoring | LE SCORE UNIQUE : probabilité de vente sous 1 an + reason codes |
| 3 | Policy | Le cadrage client (filtres M120) — pas de profils |
| 4 | Présentation | Score + raisons + faits affichés ; jamais une note opaque |

### Les juges actuels — leur sort

| Juge | Sort |
|---|---|
| Cascade / étage 0 | RESTE — seule à dire « écartée », avec motif |
| Modèle de hasard (parcel_p_score_v2, artefact m36-l2f-2026) | DEVIENT le score unique — renommé |
| Matrice (412 579 « écartées ») | MEURT — fusionne dans la cascade |
| Tier v2 (354 355 « écartées ») | MEURT comme statut servi |
| q_score | MORT (retiré de l'écran M120 ; meurt du code) |
| Charge / bilan à rebours | FAIT AFFICHÉ — ne vote pas, ne meurt pas |
| Prix marché (DVF local) | FAIT AFFICHÉ — le marché juge le lieu, on l'affiche |
| Les deux runs (q_v9_m81 / q_v8_calibre) | UN SEUL run |

### Règles de véracité (doctrine appliquée à l'algo)

- « Écartée » a UNE définition : exclue par la cascade, motif dit.
- Un statut interne ne se sert jamais nu (leçon « qualité 78/100 »).
- `faux_positif_probable` : 181 484 parcelles bâties ne sont pas des
  « faux positifs » — l'étiquette se corrige à la refonte cascade.
- Chaque compteur nomme son univers (leçon du 431 663 → 60).
- Monotonie testée en golden : améliorer un facteur ne dégrade jamais le
  score, toutes choses égales.
- Reason codes : le score sort avec ses 2-3 raisons dominantes, en clair
  (le mécanisme libelles_client existe — il se garde).
- Les copropriétés (taux de mutation 29 % vs 1,52 %) restent classées À
  PART, jamais mélangées au rang foncier (finding M36).

## 3. La cascade cible (arbitrages du 18/08)

**La cascade n'exclut que l'impossible LÉGAL ou PHYSIQUE.** Tout ce qui
n'est que cher, compliqué ou négociable est VISIBLE, scoré, avec le fait
affiché.

### Restent en cascade
Parc national (cœur) · PPR rouge (INTERDICTION — le bleu est déjà visible)
· eau/ravines · forêt publique · zonage N/A strict · emprises
routières/équipement · trait de côte · 50 pas géométriques · prescriptions
gelantes (corridor, périmètre d'attente).

### Sortent de l'exclusion (deviennent visibles, scorés, filtrables)
| Motif libéré | Volume | Devient |
|---|---|---|
| Bâti « faux positif » | 181 484 | visible — facette nu/bâti décide |
| Bâti saturé (SDP nulle) | 13 725 | visible — fait « droits résiduels : non » + facette |
| Foncier public négociable (seul motif) | 11 468 net | visible — proprietaire_type étendu « public » |
| Micro-parcelles 40-100 m² | 9 085 net | visible — plancher 40 m² en config |
| Emplacements réservés (ER) | 2 147 net | visible — fait affiché « ER » |
| Pente 31-45° | 797 net | visible — seuil falaise 45° en config |

**Vivier : 90 911 → 111 371** (confirmé, audit cascade-decoupes).
Sous-zones N/A (STECAL/hameaux, ~1 100) : calibration commune par commune
plus tard, non bloquant.

### Dettes cascade à régler à la refonte
- Seuils en dur (bati.py, etage0_ext.py) → config ; 6 PLACEHOLDER à
  calibrer.
- Porte latente INNER JOIN (app.py:1949/2125) : garde-fou « évaluées =
  431 663 » en golden.
- OCS GE = proxy BDCARTO : gardé, marqué « à remplacer si natif publié ».

## 4. Les sources du score — recensement arbitré

### DEDANS — les 11 actuelles (validées ensemble, RR@1158 hors copro 6,73)
DVF (cœur) · SITADEL · PLU/GPU · BD TOPO · pente MNT 5 m · Filosofi ·
OSM accès · Cartofriches* · LiDAR canopée · BD ORTHO piscine · NDVI.
*(friche est morte dans l'artefact servi — IV≈0 : sort au ménage M127,
la source reste en cascade/affichage.)*

Aucun retrait sans mesure : un doute sur une feature = « à re-tester au
réentraînement », jamais une coupe à l'instinct.

### AU TEST M127 — les 4 signaux propriétaire
| Signal | Volume | Attendu |
|---|---|---|
| BODACC procédures | 1 418 (+678 réingérés M124) | fort, rare |
| Successions / indivisions | 7 129 | le meilleur candidat |
| Âge dirigeant (INPI RNE) | 9 730 | transmission proche |
| PM nue dormante (DGFiP) | 82 701 | seul volume significatif |

Bonus quand présents (~2-4 % du parcellaire) — JAMAIS la fondation.

### AU TEST M127 — les 4 candidates nouvelles (ajout 18/08 soir)
- **Division cadastrale récente** (division_or la détecte déjà) — un
  découpage = un lotisseur au travail.
- **Contagion de voisinage** — part des voisins directs vendus sous 24
  mois (DVF + géométries ; plus fin que la rotation secteur).
- **Vente « terrain à bâtir » à proximité** — nature DVF existante.
- **Permis enrichi SITADEL** — type (PC/DP) et état (accordé / commencé) ;
  un PC accordé jamais commencé est un signal de vente classique.
  (permis_bin actuel est de facto binaire « < 2 ans ou pas ».)

### DEHORS — décisions fermes
- DPE passoire : 2 cas sur l'île — rien à apprendre (rouvrable si la base
  DROM grandit).
- Toutes les exclusions restent en cascade, hors score.
- Tout le contexte reste en affichage/filtre (BAN, IRIS, fiscal, GTFS,
  PLH, SRU, NPNRU...). Cas limites notés : GTFS (doublon partiel accès
  OSM), SRU (communal, trop grossier).

## 5. Le modèle — état des lieux et corrections décidées

**L'existant (audit score-calcul, artefact m36-l2f-2026)** : régression
logistique L2 + WoE + calibration isotonique. 29 features (7 mortes ou
retirées encore servies), 5 croisements, effets d'année. Train 2017-2024,
calibré 2025. RR@1158 hors copro = 6,73 (fold 2025). Dérive : 11× (2020)
→ 6,7× (2025).

**Corrections arbitrées (18/08 soir)** :
1. **Profondeur DVF 2014-2025 ACQUISE (M124)** : archives 2014-2020 en base
   (dvf_mutations_histo, 48 742 mutations, source cquest LO 2.0, URL par
   ligne) ; frontière 2020/2021 sans recouvrement (prouvé) ; catalogue dit
   la profondeur. Tenure connue 8,6 % → 17,1 %. **Clamp 2021 des features
   à lever au réentraînement M127.** Éditions : vérification M124 — seule
   2015 était rafraîchissable (éd.201910→202004, +10 mutations, exécuté) ;
   2014/2016-2020 étaient déjà à leur dernière édition année-pleine (les
   éditions d'octobre ne portent l'année la plus ancienne qu'en semestre 2).
2. **Ménage** : les 7 features mortes/retirées sortent physiquement au
   réentraînement.
3. **Trou parcel_residuel : BOUCHÉ (M125)** — 100 % des parcelles ont une
   ligne : 253 764 calculées + 177 899 avec cause structurée (sdp=0 vrai :
   zone_non_constructible/terrain_exigu/… ; NULL dit : hors_plu 4 397 =
   1,0 %). Le bin « manquant » passe de 38,9 % à ~1 % au dataset M127.
   Lecteurs vivants gardés (cause IS NULL) — invariance des filtres prouvée,
   golden 0 FAIL.
4. **Pondération des années récentes** à l'entraînement + **cadence de
   réentraînement annuelle** gravée.
5. **Mesure par segment au M127** : RR séparé sur le segment bâti (le
   vivier cible inclut 181k bâties — si le RR s'y effondre, features bâti
   à prévoir).
6. **Challenger GBM** en annexe du M127 : même walk-forward, comparaison
   chiffrée — la régression reste si l'écart ne justifie pas de perdre
   l'explicabilité.

## 6. La méthode de construction

1. La donnée d'abord, le moteur ensuite : M124 (profondeur DVF) → M125
   (parcel_residuel) → M126 (colonnes des candidates) → M127 (LE
   réentraînement, STOP rapport) → M128 (promotion + run unique +
   renommage) → M129 (cascade cible + mort des juges + restitution).
2. Un run unique produit tout (features, cascade, score) — même millésime.
3. Les golden de monotonie s'écrivent AVANT le nouveau modèle.
4. L'examen (walk-forward) est le seul juge de promotion : le nouveau
   modèle remplace l'ancien si et seulement si sa note dépasse 6,73 dans
   les mêmes conditions de mesure.

## 7. Préalables — état au 18/08 soir

- [x] Réingérer BODACC + BAN (fait M124 Phase 0 ; cron radar réparé au
      passage — il plantait chaque lundi)
- [ ] Cadence de la « grande passe » manuelle fixée et écrite
      (proposition : trimestrielle)
- [ ] Merger les branches d'audit restantes
- [ ] Mandat BPE/ZNIEFF (ingesters à bâtir) — « BPE remplace ou complète
      OSM ? » se tranche au réentraînement
- [ ] Vérif PPR côté DEAL (producteur non datable — geste dédié)
