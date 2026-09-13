# SOURCES-2 — les 92 au plein potentiel, d'après les producteurs

**Branche** `feat/sources-2` (worktree `~/Desktop/labuse-etat`), tirée de `main` après merge de
REPARATIONS-1. Référence : `RECHERCHE-PRODUCTEURS.md` (lu en entier avant toute écriture).
Étape 0 : 23/23 verrous verts (V3a candidat `q_v14` déclaré, manifeste sert `q_v11_m137`).
Aucun run, aucune bascule, aucun merge, aucun rescoring. Aucun scraping.

---

## LOT 0 — Le DPE, réparé pour de bon

### Ce que le mandat croyait, ce que le producteur montre

Le mandat partait de : « le filtre 974 rend 900 lignes métropolitaines pour 17 authentiques ;
la cause est le code postal ; réingérer en filtrant sur le code INSEE commune 974xx ». **Vérifié
chez le producteur le 13/09/2026 : le filtre INSEE ne répare rien.** Le schéma ADEME
(`dpe03existant`, 230 champs) n'a AUCUN champ « INSEE commune brut » — le seul INSEE est
`code_insee_ban`, produit du géocodage BAN de l'ADEME, et c'est LUI qui est contaminé :

| Filtre (dpe03existant) | Lignes |
|---|---|
| `code_insee_ban:974*` | 914 |
| `code_departement_ban:974` | 914 (identique) |
| `code_postal_brut:[97400 TO 97490]` | 16 |
| INSEE 974 **et** CP brut 974 | 14 |
| INSEE 974 **et** CP brut métropolitain | **900** |

Les 900 sont des logements **métropolitains** (échantillon vérifié : « 38-40 rue Saint Louis,
62200 BOULOGNE-SUR-MER » géocodé Saint-Paul ; Sète, Schiltigheim, Damgan…) que le géocodeur BAN
rabat sur l'île. Le CP brut, saisi par le diagnostiqueur d'après le bien, reste le seul juge —
la doctrine du module était la bonne.

### Le vrai gain : les jeux jamais ingérés — et le piège d'homonymie

Les jeux `dpe02neuf` (1,42 M lignes) et `dpe01tertiaire` (563 k) n'étaient **pas ingérés**.
Moisson CP brut 974 sur les trois jeux = **93 lignes** (16 existants + 75 neufs + 2 tertiaires).
Mais l'examen ligne par ligne a révélé le piège inverse — **le CP brut lui-même peut mentir par
homonymie de commune** :

- les **75 « neufs »** sont UN programme immobilier : `nom_commune_brut = "ST LEU"`, CP saisi
  97436 — mais géocodage BAN **Saint-Leu-la-Forêt (Val-d'Oise, 95563)** score 0,97, et les voies
  (« 42 rue du Rû », « 44-46 rue de Paris ») **n'existent pas** dans la table `adresses` du
  Saint-Leu réunionnais (0 résultat). C'est exactement le « risque d'homonymie majeur » que le
  rapport producteurs signalait (Saint-Denis, Saint-André, Saint-Leu, Saint-Louis) ;
- les **2 « orphelins »** historiques du jeu existant sont à **Montpellier** (« 123 TER avenue de
  Palavas », BAN 34172) et **Lille** (« 40 rue des Jardins Caulier », BAN 59350) — CP brut mal
  saisi. Ils étaient en base depuis M71, épinglés « aucun » ; ils tombent.

**Règle gravée** (`ingest_jeu`, testée) : une ligne au CP brut 974 dont le géocodage BAN est
réunionnais (cohérent) est gardée ; une ligne dont le BAN contredit (ou manque) n'est gardée que
si son adresse brute se **corrobore dans la table `adresses` locale** — sinon rejetée. Mieux vaut
une absence honnête qu'un logement de métropole épinglé sur une parcelle réunionnaise.

### Avant / après

| | avant | après |
|---|---|---|
| Jeux ADEME couverts | 1 (existants) | **3** (existants + neufs + tertiaire) |
| Lignes en base | 17 (dont 2 fausses — Montpellier, Lille — et 1 disparue amont) | **16, toutes corroborées** |
| Rattachées parcelle | 15/17 | **16/16** |
| Rattachées bâtiment (ID-RNB) | 0 (colonne absente) | **8/16** (`rnb_id`, clé BAN → `rnb_batiments.adresses`, sinon contenance géométrique) |
| Miroir producteur | non (lignes mortes conservées) | **oui** (DPE retiré/remplacé amont → supprimé) |
| Rejets mesurés | — | 77 métropolitaines (900 contaminées jamais entrées) |

Détail par jeu (run du 13/09/2026) : existant 14 gardés / 2 rejetés · neuf 0 / 75 · tertiaire 2 / 0.
Le tertiaire n'a ni `type_batiment` ni surface habitable au schéma (sa `surface_utile` reste dans
`raw`, jamais maquillée en habitable) ; `type_batiment='tertiaire'`.

