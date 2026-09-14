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

### 9. RNIC — art. 29-1 + DPE copro → **PARTIEL — producteur** (arbitrage écrit)

**Vérification live** du header du jeu open data ANAH (data.gouv.fr, fichier national CSV) :
**72 colonnes**, énumérées une à une. **AUCUNE ne porte de procédure article 29-1** (mandataire ad
hoc / administrateur provisoire, CCH L.615) **ni d'étiquette DPE de copropriété**. Ces deux
demandes du mandat exigent l'**export ANAH procédures / DPE copro dédié — non public**. C'est
exactement le cas « sinon arbitrage écrit » : **PARTIEL — producteur**.

**Tout champ publié déjà ingéré** : l'ingestion RNIC stocke `raw` (jsonb) avec **67 clés** (les 72
colonnes moins les clés « représentant légal » retirées par la garde RGPD copro). Les signaux
open-data les plus proches d'une « procédure/difficulté » — `copro_dans_pdp` (plan de sauvegarde /
plan de prévention), `copro_aidee`, `copro_dans_acv`/`pvd`, QPV — **sont déjà captés en raw**.

**Aucun re-ingest** : le CSV national (~453 Mo) n'apporterait aucun des champs demandés (absents du
jeu) ; tout ce qu'il publie est déjà en base. 0 code/DB touché. `SCHEMAS.csv` : ligne à-ingérer →
1 PARTIEL-producteur (tracé) + 1 MAXIMUM (signaux difficulté en raw).

---

### 10. BODACC — dépôts de comptes → **MAXIMUM** (fait) — nouvelle table

**Ingestion** : famille BODACC `dpc` (dépôts de comptes annuels) dans une **table dédiée
`bodacc_depots`**, **hors Score V** (mandat : faible valeur foncière). Connecteur : nouvelle
méthode `fetch_depots_by_sirens` + `parse_depot` ; where `familleavis="dpc" AND
numerodepartement="974" AND registre IN (SIREN)` (**garde 974 par département de l'annonce**, filtre
API amont). Ciblage foncier : les **9 733 SIREN propriétaires PM** du 974 (mêmes que les
procédures) — pas les 187 983 dpc du département (99 % sans lien foncier). CLI
`ingest-bodacc-depots`. Table déclarée au réservoir `bodacc`.

**Preuve** : **14 078 dépôts** pour **1 938 SIREN** propriétaires PM, en 3 min 17 s (sous le seuil
3 h). type_depot = « Comptes annuels et rapports » (14 028) / « consolidés » (50) ;
`date_cloture` 2000→(un 2117 aberrant du producteur, fidèle en base). Record complet en `raw`.

**V4e a mordu (2e fois)** : la colonne `cp` a fait casser V4e (232 CP non-974 : sièges de SCI
métropole/Antilles propriétaires de foncier 974). Or ce n'est **pas une adresse-maille 974** — c'est
le CP du **siège social**, légitimement hors 974 ; la garde 974 porte sur `numerodepartement` de
l'annonce. Colonne **renommée `cp_siege`** (sémantique juste), hors du périmètre adresse de V4e.
Aucune garde relâchée, aucune donnée perdue. `SCHEMAS.csv` : 1 à-ingérer → 1 MAXIMUM.

---

### 11. Coût de construction (EPTB) → **MAXIMUM** (fait)

**Constat** : la table `cout_construction_ref` ne portait que 2 lignes (choix promotion LABUSE servi
+ bâti EPTB 145 500 € ≈ 1 516 €/m²). Le mandat veut « la publication annuelle complète ».

**Publication EPTB 2024 Réunion** (SDES, `dreal.statistiques…/eptb/2024/la_reunion`) sourcée : prix
du terrain **117 100 €** (244 €/m², +2 %/an, +22 % vs 2019), bâti 145 500 €/96 m², **coût total
opération 281 700 €** (117 100 terrain + 164 600 bâti), 1 430 projets dont 32 % avec achat de
terrain. **La série EPTB structurée (par type) exclut les DOM** (jeu open data métropole seul,
re-vérifié) → pour le 974 la « publication complète » = ces agrégats DREAL.

