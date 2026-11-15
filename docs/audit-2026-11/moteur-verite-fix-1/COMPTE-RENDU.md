# MOTEUR-VERITE-FIX-1 — COMPTE-RENDU (lots 1 et 2, puis ARRÊT)

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
