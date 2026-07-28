# MANDAT PLU-SAINT-PIERRE — RAPPORT (PILOTE)

> Instance pilote du mandat-cadre « re-gravure des règles chiffrées de faisabilité ».
> Livrable principal : le verdict d'industrialisation (§3-§6) et le verdict de schéma (§8),
> pour décision de Vic avant la commune n°2.

Exécution : Claude Code (Fable), session du 27/07/2026. Branche `feat/plu-saint-pierre`.

---

## 1 · Source et concordance (Point d'arrêt A — validé GO)

| | |
|---|---|
| Document | Eco-PLU de Saint-Pierre, règlement écrit 227 p., « Version d'approbation – Juin 2024 » |
| idurba | `97416_PLU_20240625` — **identique** au zonage servi (manifeste + `spatial_layers`, 285 zones) |
| Statut GPU | EN VIGUEUR, aucune procédure en cours (vérifié 27/07/2026) |
| Fichier | `data/reglements/97416_reglement_20240625.pdf` (extrait de l'archive GPU de 987 Mo, téléchargement automatique) |
| Offset pages | 0 (page PDF = page imprimée, vérifié) |

## 2 · Couverture obtenue

45 libellés GPU distincts au zonage. Couverture par le YAML `config/plu_saint_pierre.yaml` :

| Catégorie | Libellés | Pool servi couvert |
|---|---|---|
| **Calibrées, habitat admis** (10) | Ug, AUg, Uf, UfCA, AUf, AUfGB, Ud, UdBO, Udl, Ucv, Up | ~7 350 parcelles (>93 % du pool) |
| **Calibrées, habitat interdit au règlement** (15) | Uaza, Uazc, Uazi, Uazp, Uazpc, AUazc, AUazi, Ue, Uea, Uep, Uemi, Ut, AUt1, AUt2 | ~310 — verdict « habitat interdit », zéro capacité logement |
| **Calibrées, construction neuve non autorisée** (5) | Us (gel SCoT), AU01, AU02, AU03, AU0c-1 | ~192 — verdict « non autorisé », zéro capacité |
| **Non calibrable par nature** (1) | AUdma (R151-8 : régie uniquement par les OAP) | 11 — repli estimation générique, motif cité |
| **Non calibrées — décision motivée** (14) | A, Ac, Ac1, Acu, Acu1, At, N, Nc, Nci, Ncu, Nge, Np, Npnr, Nr | ~90 — repli générique → non constructibles (verdict correct) |

**Décision A/N (cadrage GO n°1)** : chapitres A (p.202-211) et N (p.212-221) lus. La constructibilité
y est d'exception uniquement — zone A : logement strictement réservé à l'exploitant agricole
(1 seul par exploitation, 150 m² SDP max, Art. A1), extensions ≤25 % ; zone N : extensions ≤25 %,
carrières (Nc), équipements de parcs (Np/Nge). Les hauteurs des chapitres (A : 4/7 m ; Ac/Ac1 :
25 m ; N : 6/9 m) encadrent ces exceptions, pas une constructibilité logement ordinaire. Les graver
ferait calculer une capacité logement fictive étiquetée « Sourcé » — le pire faux positif. Le repli
générique classe déjà tout préfixe non-U/AU non constructible : c'est le verdict produit correct.
**Aucune zone A/N n'est gravée.**

**Zéro valeur non sourcée** : chaque champ chiffré porte article + page ; les cas ambigus sont en
`a_verifier` avec citation ; les « non réglementé » sont en `null` avec citation.

## 3 · Temps réel MESURÉ (PILOTE — §7.1, corrigé en revue GO n°3)

> Correction demandée par Vic : mesure aux horodatages, pas estimation. Les commits de lot ne
> sont pas encore posés (porte golden en attente de la libération de la base partagée) — la
> chronologie ci-dessous est celle des ARTEFACTS (reflog de branche, mtimes des snapshots de
> lot et livrables), tous du 27/07/2026 :

| Horodatage | Jalon |
|---|---|
| 19:03:34 | Création de la branche (`git reflog`) — début effectif du mandat |
| 19:11:51 | Archive GPU 987 Mo téléchargée (Point A : concordance + inventaire pool faits entre 19:04 et 19:11) |
| ~19:15 | Rapport Point d'arrêt A rendu → GO Vic |
| 19:21:21 | Texte intégral du règlement extrait (étude du schéma faite en parallèle) |
| 19:31:11 | Snapshot lot UG gravé |
| 19:33:45 | Snapshot lot UF+UD gravé |
| 19:51:49 | Snapshot final : 45 libellés couverts (26 entrées + gels + décisions A/N) |
| 19:53:22 | Règlement Le Tampon téléchargé (sondage hétérogénéité) |
| 20:18:12 | Rapport rédigé (1re version complète hors sections DB) |

**Mesures :**
- **Point A : 12 min** (dont ~3 min de téléchargement).
- **Étude schéma + moteur : ~10 min** (ne se répétera pas en série).
- **Extraction des 45 libellés : 27 min** (19:25→19:52), vérifications smoke incluses.
- **Sondages + audits + rapport : ~35 min.**
- **Total travail effectif début→rapport : ~1 h 15.** Le « ~4 h » annoncé initialement était
  une SURESTIMATION (il agrégeait les allers-retours de revue avec Vic et l'attente).
- **Part d'attente subie** (verrous de la base partagée — job O12 + un ALTER tiers ;
  exécutions longues) : elle domine le calendrier de la CLÔTURE (golden/échantillon toujours
  en file au moment de cette mise à jour) mais a été massivement recouverte par du travail
  utile (rapport, audits fraîcheur, sondages) — temps PERDU net estimé < 15 min.
- **Commits de lot (posés à la libération de la base, golden 116/116 entre chaque)** :
  `5b865b5` lot 1 (UG) 20:49:31 · `613778d` lot 2 (UF+UD) 20:49:52 · `f4a114f` lot 3
  (le reste, 45/45 libellés) 20:50:28. L'écart de quelques secondes entre commits mesure la
  mécanique commit+swap — les golden (3 runs complets, ~3-4 min chacun API comprise) et la
  validation §7 occupent 20:33→20:50. **Premier jalon → dernier commit de contenu :
  19:03 → 20:50 (1 h 47 bout-en-bout), dont ~40 min d'attente de base (job O12, 19:55→20:33)
  presque entièrement recouverte par les revues GO et les audits.**

**Conclusion franche : le vrai coût d'extraction d'une commune au format moderne est de
l'ordre de 40 minutes, pas de 2 h 20.** Mes premières fourchettes étaient prudentes d'un
facteur 2 à 3.

## 4 · Manuel vs automatisable (§7.2)

Le règlement de Saint-Pierre (format moderne 2024) est **remarquablement régulier** :

**Structuré, extractible mécaniquement (~70 % du travail)** :
- 1 chapitre par zone, toujours les mêmes sections : Art. <Z>3.1 (voies), 3.2 (limites),
  3.4 (emprise), 3.5 (hauteur), 5.1 (CBS/pleine terre), 6 (stationnement, tableau).
- Formulations quasi identiques d'un chapitre à l'autre (copié-collé municipal) : les
  « dispositions particulières » (EDF 1 m, piscines libres, PPRN, pente +1,5 m) se répètent mot pour mot.
- Les hauteurs sont toujours « X m à l'égout/acrotère et Y m au faîtage » → mapping he/hf direct.

**Lecture juridique indispensable (~30 % du travail, mais c'est là que sont les pièges)** :
1. **Tableaux de destinations** (Art. <Z>1) : c'est là que se joue `habitat: interdit` — 15 des
   31 libellés gravés. Un « Logement V* » avec condition « présence permanente nécessaire »
   = habitat interdit produit ; un extracteur naïf lirait « V\* = autorisé ».
2. **Préambules** : le gel provisoire de Us (SCoT), le statut R151-8 d'AUdma, la condition
   d'aménagement d'ensemble des AU — AUCUNE de ces informations n'est dans les articles chiffrés.
3. **Règles à tiroirs** (emprise/pleine terre par tranche de surface) : le choix de la tranche à
   graver exige de croiser avec la distribution du pool servi (requête DB, décision documentée).
4. **Hauteurs minimales** (Ud « entre 6 et 15 m », Ucv « entre 9 et 15 m ») : un extracteur qui
   prend « le premier nombre » grave 6 au lieu de 15.

## 5 · Verdict d'industrialisation (§7.3)

**OUI, une extraction assistée est viable, avec un dispositif en 3 étages :**

1. **Étage mécanique** (script) : téléchargement GPU par idurba (API publique, prouvé ici),
   contrôle de millésime contre le manifeste, extraction texte, découpage par chapitre de zone,
   pré-remplissage des champs récurrents (he/hf, reculs, emprise, tableau stationnement) avec
   page + article. Fiabilité attendue élevée sur les PLU modernes, bonne sur les anciens
   (articles 6/7/9/10 normalisés).
2. **Étage lecture juridique** (LLM de classe Fable, ou humain) : tableaux de destinations
   (habitat interdit ?), préambules (zones gelées/OAP-only/aménagement d'ensemble), règles
   conditionnelles, hauteurs min/max. C'est l'étage qui décide de la catégorie de chaque zone
   (calibrée / habitat interdit / gelée / non calibrable) — il ne se contourne pas.
3. **Étage validation** : (a) smoke `resolve_zone` sur tous les libellés du manifeste — zéro
   libellé sans décision explicite ; (b) golden 116 ; (c) échantillon avant/après sur le pool ;
   (d) relecture des `_src` par sondage (le taux d'erreur se mesure en re-vérifiant N citations
   au hasard contre le PDF — mesurable et bornable).

Ce qui ne s'industrialise PAS : le choix de tranche des règles à tiroirs (exige le pool servi),
et l'arbitrage des zones hors-schéma — à garder en revue humaine/Fable.

## 6 · Estimation pour les 21 communes restantes (§7.4) et ordre recommandé (§7.6)

**Référence pilote MESURÉE (§3) : ~1 h 15 de travail effectif** pour Saint-Pierre (Point A
12 min, extraction 27 min, sondages/audits/rapport ~35 min), hors attente de base et hors
allers-retours de revue. Mes premières fourchettes (7-11 j-h) étaient surestimées d'un facteur
2 à 3 — voici l'estimation refaite sur la mesure, **pour l'ENSEMBLE des 21 communes** :

- **Scénario manuel (Fable seul, comme ce pilote)** : Point A ~10 min + extraction 30 min
  (moderne régulier) à 1 h 30 (ancien format volumineux — le règlement de Saint-Paul fait
  413 p.) + validation/commits ~20 min → **1 à 2 h par commune → TOTAL 3 à 5 jours-homme
  pour les 21 communes.** En SÉRIE le rapport est allégé (temps + écarts §9), ce qui est déjà
  compté.
- **Scénario assisté** : à ces niveaux, l'étage mécanique d'extraction ne vaut probablement
  plus son propre coût de construction (~1-2 jours) pour 21 communes — il ne se justifierait
  que pour la VALIDATION systématique (contrôle de citations par sondage) ou si le rythme de
  série révèle des règlements anciens nettement plus lents que prévu. **Recommandation révisée :
  lancer la série en manuel, décider de l'outillage après 2-3 communes de mesure.**

Autrement dit : la couverture complète de l'île est une affaire de **jours, pas de semaines**.
Réserves honnêtes : (a) un seul point de mesure, sur un règlement moderne très régulier ;
(b) les anciens formats (Saint-Paul, Le Tampon) et les règlements >300 p. peuvent doubler le
temps d'extraction ; (c) l'attente d'environnement (base partagée) peut dominer le calendrier
sans consommer du travail.

**Ordre recommandé (pool servi × difficulté)** — millésimes re-vérifiés le 27/07/2026 (§6ter) :
1. **Le Tampon** (3e pool ; ancien format à articles préfixés, régulier — règlement déjà téléchargé)
2. **Saint-Louis** (4e pool ; millésime concordant `97414_PLU_20251218`, re-publié 22/07/2026 —
   re-vérifier l'updateDate au Point A, simple précaution)
3. Saint-Benoît, Le Port, Saint-Joseph, Sainte-Marie… par pool décroissant.
4. En dernier : petites communes de montagne (Cilaos, Salazie, Entre-Deux) — pools faibles.

**HORS SÉRIE tant qu'une source opposable manque (revue GO n°3) :**
- **Saint-André** (5 340 parcelles servies) et **Saint-Leu** (6 016) : documents DÉPUBLIÉS du
  GPU — pas de source vérifiable pour graver. Saint-André est de surcroît en révision générale
  (prescrite 22/06/2022, approbation annoncée pour 2024) : calibrer le règlement 2019 juste
  avant son remplacement serait du travail jeté. Réintégrer ces deux communes dès qu'un document
  réapparaît au GPU (le garde-fou de fraîcheur §6ter le signalera) ou sur décision Vic à partir
  des sources communales (§6ter).
- **Saint-Philippe** : RNU, rien à calibrer.

## 6bis · Vérification : le moteur consomme-t-il `habitat: interdit` ? (demande Vic, revue GO)

**OUI, sur toute la chaîne — vérifié dans le code et par exécution :**
- `faisabilite/engine.py:157` : `estimate_capacity` court-circuite dès `habitat == "interdit"` →
  `constructible=False`, fourchette logements (0, 0), verdict explicite. Testé sur les 15 zones
  de Saint-Pierre : toutes rendent « Habitat interdit au règlement … Aucune capacité logement
  calculée ».
- `cascade/layers/phase1.py:267-280` : la cascade lit le même champ (SOFT_FLAG FORT + bonus
  réduit à la part habitat-admis).
- `faisabilite/residuel.py:55` : le résiduel passe par `parcel_faisabilite` → capacité 0 →
  « pas de potentiel résiduel ».

**Le faux positif structurel existe, mais AILLEURS** : le champ n'agit que pour les zones
CALIBRÉES. Dans les 22 communes non calibrées, une zone d'activités au libellé préfixé U
(type Uaz…) tombe sur l'estimation générique → « constructible, R+2 estimé » alors que l'habitat
y est probablement interdit au règlement. C'est flaggé « Estimé » (honnête) mais optimiste. Le
calibrage commune par commune est précisément ce qui résorbe ce biais — à Saint-Pierre, ~310
parcelles servies en zones économiques viennent de basculer de « R+2 estimé » à « habitat
interdit ». **Le repli générique n'est pas neutre : quand il se trompe, il se trompe du côté
optimiste** (revue GO n°2).

### Ampleur sur les communes non calibrées (mesure, rien de corrigé)

Référentiel : `config/o12_zones_activite.yaml` (mandat O12-PARTIEL-2, liste PAR COMMUNE des
codes de zones activité/touristique/équipements/ZAC, graduée en niveau de preuve — explicite/
calibré/inféré/arbitré Vic 27/07/2026). Proxy au niveau ZONES (comptes parcelles servies en
file, base sous verrous du job O12 au moment de la mesure) :

- **125 zones d'activité/spécialisées, ~1 400 ha, dans 17 des 21 communes non calibrées**,
  aujourd'hui servies en estimation générique résidentielle. Têtes : Sainte-Marie (15 zones,
  472 ha — aéroport Roland-Garros + ZA), Le Port (14 zones, 302 ha), Saint-Benoît (105 ha),
  Saint-André (96 ha), Saint-Louis (76 ha), Le Tampon (66 ha).
- **Comptes en PARCELLES SERVIES (mesurés à la libération de la base, run `q_v7_defisc`,
  tiers non écartés)** : **877 parcelles servies en zones spécialisées** (liste O12 ; têtes :
  Sainte-Marie 212, Le Port 134, Saint-Benoît 100, Saint-Leu 67, Le Tampon 57, Saint-André 52)
  **+ 591 en familles 2AU\*/3AU\* fermées** (têtes : Le Tampon 129, Saint-Joseph 128,
  Saint-Louis 80, Saint-André 64, Petite-Île 56, Les Trois-Bassins 49) — dont l'ouverture exige
  une modification du PLU. **Total ≈ 1 470 parcelles servies en estimation résidentielle
  générique dont la capacité réelle est vraisemblablement nulle ou quasi nulle.**

### Mitigation bon marché — évaluation (rien d'implémenté)

Le dispositif O12 a DEUX étages, réutilisables ensemble pour éteindre l'estimation optimiste :

1. **Liste de codes par commune** (`o12_zones_activite.yaml`) : le bon outil. Curatée commune
   par commune (« jamais devinée »), niveaux de preuve tracés, arbitrages Vic datés, couvre les
   24 communes + motif 2AU/3AU. Branchement : `resolve_zone(code, commune)` connaît déjà les
   deux clés — si `code ∈ exclusions[commune]` et commune non calibrée → repli « capacité non
   calculée (zone spécialisée, en attente de calibrage) » au lieu de R+2 estimé.
   **Coût : quelques heures** (lecture du YAML dans `_zone_generique` + note produit + tests).
   Risque de faux positifs : FAIBLE — liste déjà en production sur la division en or ; les
   « inféré » (famille e sans description GPU) sont le seul étage réfutable, et l'erreur
   résiduelle serait du côté prudent (capacité masquée, pas inventée). ⚠ Deux caveats :
   (a) le fichier vit sur la branche O12 NON MERGÉE — dépendance de merge à séquencer ;
   (b) sémantique à confirmer par Vic : la liste exclut aussi touristique/équipements/ZAC par
   arbitrage « division en or » — pour la faisabilité générale, même direction prudente, mais
   c'est un choix produit à re-valider.
2. **Regex descriptive** (`ACTIVITE_DESCR_RE` + protection habitat/résidentiel/proximité,
   finding BP0363) : complément utile mais **fail-open massif ici** — mesuré sur les 21
   communes : elle n'attrape des zones que dans 7 communes ; dans les autres (Le Port,
   Saint-Louis, Le Tampon, Saint-Leu…), le champ `name` GPU ingéré = code brut, sans
   description → la regex ne voit rien. Ne peut PAS être la protection principale.

**Recommandation** : mitigation n°1 (liste de codes) en correctif court, la regex en filet ;
le calibrage par commune reste la résorption définitive.

### MANDAT PRÊT À TIRER — « Repli non optimiste » (décision Vic, revue GO n°3)

**Déclencheur : merge de la branche O12** (le mandat NE duplique PAS `o12_zones_activite.yaml`
et ne le sort pas de sa branche — dépendance stricte). Périmètre : `_zone_generique` /
`resolve_zone` + messages produit + tests. Durée cible : quelques heures (Opus possible).

Comportement du repli pour une commune NON calibrée — **trois situations, trois formulations**
(arbitrage Vic 27/07/2026) :

1. **Code ∈ liste O12 de la commune** (activité / équipement / tourisme / ZAC) →
   « **Capacité non calculée — zone spécialisée, en attente de calibrage.** »
   Étiquette Estimé, capacité NON calculée (on ignore, on le dit). Jamais de R+2 estimé.
2. **Code matchant `exclusions_pattern` (^2AU/^3AU)** → plus fort qu'une ignorance :
   « **Non constructible en l'état — zone AU fermée (ouverture soumise à modification du
   PLU).** » `constructible_neuf=False`. Étiquette **Sourcé** si la famille de zonage
   l'établit — la convention de nommage 2AU/3AU est le fondement (à confirmer article par
   article lors du calibrage de la commune) ; message distinct, ne PAS le noyer avec les zones
   spécialisées.
