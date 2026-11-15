# MOTEUR-VERITE-FIX-1 — COMPTE-RENDU (lots 1 à 6, ARRÊT final)

## LE TABLEAU COMPLET — permis réels pour juge, lot par lot (cumulatif)

| Mesure | Audit | LOT 1 | LOT 2 | LOT 3 | LOT 4 | LOT 5 | **LOT 6** |
|---|---|---|---|---|---|---|---|
| Test 1 — « constructible » sur les 4 812 permis H | 4 632 (96,3 %) | 4 633 | 4 642 | 4 643 | 4 661 | 4 665 | **4 674 (97,1 %)** |
| Test 2 — dépassements d'enveloppe > 1,10 | 106 (2,6 %) | 103 | 102 | 100 | 97 | 97 | **97 (2,4 %)** — jamais monté |
| terrain_exigu (parcelles des permis H) | 327 | 322 | 275 | 275 | 275 | 268 | **104** (−68 %) |
| Cohorte 6 601 — « non constructible LABUSE » | 220 | 219 | 206 | 205 | 184 | 179 | **156** |
| Cohorte — au-dessus (total) | 2 507 (38,0 %) | 2 492 | 2 486 | 2 485 | 2 477 | 2 477 | **2 477 (37,5 %)** |
| Garde A/N (capacité nouvelle sans règle) | — | 0 | 0 | 0 | 0* | 0* | **0*** |

\* 22 parcelles A/N deviennent constructibles à partir du LOT 4 — TOUTES « plafonné à X m² »
avec la règle du secteur citée (Aba/Arh/Nrh/Nba, SDP ≤ plafond vérifiée) : capacité AVEC règle,
commandée par le mandat. Contrôles inverses : 30 plus fortes hausses relues à CHAQUE lot
(150 relectures, toutes reproduites au moteur, 0 anomalie). Suite unitaire verte à chaque lot.

Branche `fix/moteur-verite-1` (base `origin/main` `e269abaa0`, audit VERITE-TERRAIN-3 mergé pour
garder `ERREURS.md`). Juge de paix : les permis réellement accordés (cohorte VT-3 : H = 4 812 PC
logements post-règles ; rejeu VT-2 : 6 601 permis PC/DP). Principes appliqués : on n'exclut que
sur du certain ; une contrainte partielle réduit ; une inconnue donne « à vérifier » ; aucune
capacité créée sans règle prouvée (citée mot pour mot, image de la ligne de la page officielle).

## Référence AVANT correctifs (audit VERITE-TERRAIN-3, moteur main `e269abaa0`)

| Mesure | Valeur |
|---|---|
| Test 1 — « constructible » sur H | 4 632/4 812 (96,3 %) |
| Test 2 — dépassements d'enveloppe > 1,10 | 106/4 096 (2,6 %) |
| Rejeu VT-2 — permis au-dessus | 2 507/6 601 (38,0 %) ; densité 964 · non constructible 220 |
| terrain_exigu (parcelles des permis H) | cause de 48 des 180 « non » |

---

## LOT 1 — la régression du 31/10 (V1 étage 2) : H/2 à l'égout du bâtiment ENVISAGÉ

**Ce qui change** (`gabarit/contract.py`, `gabarit/engine.py`, `gabarit/builder.py`,
`faisabilite/db.py`, `faisabilite/engine.py`) : le retrait relatif « L ≥ H/2, minimum 3 m » ne se
calcule plus sur le FAÎTAGE MAXIMAL de la zone (commit `3cf76e039`) mais sur la hauteur à
l'ÉGOUT du bâtiment envisagé, NIVEAU PAR NIVEAU : le moteur gabarit évalue chaque nombre de
niveaux admis (égout envisagé = n × 3 m), retient le scénario au PLANCHER maximal (aire ×
niveaux, bornée au CES), et la capacité compte les MÊMES niveaux que l'assiette retenue
(écran Gabarit, fiche et capacité racontent le même scénario). La formule ne s'applique qu'aux
limites où le règlement exige un retrait (setbacks `limite-sep`) ; sans hauteur validée, elle
reste « non intégrée » (on ne devine pas H).

**Preuve réglementaire** : Le Port Ub 7.2 (sondage image `sondage/SONDAGE-01-bande.png`) :
« …au moins égale à la moitié de la hauteur (H) de la **façade concernée**, avec un minimum de
3 mètres. La hauteur (H) est mesurée du sol existant après travaux **jusqu'à l'égout du
toit**. » — H n'est pas le faîtage de la zone.

**Témoins** : AO1919 (La Possession UA) octobre 564 m² → régression 73 m² → **LOT 1 282 m²**
(scénario retenu R+1, recul 3 m — le permis réel de 191 m² est de nouveau couvert) ;
BO0496 (Saint-Joseph U3) 264 → 81 → **177 m²** (R+2, recul 4,5 m ; permis 145 m² couvert).

**Mesures après LOT 1** (rejeu complet, cache `cache-lot1/`) :

| Mesure | Avant (VT-3) | Après LOT 1 |
|---|---|---|
| Test 1 — « constructible » sur H | 4 632/4 812 (96,3 %) | **4 633/4 812 (96,3 %)** |
| Test 2 — dépassements d'enveloppe > 1,10 | 106/4 096 (2,6 %) | **103/4 077 (2,5 %)** |
| terrain_exigu (parcelles des permis H, même métrique) | 327 | **322** |
| Cohorte rejouée — au-dessus | 2 507/6 601 (38,0 %) | **2 492/6 601 (37,8 %)** |
| — densité > calibrage | 964 | **950** |
| — non constructible | 220 | **219** |
| **Les 19 régressions d'octobre** | 19 au-dessus | **17 re-couvertes** ; restent 2 découpes PPR correctes (Plaine-des-Palmistes, Saint-Louis, ratios 1,11-1,16) et 2 Sainte-Rose 1AUa (limite admise à l'art. 7 — commune HORS pilote LOT 2, ratios 1,19-1,37) |

