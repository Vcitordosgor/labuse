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
