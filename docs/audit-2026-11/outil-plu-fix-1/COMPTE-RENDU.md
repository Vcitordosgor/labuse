# Outil PLU — compte-rendu OUTIL-PLU-FIX-8 (24/11/2026)

> Branche `fix/outil-plu-1`, worktree `~/Desktop/labuse-plu-fix`, base `labuse` (user OS `openclaw`),
> ports 7480 (API) / 10280 (front). PDF officiels dans `~/Desktop/labuse/data/plu_reglements`.
> **Tout chiffre ci-dessous sort de `scripts/plu_chiffres.py`** (sortie brute collée §« Chiffres ») —
> aucun chiffre écrit de mémoire. Lu en entier avant d'agir : `relecture-plu-6.md`, `relecture-plu-5.md`,
> `audit-outils/01-PLU-ASTRA-2.md`, et les sections FIX-6/FIX-7 ci-dessous. Réingestion du jour :
> **3302 extraits, 21 communes.**

## LOT 0 — filet de non-régression (AVANT toute correction) — `tests/test_plu_cas_valides.py`

**31 tests, un par cas cité aux relectures 1-6 et aux deux rapports externes** (les 15 non-régressions de
la relecture-6, piscine Saint-Denis p.22, exception U2e art.13 entier + seuil 20 % p.100, renvois de
secteur AU3c→U3c / 2AUd→Ud, 48 articles d'Entre-Deux, 3 barèmes imposés « stationn… », date L'Étang-Salé,
réfs de prose = 0, dédup Possession, Beauvallon AUp, STECAL NTA/NTB, A↛AU, casse/accents, pagination,
« emprise au sol » expr<mots). Chaque test affirme une **valeur précise** (texte, zone, article, page).

- **Preuve que le filet MORD** (sortie brute) — réingéré sur le code FIX-7 (`7588d8572`), les cas réparés
  par ce mandat sont **rouges**, dont l'U2e exigé par le mandat :
  ```
  FAILED test_u2e_article13_entier_avec_seuil_20pct
  FAILED test_u2e_article13_pas_de_moignon_definition_sans_zone
  FAILED test_u2e_article13_famille_toutes_zones_portent_le_20pct
  FAILED test_zero_doublon_octet_meme_zone
  FAILED test_le_port_2AU_article_aspect_servi
  FAILED test_le_port_1AU_2AU_ont_des_articles_propres
  FAILED test_preambule_saint_pierre_ucv_rattache
  FAILED test_couverture_plan_zonage_peu_de_zeros
  8 failed, 23 deselected
  ```
- **Après les correctifs (base réingérée)** : `31 passed`. Commit séparé (le filet d'abord).

## LOT 1 — U2e article 13 : l'article redevient ENTIER (seuil 20 % compris)

- **Cause exacte, et correction d'attribution** : la régression n'a PAS été introduite par FIX-7 ni par
  `_SUBHEAD`/`_subhead_titre` (hypothèse de la relecture-6) — l'article 13 ne fait que 2 pages, sous le
  seuil des 6 pages du sous-découpage. La vraie règle fautive est la **boucle de frontières
  `_RESET_CHAP_M`** : elle prend TOUTE ligne « Définition » (mot-clé de `_RESET_CHAP_SRC`) pour une
  frontière de chapitre SANS zone, y compris l'**intertitre interne** « Définition » sous « 13.1 -
  Espaces libres ». Preuve par ré-exécution du découpage FIX-5/FIX-6/FIX-7 sur le PDF Saint-Paul :
  FIX-5 gardait l'article entier (3353 car., zone U2E, 20 %) ; **FIX-6 déjà le coupait** (moignon 143 car.
  + « Définition » zone None 3207 car. portant le 20 %) ; FIX-7 identique. **La régression date de FIX-6.**