**Contrôle inverse** (`CONTROLE-INVERSE-lot1.csv`) : 103 parcelles en hausse sur ~8 000 ;
les 30 plus fortes relues UNE PAR UNE : 30/30 reproduites au moteur (sdp = emprise × 45 % ×
niveaux du scénario, minima respectés — dont le 1,9 m d'U4 Saint-Joseph), toutes expliquées par
le recul faîtage-de-zone → égout-envisagé (ex. AO1919 73 → 282 m², R+1 à 3 m). **Garde A/N : 0
parcelle passée de non-constructible à constructible en zone A ou N** (les 2 hausses en zone A/N
— AK0834, AZ0660 — étaient DÉJÀ constructibles par leur portion U/AU, seule la formule change).
Garde des rubans : suite unitaire verte (365 tests gabarit/faisabilité, gardes UAU/érosion
incluses).

---

## LOT 2 — construire en limite (V1 étage 1), pilote 5 communes, puis ARRÊT

**Lecture réglementaire** (un lecteur par commune, citations mot pour mot ; règlements officiels
PDF téléchargés des packs GPU — Saint-André : PDF du site de la mairie, **md5 identique** à
celui enregistré au calibrage 2019). 155 classements (zone × latérales/fond) :

| Commune | retrait_obligatoire | limite_ou_retrait | limite_sous_conditions | limite_imposee |
|---|---|---|---|---|
| Le Port (16) | 1 | 8 | 4 | 3 |
| Saint-André (38) | 17 | 3 | 16 | 2 |
| Saint-Joseph (39) | 1 | 18 | 19 | 1 |
| Saint-Louis (38) | 4 | 6 | 28 | 0 |
| Saint-Pierre (24) | 2 | 0 | 22 | 0 |

Détail et citations : `implantation/<insee>.csv` + `<insee>-NOTES.md`. Sondage de 10 règles à
graine fixe avec l'image de la ligne de la page officielle : `sondage/SONDAGE.md` (10/10 bandes
extraites).

**Ce qui change au moteur** (`faisabilite/zonage.py`, `gabarit/builder.py`, `faisabilite/db.py`,
`faisabilite/engine.py` + feuilles YAML `implantation_laterales`/`implantation_fond`,
validées-only) :
- `limite_ou_retrait` sans condition et `limite_imposee` → recul 0 sur les arêtes du côté
  (latérales / fond séparément), sourcé ;
- condition MODÉLISABLE : `largeur_terrain_max:X` (largeur = petit côté du rectangle englobant
  minimal, mesurée — condition évaluée, pas de mention) ; `une_seule_limite` /
  `deux_limites_max` → recul 0 sur la (les) arête(s) latérale(s) la (les) plus longue(s) ;
- condition NON modélisable (bande de hauteur, % de linéaire, affectation, voisinage) → le
  retrait reste la capacité retenue, avec la mention « implantation en limite possible sous
  conditions : capacité supérieure possible, à vérifier » ;
- assiette avec retrait VIDE + limite possible → verdict « **Constructible — capacité à
  vérifier** », jamais « terrain trop exigu » ;
- les arêtes en limite portent `limite-sep-limite` : la formule H/n du LOT 1 ne re-insète que
  les arêtes encore en retrait. Saint-Denis et La Possession : AUCUN recalibrage (code commun
  seulement), conformément au mandat.

**Liste des interprétations (à trancher par le relecteur)** :
1. Le Port Ub latérales : l'imposition en limite ne vaut que dans une bande de 20 m depuis
   l'alignement (non modélisée) ; gravé `largeur_terrain_max:12` pour l'imposition deux-limites,
   la bande portée en texte. Terrains > 12 m : « au moins une limite » lue comme mention (pas
   d'arête imposée d'office).
2. Le Port Ud : « en limite séparative et/ou suivant l'alignement des constructions limitrophes
   existantes », sans retrait chiffré → `limite_imposee` (sans condition modélisable).
3. Saint-Pierre Ud/Udl/UdBO/Ucv : le « premier rideau » IMPOSE au moins une limite latérale —
   classé `limite_sous_conditions` non modélisable (pas de notion de rideau au moteur) ; le
   YAML calibré actuel gommait cette imposition.
4. Saint-Pierre : plafonds de linéaire en limite (60-80 % selon zones) non modélisés (mention) ;
   suggestion de vocabulaire futur `lineaire_max_pct`.
5. Saint-Louis UB : paragraphe « 4 m au droit de la limite » inséré en 7.2 mais rédigé pour le
   fond (copie probable) → latérales laissées `limite_sous_conditions` (lecture prudente).
6. Saint-Louis UZ : règle dépendant d'une « affectation » en annexe graphique non ingérée →
   sous conditions non modélisables ; fond ouvert seulement pour l'individuel ≤ 12 m.
7. Saint-Joseph U4 : bascule une/deux limites à 400 m² de SURFACE de terrain — hors vocabulaire
   (gravé non modélisable, mention).