### L'état INVISIBLE ne tombe PAS — et c'est le résultat honnête

Le mandat conditionnait : « faire tomber l'état INVISIBLE **si la fiche se remplit** ». Elle ne se
remplit pas : 16 DPE sur toute l'île ne couvrent aucun des 12 témoins (G2 re-mesuré après
ingestion : `1 source vide (dpe_ademe), 0 sans état INVISIBLE`). La cause n'est plus un filtre :
**les DPE réunionnais ne remontent presque pas à l'observatoire ADEME** (obligation DROM
01/07/2024, mais ni le jeu existants ni le jeu neufs n'en portent la trace en volume — aucun jeu
DOM dédié au catalogue, vérifié). C'est un **trou producteur**, écrit comme tel dans le registre.
Volume « après lot 0 » pour le lot 6 : **16**.

Sentinelle : `dataUpdatedAt` data-fair — mesuré le 13/09/2026, les trois jeux publient dans le
même train mensuel (09/09 tous les trois) → le jeu principal suffit comme signal de version
(commentaire gravé dans `sentinelle.py`).

Preuves : `labuse ingest-dpe` (sortie ci-dessus rejouable), `tests/test_dpe.py` 13/13 dont
`test_ingest_jeu_homonymie_et_miroir`, verrous 23/23 verts après lot.

---

## LOT 1 — Les endpoints qu'on aurait dû utiliser depuis le début

Une ligne par source : ancien chemin · nouveau · ce qui a changé · preuve. Constat d'ensemble :
une partie du lot était DÉJÀ au bon endpoint (SOURCES-1/REPARATIONS-1) — vérifié plutôt que
refait ; la migration réelle du lot est la bascule **Carmen → Lizmap** et les gardes de
recoupement.