- **Correctif** (`plu_ingest.py`) : une frontière `_RESET_CHAP_M` est ignorée quand elle tombe **entre deux
  en-têtes d'article de la MÊME zone** (intertitre interne, pas un nouveau chapitre). Les vraies frontières
  (ANNEXES, TITRE après le dernier article d'une zone, préambule de la zone suivante) restent coupées.
- **Les autres articles coupés de la même façon** (ré-exécution du découpage, HEAD FIX-7) :
  Saint-Paul « Article 13- » en **U1 (p.50), U2e (p.99), U3e (p.156), AU5e (p.265)** + La Plaine
  « ARTICLE UB 5 » (« Définition Champ d'application », p.141). **5 articles réparés** (chacun retrouve son
  corps + seuil). Résidu assumé : La Plaine « ARTICLE UB 7 » p.168 — page à extraction DÉGRADÉE (« ARTICLE
  UB 7 -ARTICLE Ur / 7.1 – Définition / NTATION DES CONSTRUCTIONS… »), non le motif propre de l'article 13.
- **Résultat** : l'« Article 13- » U2E est servi ENTIER p.99-100 avec le **20 %** ; **8** « Article 13- »
  portent le 20 % (U1, U2E, U3, U3E, U4, U5, AU5E, U6) ; **0** extrait « Définition » zone NULL à Saint-Paul.

## LOT 2 — doublons : ZÉRO doublon octet, sans perdre une règle

- **Deux causes distinctes** :
  1. **Chrome d'annexe pris pour des en-têtes** — le fil d'en-tête nu « Titre 4 » / « Titre 5 » + la
     continuation de la liste de dates DCM (« 21/10/2015, 05/10/2017, … et du 27/03/2025. ») survivaient à
     la détection par fréquence et fragmentaient le lexique de Saint-Paul en **25 « Titre 4 » + 9 « Titre
     5 »**. Correctif : `_CHROME_RUNHEAD` + `_CHROME_DATELIST` les retirent → l'annexe s'ancre désormais sur
     le VRAI titre « TITRE IV GLOSSAIRE GENERAL » (1 bloc), « TITRE V », « TITRE VI PALETTE VÉGÉTALE »…
  2. **Mêmes articles génériques réédités d'un livret/bassin à l'autre** avec la MÊME zone (USDU ×3-4) —
     `_dedup` supprime les doublons octet-pour-octet (clé **(zone, texte à blancs normalisés)** : les
     variantes ne différant que d'un espace/saut de page résiduel sont collées). Un texte **distinct** sous
     la même (réf,zone) — règle d'un AUTRE bassin — est CONSERVÉ (le supprimer perdrait une règle).
- **Résultat** (script) : **0 doublon octet-pour-octet** (même zone) dans tout le corpus ; Saint-Paul
  « hauteur » 87→**69**. Les 6 couples (réf,zone) encore répétés ont des **textes substantiellement
  distincts** (bassins de vie : « Article 6- » U1 5493 vs 2706 car., etc.) — ce ne sont pas des doublons.
- Le **« 174 doublons »** de la relecture-6 comptait TOUT texte identique sans égard à la zone : 30 groupes
  servent le même texte sous des zones DIFFÉRENTES (« Article 5- : il n'est pas fixé de règle » sous 16
  zones). Les dédupliquer à l'aveugle retirerait l'article d'une zone. Ici, dédoublonnage **par (zone,
  texte)** : zéro doublon vu sous un filtre, zéro règle perdue.

## LOT 3 — zones injoignables

- **Le Port 1AU/2AU** : les en-têtes à CHIFFRE DE TÊTE (« Article 2AU 9 », « Article 1AUindicée 5 ») que
  `_ZONE_FROM_ART` ne savait pas lire (chiffre avant la classe, n° d'article noyé dans « indicée ») sont
  désormais zonés via `_ZONE_FROM_ART_NUM` (classe+chiffre → 2AU, 1AU). **15 articles 1AU + 15 articles
  2AU** servis ; « Article 2AU 9 — Aspect extérieur » **p.159** sort sous le filtre 2AU.
- **Préambules de zone rattachés** : `_zone_de_preambule` attribue sa zone au préambule / à la tête de
  chapitre qui la DÉFINIT (« La zone Ucv correspond… », « Dispositions applicables à la zone UB ») — jamais
  un simple renvoi (« se reporter au règlement de la zone U ») ni un titre « …AUX ZONES À URBANISER », et
  jamais une ANNEXE multi-zones (« ANNEXES RELATIVES AUX ZONES NS, NTA ET NTB » reste commune). **21
  préambules** rattachés (Saint-Pierre Ucv/Ud/Ug/Uf/Us/Up/Ut/Ua/Ue/AU0/A/N, Entre-Deux Ua, Petite-Île UB,
  Le Port 1AU/2AU…).
- **Couverture des 21 communes** (script) : sur **701** zones du plan de zonage, **81** étaient sans
  règlement zoné (toutes des zones À URBANISER). Traitement : renvoi GÉNÉRIQUE **AU→U « de même indice »**
  (clause standard des PLU réunionnais) dans `zones_apparentees`, **additif et déclenché UNIQUEMENT** quand
  la zone AU n'a aucun chapitre propre → **injoignables 81 → 4**. Les 4 résidus (Bras-Panon 1AUt,
  Sainte-Rose/Le Tampon 1AUto, Trois-Bassins 1AUt) sont des zones AU touristiques SANS zone U d'indice
  correspondant dans le règlement (pas de « Ut »/« Uto » stocké) — résidu BORNÉ et dit, pas un trou muet.
- **Non-régression prouvée** : `A@La Possession → ['A']` (jamais d'AU), `AU3c → U3c`, `2AUd → Ud` intacts.

## LOT 4 — dates : approbation écrite ≠ millésime du lot, nommées distinctement

Dates d'approbation écrites **relues sur les couvertures PDF** (vérifiées p.1, cf. `plu_chiffres.py` §7) et
posées en `config/plu_dates_gpu.yaml` (`date_approbation_ecrite`), distinctes du millésime du lot (dépôt
GPU) : **Saint-Denis** 2024-02 (« DOSSIER APPROUVE FEVRIER 2024 », mois seul) ≠ lot 2026-08-05 ; **La
Plaine** 2013-05-29 (« Approuvé le 29 mai 2013 · Modifié le 11 mars 2019 ») ≠ 2023-05-27 ; **Le Tampon**
2018-12-08 ≠ 2023-08-11 ; **Cilaos** 2008-02-06 ≠ 2024-02-13 ; (+ L'Étang-Salé 2017-06-22 déjà fait). Les
communes dont le lot EST l'approbation active (Saint-Paul 17/12/2025, La Possession, Saint-Louis… :
modifications récentes réellement déposées) gardent lot = approbation — conforme aux ⚠ de la relecture-6.

## RÈGLE SUR LES CHIFFRES — `scripts/plu_chiffres.py` (sortie brute)

Le « 174 attribuées » de FIX-7 **valait 3** : la bascule 849→675 des sans-zone de FIX-7 venait à ~95 % de
la **suppression** d'extraits (ré-découpe / réfs de prose supprimées), PAS d'une attribution de zone ;
seuls **3** extraits recevaient alors une zone par `_zone_de_fiche`. Ici l'attribution réelle est : 3
(fiche) + 21 (préambule) + 46 (code à chiffre de tête).

```

==============================================================================
1. CORPUS (base labuse réingérée)
==============================================================================
extraits = 3302 · communes servies = 21 · sans zone = 539 · zonés = 2763

==============================================================================
2. DOUBLONS (LOT 2)
==============================================================================
doublons octet-pour-octet (même insee,doc,zone,texte) EN TROP      = 0
doublons à blancs normalisés (même insee,doc,zone,norm-texte) EN TROP = 0  (cible 0)

Saint-Paul « hauteur » : 69 extraits ; (réf,zone) répétés = 6 couples, 6 en trop
   Article 10-    N      ×2  (textes distincts à blancs normalisés = 2)
   Article 11-    N      ×2  (textes distincts à blancs normalisés = 2)
   Article 13-    U1     ×2  (textes distincts à blancs normalisés = 2)
   Article 6-     U1     ×2  (textes distincts à blancs normalisés = 2)
   Article 7-     U1     ×2  (textes distincts à blancs normalisés = 2)
   TITRE II       None   ×2  (textes distincts à blancs normalisés = 2)
   → tous les 'répétés' restants ont des textes DISTINCTS (livrets/bassins de vie différents) :
     ce ne sont pas des doublons, les supprimer perdrait une règle de bassin.

==============================================================================
3. U2e ARTICLE 13 — ENTIER SOUS SON FILTRE, SEUIL 20 % (LOT 1)
==============================================================================
   'Article 13-' zone=U2 p83-87 len=6727 contient_20%=False
   'Article 13-' zone=U2E p99-100 len=3353 contient_20%=True
   Saint-Paul : 8 'Article 13-' contiennent le seuil 20 % (zones ['U1', 'U2E', 'U3', 'U3E', 'U4', 'U5', 'AU5E', 'U6'])
   extraits 'Définition' zone NULL à Saint-Paul (ex-moignons détachés) = 0

==============================================================================
4. ZONES INJOIGNABLES — COUVERTURE DU PLAN DE ZONAGE (LOT 3)
==============================================================================
   97402 Bras-Panon             1 zéro/29 -> ['1AUt']
   97419 Sainte-Rose            1 zéro/23 -> ['1AUto']
   97422 Le Tampon              1 zéro/30 -> ['1AUto']
   97423 Les Trois-Bassins      1 zéro/30 -> ['1AUt']
   TOTAL zones du plan de zonage (21 communes) = 701 ; injoignables = 4

==============================================================================
5. LE PORT 1AU/2AU — ARTICLES PROPRES SERVIS (LOT 3)
==============================================================================
   zone 1AU : 15 extraits zonés ; apparentées=['1AU']
   zone 2AU : 15 extraits zonés ; apparentées=['2AU']
   « aspect » filtre 2AU → articles 2AU servis : [('Article 2AU', 159)]  (dont 'Aspect extérieur' p.159)

==============================================================================
6. RENVOI GÉNÉRIQUE AU→U & NON-RÉGRESSION (LOT 3)
==============================================================================
   A@97408: apparentées=['A'] ; note=None
   AU3c@97415: apparentées=['AU3', 'U3'] ; note=AU3c : le règlement renvoie à U3c
   2AUd@97422: apparentées=['UD'] ; note=2AUd : le règlement renvoie à Ud
   AUa@97401: apparentées=['U'] ; note=AUa (zone à urbaniser) : le règlement renvoie au règlement de la zone Ua de même indice — articles de Ua servis ci-dessous.

==============================================================================
7. DATES — APPROBATION ÉCRITE ≠ MILLÉSIME DU LOT (LOT 4)
==============================================================================
   97401 Les Avirons            approbation=2024-12-06   lot=2024-12-06
   97402 Bras-Panon             approbation=2026-04-28   lot=2026-04-28
   97403 Entre-Deux             approbation=2024-09-24   lot=2024-09-24
   97404 L'Étang-Salé           approbation=2017-06-22   lot=2025-09-17 [écrite≠lot, nommées distinctement]
   97405 Petite-Île             approbation=2023-06-09   lot=2023-06-09
   97406 La Plaine-des-Palmistes approbation=2013-05-29   lot=2023-05-27 [écrite≠lot, nommées distinctement]
   97407 Le Port                approbation=2024-12-09   lot=2024-12-09
   97408 La Possession          approbation=2026-06-25   lot=2026-06-25
   97410 Saint-Benoît           approbation=2020-02-06   lot=2020-02-06
   97411 Saint-Denis            approbation=2024-02      lot=2026-08-05 [écrite≠lot, nommées distinctement]
   97412 Saint-Joseph           approbation=2025-12-10   lot=2025-12-10
   97414 Saint-Louis            approbation=2025-12-18   lot=2025-12-18
   97415 Saint-Paul             approbation=2025-12-17   lot=2025-12-17
   97416 Saint-Pierre           approbation=2024-06-25   lot=2024-06-25
   97418 Sainte-Marie           approbation=2025-11-26   lot=2025-11-26
   97419 Sainte-Rose            approbation=2019-05-04   lot=2019-05-04
   97420 Sainte-Suzanne         approbation=2025-09-29   lot=2025-09-29
   97421 Salazie                approbation=2022-05-24   lot=2022-05-24
   97422 Le Tampon              approbation=2018-12-08   lot=2023-08-11 [écrite≠lot, nommées distinctement]
   97423 Les Trois-Bassins      approbation=2017-02-21   lot=2017-02-21
   97424 Cilaos                 approbation=2008-02-06   lot=2024-02-13 [écrite≠lot, nommées distinctement]

==============================================================================
8. ATTRIBUTION DE ZONE — « 174 » de FIX-7 : d'où venait l'erreur
==============================================================================
   zone posée par _zone_de_fiche (fiche/annexe zonée)      = 3
   zone posée par _zone_de_preambule (préambule de zone)   = 21
   zone posée par code à chiffre de tête (Le Port 1AU/2AU) = 46
   → FIX-7 annonçait « ≈174 fiches/annexes attribuées » : FAUX. La bascule 849→675 des
     sans-zone de FIX-7 venait à ~95 % de la SUPPRESSION d'extraits (ré-découpe/réfs de
     prose), pas d'une attribution ; seuls 3 extraits recevaient alors une zone (_zone_de_fiche).

PLU_CHIFFRES_DONE
```

## FIN

Réingestion faite (3302 extraits, 21 communes). Les 31 tests du LOT 0 sont **verts** (sortie brute
ci-dessus). Poussé sans `--no-verify`. **Pas de fusion dans `main`. API arrêtée.**

---

# Outil PLU — compte-rendu OUTIL-PLU-FIX-7 (24/11/2026)

> Branche `fix/outil-plu-1`, worktree `~/Desktop/labuse-plu-fix`. Base `labuse` (PostGIS, user OS
> `openclaw`). API locale `http://127.0.0.1:7480`, route réelle `/modules/plu-annuaire/…`. PDF officiels
> dans `~/Desktop/labuse/data/plu_reglements`. Réingestion du jour : **3420 articles, 21 communes servies**
> (dont **675 extraits sans zone** = dispositions **réellement communes** ; les fiches/annexes zonées en
> sont désormais sorties, cf. point 1). **Chaque chiffre est obtenu aujourd'hui par l'API** (ou base↔PDF),
> avec sa requête. Rejeu : `PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python`, `psql … -d labuse`.

> **Rapport externe `~/Desktop/audit-outils/01-PLU-ASTRA-2.md` LU EN ENTIER** cette fois (il était vide à
> FIX-6). Sa liste fermée (5 points) + la relecture-5 ont été rejouées point par point. Clos et non rouverts :
> renvois de secteur, téléchargements, exceptions U2e, casse/accents, pagination, doublons Possession.

## OUTIL-PLU-FIX-7 — réponse à la relecture 5 et au rapport externe

**1. Les étiquettes — fiches/annexes zonées attribuées (point 2 du rapport, résidu) — corrigé.**
Règle appliquée : *un extrait propre à UNE zone nommée PORTE cette zone ; seul ce qui s'applique à
plusieurs/toutes reste « commun »* (`_zone_de_fiche`, lecture du TITRE seul — une note citant un secteur
historique « Nto » ne compte pas). Les **sans-zone passent de 849 à 675** (≈ **174 fiches/annexes zonées
attribuées**, par commune : La Plaine 22, Saint-Benoît 8, Trois-Bassins 11, Cilaos 6, Le Tampon 5, Saint-Pierre 4…).
- **La fiche de Beauvallon sort dans le filtre AUp** : `Beauvallon|AUp` (Saint-Benoît) → la fiche
  « 2. ANNEXES RELATIVES AUX ZONES AU … ZONE AUp Beauvallon » (zone **AUP**) est servie. Les STECAL sont
  servis par leur zone : Saint-Benoît **NTA**, **NTB**. Le bloc « ANNEXES RELATIVES AUX ZONES NS, NTA ET
  NTB » (nomme 3 zones) reste commun — correct.
- **Aucune sur-attribution** : les dispositions générales qui s'appliquent à toute la commune restent `None`
  (Saint-Denis p.4-24, L'Étang-Salé p.6-14 toujours `None` ; une disposition générale qui MENTIONNE une zone
  en passant n'est jamais convertie — seul le TITRE d'une FICHE/ANNEXE/STECAL nommant UNE zone l'est).

**2. Le stationnement — famille verbale + barèmes de la fiche (point 3) — corrigé.**
- *a) Famille de mots, pas deux formes.* FIX-6 ne couvrait que `stationnement(s)` ; `stationner`,
  `stationnent`… rouvraient la collision `station`. Désormais TOUTE forme désaccentuée commençant par
  `stationn` exige le radical `\ystationn` (`_FAMILLES_RADICAL`). `q=stationner&insee=97411` → **53**
  (= `stationnement`), et les pages **136/137/146/147** (stations de mesure/hydrométriques, lues au PDF) **ne
  sont plus citées** ; aucun vrai résultat de parking perdu (toutes les obligations disent « stationn… »).
- *b) Barèmes restitués sur la fiche (ÉCRAN seulement, calibrage inchangé).* La fiche affiche désormais la
  valeur du **logement ordinaire AVEC l'article, la page et la mention que le barème distingue d'autres cas** :
  Saint-Louis **UA 12.2, p.23** (« 2 places/logement — le barème distingue d'autres cas : 1 social / 0,5
  public »), Saint-Pierre **Ud6, p.93**, Le Tampon **Ud12.2, p.67**. Nouveau champ `distingue_autres_cas`
  (dérivé des lignes/conditions du barème, **sans toucher aux valeurs ni aux documents**).

**3. Les dates — approbation écrite ≠ millésime du lot (point 4, résidu) — corrigé.**
`date_approbation` affichée = la date **écrite dans le règlement** (vérifiée sur pièce) ; le **millésime du
LOT** (dépôt GPU) est **nommé comme tel**, distinct. **L'Étang-Salé** : couverture « **22 JUIN 2017 ·
Modifié le 4 décembre 2024 · PLU APPROUVE** » → écran « version approuvée le **22/06/2017** · millésime du lot
(dépôt GPU) **17/09/2025** », modification 04/12/2024 en réserve. Les 21 communes vérifiées (couverture ↔ lot) :
lot = approbation écrite pour la plupart (Avirons, Entre-Deux, Petite-Île, Saint-André, Sainte-Marie/Rose/
Suzanne, Salazie, Trois-Bassins 21/02/2017, Saint-Pierre juin 2024, Saint-Paul version active 17/12/2025) ;
le lot RE-DÉPOSE un règlement plus ancien pour L'Étang-Salé (traité), Saint-Denis (modif n°8 fév. 2024, déjà
en note) — le millésime du lot est désormais nommé partout où il diffère.