3. **Zone ordinaire non calibrée** → estimation générique, étiquette Estimé — INCHANGÉ.
4. **(Ajout revue GO n°4) Zones documentées NON CALIBRABLES dans une commune CALIBRÉE**
   (Uavap Saint-Denis — 302 parcelles servies —, AUdma Saint-Pierre) : aujourd'hui elles
   retombent en estimation générique R+2. Formulation : « **Capacité non calculée — zone à
   règles particulières** » (AVAP / zone régie par les seules OAP), pas d'estimation générique.
   Convention d'activation à définir au mandat (ex. marqueur `non_calibrable: true` dans le
   YAML de la commune — micro-extension de schéma à arbitrer par Vic).

Validation du mandat : golden 116 ; comptage avant/après des parcelles servies qui changent de
message par commune ; aucun changement pour les zones ordinaires ni pour les zones calibrées
chiffrées.

#### MISE À JOUR PHASE 4 (Vic, 28/07/2026) — poids réels mesurés, RE-PRIORISATION

Pools servis mesurés en phase 4 (`docs/mandats/PLU_NUIT_PHASE4_MESURES.md`,
`reports/plu-phase4/populations.json` + `population_d.json`), run `q_v7_defisc` :

| Population | Contenu | Pool servi | Priorité |
|---|---|---|---|
| **e** — 92 libellés gelés classés positifs par la cascade | capacité 0 exacte au moteur, mais parcelles SERVIES dans les tiers | **1 229** | **1 — d'abord** |
| **d** — cascade vs habitat-interdit calibré (87 zones `zones:`) | positives cascade, habitat interdit au règlement | **1 005** (0 brûlante · 24 chaudes · 115 réserve · 866 à creuser) | mesurée en phase 4 — priorité À ARBITRER (même mécanique que e : la cascade ignore le règlement ; 24 chaudes concernées) |
| **b** — 11 zones sans hauteur (générique optimiste servi) | Uavap Saint-Denis 302, AUBm La Possession 124, AUx 44… | **553** | 2 — ensuite |
| **a** — 14 habitat-interdit gelées | capacité 0 déjà exacte (st-liste), seule l'étiquette ment | **238** | 3 — en dernier |
| **c** — emprises implicites | ~~17 797~~ → **la population est QUASI VIDE** : 76 des 89 zones sont bornées par la pleine terre gravée (passe d'harmonisation doctrine a de la nuit — résultat obtenu sans l'avoir cherché) ; reste **13 zones / 237 parcelles** sans aucune borne | 237 | 3 — DÉCLASSÉE en note, ne justifie plus un traitement |

