# GEOPF-2 — Les couches candidates : a-t-on déjà l'info ?

**Branche** `audit/geopf-2` (worktree `labuse-geopf`) · **lecture seule** · 2026-09-25.
Aucune écriture dans `src/` ni en base. Référence : `../GEOPF-1/GEOPF-REUNION.csv`.
Preuves comptées sur la base de production (`postgresql://openclaw@localhost:5432/labuse`,
264 tables) — **La Réunion uniquement** : chaque décompte = un décompte Réunion.

> **En tête.** Sur **48 sous-couches** examinées (une ligne par sous-couche, pas par famille) :
> **25 sont déjà là en entier**, **6 en partie**, **17 absentes**.
> La quasi-totalité du bloc A (le « déjà en base » de GEOPF-1) se confirme **sous-couche par
> sous-couche** — y compris tous les espaces protégés (ZNIEFF, biotope, réserves, RAMSAR,
> cœur de Parc, Conservatoire du littoral), que GEOPF-1 croyait absents et qui sont en réalité
> ingérés sous `kind=ens`. Le bloc C (hors Géoplateforme) est **entièrement couvert** sauf le
> PEB de Pierrefonds, **que la DGAC ne publie pas**. Les vrais trous sont dans le bloc B
> (EnR, biodiversité réglementaire, SCOT, toponymes) et quelques sous-couches du bloc A
> (ZAC, pylônes/postes électriques, propriétaires au carreau). **Aucune reco : Vic choisit.**

Détail complet, colonne par colonne, dans **`CANDIDATES.csv`**. Colonnes : `bloc, sous_couche,
deja_chez_labuse, preuve, visible_ou, source_producteur, millesime_licence, couverture_reunion,
effort (S/M/L), metiers`.

> ⚠️ La colonne **métiers** est une association best-effort (promoteur · lotisseur · notaire ·
> architecte · agence · apporteur · installateur solaire) : « la liste de Fable » n'a pas été
> retrouvée dans le dépôt, donc les métiers sont déduits de l'usage de chaque donnée.

---

## Bloc A — familles « déjà en base » (confirmation sous-couche par sous-couche)