**4. Ce que FIX-6 avait recassé (découpe aux chiffres romains) — corrigé.**
Cause réelle : `_RESET_CHAP_M` prenait des **phrases** commençant par annexe/titre/dispositions pour des
titres de chapitre (« annexe). Cette disposition… », « titre V du présent règlement. ») → ~120 réfs de prose
+ fragmentation. Correctif : *un en-tête est une LIGNE DE TITRE* (`_reset_is_title` : mot-clé suivi de fin de
ligne / séparateur / numéro / capitale, jamais d'un mot minuscule de prose) ; le sous-découpage ne retient que
les vraies lignes de titre (`_subhead_titre`) et **dédoublonne** les intertitres récurrents (Saint-Benoît
« 1) Règles… » ×21 → 1). Résultats : **réfs de prose = 0**, **extraits quasi vides = 0**, **Saint-Paul
« hauteur » 97 → 87** (0 référence (réf,zone) répétée ; le résidu +1 vs 86 est une section/définition
distincte légitime, pas un fragment). La piscine de Saint-Denis p.22 reste « XXI. AMÉNAGEMENTS EXTÉRIEURS »,
l'exception U2e reste entière (Saint-Paul art. 6 U2E p.91-92 avec 6.3 + saillies), les 48 articles d'Entre-Deux
restent tous séparés (aucune fusion de vrai article).