Total mesurable ≈ 2 250 parcelles (a+b+c+e hors recouvrements) + population d 1 005.
Nettement moins que redouté. **La doctrine du mandat intègre la leçon 24 du mandat-cadre**
(Salazie +33 % : le repli est ARBITRAIRE, pas systématiquement optimiste — un durcissement
uniforme créerait des faux négatifs ; l'argument est l'exactitude, pas le sens du biais).

## 6ter · Audit de fraîcheur GPU — 24 communes (demande Vic, revue GO)

Comparaison manifeste de calibrage (`config/calibrage/zonage_*.yaml`, extraits le 07/07/2026)
vs document GPU EN_VIGUEUR (API `geoportail-urbanisme.gouv.fr/api/document?grid=<insee>`,
interrogée live le 27/07/2026) :

- **21/24 communes : idurba identique** — zéro divergence de millésime.
- **Correction sur mon signalement Saint-Louis** : le « 22/07/2026 » est la date de
  **re-publication du MÊME document** (`97414_PLU_20251218`, idurba inchangé) — pas un nouveau
  millésime. Alerte initiale surestimée. Leçon quand même : un contrôle de fraîcheur doit
  suivre `originalName` (millésime) ET `updateDate` (re-publications, qui peuvent porter des
  corrections de fichiers sous le même idurba).
