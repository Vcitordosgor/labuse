# VERITE-TERRAIN-3 — LABUSE face aux permis réellement accordés

Audit du 15/11/2026, lecture seule. Moteur testé = **main `e269abaa0`** (en direct) ; à côté, le
**classement servi** = run q_v20 (promu le 21/10/2026) — c'est ce que le client voit aujourd'hui.
Vérité de référence = les permis réellement autorisés par les mairies (`sitadel_permits`,
Sit@del3/SDES). Suite de VERITE-TERRAIN-2 (oct. 2026) : son volet D est REJOUÉ, pas refait ;
les lots 2 à 5 du mandat sont faits ici pour la première fois.

## La page à lire (français simple)

**1. Là où une mairie a accordé un permis de logements, LABUSE dit-elle « constructible » ?
OUI dans 96,3 % des cas** (4 632 permis sur 4 812 accordés depuis les règles actuelles de chaque
commune). Le classement servi au client dit oui dans 90,8 % (4 371/4 812) : l'écart (263 permis)
vient de corrections déjà dans le moteur mais pas encore dans le run servi du 21/10. Les refus
restants se concentrent en zones agricoles et naturelles (A : 76/131 ; N : 72/130), où la
relecture montre surtout des exceptions légales (maison d'exploitant, extension d'un bâti
existant) — voir le détail de la relecture des 60 « non » ci-dessous et dans `ERREURS.md`.

