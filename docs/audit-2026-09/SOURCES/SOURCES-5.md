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

### 2. Classement sonore ITT (Cerema) → **MAXIMUM** (fait)

**Constat** : le chemin était déjà le service ArcGIS officiel du Cerema
(`Routes_classement_sonore_La_Reunion_V2/FeatureServer/0`, 1004 tronçons, maxRecordCount 2000 →
pas de troncature). L'ingestion (`bruit_route.ingest_bruit_route`) matérialise correctement la
BANDE (buffer `sect_bruit` m sur l'axe, EPSG:2975, subtype `cat1..cat5`), mais ne gardait que
**7 clés** d'`attrs`, jetant ~50 colonnes publiées.

**Largeur d'affectation** = `sect_bruit` (déjà là, pilote le buffer) ; **référence d'arrêté** =
métadonnée (les AP préfectoraux des 14 & 15/12/2023) — n'existe pas comme champ dans le flux,
désormais **explicitée** dans `attrs.reference_arrete`.

**Correctif** : `attrs` recopie **tout champ publié** (56 clés) — trafic (`tmjatv_*`, `tmja_vl20a`,
`tmja_pl20a`, `pl__global`), niveaux acoustiques de référence (`jlaeq_ref`/`nlaeq_ref`),
débits/vitesses VL/PL par période (`*_0618/1822/2206`), voirie (`larg_chaus`, `nb_voies`, `rampe`,
`sens_circu`), tissu/zonage, identité du tronçon. Clé accentuée `catégorie`→`categorie` (int),
chaînes vides→None. Logique buffer/subtype **inchangée**.

**Preuve** :

| | lignes | geom_2975 | subtypes (pilote cascade) | clés attrs |
|---|---|---|---|---|
| avant | 1004 | 1004 | cat1:83 / cat2:147 / cat3:494 / cat4:278 / cat5:2 | 7 |
| après | 1004 | 1004 | **cat1:83 / cat2:147 / cat3:494 / cat4:278 / cat5:2** | **56** |

→ distribution des catégories **identique** = cascade inchangée ; `reference_arrete` présent,
`jlaeq_ref=69`, `tmjatv_an=2016` vérifiés. `SCHEMAS.csv` : ligne « à ingérer » → 10 lignes MAXIMUM
(familles de colonnes). Portes après #2 : à jouer ci-dessous.

---

### 3. EDF HTA (réseau moyenne tension) → **MAXIMUM** (fait)

**Constat** : chemin déjà officiel (portail open data EDF Réunion Koumoul/data-fair,
`reseaux_mt.ingest_lignes_mt`, 4211 tronçons aériens + 15 269 souterrains). **Vérification live des
CSV** : le flux ne publie que **3 colonnes** — `statut`, `geo_shape` (géométrie, = geom de la
couche), `geo_point_2d` (centroïde). EDF a **retiré** la tension exacte et le nom de départ « afin
de renforcer la sécurité publique » (mention du portail).

**Arbitrage (mandat A#3 « tension + gestionnaire »)** : ces deux-là ne sont pas des colonnes du
flux — mais ce sont des **faits de jeu, sourcés et constants** que la fiche du portail donne :
la **tension** est la classe HTA (moyenne tension 15-20 kV — c'est la définition du jeu), le
**gestionnaire** est **EDF SEI** (Système Électrique Insulaire, exploitant du réseau réunionnais).
Surfacés en clairs dans `attrs.tension_classe` / `attrs.gestionnaire`. La tension au volt près
reste **non publiée = raison producteur** (documenté). `geo_point_2d` = doublon G1 de la géométrie,
non ingéré (arbitrage écrit).

**Preuve** : 19 480 tronçons (4211 + 15 269) inchangés, geom_2975 backfillée ;
attrs `{statut, millesime, precision}` → `{statut, millesime, precision, tension_classe,
gestionnaire}`. `SCHEMAS.csv` : 1 ligne à-ingérer → 4 MAXIMUM + 1 PARTIEL-doublon (geo_point_2d).

---

### 4. ZNIEFF (INPN/MNHN) → **MAXIMUM** (fait)

**Constat** : chemin déjà officiel (WFS Géoplateforme `patrinat_znieff1/znieff2`, `znieff.build_znieff`,
134 type I + 28 type II = 162 continentales, marines exclues à raison). L'`id_mnhn` (identifiant
national) et `type` I/II étaient déjà là — mais seules **5 clés** étaient gardées sur les 22 publiées.

**Correctif** : `attrs` recopie **les 22 champs du WFS** — `cd_sig` (code national SIG),
`id_local`, `nom_site`, `url_fiche`, `gest_site`/`operateur`, dates (`date_crea`, `modif_adm`,
`modif_geo`, `acte_deb/fin`), surfaces (`surf_off`, `area_sig`), `precision`, `src_geom`/`src_annee`,
drapeaux (`marin`, `territoire`, `p1_nature`, `p4_geologi`). `type` et alias `gestionnaire`
conservés pour les lecteurs existants. Gardes marin/territoire inchangées.

**Arbitrage** : la **liste des espèces déterminantes** n'est PAS dans cette couche WFS géométrique
(jeu INPN distinct) → PARTIEL-producteur pour ce seul détail ; MAXIMUM sur tout ce que le WFS publie.

**Preuve** : 162 zones inchangées (134/28), geom_2975 OK ; attrs 5 → 23 clés ;
`id_mnhn=040030088`, `cd_sig=I032G2040030088`, `type=type I` vérifiés. `SCHEMAS.csv` : 1 ligne
à-ingérer → 8 MAXIMUM + 1 PARTIEL (espèces).

---

### 5. INPN / patrinat — espaces protégés → **MAXIMUM** (fait) — + bug de perte silencieuse corrigé

**Constat** : `ingest_espaces_proteges` (kind `ens`, 7 typenames patrinat WFS Géoplateforme) ne
gardait que **3 clés** (`type/src/marin`). **En re-vérifiant les typenames sur GetCapabilities**
(data.geopf.fr) j'ai découvert que **2 avaient dérivé et renvoyaient un 400 avalé par un
`except: continue` MUET** : `patrinat_rb:reserve_biologique` → devenu `patrinat_rb:rb` (les **37
réserves biologiques** ne rentraient plus, 4 communes de couverture perdues : Bras-Panon, Cilaos,
Les Avirons, Salazie) et `patrinat_aphn:aire_protection_habitats_naturels` → `patrinat_aphn:aphn`.

**Correctifs** : (1) typenames corrigés + `patrinat_rncfs:rncfs` ajouté (réserve nationale de
chasse, 0 au 974 mais couche officielle) ; (2) l'échec WFS n'est **plus muet** (log.warning,
principe « jamais une couche vide en silence ») ; (3) `attrs` recopie **tout champ publié**
(24 clés : `id_mnhn`, `cd_sig`, `id_local`, `nom_site`, `url_fiche`, `gest_site`/`operateur`,
dates, `surf_off`/`area_sig`, `precision`, `src_geom`, drapeaux).

**Portée préservée** : re-ingestion **par commune** (le lecteur cascade `kind_present_commune('ens',
commune)` s'appuie sur la colonne `commune` — une ingestion île entière `commune=NULL` aurait
basculé ~21 communes en UNKNOWN). Seules les lignes source 25 (patrinat) touchées ; l'ENS
départemental DEAL Lizmap (source 113) et les sites/ramsar **intacts**.

**Preuve** : 73 lignes, **21 communes** inchangées, subtypes identiques (apb 8 / cdl 27 /
réserve_biologique 37 / rnn 1), LOST=[] GAINED=[] ; attrs 3 → 24 clés ; `id_mnhn=FR23REU01`,
`gest_site=ONF` vérifiés. `SCHEMAS.csv` : 1 ligne à-ingérer → 7 MAXIMUM.

---

### 6. Espaces protégés Ramsar / sites classés → **MAXIMUM** (arbitrage : flux DEAL conservé)

**Comparaison des deux flux officiels** (règle Groupe A : ne basculer que si le Géoplateforme est
plus complet) :

| couche | DEAL Carmen (servi, source 113) | Géoplateforme patrinat |
|---|---|---|
| Ramsar | 1 (Étang Saint-Paul) | 1 |
| sites classés | 5 | 5 (`patrinat_sc:sc`) |
| **sites inscrits** | **2** | **0 — aucune couche nationale** |
| réserves naturelles | 152 | (autre couche) |
| ENS départemental | 178 | absent (jeu non public) |

**Verdict** : le Géoplateforme **n'est PAS plus complet** — il n'expose **aucune couche de sites
inscrits** (l'INPN patrinat ne publie que `sc` = classés), alors que la couche DEAL
`Sites_Classes_-_Inscrits` porte les deux. Basculer PERDRAIT les 2 sites inscrits (Mare à Poule
d'Eau…). De plus le flux DEAL est **déjà « tout champ publié »** (SOURCES-4 lot 3 : les sites
portent `identifian` 974-00x, `nature_du_` « arrêté ministériel », date, surface). Seul apport
Géoplateforme = l'`id_mnhn` national — cross-référence fragile (join inter-source) pour 6 entités,
G1/doublon → **non substitué**. **Décision : DEAL Carmen reste canonique.** Aucun code/DB touché,
comparaison tracée. (Pas de ligne « à ingérer » dans `SCHEMAS.csv` : la source était déjà MAXIMUM.)

---

### 7. Annuaire de l'administration (DILA) → **MAXIMUM** (fait) — nouvelle table

**Constat** : `mairies.py` (K2) ne captait que les **24 mairies**. Le mandat veut **tous les
services**.

**Ingestion** : nouveau module `ingestion/annuaire_services.py` + CLI `ingest-annuaire-services`
→ table **`annuaire_services`**. Source ODS `api-lannuaire-administration`. **Garde 974 au plus
tôt** : filtre API `startswith(code_insee_commune,"974")` (974xx = La Réunion seule) PUIS
re-vérification par ligne. **Tout champ publié** : les 44-49 champs du record DILA conservés dans
`raw` (jsonb), les plus utiles promus en colonnes (nom, pivot_type, sigle, categorie,
type_organisme, insee, commune, cp, adresse, tél, email, site, mission…). Upsert par `id` +
**purge des services disparus** (idempotent).

**Registre / lecteur / gate** : table déclarée dans le réservoir `annuaire_service_public`
(carte → V1c verte) ; lecteur ajouté à `/admin/contacts-institutionnels` (clé `services`, via
`services_974()`) — le réservoir n'est pas muet. La section front « annuaire complet » reste un
ajout mince à faire (backend prêt ; les 24 mairies restent affichées comme aujourd'hui).

**Preuve** : **436 services** ingérés, **garde 974 = 0 rejet non-974** (INSEE), **136 types** de
service (france_services 37, point_justice/tribunaux 32, gendarmerie 28, mairie 24, ccas 22,
police_municipale 22, sip 11, préfecture 10…), **24 communes** couvertes, `raw` = 49 champs complet.

**V4e a mordu (bon signe)** : la 1re passe a fait CASSER V4e — la colonne `code_postal` portait des
CP DILA erronés (93200 Seine-St-Denis, 97250 Martinique sur des antennes mal saisies) et des CEDEX
978xx. Ces lignes ont pourtant un **INSEE 974** (ce SONT des services réunionnais) → la ligne n'est
pas rejetée, mais la colonne servie `code_postal` est validée par le garde (`_cp_prefixe_974`,
974/977) : sinon NULL (16 lignes), le CP brut reste dans `raw`. **Aucune tolérance ajoutée**, garde
non relâché. `SCHEMAS.csv` : 1 ligne à-ingérer → 3 MAXIMUM.

**Doublon** : les 24 mairies figurent aussi dans `annuaire_services` (même source DILA) ; la table
`mairies` reste le contact spécialisé par commune lu par la fiche — granularité distincte, pas un
doublon inter-source.

---

## Groupe B — champs supplémentaires

### 8. AZI / TRI — dates + bassin de risques → **MAXIMUM** (fait)

**Constat** : `azi_communes` ne gardait que `libelle`, `risques`, `date_diffusion`. Le GASPAR
publie bien plus : **`libelle_bassin_risques`** et, pour l'AZI, `date_debut/fin_etude`,
`date_realisation`, `date_debut/fin_programmation`, `date_debut/fin_information`,
`date_publication_web` ; pour le TRI, `date_arrete_pcb/carte/pcb_local/prefet/approbation/national`.

**Correctif** (additif, `ALTER … IF NOT EXISTS`) : colonnes `bassin_risques`, `dates` (jsonb =
tous les champs `date_*`) et `raw` (jsonb = record GASPAR intégral). Reader `azi_tri_commune`
surface bassin + dates. Table replacée à l'identique (DELETE + réinsertion), rien de run-scopé.

**Preuve** : **39 lignes / 22 communes inchangées** (30 AZI + 9 TRI), 128 scénarios TRI intacts ;
`bassin_risques` 30/39, `dates` 39/39, `raw` 39/39. Exemple TRI Saint-Denis :
`dates={date_arrete_pcb:25/01/2013, date_arrete_carte:26/12/2013}` ; AZI La Montagne :
`bassin_risques="La Montagne"`. Les `date_*_etude` de l'AZI sont **null au 974 = trou producteur**
(GASPAR ne les remplit pas ici ; captés quand présents). `SCHEMAS.csv` : 2 lignes à-ingérer → 3
MAXIMUM.

---

## Reprise

Commande : **« continue SOURCES-5 »**. Prochaine source : **9. RNIC** (procédures article 29-1 +
étiquette DPE de la copropriété, si le jeu open data les porte — sinon arbitrage écrit).

Restantes après #8 : B9 RNIC 29-1/DPE copro · B10 BODACC dépôts de comptes · B11 Coût construction
· B12 Forêts ONF régime · B13 Potentiel foncier colonnes restantes · C14 Sudocuh · C15 RP Logements
EGOUL · C16 Cadastre d'époque · C17 BD CARTO V5 · C18 DPE ADEME 230 champs.