- **Saint-Philippe** : RNU documenté (`config/rnu_communes.yaml`, vérifié 26/07/2026) — 0 zone
  au manifeste, cohérent.
- **⚠ TROU DE FRAÎCHEUR RÉEL — Saint-André et Saint-Leu : documents DÉPUBLIÉS du GPU.**
  L'API documents renvoie 0 document (tous statuts) pour 97409 et 97413, et l'API Carto GPU
  `zone-urba` renvoie 0 feature en des points où notre base sert 142 zones (Saint-André,
  idurba `97409_20190228`) et 368 zones (Saint-Leu, idurba `97413_20070226` — un document de
  2007). Contrôle positif fait sur Saint-Pierre (1 feature, bon idurba) : l'API fonctionne, la
  dépublication est avérée. **Le zonage servi de ces 2 communes n'est plus vérifiable à la
  source** — vraisemblablement cycle de re-publication communal en cours (leurs documents
  étaient les plus anciens de l'île). Ampleur produit : **5 340 parcelles servies (Saint-André)
  + 6 016 (Saint-Leu)** au run épinglé. Rien dans le produit ne l'aurait signalé.

### Vérifiabilité Saint-André / Saint-Leu — approfondissement (revue GO n°3)

1. **Archives GPU : AUCUNE.** L'API documents renvoie un tableau VIDE pour 97409 et 97413 —
   tous statuts confondus (les autres communes listent leurs versions ARCHIVE ; ex. Saint-Pierre
   expose son PLU 2023 archivé). Impossible donc de confronter notre calibrage à une archive
   GPU. Notre propre chaîne reste auto-cohérente (manifestes `zonage_saint_andre.yaml` 142
   zones / `zonage_saint_leu.yaml` 368 zones, extraits le 07/07/2026, round-trip DB↔YAML zéro
   écart, geoms sidecar md5) — on peut prouver ce qu'on sert, plus le rattacher à la source.
2. **Sources alternatives — OUI, les deux communes restent calibrables plus tard :**
   - Saint-André : règlement 2019 **en ligne sur le site communal** (vérifié vivant, PDF 6,7 Mo,
     mars 2019 : `saint-andre.re/wp-content/uploads/2019/03/3-RSglement.pdf`) — cohérent avec
     l'idurba calibré `97409_20190228`. NE PAS le calibrer (décision Vic : révision en cours,
     travail jeté).
   - Saint-Leu : page PLU de la mairie (`saintleu.re/plan-local-d-urbanisme-plu`) + versions
     détenues par l'État (DEAL : `reglement_StLeu_EP` — version enquête publique, PAS
     l'approuvée) ; PLU en révision.

   **Saint-André — deux hypothèses à trancher (appel/mail Vic, aucune conclusion ici).**
   La révision générale était annoncée pour 2024 ; nous sommes en juillet 2026 et le document
   est dépublié du GPU. Soit (H1) **la révision est aboutie** et le nouveau PLU, approuvé, n'est
   pas (encore/correctement) publié au GPU — auquel cas le zonage que nous servons (2019) est
   PÉRIMÉ sur le fond ; soit (H2) **la révision traîne** et le PLU 2019 reste le document en
   vigueur, seule sa publication GPU ayant sauté — auquel cas notre zonage est bon mais sa
   vérifiabilité (et l'opposabilité, cf. point 3) est en question. À demander au service
   urbanisme de la commune : « La révision générale prescrite le 22/06/2022 a-t-elle été
   approuvée ? Si oui, à quelle date, et le dossier approuvé est-il transmissible ? Sinon, le
   PLU approuvé le 28/02/2019 est-il toujours en vigueur, et pourquoi n'apparaît-il plus sur le
   Géoportail de l'urbanisme ? » La réponse tranche H1/H2 ET la question d'opposabilité.

   **Saint-Leu — dossier prêt pour le mail de Vic.** Destinataire : service urbanisme de la
   mairie de Saint-Leu (via `saintleu.re`), en copie le TCO (Territoire de l'Ouest, compétence
   planification — c'est lui qui a porté la mise en compatibilité SAR/SCoT). Demandes :
   (1) « Le PLU approuvé le 26/02/2007 (référence GPU `97413_20070226`) est-il toujours le
   document en vigueur ? » ; (2) « Pourquoi n'est-il plus publié au Géoportail de
   l'urbanisme ? » ; (3) « Où en est la révision (arrêt de projet ? enquête publique close ?
   approbation prévue ?) » ; (4) « Le règlement écrit et le plan de zonage APPROUVÉS
   sont-ils transmissibles (PDF) ? » — la version DEAL en ligne étant celle de l'enquête
   publique, elle ne fait pas source pour graver.
3. **Opposabilité — question ouverte, à trancher par Vic auprès des communes.** Depuis 2023, la
   publication au GPU conditionne le caractère exécutoire des documents d'urbanisme. Deux
   documents dépubliés posent donc une question d'opposabilité du zonage que nous servons pour
   11 356 parcelles — AUCUNE conclusion juridique ici, seulement le signalement : vérification
   à faire par Vic auprès des communes/DEAL. Le produit met en avant la vérifiabilité ; tant que
   la question est ouverte, prudence sur l'étiquette de fiabilité de ces deux communes.

**Garde-fou automatisable — architecture et coût** (spécification VALIDÉE en revue GO n°4 ;
implémentation dans un mandat séparé — cible Opus, une demi-journée ; **le cron hebdomadaire
est à reporter au kit VPS**) :
- **Quoi** : commande `labuse check-plu-fraicheur` — pour chacune des 24 communes, GET
  `api/document?grid=<insee>` ; DEUX comparaisons (spec corrigée en revue GO n°4 — le contrôle
  zonage seul n'aurait PAS attrapé le cas Saint-Denis, où le zonage était à jour et le
  règlement de gravure en retard) :
  1. **idurba du ZONAGE** en vigueur vs manifeste `config/calibrage/zonage_<commune>.yaml` ;
  2. **millésime du RÈGLEMENT GRAVÉ** (`source.reglement_grave.millesime` du
     `config/plu_<commune>.yaml`, champ posé rétroactivement sur les 3 communes calibrées avec
     fichier + md5 + date de vérification) vs le document en vigueur au GPU.
  **Quatre alertes distinctes** : (a) nouveau millésime de zonage, (b) re-publication du même
  millésime (updateDate), (c) **0 document = dépublication** (cas réel du jour), (d) **« règles
  gravées sur un règlement antérieur au document en vigueur »** — Saint-Denis déclenche (d)
  par construction : millésime gravé 2024-02-20 < 97411_PLU_20260423. C'est le comportement
  ATTENDU : l'alerte prompte le diff (fait le 27/07/2026 : règlement écrit identique, alerte
  documentée au YAML, à réexaminer à chaque nouvelle procédure).