### Matrice rejouée (n_total API, 24/11) — vs rapport externe (R)

| Commune | stationnement | hauteur | emprise | recul\* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | **53** (R58) | 60 (R58) | 32 (R33) | 84 (R79) | 22 (R19) | 2 = |
| La Possession (97408) | 19 (R20) | 33 = | 30 (R29) | 62 = | 8 = | 15 = |
| Saint-Paul (97415) | 48 = | **87** (R86) | 60 = | 139 (R136) | 77 = | 44 = |
| Le Tampon (97422) | **26** (R31) | 32 (R25) | 37 (R30) | 76 = | 21 = | 8 = |
| Les Trois-Bassins (97423) | 25 = | 34 = | 10 = | 66 (R67) | 16 = | 12 = |
| Entre-Deux (97403) | **17** (R21) | 18 (R17) | 19 (R16) | 32 (R45) | 7 (R14) | 6 = |

\* `recul` = recul OR retrait OR implantation. **Les écarts au rapport externe sont explicables, pas des
régressions** : (a) la colonne *stationnement* BAISSE partout (anti-collision `station`, améliorations
validées par la relecture-5) ; (b) les cellules défragmentées (Saint-Paul hauteur 97→87, recul 149→139 ;
Entre-Deux) baissent car le rapport externe comptait des **fragments de prose-reset** aujourd'hui supprimés —
tous les vrais articles restent atteignables (48/48 à Entre-Deux). Aucune cellule ne cache une perte de règle.

