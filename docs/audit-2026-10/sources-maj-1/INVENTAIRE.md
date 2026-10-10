# MANDAT-SOURCES-MAJ-1 — Phase 1 : inventaire des sources

**Date** : 2026-10-10 · **Branche** : `fix/sources-maj-1` (worktree `labuse-sources`) · **Base** : locale (`labuse`) · **Portée** : LECTURE SEULE.

> Objectif : pour chaque source servie, dire si elle est à sa **dernière version chez le producteur**, et préparer la liste à injecter. **Rien n'a été injecté. Aucun run, aucune bascule.** La suite (Phase 2) attend la validation de Vic.

---

## 1. Méthode & périmètre

- **Périmètre = 100 lignes** : les **99 sources affichées** (filtre vitrine canonique `sources_catalog.WHERE_AFFICHEES` : `status ∈ {connecte, manuel, live}`, pas `DOUBLON/RETIRÉ/DORMANT`, pas `affichage_desactive`, pas masquée) **+ la 1 source interne** (id 96, Cadastre d'époque Etalab). Le mandat parle de « 100 affichées + interne » ; le compte réel est **99 affichées + 1 interne = 100**.
- Les **29 autres** lignes de `data_sources` (14 `partenariat_requis`, 5 `retiree`, 4 `hub`, 6 `alias`) sont hors périmètre servi → **annexe §5**, non inventoriées ligne à ligne.
- Pour chaque source : **version servie** (lue en base + `source_millesime`), **version producteur vérifiée EN LIGNE le 2026-10-10** (URL citée), **état**, **tables touchées** (lecture du connecteur dans `src/labuse/ingestion/`), **impact run** (entre-t-elle dans le résiduel/scoring ?), **durée d'injection** estimée.
- **États** : `à jour` · `en retard` · `flux continu` (API/base vivante, dernière donnée par construction) · `injoignable` · `collecte manuelle`.
- **Réseau** vérifié au départ (IGN `data.geopf.fr`, `files.data.gouv.fr`, `georisques.gouv.fr` répondent). Garde-fou 974 respecté.

---

## 2. Synthèse — l'essentiel pour décider

### 2.1 Décompte des états (100 sources)

| État | Nombre | Dont impact run |
|---|---|---|
| à jour | 54 | 6 |
| flux continu (vivant) | 29 | 6 |
| en retard | 13 | 4 |
| injoignable | 1 | 0 |
| collecte manuelle | 3 | 0 |

*(Le détail par source est aux §4.1–4.8. « impact run » = la table est lue par `faisabilite/`, `residuel.py`, `builder.py` ou le scoring `p_model`/`score_v`.)*

### 2.2 Les 13 sources EN RETARD (le cœur du mandat)

| id | source | servi → producteur | impact run | injectable sans toucher `parcels` ? | reco |
|---|---|---|---|---|---|
| **96** | **Cadastre d'époque / PCI Etalab** | **2026-06 → 2026-09** (3 mois) | **OUI** (géométrie/contenance `parcels`) | **NON — modifie `parcels`** | ⛔ **hors mandat** (garde-fou « `parcels` géométries jamais modifiées » + « aucun run »). Escalade séparée. |
| **28** | Cerema/GéoLittoral érosion côtière | 2018 → MAJ 2026 | **OUI** (cascade `trait_de_cote`, recul) | oui (`spatial_layers`) | ✅ candidat injection |
| **46** | Classement sonore ITT (Cerema) | arrêtés déc-2023 → **26/12/2024** | **OUI** (cascade `bruit_route`) | oui (`spatial_layers`) | ✅ candidat injection |
| **16** | SITADEL (SDES) | données juil-2026 → **août 2026** (MAJ 29/09) | **OUI** (scoring Sitadel) | oui (`sitadel_permits`) | ✅ candidat injection |
| **10** | RPG agricole (IGN proxy) | campagne 2024 → **2025 (R04)** | **OUI** (cascade `safer`) | oui (`spatial_layers`, WFS LATEST) | ✅ candidat injection |
| 86 | SIRENE établissements géoloc | août-2026 → **sept-2026** | non | oui (`sirene_etablissements`) | ✅ candidat (sans run) |
| 102 | Conso d'espaces NAF (Cerema) | 2021-2024 → **2021-2025** | non | oui (`commune_conso_enaf`) | ✅ candidat (sans run) |
| 100 | RNIC copropriétés (Anah) | snapshot annuel → **quotidien** | non | oui (`rnic_coproprietes`) | ✅ candidat (sans run) |
| 126 | Fibre Arcep (Ma connexion internet) | 2026_T1 → **2026_T2** | non | oui (`arcep_immeubles`) | ✅ candidat (sans run) |
| 74 | Transport GTFS (PAN, 7 réseaux) | ≤2026-08-17 → jusqu'à **2026-09-20** | non (indirect aménités) | oui (`spatial_layers` transport) | ✅ candidat (sans run) |
| 69 | BD ORTHO IRC (IGN) | **table vide** → dispo 974 2025-01-01 | non | oui (`ortho_tiles`/WMS) | 🟡 activation optionnelle (fond IRC) |
| 41 | INSEE RP Logement | FD_LOGEMT 2022 → **« Logement 2023 »** | non | oui (`rp_logement_commune`) | 🟡 **nécessite adapter le parseur** (rupture format harmonisé) → pas un simple re-sync |
| 73 | FRR ex-ZRR (Légifrance) | réf. 2024 → arrêté **14/04/2025** | non | — (texte) | ⏭️ **sans objet 974** (aucune commune réunionnaise dans le périmètre FRR) |

### 2.3 Sources vivantes qui rapatrieraient du plus frais si re-synchronisées

Classées `flux continu` (donc « à jour par construction »), mais un re-sync ramène des révisions récentes. Les **run-impact** parmi elles : BD TOPO bâti (17, WFS LATEST V3.5 2026-09-15), GPU zones/SUP/prescriptions/PEB/assainissement (3, 44, 105, 106, 108, 63), PPR (30), couches cascade DEAL (47, 111, 112, 113, 117, 145), BODACC pour `score_v` (29). Un re-sync de ces couches **ne change les scores servis qu'après un run**.

### 2.4 Injoignable

- **id 35 Cartofriches (Cerema)** — API `apidf(-preprod).cerema.fr` en **HTTP 503 depuis le 02/10/2026**. Pas d'impact run. À réessayer ; on passe.

### 2.5 Le point structurant : le cadastre

Le **cadastre** (id 96 interne + id 1 API Carto, même source DGFiP/Etalab) a **~3 millésimes de retard** (servi 2026-06, producteur **1er sept. 2026**). C'est la seule source **en retard à impact run certain** : la géométrie/contenance des `parcels` (431 663 parcelles 974) est le socle du résiduel et du scoring. **Mais** la mettre à jour :
1. **modifierait les géométries de `parcels`** → interdit par le garde-fou du mandat (« `parcels` : géométries jamais modifiées ») ;
2. **imposerait un run complet** (résiduel + scoring + bascule) → interdit par le mandat (« Aucun run »).

➡️ **Recommandation : cadastre EXCLU de la Phase 2.** À traiter dans une opération dédiée avec run, sous décision de Vic. Voir Phase 3 pour l'analyse du run.

---

## 3. Liste proposée à l'injection (à valider par Vic)

**Ordre du mandat : d'abord sans impact run, puis avec impact run.**

**Groupe A — sans impact run (injection + rebuild tuiles éventuel, PAS de run) :**
- 86 SIRENE géoloc · 102 Conso NAF · 100 RNIC · 126 Arcep fibre · 74 GTFS transport.
- *(optionnel)* 69 BD ORTHO IRC (activation d'un fond, jamais ingéré).
- *(écarté sauf accord)* 41 INSEE RP Logement 2023 — demande d'**adapter le parseur** (format harmonisé 2023), donc pas un simple re-sync ; à traiter hors de ce lot si Vic le veut.

**Groupe B — avec impact run (injection des données ; les scores ne bougeront qu'au prochain run, décidé en Phase 3) :**
- 28 Érosion côtière · 46 Classement sonore · 16 SITADEL · 10 RPG.

**Exclus :**
- ⛔ 96 Cadastre (parcels geom + run requis) — hors mandat.
- ⏭️ 73 FRR (sans objet 974).
- ⏳ 35 Cartofriches (injoignable 503).

> **STOP — en attente de la validation de Vic sur cette liste avant toute injection (Phase 2).**

---

## 4. Inventaire détaillé par famille de producteur

### 4.1 IGN — référentiels téléchargeables / WxS (Géoplateforme)

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 6 | RGE ALTI (altimétrie) | édition non enregistrée (pente 5 m) | RGE ALTI 2.0 D974 **2023-09-05** (seule édition 974) | à jour | `rgealti_mnt_5m`,`mnt_tiles`→`rgealti_pente_5m` | **oui** (pente ≥15/30 %) | ~30 min |
| 8 | Forêts publiques (ONF) | BD TOPO V3 forêt publique (WFS) | BD TOPO **V3.5 D974 2026-09-15** (WFS = dernière) | à jour | `spatial_layers` kind=`foret_publique` | non | <1 min |
| 10 | RPG agricole | proxy RPG.LATEST campagne 2024 | **RPG 4.0 R04 2025-01-01 (campagne 2025)** dispo | **en retard** | `spatial_layers` kind=`safer`/rpg | **oui** (modulation agricole) | <1 min (WFS) |
| 17 | BD TOPO IGN | V3 édition non enregistrée (WFS) | BD TOPO **V3.5 D974 2026-09-15** (WFS LATEST) | à jour | `spatial_layers` (batiment, voirie, water, ravine…) | **oui** (`batiment`→SDP/bâti) | ~2 h |
| 22 | BD CARTO V5 occupation sol | V5 occupation du sol (proxy WFS) | BD CARTO **V5.0 D974 2025-09-15** | à jour | `spatial_layers` kind=`ocs_ge` | non | <1 min |
| 61 | BD ORTHO 20 cm | 974 millésime 2025 | BD ORTHO RVB 0M20 **D974 2025-01-01** | à jour | `ortho_tiles` (5 041) + WMS | non | ~30 min |
| 69 | BD ORTHO IRC | **vide** | IRC 0M20 **D974 2025-01-01 dispo** | **en retard** (jamais ingérée) | aucune (→`ortho_tiles`/WMS IRC) | non | ~30 min si activée |
| 70 | LiDAR HD MNH 50 cm | survol 2023, MNx édités 13/03/2025 | **édition courante = servie** (1er DROM, pas de re-survol 974) | à jour | WMS + dalles → `parcel_bati_revele`/hauteur | **oui** (hauteur→niveaux/SDP) | ~1-2 h |
| 83 | CoSIA (couverture IA) | CoSIA 2025, PVA juil-août 2025 | CoSIA 1.0 **D974 2025-01-01 = dernier** | à jour | `parcel_cosia_couverture`,`batiment_cosia` | **oui** (bâti révélé→déclasse) | ~1 h |
| 144 | OCS GE occupation/artif | 2.0 D974 2017+2022, diff 2025-09-16 | 2.0 D974 2017+2022, DIFF édité 2025-04-10 (pas de 974 +récent) | à jour | `ocsge_sol`,`ocsge_evolution`,`parcel_ocsge` | non | ~30 min |
| 147 | BAN PLUS (adresse↔bâti) | data.gouv maj 27/08/2026 | data.gouv **27/08/2026** = servi | à jour (flux continu) | `ban_plus_liens` (738 540) | non | ~5 min |
| 148 | Communes contours (ADMIN EXPRESS) | seed 24 communes | geo.api.gouv live, 24 communes (AE national 2026-09-23 ; 974 inchangé) | à jour | `communes_referentiel` (24) | non | <1 min |
| 154 | BD NYME lieux-dits | BD TOPO V3 toponymes | BD TOPO **V3.5 D974 2026-09-15** | à jour | `lieux_dits` (1 762) | non | <1 min |
| 155 | SCAN 50 historique 1950 | carte 1950 (WMTS) | produit historique figé (immuable) | à jour | aucune (WMTS) | non | n/a |
| 156 | EduGéo Réunion 1980 | carte 1980 (WMTS) | produit historique figé (immuable) | à jour | aucune (WMTS) | non | n/a |

*Notes : « édition non enregistrée » pour 6/17/154 = métadonnée non figée, pas un retard (WFS BDTOPO_V3 sert toujours la dernière, V3.5 2026-09-15). geoservices.ign.fr redirige vers cartes.gouv.fr ; éditions lues sur les flux Atom `data.geopf.fr/telechargement/resource/<PRODUIT>?zone=D974`.*

### 4.2 IGN — API Carto / Géoportail de l'urbanisme (GPU) / couches geopf WFS

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 1 | Cadastre (API Carto PCI) | PCI Express « latest » | millésime **1er sept. 2026** (PCI DGFiP/Etalab) | flux continu | `parcels` (idu, geom, surface_m2, **contenance_m2**…) via `cadastre_bulk`/`cadastre_ingest` | **oui** (socle surface) | ~30 min–2 h |
| 3 | Urbanisme PLU/GPU (`zone-urba`) | GPU/PLU par commune | flux continu, idurba+date de révision par document | flux continu | `spatial_layers` kind=`plu_gpu_zone` | **oui** (`zone_servie.py`) | ~30 min |
| 25 | INPN/patrinat espaces protégés | passe 05/07/2026 | couches `patrinat_*` servies en continu (WFS) | flux continu | `spatial_layers` kind=`ens` | non | ~5 min |
| 44 | SUP assiettes GPU | assiettes SUP (sync 2026-09-14) | GPU flux continu par commune | flux continu | `spatial_layers` kind=`sup` | **oui** (`gabarit/builder.py`) | ~30 min |
| 63 | GPU zonages d'assainissement | idurba/commune, SIG 4/24 (11/07/2026) | flux continu ; couverture SIG partielle (publication/commune) | flux continu | `spatial_layers` kind=`zonage_assainissement`+`parcel_anc` | **oui** (`viabilisation_build.py`) | ~15 min |
| 76 | ZNIEFF (INPN/MNHN) | INPN maj 29/08/2025 | PatriNat millésime 06/2025 republié continu (couche maj 05/10/2026) | à jour | `spatial_layers` kind=`znieff` | non | ~5 min |
| 105 | GPU emplacements réservés | prescriptions typepsc 05 | GPU flux continu (ER/document communal) | flux continu | `spatial_layers` kind=`plu_gpu_prescription`(05) | **oui** (`db.py` emplacement_reserve) | ~30 min |
| 106 | GPU espaces boisés classés | prescriptions typepsc 01 | GPU flux continu (EBC/document communal) | flux continu | `spatial_layers` kind=`plu_gpu_prescription`(01) | **oui** (`db.py` boise_classe) | ~30 min |
| 107 | GPU droit de préemption urbain | typeinf 04 partiel | GPU flux continu (DPU/commune, partiel) | flux continu | `spatial_layers` kind=`dpu` | non | ~15 min |
| 108 | PEB plans d'exposition au bruit | Roland-Garros B/C/D (GPU) | GPU flux continu ; Pierrefonds non publié (carence producteur) | flux continu | `spatial_layers` kind=`peb` | **oui** (`db.py` zones A/B) | ~15 min |
| 150 | GéoMCE mesures compensatoires | national (sync 2026-09-26) | geopf WFS republié continu | flux continu | `spatial_layers` kind=`mesures_compensatoires` | non | ~5 min |
| 151 | SCOT (GPU) | périmètres SCOT CNIG (2026-09-26) | geopf WFS continu, date dans idurba | flux continu | `spatial_layers` kind=`scot` | non | ~5 min |
| 152 | Zones exclues EnR sauf toiture (APER) | zonages exclus (2026-09-26) | geopf WFS continu (délibération commune, 5 ans) | flux continu | `spatial_layers` kind=`enr_exclue_hors_toiture` | non | ~5 min |
| 153 | Contraintes EnR près habitations (APER) | ENR.PERIMETRE.HABITATION | WMTS geopf servi en continu | flux continu | **aucune** (fond WMTS, seed) | non | n/a |

### 4.3 Géorisques / BRGM (API v1)

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 4 | Géorisques (hub risques) | — (hub) | API v1 courante, v2 additive (token) ; aucune dépréciation v1 | flux continu | aucune (hub) | non | n/a |
| 32 | Sites et sols pollués (SSP) | sync 2026-09-14 (531 `sol_pollue`) | v1 `/ssp` live | flux continu | `spatial_layers` kind=`sol_pollue` | non | ~5-10 min |
| 33 | Cavités souterraines | sync 2026-09-14 (151) | v1 `/cavites` live | flux continu | `spatial_layers` kind=`cavite` | non | ~2-5 min |
| 34 | ICPE | sync 2026-09-14 (1268) | v1 `/installations_classees` live | flux continu | `spatial_layers` kind=`icpe` | non | ~5-10 min |
| 36 | Mouvements de terrain | sync 2026-09-14 (3085) | v1 `/mvt` live | flux continu | `spatial_layers` kind=`mvt` | non | ~5-10 min |
| 97 | CatNat (arrêtés GASPAR) | 974 paginés, 06/09/2026 (405) | v1 `/gaspar/catnat` live ; recoupement national 13/09 = 0 écart | flux continu | `catnat_arretes` | non | ~2-5 min |
| 114 | AZI/TRI inondation (GASPAR) | 07/09/2026 (39) | v1 `/gaspar/azi`+`/tri` live | flux continu | `azi_communes` (+`spatial_layers` tri_zone) | non | ~2-5 min |
| 115 | SIS secteurs info sols | 4 SIS 974, 07/09/2026 | v1 `/ssp` `conclusions_sis` ; projets préfecture figés | flux continu/figé | `spatial_layers` kind=`sol_pollue`(sis) | non | <1-5 min |
| 116 | CASIAS anciens sites industriels | 453 sites, 07/09/2026 (458) | v1 `/ssp` `casias` live | flux continu | `spatial_layers` kind=`sol_pollue`(casias) | non | ~5-10 min |

*Note : v1 reste la version courante (sans jeton). v2 additive, pas de migration obligatoire. Aucune de ces tables n'est lue par le calcul (`georisques_layers.py` : « n'alimente pas le score », flags risque = TODO).*

### 4.4 DEAL Réunion (Lizmap/Carmen) & Cerema géo

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 28 | Cerema/GéoLittoral érosion côtière | millésime 2018 (24 168 entités) | **MAJ 2026** (indicateur national enrichi, page maj 24/08/2026) | **en retard** | `spatial_layers` kind=`trait_de_cote` | **oui** (recul→HARD_EXCLUDE/SOFT_FLAG) | ~5 min |
| 30 | DEAL PPR / aléas | PPR/PPRL approuvés 2011–2026 | WFS Lizmap live, recalcule la dernière date d'approbation | flux continu | `spatial_layers` kind=`ppr_etat`(24)+aléas | **oui** (cœur cascade risques) | ~2-5 min |
| 35 | Cartofriches (Cerema) | 372 friches | API **503 depuis 02/10/2026** | **injoignable** | `spatial_layers` kind=`friche` | non (bonus non branché) | ~15-30 min |
| 40 | NPNRU (DEAL/ANCT) | QP génération 2024 (8) | NPNRU 2014→2032, génération 2024 stable | à jour | `spatial_layers` kind=`anru`(8) | non | <1 min |
| 46 | Classement sonore ITT (Cerema) | arrêtés déc-2023 (1 004) | **arrêtés 26/12/2024** (révision quinquennale) | **en retard** | `spatial_layers` kind=`bruit_route` | **oui** (secteur affecté→isolement) | ~2 min |
| 47 | 50 pas géométriques (DEAL) | cadastre 1877 (163) | WFS live ; 5 corridors « étude fév. 2026 » | flux continu | `spatial_layers` kind=`cinquante_pas` | **oui** (régime foncier) | ~1 min |
| 102 | Conso d'espaces NAF (Cerema) | 2021-2024 (24) | **2021-2025 dispo** (portail artificialisation) | **en retard** | `commune_conso_enaf` | non | ~2 min |
| 111 | Ravines — DPF (DEAL Carmen) | arrêté 2006, 275 tronçons (281) | référence 2006 inchangée (WFS live) | à jour | `spatial_layers` kind=`dpf` | **oui** (marchepied 3,25 m→rédhib) | ~1 min |
| 112 | Zones humides (DEAL Carmen) | 2003/2009/2011/2019 (3 122) | rien de public >2019 (WFS live) | flux continu | `spatial_layers` kind=`zone_humide` | **oui** (flag environnement) | ~2 min |
| 113 | Espaces protégés compl. Ramsar/sites (DEAL) | 13/09/2026 (411) | WFS live par couche | flux continu | `spatial_layers` kind=`ens` | **oui** (règle `ens`) | ~2-3 min |
| 117 | DEAL cartes de bruit stratégiques (CBS) | CBS 2022 (6) | échéance 4 (réf. 2022) en vigueur ; échéance 5 non cartographiée | à jour | `spatial_layers` kind=`bruit_carte`(6) | **oui** (dépassement cascade) | ~2 min |
| 145 | Systèmes d'endiguement (DEAL Lizmap) | EDD Hydrétudes déc. 2024 (117) | WFS live, EDD par zone | flux continu | `spatial_layers` kind=`endiguement` | **oui** (inondation résiduelle) | ~1-2 min |

### 4.5 INSEE

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 20 | BPE INSEE (équipements) | millésime 2025, géo 01/01/2025 | **BPE 2025** republiée 05/10/2026 (actualisation mensuelle) | à jour | `spatial_layers` (équipements) | non | ~5 min |
| 41 | INSEE RP Logement | FD_LOGEMT **2022** (connecteur réel) | **« Logement 2023 » harmonisé, paru 25/06/2026** | **en retard** | `rp_logement_commune` | non | ~10-20 min (⚠ parseur à adapter) |
| 52 | Filosofi (carreaux 200 m) | millésime 2021 | **Filosofi 2021 carroyé** (paru 16/02/2026) = dernier | à jour | `filosofi_carreaux_200m` | non | ~5 min |
| 66 | RP2022 fichier détail Logements (EGOUL) | RP2022 publié 16/10/2025 | **16/10/2025** = dernier | à jour | (cache→`rp_logement_commune`) | non | ~10-20 min |
| 86 | SIRENE établissements géoloc | **août 2026** | **sept. 2026** (dépôt data.gouv 21/09) | **en retard** (1 mois) | `sirene_etablissements` | non | ~10-15 min |
| 133 | RP2022 bases IRIS | RP2022 16/10/2025, géo 01/01/2024 | **16/10/2025** = dernier | à jour | `iris_rp` | non | ~2-5 min |
| 157 | Population légale (geo.api.gouv) | 2023 | populations légales **2023** en vigueur 01/01/2026 = courant | à jour | `population_legale` | non | <1 min |

### 4.6 DGFiP / Etalab cadastre / BAN

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 5 | DVF / valeurs foncières | géo-DVF 2021–2025 + archives 2014-2020 | géo-DVF « latest » 2021→2025 (2025 maj 2026-05-18) | à jour | `dvf_mutations_histo`,`dvf_secteur_medianes`,`dvf_prix_sortie_neuf`,`dvf_mutation_detail` | **oui** (`bilan.py` lit médianes) | ~10-20 min |
| 18 | Base Adresse Nationale | mensuel | `adresses-974` daté **2026-10-09** | flux continu | `adresses`,`adresse_parcelles` | non | ~1-3 min |
| 62 | Sudocuh procédures urbanisme | état 31/12/2024 | dernier état annuel = **31/12/2024** (pas de 2025) | à jour | `sudocuh_procedures` | non | <1 min |
| 71 | DGFiP parcelles personnes morales | panel 2019→2025 | dernière situation = **2025** (pas de 2026) | à jour | `parcelle_personne_morale` | non | ~15-30 min |
| **96** | **Cadastre d'époque / PCI Etalab (INTERNE)** | archives 2017-02 + **2017-07→2026-06** | millésime courant **1er sept. 2026** (3 mois) | **en retard** | `cadastre_historique` ; actualisation vive → `parcels` | **oui** (socle) | ~30 min–2 h |
| 98 | Taxe d'aménagement (DELTA) | 24/24 communes 08/09/2026 | registre DELTA, jeu maj 2026-03-03 ; 2026 clos 01/09 pour 2027 | flux continu | `taxe_amenagement_taux`,`_secteur` | non | <1 min |
| 127 | Taxe foncière REI (DGFiP) | **REI 2025** | **REI 2025** = dernier (2026 ~mai 2027) | à jour | `commune_rei` | non | <1 min |
| 132 | DFI filiation (DGFiP) | situation 19/06/2026 (409 623) | parquet « maj 19 juin 2026 » = servi | à jour | `dfi_filiation` | non | ~5-10 min |

### 4.7 data.gouv / ANCT / DHUP / SDES / ADEME / Arcep

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 16 | SITADEL (SDES) | données **juil-2026** (max 2026-07-31) | **fin août 2026** (MAJ 29/09/2026) | **en retard** | `sitadel_permits` | **oui** (scoring) | ~15-30 min |
| 37 | DPE ADEME (existant) | horizon 2026-07-03 (hebdo) | MAJ **08/10/2026**, hebdo | flux continu | `dpe_records` | non | ~10-30 min |
| 38 | QPV 2024 (ANCT) | génération 2024 | génération **2024** (geojson re-livré 21/01/2026) | à jour | `spatial_layers` kind=`qpv` | non | <1 min |
| 39 | Inventaire SRU (DHUP) | SRU 2025 v2 (18/12/2025) | campagne **2025** (fichier maj 11/08/2026) | à jour | `commune_contexte_sru` | non | <1 min |
| 100 | RNIC copropriétés (Anah) | snapshot annuel (2220) | **MAJ quotidienne** depuis avril 2026 | **en retard** | `rnic_coproprietes` | non | ~20-40 min |
| 101 | RPLS logements sociaux (SDES) | millésime 01/01/2025 | **01/01/2025** (publié 27/11/2025) = dernier | à jour | `rpls_commune` | non | <1 min |
| 109 | Zonage ABC (DHUP) | arrêté 23/06/2026 | arrêté **23/06/2026** (fichier maj 03/07) = dernier | à jour | `commune_zonage_abc` | non | <1 min |
| 126 | Fibre Arcep | **2026_T1** | **2026_T2** (au 30/06, maj 28/09/2026) | **en retard** (1 trim) | `arcep_immeubles` | non | ~5-15 min |
| 128 | ACV/PVD/ORT (DGALN grist) | table vivante (19 communes) | grist vivant (state 28/09/2026) | flux continu | `commune_ort` | non | <1 min |
| 129 | Loyers OLL (ADIL/AGORAH) | OLL 2024 L9740 | dernière campagne **2024** (pas de 2025 974) | à jour | `oll_loyers`,`oll_zonage` | non | ~1-3 min |
| 130 | Loyers DHUP carte des loyers | carte 2025 (JSON embarqué) | édition **2025** = dernière | à jour | aucune (JSON `loyers.py`) | non | n/a |
| 131 | Coût de construction (EPTB) | EPTB 2024 ; choix 2300-2800 €/m² | EPTB **2024** publié (2025 non paru) | à jour | `cout_construction_ref` | non | <1 min |

*Note : 126 Arcep — slug `base_imb/last/` stable, un re-sync ramène T2 automatiquement. 130 : doc_url du seed pointe « 2024 » mais le fichier servi est bien 2025 (cosmétique).*

### 4.8 APIs vivantes & divers

| id | nom | version servie | version producteur (2026-10-10) | état | tables | run | durée |
|----|-----|------|------|---|---|---|---|
| 7 | Parc National (INPN/Région ODS) | millésime 2021 | dataset `pnrun_2021` live (pas de +récent) | à jour | `spatial_layers` | non | <1 min |
| 15 | Potentiel foncier (Région ODS) | — | dataset `potentiel-foncier` live | flux continu | `spatial_layers` | non | <1 min |
| 19 | OpenStreetMap / Overpass | base OSM vivante | endpoint Overpass inchangé | flux continu | `spatial_layers`,`parcel_amenites` | **partiel** (aménités→p_model prix) | ~5-30 min |
| 24 | ABF / Monuments historiques (Mérimée) | liste immeubles MH | dataset Culture vivant (maj hebdo jeudi) | flux continu | `spatial_layers` kind=`abf` | non | <1 min |
| 26 | VRD / assainissement (SPANC) | manuel | pas d'open-data (EPCI) | collecte manuelle | — | non | manuel |
| 29 | BODACC procédures collectives (DILA) | — | DILA flux quotidien (live) | flux continu | `bodacc_depots/sondages/procedures` | **oui** (scoring `score_v`) | ~5-15 min |
| 31 | INPI RNE (dirigeants) | — | endpoint live (401 sans token) | flux continu | `pm_dirigeants`,`pm_dirigeant_gigogne` | non | ~10-30 min |
| 42 | PLH des 5 EPCI | extraction doc CDHH | PDF documentaire, pas d'API | collecte manuelle | (doc) | non | manuel |
| 43 | RTAA DOM (Légifrance) | arrêté 17/04/2009 mod. 11/01/2016 | dernier « modifié par » = **11/01/2016** (aucune modif après) | à jour | (texte) | non | n/a |
| 45 | Recherche d'entreprises (DINUM) | Sirene/RNE courant | endpoint live 200 | flux continu | (enrichissement PM) | non | ~5-30 min |
| 48 | PVGIS (Commission UE) | v5.3, SARAH3 | **v5.3 courante** (sortie 25/09/2024) | à jour | `solar_grid`,`parcel_solar` | faible (bonus faisabilité) | ~30 min–2 h |
| 51 | Parkings OSM (APER) | OSM | Overpass live | flux continu | `spatial_layers` | non | ~5 min |
| 72 | ZFANG (Légifrance/DGOM) | Décret 2026-421 du 29/05/2026 | texte initial, aucune modif = dernier en vigueur | à jour | (texte, overlay) | non | n/a |
| 73 | FRR ex-ZRR (Légifrance) | réf. 2024 | arrêté **14/04/2025** existe | en retard (**sans objet 974**) | (texte) | non | n/a |
| 74 | Transport GTFS (PAN, 7 réseaux) | ≤2026-08-17 | dates +fraîches (Cars Jaunes 2026-09-20…) | **en retard** | `spatial_layers` transport | non (aménités indirect) | ~10-20 min |
| 75 | OSM transport (pôles/téléphérique) | Overpass | live | flux continu | `spatial_layers` | non | ~5 min |
| 84 | Radar (pige d'annonces) | collecte manuelle LABUSE | interne | collecte manuelle | (table interne) | non | manuel |
| 88 | Trafic RN (Région SIR) | comptages/tronçon | dataset ODS live | flux continu | `trafic_rn` | non | <1 min |
| 93 | EDF Réunion lignes HTA (Koumoul) | géom ~02/2020, publié 16/10/2025 | pas de nouveau millésime (géom 2020) | à jour | `spatial_layers` (réseau MT) | non | <1 min |
| 94 | TCSP voies bus (OSM) | Overpass voies bus 974 | live | flux continu | `spatial_layers` tcsp | non | ~5 min |
| 99 | Annuaire administration (DILA) | 24 mairies | DILA live | flux continu | `annuaire_services`,`mairies` | non | <1 min |
| 143 | RNB Référentiel Bâtiments | flux continu, 13/09/2026 | endpoint `alpha` live (pas de v1/v2) | flux continu | `rnb_batiments`,`rnb_rattachement_bdtopo` | non (résiduel bâti=LiDAR) | ~20 min-1 h |

*Note : 19 OSM et 74 GTFS alimentent `parcel_amenites` (distances TCSP/équipements) lu par le modèle de prix `p_model` → impact scoring **indirect**. BODACC (29) est lu par `score_v` (détresse juridique) → impact scoring direct.*

---

## 5. Annexe — sources hors périmètre servi (29)

Non inventoriées ligne à ligne (hors vitrine) :
- **6 alias** (pointent une source servie) : 2 Cadastre Etalab→1, 9 Potentiel foncier→15, 21 SIRENE→86, 65 RGE ALTI 5 m→6, 67 GPU assainissement→63, 119 DVF Région→5.
- **4 hubs** (portails, pas de donnée propre) : 11 Région ODS, 12 PEIGEO, 13 DEAL WMS/WFS, 14 Géoplateforme IGN.
- **5 retirées** : 49 EDF SEI, 50 ODRÉ, 68 Office de l'eau, 87 MOBPRO, 89 BDNB.
- **14 partenariat requis** (pas de donnée servie, convention en attente) : 27 Fichiers fonciers, 95 Réunion Express, 110 ZPPA, 118 SAR, 134 assainissement EPCI, 135 ZAE, 136 ZAC, 137 OPAH/PIG, 138 ORT infra, 139 ENS Département, 140 micro-données OLL, 141 LOVAC, 142 DV3F, 146 hypsométrie littoral.

---

## 6. Prochaine étape

**Phase 1 terminée.** En attente de la **validation de Vic sur la liste du §3** (Groupe A sans run, Groupe B avec run, exclusions). Aucune injection avant accord. Le verdict « faut-il un run ? » est préparé pour la Phase 3 et dépend du Groupe B + cadastre.
