# M6 Phase 1 §1.3c — Statuts documentaires (PLU / SAR-SMVM / DPU-ZAD)

Audit LECTURE SEULE du **13/07/2026** (branche `audit/grand-check`). Méthode : base (`spatial_layers`, SELECT uniquement), API GPU (`/api/document?partition=DU_<insee>`, `/api/<insee>/procedures`, `/api/document/<id>/details`), WFS `data.geopf.fr`, web (presse locale, sites communes, MRAe, préfecture). Aucune écriture base, aucune ingestion, aucun code modifié.

Données jumelles : [`1-3c-statuts-communes.csv`](1-3c-statuts-communes.csv) (structure prête pour le futur outil « Évolution PLU » du backlog).

---

## BLOC A — Statut documentaire par commune (24)

### Synthèse

- **22 communes / 24 : document en base = document opposable**, aucune procédure approuvée postérieure au millésime ingéré (procédures GPU/Sudocuh vérifiées une à une le 13/07/2026).
- **1 commune où le document en base n'est PLUS l'opposable consolidé : Saint-Benoît** (voir vigilance n°6, nouvelle).
- **1 commune sans zonage servi par le GPU : Saint-Louis** (retrait du 10/07/2026 toujours effectif ; la base porte le dernier opposable connu).
- 1 commune en RNU confirmé : Saint-Philippe.
- La liste « PLU à recalibrer » de M5.1 reste **vide** au sens strict (aucun *millésime GPU* plus récent que la base) ; mais le cas Saint-Benoît montre la limite du critère « millésime GPU » : des **modifications simplifiées approuvées** (opposables — cf. mémoire projet, ex. Saint-André modif-1 UA) peuvent ne jamais donner lieu à un re-téléversement GPU.

Le détail commune par commune (doc, date d'approbation, idurba base vs GPU, statut d'évolution, sources, vigilance) est dans le CSV. Ci-dessous uniquement les écarts et les 5+2 vigilances.

### Mise à jour des 5 vigilances M5.1 (relevé 13/07/2026, recoupé web)

| # | Commune | État M5.1 | État au 13/07/2026 (cet audit) | Verdict |
|---|---|---|---|---|
| 1 | **Saint-Louis (97414)** | 20251218 retiré de production le 10/07, re-téléversement `not_valid` | **Toujours aucun document en production** (vérifié API). Aucune actualité contentieuse trouvée (presse, TA, jurisprudence) → panne de téléversement probable, pas un retrait juridique. Seule procédure connue : M1 approuvée 09/04/2024, déjà intégrée au millésime. | **Vigilance MAINTENUE** — re-vérifier sous quelques jours ; base = dernier opposable connu |
| 2 | **Saint-Leu (97413)** | révision en approbation imminente (visée S2 2026) | Enquête publique **lancée** (après report S1 2026) ; **avis défavorable de la commission permanente de la Région le 27/02/2026** (incompatibilités SAR) mais la ville poursuit ; approbation toujours annoncée « début S2 2026 » sur saintleu.re. **Non approuvée au 13/07/2026** — PLU 2007 opposable. | **Vigilance MAINTENUE (maximale)** — candidat n°1 au recalibrage, surveiller chaque semaine (saintleu.re + partition DU_97413) |
| 3 | **Saint-André (97409)** | révision en cours non approuvée (2e arrêt juil. 2025, avis défavorables) | **Rien de neuf** : pas d'enquête publique (impossible avant les municipales de mars 2026), pas d'approbation ; la commune doit repasser en CDPENAF. PLU 2019 opposable. | **Vigilance MAINTENUE** — approbation improbable avant fin 2026 |
| 4 | **Le Port (97407)** | `legalStatus = PARTIALLY_ANNULLED`, jugement introuvable | Statut **confirmé** en production (re-téléversement du 18/11/2025 déjà porteur du statut → jugement TA vraisemblablement entre 01 et 11/2025). Jugement toujours **introuvable** : rien sur la page décisions du TA de La Réunion, rien en presse, Pappers Justice inaccessible. | **Vigilance MAINTENUE** — action concrète : demander le jugement au greffe du TA de La Réunion avant tout recalibrage du Port |
| 5 | **Saint-Philippe (97417)** | RNU confirmé, débordements voisins | Inchangé (partition vide, PLU en élaboration DEAL). Anomalie mineure relevée : le débordement de Saint-Joseph présent en base porte l'**ancien** millésime `97412_PLU_20240320` (résidu d'une ingestion antérieure au passage de Saint-Joseph à 20251210) — sans impact scoring (hors zonage propre de la commune), à purger à la prochaine ré-ingestion. | RNU confirmé ; anomalie cosmétique consignée |

### Vigilances NOUVELLES issues de cet audit