- **Où** : résultat versé dans l'infra existante `source_checks`/`source_radar` +
  `admin_alertes` (rien à créer côté modèle) ; l'état de référence est déjà dans les manifestes.
- **Périodicité** : hebdomadaire suffit largement (les procédures PLU bougent au rythme du
  mois) ; un run = 24 requêtes HTTP ≈ 15 s, coût réseau nul, aucune dépendance nouvelle.
- **Coût de mise en place estimé** : ~une demi-journée (commande CLI + cron + test), la logique
  de comparaison tenant en ~50 lignes. La requête et la comparaison sont celles exécutées à la
  main dans cet audit.

## 7 · Validation sur pièces (Point d'arrêt B) et mesures d'impact (§6 du mandat)

> Exécutée à la libération de la base (20:33-20:50), en LECTURE SEULE — aucun re-run de
> scoring, aucun contact avec le champion P.

### 7.1 Échantillon de contrôle — 10 parcelles, avant (repli) → après (calibré)

Sortie intégrale : `/tmp/plu_sp/validation_b_output.txt` (recalculable : script §7.4).
Condensé — SDP en m², logements en fourchette sous-sol :

| Zone | Parcelle | Surface | AVANT (repli générique) | APRÈS (calibré) | Article invoqué |
|---|---|---|---|---|---|
| Ug | 97416000CO0087 | 893 m² | R+2 · SDP 751 · 7-9 logts (Estimé) | R+1 · SDP 402 · 4-5 logts | Art. Ug3.5, p.103 |
| Ug | 97416000CO0088 | 855 m² | R+2 · SDP 675 · 6-8 | R+1 · SDP 385 · 3-5 | Art. Ug3.5, p.103 |
| Uf | 97416000CR0151 | 1 642 m² | R+2 · SDP 1 494 · 14-15 | R+1 · SDP 739 · 7-10 | Art. Uf3.5, p.119 |
| Uf | 97416000CR0153 | 1 515 m² | R+2 · SDP 1 360 · 13-14 | R+1 · SDP 682 · 6-9 | Art. Uf3.5, p.119 |
| Ud | 97416000CS1116 | 2 118 m² | R+2 · SDP 1 962 · 19-20 | **R+4 · SDP 2 859 · 28-32** (hausse : centralité) | Art. Ud3.5, p.84 |
| UdBO | 97416000HY1680 | 524 m² | R+2 · SDP 65 · 0-1 | R+4 · SDP 108 · 1-2 | Art. Ud3.5, p.84 (UdBO) |
| Ucv | 97416000DS0213 | 129 m² | trop exigu (0) | trop exigu (0) — inchangé | — |
| Up | 97416000EL0018 | 324 m² | R+2 · SDP 141 · 1-2 | R+1 · SDP 151 · 1-2 | Art. Up3.5, p.147 |
| Us | 97416000CD0763 | 175 m² | R+2 · SDP 66 · 0-1 (Estimé) | **0 — construction neuve non autorisée (gel)** | Préambule p.129 + Art. Us1 |
| AU02 | 97416000CO0540 | 25 277 m² | **R+2 · SDP 31 321 · ~227 logts (Estimé)** | **0 — zone AU fermée** | Art. AU01, p.200 |

