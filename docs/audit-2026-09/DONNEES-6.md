# DONNEES-6 — permis Sitadel aux dates incohérentes (autorisation avant dépôt)

Branche `feat/donnees-6` depuis main **fd1ed66d** (après merge de feat/donnees-5). Un commit.

## Le constat
**7 745** permis Sitadel (sur 50 143 portant les deux dates, ~15 %) ont une date d'autorisation
antérieure à leur date de dépôt. Cause établie en amont : **donnée brute du producteur** (SDES/Dido),
pas une inversion à l'ingestion (`permits_sdes.py` lit `date ← DATE_REELLE_AUTORISATION`,
`date_depot ← DR_DEPOT`, chacune de sa colonne nommée ; un swap inverserait 100 % des lignes, or 84 %
sont chronologiquement correctes).

## Vérification 1 — le délai médian les inclut-il ? NON, écart nul
Toute médiane de délai filtre déjà `valide` (posé `valide = delai >= 0` par `permit_delais_m10`) :
- fiche commune / comparateur : `registre/moteurs/commune.py` — `WHERE valide AND delai_mois >= 0` ;
- outil Permis : `api/modules.py` — liste `CASE WHEN d.valide THEN d.delai_mois`, fiche `if delai_valide`,
  médianes/p25/p75/tendance toutes en `FILTER (WHERE valide …)` ;
- Flash : `flash/data.py` — `percentile_cont(…) FILTER (WHERE valide AND date_depot <= cut)`.

Contrôle base : `m10_permit_delais` = 50 290 lignes, **7 633** avec `delai_mois < 0`, **toutes
`valide = false`, 0 fuite** (`delai<0 ET valide=true` = 0). Les inversés sont donc déjà hors de tout
calcul → **recalculer « sans eux » rend la même médiane : écart = 0 pour les 24 communes** (rien à
retirer). Le tableau par commune est inutile : la médiane servie ne les a jamais comptés.

## Vérification 2 — modificatifs / transferts ? Profil distinct, mais le flux ne le dit pas
Le flux open data Sitadel3/Dido ingéré **ne porte AUCUNE colonne de numéro de modificatif ni de type
de dossier initial/modificatif/transfert** — seulement `TYPE_DAU` (PC/DP/PA/PD) et `ETAT_DAU`
(en-tête `permits_sdes.py`, schéma vérifié 10/07/2026 ; `permit_id` uniforme 13 car., sans suffixe M).
On **ne peut donc pas étiqueter** un permis « modificatif » depuis la base.

Profil des 7 745 inversés vs 41 937 normaux (circonstanciel, cohérent avec des modificatifs/transferts) :
- **type** : 98 % PC (7 622) — PC 16,6 % inversés vs DP 2,9 % / PA 5,8 % / PD 0,5 % ;
- **achèvement** : **71 %** portent une DAACT (achevés) contre **36 %** des normaux ;
- **écart autorisation→dépôt** : médiane **327 j**, p25 177 j, p75 588 j, max 4 756 j ; **46 %** > 1 an,
  seulement **4,4 %** ≤ 1 mois.
Un original autorisé puis un dépôt de **modificatif/transfert** postérieur (record dont `DR_DEPOT` est
mis à jour, `DATE_REELLE_AUTORISATION` restant l'originale) explique bien ce profil (grands écarts,
dossiers achevés) — mais le flux ne le confirme pas. Les ~4 % à écart ≤ 1 mois ressemblent, eux, à des
erreurs de saisie amont. **Aucune certitude par permis.**

## La correction (un commit)
1. **Délai** : les inversés restent exclus de tout calcul (déjà le cas via `valide`) — verrouillé par
   `tests/test_permis_dates_incoherentes.py` (autorisation avant dépôt → `_months < 0` → jamais `>= 0`).
2. **Affichage — on ne réordonne JAMAIS les dates.** Le flux n'ayant pas le n° de modificatif, on ne
   peut pas écrire « modifié, dernier dépôt le… » : chaque permis inversé montre **les deux dates telles
   que le producteur les donne** + la mention **« dates incohérentes chez le producteur »**. Trois
   surfaces alignées :
   - Dossier (`miroir.py:_r_permis_liste`) ;
   - fiche React « Sur cette parcelle » (`autour.tsx:HistoriqueSiteBlock`) ;
   - outil Permis, fiche d'un permis (`ModulePanel.tsx`) — dates montrées telles quelles, mention + le
     délai d'instruction reste non servi.

## Preuve — Dossier AM0112 (4 PC, 2 inversés) · `DONNEES-6-preuve.txt`
```
Sur cette parcelle (permis) — 4 permis sur la parcelle (Sitadel) —
  PC — déposé 2018-10-15, autorisé 2017-08-25 — dates incohérentes chez le producteur ;
  PC — déposé 2017-12-28, autorisé 2017-03-09 — dates incohérentes chez le producteur ;
  PC — déposé 2016-01-01, autorisé 2016-07-01 ;      ← cohérent, pas de mention
  PC — déposé 2015-01-01, autorisé 2015-07-30
```
Les dates ne sont jamais échangées (label « déposé » puis « autorisé », valeurs brutes) ; seuls les
deux permis réellement inversés portent la mention.

## Portes de recette
- **tsc -b** vert · **circuit verrous -w G8** vert · **pytest** 0 échec nouveau (voir commit).