| Sous-couche | Déjà ? | Preuve (table · objets Réunion) | Visible où | Effort si manque |
|---|---|---|---|---|
| Espaces protégés — **ZNIEFF I** | ✅ oui | `spatial_layers` kind=znieff `type I` = **134** | couche ZNIEFF | — |
| Espaces protégés — **ZNIEFF II** | ✅ oui | kind=znieff `type II` = **28** | couche ZNIEFF | — |
| Espaces protégés — **arrêtés de biotope** | ✅ oui | kind=ens `apb` = **8** | couche Espaces naturels protégés | — |
| Espaces protégés — **réserves naturelles** | ✅ oui | kind=ens `reserve_naturelle` 152 + RNN 1 + rés. biologique 37 = **190** | couche Espaces naturels protégés | — |
| Espaces protégés — **RAMSAR** | ✅ oui | kind=ens `ramsar` = **1** (Étang St-Paul) | couche Espaces naturels protégés | — |
| Espaces protégés — **cœur de Parc national** | ✅ oui | kind=parc_national `coeur`=1 (+2 aires adhésion) | couche Parc national | — |
| Espaces protégés — **Conservatoire du littoral** | ✅ oui | kind=ens `conservatoire_du_littoral` = **27** | couche Espaces naturels protégés | — |
| **RPG** — terres agricoles | ✅ oui | kind=safer `rpg` = **38 460** (src RPG.LATEST) | couche « Foncier agricole — RPG/SAFER » | — |
| PLU/GPU — **DPU** | ✅ oui | kind=dpu = **202** | couche DPU | — |
| PLU/GPU — **ZAC** | ❌ non | pas de table ; source #136 « en attente (pas d'open data 974 fiable) » | nulle part | **M** |
| PLU/GPU — **sursis à statuer** | ❌ non | pas exposé par info-surf GPU | nulle part | **S** |
| PLU/GPU — **taxe d'aménagement majorée** | ✅ oui | `taxe_amenagement_secteur` 24 taux + 10 465 parcelles | outil Taxe + fiche + Financier | — |
| Réseau élec — **lignes (HT + HTA EDF)** | ✅ oui | kind ligne_ht 48 + ligne_mt **19 480** (90/63 kV, aérien/souterrain) | couches Lignes HT / MT | — |
| Réseau élec — **pylônes** | ❌ non | aucun objet pylône | nulle part | **M** (BD TOPO) |
| Réseau élec — **postes de transformation** | ❌ non | aucun objet poste | nulle part | **M** (BD TOPO) |
| **Zones interdites aux EnR hors toiture (APER)** | ❌ non | pas de couche d'exclusion (≠ parkings_aper) | nulle part | **M** |
| **Cours d'eau et ravines** | ✅ oui | ravine 12 716 + water 6 120 + dpf 281 + bassin_versant 150 | couches ravines/hydro | — |
| **Forêts publiques** | ✅ oui | kind=foret_publique = **65** | couche Forêts publiques | — |
| Carreaux INSEE — **densité** | ✅ oui | `filosofi_carreaux_200m` = **14 773** | fiche commune / Étude de zone | — |
| Carreaux INSEE — **niveau de vie** | ✅ oui | `filosofi…ind_snv` | fiche commune / Étude de zone | — |
| Carreaux INSEE — **âge** | ✅ oui | `filosofi…ind_0_3…65_79` | fiche commune / Étude de zone | — |
| Carreaux INSEE — **propriétaires** | ❌ non | Filosofi ne porte pas le statut propriétaire au carreau | nulle part (au carreau) | **L** |
| **Bornes de limite de propriété** | ❌ non | aucune table de bornage | nulle part | **M** (valeur faible) |
| **Parcelles cadastrales 2008-2013** | 🟡 en partie | `cadastre_historique` = **6 526** (2008→2026) mais ≈ parcelles mères disparues, pas un parcellaire complet | outil Remonter le temps | **M** (millésimes PCI complets) |
| **Zones d'activités** | ✅ oui | kind=zone_activite = **9 020** (activités & services, mixte) | couche Zones d'activité | — |
| **Communes touristiques / stations classées** | ❌ non | pas de flag ; LABUSE a zonage ABC (24) + ORT, pas le label station classée | nulle part | **S** (liste DGE) |

**Bloc A : 17 en entier · 1 en partie · 8 absentes** (sur 26).

---

## Bloc B — « absentes » de GEOPF-1 (vérifier qu'on n'a rien d'équivalent)

| Sous-couche | Déjà ? | Preuve / équivalent LABUSE | Visible où | Effort |
|---|---|---|---|---|
| **Potentiel PV « clé en main »** | 🟡 en partie | LABUSE calcule SON potentiel : `parcel_solar` 431 663 + `solar_grid` 15 680 + `toiture_lidar` ; le cadastre solaire IGN natif non ingéré | outil Prospection solaire + fiche | **M** |
| **Parkings PV (loi APER)** | ✅ oui | `parkings_aper` = **901** (surface, proprio PM, échéance ; 155 déjà équipés) | outil solaire / Étude de zone | — |
| **Contraintes EnR près des habitations** | ❌ non | aucune table (geopf `ENR.PERIMETRE.HABITATION` non ingéré) | nulle part | **S/M** |
| **Mesures compensatoires biodiversité** | ❌ non | aucune table | nulle part | **M** |
| **Zones OFB (avis gestionnaire)** | ❌ non | aucune table | nulle part | **M** |
| **CarHab — habitats naturels Réunion** | ❌ non | aucune table (`parcel_vegetation` = strate LiDAR, ≠ habitats) | nulle part | **M** (GPKG) |
| **Zones humides** | ✅ oui | kind=zone_humide = **3 122** (inventaires 2003→2019) | couche Zones humides | — |
| **Prairies permanentes / z. humides BCAE (PAC)** | ❌ non | aucune table BCAE | nulle part | **M** |
| **SCOT et son périmètre** | ❌ non | pas de table (kind=sar = SAR, ≠ SCOT) | nulle part | **M/L** |
| **Carte des pentes** | ✅ oui | kind=pente = **147 398** + `rgealti_pente_5m` (calc RGE ALTI 5 m) | fiche parcelle / exports / gabarit | — |
| **Atlas des patrimoines** | 🟡 en partie | `abf` 200 (ABF/monuments) + ZPPA ; l'Atlas complet (culturel/naturel) non | couche ABF / monuments | **M** |
| **Lieux-dits et toponymes (recherche)** | 🟡 en partie | adresses BAN + toponymes ZA/ravines en attrs ; pas la BD NYME IGN | recherche (adresses/parcelles/propriétaires) | **M** |
| **Cartes anciennes (ortho 1950 / SCAN 1950 / EduGéo 1980)** | 🟡 en partie | ortho historiques 1950→2023 branchées ; SCAN 50 / EduGéo non | outil Remonter le temps (ortho) | **S** |
| **SCAN 25** | ❌ non | fond = Plan IGN v2 ; SCAN 25 non branché | nulle part | **S** (raster) |
| **Labels tourisme** (stations vertes, Pavillon bleu, Clef verte) | ❌ non | aucune table | nulle part | **S** |
| **Zones interdites aux drones (UAS)** | ❌ non | aucune table | nulle part | **S** (WMS) |