Chaque ligne est vérifiable à la main : article + page cités dans le YAML.

### 7.2 Golden et tiers

- **Golden 116/116 PASS à CHACUN des 3 commits de lot** (API locale 8010 relancée entre chaque
  état de fichier, référence `reports/m6-audit/golden/golden-parcelles.json`, 5 parcelles 97416
  incluses). 73 tests unitaires faisabilité/config PASS.
- **Tiers servis inchangés AU BIT PRÈS** après pose du fichier : 120 / 1 031 / 3 587 / 72 980 /
  353 945 (re-comptés sur `q_v7_defisc` post-commit). Attendu — ils viennent du run épinglé et
  AUCUN re-run n'a été lancé.

### 7.3 Écart repli vs calibré — LE chiffre du mandat

Échantillon aléatoire de 400 parcelles du pool servi de Saint-Pierre (seed 42), moteur complet
(géométrie réelle), passe « avant » = YAML retiré, passe « après » = YAML en place :

- **Le repli générique SURESTIME : médiane -33 % de SDP** une fois calibré (quartiles -38 % /
  -33 %). SDP en baisse pour **299 parcelles sur 357** constructibles aux deux passes, en hausse
  pour 58 (les centralités Ud/UdBO/Ucv où le vrai PLU dépasse le hé générique 9 m).