**Correctif** : ligne `eptb_2024_terrain` (244 €/m²) ajoutée + note `eptb_2024_maison` enrichie
(coût total, projets). Toutes en **contexte (servi=False)** — la ligne SERVIE au bilan reste le
choix promotion 2 300-2 800 €/m² SDP, **inchangée** (aucun bilan ne bouge). **Cadence ANNUELLE
déclarée à la sentinelle** (365 j, `job_sur_clic`).

**Preuve** : 3 lignes de référence (servie = 2300-2800 inchangée). Passage par la **vanne** : la
nouvelle version part en **quarantaine** (staging pour Vic — comportement voulu ; le servi ne bouge
pas). `SCHEMAS.csv` : 1 à-ingérer → 1 MAXIMUM. Portes vertes.

---

### 12. Forêts publiques (ONF) → **MAXIMUM** (fait)

**Constat** : `ingest_foret_publique` (BDTOPO_V3:foret_publique) ne gardait que `{toponyme, src}`.
Le mandat veut **régime + propriétaire**.

**Correctif** : `attrs` recopie **les 13 champs BDTOPO** + 3 dérivés : **`regime`** = `nature`
(« Forêt domaniale » / « départemento-domaniale »), **`proprietaire`** dérivé du régime (droit
forestier standard : domaniale→État, départemento-domaniale→Département+État, communale→Commune —
pas d'invention), **`gestionnaire`** = `sources` (« ONF 2021 »). `identifiants_sources` (id ONF),
`cleabs`, dates, importance, précision conservés. Le **subtype** (domaniale/publique) qui pilote le
hard_exclude cascade est **INCHANGÉ**.

**Topologie corrigée** : re-ingestion **île entière en une passe** (`commune=NULL`) = **65 forêts
distinctes** (44 domaniale + 21 publique), au lieu de la duplication par-commune (227 : une grande
forêt — Mafate, Plaine des Cafres — intersecte plusieurs bbox communales). Le lecteur cascade lit
`kind_present` global + géométrie → `commune=NULL` sans effet. Subtypes **identiques** à l'existant.

**Preuve** : 65 rows, geom_2975 OK, subtypes 44/21 inchangés ; attrs 2 → 16 clés ;
`regime="Forêt domaniale"`, `proprietaire="État (forêt domaniale)"`, `gestionnaire="ONF 2021"`.
`SCHEMAS.csv` : 1 à-ingérer → 2 MAXIMUM. Portes vertes.

---

### 13. Potentiel foncier (Région ODS) → **MAXIMUM** (fait)

**Constat** : `ingest_potentiel_foncier` restreignait la requête ODS à `select=section,parcelle,
espacesar,zpu,geo_shape` — 4 champs sur 11.

**Correctif** : `select` supprimé → **tout champ publié** du jeu `potentiel-foncier` recopié dans
attrs : **`surf_rp`** (surface m²), **`libelle`** (code SAR, ex. « Um »/« UC »), **`particular`**
(particularité, ex. « en ZAC — ZAC Plateau Domenjod en projet »), `num_rp`, `quartier`,
`geo_point_2d`, `insee` — en plus de espacesar/zpu/section/parcelle. Re-ingestion par-INSEE
(natif au jeu). subtype/`_sar_vocation` inchangés.

**Preuve** : **2 453 îlots / 24 communes inchangés**, geom_2975 OK ; attrs 4 → 9 clés (non-null) ;
`surf_rp=7318.72`, `libelle="UC"` vérifiés. `SCHEMAS.csv` : 1 à-ingérer → 1 MAXIMUM. Portes vertes.

---

## Groupe C — les volumineuses

### 14. Sudocuh → **MAXIMUM** (fait) — flux officiel

**Constat** : l'ancien `scripts/m41_ingest_sudocuh.py` chargeait un **CSV local de 6 colonnes**
(24 communes). Le mandat veut « les ~90 colonnes du fichier ».

**Reprise au flux officiel** : nouveau module `ingestion/sudocuh.py` + CLI `ingest-sudocuh` →
télécharge le **classeur XLSX national DGALN** « État des documents d'urbanisme par commune »
(data.gouv, Licence Ouverte 2.0), feuille `ListeCommunes`. **Le fichier a 23 colonnes** (le « ~90 »
du mandat était une surestimation — vérifié). Filtre **974 par code INSEE** (garde). Tout champ
publié : colonnes promues (region, dept, collectivité porteuse, SIREN EPCI, code état, id DU
opp/en cours, code BCSI, état commune, prescription/approbation/exécutoire DU en vigueur, POP
mun/tot, superficie) + `raw` jsonb complet. `openpyxl` (dép. `ml` déjà déclarée) installé.

**Preuve** : **24 communes / 23 colonnes**, `raw` + `pop_mun` peuplés (24/24). **`approbation_opp`
(lu par qv14 comme date as-of du DU) IDENTIQUE** à l'extrait curaté (**0 diff**) → **zéro impact
scoring** (l'officiel confirme le curaté). SIREN EPCI = 0 (compétence PLU communale au 974, normal).
La chair servie reste `veille_plu.yaml`. Legacy script m41 laissé (superseded, inoffensif).
`SCHEMAS.csv` : 1 à-ingérer → 1 MAXIMUM. Portes vertes.

---

### 15. INSEE RP détail Logements (EGOUL) → **MAXIMUM** (fait) — nouvelle table

**Constat** : `anc.ingest_insee_egoul` n'exploitait qu'`EGOUL` (raccordement) + `IPONDL` du fichier
détail national FD_LOGEMT_2022 (**69 variables**, ~26 M lignes). Le mandat veut « chauffage, taille
fine, toutes les variables ».

**Ingestion** : nouveau module `ingestion/rp_logement.py` + CLI `ingest-rp-logement` → une passe sur
le **même fichier détail** (déjà téléchargé en cache, 419 Mo, `data/insee_rp/`), filtre **974 par
COMMUNE**, agrège par commune les **distributions pondérées (IPONDL)** de **24 variables LOGEMENT** :
chauffage (CHAU/CHFL/CHOS/CMBL), taille (NBPI pièces, SURF surface), type (TYPL/TYPC), période
(ACHL/BATI), catégorie/statut (CATL/STOCD), équipements (EAU/ELEC/WC/BAIN/GARL/ASCEN/CLIM/CUIS/SANI/
VOIT/HLML/CATIRIS). Table `rp_logement_commune` (jsonb). **Agrégat commune uniquement (RGPD** : l'INSEE
ne diffuse pas plus fin que l'IRIS ; aucune ligne individuelle stockée).

**Preuve** : **24 communes, 169 484 logements** agrégés, 24 variables, en 59 s (passe unique). Ex.
Saint-Denis : NBPI {3P:18 329, 4P:16 423…}, CHAU {central:5 868, individuel:62 326}, SURF, CLIM
distribués. Table au réservoir `insee_rp2022_egoul`. Le zip 419 Mo reste **hors git** (`data/`
gitignored). `SCHEMAS.csv` : 2 lignes (RP2023 PARTIEL + EGOUL à-ingérer) → MAXIMUM. Portes vertes.

---

### 16. Cadastre d'époque → **MAXIMUM** (fait) — ⚠ outil Remonter le temps vérifié intact

**Constat** : `MILLESIMES_ETALAB` était une liste **sparse de 5** éditions. L'index Etalab
(cadastre.data.gouv.fr) publie **35 éditions trimestrielles** 2017-07→2026-06.

**Correctif** : `MILLESIMES_ETALAB` densifié aux **35 éditions publiées** (+ BD Parcellaire 2008 +
PCI EDIGEO 2017-02 déjà là). La table `cadastre_historique` est un outil de **récupération
d'orphelines** (parcelles disparues → localisation des permis) ; `_pass_etalab` n'écrit QUE dans
`cadastre_historique` (vérifié : le seul mutateur de `sitadel_permits` est `rattacher_par_geometrie`).
J'ai relancé **uniquement les passes `_pass_etalab` des nouveaux millésimes, SANS rattachement** —
donc **`sitadel_permits` INTACT** (le rattachement, qui change la localisation servie des permis,
reste un geste Vic).

**⚠ Remonter le temps — preuve avant/après** (capture DOM, WebGL non capturable) :

| | avant | après |
|---|---|---|
| millésimes existants | 2008/2017-02/2017-07/2019/2021/2023/2025-09 (1262/221/4586/151/195/70/10) | **identiques (octet pour octet)** |
| nouveau millésime | — | **2026-06 : +31 parcelles** (subdivisions récentes absentes des checkpoints sparse) |
| `sitadel_permits` géoloc | 49 643 | **49 643 (inchangé)** |

→ l'outil sert les **mêmes millésimes** qu'avant + un checkpoint 2026-06 ; aucune localisation de
permis touchée. Les 30 millésimes intermédiaires n'ont récupéré aucune orpheline (déjà captées par
les checkpoints sparse). Passe : 8 min 47 s (sous le seuil 3 h). `SCHEMAS.csv` : 1 à-ingérer →
1 MAXIMUM.

**⚠ Note pour Vic (fragilité de test, PAS un bug SOURCES-5)** : `tests/test_alertes.py` casse quand
la suite est jouée **≥ ~15 fois le même jour** — le plafond quotidien de notifications (50/(kind,
compte,jour), `event_log`) sature à force de runs, et le test compte le total du jour (compte NULL).
Vérifié : reproduit à HEAD=#15 sans mes changements, redevient vert au changement de jour (0 ligne
`veille_zone` committée). Test-isolation à durcir (isoler le compteur du jour), hors périmètre SOURCES-5.

---

### 17. IGN BD CARTO V5 → **MAXIMUM** (fait) — occupation + arbitrage doublons

**occupation_du_sol** : le thème ne publie que **2 champs** (`nature` — déjà servi — et `cleabs`,
identifiant IGN). `cleabs` ajouté aux attrs (code). Je n'ai **pas re-ingéré** (le bbox par-commune
= extent des parcelles déborde sur les communes voisines → duplication 1643→3250 vs le bbox serré
de `ingest-island` ; `moteurs.py` lit `ocs_ge WHERE commune IS NOT NULL` donc l'île-entière/NULL est
exclue). Les 1 643 polygones existants sont conservés intacts ; le `cleabs` sera capté au prochain
`ingest-island` (code prêt, additif).

