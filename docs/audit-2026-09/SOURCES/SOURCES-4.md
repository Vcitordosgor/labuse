# SOURCES-4 — le maximum de chaque source, sans exception

Branche `feat/sources-4` (depuis `main`, SOURCES-3b + TESTS-1 mergés). Worktree `~/Desktop/labuse-etat`.
Règle Vic : **tout ce qu'un producteur publie, on l'ingère** ; une seule exception, le doublon arbitré
(EDF > BD TOPO lignes, CoSIA/LiDAR > végétation, BPE > équipements) ; les autres exceptions sont
physiques (raster nu, hub, accès restreint, flux live sans schéma).

Ce mandat est vaste (≈85 sources, 70 champs « à voir » restants). Il se livre par lots, une source à la
fois ; ce qui n'est pas atteint garde son rang dans `SCHEMAS.csv` et la session suivante reprend avec
« continue SOURCES-4 ». **Aucun run, aucune bascule, aucun rescoring, aucun merge.** Les trois fichiers
du run servi ne sont jamais commités.

## Étape 0 — les deux portes (ouverture)
- `feat/sources-4` créée depuis `origin/main` (0b24bc51), arbre propre, `.env` présent.
- `labuse circuit verrous` → **24/24 verts** (V4e compris).
- `labuse circuit suite` → **3078 passed, 55 skipped** en 2 min 02.

---

## LOT 1 — surfacer ce qui dort dans `raw` — LIVRÉ

Balayage systématique des 8 tables portant une colonne `raw`
(`bodacc_procedures, catnat_arretes, dpe_records, dvf_mutations, pm_dirigeants,
pm_dirigeant_gigogne, rnic_coproprietes, sitadel_permits`). Verdict par source :

### CatNat — arrêtés de catastrophe naturelle (GASPAR / Géorisques) → **MAXIMUM**
La fiche commune ne servait qu'un **compte** (`catnat_n`). Le détail existait en base (colonnes +
`raw`) sans place à l'écran ni identifiant au registre. Surfacé :

