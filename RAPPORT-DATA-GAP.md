# RAPPORT DATA GAP — audit & complétion des sources (mandat 10/07/2026)

Branche `feature/data-gap-2026-07` (depuis main, tag `score-v1.1` inclus). **Phase 0 : audit
réel du code et de la base** — rien n'est supposé, chaque statut a été vérifié (tables,
`spatial_layers`, modules d'ingestion, `config/cascade_rules.yaml`, cascade étages 0/1/2).
La Phase 1 (colonnes « Décision Phase 1 ») sera complétée lot par lot.

## Socle confirmé PRÉSENT (hors lots)

| Source | Où (code / base) | Notes |
|---|---|---|
| PLU calibrés 23 communes + St-Philippe RNU | `config/communes_gold_standard.yaml`, `plu_*.yaml`, couches `plu_gpu_zone` (6 306) / `plu_gpu_prescription` (17 765), cascade `zonage_plu_gpu`+`prescription_plu` | ✓ |
| Cadastre / parcelles | `parcels` = 431 663, geom_2975, centroïdes | ✓ |
| Propriétaires PM (DGFiP) | `parcelle_personne_morale` = 82 701 liens | ✓ + enrichissements Score V |
| BODACC | `bodacc_procedures`, `bodacc_annonces_owner`, étage 2 + Score V | ✓ |
| INPI RNE | `pm_dirigeants` (27 146), gigogne, étage 2 `age_dirigeant` | ✓ |
| Géorisques PPR + aléas | couches `ppr` (164), `georisque_alea` (993), `icpe`, `cavite`, `mvt`, cascade `risques` | ✓ |
| Cartofriches | couche `friche` (372), étage 1 POSITIVE | ✓ |
| DPE ADEME | `dpe_records` (910 — base 974 intrinsèquement mince), étage 2 flag | ✓ |
| QPV 2024 | couche `qpv` (57), fiscal fiche | ✓ |
| ABF / Mérimée | couche `abf` (200), cascade UNKNOWN covisibilité | ✓ |
| ENS | couche `ens` (73), SOFT_FLAG moyen | ✓ |

## Lots cibles — statut d'audit