8. Saint-André UC/UD fond : « interdite » sans retrait chiffré → `retrait_obligatoire` avec
   min_m VIDE (rien d'écrit, rien d'inventé — l'assiette garde le retrait latéral).
9. Saint-André UE/US : retrait obligatoire si la limite touche une zone habitat (voisinage non
   modélisé) → mention.
10. Fond de parcelle : plusieurs règlements ne distinguent pas latérales/fond (Saint-Joseph
    U2→U5, Le Port hors Ub) — lecture littérale : même mode des deux côtés.

**Mesures après LOT 2** (rejeu complet, cache `cache-lot2/`, cumulatif LOT 1 + LOT 2) :

| Mesure | Avant (VT-3) | Après LOT 1 | Après LOT 2 |
|---|---|---|---|
| Test 1 — « constructible » sur H | 4 632 (96,3 %) | 4 633 (96,3 %) | **4 642/4 812 (96,5 %)** — dont 9 permis par le seul verdict « Constructible — capacité à vérifier » |
| Test 1 — « non » | 180 | 179 | **170** |
| Test 2 — dépassements d'enveloppe > 1,10 | 106 (2,6 %) | 103 (2,5 %) | **102/4 077 (2,5 %)** |
| terrain_exigu (parcelles des permis H) | 327 | 322 | **275** (−52) |
| Cohorte rejouée — au-dessus | 2 507 (38,0 %) | 2 492 (37,8 %) | **2 486/6 601 (37,7 %)** |
| — non constructible LABUSE | 220 | 219 | **206** (+11 « capacité nulle » = les nouveaux « à vérifier », SDP ∅ comptée 0 par le comparateur — honnête) |
| — densité > calibrage | 964 | 950 | 944 |

Lecture honnête : le gain du pilote est VISIBLE mais borné — dans les 5 communes, beaucoup de
faux « exigu » tombent (−52) et Le Port Uc gagne des capacités réelles (limite admise sans
condition, jusqu'à +543 m² sur AI1683) ; mais une grande part des zones pilotes est en
`limite_sous_conditions` NON modélisables (Saint-Pierre en tête) → mention « capacité
supérieure possible, à vérifier », pas un chiffre. Les cas témoins BI0220 (Saint-André) et
AL1652 (Le Port) restent bornés par le RECUL SUR VOIE (V5 : maximum modélisé en minimum —
LOT 4) et l'alignement sur voie non calibré : leurs verdicts sont désormais honnêtes
(« capacité à vérifier »), la capacité chiffrée viendra du LOT 4.

**Contrôle inverse après LOT 2** (`CONTROLE-INVERSE-lot2.csv`) : 119 parcelles en hausse vs
l'audit ; les 30 plus fortes relues UNE PAR UNE : 30/30 reproduites au moteur (chaîne emprise ×
45 % × niveaux respectée), origine identifiée LOT 1 (formule) ou LOT 2 (limite admise — ex. les
10 Uc du Port, zones `limite_ou_retrait` au verbatim Uc 5 p.54) ; **garde A/N : 0** parcelle
passée de non-constructible à constructible en zone A ou N (l'unique A du tableau, AK0834,
était déjà constructible par sa portion U/AU — gain LOT 1 seulement) ; garde des rubans :
suite unitaire verte (389 tests gabarit/faisabilité/zonage + 4 gardes neuves
`tests/test_moteur_verite_fix1.py`).

---

## HORS MANDAT, constaté et listé (aucune action ici)

- **V2 — le classement servi** (run q_v20 du 21/10) n'est PAS rejoué par cette branche : les
  corrections n'atteindront le client qu'à la prochaine bascule de run (263 permis de H encore
  fermés au servi d'aujourd'hui).
- **Le Tampon 2AUc** : 6 permis neufs 2024-2026 dans une zone subordonnée à ouverture au GPU
  2023 — décalage de source (modification non répercutée au GPU), à instruire côté veille PLU.

## ARRÊT

Conformément au mandat, ARRÊT après le LOT 2 : les lots 3 (exclusions trop dures) et 4 (règles
mal lues) attendent la validation de ces mesures et des interprétations ci-dessus.

---

## LOT 3 — les exclusions trop dures (V4, V6, V7, V8, V9, V10)

**Ce qui change** :
- **V6 (PPR rouge partiel)** : la part rouge était DÉJÀ découpée par le moteur — l'erreur était
  double : (a) le MESSAGE accusait le PPR en entier (« Parcelle couverte par le PPR en zone
  rouge ») même à 9 % de rouge quand l'assiette était en réalité vidée par les emplacements
  réservés et les reculs (AD0863 : Uc 80 %, ER 179 m²) ; (b) la raison « ppr_rouge » était posée
  dès que le rouge touchait. Désormais la raison n'est posée que si le rouge est DOMINANT
  (≥ 50 % MESURÉ, requête `_HORS_PPR_ROUGE`) et le verdict porte le % ; sinon l'attribution va
  aux vrais consommateurs (ER/EBC/contraintes/reculs). POURQUOI la dérogation PPR-PARTIEL n'a
  pas joué sur AD0863 : `verdict_ppr_partiel` exige que le reste hors rouge soit RÉELLEMENT
  constructible au moteur — il ne l'est pas (ER + reculs), le refus de dérogation était correct ;
  seul le message mentait. Témoin : AD0863 dit maintenant « Emplacement réservé couvrant la
  parcelle ».
- **V7 (trait de côte prospectif)** : la couche `trait_de_cote` (bandes courte/longue) est une
  PROJECTION d'érosion — le facteur ×(1−part) (jusqu'au 0 « rédhibitoire » à 100 %) devient une
  ALERTE « à vérifier auprès des services de l'État », aucune surface retirée. Témoin BX0750
  (Ua Saint-Benoît, maison ACHEVÉE, DAACT 17/07/2025) : 0 → 468 m².
