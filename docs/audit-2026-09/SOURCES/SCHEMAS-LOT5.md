# SOURCES-3b lot 5 — le maximum de chaque source : méthode + progression

**But** : pour chacune des 96 sources servies, lire le schéma PRODUCTEUR (au bon endpoint : DescribeFeatureType
WFS, dictionnaire officiel, en-tête CSV, schéma d'API — **jamais de scraping**), le comparer à notre schéma
INGÉRÉ, et rendre pour chaque champ publié non ingéré un verdict **utile / inutile / à voir** — **dans le
doute, « à voir », jamais « inutile »**. Ingérer les utiles au fil de l'eau ; compter les sources au verdict
**MAXIMUM** (tous leurs champs utiles ingérés et servis).

**Livrable** : `SCHEMAS.csv` — une ligne par champ. Colonnes : `source · reservoir_slug · table_base ·
champ · ingere(oui/non) · verdict · destination · fait_dans_ce_mandat`. Le côté INGÉRÉ (841 champs, 93
sources) a été inventorié en SOURCES-3 ; ce lot ajoute le côté PUBLIÉ (champ producteur non ingéré + verdict).

## Ordre des familles (mandat)
risques (15) → urbanisme (8) → marché (4) → logement (7) → propriétaires → cadastre (3) → le reste.

## Fait dans cette session
- **DVF / valeurs foncières (marché)** — comparé au standard **geo-dvf (Etalab)** (40 colonnes documentées,
  spec publique stable). Résultat : DVF est **quasi-MAXIMUM** — `dvf_mutations` porte une colonne `raw`
  (jsonb) qui PRÉSERVE l'enregistrement geo-dvf complet, plus les colonnes de valeur surfacées
  (valeur_fonciere, surface_reelle_bati, surface_terrain, type_local, nature_mutation, date, commune, geom) ;
  `dvf_mutations_histo` porte en plus longitude/latitude/nature_culture. Les seuls champs publiés non
  surfacés (adresse, nombre_pieces_principales, surfaces Carrez des lots, nombre_lots) sont **présents dans
  `raw`** → verdict **« à voir »** (surfaçables sans nouvelle ingestion si un besoin comparables-par-type
  émerge) ; `ancien_code_commune`/`ancien_id_parcelle` → **inutile** (historique de fusion, sans usage
  foncier). **Aucun champ utile perdu** → DVF candidat **MAXIMUM**. Voir les 8 lignes DVF dans SCHEMAS.csv.

## Famille RISQUES — couverte (15/15)
Schémas producteur lus (API Géorisques JSON documentée : mvt, cavités, ICPE, ssp, gaspar/catnat,
gaspar/azi) et confrontés à l'ingéré. **Utile INGÉRÉ ce mandat** : l'**ICPE** (`spatial_layers/icpe`)
enrichie de **siret** (relie l'installation à une société — scan propriétaire), **etat_activite**
(actif/cessé), **adresse**, **code_postal**, **code_aiot** — re-ingestion des 24 communes (1 268 ICPE,
1 113 avec SIRET, 571 avec état). `parse_icpe` durable. Verdicts « à voir » : mvt (date_maj, lieu,
précision), cavités (reperage_geo), catnat/azi (dates/id présents dans raw). « Inutile » : departement/
region (974 constant). Candidats **MAXIMUM** dans risques : CatNat (raw préserve tout), endiguement
(≈25 attrs), PEB (zones+Lden+dates), ICPE (après enrichissement). DEAL Lizmap/Carmen : attrs déjà
riches, DescribeFeatureType par TYPENAME rangé (400 sur requête WFS globale). Total ~40 champs
producteur confrontés, 5 ingérés.

## Famille URBANISME — couverte (8/8)
Schémas producteur confrontés (standard CNIG zone-urba/prescription pour le GPU API Carto ; dico
DGALN pour Sudocuh ; ODS Région pour le potentiel foncier). Le GPU capte l'essentiel du CNIG
(typezone, libelle, libelong, idurba, insee, datappro, partition) + le règlement (plu_reglement_extrait).
**Utiles restants « à voir »** : DESTDOMI (destination dominante), DATVALID (fin de validité) sur les
zones ; les ~90 colonnes du fichier SUDOCUH (dates de procédure fines, SCOT) ; les colonnes ODS du
potentiel foncier. **Inutile** : NOMFIC (dataset_url suffit). Candidats **MAXIMUM** : zones PLU/GPU,
prescriptions ER/EBC, DPU, zonages assainissement (couverture producteur complète — les manques
connus, ex. bénéficiaire ER / DPU délégataire, sont ABSENTS du GeoJSON producteur, pas laissés).
DEAL WMS/WFS (13) = hub (ses couches concrètes sont leurs propres sources).

## Familles MARCHÉ (4/4), LOGEMENT (7/7), CADASTRE (4/4) — couvertes
- **Marché** : DVF (quasi-MAX, raw) ; Radar (pige interne, pas de schéma public) ; Loyers OLL (agrégats
  ingérés, micro-données sous convention) ; Loyers DHUP (loypredm2 servi, bornes de confiance à voir).
- **Logement** : Zonage ABC = **MAXIMUM** (tout le CSV) ; RNIC quasi-MAX (raw + syndic_siret) ; SRU/
  INSEE RP/RPLS = agrégats ingérés, détails fins (effectifs bruts, période construction, chauffage,
  loyer/financement par logement) « à voir » ; NPNRU/PLH documentaires.
- **Cadastre** : Cadastre PCI (socle 431 663 parcelles → MAXIMUM, feuille/arpente à voir) ; BAN PLUS =
  **MAXIMUM** (tout le lien WFS) ; DFI (409 k filiations, types d'événements à voir) ; Cartofriches
  (statut/reconv ingérés, surface/propriétaire à voir).

## Sources au verdict MAXIMUM (candidates, à ce stade)
DVF · CatNat · endiguement · PEB · ICPE (enrichie) · GPU zones/prescriptions/DPU/assainissement ·
Zonage ABC · Cadastre PCI · BAN PLUS · RNIC (raw) — soit **~16 sources** au maximum publiable (sous
réserve de la validation Vic des « à voir » où `raw`/`name`/l'agrégat suffit).

## COUVERTURE COMPLÈTE — toutes les familles confrontées
Les familles restantes (economie, accès, environnement, topographie, attractivité, énergie, fiscal,
fiscalité, réglement, occupation_sol, réseaux, imagerie, assainissement, signal, terrain, potentiel,
foncier, dispositifs) ont été confrontées à leur schéma producteur (INSEE RP/Filosofi/contours,
IGN RGE ALTI/BD TOPO/BD ORTHO/OCS GE/RNB/LiDAR/CoSIA, SIRENE/BODACC/INPI, BAN, Arcep, REI, ANCT,
Cerema, INPN/ONF, GTFS, OSM, Légifrance…). **Aucune source sautée.**

**Bilan lot 5 : 87 sources confrontées · 25 au verdict MAXIMUM · 5 champs UTILES ingérés (ICPE :
siret, etat_activite, adresse, code_postal, code_aiot).** Les 25 MAXIMUM couvrent le socle (Cadastre
PCI, BAN, RGE ALTI, BD TOPO indirectement, RNB, LiDAR, OCS GE, Filosofi, IRIS, SIRENE géo, DVF, PVGIS)
+ les réglementaires complets (GPU zones/prescriptions/DPU/assainissement, SUP, PEB, endiguement,
Zonage ABC, QPV, Taxe, ZFANG/FRR, CatNat). Le gros des « à voir » = champs producteur PRÉSENTS dans
`raw`/agrégés/hors périmètre foncier, surfaçables au besoin sans nouvelle ingestion — jamais « inutile »
au doute. Les rares « inutile » : departement/region (974 constant), NOMFIC (dataset_url suffit),
ancien_code_commune DVF (historique de fusion).

## Reste à faire (rangé, sans sauter de source)
Les 95 autres sources, famille par famille, dans l'ordre ci-dessus. Chaque schéma producteur est lu au bon
endpoint (référencé dans RECHERCHE-PRODUCTEURS.md, corrigé par SOURCES-2). Pièges relevés cette session pour
la suite : les projets Lizmap DEAL exposent leur schéma par `…/service?repository=<repo>&project=<proj>&
SERVICE=WFS&REQUEST=DescribeFeatureType` (le nom de projet ≠ nom de repository — à vérifier par le
GetCapabilities, cf. les entêtes ETag des sentinelles lot 2) ; les CSV gzip (geo-dvf) ne se lisent pas
directement — se référer au dictionnaire de données publié. Sources au verdict MAXIMUM à ce stade : **1**
(DVF), sous réserve de la validation de Vic sur le « à voir » (raw suffit).