6. **Saint-Benoît (97410) — FORTE : le document en base n'est plus l'opposable consolidé.** Le GPU (= la base) sert toujours `97410_PLU_20200206`, mais les procédures GPU/Sudocuh + le site de la ville établissent :
   - **MS n°2 approuvée le 04/07/2023** (délib. n°050-07-2023) — parcelle AK 810 en centre-ville (ancienne maternité) : levée de la servitude de projet inscrite au PLU ;
   - **MS n°3 approuvée le 04/09/2024** (délib. n°078-09-2024) — évolution du règlement en zones U et AU pour les équipements publics / CINASPIC ;
   - MAJ n°1 du 30/10/2025 (annexes) ; MS n°1 et MS n°4 (reclassement ~3,5 ha AUp→AUe, secteur Beauvallon) **en cours** ; **révision générale prescrite le 19/06/2025**.
   Ces modifications simplifiées approuvées sont **opposables** et absentes du zonage servi. Impact probablement limité (une parcelle + règles équipements publics — rien trouvé sur les hauteurs ni les OAP), mais à intégrer au calibrage Saint-Benoît (qui porte déjà la note « hauteurs prudentes »). Aucun re-téléversement GPU à attendre à court terme : la commune n'a jamais republié depuis 2020.
7. **Saint-Denis (97411) — point M5.1 précisé + révision générale en cours.** Le millésime `97411_PLU_20260423` servi (et en base) est l'approbation de la **modification simplifiée n°9** (fichier `97411_20260423_rapport_MS9_20260423.pdf` dans le dossier GPU) — pas une révision générale. La **révision générale reste en cours** (procédures Sudocuh `inProgress`, avis MRAe 2023) : un PLU entièrement refondu arrivera à moyen terme. Base à jour au 13/07/2026.
8. **Les Avirons (97401) — faible.** L'entrée Sudocuh « révision en cours » (19/12/2024) n'est pas confirmée par le web : la révision générale a été **approuvée le 06/12/2024** (millésime en base) ; l'entrée est vraisemblablement la même procédure mal clôturée. Une délibération CM du 11/03/2025 touche au PLU (objet non précisé) — à regarder au prochain point de fraîcheur.

### Écarts idurba base ↔ GPU (rappel)

Uniquement des écarts de **casse** (`plu` vs `PLU`) : Entre-Deux, L'Étang-Salé (constaté en minuscules en base à ce relevé), Sainte-Marie, Sainte-Suzanne, Cilaos, Saint-Louis — même document. Saint-André (`97409_20190228`) et Saint-Leu (`97413_20070226`) ont des idurba sans segment « PLU » car jamais issus du flux GPU (communes jamais publiées sur le GPU). Débordements géométriques normaux des voisins sous Saint-Denis, Saint-Paul, Saint-Philippe.

---

## BLOC B — SAR / SMVM

### En base ?

**Oui, mais uniquement en PROXY.** `spatial_layers kind='sar'` = 2 453 objets sur les 24 communes, construits depuis le champ `espacesar` du **potentiel foncier Région** (data.regionreunion.com, grain îlot) — ce n'est **pas** le zonage réglementaire du SAR. Subtypes : `vocation_urbaine` 1 083, `vocation_continuite` 461, `vocation_mixte` 380, `vocation_agricole` 345, `vocation_rurale` 106, `vocation_naturelle` 57, **`vocation_coupure` 21** (9 communes). Couverture surfacique : **~26 km² soit ~1 % de l'île** (les seuls îlots « à potentiel » de la Région) — les vraies coupures d'urbanisation et les espaces agricoles du SAR couvrent des surfaces très supérieures.

**SMVM : absent.** Les 6 seules occurrences « SMVM » en base sont des libellés de zones PLU (3 zones N Saint-André « espaces naturels remarquables du littoral identifiés au SMVM », 3 zones N/A Petite-Île autour de Grand Anse) — aucune couche dédiée.

### Pris en compte par le moteur ?

**Oui, en informatif assumé** (`src/labuse/cascade/layers/phase1.py`, couche `sar`, DÉCISION 2 documentée dans le code) : badge « SAR (proxy indicatif) », **zéro pouvoir d'exclusion** (jamais de HARD_EXCLUDE/SOFT_FLAG), warning de divergence quand le proxy naturel/agricole contredit une zone PLU U/AU. Hors îlot cartographié, le moteur ne conclut pas (« aucune contrainte SAR déduite automatiquement »). Le mot « SMVM » n'apparaît nulle part dans `src/` : le SMVM n'est pris en compte par aucune règle.

### Statut juridique du SAR (recherche web 13/07/2026, sourcée)

