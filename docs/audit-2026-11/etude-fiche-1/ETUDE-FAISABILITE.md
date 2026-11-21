# L'Étude de faisabilité — comment elle marche, ce qu'elle vaut

*Audit ETUDE-FICHE-1 — lecture seule, branche `audit/etude-fiche-1` (base `origin/main`, commit de base `2b4c17d51`). Aucune correction, aucun déploiement. Tout ce qui est écrit ici décrit le code **réellement exécuté** le 11-12/11/2026 ; ce que je n'ai pas pu vérifier est signalé « non vérifié ».*

---

## Comment ça marche (en dix lignes)

1. Vous choisissez **1 à 8 parcelles contiguës** : LABUSE les fusionne en une seule « assiette » (comme l'Assemblage).
2. Vous choisissez un **type de projet** (résidence étudiante, senior, logement social, ou lotissement).
3. Vous **composez votre programme** : combien de T1, T2, T3, T4 — et le stationnement (aérien ou en sous-sol).
4. Vous cliquez **« Analyser »**. Le calcul tourne quelques dizaines de secondes, dans un processus séparé.
5. LABUSE lit les **règles du PLU** de la commune (reculs, hauteur, emprise, perméabilité, stationnement, mixité) et les **contraintes** (PPR, EBC…).
6. Il **retire les reculs et le PPR rouge** de l'assiette → il reste une « zone d'implantation ».
7. Il **dessine** dans cette zone une ou deux **barres** de bâtiment (profondeur fixe 13 m), empile des niveaux, place le parking et un accès.
8. Il **découpe** la barre en logements selon vos T1–T4, compte les places imposées, mesure l'emprise et la hauteur.
9. Il **confronte** ce dessin aux règles : chaque contrôle est *Réussi / Échoué / À confirmer / Non effectué / Non applicable*.
10. Il affiche un **plan masse**, une **coupe**, un tableau **réglementaire vs projet**, un verdict — et un **PDF** qui reprend exactement les mêmes chiffres.

> **La boussole de l'outil (à retenir) :** LABUSE ne cherche pas à *remplir* la parcelle comme le ferait un architecte. Il pose une forme simple et prudente (barre de 13 m), tout stationnement **aérien** par défaut, et **soustrait le risque** (PPR). Résultat mesuré sur 4 cas réels : il **sous-estime** le nombre de logements d'un collectif (de 0,38× à 0,97× l'architecte) et **surestime** un peu un lotissement (1,20×). Voir § *Comparaison aux architectes*.

---

## 1. Le parcours, écran par écran

L'outil a **quitté le menu Outils** : il s'ouvre en overlay plein écran depuis la 9ᵉ carte des Documents, une tuile de la fiche parcelle, ou le pont Assemblage (`frontend/src/components/outils/EtudeEcran.tsx`, `registry.ts:121` → `hidden:true`). Le composant du parcours est `frontend/src/components/outils/EtudeV6.tsx`.

| Étape | Écran | Ce qu'on y fait | Appel serveur |
|---|---|---|---|
| ① | **Choix des parcelles** (`EtapeParcelles`) | On saisit une adresse / IDU / référence, on ajoute jusqu'à 8 parcelles. LABUSE affiche contenance, surface réelle, zone PLU, règles de l'assiette, et surtout la **contiguïté** (bloquant si non contiguës). | `POST /modules/etude/parcelles` |
| ② | **Type de projet** (`EtapeType`) | 4 pavés : *Résidence étudiante · Résidence senior · Logement social · Lotissement* (`EtudeV6.tsx:74-77`). Dès le choix, la **règle de stationnement** applicable et la **mixité sociale** s'affichent. | `POST /modules/etude/stationnement` |
| ③ | **Votre programme** (`EtapeProgramme`) | On fixe le nombre de T1/T2/T3/T4 (ou, en lotissement, la taille de lot et la largeur de voirie). On choisit **Aérien / Sous-sol** (sous-sol grisé si PPR ou interdit). Une **jauge** estime « ≈ N logements » avant calcul. | `POST /modules/etude/jauge` |
| ④ | **Calcul** | Bouton « Analyser mon projet → ». Animation d'attente ; borne dure 60 s. | `POST /modules/etude` |
| ⑤ | **Résultat** | Verdict, 2 chiffres (logements tenus/demandés, surface du programme), **plan masse**, **coupe**, tableau **surfaces**, bloc **« ce qui limite »**, **contrôles**, bouton **« Générer le PDF »**. | — (même payload) |

Captures WebKit (Safari 18.2, 1440×900) dans `captures/` : `01-etape1-parcelles` … `06-resultat-complet-social-aerien`, et les variantes par type / sous-sol / lotissement / cas limites (voir l'index en fin de fiche).

Les boutons de navigation (Retour / Continuer / Analyser) sont dans la colonne de droite (`PiedEtape`, `EtudeV6.tsx:1251-1253`). **Aucun calcul n'a lieu dans le navigateur** : tout vient du serveur.

---

## 2. Les données lues (source · table · millésime)

Toutes lues dans un **processus enfant** avec session DB fraîche (`modules.py:2108 _worker_etude`). Le terrain est chargé par `src/labuse/implantation/terrain.py:charger`.

| Donnée | Source / table | Colonne | Remarque |
|---|---|---|---|
| Géométrie parcelle | `parcels` | `geom_2975` (EPSG:2975), `contenance_m2` | Fusion `ST_Union(geom_2975)` (terrain.py:171-186). |
| Zone PLU + famille | `spatial_layers` `kind='plu_gpu_zone'` | `subtype` → `labuse_zone_famille(subtype)` | terrain.py:123-127. |
| Règles chiffrées du PLU | **config calibrée** `labuse.plu.destinations.regles_zone(insee, zone)` | reculs, hauteur égout/faîtage, CES, pleine terre, stationnement, mixité | regles.py:326-365. Chaque règle porte un **statut** (`validée`+citation) et une **page PDF**. |
| PPR | module unique `labuse.ppr` (fonction SQL `labuse_ppr_couleur`) | rouge = interdiction (retirée de la zone), bleue = prescription (signalée) | terrain.py:95-108, 274-276. |
| Pente | profil altimétrique **LiDAR / RGE ALTI** (réseau requis) | `pente_moyenne_pct`, `pente_max_pct` | terrain.py:143-162. **Fait contextuel seulement** — n'entre pas dans le dessin. |
| EBC / ER / SUP / servitudes | `spatial_layers` (`_CONTRAINTES`) | comptage d'intersection | terrain.py:23, 284-289 — **signalés**, pas modélisés géométriquement (sauf EBC retiré de la zone). |
| Distance TCSP (plafond stationnement) | `moteur._tcsp_dist_m` (stations `tcsp_station`) | distance < 800 m | service.py:617-623. |
| Millésime PLU | `plu_reglement_extrait` | `max(millesime)` | service.py:626-633. Affiché « p. N » + lien Géoportail de l'urbanisme (`idurba`). |

**Hypothèse forte non lue en base : le terrain est supposé NU.** Le champ `terrain:"libere"` (EtudeIn, défaut) dit « on raisonne comme si le sol était libéré ». Le bâti existant **n'est pas soustrait** de la capacité par le moteur d'implantation ; la pente LiDAR est lue mais le terrain est traité **comme plat** pour le dessin (aucune cote altimétrique dans la géométrie). → voir Doutes #2 et #4.

---

## 3. Le moteur : ce qu'il fait vraiment

Fichiers : `src/labuse/implantation/{moteur,geometrie,capacite,controles,terrain,lotissement,service}.py` + constantes `config/implantation_conventions.yaml`.

### 3.1 Comment il place le bâtiment

1. **Zone d'implantation** = assiette fusionnée **inset des reculs** (voie + séparatives), **moins** le PPR rouge, **moins** l'EBC (terrain.py). C'est la seule surface où LABUSE a le droit de bâtir.
2. **Repère** (`Frame.depuis`, geometrie.py:38) : on tourne la zone pour aligner son grand axe sur X.
3. **Recherche en grille déterministe** (`moteur._rechercher`, moteur.py:243) : on essaie **chaque combinaison** de :
   - **forme** ∈ `["barre", "deux_barres", "L"]` (moteur.py:37) — une barre simple, deux barres parallèles, ou un L ;
   - **niveaux** ∈ `[1,2,3,4,5,6]` = R+0 à R+5 (moteur.py:28) ;
   - **fraction** d'occupation de la largeur de zone : `1.00 → 0.30` par pas de 0,05 (de 0,10 sur grande assiette) (moteur.py:30,35).
4. Pour chaque candidat, `poser_barre` (geometrie.py:278) glisse une bande de **profondeur 13 m** le long de la zone, cherche le plus long segment contenu (`_meilleure_bande`, `_bande_x`), et **plaque le bâtiment du côté opposé à la voie**.
5. On garde le **meilleur candidat faisable** selon l'objectif (`_clef`, moteur.py:194). L'étude en ligne vise « équilibre » (le plus de logements qui tiennent).
6. **Budget de temps : ~22 s** (moteur.py:289, `LABUSE_ETUDE_GRILLE_BUDGET_S`) sous la borne dure de 60 s. Au-delà, on rend le meilleur trouvé, ou « simulation impossible ».

**Conséquence de forme :** LABUSE ne pose au plus que **deux volumes** (deux barres, ou un L). Il ne compose jamais 4–5 plots comme un architecte. C'est la cause n°1 du sous-dimensionnement des grands collectifs (§ Comparaison).

### 3.2 Le stationnement

- **Aérien (défaut)** : `poser_stationnement` (geometrie.py:315) place des places **2,5 × 5 m** (conventions l51-52), des allées de desserte **5 m** (l53), un accès **4 m** (l54) sur le sol restant, puis relie allées → accès → voie.
- **Sous-sol (au choix, 1 ou 2 niveaux)** : `poser_sous_sol` (geometrie.py:452) enterre les places à **25 m²/place circulation comprise** (l55), avec une **rampe 3,5 m de large, pente max 18 %** (l56-57), hauteur de niveau 3 m (l58). Le sol **n'est pas entamé** par le parking → plus de logements possibles. L'emprise enterrée est confrontée à l'emprise réglementaire ; la part « sur dalle » est retirée de la pleine terre (capacite.py:120-131).
- **Nombre de places imposé** = barème PLU appliqué par logement (`BaremeStationnement.places_pour`, regles.py:65), plafonné par la loi : **L.151-35** (logement aidé / RPA / résidence universitaire) = au plus 1 place/logt, **0,5 à moins de 800 m d'un TCSP** (`_ratio_l15135`, service.py:613 ; rayon porté à 800 m par la loi 2025-1129).

### 3.3 L'accès

Un **seul** débouché (largeur 4 m) est tracé entre le parking et la voie (`_acces_corridor`, geometrie.py:424). Si **aucune voie classée** ne touche la parcelle, l'accès est **hypothétique** → le contrôle « Accès (voie) » passe « À confirmer » et interdit le verdict « Exploitable » (controles.py:530).

### 3.4 Règles du PLU : appliquées vs ignorées

| Règle PLU | Appliquée ? | Comment |
|---|---|---|
| Reculs (voie, séparatives) | **Oui, géométriquement** | Inset de la zone d'implantation (le bâti ne peut pas en sortir). |
| Hauteur (égout ou faîtage) | **Oui** | `hauteur_projet_m` (controles.py:45) : niveaux × 3 m, + 2,5 m de toiture **si la règle se mesure au faîtage**. |
| Emprise au sol (CES) | **Oui** | Emprise mesurée sur le dessin ≤ CES × surface (controles.py). |
| Perméabilité (pleine terre) | **Oui** | Pleine terre mesurée ≥ % × surface. |
| Stationnement | **Oui** (barème + plafonds L.151-35/36) | Mais au **pied de la lettre** : ignore les dérogations locales (ex. RPA 1 place/3 logts — voir Doute #5). |
| Mixité sociale | **Partiel** | Calcule la SDP aidée = SDP × quota si SDP > seuil (capacite.py:170-182), **affichée** mais non imposée au dessin. |
| PPR rouge / bleue | **Oui** | Rouge retiré de la zone ; bleue signalée « À confirmer ». |
| EBC | **Oui** (retiré de la zone) | |
| Prospect (hauteur relative L ≥ H/2) | **Non chiffré** | « À confirmer » systématique si la règle existe (controles.py). |
| Destinations / mixité fonctionnelle (commerces, bureaux) | **Non** | LABUSE ne dessine **que du logement**. |
| Espaces verts / marge plantée détaillée | **Partiel** | Souvent « À confirmer » (donnée insuffisante). |
| Accessibilité PMR, locaux vélos, stationnement visiteurs détaillé | **Non** | Non modélisés. |
| Pente réelle du terrain, déblais/remblais, gestion des eaux pluviales | **Non** | Pente lue mais terrain traité comme plat. |

### 3.5 Toutes les hypothèses et constantes (valeur · origine · fichier:ligne)

Chaque valeur ci-dessous est **« Estimé »** — jamais une règle du PLU (`config/implantation_conventions.yaml:3-6`). Une valeur « Estimé » ne peut jamais produire un contrôle « Réussi ».

| Constante | Valeur | Rôle | Ligne |
|---|---|---|---|
| `profondeur_m` | **13,0 m** | profondeur d'une barre (bâtiment traversant) | conventions.yaml:13 |
| `largeur_coursive_m` | 1,4 m | coursive extérieure de desserte (non habitable) | :14 |
| `surface_noyau_m2` | 20,0 m²/niveau/bât. | escalier + ascenseur + palier | :15 |
| `max_logements_par_noyau` | 6 | au-delà, un noyau de plus | :21 |
| `longueur_max_coursive_par_noyau_m` | 30,0 m | distance d'évacuation | :22 |
| `hauteur_etage_m` | **3,0 m** | hauteur d'un niveau | :23 |
| `toiture_m` | 2,5 m | acrotère, **ajouté seulement si la règle se mesure au faîtage** | :24 |
| `coef_plancher_habitable` | **0,80** | plancher → habitable (SHAB) | :28 |
| `retrait_inter_barre_m` | 6,0 m | jeu entre deux volumes ; aussi distance inter-bâtiment de convention | :29 |
| `inset_zone_m` | 0,1 m | marge pour rester dans la zone | :33 |
| Surfaces logement | **T1 30 · T2 56 · T3 70 · T4 80 m²** (varangue comprise) | surface moyenne par type | :41-44 |
| `repartition_equilibre` | **[T2, T3, T2, T4, T2, T3]** (≈50/33/17 %) | mix proposé si « équilibre » | :48 |
| Place de parking | **2,5 × 5 m** | dimensions usuelles | :51-52 |
| `allee_largeur_m` | 5,0 m | allée double sens | :53 |
| `acces_largeur_m` | 4,0 m | débouché sur voie | :54 |
| `m2_par_place_sous_sol` | **25,0 m²** | place enterrée, circulation comprise | :55 |
| `rampe_largeur_m` / `rampe_pente_max_pct` | 3,5 m / **18 %** | rampe de sous-sol | :56-57 |
| `hauteur_sous_sol_m` | 3,0 m | → longueur de rampe = h / pente | :58 |
| **Lotissement** `LOT_CIBLE_M2` | **450 m²** | taille de lot visée (aucun minimum PLU, loi ALUR) | lotissement.py:24 |
| `VOIRIE_LARGEUR_M` | 5,0 m | chaussée (hypothèse) | :25 |
| `LOT_FACADE_MIN_M` | 12,0 m | façade mini sur voirie | :28 |
| `TOURNE_FACTEUR` | 2,2 | côté de l'aire de retournement | :30 |
| Grille de recherche | niveaux R+0→R+5 ; fractions 1,00→0,30 ; formes barre/2-barres/L | — | moteur.py:28-37 |
| Budget moteur | **~22 s** (borne dure API 60 s) | — | moteur.py:289 ; config.py:64 |
| Terrain | **supposé nu** (`terrain:"libere"`) | — | modules.py:2061 |

---

## 4. Chaque chiffre affiché : d'où il vient

Toute valeur affichée porte un **statut** (mesuré · dérivé · non vérifié) — `service._grandeurs` (service.py:256).

| Chiffre à l'écran | Origine | Sourcé / Estimé |
|---|---|---|
| Contenance, surface réelle, écart | `parcels.contenance_m2`, `ST_Area(geom_2975)` | **Sourcé** (cadastre) |
| Zone PLU | `spatial_layers` | **Sourcé** |
| Reculs, hauteur, CES, pleine terre, stationnement, mixité **réglementaires** | `plu.destinations.regles_zone` (+ citation article/page) | **Sourcé** (PLU calibré) |
| PPR rouge/bleue (m²) | intersection géométrique `labuse.ppr` | **Sourcé** |
| Pente | LiDAR / RGE ALTI | **Sourcé** (contextuel) |
| Logements, places, emprise, SDP, pleine terre **du projet** | **mesurés sur le dessin** (capacite.py:90) | **Estimé** (dépend des conventions 13 m / 3 m / 0,80…) |
| Surfaces T1–T4, varangues | conventions (ou votre saisie) | **Estimé** |
| SHAB | modules × 0,80 | **Estimé** |
| SDP *autorisée*, emprise *mobilisable* | **dérivées** d'une règle PLU × surface **dessinée** (`aire_dessin_m2`, pas la contenance !) | Dérivé — attention : base = zone dessinée (Doute #7) |
| Places imposées | barème PLU + plafond L.151-35 | **Sourcé** (règle) appliqué au nb de logements **estimé** |
| Jauge « ≈ N logements » (étape 3) | estimation enveloppe avant calcul | **Estimé** |
| N° de document `EF-xxxxxxxx` | hash du study_id | déterministe |

**Point important :** l'emprise *mobilisable* et la SDP *autorisée* sont calculées sur `terrain.aire_dessin_m2` (la zone constructible dessinée), **pas** sur la contenance cadastrale (service.py:264-281). C'est cohérent avec le contrôle d'emprise, mais peut surprendre (un « reste mobilisable » plus petit qu'attendu). Voir Doute #7.

---

## 5. Les contrôles : ce que chaque statut veut dire

Cinq états (controles.py:25-34) :

| Statut | Sens | Couleur |
|---|---|---|
| **Réussi** | règle `validée` + citée **et** la mesure la respecte | vert |
| **Échoué** | règle validée, mais la mesure la dépasse | rouge |
| **À confirmer** | ambiguïté de **donnée ou de texte** (PPR présent, prospect non chiffrable, servitude, barème manquant, accès hypothétique) | ambre |
| **Non effectué** | règle non servie / non modélisée (ex. locaux vélos) — **jamais** « Réussi » | gris |
| **Non applicable** | la contrainte est **absente** du terrain | gris |

**Verdict global** (`verdict_global`, controles.py) traduit en 3 mots :
- **Impossible pour cause établie** (assiette inconstructible, dépassement prouvé) ;
- **À compléter** — dès qu'un contrôle est *Échoué*, OU qu'un contrôle **bloquant** est *À confirmer* (PPR rouge/bleue, Stationnement, Prospect, ER/EBC/SUP, Accès — `_A_CONFIRMER_BLOQUANTS`, controles.py:530), OU que l'accès n'est pas établi ;
- **Exploitable sous hypothèses** — tous les contrôles durs *Réussi*, aucun bloquant *À confirmer*.

**Ce qui n'est JAMAIS contrôlé** (même quand la règle existe) : le **prospect** (L ≥ H/2, toujours « À confirmer »), l'**accessibilité PMR**, les **locaux vélos**, le **stationnement visiteurs** détaillé, la **gestion des eaux pluviales**, la **pente/géotechnique réelle**, les **destinations** (commerces/bureaux), l'**intégration paysagère / ABF**, et toute **dérogation locale** au barème de stationnement.

---

## 6. Le PDF dit-il la même chose que l'écran ?

**Oui — par construction.** Le PDF (`src/labuse/exports/etude_faisabilite.py`, moteur WeasyPrint hors-processus) **ne recalcule rien** : il reçoit le **même payload** que l'écran (`POST /modules/etude/pdf`, modules.py:2470) et le rend (`rendu_etude`, etude_faisabilite.py:988). Mêmes SVG (plan masse, coupe, planche), même choix de scénario (`scenario_retenu`, :126).

Un **verrou automatique** interdit au PDF d'afficher un chiffre qui ne serait pas dans le payload : `nombres_hors_payload` (etude_faisabilite.py:1191) extrait tous les nombres du HTML et refuse (échec CI) tout nombre absent du payload (hors pagination, dates, codes CRS, références cadastrales).

**Pages du PDF** (chacune rendue en image dans `pdf/`) :

| Page | Fonction | Contenu |
|---|---|---|
| P1 Synthèse | `_p1_synthese` (:417) | verdict, programme, 6 tuiles clés, stationnement/mixité |
| P2 Terrain | `_p2_terrain` (:537) | parcelles, pente, limites, accès, plan parcelle |
| P3 Règles & contraintes | `_p3_regles` (:583) | tableau PLU cité, PPR/EBC/SUP |
| P4 Enveloppe | `_p4_enveloppe` (:649) | zone d'implantation après reculs |
| P5 Plan masse (+ sous-sol, + planche) | `_p5_plan_masse` (:700) | forme, niveaux, SVG, tableau surfaces |
| P6 Distribution & coupe | `_p6_distribution` (:796) | répartition par niveau, coupe |
| P7 Capacité & contrôles | `_p7_capacite` (:833) | programme, tableau contrôles 5 états |
| P8 Hypothèses & sources | `_p8_hypotheses` (:887) | toutes les conventions « Estimé », sources |
| Annexe | `_annexe_reglement` (:937) | citations verbatim des règles |

**Deux nuances mesurées :**
1. Le verrou garantit l'identité des **chiffres par rapport au payload**, pas l'identité de **mise en page** (aucun test ne compare visuellement écran et PDF — §7).
2. **Le PDF RECALCULE le payload** dans son propre processus (`_worker_etude_pdf`, modules.py:2122, appelle `etudier_payload`) — il ne reçoit pas le payload déjà affiché. Comme le moteur est **borné en temps** (§8), un PDF rendu sur un processus plus lent peut imprimer un scénario **plus petit** que l'écran. Observé ici : à budget 22 s le PDF montrait **14 logts R+1**, à budget complet **18 logts R+2** (= l'écran). Le PDF versionné dans `pdf/` a été rendu à budget complet pour refléter l'écran. → Doute #1.

> **Observation annexe (bug d'environnement) :** sur ce poste, `POST /modules/etude/pdf` échoue en **HTTP 500** — `AssertionError: daemonic processes are not allowed to have children` (modules.py:2491). Le rendu PDF est lancé dans un processus (ETUDE-ASYNC) qui tente lui-même de lancer WeasyPrint dans un sous-processus (NU4-FIX-1) — imbrication interdite. Le PDF de cette fiche a donc été rendu **en direct** (`LABUSE_PDF_PROCESS_ISOLE=0`, rendu in-process), ce qui prouve que le code de rendu fonctionne. À vérifier en production (le réglage `pdf_process_isole`/systemd peut différer). → Doute #8.

---

## 7. Tests existants — et ce qu'aucun test ne vérifie

**Tests présents** (backend `tests/`, frontend `*.test.tsx`) :

- `test_etude_v6_8_pdf.py` — extrait le texte du PDF (pdftotext) et vérifie : une seule implantation (votre programme), nb logts = nb places plafonné L.151-35, statut recalculé, une seule règle de stationnement en §2, un seul n° EF-…, sous-sol (rampe comptée, pleine terre ≥ 30 %).
- `test_etude_v6_capacite.py` — capacité stable, typologie respectée (pas de substitution T1↔T4), **une seule vérité** sur le programme dessiné (tenus = résumé = places), mixité correcte.
- `test_etude_v6_assiette.py` — contiguïté, géométrie multi-parcelles.
- `test_etude_v6_stationnement.py` — régime (général, plafond national), modes aérien/sous-sol.
- `test_etude_v6_lotissement.py` — tableau des lots, pleine terre, bilan surfacique.
- `test_etude_async.py`, `test_etude_zone_determinisme.py` — processus séparé, déterminisme.
- `test_fixfinal_etude_hors_perimetre.py`, `test_recette4_etude_acces.py` — hors-périmètre, accès « à confirmer ».
- Front : `EtudeV6.test.tsx`, `Etude.test.tsx`, `Faisabilite.test.tsx` — flux 3 étapes, aucun calcul front, 0 scénario = message.

**Ce qu'aucun test ne vérifie** (confirmé par lecture, à confirmer par un run complet) :
- **Rendu du PDF lui-même** (WeasyPrint) : le test d'extraction est marqué `@pytest.mark.reel` et **sauté localement** (poppler requis).
- **Fidélité visuelle écran ↔ PDF** (mise en page, sauts de page, pagination).
- **Rendu des SVG** (plan masse, **coupe**, planche) : couleurs, ordre des calques, géométries — aucun test de forme.
- **Parcelles non contiguës** : le refus est mentionné mais aucun test d'assertion sur le message.
- **Exactitude du nombre de places dessinées** = places imposées, dans le PDF.
- **Complétude du tableau réglementaire** (toutes les règles présentes).
- **Déterminisme du PDF** (même hash pour même entrée).
- **Hypothèses éditées par l'utilisateur** qui circulent jusqu'au PDF.
- **Le temps de calcul** (aucun test de performance).

---

## 8. Le temps de calcul mesuré

Mesuré sur ce poste (Mac 8 cœurs), `POST /modules/etude`, backend chaud, un seul appel à la fois (`/usr/bin/time -p`) :

| Cas | Parcelles | Type | Temps | Résultat |
|---|---|---|---|---|
| Étang-Salé | 4 | social | **25,7 s** | Exploitable · capmax 28 |
| Saint-André | 2 | social | **28,7 s** | À compléter · capmax 21 |
| Saint-Denis | 2 | senior | **19,9 s** | À compléter · capmax 12 |
| Saint-Leu | 3 | lotissement | **5,4 s** | À compléter (lotissement) |
| Étang-Salé sous-sol | 4 | social | **16,5 s** | Exploitable · capmax 32 |

- Le collectif coûte **15 à 30 s** (la recherche en grille explore formes × niveaux × fractions jusqu'au **budget ~22 s**, moteur.py:289). Le lotissement est **5×** plus rapide (pavage direct, pas de grille).
- **Important — le résultat dépend du budget de temps, donc de la charge/vitesse de la machine.** À budget réduit (22 s, processus froid) la même assiette Saint-André rendait **14 logements R+1** ; à budget complet (150 s) elle rend **18 logements R+2** (capmax 21). La recherche garde « le meilleur trouvé avant la borne » : sur une machine lente ou chargée, elle s'arrête plus tôt sur un scénario **plus petit**. → Doute #1.

---

---

## 9. Comparaison aux quatre études d'architectes

Détail complet et JSON bruts : `COMPARAISON-ARCHITECTES.md` et `replays/`. Synthèse :

| Cas | Type | LABUSE | Architecte | Ratio |
|---|---|---|---|---|
| Étang-Salé (AW99/451/624/625, UA, 1 746 m²) | collectif | **28** logts · 30 pl · R+3 · emprise 614 m² · SDP 2 190 m² | 29 logts · 31 pl (1 aérien) · R+3 · 710 m² · 2 368 m² | **0,97** |
| Saint-André (AX255/256, UC, 4 163 m²) | collectif | **18** logts · 27 pl · R+2 · 608 m² · 1 627 m² | 48 logts · 48 pl · R+2 · — · 2 568 m² | **0,38** |
| Saint-Denis RPA (DL247/248, Ui, 1 580 m², PPR) | senior | **12** logts · 12 pl · R+3 · 258 m² · 920 m² | 22 logts (plan 27) · 8 pl · ~R+3 · 377 m² | **0,55** |
| Saint-Leu (AC261/262/264, UD) | lotissement | **36** lots (moy 407 m²) · 2 pl/lot | 30 lots (16+14) · 2 pl/lot | **1,20** |

*Note cadastre : la parcelle **AC0263 est absente** de la table `parcels` ; le rejeu lotissement a porté sur 3 parcelles (AC0261/0262/0264) au lieu de 4.*

**Causes des écarts** (toutes vérifiées sur les payloads) :
1. **Forme bâtie** : barre / 2 barres / L de profondeur 13 m sur la seule zone d'implantation — ne remplit pas la parcelle comme un architecte (cause dominante, surtout Saint-André ×2,7).
2. **Stationnement 100 % aérien par défaut** : mange l'assiette ; l'architecte enterre (Étang-Salé : parité à ±1 car l'écart vient de là).
3. **Prise en compte du PPR** rouge **+ bleue**, absente des plans d'architecte (décisif : Saint-André zone d'implantation 2 006 m² sur 4 163 ; Saint-Denis 649 m² sur 1 580).
4. **Barème de stationnement au pied de la lettre** : ignore la dérogation RPA 1 place/3 logts → LABUSE affiche **plus** de places que l'architecte (12 vs 8) malgré **moins** de logements.
5. **Hauteurs réglementaires strictes** — mais **concordantes** avec l'architecte dans les 3 cas (R+3, R+2, ~R+3).
6. **Lotissement surdimensionné** : pavage déterministe au lot de 450 m² (jusqu'à 251 m²), voirie légère → 36 lots vs 30 ; LABUSE le dit lui-même « pré-lotissement indicatif ».

---

## 10. Mes doutes (10, par gravité)

### Peut tromper un promoteur
1. **Le résultat n'est pas reproductible — il dépend de la vitesse de la machine.** La recherche en grille est **bornée en temps** (~22 s, moteur.py:289) et garde « le meilleur trouvé avant la borne ». Même entrée Saint-André : **14 logements R+1** (budget 22 s, froid) vs **18 logements R+2** (budget complet). Un promoteur peut obtenir deux chiffres différents selon la charge, et — comme le PDF **recalcule** — un **PDF qui contredit l'écran**. *C'est le doute le plus grave.*
2. **Sous-estimation systématique des collectifs.** Sur de grandes parcelles, LABUSE affiche 0,38 à 0,55× le nombre de logements d'un architecte (Saint-André 18 vs 48). Cause : forme barre/L de profondeur fixe 13 m sur la seule zone d'implantation, + stationnement 100 % aérien par défaut. Risque : **écarter une parcelle rentable**. Le verdict dit « ce qui limite » mais le chiffre mis en avant reste bas.
3. **Stationnement surestimé par application littérale du barème.** À Saint-Denis (RPA), LABUSE impose **1 place/logement** et ignore la **dérogation RPA 1 place/3 logements** → 12 places affichées contre 8 réelles. Un promoteur de résidence senior voit un besoin de parking (donc un coût) surévalué.
4. **Le terrain est supposé nu, sans le dire assez fort.** La capacité est calculée comme si le sol était libre (`terrain:"libere"`). Sur une parcelle **déjà bâtie**, rien n'est déduit : le chiffre affiché n'est pas un **potentiel net** (après démolition/conservation de l'existant).

### Fait désordre
5. **Lotissement surdimensionné.** Pavage déterministe au lot de 450 m² (jusqu'à 251 m²), sans superficie minimale ni desserte/pente réelle → 36 lots contre 30 à l'architecte. LABUSE prévient « pré-lotissement indicatif », mais le nombre est mis en avant.
6. **La pente est lue mais le terrain est dessiné plat.** À Étang-Salé, « hauteur sur la pente (relief 4,5 m) » apparaît comme **1ᵉʳ facteur limitant** alors que la géométrie ne modélise aucun relief (ni déblai/remblai, ni rampe adaptée au terrain). Message et dessin semblent se contredire.
7. **Le prospect n'est jamais chiffré.** Dès qu'une règle de hauteur relative (L ≥ H/2) existe, le contrôle reste « À confirmer » et **interdit** le verdict « Exploitable » même si tout le reste passe. Impression d'étude inachevée.
8. **Le PDF peut échouer en production.** Sur ce poste, `POST /modules/etude/pdf` renvoie **HTTP 500** (`daemonic processes are not allowed to have children`, imbrication processus étude × processus WeasyPrint). À vérifier selon la config de prod (`pdf_process_isole`/systemd). Par ailleurs, « emprise mobilisable » et « SDP autorisée » se calculent sur la **zone dessinée** (`aire_dessin_m2`), pas la contenance cadastrale — un lecteur peut mal interpréter le « reste ».

### Sans conséquence
9. **La parcelle AC0263 (Saint-Leu) est absente de la table `parcels`** : le rejeu lotissement a porté sur 3 des 4 parcelles. C'est une lacune de **donnée**, pas du moteur ; sans effet sur le produit.
10. **Sur une très grosse assiette, le budget de 22 s peut rendre « simulation impossible ».** Rare, message honnête, relançable (un 2ᵉ passage « faisable-probable » récupère la plupart des cas, moteur.py:346).

---

## Index des captures (WebKit, `captures/`)

| Fichier | Contenu |
|---|---|
| `01-etape1-parcelles` | Étape 1, Saint-André AX255+256, règles PLU + contiguïté |
| `02-etape2-type-projet` | Les 4 types de projet |
| `03-etape2-type-choisi-social` | Type « logement social » choisi + régime stationnement |
| `04-etape3-programme-aerien` | Composition T1–T4 + stationnement aérien + jauge |
| `05-calcul-en-cours` | Écran de calcul |
| `06-resultat-complet-social-aerien` | Résultat complet : plan masse, surfaces, « ce qui limite », contrôles |
| `07-resultat-plan-masse` | Plan masse (zoom SVG) |
| `10/11/12-type-{etudiante,senior,social}-aerien-{etape3,resultat}` | Les 3 types collectifs, aérien |
| `13-type-social-sous-sol-{etape3,resultat}` | Stationnement en sous-sol (Étang-Salé) |
| `14→17-lotissement-{etape1,etape2,etape3,resultat}` | Lotissement Saint-Leu |
| `20/21-depassement-{etape3,resultat}` | Programme qui dépasse la capacité |
| `22-non-contigues-etape1` | Parcelles non contiguës (refus) |

*Les pages du PDF rendues en image sont dans `pdf/`.*