**Arbitrage « tous les thèmes » (règle G1)** : la Géoplateforme expose **36 thèmes BDCARTO_V5**. **BD
CARTO V5 est PLUS GROSSIER que BD TOPO** (déjà ingéré) → les 35 autres thèmes sont tous des
**doublons** d'une source plus fine : hydro → BD TOPO water ; voirie/aérodrome/voie ferrée/câble →
BD TOPO voirie + transport servi ; bâti (constructions, zone habitation) → BD TOPO constructions +
CoSIA ; cimetière/bassin versant/zone activité → BD TOPO (SOURCES-4) ; ligne électrique → EDF HTA
(#3) ; parc/réserve → patrinat (#5)/parc national ; limite terre-mer → trait de côte (#1) ; admin
(commune/dépt/région/EPCI) → carte des 24. **Seul `occupation_du_sol` est non-doublon** (BD TOPO n'a
pas de thème occupation ; OCS GE 974 hors WFS) — servi. `SCHEMAS.csv` : 1 à-ingérer → 1 MAXIMUM +
1 PARTIEL-doublon. Portes vertes.

---

## Reprise

Commande : **« continue SOURCES-5 »**. Prochaine source : **18. DPE ADEME** (les 230 champs des trois
jeux ; base 974 quasi vide, schéma complet pour le jour où l'ADEME répare son flux DROM).

Restantes après #17 : C18 DPE ADEME 230 champs.