- **15 parcelles sur 400 (3,8 %) perdent TOUTE constructibilité** (gel Us/AU0, habitat interdit),
  **0 n'en gagne**.
- Mécanique de la surestimation : hé générique 9 m (R+2) vs hé réels 6-7 m (R+1) sur Ug/Uf/Up
  qui portent >80 % du pool + aucune contrainte d'emprise/pleine terre au repli.

**Conséquence produit (à l'échelle de l'île)** : les chiffres servis sur les 21 communes non
calibrées sont vraisemblablement optimistes du même ordre (~⅓ de SDP en médiane) partout où le
tissu ressemble à Saint-Pierre — et l'écart est PIRE sur les ~1 470 parcelles servies en zones
spécialisées/AU fermées (§6bis : 877 + 591 comptées, capacité réelle proche de zéro). La
priorisation de la série de calibrage (§6) et le mandat « Repli non optimiste » (§6bis) en
découlent directement.

### 7.4 Reproductibilité

Script de mesure : `/tmp/plu_sp/validation_b.py` (copie à archiver si besoin — lecture seule,
déplace temporairement le YAML pour la passe « avant », le remet en place, caches purgés).

## 8 · § FRICTIONS DE SCHÉMA (amendement au GO) et verdict de schéma

Chaque friction : citation → ce qui a été gravé → ce qu'un schéma idéal porterait.

**F1 — Règles à tiroirs par tranche de surface (emprise, pleine terre).**
« L'emprise au sol des constructions est limitée à : 80 % … ≤150 m², 70 % … 150-250 m², 50 % …
>250 m² » (Art. Ug3.4, p.102-103 ; idem Uf/Up/Us, et CBS partout). Schéma idéal :
`emprise_sol_tranches: [{max_m2: 150, pct: 80}, …]` — le moteur a déjà la surface de la
parcelle, l'application serait exacte.

*Ce que la gravure v1 a fait, précisément (demande Vic)* : dans TOUS les cas, la tranche gravée
est à la fois **la tranche dominante du pool servi ET la plus conservatrice** (emprise la plus
basse / pleine terre la plus haute — les règlements donnent plus de droits aux petites
parcelles, donc la tranche des grandes parcelles est toujours la plus stricte). Aucune zone n'a
été laissée non calibrée pour ce motif, aucune valeur permissive n'a été retenue. Fidélité par
zone :

| Zone | Règle à tiroirs | Gravé | Fidèle pour | Approximatif (sous-estimé) pour |
|---|---|---|---|---|
| Ug/AUg | emprise 80/70/50 · PT 30/25 | 50 · 30 | 81 % du pool (>250 m²) | 663 parcelles ≤250 m² |
| Uf/AUf | emprise 70/50 · PT 40/30 | 50 · 40 | 93 % / 83 % du pool | ~180-430 petites parcelles |
| UfCA/AUfGB | idem Uf | 50 · 40 | 87 % / 73 % | ~20-45 parcelles |
| Up | emprise 80/60 | 60 | 87 % du pool (>=150 m², médiane 261 m² — vérifié post-verrous) | 26 parcelles <150 m² |
| UdBO | PT 40/25 | 40 | 67 % (>250 m²) | 28 parcelles ≤250 m² |
| Ud / Ucv | PT 20/20 (identique) | 20 | **100 % — exact, pas d'approximation** | — |
| Ud / Ucv | exception emprise « non réglementée » si UF<200 m² | 60 / 70 gravés | parcelles ≥200 m² | petites parcelles (cap appliqué à tort, sous-estime) |
| Us | tranches sans effet (zone gelée) | — | — | — |

**Bilan : la gravure est fidèle pour ~85 % du pool des zones concernées, et prudente-par-
construction (jamais optimiste) pour le reste.** Le passage au schéma v2 (tranches natives)
rendrait ces ~15 % exacts sans re-sourcer quoi que ce soit.

