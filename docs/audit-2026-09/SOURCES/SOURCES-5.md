# SOURCES-5 — les 18 dernières, jusqu'au bout

**Branche** : `feat/sources-5` depuis `main` (`63c5a3f0`). **Worktree** : `~/Desktop/labuse-sources5`.
**But** : porter à **MAXIMUM** les 18 sources déjà servies mais incomplètes (chemin ancien, extrait,
ou champs manquants). Objectif de clôture : **68 sources MAXIMUM**, `SCHEMAS.csv` sans ligne « à ingérer ».

**Règle** : aucun run, aucune bascule, aucun merge, aucun rescoring. Ingestion par la vanne, garde 974,
sonde, un commit par source, les deux portes rejouées après chaque source.

---

## Étape 0 — les deux portes (ouverture)

- `pwd` = worktree `labuse-sources5`, branche `feat/sources-5`, arbre propre, `.env` présent.
- **Piège d'environnement confirmé** : le binaire `labuse` de conda (`labusedb`) est un editable qui
  pointe sur `~/Desktop/labuse/src` (PAS le worktree). Toute commande doit exporter
  `PYTHONPATH=$HOME/Desktop/labuse-sources5/src` sinon elle joue le mauvais arbre (le premier
  `circuit verrous` lu sans PYTHONPATH tombait sur l'autre arbre = V1c faux rouge de 16 orphelines
  du DB partagé). Prélude standard de session :
  `cd ~/Desktop/labuse-sources5 && set -a && source .env; set +a; export PYTHONPATH=$HOME/Desktop/labuse-sources5/src; export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
- **Porte 1 — verrous** : `24 joués (17 verrous + 7 garanties) : tout va bien` ✓ VERTE.
- **Porte 2 — suite** : `3099 passed, 55 skipped` en 2 min 18 → `✓ suite verte`. ✓ VERTE.

Réseau vers les portails gouvernementaux : OK (geoportail/data.gouv 200, géorisques 301).

---

## Groupe A — reprendre au flux officiel

### 1. GéoLittoral — érosion côtière → **MAXIMUM** (fait)

**Constat** : le chemin était déjà le SHP officiel du Cerema
(`N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip`, 1007 entités, EPSG:2975), mais
l'ingestion (`layers_ingest.ingest_trait_de_cote`) ne gardait que **2 clés** dans `attrs`
(`taux`, `src`) — elle jetait les 12 autres colonnes du dbf.

**Colonnes du SHP** (13) : `nb_tdc, taux, duree, tdc_ancien, incert_anc, tdc_rec, incert_rec,
marqueur, amenagemen, prj_ind, product, date_prod, moa`.

**Correctif** (doctrine SOURCES-4 « tout champ publié ») : la boucle recopie désormais **tout le
dbf** dans `attrs`, sentinelle `-9999`/`-9000` → `None` (donnée absente, jamais affichée telle
quelle), chaînes trimées. `taux` reste le pilote du subtype cascade (inchangé).

**Structure préservée** : la couche est nationale mais stockée **24× (une par commune)** parce que
`faisabilite/db.py:36` la lit `WHERE t.commune = p.commune` — duplication load-bearing, conservée
(24 168 lignes = 1007 × 24). `geom_2975` re-rempli par le trigger `trg_layers_geom_2975` à l'INSERT.

**Preuve (comparaison, ancien gardé en `__precedente` le temps de la mesure puis purgé)** :

| | lignes | geom_2975 | communes | clés attrs | subtypes (pilote cascade) |
|---|---|---|---|---|---|
| avant (`__precedente`) | 24 168 | 24 168 | 24 | 2 (`src,taux`) | 48 / 4800 / 3360 / 15960 |
| après | 24 168 | 24 168 | 24 | **14** (13 SHP + `src`) | **48 / 4800 / 3360 / 15960** |

→ distribution des subtypes **identique** = cascade/verdicts **inchangés** ; seul `attrs` s'enrichit.
Échantillon après : `{taux:0.0, duree:58.0, nb_tdc:2, tdc_ancien:1950, tdc_rec:2008, incert_anc:50,
incert_rec:10, marqueur:3, amenagemen:0, prj_ind:'UTM40', product:'Cerema', date_prod:'10-Feb-2017',
moa:'MTES-DGALN'}`.

`SCHEMAS.csv` : la ligne unique « à ingérer » remplacée par **13 lignes MAXIMUM (SOURCES-5)**.
Réservoir `erosion_cotiere_geolittoral` millésime re-libellé.

**Portes après source 1** : verrous 24/24 ✓ · suite 3099 passed ✓.

---

## Reprise

Commande : **« continue SOURCES-5 »**. Prochaine source : **2. Classement sonore ITT** (service
ArcGIS Cerema, largeur d'affectation + référence d'arrêté).

Restantes après #1 : A2 classement sonore ITT · A3 EDF HTA · A4 ZNIEFF (WFS INPN) · A5 INPN espaces
protégés (WFS Géoplateforme) · A6 Ramsar/sites classés · A7 DILA · B8 AZI/TRI dates · B9 RNIC
29-1/DPE copro · B10 BODACC dépôts de comptes · B11 Coût construction · B12 Forêts ONF régime ·
B13 Potentiel foncier colonnes restantes · C14 Sudocuh · C15 RP Logements EGOUL · C16 Cadastre
d'époque · C17 BD CARTO V5 · C18 DPE ADEME 230 champs.