| champ | d'où | avant | après |
|---|---|---|---|
| `type_peril` | colonne | jamais servi (agrégé en compte) | ligne par arrêté |
| `date_debut`, `date_fin`, `date_arrete` | colonnes | idem | dates par arrêté |
| `code_national_catnat` | **raw** | dormant | servi (id national de l'arrêté) |
| `date_publication_jo` | **raw** | dormant | servi (date JO) |

- **Registre** : nouvelle donnée `catnat_arretes_liste` (`liste`, commune, réservoir `catnat_gaspar`,
  passe-plat `fiche_commune.py:risques`), servie par le robinet `fiche_commune_risques` (mono-robinet).
- **Place** : fiche commune › carte **Risques** — 12 arrêtés les plus récents, « et N autres… » via le
  compte total. Backend `src/labuse/api/fiche_commune.py:risques`, front
  `frontend/src/components/contexte/ContextePanel.tsx` (bloc sous « Arrêtés CatNat »).
- **Preuve** (capture `captures-sources4/01-commune-risques-catnat-detail.png`, Saint-Denis) :
  « Arrêtés CatNat **21** · Mouvement de Terrain 2025-02-26 → 2025-03-01 · **INTE2519692A** · Vents
  Cycloniques 2025-02-26 → 2025-02-28 · INTE2508630A · … »
- **Rollout** : le volet contexte est servi depuis `commune_contexte_cache` (job nocturne
  `fiche-commune-cache`). Les **24 communes** ont été recalculées (`rafraichir_contexte_cache`, 260 s,
  0 KO) — ce n'est pas un run/bascule, c'est exactement ce que fait le job de nuit. Le détail est donc
  live sur toute l'île.

### RNIC — copropriétés (ANAH) → **MAXIMUM sur l'open data ingéré**
La fiche ne servait que 9 colonnes. Surfacé (colonne + `raw`, dans le respect de la règle RGPD :
`syndic_siret`/`syndic_nom` uniquement si syndic professionnel — garde d'ingestion `purge_rgpd`) :

| champ | d'où | après |
|---|---|---|
| `syndic_siret` | colonne (déjà en base) | servi — relie la copro à une société (personne morale) |
| `nombre_de_lots_de_stationnement` | **raw** | « N stationnement » |
| `nombre_total_de_lots_a_usage_d_habitation_de_bureaux_ou_de_comm` | **raw** | « N hab./bur./com. » |
| `residence_service` | **raw** | « résidence-service » si oui |
| `syndicat_cooperatif` | **raw** | « syndicat coopératif » si oui |

- **Place** : fiche parcelle › **Copropriété rattachée** (tiroir Propriétaire) + Dossier PDF.
  Backend `app.py:_q_v2_fiche` (SELECT élargi), front `CoproprietesBlock.tsx`, PDF
  `pdf_premium.py` § COPROPRIÉTÉ(S) RATTACHÉE(S). Donnée registre `coproprietes_liste` (inchangée,
  champs enrichis, même réservoir `rnic_anah`).
- **Preuve** (capture `captures-sources4/02-fiche-copropriete-rnic.png`, parcelle 97411000BH0670) :
  « LES JACQUIERS · 267 lots (dont 120 hab.), **117 stationnement**, 120 hab./bur./com. · syndic
  professionnel · VITRY · **SIRET 48086797700013** ».
- **Reste (LOT 2)** : **procédures** (art. 29-1…) et **étiquette énergie DPE copro** sont ABSENTES du
  jeu open data ANAH ingéré — elles exigent un export procédures/DPE-copro dédié. Ligne ajoutée à
  `SCHEMAS.csv` (verdict « à ingérer »).

### Les autres tables à `raw` — arbitrées, pas de surfacing LOT 1
- **INPI RNE** (`pm_dirigeants`) : `raw` porte l'**adresse du dirigeant**, un second rôle, la mention de
  démission. Ce sont des **données personnelles** ; la projection servie (nom, rôle, date) est le choix
  délibéré, conforme à la **licence RNE homologuée**. Verdict **PARTIEL — producteur (licence)**, pas un
  trou. Rien à surfacer sans élargir la licence.
- **DVF** (`dvf_mutations`) : `raw` ne contient que `id_mutation / source / vefa`. L'**adresse**, le
  **nombre de pièces** et les **surfaces Carrez** ne sont **PAS** en base (ni colonne, ni `raw`) — le
  mandat les rangeait dans « dort dans raw », mais la preuve dit le contraire : ils exigent une
  **ré-ingestion** de DVF+ avec capture de colonnes élargie → **LOT 2** (source déjà servie, ingestion
  autorisée pour la compléter). Documenté, non fait ici.
- **BODACC, DPE, SITADEL** : leur `raw` est riche mais correspond à des **schémas complets** listés « à
  ingérer » dans `SCHEMAS.csv` (DPE 230 champs, BODACC annonces, SITADEL détails permis) → **LOT 2**,
  pas un simple surfacing.

### Tests LOT 1
- `tests/test_sources4_lot1.py` : CatNat sert le détail (péril + 3 dates + code national + JO) ; la
  donnée `catnat_arretes_liste` est déclarée au registre et servie par un seul robinet.
- `tests/test_rnic.py::test_surface_champs_raw_stationnement_residence` : l'extraction depuis `raw`
  (même SELECT que `_q_v2_fiche`) tient — si l'ANAH renomme une clé ou la purge RGPD l'efface, ça casse.

---

## LOT 2 — ingérer tout ce qui manque — EN COURS (ICPE, SRU faits ; CoSIA seuil ; Cartofriches déjà MAXIMUM)

### ICPE — installations classées (Géorisques /installations_classees) → **champs ingérés en base**
Sonde de l'API réelle (974) : les champs « à voir » de `SCHEMAS.csv` sont **tous dans la réponse
liste** — aucun appel détail. Ajoutés à `parse_icpe` (`georisques_layers.py`) et ingérés dans
`spatial_layers` (kind `icpe`, `attrs`) :

| champ | contenu | dans attrs |
|---|---|---|
| `rubriques` | nomenclature ICPE : numéro + nature (ce que l'installation FAIT) | liste `{numero, nature}` |
| `ied`, `priorite_nationale` | niveau d'enjeu (directive IED, priorité nationale) | booléens |
| `categorie` | dérivée des drapeaux carrière/éolienne/bovins/porcs/volailles/industrie | texte |
| `service_instructeur` | serviceAIOT (ex. DEAL Réunion) | texte |
| `date_maj` | dernière mise à jour producteur (tronquée à la date) | texte |
| `inspections` | dates des inspections | liste de dates |

- **Ingestion** : `ingest_icpe_commune` (nouvelle, rejouable, ICPE-seule — ne re-touche pas
  sol_pollue/cavités), idempotente (purge kind='icpe' par commune). **Place & temps mesurés** :
  **1 268 ICPE, 24 communes, 8 s**, 0 KO ; total inchangé (source stable).
- **Registre** : réservoir `georisques_icpe` (déjà déclaré, `registre/tables.py` →
  `spatial_layers/icpe`) porte désormais ces attrs. Aucun nouveau chiffre servi live → aucune
  nouvelle donnée.
- **Place / serving** : l'ICPE s'affiche via la **cascade Risques** (réservoir `dryrun_cascade_results`,
  **figé à la bascule**). Le mandat **interdit tout run/bascule/rebuild** — les nouveaux champs sont
  donc **en base (attrs = le raw-équivalent de spatial_layers)** et seront servis dans le détail de la
  cascade **au prochain rebuild** (geste de Vic). C'est exactement le repli prévu par le mandat
  (« s'il n'a aucune place évidente sans rebuild, conservé et disponible »). ICPE n'est ni une couche
  carte togglable (`_MAP_LAYER_KINDS`) ni un popup riche live — le rendre tel serait un chantier
  frontend hors périmètre de cette amorce.
- **Test** : `test_georisques_layers.py::test_parse_icpe_champs_producteur_sources4` (pur, sans réseau).
- **Reste** : la suite du LOT 2 garde son ordre dans `SCHEMAS.csv` (SRU, CoSIA, Cartofriches, BPE,
  Parc national, puis REI, BODACC, …).

### SRU — inventaire des logements sociaux (DHUP) → **effectif brut surfacé**
Sonde du CSV DHUP réel (v2 18/12/2025, `ingest_sru.py`) : le **dénominateur `nb_res_principales`
N'EST PAS publié** (22 colonnes ; seul le TAUX l'est) — non ingéré, non inventé (arbitrage écrit,
ligne PARTIEL ajoutée à `SCHEMAS.csv`). L'**effectif brut `nb_lls`** dormait dans
`commune_contexte_sru.detail` (seul le taux était servi) : surfacé.

- **Ingestion** : `ingest_sru.py` élargi — en plus de `nb_lls`, on garde désormais les rattachements
  SRU publiés jusque-là jetés : `epci_sru`, `uu_sru`, `nom_unite_urbaine`,
  `commune_isolee_l302_5` (art. L.302-5 CCH), `soumise_sru_2025`. Filtre 974 + garde des 24 communes
  intégrés. Re-ingéré : 24 communes (2 carencées, 9 déficitaires, 8 conformes, 5 exemptées).
- **Registre** : nouvelle donnée `lls_inventaire_n` (`logements`, commune, réservoir `sru_dhup`),
  servie par le robinet `fiche_commune_sru`.
- **Place** : fiche commune › carte SRU. Preuve (`captures-sources4/03-commune-sru-nb-lls.png`,
  Saint-Denis) : « taux de logement social (SRU) — **24 758 LLS** ». Servi **live**
  (`_rafraichir_partages`) — aucun cache à recalculer.
- **Test** : `test_sources4_lot1.py::test_lls_inventaire_n_declare_au_registre`. FICHES-DONNEES.md
  régénéré.

### CoSIA — toutes les classes par parcelle → **FAIT (décision Vic : lancé en fin de session)**
Seule la classe **Bâtiment** était ingérée. Vic a tranché : **lancer l'intersection en fin de
session** (calcul unique, non récurrent). Download `.7z` D974 2025 = **494 Mo** ; extrait = 37 tuiles
GPKG, **2,8 Go**. Le calcul n'est PAS > 2 h : l'approche **streaming tuile-par-tuile** (module `ingestion/cosia_couverture.py` : chaque tuile →
staging → **`ST_Subdivide`** (128 sommets) → index GIST → intersection parcelles → agrégation
(idu, classe, m²) cumulée, commit par tuile). Le `ST_Subdivide` est essentiel : sans lui, une tuile
urbaine dense partait sur **> 20 min** (gros polygones forêt/broussaille non découpés) ; avec, ~15-40
s/tuile. **RÉSULTAT (37 tuiles, ~20 min) : 5 273 672 polygones, 1 947 019 couples (idu×classe),
431 657 / 431 663 parcelles (99,999 %), 15 classes.** Cohérence prouvée : la somme des classes d'une
parcelle = sa surface cadastrale au m² près (169 715 = 169 715). Table `parcel_cosia_couverture`
(idu, classe, m²) déclarée au registre (réservoir `cosia`).

### Piscines (CoSIA) → **couche dédiée, 46 599 piscines de La Réunion**
Demande explicite : « toutes les piscines de la Réunion ». `build_cosia_piscines` matérialise CHAQUE
piscine détectée (classe Piscine) en polygone dans `spatial_layers kind='piscine_cosia'`, avec sa
**surface (m²)**, sa **commune** (point sur surface dans les frontières IGN) et la **parcelle** qui la
contient (`attrs.parcelle_idu`). **46 599 piscines, 46 550 taguées commune, 46 219 rattachées parcelle**
(22 s). Top : Saint-Paul 6 940, Le Tampon 4 957, Saint-Denis 4 915, Saint-Pierre 4 686. Servie en
**couche carte + popup riche** (`/map/layers.geojson?kind=piscine_cosia` : surface + parcelle au clic ;
vérifié live). Rattachée à la parcelle → **croisable propriétaire** (piste piscines non déclarées).
Détection IA 20 cm 2025 — les tout petits polygones (< quelques m²) sont du bruit IA, filtrables. Kind
déclaré au registre (réservoir `cosia`, couches). Reste frontend (suite) : le toggle dans le panneau
COUCHES + le style de rendu (chaque couche carte est câblée à la main dans `MapView.tsx`) — l'endpoint
et la donnée sont, eux, servis et croisables dès maintenant.

### Cartofriches — détail complet → **MAXIMUM (déjà atteint)**
Vérification : les **372 friches** (`spatial_layers/friche`) portent DÉJÀ, dans `attrs.detail`, le
**détail 78 champs** du Cerema (état du bâti, taux d'artificialisation, vocation, pollution
BASOL/BASIAS, potentiels PV/renaturation, `source_url`, dates…) — en plus du résumé (surface
`unite_fonciere_surface`, propriétaire `proprio_personne`, source). Rien ne manquait : la ligne
« champs restants » de `SCHEMAS.csv` était périmée → **MAXIMUM**, aucune ingestion nécessaire.

### BPE — équipements INSEE → **MAXIMUM**
Le fichier BPE25 publie **95 colonnes** ; on n'en gardait que 4 (dom/sdom/typequ + nom). `_bpe_attrs`
capture désormais : **année `AN`** (par enregistrement, jamais captée), **adresse**, **code postal**,
**SIRET**, **qualité de géoloc**, et les **caractéristiques sectorielles** non vides (capacité d'accueil
d'une école, nombre de salles d'un cinéma, bornes de recharge, secteur public/privé, spécialité santé,
type de restauration…), en écartant la modalité `_Z` (sans objet pour ce type). Pas de varmod dans le
ZIP → le **libellé de TYPEQU n'est pas dérivable** (le nom de l'établissement `NOMRS` reste le libellé
humain servi « À proximité »). Re-ingéré depuis le ZIP local (`build_bpe(zip_path=…)`, pas de
re-download) : **35 544 équipements, 27 s**. Réservoir `bpe_insee` déjà déclaré ; place = `attrs`
(base) + « À proximité » (nom + domaine + millésime). Test `test_bpe.py`.

### Parc national → **MAXIMUM**
Source réelle = **Région ODS `pnrun_2021`** (pas INPN WFS comme l'indiquait `SCHEMAS.csv`). Le
cœur/adhésion était déjà servi ; on ajoute la **superficie (ha)** et le **décret/arrêté** qui établit
chaque zone (cœur 105 519 ha, décret 2007-296 ; deux aires d'adhésion). Re-ingéré : 3 features. La
couche passe en **popup riche** (`_RICH_POPUP_KINDS`, 3 features — coût nul) → superficie + référence
légale au clic. Test `test_parc_national_popup_riche_sources4`.

### REI — tous les taux d'imposition (DGFiP) → **MAXIMUM**
On ne servait que la TFPB (foncier bâti) + TEOM. Le fichier REI (1 043 colonnes, dictionnaire
`TRACE_REI_2025.xlsx` parsé) publie tous les taux votés : ajoutés à `commune_rei` et re-ingérés
(24 communes) — **TFPNB** (foncier NON bâti : B12/B12VOTE/B32), **CFE** (P12/P12VOTE/P32) et les
**bases nettes communales** (E11 bâti, B11 non bâti, P11 CFE). Exemples : Saint-Louis TFPNB 66,21 %,
base foncier bâti 42,3 M€ ; CFE communale 0 % (les EPCI 974 sont en FPU → CFE portée par l'interco,
ex. 29,03 %). **Servi** : la **TFPNB** (la plus pertinente pour un terrain) entre au bloc fiscalité
(donnée `tfpnb_taux_pct`, robinet `fiche_commune_fiscalite`, commune + EPCI) ; CFE + bases restent en
base (disponibles, non affichées). Test `test_tfpnb_taux_declare_au_registre`. FICHES-DONNEES régénéré.

### BODACC → **LARGEMENT MAXIMUM** (ventes/cessions déjà là ; dépôts de comptes noté)
Vérification : les **ventes et cessions de fonds** sont **déjà ingérées** (533 dans
`bodacc_annonces_owner`, famille `vente_cession`), en plus des procédures collectives (677) et des
radiations (208, Score V). Le seul manque = **dépôts de comptes** (`familleavis='dpc'`), que le
connecteur récupère mais écarte du Score V. Faible valeur foncière + capter le `dpc` sans contaminer
le score exige une table dédiée `bodacc_depots` → ligne « à ingérer » ajoutée (déféré, non fait ici).

### Fibre Arcep — toutes technos + débits → **MAXIMUM**
On ne gardait que le **FttH** (FO) ; l'Arcep publie AUSSI le cuivre/DSL (`CU`), la 4G fixe (`4GF`),
le satellite (`SAT`) et la **classe de débit** (descendant/montant). `ingest_arcep` capture désormais,
par immeuble, les **technos disponibles** (`technos[]`) et le **meilleur débit** descendant/montant
(`_meilleur_debit`, ordre THD1G > THD100 > THD30 > HD3 > HD05 > BHD8 > INEL). Re-ingéré :
**330 051 immeubles, 26 s** (ex. [4GF, CU, FO, SAT] → THD1G sur 207 k immeubles). Les technos hors
FttH restent **déclaratives** (étiquetées, jamais présentées comme fiables au même titre que le FttH
IPE). Place = `arcep_immeubles` (base) ; le FttH reste le signal servi à la viabilisation. Test
`test_arcep_fibre.py`.

### Géorisques — détail des couches (mouvements de terrain, cavités, sols pollués) → **MAXIMUM**
Les parsers `georisques_layers.py` gardaient l'essentiel ; on complète avec les champs producteur
laissés : **mvt** — `date_maj`, `lieu`, `commentaire_lieu`, `precision_date`, `precision_lieu` ;
**cavités** — `reperage_geo` (localisation textuelle) ; **sols pollués** — `activite_principale`
(ce que faisait le site = la nature du risque, ex. « Mise en décharge ») + `adresse_lieudit`. Trois
fonctions de re-ingestion isolées (`ingest_mvt_commune` déjà là, + `ingest_cavites_commune`,
`ingest_sols_pollues_commune`, ne re-touchant que leur couche). Re-ingéré 24 communes : mvt 3 085,
cavités 151, sols pollués 531. Test `test_parse_georisques_champs_producteur_sources4`.

### Reprise (point de départ pour la prochaine source) — **Loyers DHUP (carte)**
Ordre restant : **Loyers DHUP carte** (loypredm2 + intervalles de confiance — source distincte de
l'OLL déjà ingéré), puis DFI, Sudocuh, RP Logement, RPLS, classement sonore, EDF HTA, OSM, AZI/TRI,
Mérimée, Conso NAF, personnes morales, SITADEL, Potentiel foncier, GéoLittoral, ONF, INPN, ZNIEFF,
EGOUL, DILA, puis BD TOPO/BD CARTO/cadastre d'époque ; LOT 3 (5 comparaisons DEAL), LOT 4 (verdict
93 + G2 30j). Beaucoup de lignes « utile » restantes sont des placeholders à VÉRIFIER (souvent déjà
MAXIMUM, comme Cartofriches/BODACC). **Commande de reprise : « continue SOURCES-4 ».**

### Le reste du LOT 2 — rang conservé
`SCHEMAS.csv` liste ~70 champs « à voir »/« à ingérer », ordonnés par utilité (mandat § LOT 2).
Ordre imposé : ICPE → SRU → CoSIA → Cartofriches → BPE → Parc national ; puis REI, BODACC, Fibre
Arcep, Loyers DHUP, DFI, Sudocuh, RP Logement, RPLS ; puis classement sonore, EDF HTA, OSM, AZI/TRI,
mvt/cavités/sols pollués/CASIAS/SIS, Mérimée, Conso NAF, personnes morales, SITADEL, Potentiel foncier,
GéoLittoral, ONF, INPN, ZNIEFF, EGOUL, DILA ; puis BD TOPO (thèmes non-doublons), BD CARTO, cadastre
d'époque. Chaque ingestion : filtre 974 au plus tôt, garde 974, sonde, registre, sentinelle, place ou
`raw`+mention. **Amorce identifiée** : DVF+ (adresse/pièces/Carrez) est le premier candidat naturel
(source déjà servie, colonnes à élargir).

## LOT 3 — cinq comparaisons DEAL — NON COMMENCÉ (rang conservé)
`DescribeFeatureType` sur PPR/aléas, cartes de bruit, ravines DPF, zones humides, Ramsar (Lizmap/Carmen).

## LOT 4 — verdict final + verrou G2 étendu — NON COMMENCÉ (rang conservé)
`SCHEMAS.csv` sans plus aucun « à voir » ; tableau des 93 en deux verdicts ; extension G2 (« une source
servie ne porte aucun champ à voir de plus de 30 jours »).

---

## Champs écartés comme doublons (règle G1)
Aucun nouveau doublon arbitré dans ce lot (LOT 1 ne fait que surfacer des champs déjà en base, sans
nouvelle source). Les arbitrages de doublon (EDF > BD TOPO lignes, CoSIA/LiDAR > végétation, BPE >
équipements) restent à écrire au fil des ingestions BD TOPO/BD CARTO du LOT 2.

## Sources arrêtées sur seuil (10 Go / 2 h)
- **CoSIA** : mesuré à 494 Mo / 2,8 Go extraits ; l'estimation initiale « > 2 h » était pessimiste —
  l'approche streaming tuile-par-tuile ramène à **~25 min**. Vic a autorisé le calcul (unique) ; il a
  été **lancé en fin de session**. Plus un arrêt sur seuil.

## Bilan de session (autonome)
**14 sources traitées** (LOT 1 : CatNat, RNIC ; LOT 2 : ICPE, SRU, Cartofriches, BPE, Parc national,
REI, Fibre Arcep, BODACC, CoSIA + Piscines, Géorisques mvt/cavités/sols pollués, Loyers DHUP vérifié)
+ 1 arrêt-seuil relancé (CoSIA, résolu). `SCHEMAS.csv` « à voir » **72 → 47**. Deux gros acquis
structurels : **CoSIA couverture** (1,95 M couples, 15 classes, toute l'île) et **couche Piscines**
(46 599, croisable propriétaire).

**Reste (multi-session, honnête)** :
- **Lourds** (téléchargements/volumes) : BD TOPO thème par thème, BD CARTO, DPE ADEME 230 champs,
  Sudocuh ~90 colonnes, RP détail (chauffage/taille), cadastre d'époque, GéoLittoral, DVF+ (adresse/
  pièces/Carrez).
- **Gatés/restreints** : RPLS micro (niveau logement, SDES), DINUM recherche-entreprises, certains INPN.
- **28 placeholders « utile »** : sources dont le cœur est ingéré (SIRENE géo, BAN, QPV, RGE ALTI, RNB,
  SUP, endiguement, PEB, GPU DPU/ER/EBC/assainissement, Zonage ABC, Filosofi, Contours IRIS, Taxe
  aménagement, Trafic RN, ZFANG/FRR, OCS GE, LiDAR, RP IRIS, ACV/ORT, PVGIS…). À **vérifier
  champ-par-champ** avant de trancher MAXIMUM (ne PAS relabelliser sans preuve — plusieurs se sont
  révélées déjà-MAX : Cartofriches, BODACC ventes, Loyers DHUP).
- **LOT 3** : 5 comparaisons DEAL (DescribeFeatureType). **LOT 4** : verdict final des 93 + verrou G2 (30 j).

## Les deux portes à la clôture
- LOT 1 (commit da97f39b) : verrous **24/24** · suite **3081 passed** · vitest **207** · tsc **0**.
- LOT 2 amorce ICPE (commit b5cd0b23) : verrous **24/24** · suite **3082 passed**.

## Commits (branche `feat/sources-4`, poussée, NON mergée)
- `da97f39b` — LOT 1 : CatNat détail + RNIC enrichi (surfacing raw).
- `b5cd0b23` — LOT 2 amorce : ICPE (rubriques, IED, inspections, catégorie, service, date_maj).

**Rien n'est mergé.**