| Source | Ancien | Nouveau | Ce qui a changé | Preuve |
|---|---|---|---|---|
| Ravines DPF | WFS Carmen 29 (GML → ogr2ogr) | **WFS Lizmap** `00cartogenerale/deal_reunion`, GeoJSON natif | mêmes comptes (275 cours + 6 plans) ; plus de dépendance GDAL | ingestion rejouée 13/09, comptes identiques |
| Zones humides DEAL | WFS Carmen 29 | **WFS Lizmap** | mêmes comptes (1 507+187+30+49+1 349) ; QGIS Server sert des anneaux dégénérés → nettoyage géométrique ajouté | ingestion rejouée, 1 349 = Carmen |
| Espaces protégés compl. | WFS Carmen 29 | **WFS Lizmap** | Lizmap sépare RNN Étang (2) et **RNMR marine (150 zones réglementées** vs 1 agrégat Carmen) ; + **`Espace_Naturel_Sensible` du Département (178, gestionnaire/propriété/dateMAJ)** — la couche « ms:ENS » du rapport, jamais servie avant | `ens/ens_departement` 178 en base |
| DEAL PPR / aléas | Lizmap `01risque` (déjà migré, SOURCES-1) | inchangé + **couche « état des PAC, PPR, PPRL et date d'approbation »** (`02etat_ppr_pac`, 24 communes) | kind `ppr_etat` (statuts Approuve/En revision + 6 dates par commune) ; `source_millesime` = plus récente approbation lue chez le producteur : **PPR approuvé le 16/04/2026** | 24/24 communes ingérées |
| 50 pas géométriques | — | **déjà sur Lizmap** (`LIMITE_HA`, 163 tronçons) depuis SOURCES-1 | rien à migrer | vérifié code + base |
| Cartes de bruit CBS | WFS Carmen `Cartes_bruit_strategiques` | **pas de migration** : le projet Lizmap `cartesbruitstrategiques` ne publie AUCUNE couche en WFS (GetCapabilities vide, WMS image seule — vérifié 13/09) | Carmen reste le seul canal vectoriel | probe WFS/WMS 13/09 |
| Classement sonore ITT | ArcGIS Cerema (catégories 1-5, 1 004 tronçons) | **déjà le producteur méthodo** (Cerema) ; Lizmap ne le sert pas en WFS | rien | sentinelle `count` déjà en place |
| CatNat | API GASPAR paginée (déjà, CIRCUIT-3) | + **recoupement export CSV national** (`gaspar.zip` officiel) à chaque ingestion | garde « l'API a perdu des arrêtés » VISIBLE ; mesuré : CSV 426 = base 426, **écart 0** | `labuse ingest-catnat` sortie |
| AZI / TRI | GASPAR par commune (déjà) | inchangé (scénarios TRI = lot 4) | — | — |
| GTFS transport | PAN, 7 slugs (déjà) | **vérifiés UN PAR UN le 13/09** : Car Jaune (maj 12/09/2026, RT), Citalis (16/07), Papang (29/12/2025, validité→2028), Kar'Ouest (17/08), Alternéo (25/08, RT×3), Carsud (20/08, RT), Estival (27/01) — tous valides ≥ 31/12/2026 | GTFS-RT : disponible sur 3 réseaux, **documenté non ingéré** (positions temps réel = donnée d'exploitation éphémère, sans valeur foncière — arbitrage) | table au registre |
| DVF | — | **déjà l'amont Etalab/DGFiP** (`files.data.gouv.fr/geo-dvf`, 974 couvert) ; base au **31/12/2025** = la MàJ du 07/04/2026 est intégrée ; DVF Région déjà rétrogradée en échantillon producteur (0 donnée servie, SOURCES-1 lot 4) | rien à faire, vérifié | `max(date_mutation)=2025-12-31` |
| LiDAR HD | millésime « dalles publiées 25/06/2025 » | **WFS du tableau d'assemblage** (`IGNF_LIDAR-HD_METADONNEE:metadata`) : balayage des 2 665 dalles 974 → **survol du 11/08/2023 au 11/10/2023** (mission unique 23LHDREUNION, capteur RIEGL VQ780 II-S), édition MNx 13/03/2025 — la date de survol est désormais AFFICHÉE (source_millesime) ; le TA donne MNT/MNS/MNH + COPC.LAZ par dalle | sentinelle témoin TA déjà en place (RECETTE-11 A5), doublon évité | balayage 13/09 |
| BD TOPO | Géoplateforme WFS (déjà) | sentinelle `api` sur le jeu (archivage trimestriel) déjà en place | rien | vérifié |