- **SAR 2011 toujours en vigueur** (décret CE n°2011-1609 du 22/11/2011). La modification « carrières » (AP du 10/06/2020) a été **annulée par le TA le 12/07/2022** → version initiale applicable.
- **Révision « SAR 2050 »** : prescrite le 22/11/2021 (délib. DAP2021_0042) ; concertation 2023-2025 ; **arrêt prévu courant 2026** (pas voté au 13/07/2026 — rencontres EPCI encore le 20/05/2026) ; **enquête publique prévue 2027** ; approbation par décret CE au plus tôt fin 2027/2028. → **Le SAR 2011 + SMVM restent la référence opposable pour l'horizon produit.** (Sources : sar.regionreunion.com/blog/3627, CESER, CIREST, reunion.gouv.fr.)

### Où trouver la donnée (backlog ingestion motivé)

Constat vérifié URL par URL : **aucun téléchargement vectoriel public direct du zonage réglementaire SAR 2011** —
- **PEIGEO** (geonetwork `peigeo.re:8080`, HTTP seulement) : fiches existantes mais sans distribution — « Destination générale des sols » = **raster** `SARapprouveDGS.tif` non téléchargeable ; couche vecteur `sar_zpu` (zones préférentielles d'urbanisation, AGORAH) avec `distributionInfo` **vide** ; 0 fiche « coupure ».
- **data.regionreunion.com** (Opendatasoft) : 0 résultat SAR/SMVM sur les 277 jeux.
- **Géo-IDE / data.gouv.fr / geo.data.gouv.fr / Géoplateforme IGN (CSW)** : 0 fiche Réunion.
- **Seul flux vivant** : WMS Sextant/Ifremer `https://sextant.ifremer.fr/services/wms/polmar_reunion`, couche `DCE_POLMAR_RUN_ERLAP_SAR2010_P` (**espaces naturels remarquables du littoral SAR/SMVM**, millésime 2011) — WMS image uniquement, pas de WFS, téléchargement fermé.
- **SMVM** : cartes 1/50 000 en PDF dans le dossier d'approbation (regionreunion.com, 403 robots) ; aucune déclinaison SIG publique hors la couche ENRL ci-dessus.

**Backlog proposé** (par ordre de levier) :
1. **Demande directe AGORAH** (`geomatique@agorah.com`, copie `region.reunion@cr-reunion.fr`) : export shapefile des couches SAR (`sar_zpu`, destination générale des sols, coupures d'urbanisation, espaces agricoles, SMVM). Les fiches PEIGEO prouvent que la donnée existe en vecteur. Voie la plus réaliste.
2. À défaut : vectorisation depuis le raster `SARapprouveDGS.tif` (à demander aussi) ou les PDF 1/50 000 — coûteux, à réserver aux coupures d'urbanisation + espaces agricoles (les deux familles qui s'imposent aux PLU et peuvent contredire une opportunité).
3. Court terme sans dépendance : garder le proxy actuel (informatif) ; éventuellement ingérer la couche ENRL WMS→(vectorisation) pour la « protection forte littorale ».
4. **Veille** : arrêt du SAR 2050 courant 2026 (sar.regionreunion.com) — le projet arrêté contiendra une nouvelle carte de destination générale des sols.

### Chiffrage demandé (croisement en mémoire, SELECT uniquement)

**Le chiffrage sur l'emprise réelle du SAR est impossible aujourd'hui** : aucune emprise vectorielle des coupures d'urbanisation / espaces agricoles SAR n'est récupérable en lecture (cf. ci-dessus ; le seul flux est un WMS image non exploitable pour un croisement parcellaire honnête).

**Minorant via le proxy en base** (run servi `m36-l2f-2026-2026-07-12`, jointure spatiale `ST_Intersects` en SELECT, aucune écriture) — parcelles scorées intersectant un îlot proxy `vocation_coupure` ou `vocation_agricole` :

| Tier | Coupure d'urbanisation (proxy) | Espace agricole (proxy) | Total |
|---|---|---|---|
| Brûlantes (119) | 2 | 4 | **6 (~5 %)** |
| Chaudes (1 032) | 10 | 23 | **33 (~3 %)** |
| Réserve foncière (4 547) | 8 | 101 | **109 (~2,4 %)** |

Communes les plus touchées : Saint-Leu (1 brûlante + 8 chaudes en coupure proxy — à rapprocher de l'avis défavorable Région sur son PLU pour incompatibilités SAR), Saint-Benoît (1 brûlante + 7 chaudes agricole), L'Étang-Salé et Sainte-Marie (4 chaudes agricole chacune).

⚠ **Lecture honnête : ce sont des minorants sévères.** Le proxy ne couvre que ~1 % de l'île ; une parcelle « hors îlot » peut parfaitement être dans une vraie coupure d'urbanisation ou un espace agricole SAR. Le chiffre réel ne pourra être établi qu'après ingestion du zonage AGORAH (backlog n°1).

---

## BLOC C — DPU / ZAD (annexes PLU)

### En base ?

**Non.** Aucune couche DPU ni ZAD dans `spatial_layers` (vérifié par kind, subtype, name, attrs). Les couches « information » du GPU n'ont été ingérées que pour le `typeinf 19` (zonages d'assainissement, 4 communes — chantier ANC). Aucune mention DPU/ZAD dans le moteur (`src/`). Rappel : la **décision 50 pas est tranchée** — la couche en base (`cinquante_pas`, 163 objets) = réserve des 50 pas géométriques, conservée ; bande 100 m loi Littoral = backlog existant, non re-questionné ici.

### Source (vérifiée le 13/07/2026) et backlog motivé

- **Standard CNIG PLU v2024** : DPU et ZAD = périmètres d'information `INFO_SURF`, **`typeinf 04`** (DPU ; `stypeinf 01` = DPU renforcé) et **`typeinf 05`** (ZAD). Numérisation **facultative** dans les annexes → couverture GPU très hétérogène.
- **Flux d'ingestion identique au typeinf 19 déjà maîtrisé** : WFS `https://data.geopf.fr/wfs`, couche `wfs_du:info_surf`, `cql_filter=partition LIKE 'DU_974%' AND typeinf='04'` (resp. `'05'`) — testé, fonctionnel, paginé. (apicarto `info-surf` fonctionne aussi mais explose >10 Mo sur Saint-Denis, sans pagination.)
- **Couverture 974 réelle au 13/07/2026** :
  - **DPU (typeinf 04) : 202 objets, 4 communes seulement** — Saint-Paul 173 (DPU + délégations par secteurs Cambaie/Barrage, centre-ville, Saint-Gilles, La Saline…), Saint-Denis 25 (dont 2 renforcés), Le Tampon 2 (renforcés), Sainte-Marie 1 (renforcé).
  - **ZAD (typeinf 05) : 5 objets, 4 communes** — Saint-Paul 2 (**ZAD Cambaie**, **ZAD Barrage**), Saint-Denis 1, Sainte-Marie 1, L'Étang-Salé 1 (« servitude d'aménagement »).
  - Saint-Pierre : rien (la **ZAD de Pierrefonds** est en cours de création côté préfecture — dossier publié sur reunion.gouv.fr, pas encore de couche SIG).
