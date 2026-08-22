# PAU CoSIA — Phase 2 : ingestion canonique + recalcul (FAIT)

Suite de `PAU_COSIA_MESURE.md` (Phase 1) et `PAU_COSIA_PHASE2_BLOCAGE.md` (source trouvée).
Décision Vic : GO au **jeu médian** (un seul changement à la fois), source CoSIA **canonique**
(jamais `qa_cosia_bati`), déduplication **dans le geste** prouvée par un test.

## Source (canonique, IGN Géoplateforme)
Téléchargée par curl (494 Mio .7z), **MD5 vérifié** `e377864d3b75a45d28c0da11321e28f2`.
CoSIA v1.0 D974 millésime 2025, **VECTEUR GPKG** (37 tuiles, EPSG:2975), classe « Bâtiment »
(1/15) = **445 190 footprints** (identique au dump QA `qa_cosia_bati`, qui en était une copie).
`data/cosia/` ajouté au `.gitignore` (la donnée vit en base, pas dans Git).

## Ce qui a été construit (au standard)
- **`src/labuse/ingestion/cosia.py`** — lit les GPKG en PUR PYTHON (`sqlite3` + strip de l'en-tête
  GeoPackage → WKB ; aucune dépendance GDAL/fiona) et matérialise **`spatial_layers
  kind='batiment_cosia'`** (geom 4326, trigger → geom_2975). Idempotent (purge par kind).
  Commune taguée par point-sur-surface dans les frontières IGN (`communes974.geojson`).
  CLI **`labuse ingest-cosia`**. Résultat : **445 190 polygones, 444 914 tagués commune** (276
  bâtiments de bord hors frontière — négligeable), 24 communes.
- **Catalogue** (`data_sources`) : entrée « CoSIA (couverture du sol IA, IGN) », millésime +
  horizon (2025-01-01) + licence portés ; `seed_sources.py` (registre de référence) ET upsert
  au module (`last_sync_at` posé à l'ingestion).
- **Radar de fraîcheur** (`fraicheur.py`) : source `cosia` ajoutée (SOURCES + DS_NAMES),
  cadence « pluriannuelle », `cadence_norme` volontairement absente (re-survol irrégulier → pas
  d'alerte de retard, comme `ortho_piscine`). `total` du radar : 10 → **11**.
- **`build_pau`** (`rnu.py`) : source bâti = BD TOPO **∪** CoSIA, la seconde **dédupliquée DANS
  LE GESTE** — clause `NOT EXISTS (… ST_Intersects bâti BD TOPO)` : les footprints CoSIA qui
  recouvrent un bâti BD TOPO sont exclus AVANT le clustering, jamais comptés deux fois. Si la
  couche CoSIA est absente/vide, l'union se réduit à BD TOPO (aucune régression). Jeu **médian
  inchangé**.
- **Test** (`tests/test_pau_cosia.py`) : `test_dedup_dans_le_geste` prouve end-to-end que 3 BD
  TOPO + 4 CoSIA (dont 2 doublons) → **5 footprints** entrent le clustering (jamais 7) ;
  `test_sans_cosia_comportement_bd_topo_seul` (non-régression) ; `test_avertissement_pau_reste_affiche`.

## Vérification finale (dev DB, Saint-Philippe 97417)

| mesure | avant (BD TOPO) | après (BD TOPO ∪ CoSIA) | cible Phase 1 |
|--------|----------------:|------------------------:|--------------:|
| noyaux | 35 | **47** | 47 ✅ |
| parcelles dans la PAU | 2 373 | **2 656** | ~2 655 ✅ |
| PAU (ha) | 268 | 350 | 349 ✅ |
| plancher de tier (PAU ∧ ≥ 600 m²) | 947 | **1 146** | 1 145 ✅ |
| **sortants** | — | **0** | 0 ✅ |

+283 parcelles entrent la PAU (0 sortent — monotone, vérifié : baseline 2 373 ⊆ enrichi 2 656).
+199 parcelles au plancher de tier (947 → 1 146). Les écarts ±1 vs Phase 1 = footprints
canoniques (tagués par frontière commune, 3 994 à St-Philippe) vs le proxy QA (3 955, tagués
par parcelle). **Déduplication mesurée : 2 397 footprints CoSIA partagés exclus** (BD TOPO 4 512
+ 1 597 CoSIA nouveaux = source de clustering).

**La PAU reste ESTIMÉ** : `AVERTISSEMENT_PAU` inchangé (« Enveloppe urbanisée estimée par
LABUSE… »), servi par `rnu_block`, testé. La qualité monte (imagerie 2025 vs ortho ~2023), la
nature ne change pas.

**Les tiers ne bougent PAS automatiquement** : `parcel_pau` est recalculée, mais le plancher
n'est appliqué qu'au prochain `labuse score-v2` (jamais rétroactif). Le re-score est un geste
délibéré SÉPARÉ, hors de ce mandat (qui améliore la PAU, pas le classement servi).

## Doublon `p_model_bati_cosia` — MARQUÉ (provenance retrouvée)

`p_model_bati_cosia` (idu, emprise_cosia_m2 — SANS géométrie) a été **construite le 04/08/2026**
(commit `557da08c`, mandat [TRAIN1] pilote CoSIA) : 321 314 parcelles, agrégation à la parcelle
de l'emprise des **mêmes footprints CoSIA 2025**. Le code de construction n'a jamais été versé
au dépôt (seuls le doc `PILOTE_COSIA_RAPPORT.md` et l'effet mesuré l'ont été) → provenance
hors dépôt, exactement le problème signalé.

**Preuve que c'est la MÊME donnée** : re-dérivée depuis `batiment_cosia` (somme des emprises par
parcelle, St-Philippe) = **521 936 m²** vs `p_model_bati_cosia` **521 918 m²** — écart **0,003 %**.

**Décision (marquer, pas remplacer dans ce mandat)** : `batiment_cosia` est désormais la source
GÉOMÉTRIQUE canonique ; `p_model_bati_cosia` en est l'agrégat par parcelle, re-dérivable par
`SELECT idu, sum(ST_Area(ST_Intersection(bati, parcelle)))`. Le remplacement propre (re-dériver
`p_model_bati_cosia` DEPUIS `batiment_cosia`, supprimant la provenance hors dépôt) est un
**follow-up** : il touche la chaîne faisabilité (bati_revele/verdict_servi/constructibilité, 9
consommateurs) et les valeurs bougeraient à la marge → hors du principe « un seul changement à
la fois » de ce mandat PAU. Marqué ici et dans `bati_revele.py` pour l'arbitrage suivant.