**Bloc B : 3 en entier · 4 en partie · 9 absentes** (sur 16).

---

## Bloc C — hors Géoplateforme (source officielle)

| Sous-couche | Déjà ? | Preuve (objets Réunion) | Source officielle · millésime | Effort |
|---|---|---|---|---|
| **PEB — Roland-Garros (Gillot) / Pierrefonds** | 🟡 en partie | kind=peb = **8** (Gillot zones B/C/D) ; **Pierrefonds non publié par la DGAC** | DGAC via annexes GPU · Roland-Garros B/C/D | impossible (Pierrefonds non publié) |
| **Zone des 50 pas géométriques** | ✅ oui | kind=cinquante_pas = **163** | DEAL Réunion (Lizmap) · cadastre 1877 géoréf. 2012 | — |
| **Recul du trait de côte (Cerema)** | ✅ oui | kind=trait_de_cote = **24 168** | Cerema / GéoLittoral · 2018 | — |
| **Sols pollués — SIS** | ✅ oui | kind=sol_pollue `sis` = **10** (4 SIS 974 = recensement officiel complet) | BRGM/MTE Géorisques infosols · 07/09/2026 | — |
| **Sols pollués — CASIAS** | ✅ oui | `casias` = **458** (453 sites : 435 pts + 18 emprises) | BRGM/MTE Géorisques CASIAS · 07/09/2026 | — |
| **Sols pollués — ICPE** | ✅ oui | kind=icpe = **1 268** | BRGM / Géorisques | — |

**Bloc C : 5 en entier · 1 en partie · 0 absente** (sur 6).

---

## Récapitulatif

| Bloc | En entier | En partie | Absentes | Total |
|---|--:|--:|--:|--:|
| A — déjà en base (confirmé) | 17 | 1 | 8 | 26 |
| B — absentes (vérifiées) | 3 | 4 | 9 | 16 |
| C — hors Géoplateforme | 5 | 1 | 0 | 6 |
| **Total** | **25** | **6** | **17** | **48** |

### Les 17 absentes, groupées
- **PLU/GPU** : ZAC, sursis à statuer *(source connue, non ingérée)*.
- **Réseau électrique** : pylônes, postes de transformation *(BD TOPO à ingérer)*.
- **EnR / solaire** : zones interdites EnR hors toiture (APER), contraintes EnR près habitations,
  labels tourisme, zones drones.
- **Biodiversité réglementaire** : mesures compensatoires, zones OFB, CarHab, prairies BCAE.
- **Urbanisme / statistique** : SCOT, propriétaires au carreau, communes touristiques.
- **Fonds / cosmétique** : SCAN 25, bornes de limite de propriété.

### Les 6 en partie (l'essentiel est là, il manque une brique)
- Parcelles cadastrales 2008-2013 (millésimes partiels), potentiel PV (calc interne ≠ produit IGN),
  Atlas des patrimoines (ABF oui, reste non), toponymes (BAN oui, BD NYME non), cartes anciennes
  (ortho oui, SCAN/EduGéo non), **PEB (Gillot oui, Pierrefonds indisponible côté DGAC)**.

*Ce rapport dresse l'état des lieux ; il ne recommande rien. Vic choisit les couches à ajouter.*