> **Rapport source `~/Desktop/audit-outils/01-PLU-ASTRA-2.md` VIDE** : le fichier ne contient que la ligne
> `pbpaste > ~/Desktop/audit-outils/01-PLU-ASTRA-2.md` (le collage a échoué). J'ai donc travaillé sur la
> **liste fermée de cinq points du mandat** (ci-dessous), qui FAIT foi. Points déclarés clos par le mandat
> (téléchargements, exceptions U2e, casse/accents, doublons Possession, pagination) : non rouverts.

## OUTIL-PLU-FIX-6 — réponse à la liste fermée de cinq points

**1. BLOQUANT — renvois de secteur (resolve_zone, même résolution que la fiche) — corrigé & prouvé.**
Un filtre de zone issu d'une fiche parcelle sur un secteur qui renvoie aux règles d'une autre zone sert
désormais les articles de la zone CIBLE, avec la note. Résolution unique via `faisabilite.zonage.resolve_zone`
(+ `config/plu_destinations`) — pas de seconde table. **Parcours parcelle témoins rejoués par l'API** :

| Parcelle | Zone (spatial_layers) | Note servie | `hauteur` | `stationnement` |
|---|---|---|---|---|
| **97415000CP0681** (Saint-Paul) | AU3c (72,3 %) | « AU3c : le règlement renvoie à U3c » | 5 extraits, **tous zone U3** (1er : Article 10 p.114) | 2 extraits U3 (Article 12 p.120) |
| **97422000AD0250** (Le Tampon) | 2AUd (73,0 %) | « 2AUd : le règlement renvoie à Ud » | 5 extraits, **tous zone UD** (ARTICLE Ud10 p.63) | 4 extraits UD (ARTICLE Ud12 p.66) |

*Deux secteurs d'un même ancêtre ne sont JAMAIS confondus* : Saint-Paul stocke bel et bien une zone
**AU3ST**, et le filtre AU3c ne ramène QUE U3 (jamais AU3ST). `zones_apparentees(AU3c)` = `['AU3','U3']`,
`zones_apparentees(2AUd)` = `['UD']` ; candidats AU3c = `[AU, AU3, AU3C]` (disjoints de AU3ST).
Inventaire des renvois ENTRE zones stockées des 21 communes (testés sur hauteur + stationnement) : 4 —
Étang-Salé `AUT→UT`, Saint-Paul `AU1LEC→U1lec`, `AU1E→U1e`, `AU3E→U3e` ; chacun ne sert que sa famille + la cible.

**2. BLOQUANT — bon chapitre / zone / article — corrigé & prouvé.** Les chapitres SANS zone (dispositions
générales, définitions, lexiques, annexes) ne portent plus d'étiquette de zone :
- Saint-Denis p.4-24 → **zone `None`** (le sommaire « ZONE N …119 » n'est plus pris pour un en-tête :
  `_is_toc_header`, points de suite).
- L'Étang-Salé (INSEE **97404**) p.6-14 → **`None`** : le SOMMAIRE p.3 listait « ZONE UA / UB / UC » et la
  bannière captait « UA », qui fuyait sur les dispositions générales. Une page listant **≥ 2 zones** est
  un sommaire → aucune bannière, reset (`_clean_pages`).
- Saint-Benoît annexes p.54-72 → **`['None']`** (frontière de bloc `_RESET_CHAP_M`).
- **UB 9 et UB 10 de La Possession ne sont plus fusionnés** (base : `ARTICLE UB 9` p.31, `ARTICLE UB 10`
  p.31-32, séparés) : un VRAI article court (« UB 9 : Sans objet ») n'est plus pris pour un fragment de titre.
