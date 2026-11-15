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

**Mesures après LOT 2** (rejeu complet, cache `cache-lot2/`) : [MESURES-LOT2]

**Contrôle inverse après LOT 2** : [CONTROLE-LOT2]

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
