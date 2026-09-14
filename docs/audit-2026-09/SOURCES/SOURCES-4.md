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

### CoSIA — toutes les classes par parcelle → **SEUIL (mesuré, décision Vic)**
Aujourd'hui seule la classe **Bâtiment** est ingérée (`p_model_bati_cosia` par parcelle +
`spatial_layers/batiment_cosia` géométrie). Ingérer **les 14 autres classes par parcelle** exige le
lot GPKG D974 (absent du worktree — `data/cosia/extract/` vide). **Poids mesuré : le .7z D974 2025 =
494 Mo compressés** (HTTP HEAD, sous le seuil 10 Go). Le coût réel n'est pas le download mais
l'**intersection île entière** : 431 663 parcelles × ~14 classes × des millions de polygones 20 cm →
calcul **> 2 h** (le second seuil du mandat). **Arrêt sur cette source, chiffre écrit — décision Vic**
(run dédié, table `parcel_cosia_couverture` à créer). Non fait ce mandat.

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

### Reprise (point de départ pour la prochaine source) — **BODACC**
Après REI (MAXIMUM), l'ordre imposé reprend à **BODACC** (ventes et cessions de fonds, dépôts de
comptes), puis Fibre Arcep, Loyers DHUP, … **Commande de reprise : « continue SOURCES-4 ».**

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

## Sources arrêtées sur seuil (10 Go / 2 h) — pour décision de Vic
- **CoSIA (toutes classes par parcelle)** : download **494 Mo** compressés (sous 10 Go), mais
  l'intersection île entière (431 663 parcelles × ~14 classes, polygones 20 cm) dépasse **2 h**.
  Bâti déjà servi ; le reste = run dédié `parcel_cosia_couverture`. **Chiffre écrit, Vic tranche.**

## Les deux portes à la clôture
- LOT 1 (commit da97f39b) : verrous **24/24** · suite **3081 passed** · vitest **207** · tsc **0**.
- LOT 2 amorce ICPE (commit b5cd0b23) : verrous **24/24** · suite **3082 passed**.

## Commits (branche `feat/sources-4`, poussée, NON mergée)
- `da97f39b` — LOT 1 : CatNat détail + RNIC enrichi (surfacing raw).
- `b5cd0b23` — LOT 2 amorce : ICPE (rubriques, IED, inspections, catégorie, service, date_maj).

**Rien n'est mergé.**