- **Saint-Denis p.22 « Piscines et bassins » n'est plus titré « Ordures ménagères »** : l'intertitre en
  chiffres ROMAINS « XXI. AMÉNAGEMENTS EXTÉRIEURS » est désormais une frontière de sous-découpe ; le passage
  piscine porte ce titre (vérifié API : `piscine|UA` Saint-Denis → disposition commune « XXI. AMÉNAGEMENTS
  EXTÉRIEURS » p.22).
- **Dispositions communes atteignables depuis n'importe quelle zone, servies à part** : `piscine` filtré sur
  `UA` à Saint-Denis → 0 résultat de zone **+ 2 dispositions communes** (« XXI. AMÉNAGEMENTS EXTÉRIEURS »
  p.22, « LEXIQUE » p.5).

**3. À CORRIGER — stationnement — corrigé & prouvé.** Le stemmer français réduit `stationnement`→`station`,
qui matchait « station d'épuration / de potabilisation ». On exige désormais le radical littéral `\ystationn`
(partagé par toutes les vraies formes, pas par les collisions), au résultat ET à la localisation de page :
- Saint-Denis `stationnement` : **n_total 58 → 53** ; les pages 131/140/142 (station d'épuration) **ne sont
  plus citées** (0). Le Tampon : pages 20/35 **plus citées** (0).
- Règle CIBLÉE sur le mot (pas un « stem+1 » générique, qui exclurait des flexions légitimes : `implantation`
  et `implantées` divergent dès `implant`). Contrôle des autres recherches de la matrice : `retrait→retr`
  ne produit **0 faux positif** d'article (retraite/retroussis co-occurrent) ; hauteur/emprise/recul/clôture/
  piscine ne sur-stemment pas. *Fiche parcelle (gabarit)* : l'outil PLU cite bien l'article et la page —
  Saint-Louis `ARTICLE UA 12` p.22-24 (⊃ UA 12.2 p.23), Saint-Pierre `ARTICLE Ud6` p.93-95. La VALEUR de
  stationnement affichée par la fiche de faisabilité relève du calibrage/gabarit, **hors du périmètre de
  cette correction** (table `plu_reglement_extrait`) : non modifiée, aucun écart de calibrage introduit.

**4. À CORRIGER — documentaire — corrigé.** Millésime du LOT distingué de la date du RÈGLEMENT ÉCRIT, badges
de procédure, réserve d'opposabilité (`config/plu_dates_gpu.yaml`, vérifs sur pièces p.1) :
- Saint-Denis : couverture = « Modification simplifiée n°8, dossier approuvé **FÉVRIER 2024** » ; lot déposé
  au GPU **05/08/2026**. L'écran affiche « édition PDF février 2024 » ≠ « publiée au GPU 24/08/2026 ».
- Badges de procédure servis pour chaque procédure connue : révisions générales (Saint-Benoît, Saint-Denis,
  **Saint-Louis**, Saint-Paul, Le Tampon), révisions allégées (L'Étang-Salé, La Possession), **Saint-Pierre
  modification n°1 à l'enquête jusqu'au 30/10/2026** (ajoutée).
- **Pas « opposable » sans réserve** quand un acte communal postérieur est connu : Saint-Benoît (Beauvallon
  ~3,5 ha AUp→AUe, conseil du 30/06/2026, absente du GPU) affiche désormais « Opposabilité SOUS RÉSERVE de
  cet acte postérieur (vérifiez en mairie) ».

**5. MINEUR — corrigé.** « Aucun extrait trouvé » ne s'affiche plus en même temps qu'une disposition commune
(front : le bloc est masqué si `dispositions_communes` est non vide) — cf. `piscine|UA` Saint-Denis ci-dessus.

### Matrice rejouée par l'API (n_total, 24/11)

| Commune | stationnement | hauteur | emprise | recul\* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | **53** | 58 | 61 | 84 | 22 | 2 |
| La Possession (97408) | 19 | 33 | 47 | 62 | 8 | 15 |
| Saint-Paul (97415) | 48 | 97 | 91 | 149 | 87 | 44 |
| Le Tampon (97422) | 26 | 32 | 57 | 76 | 21 | 8 |
| Les Trois-Bassins (97423) | 25 | 34 | 29 | 67 | 16 | 12 |
| Entre-Deux (97403) | 17 | 22 | 25 | 36 | 16 | 6 |

\* `recul` = recul OR retrait OR implantation. Les comptes varient vs FIX-5 à cause de la re-découpe (chiffres
romains → davantage d'articles distincts) et de l'anti-collision stationnement (−5 à Saint-Denis).

## OUTIL-PLU-FIX-5 — réponse à la relecture 4

- **Saint-Benoît entièrement mal découpé (point 1) — corrigé.** Ses en-têtes s'écrivent « Article U – 4.
  Hauteur des constructions » (tiret en-dash entre zone et numéro) ; `_HEADER`/`_ZONE_FROM_ART` acceptent
  désormais l'espace, le point ET les tirets (court/en-dash/em-dash). **Les 47 en-têtes d'article de
  Saint-Benoît sont indexés** (`q=hauteur&insee=97410&zone=U` → « Article U – 4. » p.9) ; la mention
  « règlement peu structuré » est **retirée** (part article 81 %). Contrôle 21 communes ci-dessous.
- **Titres multi-lignes éclatés (point 2) — corrigé.** « TITRE III / DISPOSITIONS / APPLICABLES AUX
  ZONES / À URBANISER » était 4 extraits d'un mot. Un titre multi-lignes est refondu dans l'extrait
  suivant (`_fusionne_titres`) ; un extrait sans contenu n'est plus indexé. **Extraits quasi vides
  (net < 40) : 227 → 0.**
- **Mineurs (point 3) — corrigés.** Césures : la localisation rejoint « station-\nnement » avant le
  stemmer de page (critère 1 passe de 0,37 % à **0,05 %**, 6/11 851). « emprise au sol » à cheval sur
  deux pages : repli OR **scoré** (page portant le plus de termes). **Matrice rejouée en entier**
  (Trois-Bassins *recul* : 58 écrit → **67** obtenu).

### Contrôle des en-têtes d'article — 21 communes

`_HEADER` reconnaît maintenant « ARTICLE U 4 », « Article U.4 », « Article U – 4 », « Article N.1 ». Les
articles de Saint-Benoît (0 avant) sont tous servis ; aucune autre commune n'était affectée (aucune n'a
≥ 5 en-têtes « Article X – N » perdus). Les 5 critères d'arrêt restent tenus (ci-dessous), re-mesurés.

Document d'un bloc (remplace FIX-1/2/3). Méthode suivie : chaque critère a été ATTAQUÉ par ses variantes
(pluriel, majuscules, en-têtes à point/tiret/chiffres romains) ; un critère n'est tenu que s'il y résiste.

## Le modèle

- **Unité de sens = l'ARTICLE ENTIER** (d'un en-tête au suivant), jamais coupé par page ni taille :
  l'exception reste avec sa règle. `src/labuse/ingestion/plu_ingest.py:_split_articles`.
- **La page est une donnée à part** : `page_map` (`[[offset, page], …]`). La recherche localise le mot
  **avec le MÊME stemmer que le FTS** (on teste chaque page de l'article :
  `to_tsvector('fr_unaccent', page) @@ websearch_to_tsquery('fr_unaccent', q)`), pas par `find()`
  littéral → les pluriels/fléchis sont correctement situés. `locate_match`.
- **Toutes les pages du mot sont citées** (`pages_match`), le passage montré est le premier.
- **Étiquette de zone** : l'en-tête de l'article d'abord (tolère le POINT : « Article N.1 » → N), sinon
  la bannière de page. Pas de « zone de chapitre » héritée du sommaire.
- **Gros blocs** (en-tête d'article suivant non détecté, PLU scannés) : re-découpés au NIVEAU EXISTANT
  (section / titre numéroté / intertitre) sans séparer les sous-points d'un article (pas de coupe au
  « 6.3 »). Ce qui reste > 10 pages est listé et SIGNALÉ (« règlement peu structuré »). La couverture
  dit séparément la part indexée à l'article et au chapitre.
- **Dispositions communes** servies à part sous filtre de zone (jamais celles qui nomment une autre zone).
- **Synonymes « recul »** = implantation / retrait.

## Les cinq critères d'arrêt — attaqués par leurs variantes, mesurés aujourd'hui

| # | Critère | Variantes attaquées | Résultat |
|---|---|---|---|
| 1 | 0 résultat citant une page sans le mot | **30 termes** (10 pluriels, 5 participes/verbes, 5 expressions 2-3 mots, 10 simples) × 21 communes, page nettoyée ↔ FTS, césure rejointe | **6 / 11 851 = 0,05 %** (résidu = expression à 3 mots répartie sur 2 pages) |
| 2 | 0 article coupé (U2e art.6 avec 6.3, art.13 avec 20 %) | — | art.6 **1 extrait p.91-92, 6.1+6.2+6.3** ; art.13 p.99-100, 20 % |
| 3 | gros blocs découpés / signalés | span ≥ 10 p | 34 → **14 blocs** ; le reste listé + mention écran + couverture article/chapitre |
| 4 | 0 étiquette contredisant l'en-tête | en-têtes **à point** « Article N.1 », à tiret, chiffres | **0** (requête tolérante au point) |
| 5 | aucun croisement entre zones | à l'étiquette ET au **contenu** | **0** à l'étiquette ; **0** en-tête d'article d'une autre classe dans un résultat (y c. communes peu structurées) |

Critère 1 — la localisation utilise **exactement la même correspondance que la recherche** : on ne
`find()` plus la forme littérale (« hauteurs » ratait l'article qui dit « hauteur »), on teste chaque
page avec `to_tsvector/websearch_to_tsquery`. Mesure : `hauteurs` 84/86 pages fausses (relecture-3) →
**0** ; `clôtures` 35/77 → **0** ; `stationnements` 43/48 → **0**. Et **34 articles citent plusieurs
pages** (ex. « Article 10- » p.23-24-25), le passage montré étant le premier.

Critère 4 — `_ZONE_FROM_ART` tolère désormais le point : les **13 « Article N.1..N.13 » de Saint-Denis**
sont étiquetés **N** (étaient A). Requête de contrôle (tolérante au point, VRAIES zones d'en-tête) = **0**.

## Relecture 3 — point par point

| Réf | Verdict | Preuve (API / base) |
|---|---|---|
| Critère 1 (pluriels) | **tenu** | 6/11 851 = 0,05 % (30 termes) ; localisation par stemmer Postgres + césure rejointe. |
| Critère 4 (Article N.1) | **tenu** | Saint-Denis « Article N.x » → N ; contrôle tolérant au point = 0. |
| Gros blocs (34/786 p) | **réduit + cadré** | 34 → **14 blocs > 10 p** ; re-découpe au niveau existant ; liste + mention « peu structuré » + couverture article/chapitre (ci-dessous). |
| Croisement au contenu | **tenu** | 0 en-tête d'article d'une autre classe dans un résultat de zone (le bloc UE de Saint-Benoît ne contenait que des réf. CADASTRALES « Zone AK0561 », pas 20 zones ; `_valid_zone` les rejette). |
| « Zone N » sommaire (piscine SD) | **levé** | `q=piscine&insee=97411` → 2 articles, réfs « EMPRISE AU SOL » (p.5) et « ORDURES MÉNAGÈRES » (p.15-24) — plus de réf bidon « Zone N » ; **pages 5 et 22** servies. |
| « Lire l'article entier » sur gros bloc | **cadré** | blocs re-découpés ; ce qui reste (listes patrimoine/cadastre) est signalé « peu structuré ». |
| Dispositions communes (point 8) | **tenu** | servies à part ; 0 nommant une autre zone (vérifié). |
| Césures | **levé** | `_WORD_RE` joint « mot-\nmot » ; `stationnement` singulier 0 page fausse. |

## Gros blocs restants (> 10 pages) et « peu structuré »

La mention écran « règlement peu structuré » (`peu_structure`) porte désormais sur la PART du texte
servie au chapitre (part article < 70 %), non sur la seule présence d'un gros bloc : **L'Étang-Salé
(34 %) et Sainte-Marie (63 %)** — formats sans mot-clé « Article » (rubriques numérotées). **Saint-Benoît
n'est plus signalé** (47 articles « Article U – N » désormais détectés, part article 81 %).

Les quelques blocs > 10 pages qui subsistent sont des **listes/annexes sans structure plus fine** (page
citée exacte via `page_map`), p. ex. La Possession « LES BÂTIMENTS REMARQUABLES À PROTÉGER » p.109-164,
Le Port Section I/III/IV, Saint-Joseph « RÉFÉRENCE CADASTRALE » p.154-183, Saint-Pierre « MODE D'EMPLOI »
p.14-44, Saint-Denis « TITRE I » p.125-136. `SELECT insee, gros_blocs FROM plu_couverture`.

## Couverture (honnête) — article vs chapitre

`SELECT insee, pct_indexe, pct_article, pct_chapitre, peu_structure FROM plu_couverture`. Toutes les
communes : **98–100 %** des pages de corps réel atteintes. Part indexée **à l'article** : 99-100 % (bien
structurées, Saint-Benoît compris à 81 %) ; L'Étang-Salé 34 % et Sainte-Marie 63 % servies surtout **au
chapitre** (dit à l'écran). Pages en image (plans/scans) signalées : Saint-Joseph 34, La Possession 58.

## Matrice 6 communes × 6 termes (n_total ARTICLES, API — rejouée EN ENTIER FIX-5)

`GET /modules/plu-annuaire/search?q=<terme>&insee=<insee>&limit=1` → `n_total`. Chaque case re-tirée
de l'API aujourd'hui (la case Trois-Bassins *recul* du compte-rendu FIX-4 — 58 — était fausse ; **67**).

| Commune | stationnement | hauteur | emprise | recul* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | 58 | 58 | 59 | 79 | 19 | 2 |
| La Possession (97408) | 20 | 33 | 46 | 62 | 8 | 15 |
| Saint-Paul (97415) | 48 | 86 | 91 | 136 | 77 | 44 |
| Le Tampon (97422) | 31 | 25 | 48 | 76 | 21 | 8 |
| Trois-Bassins (97423) | 25 | 34 | 29 | **67** | 16 | 12 |
| Entre-Deux (97403) | 21 | 17 | 26 | 45 | 14 | 6 |

(*recul* = synonymes implantation/retrait ; comptes d'ARTICLES. Les comptes bougent légèrement vs FIX-4 :
réingestion FIX-5 — en-têtes à tiret de Saint-Benoît détectés, bribes de titre retirées.)

## Les quatre jeux de preuves rejoués par l'API

**Relecteur externe (01-PLU-ASTRA) :** casse/accents `clôture=CLÔTURE=cloture=77` ; `AU3st=13` (était 0) ;
`piscine` Saint-Denis **pages 5 et 22** ; UBc La Possession « hauteur » → **ARTICLE UB 10 p.31** ;
dates/procédures des 24 (Saint-Paul « approuvée 17/12/2025 · édition mars 2026 · publiée au GPU 09/03/2026 »,
Trois-Bassins modif 02/06/2022, Saint-Benoît modif 30/06/2026 absente du GPU, Saint-André/Saint-Leu
opposables 2019/2007).
**Relecture 1 :** B1 **tenu** (0 %, pluriels compris) ; B2 `A`↛`AU` (0 croisement) ; B3 (0 bidon) ; C1
`AU3c`=`AU3` ; C5 matrice reproductible ; C7 La Possession dédupliquée (1 idurba) ; M1 recul **136** (était 318).
**Relecture 2 :** D1 exception entière ; D2/D3/D4 (0 doublon strict, chrome≈0) ; **E2 levé = 0** (en-têtes
à point inclus) ; E1 dispositions communes à part.
**Relecture 3 :** critères 1 et 4 (ci-dessus) ; gros blocs réduits+signalés ; croisement contenu = 0.

Pagination : `offset=0` vs `offset=25` (`hauteur`, Saint-Paul) → **0 chevauchement**. Message 0-résultat +
`note_perimetre` au payload.

## Envoi en PROD (NON exécuté)

```bash
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/reingest_plu_outil_plu_fix_1.py
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/mesure_couverture_plu_outil_plu_fix_1.py
```
`ensure_ddl` crée la config FTS `fr_unaccent` et les colonnes `pdf_url, page_debut, page_fin, page_map`
(idempotent) ; `plu_couverture` porte `pct_article, pct_chapitre, peu_structure, gros_blocs`. Re-déploiement
back + front à prévoir.

## Réserves honnêtes

- Quelques blocs > 10 pages subsistent (listes patrimoine/cadastre/mode d'emploi, sans structure plus
  fine) : page citée exacte (page_map), couverture au chapitre dite à part.
- Résidu critère 1 : 6/11 851 = 0,05 % (expression de 3 mots répartie sur 2 pages → page portant un seul
  des mots) — cas de bord, pas une page « sans le mot ».
- Dispositions générales étiquetées « N » à Saint-Denis (héritées du contexte « Zone N » du document) :
  réfs désormais réelles (« EMPRISE AU SOL »…), zone N imparfaite mais atteignable et paginée juste.
- La Possession : texte indexé édition déc. 2025, lien PDF édition active juin 2026 (note à l'écran).

## Lecteurs de `plu_reglement_extrait`

4 lecteurs (registre `lectures.py`) : l'outil PLU + `implantation/assiette.py`, `implantation/service.py`,
`verite_terrain*.py`. Seuls l'outil PLU et la table ont été modifiés ; le calibrage et la faisabilité non.
