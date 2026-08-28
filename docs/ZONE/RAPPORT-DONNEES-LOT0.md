# ZONE-DONNÉES · LOT 0 — INVENTAIRE ET MESURES (avant code)

## M0 — Inventaire de l'existant (base dev, on ne réingère rien)

| Source | Table | Volume | Servi par l'outil |
|---|---|---|---|
| BPE (INSEE 2025) | `spatial_layers` kind=`amenite_bpe` | 35 546 | oui (équipements) |
| OSM aménités | `spatial_layers` kind=`amenite` | 15 214 | non (dispo) |
| GTFS arrêts | `spatial_layers` kind=`transport_arret` | 9 956 | oui (générateurs de flux) |
| pôles d'échange | `spatial_layers` kind=`pole_echange` | 61 | oui |
| Filosofi carreaux 200 m | `filosofi_carreaux_200m` | 14 773 | oui (population/revenu) |
| DVF mutations | `dvf_mutations_parcelle` | 102 551 | oui (marché) |
| Sitadel permis | `sitadel_permits` | 50 292 | oui (marché/permis) |
| parcelles | `parcels` | 431 663 | oui |
| **SIRENE établissements** | `sirene_etablissements` | **0** | **non (vide → à ingérer)** |
| MOBPRO | `mobpro_commune` | **0** | non (abandonné, cf. LOT 2) |
| PLU calibré | `config/plu_*.yaml` (destinations_autorisees…) | par commune | non (à brancher, LOT 7) |
| zones PLU | `spatial_layers` kind=`plu_gpu_zone` | — | non (LOT 8) |
| QPV | *(aucune table dédiée ; `anru_quartiers` seul)* | — | via SIRENE plg_qp24 |

## M1 — Choix du fichier SIRENE : **candidat (a), INSEE**

Deux candidats comparés sur le 974 :
- **(a) INSEE « Géolocalisation des établissements du répertoire Sirene pour les études statistiques »**
  (parquet, 771 Mo national, mensuel). Porte `siret, x_longitude, y_latitude, qualite_xy` (qualité de
  position **documentée**), `epsg`, `plg_iris` (rattachement IRIS **gratuit** → LOT 4), `plg_qp24` (QPV).
  Ne porte pas le NAF/effectif → jointure à `StockEtablissement` (parquet) sur le SIRET.
- **(b) Etalab « geo-sirene » par département (BAN)** : **DÉPRÉCIÉ** — les anciennes URLs
  `files.data.gouv.fr/geo-sirene/...` renvoient 404, Etalab a basculé sur le fichier INSEE.

**Choix : (a).** Justification : (b) n'existe plus ; (a) porte une variable de qualité **documentée**
(on lit, on ne déduit pas), le rattachement IRIS et QPV, et des coordonnées GPS directes. Traitement
par **DuckDB en lecture parquet distante** (pushdown sur `plg_code_commune LIKE '974%'`) — le 974 se
filtre en ~5 s **sans télécharger le fichier national entier**.

## M2 — Qualité de position sur le 974 (variable `qualite_xy` LUE, doc INSEE)

Légende (doc v8 § 3.1) : 11 = voie sûre + numéro trouvé · 12 = voie sûre, position dans la voie ·
21 = voie probable + numéro · 22 = voie probable, position dans la voie · 33 = voie inconnue, position
dans la commune.

| Position | Codes | N (974 géolocalisés) | % |
|---|---|---|---|
| **Adresse (numéro trouvé)** | 11 + 21 | 376 723 | 90,6 % |
| **Voie** | 12 + 22 | 29 202 | 7,0 % |
| Centroïde commune (imputé) | 33 | 9 716 | 2,3 % |
| **Total** | | 415 641 | |

**Adresse + voie = 97,7 %** (> seuil 80 %) → **on ingère le fichier tel quel**, aucun re-géocodage BAN
nécessaire. On sert la précision que la donnée porte ; les 2,3 % en centroïde-commune sont marqués et
peuvent être exclus des « plus proches ».

## M3 — Projection (le piège majeur, ÉVITÉ)

Doc § 2.3 : La Réunion = **RGR92 / UTM 40 Sud / EPSG 2975** (métropole = Lambert 93). MAIS le fichier
fournit AUSSI `x_longitude` / `y_latitude` **en degrés décimaux (WGS84 = GPS)**. → On ingère
**directement le lon/lat** (`ST_MakePoint(x_longitude, y_latitude), 4326`), **aucune reprojection** :
le piège « établissements dans l'océan » est écarté par construction.

## M5 — Filosofi : millésime et imputation

- 14 773 carreaux = **Filosofi 2021** (dernier carroyage publié — pas en retard, aucun upgrade requis).
- Indicateur d'imputation `i_est_200` : **53,4 % des carreaux imputés** (`i_est_200='1'`, niveau de vie
  winsorisé) contre 46,6 % mesurés. Cohérent avec la note INSEE (~66 % à La Réunion). → le badge
  « ESTIMÉ » du revenu doit être **piloté par `i_est_200` par carreau** (LOT 3), pas par une règle
  générique.

## Réconciliation NAF (addendum LOT 1)

633 codes NAF distincts servis en 974, nomenclature **NAFRev2** (182 631 / 182 632). Confronté à
`naf_nomenclature.py` (rév. 2, 732 sous-classes, SocialGouv) : **1 seul code absent** (`514C`, un unique
établissement encore en NAFRev1). → **`naf_nomenclature.py` COÏNCIDE avec le NAF de SIRENE, il est
GARDÉ** (pas remplacé) ; les synonymes (« notaire », « garage »…) continuent de résoudre. Le code
NAFRev1 orphelin (1 établissement) n'a pas de libellé rév.2 — négligeable, laissé sans libellé.