- **Autres sources : quasi nulles** — data.gouv.fr : 0 jeu DPU/ZAD Réunion ; EPCI (CINOR/TCO/CIVIS/CIREST/CASUD) et DEAL : rien d'indexé ; les DPU vivent dans les délibérations communales (PDF + plan annexé).

**Backlog proposé** :
1. **Ingestion GPU info_surf typeinf 04/05** (207 objets, 5 communes) — coût très faible (réutilisation du pattern `ingestion/anc.py`), gain immédiat : badge « périmètre DPU/ZAD » sur les fiches des communes couvertes (Saint-Paul en premier — commune premium, 173 périmètres + 2 ZAD). Intérêt métier direct : dans un périmètre DPU/ZAD, la commune peut préempter la vente — information critique pour un prospecteur.
2. **Complément manuel ciblé** (moyen terme) : vectoriser les DPU des autres communes depuis les délibérations (la quasi-totalité des communes au PLU ont un DPU sur leurs zones U/AU — le zonage U/AU donne une borne supérieure mais pas le périmètre délibéré) ; surveiller l'arrêté préfectoral **ZAD Pierrefonds** (Saint-Pierre).
3. À l'ingestion, re-balayer typeinf 04/05 à chaque republication GPU (les MS/révisions à venir — Saint-Leu, Saint-Benoît, Saint-Denis — peuvent embarquer de nouvelles annexes numérisées).

---

## Récapitulatif des verdicts

| Objet | En base ? | Moteur ? | Opposable couvert ? | Action |
|---|---|---|---|---|
| PLU (24 communes) | oui, 24/24 au millésime GPU | oui | 23/24 (Saint-Benoît : MS2/MS3 approuvées non intégrées) | vigilances 1-8 ci-dessus ; outil « Évolution PLU » nourri par le CSV |
| SAR 2011 | proxy vocation (~1 % de l'île) | informatif, zéro exclusion (DÉCISION 2) | non (zonage réglementaire absent) | backlog : demande AGORAH ; veille SAR 2050 (arrêt 2026, EP 2027) |
| SMVM | non (6 libellés PLU incidents) | non | non | inclus dans la demande AGORAH ; WMS Sextant ENRL en pis-aller |
| DPU (typeinf 04) | non | non | non | backlog : ingestion WFS GPU (202 obj., 4 communes) + délibérations |
| ZAD (typeinf 05) | non | non | non | backlog : ingestion WFS GPU (5 obj., 4 communes) + veille ZAD Pierrefonds |
| 50 pas | oui (décision tranchée) | oui | — | aucune (ne pas re-questionner) |