| Lot | Source cible | Statut | Où dans le code / la base | Manque exact |
|---|---|---|---|---|
| 1 | DVF Etalab 974 | **PARTIEL** | `dvf_mutations_parcelle` (102 551 lignes, 37 868 parcelles, **millésimes 2021-2025 seuls** — 2014-2020 retirés de la distribution) ; `dvf_mutations` (points, bonus étage 2 existant) | Variables par parcelle (prix / prix·m² dernière mutation) non matérialisées ; **médiane €/m² par secteur × type de bien** absente. Flag « >20 ans » incalculable (consigné). Aucun scoring dormance (Score V le fait déjà). |
| 2 | SIS + CASIAS | **PARTIEL** | Géorisques `/ssp` ingéré : couche `sol_pollue` = 480 (tous `identifiant_ssp`, 424 `identifiant_casias`) ; cascade étage 1 `sol_pollue` ≤ 50 m SOFT_FLAG **faible** (`etage1.py:71`) | Distinction SIS (intersection périmètre) vs CASIAS (< 100 m) absente ; malus actuel = faible/info, mandat = malus Stage 1 + mention fiche coût dépollution |
| 3 | PEB + classement sonore | **ABSENT** | rien (aucune couche, aucun module) | Tout — sources à identifier (GPU/DEAL : PEB Roland-Garros + Pierrefonds, classement sonore ITT 974) |
| 4 | SUP complètes (GPU) | **ABSENT** | rien — API Carto GPU `assiette-sup-s/l/p` vérifiée VIVANTE sur le 974 (acte-sup répond à St-Denis) | Tout (I4, canalisations, T4/T5/T7, autres) |
| 5 | SAR / SMVM | **PARTIEL** | couche `sar` (2 453) = **PROXY** vocation via « potentiel foncier » Région ODS (couverture partielle, îlots seulement) ; vocations dont « Coupure d'urbanisation » (~23) et « Espace d'urbanisation prioritaire » présentes ; cascade : INFO SANS pouvoir d'exclusion (décision Vic 08/07/2026, `phase1.py:129`) | Le SAR **réglementaire** (zonage complet DEAL/Région + SMVM) : à retrouver ; si introuvable → BLOQUÉ (le proxy reste informatif, décision 08/07 respectée) |
| 6 | 50 pas géométriques | **ABSENT** | rien | Tout — source DEAL/ONF à identifier |
| 7 | Périmètres irrigués (ILO/PEIGEO) | **ABSENT** | rien (PEIGEO déjà noté injoignable dans une vague antérieure) | Tout — retenter PEIGEO + data.gouv |
| 8 | Dynamique constructive | **PARTIEL** | `sitadel_permits` = 50 043 (SDES/Dido, jusqu'au mois courant — mandat Sitadel3 mergé) ; bonus étage 2 `sitadel` rayon 200 m / 36 mois (binaire de fait) ; signal `new_permit_nearby` = ÉVÉNEMENT (veille, non scoré), touche 31 499 parcelles sur St-Paul seul | Indicateur **GRADUÉ** (densité PC 300-500 m / 5 ans) par parcelle ; graduation du bonus existant SANS double compte (cf. décision lot 8) |
| 9 | Potentiel résiduel (bâti + MNT) | **PARTIEL** | `parcel_residuel` = 263 626 (SDP résiduelle, `faisabilite/residuel.py`) ; bâti BD TOPO 817 506 dont **85,7 % avec `hauteur`** et `nombre_d_etages` ; grille pente RGE ALTI **~180 m** (147 398 cellules, `slope_pct`) ; cascade pente = max des cellules intersectées | `parcel_terrain(idu, pente_moy_deg, pente_max_deg, flag_terrassement_lourd)` absent ; pente 5 m à dériver (RGE ALTI 5 m, disque OK : 100 Gi libres) ; vérifier que `residuel.py` consomme bien la hauteur réelle (placeholder niveaux repéré) |
| 10 | RNIC copropriétés | **ABSENT** | rien | Tout |
| 11 | Pack marché | **PARTIEL** | `commune_contexte_sru` (24, millésime 2025, statuts dont 2 carencées) ✓ ; `commune_insee_logement` (RP 2023) ✓ ; loyers DHUP 2025 (`data/carte_loyers_reunion_2025.json` + `loyers.py`) ✓ ; Obsimmo ✓ | **RPLS** (parc social par commune) absent ; **Filosofi carreaux 200 m** absent ; (`plh_epci` vide — noté, PLH hors liste cible) |

## Vérifications AJOUTS SESSION

1. **Permis datés dans le futur : 1 seul** (max 2026-08-17, > aujourd'hui) sur 50 043 → < 50 :
   **artefact d'alimentation source consigné**, parsing de dates hors de cause.
2. **`new_permit_nearby`** : signal d'ÉVÉNEMENT (delta de veille, rayon 200 m, non scoré) —
   le lot 8 produira bien un indicateur **gradué** (densité), le booléen ne discrimine plus
   (31 499 parcelles touchées sur Saint-Paul).

## Contraintes actées

- Score V intouchable (tables/moteur/vue) — la dormance/vendabilité n'est re-scorée nulle part.
- Espace disque vérifié : 100 Gi libres → RGE ALTI 5 m 974 possible, dalles brutes nettoyées
  après dérivation du raster de pente (conservé pour le mandat ortho).
- Millésimes et règles de scoring exactes : complétés lot par lot en Phase 1 ci-dessous.

## Phase 1 — journal des lots (complété au fil de l'eau)

*(à venir : un bloc par lot avec statut final, règle de scoring exacte, millésime, volumétrie)*

### LOT 1 — DVF : FAIT (variables marché, zéro scoring)
- `v_parcel_dvf_last` : **37 868 parcelles** avec dernière mutation (date, nature, valeur,
  prix/m² bâti, prix/m² terrain, flag multi-parcelles). Caveat DVF : valeur = mutation entière.
- `dvf_secteur_medianes` : **2 357 lignes** (850 secteurs cadastraux × type de bien,
  39 425 ventes 2021-2025). Moy. des médianes : terrain 295 €/m², maison 2 471 €/m² bâti,
  appartement 2 361 €/m² — plausibles. Ventes ≤ 1 000 € (symboliques) écartées ; prix/m²
  bornés [50-20 000]. Grain MUTATION (pas de double compte multi-lignes).
- Fiche : bloc `dvf_parcelle` (dernière mutation + médianes secteur). CLI `labuse dvf-marche`.
- **Aucun scoring** (mandat) : dormance = Score V ; « mutation > 20 ans » incalculable
  (millésimes 2014-2020 retirés). Millésime : géo-DVF 2021→2025 (pub. 04/2026).

### LOT 2 — SIS + CASIAS : FAIT
- Connecteur Géorisques étendu : sous-collection `/ssp.conclusions_sis` (périmètres SIS
  MultiPolygon réglementaires) → couche `sol_pollue` subtype `sis`. Ré-ingestion 24 communes :
  **4 SIS + 426 CASIAS + 56 instructions** (millésime : API Géorisques live 10/07/2026).
- Règle de scoring (Stage 1, couche `sol_pollue`) : parcelle ∩ périmètre SIS → SOFT_FLAG
  **moyen** (pénalité ×2), détail fiche « coût de dépollution potentiel, étude de sol
  obligatoire à la mutation (L.556-2 CE) » ; site CASIAS/instruction ≤ **100 m** (élargi de
  50 m) → SOFT_FLAG faible (×1). Verdicts cliquables (source_table/source_id).

### LOT 8 — Dynamique constructive : FAIT (graduée, ajout session)
- Couche `sitadel` (scored) passée de binaire à **GRADUÉE** : magnitude = min(1, n_PC/15)
  dans un rayon **400 m** sur **60 mois**, **PC seulement** (DP/PA/PD exclus de la densité).
  Détail fiche : « Dynamique constructive : n PC ≤ 400 m sur 5 ans (densité X %) ».
- **Écart au mandat documenté** : le mandat demandait un bonus Stage 1 — l'audit a montré
  que le bonus scoré existe déjà (couche `sitadel`, Stage 2/axe A, Socle V1) ; en créer un
  second en Stage 1 aurait doublonné le même signal (interdit par le lot). Gradué EN PLACE.
- `new_permit_nearby` (événement de veille) inchangé — rôles désormais distincts :
  événement (delta) vs densité (niveau). Millésime : sitadel_permits SDES jusqu'au mois courant.

### LOT 4 — SUP (assiettes GPU) : FAIT / PARTIEL-source
- Ingestion `sup_gpu.py` (API Carto GPU, assiette-sup-s/l/p, bbox par commune, idempotent) :
  **417 assiettes** sur les 24 communes. CLI `labuse ingest-sup`.
- **Constat source** : le GPU 974 n'expose QUE pm1 (311), pm3 (30), pm2 (29), el10 (23),
  ac1-ac4 (24) — les catégories prioritaires du mandat (**I4 lignes HT, I1/I3 canalisations,
  T4/T5/T7 aéronautiques) ne sont PAS téléversées au GPU pour le 974** → règles prêtes
  (SUP_SEVERITES) mais sans données ; elles s'activeront seules au premier téléversement DEAL.
- Règle de scoring (Stage 1, couche `sup`) : t5 fort ; t4/t7/i4/i1/i3 moyen ; défaut faible ;
  pm1/pm2/pm3 + ac1/ac2 + el10 = info ×0 (**anti-double-compte** : déjà scorés par `risques`,
  `abf`, `parc_national`). Liste complète des SUP en fiche (détail du verdict).
- Millésime : GPU live 10/07/2026.

### LOT 3 — PEB + classement sonore : PARTIEL (sonore FAIT, PEB BLOQUÉ)
- **PEB : BLOQUÉ** — les zonages A/B/C/D de Roland-Garros (AP 2017-2123 du 17/10/2017, qui
  remplace le PEB 1996) et de Pierrefonds (AP 29/03/2017) n'existent **qu'en PDF préfecture**
  (~25 Mo). Vérifié : geo-ide (décommissionné, 0 fiche 974), WFS geopf `dgac_peb_arrete_wfs`
  (0 objet sur la bbox 974), dataset national 2020 (métropole seule), GPU (pas de PEB 974),
  PEIGEO/Lizmap DEAL (aucune couche). Digitalisation des PDF = hors périmètre du mandat.
  Les règles Stage 0/1 prévues (A/B exclusion, C malus fort, D info) restent à brancher au
  premier SIG disponible.
- **Classement sonore : FAIT** — flux Cerema/Cartagène (ArcGIS REST, export intégral),
  **1 004 tronçons** cat. 1-5, bandes MATÉRIALISÉES (buffer `sect_bruit` 10-300 m en 2975)
  → `spatial_layers kind='bruit_route'`. Règle Stage 1 : cat 1-2 → SOFT_FLAG **moyen**,
  cat 3-5 → **faible** (« isolement acoustique renforcé obligatoire, R.571-32 CE »).
  Millésime : Cerema 2022, en vigueur (AP 14-15/12/2023). CLI `labuse ingest-bruit-route`.

### LOT 5 — SAR / SMVM : BLOQUÉ (source réglementaire non diffusée)
- Le zonage SIG réglementaire du SAR 2011 (espaces urbains/agricoles/naturels, coupures
  d'urbanisation, ZPU) n'est diffusé NULLE PART en open data exploitable : Région ODS 0/277
  datasets, PEIGEO fiches sans lien (GeoServer 348 couches : aucune SAR), AGORAH renvoie à
  PEIGEO, SyOP = PDF 34,6 Mo, Ifremer = WMS raster (ERL SMVM 2010 seulement). La révision du
  SAR passe au Conseil d'État en 2026 — à requêter à la Région/AGORAH hors open data.
- Le PROXY existant (vocations via potentiel foncier, couverture partielle) reste en place,
  INFORMATIF sans pouvoir d'exclusion (décision Vic 08/07/2026 inchangée). Les règles du
  mandat (coupure = Stage 0/malus très fort, ZPU = bonus) s'appliqueront au SIG réglementaire
  le jour où il sera obtenu.

### LOT 7 — Périmètres irrigués : BLOQUÉ (donnée existante mais non diffusée)
- Les fiches PEIGEO « Irrigation Départementale » (secteurs en service / programmés / à
  l'étude, création 07/2025, Département DAE) existent mais TOUS les liens de distribution
  sont morts (localhost) ; le GeoServer PEIGEO (348 couches) n'a aucune couche irrigation ;
  ILO absent de data.gouv/Région/Office de l'eau. **Seule voie : demande directe à la DAE
  (secretariatdae@cg974.fr)** — consigné pour action Vic. Le renforcement du verrou Stage 0
  prévu s'appliquera à réception.

### LOT 6 — 50 pas géométriques : FAIT (approximation documentée)
- Source : WFS Lizmap DEAL (`LIMITE_HA`, 163 tronçons ~184 km, cadastre 1877 géoréférencé,
  5 tronçons mis à jour « étude documentaire 02/2026 »). La **bande polygonale n'est diffusée
  nulle part** → CORRIDOR ±90 m autour de la limite haute matérialisé (kind='cinquante_pas').
- Règle Stage 1 : parcelle intersectant le corridor → SOFT_FLAG **faible** « au contact de la
  bande des 50 pas — régime foncier spécifique à vérifier, cession encadrée ». Libellé
  volontairement prudent (« au contact », jamais « dans la bande ») — sur-inclusif côté terre.
- Sanity : **16 099 parcelles** au contact. CLI `labuse ingest-cinquante-pas`.

### LOT 9 — Potentiel résiduel (bâti + MNT) : FAIT (complète l'existant)
- **Audit confirmé** : `parcel_residuel` (263 626 parcelles) consomme DÉJÀ la hauteur/étages
  réels BD TOPO quand présents (85,7 % des 817 506 bâtiments ont `hauteur`) — le volet
  « bâti existant » était couvert, rien re-fait.
- **Pente 5 m** : RGE ALTI 5M D974 (millésime 2023-09-05, archive 251 Mo) → `gdaldem slope`
  → raster `data/rgealti/pente974_5m.tif` (378 Mo, **CONSERVÉ pour le mandat ortho**, dalles
  brutes et archive NETTOYÉES) → PostGIS `rgealti_pente_5m` (2 793 tuiles 200×200) →
  **`parcel_terrain`** (schéma canonique du mandat : idu PK, pente_moy_deg, pente_max_deg,
  flag_terrassement_lourd) : **423 452 parcelles** (98,1 % — le reliquat = hors emprise MNT),
  pente moyenne 9,2°, **86 885 en terrassement lourd** (moy > 15° ou max > 30°, choix documenté).
- Fiche : bloc `terrain`. La couche cascade `pente` (grille 180 m) reste en place pour le
  scoring Stage 1 (déjà branchée) — parcel_terrain est la table canonique fine (ortho, fiche).
- ⚠ Extraction : archive 7z SOLIDE → /vsi7z/ GDAL inutilisable en accès aléatoire (constaté :
  20 min pour 22 Ko) ; extraction py7zr (3 s) ajoutée au venv, consignée.

### LOT 10 — RNIC copropriétés : FAIT
- Fichier national ANAH T3 2025 (453 Mo, URL stable data.gouv) filtré 974 → table
  `rnic_coproprietes` : **2 220 copropriétés**, rattachement parcelle **87 %** (1 083 par
  référence cadastrale — déjà au format IDU dans le fichier —, 850 par point long/lat,
  287 sans rattachement). Lots, période de construction, syndic (SIRET), mandat en cours.
- **Pas de scoring** (mandat, cible MdB) : fiche parcelle (bloc `coproprietes`) + table
  filtrable (index parcelle_idu / insee). CLI `labuse ingest-rnic --csv <fichier national>`.

### LOT 11 — Pack marché : FAIT (RPLS + Filosofi ajoutés ; SRU/loyers/INSEE déjà présents)
- **RPLS 01/01/2025** (SDES/Dido, filtré serveur 974) → `rpls_commune` : 24 communes,
  **87 553 logements sociaux** (nb, année construction médiane, % QPV, surface moyenne).
  Script reproductible `scripts/ingest_rpls.py`.
- **Filosofi 2021 carreaux 200 m** (INSEE — le millésime 2021 couvre bien La Réunion,
  EPSG:2975) → `filosofi_carreaux_200m` : **14 773 carreaux** (ind, ménages, pauvreté,
  propriétaires, niveaux de vie, âges, logements par époque).
- **Déjà présents (audit)** : SRU 2025 (dont 2 communes carencées), carte des loyers DHUP
  2025, INSEE logement RP 2023, Obsimmo — rien re-fait.
- Fiche : bloc `marche_secteur` (carreau Filosofi au centroïde + RPLS commune). Pas de
  scoring parcelle (mandat). Alimentera module bailleur + calculette de charge foncière.

## Phase 2 — Sanity check chiffré (nouveaux flags, sur 431 663 parcelles)

| Flag | Parcelles | Lecture |
|---|---|---|
| Périmètre SIS intersecté (malus moyen) | **35** | 4 périmètres au 974 — rare et localisé, attendu |
| CASIAS/instruction < 100 m (malus faible) | **10 318** | 2,4 % — rayon élargi 50→100 m |
| Bruit routier cat 1-2 (malus moyen) | 23 016 + 25 433 | bandes 250-300 m des grands axes |
| Bruit routier cat 3-5 (malus faible) | 67 890 + 13 897 + 6 | |
| Bruit routier — toutes catégories (distinct) | **111 228** | 25,8 % — élevé mais attendu (réseau dense en zone urbanisée, bandes réglementaires jusqu'à 300 m) ; signalé, pas suspect |
| SUP scorées ac3/ac4 (malus faible) | **3 959** | 0,9 % |
| SUP toutes catégories (distinct, surtout pm1 info ×0) | 188 692 | 43,7 % — dominé par pm1 (PPR), NEUTRALISÉ anti-double-compte, aucun impact score |
| 50 pas — corridor limite haute (malus faible) | **16 099** | 3,7 % du parc, littoral |
| Terrassement lourd (pente 5 m) | **86 885** | 20,5 % — île volcanique, attendu ; parcel_terrain couvre 423 452 parcelles (98,1 %) |
| Dernière mutation DVF connue | 37 868 | fenêtre 2021-2025 |
| RNIC rattachées parcelle | 1 933 / 2 220 | 87 % |

Aucun flag à 0 % ni ≥ 90 % : rien de masqué, deux valeurs hautes expliquées ci-dessus.

## Phase 2 — Impact chaudes (recalcul île complet, label isolé `q_v3_datagap`)

⚠ **`q_v2` reste la source de vérité de l'app** — le recalcul vit sous un label dry-run
séparé ; la bascule (et sa calibration) est une décision Vic au merge.

| Statut | q_v2 (avant) | q_v3_datagap (après) |
|---|---|---|
| chaude | 1 083 | **5 455** |
| a_surveiller | 6 570 | 1 592 |
| a_creuser | 16 003 | 15 580 |
| ecartee | 408 007 | 409 036 |

**Diagnostic du ×5 sur les chaudes — entièrement imputable au LOT 8** (vérifié en base) :
les 4 627 nouvelles chaudes n'avaient AUCUN bonus sitadel en q_v2 (0 permis ≤ 200 m/36 mois)
et gagnent **+7,1 pts d'A en moyenne** avec la fenêtre du mandat (400 m / 5 ans) — l'axe A
gagne +6,3 pts en moyenne sur ces parcelles et franchit le seuil A≥60. Les nouveaux MALUS
(bruit, SIS, 50 pas, SUP) jouent dans l'autre sens : **255 chaudes perdues**.

**Proposition de calibration (SIMULÉE en lecture seule, PAS appliquée)** — réduire le poids
du bonus « dynamique constructive » devenu beaucoup plus large :
| Poids sitadel | Chaudes simulées |
|---|---|
| ×1,0 (tel que calculé) | 5 455 |
| ×0,5 | 2 987 |
| **×0,25** | **1 362** (proche des 1 083 historiques) |
Décision Vic : adopter q_v3 tel quel (lecture large), ou re-matricer avec poids sitadel
réduit (opération SQL rapide, sans ré-évaluation), ou ajuster `saturation_pc`/le poids
opportunity et relancer.

**Top 10 des chaudes perdues (les malus font leur travail)** — corridor RN1/littoral de
Saint-Paul en tête, cumul bruit cat 1-2 + 50 pas + sols pollués :

| Parcelle | Commune | Q | Nouveaux flags |
|---|---|---|---|
| 97415000DE1161 | Saint-Paul | 69→47 | bruit_route, cinquante_pas |
| 97415000BP0879 | Saint-Paul | 73→51 | bruit_route, cinquante_pas |
| 97415000BP0925 | Saint-Paul | 75→53 | bruit_route, cinquante_pas |
| 97415000DE0900 | Saint-Paul | 69→47 | bruit_route, cinquante_pas |
| 97415000BO0005 | Saint-Paul | 75→54 | bruit_route, cinquante_pas |
| 97415000BP0374 | Saint-Paul | 69→49 | bruit_route, cinquante_pas, sol_pollue |
| 97408000AP0961 | La Possession | 69→49 | bruit_route |
| 97415000BP0372 | Saint-Paul | 69→49 | bruit_route, cinquante_pas, sol_pollue |
| 97415000BP0365 | Saint-Paul | 69→50 | bruit_route, cinquante_pas, sol_pollue |
| 97415000BP0794 | Saint-Paul | 70→53 | bruit_route, cinquante_pas |

## Phase 2 — Impact Brûlantes 🔥

La vue `v_parcelles_brulantes` (dynamique, liée à q_v2 + seuil 34) donne **93 Brûlantes** ;
avec la population de chaudes q_v3_datagap (seuil 34 inchangé) : **89 Brûlantes**.
**Garde-fou [30-120] : RESPECTÉ dans les deux cas** → aucun changement de seuil proposé.
(À titre indicatif : le top décile V des 5 455 chaudes q_v3 tombe à 4 — la masse des
nouvelles chaudes est à V faible ; si q_v3 était adopté TEL QUEL, le seuil resterait
pertinent à 34, la méthode top-décile ne s'appliquant que si le garde-fou est quitté.)

---
*Fin du mandat data-gap — 11 lots traités (8 FAIT, 1 partiel, 2 BLOQUÉS documentés),
zéro régression tests (629 verts, 6 échecs préexistants identiques à main),
Score V intouché, `q_v2` intouché. AUCUN MERGE — validation et merge par Vic.*