- **V8 (SUP AC2)** : sortie de la déduction (gabarit/builder) — régime d'AVIS de l'ABF, pas une
  interdiction ; une ALERTE sourcée la signale (« Site protégé (AC2) — avis ABF requis, aucune
  surface retirée »). Témoin CY1293 (83 % retirés avant) : 73 m² servis.
- **V4/V9 (ignorances)** : le gate du potentiel (`potentiel_batir`, Python ET jumeau SQL
  `_sql_gate`/`sql_sdp_restante`/`sql_a_construire`/`est_ferme_parcel`) ne ferme plus sur une
  cause d'IGNORANCE — « Analyse incomplète — <cause> », SDP ∅ (jamais le 0 stocké pollué).
  Impact servi MESURÉ : **16 272 parcelles** requalifiées (zone_non_resolue 10 397, hors_plu
  4 255, surface_incertaine 1 586, hauteur_indispo 34). Témoin DE2186 (trou de couche à 23 m
  d'une zone UC) : « Analyse incomplète — parcelle hors du PLU outillé ».
- **V10 (AU « générique »)** : l'AU différée sert UN SEUL verdict cohérent avec la surface
  stockée — « Potentiel différé — ouverture de la zone requise · ≈ N m² après ouverture »
  (**1 238 parcelles** avec SDP > 0 concernées). Test adapté (`test_au_non_ouverte_ferme`).

**Mesures après LOT 3** (cumulatif) : Test 1 **4 643/4 812 (96,5 %)** · Test 2 dépassements
**100/4 077 (2,5 %)** — ne monte pas · terrain_exigu **275** · cohorte au-dessus **2 485
(37,6 %)**, non-constructible **205**.

**Contrôle inverse** : 123 hausses ; top 30 = celles des lots 1-2 (déjà relues) + **BX0750
0→468 m²** (V7, permis réel achevé — relu, reproduit) ; AC2 CY1293 +73 m² (hors top 30, relu).
**Garde A/N : 0** nouvelle constructibilité. Rubans : suite verte (406 tests).

---

## LOT 4 — deux règles mal lues (V5, V3)

**V5 — recul sur voie MAXIMUM lu comme minimum (Saint-André)** : les citations stockées disaient
elles-mêmes « la façade principale ne doit pas être implantée **au-delà** d'une marge de recul de
4/6 mètres » — une BANDE d'implantation, pas un retrait. Feuilles `retraits.voie` UA/UB corrigées
(`min_m: 0`, `max_m: 4/6`, `forme: bande_max`, note de calibrage). La même tournure a été
CHERCHÉE dans les 3 258 extraits des autres communes : AUCUNE autre occurrence (tournure propre à
Saint-André ; les 4/6 m des autres communes sont de vrais minima, vérifié au verbatim).

**V3 — secteurs d'habitat des zones A/N** : le moteur lit désormais la règle DÉJÀ calibrée
(`sous_destinations.logement`, sous_condition + seuil en surface de plancher) et sert
« Constructible sous conditions — habitat admis en secteur X, plafonné à N m² » avec la citation.
DOUBLE GARDE mesurée : les logements d'exploitant/de fonction sont écartés par mot-clé, et la
GARDE DU NEUF n'ouvre que si l'admission des constructions NOUVELLES est écrite au verbatim —
52 des 60 feuilles A/N à seuil (extensions d'existant, caretaker…) restent fermées. Secteurs
ouverts : **8 exactement** — Aba (Saint-André 120, Saint-Joseph 120, Salazie 150, Le Tampon 120),
Nba (Saint-Joseph 120), Arh (Saint-Louis 50, Trois-Bassins 120), Nrh (Saint-Paul 100).

**Mesures après LOT 4** (cumulatif) : Test 1 **4 661/4 812 (96,9 %)** · Test 2 dépassements
**97/4 081 (2,4 %)** — en baisse · terrain_exigu 275 · cohorte au-dessus **2 477 (37,5 %)**,
non-constructible **184** (−36 depuis l'audit).

**Contrôle inverse** : 265 hausses ; les 30 plus fortes relues : 30/30 reproduites (les
nouvelles = Saint-André UB, +380 à +430 m², libération de la bande avant par le recul voie
0-6 m). **Garde A/N : 22 parcelles** passées constructibles en zone A/N — TOUTES portent le
verdict « plafonné à X m² » avec la règle citée (vérifié : SDP ≤ plafond partout) ; c'est la
capacité AVEC règle prouvée commandée par le mandat, zéro ouverture sans règle.

---

## LOT 5 — les décisions du relecteur + le vocabulaire mesurable

Décisions appliquées (overlay `implantation/LOT5-DECISIONS.csv`, 18 feuilles) : **1** Le Port Ub —
bande de 20 m MODÉLISÉE (limite dans la bande depuis la voie, retrait au-delà ; ≤ 12 m de
largeur → deux limites, sinon au moins une, mode imposé) ; **2** Le Port Ud fond — retrait +
mention (l'alignement visé est celui des voisins, pas le fond) ; **7** Saint-Joseph U4 — bascule
MESURÉE à 400 m² de terrain (`bascule_surface:400`) ; **8** Saint-André UC/UD fond — mention
« retrait de fond non chiffré au règlement, valeur des latérales appliquée, à vérifier » ;
**10** lecture littérale des « limites séparatives » indistinctes actée (citations à l'appui) ;
**3/4/5/6/9** lectures prudentes maintenues. Nouveau vocabulaire moteur (jetons COMBINABLES) :
`profondeur_bande:X` (bande depuis la voie — découpage géométrique de l'arête),
`lineaire_max_pct:P` (part du linéaire en limite, découpage par substring),
`surface_terrain_max:X` / `bascule_surface:X` (surface cadastrale mesurée), largeur en mode
imposé → au moins une limite. Saint-Pierre encodé avec ce vocabulaire (linéaires 60-80 % par
zone, imposition du premier rideau ; la hauteur-sur-bande reste une mention).

**Mesures après LOT 5** (cumulatif) : Test 1 **4 665/4 812 (96,9 %)** · dépassements **97
(2,4 %)** — stable · terrain_exigu **268** · cohorte au-dessus 2 477, non-constructible **179**.
Effet marginal lot4→lot5 MESURÉ : 7 parcelles de Saint-André passent de « terrain exigu » à
« Constructible — capacité à vérifier » (mention de fond, décision 8) ; 4 hausses Up
Saint-Pierre (+3 à +7 m², linéaire). Contrôle inverse : les 30 plus fortes hausses vs l'audit =
celles des lots précédents (déjà relues) ; garde A/N inchangée (les mêmes 22 plafonnées avec
règle). Suite verte (406 tests).

---

## LOT 6 — l'implantation en limite étendue à toutes les communes

Même méthode que le LOT 2 : 17 lecteurs (un par commune restante), citations mot pour mot aux
règlements officiels — La Possession comprise (son règlement d'implantation est PROUVÉ identique
à l'ancien : md5 des extraits UA 7/UB 7/UEm 7/AUBm 7/TITRE III strictement égaux entre les
documents 2025-12-17 et 2026-06-25) ; Saint-Leu lu au PDF de la mairie (md5 = celui du
calibrage 2013) ; Saint-Denis EXCLU (en attente de confirmation). **595 classements**
(latérales/fond) injectés en feuilles validées : limite_sous_conditions 375 ·
retrait_obligatoire 134 · limite_ou_retrait 78 · limite_imposee 8. Zones non injectées, dites :
AU indicées de Saint-André (renvoi à la zone U d'indice — servies par le renvoi) ; U1lec/U3h/
Usdu_PlateauCaillou de Saint-Paul (absentes du YAML destinations).

**Mesures après LOT 6** (cumulatif, rejeu complet) : Test 1 **4 674/4 812 (97,1 %)** ·
Test 2 dépassements **97/4 081 (2,4 %)** — n'a monté à aucun lot · terrain_exigu **104**
(327 à l'audit, −68 %) · cohorte au-dessus **2 477 (37,5 %)**, non-constructible **156**,
« capacité nulle » 34 (ce sont les nouveaux « Constructible — capacité à vérifier », SDP ∅
comptée 0 par le comparateur — honnête). Contrôle inverse : 304 hausses vs l'audit ; les 30
plus fortes (Saint-André 12, Le Port 7, Saint-Joseph 5…) relues UNE PAR UNE : 30/30 reproduites
au moteur, 0 anomalie ; **garde A/N : AUCUNE capacité nouvelle en zone agricole ou naturelle
hors les 22 secteurs plafonnés avec règle du LOT 4** ; rubans verts (406 tests).

Sondage FINAL de vingt règles à graine fixe, toutes communes : `sondage-final/SONDAGE-20.md` —
**18/20 lignes extraites en image** depuis les PDF officiels (packs GPU téléchargés pour les
communes tirées), 2 replis en page entière (citations composées de renvois AU).

Nota de commit : les CSV de LECTURE des 17 communes (preuves) sont entrés au commit du LOT 5
(ajout du dossier docs) ; leur ACTIVATION (feuilles YAML) est dans ce commit LOT 6.

### Les interprétations NOUVELLES de l'extension (à trancher, lectures prudentes en attendant)

1. **« profondeur_bande » à double sens** : plusieurs règlements bornent la PROFONDEUR DE LA
   CONSTRUCTION le long de la limite (Avirons 12/20 m, Cilaos 15 m, Saint-Leu UA/UB 15 m,
   Trois-Bassins 1AU 10 m, Bras-Panon UC 20 m « à partir du recul imposé ») quand d'autres
   définissent une BANDE DEPUIS LA VOIE (Petite-Île 20 m, Saint-Paul U1a 10 m, Le Port Ub
   20 m). Le moteur modélise UNIFORMÉMENT en bande depuis la voie — approximation prudente
   (la limite ne sert que près de la voie), à raffiner si une notion de profondeur bâtie est
   souhaitée.
2. **Linéaires ABSOLUS en limite** (18 m La Possession, 10/12 m Saint-Paul, 18 m Le Tampon,
   10 m Saint-Leu UD, 20 m mitoyenneté UEm) : hors vocabulaire (% seulement) → mentions ;
   suggestion `lineaire_max_m`.
3. **Clauses d'angle** (interdiction de joindre deux limites contiguës, 3-5 m d'espace libre :
   La Possession UA/UB, Le Tampon) : non modélisées (mention).
4. **Saint-Benoît, fond « libre »** : la colonne explicative (non opposable) dit le fond libre,
   la règle opposable n'ouvre que les latérales → retrait prudent 1 m gravé, lecture
   alternative documentée.
5. **Petite-Île** : condition DISJONCTIVE (bande 20 m OU parcelle < 15 m) → « OU » non
   modélisé (mention) ; coquille « au minimum dans une bande » lue comme la même bande.
6. **Sainte-Rose UD muet au-delà de 14 m** → lecture la moins permissive (une limite ≤ 14 m,
   retrait sinon).
7. **Saint-Leu AUa(slo)/AUb(slo)** : secteurs d'habitat de ZAC omis de la liste limitative
   AU 2.2 (malfaçon probable du PLU) → exclus, signalé.
8. **Chapitres AU indicées absents de `plu_reglement_extrait`** dans au moins 8 communes
   (Avirons p.26-28, Plaine-des-Palmistes p.75-77, Bras-Panon p.77-81, Sainte-Marie p.41,
   Cilaos collé dans AUst, Le Tampon mal tagué, Saint-Paul, La Possession AUEm absent du
   règlement même) + tags `zone` faux/vides (Saint-Paul massivement, 97405/97410 vides) —
   à reprendre à l'ingestion des extraits ; les lectures ont contourné par recherche plein
   texte et PDF officiels (md5 vérifiés).
9. **Multi-voies** : règle récurrente « plus de limite de fond » quand le terrain est longé
   par plusieurs voies — non modélisée.
10. **OAP** : nombreux renvois « compatibles avec les OAP » — OAP non ingérées, non lues.

---

## LOT 7 — Saint-Denis (sur confirmation du donneur d'ordre)

Document en vigueur confirmé (zonage, texte, PDF, règles — vérifié par une autre session).
Lecture mot pour mot (`implantation/97411.csv`, 34 lignes, les 34 citations retrouvées
caractère pour caractère dans `plu_reglement_extrait`) : 17 zones habitat × 2 côtés —
limite_sous_conditions 26 (Ud/Udo/Udp/Udop/Uip `deux_limites_max`, plafonds de hauteur/longueur
par limite en mention ; Um/AUm 10 m par limite ; Uh/AUh une seule limite ; Uu hors limites de
zone) · limite_ou_retrait 4 (Upi 3 m, Upr 4 m) · retrait_obligatoire 4 (Uavap — règle dans
l'AVAP non ingérée, garde-fou ; Uicm 5 m, règle propre que le YAML destinations gommait) ·
imposée 0. Indices d'audit confirmés mot pour mot (Um.7 p.67 « 10 m par limite » = longueur ;
Ud.7 p.42 « 1 ou 2 limites… hauteur maximale de 18 m par limite »). Incertitudes consignées :
AVAP annexée absente de la base ; mitoyenneté imposée Ud/Udo sur 12 m depuis l'alignement
(citée, non modélisée) ; plafonds en mètres par limite hors vocabulaire (« + non »).

**Mesures après LOT 7** (cumulatif) : INCHANGÉES sur la cohorte — Test 1 **4 674/4 812
(97,1 %)**, dépassements **97 (2,4 %)**, terrain_exigu **104**, cohorte au-dessus 2 477. Effet
propre lot6→lot7 MESURÉ : **1 parcelle** (97411000HB0251, Uj, +4 m²) — attendu : le PLU
dionysien en vigueur date du 05/08/2026 et la cohorte ne compte que 7 permis postérieurs ;
le calibrage joue sur le STOCK des parcelles Ud/Um/Uj… et sera jugeable aux prochains permis.
**Contrôle inverse : garde A/N inchangée (0 nouvelle), aucune hausse nouvelle au top 30,
suite verte (411 tests).** ARRÊT.

---

# MOTEUR-VERITE-FIX-2 — réponse au relecteur indépendant (lots A-D)

Le rapport annoncé n'était pas joint au mandat ; chaque cas LISTÉ PAR LE MANDAT est traité et
gravé en test. RÈGLE gravée (`tests/test_moteur_verite_fix2.py`) : un chiffre de capacité ne
dépasse main que si TOUTES les conditions de l'article sont appliquées ; sinon niveau prudent +
« capacité supérieure possible, à vérifier » ; sans capacité établissable : « capacité à
vérifier », jamais un chiffre — le verdict peut rester « constructible ».

## LOT A — mécanisme (`45b5cfa55`)
Condition non modélisée → l'ouverture FERME (fini « ouverture + mention ») ; parseur STRICT
(« 14 m (≤ 14 m : …) » était lu **141 414 m** — Sainte-Rose ouvrait deux limites à toute
largeur ; « 20 m (…) » lu **2 014 m** de bande — Bras-Panon ; 160 jetons mal lus listés dans
`LOT-A-SEUILS-MAL-LUS.csv`, 12 nocifs) ; plafond de n limites AU TOTAL fond compris (article
indistinct), fond à 0 seulement si texte exprès. Décision extraite en fonction PURE testée.

## LOT B — plafond ≠ capacité (`b50c31b8e`)
Secteurs Aba/Arh/Nrh/Nba : SDP ∅ (« capacité à vérifier »), plafond en clé informative non
sommable ; « limite totale » = par unité foncière ; Saint-Louis Arh : 50 m² PAR TRANCHE de
600 m² (tranches complètes, incomplète « à vérifier »).

## LOT C — les cas, un par un (`2a1deba35`)
Saint-André UA/UB : position de FAÇADE (≤ 4/6 m, RD 7 m de l'axe) non modélisée → min prudent
restauré (capacité ≤ main), alignement en mention. Saint-Joseph famille U2/U3 : ruptures 15 m /
hauteurs par bande → fermeture prudente (18 feuilles `FIX2-DECISIONS.csv`). CY1293 : AC2 sans
distinction inscrit/classé dans la donnée → « capacité à vérifier » (SDP ∅) et plus jamais
« Aucune SUP ». Saint-Denis : AUj/AUm/AUh servaient 0 m (forme alignement malgré conditions
non modélisées) → 4 m sourcés ; Uicm 5 m (règle propre) ; le REPLI générique lit les retraits
calibrés (plus le défaut 3 m). AD0863 : fragments séparés par le rouge NON sommés (plus grand
tenant). BX0750 : verdict constructible, capacité NON chiffrée tant que la limite littorale
n'est pas qualifiée ; cascade alignée (plus d'exclusion dure). Interprétations risquées :
couvertes en SURENSEMBLE par le tout-ou-rien du LOT A (toute condition non modélisée est
désormais prudente).

## LOT D — mesures et preuve

| Mesure | LOT 7 | **FIX-2** |
|---|---|---|
| Test 1 — « constructible » (4 812 permis) | 97,1 % | **97,1 %** (identique — 4 674) |
| Test 2 — dépassements > 1,10 | 97 | **100** (+5/−2, TOUS expliqués ci-dessous) |
| terrain_exigu (parcelles H) | 104 | **90** |
| « capacité nulle/∅ » cohorte | 34 | **81** (les nouveaux « à vérifier » honnêtes) |

Les 5 dépassements NOUVEAUX sont l'effet direct des corrections demandées : 4 permis de
Saint-André UB (l'enveloppe rétrécit quand le recul voie prudent 6 m remplace le min 0 du
LOT 4) et 1 de Saint-Joseph U3a (famille fermée) — les permis réels y battent l'enveloppe
PRUDENTE, la mention « capacité supérieure possible » est présente (alignement/limite admis
non modélisés). 2 dépassements sortis.

**LE VRAI CONTRÔLE INVERSE** (`CONTROLE-INVERSE-VRAI.csv`) : **284 parcelles** au-dessus de
main — LISTE INTÉGRALE, chacune avec l'ARTICLE qui l'autorise et la preuve que ses conditions
sont appliquées (retrait relatif H/n à l'égout envisagé ; implantation en limite sans condition
au règlement ; conditions MESURÉES largeur/surface/bande/linéaire strictes ; portions U/AU avec
l'article de la sous-zone) — **0 sans justification**. Garde A/N : les mêmes 22 secteurs
plafonnés (désormais SDP ∅, verdict conservé).

**Sondage recalé** (`sondage-final/`, section RECALAGE FIX-2) : F02/F17 (la règle U imagée ET
le renvoi AU imagé à part), F05 (vraie page 46), F06 (règle U5.3 p.13 + renvoi p.30), F12
(p.112) ; F09/F19 fonds complétés (F19b : clause de bande 10.3 imagée) ; **3 cas « limite
imposée » ajoutés** (F21 Trois-Bassins Uaa, F22 Saint-Paul U1a, F23 Le Port Ud) — 13/13 images.

---

# MOTEUR-VERITE-FIX-3 — la liste blanche : tout est fermé par défaut

Inversion de méthode demandée par la 2e relecture indépendante : un chiffre de capacité ne peut
dépasser celui de main QUE pour une zone inscrite sur une LISTE BLANCHE explicite, article par
article. Base : merge d'origin/main `9058a8f55` (`cf935cfdf`).

## LOT 1 — liste blanche (`47a1d2376`)

Chaque feuille d'implantation qui OUVRE doit porter la déclaration « toutes les conditions de
l'article sont appliquées » + les 8 conditions (nombre_de_limites, lineaire_ou_profondeur_en_
limite, bande_depuis_voie, hauteur_en_limite, angle, patio, rupture_mitoyennete,
affectation_graphique), chacune `absente_du_texte` ou `mesuree` — sinon le moteur FERME
(`liste_blanche_ok`, gate dans `analyser_condition_implantation`). Liste initiale : **Le Port Uc,
Salazie UA, La Plaine-des-Palmistes Ub** (6 feuilles ; Plaine = budget 1 limite TOTAL). La
référence de hauteur `h_reference` est lue À L'ARTICLE pour 68 zones : **19 à l'égout prouvé**
(La Possession UA/UB et famille, Saint-Louis UC1/1AUc1, Trois-Bassins Ue) → scénario H/2 niveau
par niveau ; les autres (faîtage/altitude) restent au faîtage PRUDENT. `LISTE-BLANCHE.md`
généré pour relecture complète.

## LOT 2 — les bugs reproduits par le relecteur (`178c48742`)

* **Largeur = PORTE mesurée SUR LA VOIE** (somme des arêtes voie — plus jamais le petit côté du
  rectangle englobant). Remplie, elle ACTIVE les jetons de nombre (Sainte-Rose Ud : une seule
  limite sous 14 m — AS0031, front 52,6 m, ouvrait « toutes » sous le seuil et une au-delà) ;
  non remplie, le côté FERME (règle appliquée, pas une mention) ; en mode imposé, « au moins
  une » reste. Test de régression dédié.
* **Contour fermé** : une arête-anneau n'est JAMAIS « fond en limite 0 m » (AH0293, AY0554,
  AH1368, AW0503) — mention « à vérifier ».
* **Le repli applique les règles PROPRES de la zone** : Saint-Denis Uicm 5 m ET CES 40 % (Ui.9
  p.56) ; Udo 4 m (Ud.7 p.42) ; une règle propre NON réductible à un nombre (hauteur Udo par
  rue, Ud.10 p.44) n'est JAMAIS remplacée par une valeur générique → « capacité à vérifier »
  (champ `ZoneRules.capacite_a_verifier`, verdict constructible, SDP ∅).
* **SUP AC2 distinguée par la couche DEAL** (`spatial_layers kind='ens'`) : site CLASSÉ →
  « Autorisation spéciale requise (art. L341-10) » (CY1293 le sert), site INSCRIT → avis ABF ;
  couche muette → libellé prudent ; jamais « aucune SUP ».
* Saint-Joseph U3 (hauteurs par bande 8 m/6 m) : FERMÉ par la liste blanche (vérifié) —
  l'ouverture exigera `hauteur_en_limite: mesuree`.

## LOT 3 — « capacité à vérifier » n'est pas un zéro (`45ded1670`)

Une faisabilité constructible SANS `surface_plancher_m2` (SDP ∅) écrivait `capacite_nulle`/0
dans le résiduel. Désormais : **SDP écrite NULL + cause `capacite_a_verifier`** (famille
IGNORANCE — le jumeau SQL du gate et le filet du score servent « Analyse incomplète », jamais
« rien à bâtir »). Témoins : AS0256 (Salazie Aba), CY1293 (Saint-Leu). **Réconciliation
cascade ↔ capacité (BC1134, 61 % rouge)** : l'exclusion PPR rouge ≥ 50 % applique le MÊME test
que le moteur (`_hors_rouge_fragment_servable`) — partie hors rouge exploitable → FLAG FORT
« capacité réduite à cette partie » ; l'exclusion ne tombe que si le reste n'est pas
exploitable (contre-témoin BN0009, 100 % rouge : exclue). **RNU** : une commune au
règlement national d'urbanisme (Saint-Philippe) n'est PAS une ignorance « hors du PLU
outillé » — c'est un régime connu : le potentiel sert « constructibilité limitée aux parties
actuellement urbanisées, analyse au cas par cas » (constructible False, jamais un prix de
terrain à bâtir dans Estimer — E105 du contre-audit chirurgical, test de cohérence vert).

## LOT 4 — mesures et preuve

| Mesure | LOT 7 | FIX-2 | **FIX-3** |
|---|---|---|---|
| Test 1 — « constructible » (cohorte H) | 97,1 % | 97,1 % | **97,2 %** (4 646/4 781) |
| Test 2 — dépassements > 1,10 | 97 | 100 | **102** (+5/−3, TOUS expliqués) |
| terrain_exigu (parcelles H) | 104 | 90 | **80** |

Les 5 dépassements NOUVEAUX sont tous des RÉTRÉCISSEMENTS PRUDENTS d'enveloppe (le permis réel
bat l'enveloppe prudente, mention « capacité supérieure possible, à vérifier » servie —
vérifiée sur AL1109) : AY0595 Étang-Salé UA (contour fermé non qualifié), IZ0339 Saint-Denis Um
(« 1 ou 2 limites sur 10 m » hors liste blanche), BX0548/CD1576 Saint-Joseph U3a (famille
fermée), AL1109 Sainte-Rose 1AUa (porte de largeur fermée au-delà de 14 m). 3 dépassements
sortis (AO1881, AR0040, CD0623).

**LE CONTRÔLE INVERSE FIX-3** (`CONTROLE-INVERSE-FIX3.csv`) : la référence n'est plus
l'ancien cache de l'audit mais **origin/main ACTUEL (`9058a8f55`) rejoué dans un worktree
propre** (cache-main3, 6 569 permis). **22 parcelles** au-dessus de main — chacune justifiée
par des MESURES DE LA PARCELLE (largeur sur voie mesurée sur les arêtes voie, surface, décision
d'implantation rejouée avec ces mesures — plus un contrôle de syntaxe des paramètres de zone) :
Salazie UA ×3 (U 7.2/7.3, liste blanche, implantation ouverte avec les mesures), Le Port Uc
(art. Uc 5, liste blanche), La Possession UB/UBc/AUB ×4 (H/2 à l'ÉGOUT prouvé à l'article,
art. UB 7 p.30), La Plaine-des-Palmistes Ub ×14 (art. Ub 7, liste blanche). **HORS LISTE
BLANCHE : 0** — le script SORT EN ÉCHEC (exit 1) si une hausse non listée apparaît : la règle
FIX-3 est prouvée sur le stock, pas seulement par les tests unitaires.

**Sondage recalé une 2e fois** (`sondage-final/`, section RECALAGE FIX-3) : bandes REFAITES à
la page de la règle réellement appliquée — F02/F22 p.21 (U1b 18 m ; U1a « les rez-de-chaussée…
d'une limite séparative à l'autre » DANS la bande de 10 m depuis la voie), F05 p.46 (UC 7.3),
F06 p.13 (U5.3 régime UA), F12/F17 p.112 (U3a ; U3b/U3c). Lectures corrigées : F17 (AU3b → U3b
= FACULTÉ sous conditions, fermée sous liste blanche), F21 (Uaa imposée AVEC condition patio
non modélisée → aucun scénario chiffré en limite), F23 (Ud « et/ou suivant l'alignement des
constructions limitrophes » = alternative → reclassé, pas une imposée pure). **Les PNG du
sondage sont désormais suivis en Git** (`git add -f`, 56 images).
