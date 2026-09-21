# DONNEES-3 — les extracteurs OCS GE du Dossier

Branche `feat/donnees-3` depuis main **1091e458** (après merge de feat/donnees-2). Un commit.

## Le bug (signalé en DONNEES-2)
Le bloc `le_bien.ocsge` (bâti par `bati.py:le_bien_block`) porte les clés `part_artif_pct`,
`cs_dominant`, `us_dominant`, `millesime`, `source`. Les deux extracteurs du Dossier
(`exports/robinet_fiche.py`) lisaient **les mauvaises clés** :
- `_c_artif` → `o.get("artif_pct")` (au lieu de `part_artif_pct`) → toujours `None` ;
- `_c_usage_sol` → `o.get("usage_libelle") or o.get("usage")` (au lieu de `us_dominant`) → `None`.

Résultat : les deux lignes OCS GE tombaient « hors couverture OCS GE » dans le **Dossier**,
alors que la fiche React (`TerrainDuBienBlock`) lit la bonne clé et affiche bien 12,6 %.

## Le correctif (un commit)
`_c_artif` lit `part_artif_pct`, `_c_usage_sol` lit `us_dominant` — les champs réels. Rien
d'autre côté production.

## Preuve — pdftotext du §2 sur 97410000AN0347 (`DONNEES-3-dossier-s2-AN0347.txt`)
```
   2. Terrain
Couverture du sol
Part artificialisée (OCS GE)                      12,6 %                                      sourcé
Usage du sol dominant (OCS GE)                    US6.3                                       sourcé
Part imperméabilisée (CoSIA)                      8,2 %                                       sourcé
Part végétalisée/boisée (CoSIA)                   89,6 %                                      sourcé
Part sol nu (CoSIA)                               0,0 %                                       sourcé
```
Les valeurs OCS GE du PDF (**12,6 %**, **US6.3**) sont **identiques** à celles servies à l'écran
(payload `/parcels/{idu}` → `le_bien.ocsge.part_artif_pct = 12.6`, `us_dominant = US6.3`, lues par
la fiche React).

## Preuve — `preuve_ecran_pdf.py` rejoué sur les deux témoins : 0 écart
```
TOTAL 97410000AN0347 : 39 identiques · 32 absentes dites · 5 non câblées · 0 ÉCARTS
TOTAL 97422000BO0765 : 42 identiques · 29 absentes dites · 5 non câblées · 0 ÉCARTS
```
`part_artificialisee_pct` et `usage_sol_dominant` passent d'**ABSENTE DITE** (avant) à
**IDENTIQUE** (après) sur les deux témoins (BO0765 : artif 44,5 % / US5).

## Pourquoi la recette n'avait pas attrapé ce bug
La recette compare, ligne à ligne, **la valeur de `res.valeurs`** (= `collecte(fiche)` = la sortie
des **extracteurs**) **contre le rendu PDF** (lui aussi produit à partir de `res.valeurs`). Les deux
colonnes « écran » et « PDF » dérivent donc **du même extracteur** : il n'y a **pas d'oracle
indépendant** sur le champ réel du payload (`le_bien.ocsge.part_artif_pct`).

Quand l'extracteur lit une mauvaise clé, il renvoie `None`. La recette entre alors dans la branche
« absence » : elle vérifie que la **phrase d'absence déclarée** est bien imprimée au PDF — et elle
l'est (le miroir imprime l'absence parce que le même extracteur a renvoyé `None`). Donc
**absence côté « écran » == absence côté PDF → « ABSENTE DITE » → compté comme concordant, pas un
écart.** Un extracteur qui renvoie `None` en silence sur un champ pourtant présent est un angle
mort : l'absence concorde toujours avec l'absence.

Après correctif, l'extracteur renvoie 12,6 → la branche « valeur servie » exige que 12,6 se
retrouve au PDF → IDENTIQUE. C'est désormais un vrai contrôle de valeur.

### Un écart résiduel corrigé côté recette (`masquer_si_absent`)
En rejouant, un **autre** écart apparaissait : `dpe_connu` « absence non dite ». Cause :
DONNEES-1 lot 2.2 a introduit le drapeau déclaratif `masquer_si_absent` (la ligne DPE **disparaît**
quand il n'y a pas de DPE — ni valeur ni phrase d'absence), mais n'avait pas appris cette règle à
la recette, qui exigeait encore la phrase d'absence. La recette sait désormais qu'une ligne
`masquer_si_absent` absente est **MASQUÉE** (tenue par la déclaration, écran ET PDF), pas un écart.

## Portes de recette
- **tsc -b** vert (aucune modif front).
- **circuit verrous -w G8** vert (V5d compris).
- Les `{idu}-fiche.json` (entrées de la recette) sont régénérées de l'API `/parcels/{idu}`, non
  committées (convention rebranchement2).