**Arbitrages écrits :**
- **TYPEINF 03 ≠ anciens DPU.** Le rapport producteurs recommandait d'ajouter `TYPEINF=03` aux
  périmètres DPU. Vérifié CONTRAIRE chez le producteur : l'unique typeinf 03 du 974
  (L'Étang-Salé, DU_97404) est libellé « Espace Naturel Sensible » = zone de préemption **ENS du
  Département**, pas un DPU communal. L'ingérer en `kind='dpu'` aurait fait mentir la cascade.
  Écarté, gravé dans `gpu_infos.py`.
- **Noms de registre conservés.** Les 3 sources « (DEAL Carmen) » gardent leur nom — c'est la
  clé stable de `data_sources` (jointures circuit/sonde) ; l'endpoint, le provider et les notes
  disent la vérité Lizmap. `deal974.lizmap.com` ajouté aux passerelles mutualisées (G1).
- **Découverte au passage (pour le lot 2)** : le zonage d'assainissement (`typeinf 19`) EXISTE
  au GPU pour L'Étang-Salé (42 entités, DU_97404) et Saint-Paul (27) — le rapport producteurs le
  croyait absent partout.

Verrous 23/23 verts après lot (G1 re-passé après déclaration de la passerelle Lizmap).

---

## LOT 2 — Les trous producteurs, dits honnêtement et pas plus

### DPU — l'état des 24 communes (balayage GPU du 13/09/2026, partition par partition)

Le rapport producteurs disait « confirmés en ligne : Saint-Pierre et Saint-Benoît ». Le
producteur (GPU) dit AUTRE CHOSE — les communes qui publient un périmètre au GPU sont :

| État | Communes | Détail |
|---|---|---|
| **Périmètre publié au GPU** (typeinf 04, servi en carte + fiche) | **Saint-Denis** (41 : simple + renforcé), **Saint-Paul** (158, dont délégations nommées : « Délégation DPU BARRAGE (ZAD TCO) », BELLEMÈNE, CENTRE-VILLE…), **Sainte-Marie** (1, renforcé), **Le Tampon** (2) | 202 périmètres en base |
| **DPU institué, périmètre non publié au GPU — délégataire documenté** | **Saint-Pierre** (délégation EPF Réunion, convention n°16 24 01, délib. 35/1689-1690 du CM du 21/10/2024, simple + renforcé) ; **Saint-Benoît** (portage EPF, périmètre ajusté au PLU du 06/02/2020, délib. DEL 079 09 2022) | phrase dédiée servie à la fiche |
| **RNU** | **Saint-Philippe** — aucun document au GPU, zonage quasi absent (9 parcelles N) ; ⚠ le drapeau GPU `is_rnu=False` n'est corroboré par aucun document (dit dans la phrase) | « pas de DPU possible sans PLU/POS/carte communale » |
| **Non publié — délégataire probable EPF** | les 17 autres | phrase du rapport : « un DPU s'applique très probablement en zones U/AU (l'EPF Réunion est délégataire pour plus de 80 % des communes — Cour des comptes) mais son périmètre n'est pas publié — vérifier en mairie ou auprès de l'EPF Réunion » |

**« Jamais pas de DPU » est gravé dans le code** (`_DPU_HORS_GPU` + `_DPU_NON_PUBLIE_DEFAUT`,
`api/app.py`) : l'état `non_determinee` de la fiche sert désormais la phrase par commune.
Recensement EPF : les délibérations récentes du CA (`epf.re`, lues — 04/11/2025, 05/12/2025,
02/06/2026, 25/06/2026) ne contiennent que des *exercices* de DPU sur des ventes, pas le
recensement des conventions par commune — l'énumération exhaustive des délégataires exigerait
le dépouillement des archives CA pluriannuelles : dit ici, pas inventé.

### SIS — les projets Nord-Est/Sud servis « non opposables »

Dossier officiel préfecture téléchargé (`dossier SIS actualisé.zip`, arrêtés n°2026-215/216/
217/218-SG-SCOPP du 19/02/2026, modifiés 405/406 du 02/04/2026, consultation close le
07/05/2026) : **7 fiches de sites** extraites (id SSP, commune, centroïde EPSG:2975,
superficie). Servies en `sol_pollue/sis_projet`, **distinctes des SIS définitifs** Géorisques,
statut « projet de SIS — non opposable » toujours porté : CORETAB (Saint-Pierre), Décharge
Petite Plaine (La Plaine-des-Palmistes), Interlinge et Sucrerie Savanna (Saint-Paul), SCPR
(Saint-Louis), ZAC Triangle de l'Oasis (Le Port) — **6 points posés**. La 7e fiche (« Pipe
line SRE », Le Port, linéaire) publie des coordonnées dans un CRS non identifié
(10 162 963/517 213 — ni 2975, ni 3857) : **aucun point inventé**, anomalie dite ici.
Sentinelles : ZIP préfecture (détection d'octets, semée) + les définitifs restent sur le
témoin SSP bi-commune existant.

### PEB Pierrefonds — le vecteur TROUVÉ chez le producteur (pas de géoréférencement)

Le chemin du mandat s'arrêtait au géoréférencement du plan PDF. Mesuré dans l'ordre :
1. **SUP T5 au GPU** : 0 assiette T5 sur la bbox de Saint-Pierre (l'annexe SUP du PLU ne la
   porte pas) — échec confirmé ;
2. **Géoportail** : le WFS ne sert que le POINT aérodrome (`dgac_peb_arrete_wfs`) + le PDF de
   l'arrêté — mais la couche **`dgac_peb_plan_wmsv`** (WMS-vecteur Géoplateforme, données
   **STAC/DGAC**) rend les zones, et son **GetFeatureInfo JSON renvoie la géométrie COMPLÈTE
   et les attributs** de chaque zone (service OGC officiel, aucun scraping). Échantillonnage
   de l'axe de piste (21 points), dédoublonnage par id : **les 4 zones A/B/C/D de FMEP**
   récupérées avec Lden int/ext, `date_arret=2017-03-29`, `date_maj` STAC 12/04/2022, lien
   arrêté PDF. Précision ~11 m (4 décimales), dans la tolérance du plan au 1/25 000 — dit.