**F2 — Pas de `constructible_neuf` par zone.**
Us (gel SCoT, préambule p.129) et AU0 (« toute construction interdite », Art. AU01 p.200) ne
peuvent être rendus non-constructibles QUE via `zones_au_st`, dont l'étiquette moteur est
« secteur de transition (AU*st), H max 4 m » — capacité exacte (zéro), étiquette inexacte
(Saint-Pierre n'a aucun AU*st ; le « H max 4 m » est un artefact non sourcé). Schéma idéal :
`constructible_neuf: false` + `motif:` par zone, consommé par le verdict.

**F3 — Norme de stationnement au m² de SDP.**
« 1 place de stationnement par tranche de 75 m² de surface de plancher » (Art. Ud6 p.93, idem
Ucv). Le parseur ne consomme que « N place(s)/logement » → gravé tel quel (fidèle, affichable en
fiche) mais garde-fou stationnement NON appliqué en Ud/UdBO/Udl/Ucv, silencieusement. Schéma
idéal : `stat_par_m2_sdp: 75` en alternative à `stat_logement`.

**F4 — Hauteurs MINIMALES imposées.**
« comprises entre 6 et 15 m à l'égout » (Ud), « entre 9 et 15 m » (Ucv), « entre 8 et 16 »
(UdBO). Le schéma ne porte que des maxima ; les minima (information produit : un projet R+0 y est
refusable) sont en note. Mineur pour la SDP résiduelle (calculée au max).

**F5 — Bonus conditionnels de hauteur (mixité sociale / CBS).**
« >10 logements aidés et/ou CBS>70 % → 10/15 m » (Ug), « →18/23 m » (Ud/Ucv, +attique 21/25).
Systématiques dans ce PLU. Gravé : règle générale, bonus en note (prudent). Schéma idéal :
`hauteur_bonus: {he_m, hf_m, condition}` — à forte valeur produit (argumentaire « passez en R+4
avec 30 % de LLS »), mais demande un moteur qui scénarise.

**F6 — Étiquette du repli générique.**
`_zone_generique` annonce « PLU de la commune non outillé (aucun config/plu_<commune>.yaml) »
même quand le YAML existe et que seule la zone est absente/volontairement non calibrée (AUdma,
A/N ici). Cosmétique mais trompeur en fiche. (Code, pas schéma — non touché.)

**Verdict de schéma : v1 APTE pour les 21 communes restantes, avec les conventions du pilote**
(tranche dominante documentée, `zones_au_st` pour les gels, norme SDP en texte). Aucune friction
ne produit de chiffre FAUX étiqueté Sourcé — elles produisent des sous-estimations documentées ou
des étiquettes imparfaites. **Un schéma v2 (F1+F2+F3) vaut le coût si** le produit veut cesser de
sous-estimer les petites parcelles (F1 est la plus fréquente : 4 chapitres sur 12 ici, et les CBS
partout) : spécification ci-dessus, migration de Saint-Paul/Saint-Denis mécanique — 2 fichiers,
~250 lignes chacun, aucune valeur à re-sourcer (les tranches existantes deviennent des tranches
uniques), golden en garde-fou — **estimée 0,5 jour-homme + revue**.

**DÉCISION VIC (revue GO, 27/07/2026) : schéma v1 VALIDÉ pour la suite — pas de v2 pour
l'instant, spécification ci-dessus gardée au chaud. Décision reconfirmée avant la commune n°2.**

## 9 · Leçons à reverser au §9 du mandat-cadre

| Leçon | Détail |
|---|---|
| **Fraîcheur GPU : 4 signaux, pas 1** | Audit 24 communes (27/07/2026) : 0 divergence de millésime de zonage, MAIS Saint-André et Saint-Leu DÉPUBLIÉS (11 356 parcelles servies non vérifiables à la source), Saint-Louis re-publié le 22/07/2026 sous le même idurba, ET Saint-Denis gravé sur un règlement antérieur de 2 procédures au document en vigueur (zonage à jour — le contrôle zonage seul ne l'attrape pas). Suivre : nouveau millésime / re-publication (updateDate) / dépublication / **règlement de gravure antérieur** (champ `source.reglement_grave` posé sur les 3 YAML). Cf. §6ter. |
| **FAIT PRODUIT — le repli générique est OPTIMISTE (établi sur 3 communes indépendantes)** | Écart repli→calibré, 400 parcelles/commune, moteur complet : Saint-Pierre **-33 %** de SDP médiane, Saint-Paul **-33 %**, Saint-Denis **-53 %** ; parcelles perdant toute constructibilité : 15/11/25 sur 400 ; parcelles en GAGNANT : **0 sur 1 200**. Le repli ne se trompe que dans un sens. C'est l'argument chiffré qui justifie le calibrage complet de l'île — et le mandat « Repli non optimiste » en attendant. |
| **Format moderne vs ancien** | Île mixte confirmée : Saint-Paul 2012 et Le Tampon 2018 à l'ancienne (articles préfixés) ; Saint-Pierre 2024 moderne (chapitres 1/2/3). Le schéma porte les deux ; les correspondances d'articles du pilote (en-tête du YAML) sont réutilisables. |
| **Le tableau des destinations d'abord** | Lire Art. <Z>1 AVANT le chapitre 2 : la moitié des zones de Saint-Pierre sont habitat-interdit ou gelées — leurs hauteurs n'ont alors qu'une valeur documentaire. |
| **Préambules porteurs de droit** | Gel SCoT (Us), R151-8/OAP-only (AUdma), aménagement d'ensemble (toutes les AU) : uniquement dans les préambules. |
| **PRINCIPE DE GRAVURE (validé Vic, revue GO n°5)** | Règle à tiroirs que le schéma ne porte pas → graver la **tranche dominante du pool servi**, qui doit aussi être **la plus conservatrice** (les règlements donnent plus de droits aux petites parcelles : c'est structurel). Jamais la valeur permissive, jamais de zone sacrifiée pour ce motif, écart documenté en `_note` avec les %. Corollaire général : **quand on ne sait pas, on sous-estime.** |
| **Réutiliser la liste O12** | `o12_zones_activite.yaml` (branche O12) = codes de zones activité/spécialisées des 24 communes, curatée et arbitrée — précieuse en série pour pré-identifier les zones habitat-interdit d'une commune AVANT lecture, et candidate mitigation du repli optimiste (cf. §6bis). |
| **GPU archives monolithiques** | ~1 Go par commune, mais téléchargement direct fiable (redirect data.geopf.fr) ; le règlement écrit pèse ~5-8 Mo une fois extrait. |
| **Base partagée** | Ne pas démarrer l'API locale (son `ALTER TABLE parcels` au boot) pendant qu'un job d'ingestion tourne : convoi de verrous. Golden à passer en fenêtre calme. |
| **Temps réel** | ~4 h pilote bout-en-bout ; extraction pure ~2 h 20 ; projection SÉRIE 2,5-4 h/commune en manuel. |