**2. Ce qui a été autorisé tient-il dans l'enveloppe réglementaire de LABUSE ? OUI à 97,4 %.**
Sur 4 096 permis mono-parcelle mesurables, le projet autorisé consomme en médiane **22 %** de
l'enveloppe maximale de LABUSE (emprise après reculs × niveaux, sans le coefficient
d'occupation) ; seuls 106 permis (2,6 %) la dépassent de plus de 10 %. L'« estimation rapide »
servie (enveloppe × 45 %) couvre elle aussi le réalisé dans ~80 % des cas (autorisé médian =
48 % de l'estimation ; 20,5 % des permis la dépassent) — le coefficient de 45 % est donc
prudent-médian, pas sous-dimensionné, mais 1 permis sur 5 construit davantage.

**3. Le classement distingue-t-il les terrains qui reçoivent un projet ? OUI, nettement.**
426 parcelles à permis récent (terrain encore nu) contre 1 272 comparables tirés à graine fixe :
bandes hautes (Excellente + Bonne + À étudier) **76,5 %** côté permis contre **48,5 %** côté
comparables — écart **+28,0 points, IC 95 % [23,1 ; 32,9]**. Faible + Non retenue : 21,6 %
contre 43,8 %. Le classement servi et le moteur en direct donnent ici la même distribution.

**Les deux défauts d'octobre (VT-2)** : les 418 permis « non constructible LABUSE » sont tombés
à **219** (165 corrigés, 33 partiellement) — le correctif est réel mais il reste du stock, dont
**71 parcelles encore « terrain trop exigu »**. Les 913 « densité > calibrage » sont quasi
inchangés (**910**), et **19 permis ont RÉGRESSÉ** : pas à cause de nouveaux PLU (millésimes et
YAML inchangés, vérifié) mais à cause du commit `3cf76e039` du 31/10 qui applique un retrait
séparatif « H/2 » calé sur le faîtage maximal de la zone (8 m au lieu de 3 m à La Possession) —
voir V1.

### Les erreurs confirmées de LABUSE, de la plus grave à la moins grave

Détail, preuves et requêtes : `ERREURS.md`. En une ligne chacune :
1. **V1** — le retrait séparatif facultatif est appliqué comme obligatoire, et depuis le 31/10
   avec une amplitude fausse (H/2 au faîtage de ZONE au lieu de l'égout de la façade) : 33/40
   dépassements du Test 2, 4+3 faux « exigu » relus, 19 régressions — l'erreur dominante.
2. **V2** — le run servi (21/10) n'a pas été rejoué après les correctifs : 263 permis de H
   encore « fermés » à l'écran que le moteur ouvre ; verdicts périmés prouvés (AW0822…).
3. **V3** — l'habitat conditionnel des secteurs A/N (Aba, Arh, Ns hameaux) est calibré dans la
   config mais le moteur de capacité ne le lit pas : 11 permis réels sous le seuil réglementaire
   servis « construction neuve non autorisée ».
4. **V4** — un échec de géométrie (« assiette à vérifier ») est servi comme un NON ferme.
5. **V5** — Saint-André UB : recul sur voie MAXIMUM (≤ 6 m) modélisé comme un minimum.
6. **V6** — PPR : une touche rouge de 9,1 % ferme toute la parcelle (override partiel muet).
7. **V7** — bande prospective trait de côte traitée en interdiction rédhibitoire.
8. **V8** — SUP AC2 (avis ABF) déduite comme inconstructible totale (83 % d'une parcelle).
9. **V9** — faux « hors PLU » sur trou de couche de zonage, compté « fermé » par le gate.
10. **V10** — AU « générique » : gate fermé avec SDP servie positive sans cause (contradiction
    interne à l'écran).

---

## LOT 0 — Les données de vérité

### La table des permis : `sitadel_permits` (la seule)

50 809 autorisations, deux sources (`raw->>'src'`) : SDES Dido Sitadel3 974 (50 627) et Région
ODS (182). Types : PC 46 390 · DP 2 454 · PD 1 146 · PA 819. Dates d'autorisation (`date`) du
02/01/2013 au 31/08/2026 (1 nulle) ; dépôt (`date_depot`) du 01/01/2004 au 31/08/2026 (453
nulles). Champs réellement présents dans `raw` (liste EXHAUSTIVE mesurée) : etat, famille,
nb_lgt, surf_hab, destination, daact, insee, adr_num/voie/lieudit, geoloc (10 748),
parcelles_actuelles / origine_redecoupee / parcelle_origine (9 880), petitioner_name/siren/siret
(9 302), src, pv, date_depot_brute (5), date_autorisation_brute (1). **N'existent pas** :
surfaces démolies/conservées, niveaux/hauteur, typologie individuel/collectif/résidence.

Remplissage des 46 390 PC : surface habitable créée > 0 : **40 330 (86,9 %)** · logements créés
> 0 : **39 469 (85,1 %)** · DAACT : 20 382 (43,9 %) · SIREN demandeur : 7 310 (15,8 %) · insee :
46 150 (99,5 %) · `idu_codes` : 100 % · `geom` nulle : 734 (1,4 %).

États (`etat`, codes Sitadel3, décodés `ingestion/permits.py:94-97`) sur les PC :
2 = autorisé (10 746) · 4 = annulé (4 217) · 5 = commencé (11 062) · 6 = achevé (20 365, tous
avec DAACT). Les codes 3 (refusé) et 7 (sans suite) sont absents du flux 974.

### Qualité et pièges mesurés

- **Doublons** : 0 doublon de `permit_id` ; 599 doublons exacts (mêmes parcelles + même surface
  + mêmes logements sous deux numéros) ; 3 660 resoumissions sur la même assiette (le plus
  récent gardé). Suffixes « M » (modificatifs) : 131, AUCUN n'a son permis de base en table —
  comptés comme permis à part entière.
- **Permis ↔ parcelle** : 54 503 liens parcelle sur les PC, dont 41 985 (77,0 %) vers une
  parcelle du cadastre actuel. 11 310 PC (24,4 %) ont au moins une parcelle disparue ; 9 100
  portent le remap `parcelles_actuelles` posé à l'ingestion.
- **Annulés** : exclus partout (etat=4) ; comptés dans l'entonnoir.

### Ce qui, dans LABUSE, lit déjà les permis (neutralisé dans les tests)

Cartographie complète (fichier:ligne) en annexe de `COUVERTURE.md` ; l'essentiel : `zone.py:710`
(compteur d'autorisations de la fiche zone — affichage), `verite_terrain_capacite.py` (outil
Comparatif), `signaux_vie.py:90` (signal « permis actif < 3 ans » — widget veille). **Aucun de
ces lecteurs n'entre dans le verdict de constructibilité, le score, les bandes ni la surface à
retenir** (vérifié dans `potentiel_batir.py`, `score_labuse.py`, `surface_retenue.py` : leurs
entrées sont les caches zones/résiduel/constructibilité/AU, jamais `sitadel_permits`). Les
tests 1-3 ne testent donc pas LABUSE avec ses propres entrées.

### Les règles actuelles par commune

Date de coupe = millésime du règlement MODÉLISÉ (`config/plu_destinations/*.yaml`), croisé avec
Sudocuh (approbation du DU en vigueur) et le GPU (idurba) :

| INSEE | Commune | Approbation Sudocuh | Millésime modélisé (coupe) | Dernière version GPU |
|---|---|---|---|---|
| 97401 | Les Avirons | 2024-12-06 | 2024-12-06 | 2024-12-06 |
| 97402 | Bras-Panon | 2019-11-30 | 2026-04-28 | 2026-04-28 |
| 97403 | Entre-Deux | 2024-09-24 | 2024-09-24 | 2024-09-24 |
| 97404 | Étang-Salé | 2017-12-22 | 2025-09-17 | 2025-09-17 |
| 97405 | Petite-Île | 2017-02-23 | 2023-06-09 | 2023-06-09 |
| 97406 | Plaine-des-Palmistes | 2013-05-29 | 2023-05-27 | 2023-05-27 |
| 97407 | Le Port | 2018-10-02 | 2024-12-09 | 2024-12-09 |
| 97408 | La Possession | 2019-06-12 | 2025-12-17 | 2025-12-17 |
| 97409 | Saint-André | 2019-02-28 | 2019-02-28 | (pas d'extraits GPU) |
| 97410 | Saint-Benoît | 2020-02-06 | 2020-02-06 | 2020-02-06 |
| 97411 | Saint-Denis | 2013-10-26 | 2026-08-05 | 2026-08-05 |
| 97412 | Saint-Joseph | 2019-06-26 | 2025-12-10 | 2025-12-10 |
| 97413 | Saint-Leu | 2007-02-26 | 2007-02-26 | (pas d'extraits GPU) |
| 97414 | Saint-Louis | 2014-03-11 | 2025-12-18 | 2025-12-18 |
| 97415 | Saint-Paul | 2012-09-27 | 2025-12-17 | 2025-12-17 |
| 97416 | Saint-Pierre | 2024-06-25 | 2024-06-25 | 2024-06-25 |
| 97417 | Saint-Philippe | RNU | — (exclue de H) | — |
| 97418 | Sainte-Marie | 2013-12-27 | 2025-11-26 | 2025-11-26 |
| 97419 | Sainte-Rose | 2019-05-04 | 2019-05-04 | 2019-05-04 |
| 97420 | Sainte-Suzanne | 2017-03-22 | 2025-09-29 | 2025-09-29 |
| 97421 | Salazie | 2022-05-24 | 2022-05-24 | 2022-05-24 |
| 97422 | Le Tampon | 2018-12-08 | 2023-08-11 | 2023-08-11 |
| 97423 | Trois-Bassins | 2017-02-21 | 2022-06-02 | 2017-02-21 |
| 97424 | Cilaos | 2008-02-06 | 2024-02-13 | 2024-02-13 |

Le millésime modélisé est la **dernière version** du règlement (modifications comprises) — c'est
bien « la date depuis laquelle les règles que LABUSE modélise s'appliquent ». Quand il diffère de
l'approbation Sudocuh (ex. Saint-Paul 2012 → version 2025), les permis entre les deux dates sont
rangés « hors règles actuelles », jamais comptés contre LABUSE.

## LOT 1 — L'entonnoir des cohortes

| Étape | Permis |
|---|---|
| E0 — stock `sitadel_permits` | 50 809 |
| E1 — type PC | 46 390 |
| E2 — famille « logements » | 39 318 |
| E3 — crée de la surface OU des logements | 39 318 (inclus dans E2 mesuré) |
| E4 — non annulé (etat ≠ 4) | 35 623 |
| E5 — date et insee connus | 35 615 |
| E6 — dédoublonné (599 exacts + 3 660 resoumissions retirés) | 31 955 |
| E7 — toutes les parcelles au cadastre actuel | 24 957 |
| E8 — **H : postérieurs aux règles actuelles** | **4 812** |
| dont hors-règles (antérieurs, décrits à part) | 19 900 |
| dont Saint-Philippe (RNU, sans date de coupe) | 245 |

H : mono-parcelle 4 259 · multi-parcelles 553 ; individuel (1 logt) 3 852 · collectif/groupé
(≥ 2 logts) 951 · surface sans logement compté 9. (Typologie Sit@del absente — approximation
par nb_lgt, dite en couverture.)

**R** (permis récents au terrain encore vierge) : H mono-parcelle, jamais commencé (etat=2),
autorisé depuis le 01/01/2025, ET bâti connu de LABUSE < 20 m² (`p_model_bati`) : **426
parcelles**. Vérification de l'état « avant-projet » : double verrou état Sit@del × bâti LABUSE.

**T** (témoins) : 3 comparables par parcelle de R — même commune, même famille de zone, nu
(bâti < 20 m²), surface ± 30 %, jamais citées par AUCUN permis. Tirage déterministe
`md5(r_idu || idu || 'VT3-T-2026-11-15')` (commande : `scripts/cohortes.sql`) : **1 272
tirages** (1 245 parcelles distinctes ; 3 parcelles de R n'ont pas leurs 3 comparables).

## Rejeu VT-2 — les deux défauts d'octobre, aujourd'hui

Mêmes 6 601 permis (PC/DP logements post-PLU, filtres d'octobre), moteur de main + run servi 17
(`scripts/rejouer_capacite_vt3.py`) :

| Cause « au-dessus » | Octobre (q_v19) | Aujourd'hui (main + run 17) |
|---|---|---|
| parcelle non servie | 1 294 | 1 294 |
| densité réelle > calibrage | 913 | **964** |
| non constructible LABUSE | 418 | **220** |
| réunion incomplète | 27 | 28 |
| surface Sit@del aberrante | 1 | 1 |
| **Total au-dessus** | **2 653 (40,2 %)** | **2 507 (38,0 %)** |

Transitions permis par permis (0 permis entré/sorti du périmètre) :
- Défaut « 418 non constructibles » : **165 corrigés** (couverts désormais), 33 passés en
  capacité positive mais encore sous l'autorisé, 1 en réunion incomplète, **219 inchangés**.
  Causes restantes au grain parcelle : zone_non_constructible 137 · **terrain_exigu 71** ·
  divers 11. Le ratio médian SDP global est inchangé (0,46).
- Défaut « 913 densité » : **910 inchangés**, 2 corrigés — rien n'a bougé sur ce front.
- **21 régressions** : permis couverts en octobre, plus aujourd'hui — la capacité LABUSE a
  baissé (souvent ~de moitié) à La Possession (7), Saint-Joseph (5), Bras-Panon (2),
  Sainte-Rose (2)… La relecture RÉFUTE l'hypothèse « nouveaux millésimes PLU » : les millésimes
  sont identiques et `git diff` des YAML des 6 communes est VIDE. Cause unique prouvée : le
  commit `3cf76e039` (FAISA-REGLES-1 D-024, 31/10, postérieur au run VT-2) fait appliquer par
  `gabarit/builder.py` (l.273-290) un retrait séparatif « H/2 min 3 m » avec H = **faîtage
  maximal de la zone**, sur TOUTES les limites (ex. La Possession UA : recul 8 m au lieu de
  3 m → capacité 564 → 73 m² ; reconstruction numérique exacte dans la relecture). Verdicts :
  **19 erreur de calibrage nouveau** (les art. 7 admettent l'implantation en limite et H = la
  façade concernée à l'égout), 2 règle nouvelle correcte (découpe PPR réelle). Voir
  `relectures/VT2-DEFAUTS-RELECTURE.md` (traces rejouables `_v1_*.json`).
- **Relecture de 20 des 219 restants** (graine `VT3-219`) : **9 erreurs LABUSE** (3 faux
  « exigu » de même racine D-024 ; 6 STECAL/secteurs d'habitat Ns21/Ns34/Ns46 Saint-Benoît,
  Aba Salazie et Saint-André traités en zones fermées alors que le règlement ADMET l'habitat
  neuf plafonné — jusqu'au YAML de LABUSE qui porte la règle en `sous_condition`) · 6 décalages
  (micro-parcelles redécoupées, bâti issu du permis lui-même) · 1 exception légale ·
  4 indéterminés (exploitants agricoles non démontrables, règlement Saint-Leu non chargé).
- Nota : ces corrections moteur ne sont **pas encore servies** (run q_v20 du 21/10) — sur H,
  263 permis restent « fermés » au servi alors que le moteur du jour les ouvre (92 « générique »
  AU, 88 declasse_non_constructible, 39 zone fermée, 20 terrain_exigu, 13 rédhibitoire).

## Test 1 — Verdict de constructibilité sur H (4 812 permis)

| Lecture | Constructible | Taux |
|---|---|---|
| **Moteur en direct (main)** | 4 632 / 4 812 | **96,3 %** |
| Classement servi (gate q_v20) | 4 371 / 4 812 | 90,8 % |

(2 permis en sens inverse : servi ouvert, moteur non.)

Par famille de zone (moteur direct) : U **4 047/4 090 (98,9 %)** · AU 393/411 (95,6 %) ·
A 76/131 (58,0 %) · N 72/130 (55,4 %) · mixtes A|U 20/20, N|U 13/14. Par type : individuel
3 707/3 852 (96,2 %) · collectif 916/951 (96,3 %). Par commune : de 100 % (Petite-Île,
Étang-Salé, Cilaos, Bras-Panon, Saint-Denis) à 87,5 % (Saint-Benoît 492/562), 89,0 %
(Salazie 89/100), 90,3 % (Le Port 28/31).

Causes des 180 « non » : terrain_exigu 48 · zone_non_constructible (A/Aba/N/Ns…) 113 ·
hors_plu 3 · zone_non_resolue 3 · autres 13.

**Relecture des « non »** (60 tirés à graine `VT3-LOT2-60`, fichiers
`relectures/TEST1-RELECTURE-*.{csv,md}`) : **erreur LABUSE 16 · exception légale 23 ·
décalage 20 · indéterminé 1**. Les exceptions dominantes : 14 STECAL « hameau » Ns de
Saint-Benoît (habitat admis au règlement, permis 2020-2021 avant la caducité ELAN), logements
d'exploitant en A, 2 collectifs sociaux sur emplacement réservé « mixité sociale » (construits
par le bénéficiaire de la servitude). Les 16 erreurs se rangent en : secteurs d'habitat Aba/Arh
calibrés mais non lus (5, → V3), reculs facultatifs appliqués obligatoires (4, → V1), PPR rouge
partiel fermant tout (1, → V6), trait de côte prospectif rédhibitoire (1, → V7), recul voie
max→min Saint-André UB (1, → V5), échec d'assiette servi en non ferme (2, → V4), faux
« hors PLU » sur trou de couche (1, → V9), autre (1). Chaque erreur : preuve + SQL dans les CSV.

## Test 2 — L'autorisé tient-il dans l'enveloppe ? (H mono-parcelle, 4 096 mesurables)

Deux grandeurs LABUSE, toutes deux « terrain libéré » (le moteur de faisabilité calcule sur
l'assiette entière, bâti non déduit) :
- **estimation rapide** = emprise constructible (après reculs, CES, pleine terre, clip U/AU,
  PPR rouge) × 45 % d'occupation × niveaux = `surface_plancher_m2` servie ;
- **enveloppe maximale** = la même emprise × niveaux, SANS le 45 %.

| Ratio autorisé / LABUSE | n | médiane | Q1 | Q3 | p90 | p95 | > 1,0 | > 1,1 |
|---|---|---|---|---|---|---|---|---|
| / enveloppe maximale | 4 096 | **0,22** | 0,11 | 0,40 | 0,66 | 0,86 | 131 (3,2 %) | **106 (2,6 %)** |
| / estimation rapide | 4 095 | **0,48** | 0,25 | 0,88 | 1,46 | 1,91 | 839 (20,5 %) | 723 (17,7 %) |

Niveaux/hauteur autorisés : champ ABSENT de Sit@del → comparaison impossible (couverture).

**Relecture des 40 dépassements les plus forts** (`relectures/TEST2-RELECTURE-40.md`) :
**erreur LABUSE 34 · décalage 3 (permis antérieurs au PPR en vigueur) · donnée permis douteuse
1 · indéterminé 2.** 33 des 34 erreurs ont la MÊME cause : le retrait séparatif facultatif
appliqué comme obligatoire (→ V1 ; contre-épreuve : enveloppe recalculée au CES du règlement,
le dépassement disparaît, ratios 0,13-1,12) ; s'y ajoutent le recul voie inversé de Saint-André
UB (V5, 7 cas du même lotissement) et la SUP AC2 traitée en exclusion totale (V8).

**Où se situe l'estimation rapide (jugement du 45 %, sans conclure à une erreur)** : le projet
autorisé médian consomme 48 % de l'estimation (45 % du gabarit) — 45 % est donc un
milieu-de-gamme réaliste ; par type : individuel méd 0,45 (n=3 308), collectif 0,59 (n=758),
p90 1,46/1,60. Un projet sur cinq construit plus que l'estimation : elle est une médiane
raisonnable, pas un plafond.

## Test 3 — Le classement sépare-t-il R de T ?

Score LABUSE en direct (main, `scoring/score_labuse_combine.combiner`) = distribution identique
au servi q_v20 (mêmes caches, barème inchangé depuis le run). Bandes (vocabulaire client) :

| Bande | R (426) | T (1 272 tirages) |
|---|---|---|
| Excellente (A) | 18 (4,2 %) | 22 (1,7 %) |
| Bonne (B) | 130 (30,5 %) | 268 (21,1 %) |
| À étudier (C) | 178 (41,8 %) | 327 (25,7 %) |
| Faible (D) | 76 (17,8 %) | 242 (19,0 %) |
| Non retenue (0) | 16 (3,8 %) | 315 (24,8 %) |
| Hors classement (HC) | 6 (1,4 %) | 84 (6,6 %) |
| Analyse incomplète (NC) | 2 (0,5 %) | 14 (1,1 %) |

**A+B+C : 76,5 % [IC95 72,3-80,3] contre 48,5 % [45,8-51,3] — écart +28,0 points
[23,1 ; 32,9].** D+0 : 21,6 % contre 43,8 %. Surface à retenir (= estimation rapide, pas
d'esquisse sur ces parcelles) : à 0 / non constructible pour 3,5 % de R contre **25,6 %** de T ;
médianes positives voisines (215 vs 203 m²).

**Relecture des 30 R classées Faible/Non retenue** (`relectures/LOT4-RELECTURE-30-NOTES.md`) :
justifié ou limite **15** (la SDP servie couvre le permis — une bande « Faible » pour une
maison isolée n'est pas une faute de classement promoteur) · barème/moteur sévère **10**
(SDP résiduelle sous l'autorisé, ×1,2 à ×11, surtout petites parcelles bâties en limite —
conséquence de V1) · donnée LABUSE fausse **3** (cache servi périmé → V2) · règle non ingérée
**1** (STECAL Aba « Milieu rural habité » → V3) · permis atypique **1**. Transverse : 19/25 D
portent un malus de pente réel (15-37 % au MNT) ; 3 parcelles ne sont « Faible » que par le
malus d'accès du run cascade.

## LOT 5 — Signal secondaire : ventes « terrain à bâtir » (un indice, pas une preuve)

4 230 ventes DVF 2021-2025 en nature « terrains a bâtir » (aucun local bâti dans la mutation sur
la parcelle) ; 4 179 sur parcelle du cadastre actuel. **1 426 (34,1 %)** portent sur une parcelle
que LABUSE sert aujourd'hui fermée/non constructible — mais seules **403/1 426** sont
postérieures aux règles actuelles de leur commune (les autres ont été vendues sous un autre
zonage : l'indice ne vaut que pour elles). Causes dominantes : terrain_exigu en U **798** ·
habitat_interdit en U 156 · « générique » AU 81 · terrain_exigu N/AU/A 128. Relecture de 20
(`relectures/LOT5-RELECTURE-20-NOTES.md`) : fermeture **défendable 15** (slivers réellement
vidés aux reculs — vérifié par inset indépendant —, zones A réelles, zones économiques où les
permis confirment « locaux ») · **suspecte 2** (AE0479 cache périmé → V2 ; CD0898 contradiction
AU « générique » → V10) · vente antérieure aux règles actuelles 2 · indéterminé 1. L'indice DVF
est de plus très bruité (12/20 mutations multi-parcelles, prix = mutation entière) : le marché
ne contredit presque jamais la fermeture — signal faible, comme annoncé.

## LOT 6 — Prix : écarté (fait par VT-2 volet E, DVF inchangée depuis). Voir COUVERTURE.md.

---

## Reproduire

Depuis `~/Desktop/labuse-verite3` (`PYTHONPATH=src`, venv `~/Desktop/labuse/.venv`) :
`scripts/cohortes.sql` (cohortes + entonnoir, psql depuis `cohortes/`) ·
`scripts/rejouer_capacite_vt3.py run` (rejeu VT-2 état du jour) ·
`scripts/lot2_lot3_analyse.py` (tests 1-2) · `scripts/lot4_score_live.py` +
`scripts/lot4_faisa_live.py` (test 3) · `scripts/servi_parcelle.sql`, `scripts/lot5_tab.sql`.
Registre des erreurs : `ERREURS.md` · tous les cas relus : `CAS.csv` · périmètre : `COUVERTURE.md`.