3. Géoréférencement PDF : **inutile** (et le PDF de l'arrêté ne contient d'ailleurs PAS la
   carte, vérifié).

Ingestion `ingest_peb_pierrefonds` (zones A/B/C/D EXIGÉES sinon échec franc, purge ciblée
FMEP, Roland-Garros intact) → **8 zones PEB en base** (4 FMEP + 4 Roland-Garros). Le détail
« Pierrefonds non publié au GPU » de la fiche est corrigé.

### Saint-Leu — révision en cours, servie sur toutes les parcelles

`dispositifs.plu_procedure` (nouveau, back + front) : « PLU en révision — enquête publique du
1er septembre au 9 octobre 2026 ; le PLU actuel reste opposable » + lien
`registre-numerique.fr/revision-plu-stleu`, sur TOUTE parcelle de Saint-Leu. Sentinelle : le
« module procedure » du GPU n'existe pas à l'API Carto (404 vérifié) ; le vrai signal est
l'**apparition du document au GPU** (aujourd'hui 0 à la partition DU_97413, vérifié) — témoin
semé sur `/document?partition=DU_97413` (léger, métadonnées seules).

### Assainissement, PLH, OLL, Chroniques de l'eau — déjà dits, vérifiés

- **Assainissement** : le rapport producteurs (« aucune publication open data, ni GPU
  typeinf 19 ») est CONTREDIT par le producteur : 4 communes ont leur zonage SIG au GPU
  (L'Étang-Salé, Le Port, Saint-Denis, Saint-Paul — déjà ingérées, `zonage_assainissement`),
  ailleurs l'app sert le taux de non-raccordement du secteur (INSEE RP2022), jamais une proba
  parcellaire. Rien à changer : l'app fait déjà MIEUX que la phrase du mandat.
- **PLH des 5 EPCI** : extraction documentaire, rappel `depot_manuel` 365 j — trou vectoriel
  producteur, déjà déclaré.
- **Loyers OLL** : agrégats par zone servis ; micro-données = CHANTIER sous convention
  (demande écrite prête) — déjà déclaré.
- **Chroniques de l'eau** : servies (classement ANC 3 communes), PDF producteur, licence à
  confirmer (lot 5) — déjà déclaré.

Verrous 23/23 verts après lot (2 sondes semées : GPU document DU_97413 + ZIP SIS préfecture).

---

## LOT 3 — Trois sources nouvelles

### 1. Systèmes d'endiguement et zones protégées (DEAL Lizmap) — INGÉRÉE

Projet Lizmap dédié `02sprinr/03digues` (vérifié live 13/09/2026). **69 tronçons de digue +
48 zones protégées** → `spatial_layers kind='endiguement'`. Chaque zone protégée porte la
classe d'ouvrage (A/B/C), le **niveau de protection** (période de retour), les niveaux/débits
NGR de danger-protection-sûreté, la **population protégée**, le gestionnaire, l'arrêté et la
source d'étude (EDD Hydrétudes déc. 2024) — et TOUJOURS le statut « inondation résiduelle
au-delà du niveau de protection ». Intégration complète : registre (`endiguement`), pont,
carte table→réservoir, filtre (sous-types + classe ≥ 80 %, joué OK), sentinelle (raison
écrite, même famille Lizmap), couche carte (aplat zones + trait digues, popup riche
classe/niveau/population, familles « Risques et nuisances »), `labuse ingest-endiguement`.
Licence : non écrite sur Lizmap → courrier DEAL (lot 5).

### 2. Carte hypsométrique du littoral (DEAL) — IMAGE SEULE chez le producteur, dit

La carte existe : projet Lizmap `02sprinr/04tsunami` (« Carte hypsométrique du littoral de La
Réunion », couche `Courbes_de_niveau_hypsometrique__en_metres`). Mais le producteur ne la sert
qu'en **WMS image** : la couche est **REFUSÉE en WFS** (`ServiceException: TYPENAME not
available`, vérifié 13/09/2026) — aucun vecteur à ingérer sans convention. Déclarée au
registre en CHANTIER (`S.A_FAIRE`, hors vitrine, raison écrite V2b) avec la demande de vecteur
au courrier DEAL (lot 5). **La donnée de submersion marine est servie à la place par le
vecteur réglementaire du même producteur** : les aléas PPRL `Alea_submersion_marine` (50
zones) et `Alea_submersion_marine__changement_climatique` (50) du projet `01risque`, ingérés
dans `georisque_alea` (subtypes `submersion_marine`/`submersion_marine_cc`, degré + dates
PAC/approbation, auteur BRGM) — total aléas 1 093 zones sur les 24 communes. Ils apparaissent
d'eux-mêmes dans la fiche Risques (lecture par intersection, tous subtypes) ; le bouton carte
dédié est laissé à la validation pixels de Vic (doctrine COUCHES-1).

### 3. BAN PLUS — lien adresse ↔ bâtiment ↔ parcelle (IGN) — INGÉRÉE

WFS Géoplateforme `BAN-PLUS:lien_adresse_bati` : id adresse BAN ↔ bâtiment BD TOPO (cleabs) ↔
**IDU parcelle** — ingéré : **745 874 liens** (0 hors 974), dont **629 825 avec ID-RNB
(84,4 %)** résolus localement par `rnb_batiments.ext_bdtopo` — l'ID-RNB devient la clé de
jointure DPE ↔ RPLS ↔ BAN. Table `ban_plus_liens` (moisson paginée 5 000/page, filtrage 974 au
plus tôt, idempotente). ⚠ leçon gravée : la jointure tableau se fait par `unnest` (hash join) —
le `= ANY(ext_bdtopo)` naïf est un produit croisé 746 k × 414 k, annulé après 28 min. Registre, pont, carte table→réservoir, filtre (0 lien hors 974 bloquant +
part RNB ≥ 50 % avertissant), sentinelle api (`last_update` du jeu data.gouv, IGN — maj
27/08/2026). Licence Ouverte 2.0. `labuse ingest-ban-plus`.

---

## LOT 4 — Les champs laissés sur la table

Champ par champ — **ajouté**, **déjà servi (vérifié)**, ou **absent chez le producteur (dit)** :

| Champ du mandat | État | Détail |
|---|---|---|
| Scénarios d'inondation AZI/TRI (fréquent/moyen/extrême) | **AJOUTÉ** | les 12 couches d'iso-hauteurs des 6 TRI (WFS Lizmap `01risque`, standard DI v2) → `tri_zone` : **128 zones** (43 fréquent `01For` / 42 moyen `02Moy`+`03Mcc` / 43 extrême `04Fai` — codes MESURÉS chez le producteur, jamais devinés), hauteurs d'eau min/max, flag changement climatique, TRI, servi en carte (kind whitelisté + popup riche). ⚠ deux couches (PIER/SUZA) servent leurs champs en minuscules — lecteur insensible à la casse |
| Isophones (cartes de bruit) | **déjà servi** | `bruit_carte` : dépassements Lden/Ln par source (routes dép./nat., voies communales) — WFS Carmen, le seul canal vectoriel (Lizmap = WMS image, lot 1) |
| Catégories sonores (classement) | **déjà servi** | `bruit_route` : 1 004 tronçons, catégories 1-5 + largeur (ArcGIS Cerema) |
| Acte des SUP | **AJOUTÉ** | champ `fichier` du GPU = l'arrêté/décret PDF de la servitude → `attrs.acte_fichier` sur chaque assiette |
| Générateur des SUP | **AJOUTÉ** | endpoints `generateur-sup-s/l/p` interrogés par commune, joints par `idgen` → `attrs.generateur_nom/type` (ex. « LA RAVINE DU BERNICA », type Site) |
| Bénéficiaire des ER | **absent chez le producteur (dit)** | vérifié sur les dépôts GPU 974 : les prescriptions ER ne portent que `libelle` (« Emplacement réservé ») + `txt` (numéro) — aucun champ bénéficiaire structuré dans les GeoJSON servis. Rien à ingérer sans inventer |
| Avancement Cartofriches | **déjà servi (vérifié)** | `attrs.site_statut` (« friche avec projet », « friche potentielle ») + `site_reconv_type/annee` présents sur les friches Cerema ET AGORAH en base |
| Classe DPE des logements RPLS | **AJOUTÉ — vide chez le producteur (dit)** | colonnes `DPEENERGIE/DPESERRE` du fichier logement Dido branchées (`rpls_commune.dpe_classes`, `pct_passoires`, `pct_dpe_renseigne`) — MESURÉ : DPEENERGIE vide sur les 87 553 logements 974 → 0 % renseigné partout, cohérent avec le lot 0 (DPE DROM quasi absents). Le canal servira dès que le producteur remplira |
| Lien parcelle ↔ SIREN des PM | **déjà servi (vérifié)** | `parcelle_personne_morale.siren` en base (panel millésimes 2019→2025) |
| Filiation DFI | **déjà servi (vérifié)** | `dfi_filiation` : 409 623 lignes (frise Remonter le temps, OUTILS-MUSCLER-2) |
| Hauteur BD TOPO | **déjà servi (vérifié)** | `batiment_hauteur_lidar.hauteur_bdtopo_m` (+ faîtage/égout LiDAR et écart mesuré) |
| TMJA du trafic RN | **déjà servi (vérifié)** | `trafic_rn.tmja` (+ part poids lourds `nb_pl`, géométrie tronçon) |
| Limites du DPF | **déjà servi** | `dpf` cours_eau 275 + plan_eau 6 (migré Lizmap, lot 1) |
| Assiette AC1 des MH | **déjà servi (vérifié)** | `sup/ac1` : 6 assiettes en base (3 communes), désormais avec acte + générateur |

Mesure post-ingestion SUP : **417 assiettes, 417 avec acte, 411 avec générateur** (24 communes).

---

## LOT 5 — Les licences : le dossier pour Vic

Livré dans **`LICENCES-A-CONFIRMER.md`** (même dossier) : six courriers d'une page, prêts à
envoyer — DEAL Réunion (toutes les couches Lizmap, + demande du vecteur hypsométrique),
Conservatoire du littoral, ONF, EDF Réunion (SEI), Parc national, Région Réunion (trafic RN,
DVF Région, potentiel foncier, + rappel SAR). Chaque courrier nomme les couches consommées et
demande une réponse ÉCRITE sur la réutilisation commerciale.

**Audit ODbL** (dans le même fichier) : 7 dérivés OSM inventoriés (amenite, parkings_aper,
tcsp_*, pole_echange, parcel_amenites…), chacun avec son verdict de redistribuabilité —
conformes, avec la règle gravée : tout export en masse d'une base dérivée doit porter l'ODbL
et l'attribution. BANO : non utilisée (BAN IGN Licence Ouverte seule, vérifié).

**DVF, la clause qui peut mordre — vérifiée** : servie agrégée/à la parcelle, jamais
nominative, jamais jointe à une identité de personne physique (le fichier PM DGFiP EXCLUT les
personnes physiques) ; pages derrière authentification (403 à deux comptes) ; exports
cloisonnés par compte. **Aucun chemin de ré-identification ni d'indexation.** Ce lot n'écrit
pas en base.

---

## LOT 6 — Les « à confirmer », confirmés chez le producteur

| « À confirmer » du rapport producteurs | Réponse, mesurée le 13/09/2026 |
|---|---|
| Couverture/millésimes OCS GE 974 | **CONFIRMÉ et déjà servi** : OCS GE native D974, millésimes 2017 + 2022 (livraisons IGN 2025-04) + diff artificialisation officiel 2017→2022 (2025-09-16) — REPARATIONS-1, en base |
| Couverture/millésime CoSIA 974 | **CONFIRMÉ deux fois** : lot D974 GPKG natif millésime 2025 (PVA juil.-août 2025, 20 cm) DÉJÀ ingéré ; et les 3 périodes WMS/WMTS (2017-2020, 2021-2023, 2024-2026) rendent une classification réelle sur Saint-Denis (GetMap vérifié) |
| GéoLittoral érosion — couverture 974 | **CONFIRMÉ** : fichier Réunion dédié chez le producteur (`N_evolution_trait_cote_S_reunion_epsg2975_062018`, HTTP 200) — mais millésime 06/2018 (8 ans), dit ; sentinelle octets en veille |
| Loyers DHUP — couverture 974 | **CONFIRMÉ** : le CSV national 2025 (publié 11/12/2025) porte les 24 communes 974, `loypredm2` par commune (vérifié ligne à ligne) — gravé au registre |
| Complétude RNB 974 | **MESURÉ** : 414 081 bâtiments · rattachement BD TOPO 74,3 % (43 123 sans RNB intersectant, 166 851 recouvrement insuffisant) · hauteurs LiDAR 98,6 % |
| Date de survol LiDAR HD | **LEVÉ (lot 1)** : 11/08/2023 → 11/10/2023, mission unique 23LHDREUNION, capteur RIEGL VQ780 II-S, édition MNx 13/03/2025 — affichée au registre |
| Volume DPE réel après lot 0 | **16** DPE réunionnais corroborés (14 existants + 2 tertiaires) — trou producteur, pas trou de filtre (lot 0) ; corollaire : le champ DPE du RPLS est VIDE chez le producteur pour les 87 553 logements sociaux 974 |

Restent invérifiables (écrits comme tels) : les licences des producteurs du lot 5 (réponses
écrites attendues — c'est l'objet des courriers), et le vecteur hypsométrique DEAL (WMS image
seule tant que la DEAL n'ouvre pas la couche).

---

## Clôture

- **Fiches** : `fiches/<id>.md` — 22 fiches écrites/mises à jour, verdicts recalculés d'après
  les mesures produites par ce mandat (pas d'après le rapport de recherche).
- **Registre** : 121 sources en base = 96 en vitrine + 25 hors vitrine (3 nouvelles : 2
  servies + 1 chantier) ; toutes les sondes semées, aucune source NUE (G4).
- **Le run servi `q_v11_m137` est INTACT** : aucun run, aucune bascule, aucun merge, aucun
  rescoring. Les couches ajoutées enrichissent la lecture LIVE et les prochains runs, jamais
  les verdicts gelés.
- **Verrous** : 23/23 verts à la clôture (rejoués après chaque lot ; le « à décider » V1d
  ban_plus levé en donnant au réservoir son lecteur réel — donnée `ban_plus_adresses_bati`
  au bloc « Le bien », robinet `/parcels/{idu}`).
- **Tests** : back **3 026 passed / 34 failed — les 34 sont TOUS déjà en échec sur main**
  (différentiel mesuré : main 38 échecs sur la même base, la branche en répare 4 au passage,
  n'en ajoute 0 ; le seul échec introduit — attente des couches aléas dans
  `test_deal_risques` — corrigé) ; front tsc 0 erreur, vitest 207/207.
- **Preuves servies (API du mandat, `:8032`)** : `/map/layers.geojson?kind=endiguement` →
  117 (69 digues + 48 zones protégées) ; `?kind=tri_zone` → 128 (43/42/43) ; fiche parcelle
  Saint-Leu `97413000AC0001` → `plu_procedure` (révision + lien), `dpu` (phrase « jamais pas
  de DPU »), `adresses_bati` BAN PLUS (10 liens, 2 adresses, 5 bâtiments). L'API `:8032`
  reste lancée pour la relecture de Vic ; `:8020` jamais touchée.
- **Rien n'est mergé.** Vic relit, envoie les courriers licences, merge.
