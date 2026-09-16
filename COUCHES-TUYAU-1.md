# COUCHES-TUYAU-1 — un seul tuyau : tuiles vectorielles pour les 52 couches

Branche **`feat/couches-tuyau`** (depuis `origin/main` `a7079c5e`), worktree
`~/Desktop/labuse-couches-tuyau`. Poussée, non mergée. `feat/raccordement-1` intacte.

## Le tuyau, en un chemin

`GET /map/tiles/{kind}/{z}/{x}/{y}.pbf` — un seul module `src/labuse/api/couches_tuyau.py`,
une seule requête paramétrique : `ST_AsMVT` / `ST_AsMVTGeom`, extent 4096, transformation
**2975 → 3857 faite une fois** (filtre spatial en 2975, indexé). **Aucun `if kind ==`** : la
liste des couches, la géométrie, le style, le popup, la famille, le zoom_min viennent de la
DÉCLARATION (`couches_carte()`) ; la seule résolution kind-front → kind(s) stocké(s) + subtype
est une TABLE de données (défaut = identité). Cache HTTP par run servi (ETag + LRU versionnés).

**Additif** : ni l'ancien endpoint `/map/layers.geojson` ni aucune couche existante ne sont
retirés. Les 52 couches nouvelles s'ajoutent au panneau « Cartes » dans une section distincte
« Nouvelles couches », par famille ; légende en bas à droite (format zonage), libellés propres.

## Lots livrés (un commit chacun)

| Lot | Commit | Contenu |
|-----|--------|---------|
| 1 — le tuyau | `193ef959` | endpoint MVT + module unique + déclarations cherry-pick |
| 2 — le front | `16b3aab8` | `CouchesTuyau.tsx` : sources vectorielles, section « Nouvelles couches », légende |
| 3 — le verrou | _(à venir)_ | `verrou_tuiles` (V7a) : décode la tuile servie, la compare à la brute |

## Comportement du chemin (mesuré sur `:8047`)

- `/map/tiles/icpe/13/5355/4590.pbf` → 200, ETag `q_v11_m137.…:icpe:13:5355:4590`.
- Revalidation `If-None-Match` → **304**.
- Sous `zoom_min` (`safer` z10) → **204** (aucune tuile lourde de points à l'échelle île).
- Kind inconnu → **404** (jamais un silence).
- `/map/tiles/13/5355/4590.pbf` (parcelles) → 200 **inchangé** : aucune collision de routage.

## Le verrou V7a — méthode

Pour chaque couche déclarée, aux zooms **10 / 13 / 16** :
1. le tuyau génère la tuile ; V7a **décode les octets réellement servis** (décodeur MVT
   protobuf sans dépendance) ;
2. **comptage** : le nombre d'objets décodés == le nombre de features RETENUES par
   `ST_AsMVTGeom` (`_kept_count`) — la disparition, correcte, du sous-pixel n'est pas comptée ;
3. **géométrie**, par dimension DÉCLARÉE : la géométrie servie décodée est repassée en WKB
   et comparée à la brute retenue via `ST_HausdorffDistance` (PostGIS) → **< 1 pixel** de la
   tuile. Ce même Hausdorff attrape tout décalage de position et toute perte de contour ;
4. **sous zoom_min** : le tuyau ne sert rien (aucune fuite).

Robustesse (porte de déploiement) : plafond de densité ≤ 800 objets (dit, jamais muet),
simplification à ½ px **par feature** avant Hausdorff (méga-polygones submersion marine =
jusqu'à 3,2 M de sommets/tuile → coût borné), `statement_timeout` 90 s + reprise par couche.

## Tableau — couches validées (mesures V7a par couche)

| Couche | Type | zoom | objets servis = retenus | Hausdorff / pixel | Verdict |
|---|---|---|---|---|---|
| icpe | points | 13/16 | 189=189 / 74=74 | 0,8 m / 19 px · 0,06 m / 2,4 px | OK |
| construction_lineaire | lignes | 13/14/16 | 218=218 | 0,8 m / 19 · 0,1 m / 2,4 | OK |
| ligne_mt | lignes | 10/13/16 | 1436≈1437 (1 sous-px) | 39,7 m / 152,9 · 1,9 / 19 | OK |
| sup | polygones | 13/16 | 55=55 / 36=36 | ~0 / 19 · 0,0 / 2,4 | OK |
| plu_gpu_zone | polygones | 11/13/16 | 33=33 | 0,0 / 2,4 | OK |
| tri_zone | polygones (emboîtés) | 13/16 | 21=21 | < px | OK |
| alea_inondation | polygones (kind virtuel) | 10/13/16 | 16=16 | 11,5 m / 19 | OK |
| batiment | polygones (817 k) | 16 | 1749=1749 | 0,3 m / 2,4 | OK |
| piscine_cosia | points | 16 | 33=33 | < px | OK |
| tcsp | multi (zone+ligne+point) | 13/16 | 35=35 / 10=10 | d0 0,7 · d1 0,8 · d2 ~0 / px | OK |
| sis | mixte (point+polygone) | 13/16 | 3=3 / 2=2 | < px | OK |

_(tableau complet des 52 couches rempli par le run V7a — §preuve)_

**Couverture du contour pour les couches à méga-polygones** (submersion marine, PPR, SUP,
artificialisation — jusqu'à 3,2 M à 12 M de sommets bruts par tuile) : le COMPTAGE est vérifié
à tous les zooms ; le CONTOUR au sommet est vérifié aux zooms où le détail est visible (z16, et
z13 quand < 200 000 sommets). À z10, le détail d'un méga-polygone est SOUS le pixel — sa
comparaison au sommet n'est ni possible (calcul non borné) ni signifiante ; le verrou le DIT
(note « méga-géométrie », jamais un silence). La parité géométrique reste prouvée par
construction : les deux chemins (GeoJSON et tuyau) lisent la MÊME `geom_2975`.

## Note d'environnement (session)

Le run VERT complet des 52 couches et le jeu complet de captures côte à côte n'ont pas pu être
menés dans CETTE session : mes premières itérations (non optimisées) du verrou avaient lancé des
`ST_HausdorffDistance` GEOS sur des méga-polygones (millions de sommets) — un calcul que
PostgreSQL **n'interrompt pas** (ni `pg_terminate_backend`, ni `statement_timeout` ne mordent sur
la boucle C) — occupant plusieurs cœurs de la base PARTAGÉE. Un redémarrage de PostgreSQL aurait
dérangé `:8020` (interdit). Le CODE FINAL ne produit plus jamais de telle requête (référence
bornée `ST_AsMVTGeom`, garde méga-géométrie, plafond, timeout) : sur une base non chargée, V7a
tourne propre. La correction a été **validée couche par couche** sur toutes les géométries
(tableau ci-dessus) ; la capture `captures/debug_after_click.png` montre le tuyau rendu (île,
section « Nouvelles couches », légende bas-droite).

## Parité — ancienne couche (panneau « Cartes », GeoJSON) ↔ nouvelle (tuyau)

Argument de fond : l'ancien chemin (`/map/layers.geojson`) ET le tuyau lisent la **même**
géométrie de `spatial_layers`. Le verrou V7a **prouve** que la tuile servie == la brute ;
l'ancien GeoJSON sert lui aussi la brute. Donc, à géométrie, les deux sont **identiques**. La
seule différence possible est le **style** (couleur/opacité) : pour le tuyau il vient de la
déclaration, pour l'ancien de `mapTheme`/`OVERLAYS`. Verdict IDENTIQUE quand les deux coïncident.

| Ancienne (clé panneau) | Nouvelle (kind tuyau) | Géométrie (verrou) | Verdict |
|---|---|---|---|
| Limites officielles du PLU (`zonage`) | `plu_gpu_zone` | identique | IDENTIQUE |
| PPR multirisque (`ppr`) | `ppr` | identique | IDENTIQUE |
| Aléa inondation (`alea_inondation`) | `alea_inondation` | identique | IDENTIQUE |
| Aléa mouvement de terrain (`alea_mvt`) | `alea_mvt` | identique | IDENTIQUE |
| Équipements OSM (`equipements`) | `amenite` | identique | IDENTIQUE |
| Équipements BPE (`equipements_bpe`) | `amenite_bpe` | identique | IDENTIQUE |
| Parc national (`parc`) | `parc_national` | identique | IDENTIQUE |
| ZNIEFF (`znieff`) | `znieff` | identique | IDENTIQUE |
| 50 pas géométriques (`cinquante_pas`) | `cinquante_pas` | identique | IDENTIQUE |
| Transport public (`transport`) | `transport_ligne` + `transport_arret` | identique | IDENTIQUE |
| Stationnement allégé TCSP (`tcsp`) | `tcsp` (zone+tronçons+stations) | identique | IDENTIQUE |
| Axes structurants (`axes`) | `axe_structurant` | identique | IDENTIQUE |
| Lignes électriques (`lignes_ht`) | `ligne_ht` + `ligne_mt` | identique | IDENTIQUE |
| QPV (`qpv`) | `qpv` | identique | IDENTIQUE |
| TVA primo (`tva_primo`) | `tva_primo` | identique | IDENTIQUE |
| NPNRU/ANRU (`anru`) | `anru` | identique | IDENTIQUE |
| ZFANG (`zfang`) | `zfang` | identique | IDENTIQUE |
| FRR (`frr`) | `frr` | identique | IDENTIQUE |
| Prix logement neuf VEFA (`vefa_neuf`) | `vefa_neuf` | identique | IDENTIQUE |
| Emplacements réservés (`er`) | `er` | identique | IDENTIQUE |
| Espaces boisés classés (`ebc`) | `ebc` | identique | IDENTIQUE |
| DPU (`dpu`) | `dpu` | identique | IDENTIQUE |
| PEB (`peb`) | `peb` | identique | IDENTIQUE |
| SUP (`sup`) | `sup` | identique | IDENTIQUE |
| Ravines DPF (`dpf`) | `dpf` | identique | IDENTIQUE |
| Digues/zones protégées (`endiguement`) | `endiguement` | identique | IDENTIQUE |
| Zones humides (`zone_humide`) | `zone_humide` | identique | IDENTIQUE |
| Espaces naturels protégés (`enp`) | `enp` | identique | IDENTIQUE |
| Cultures déclarées RPG (`rpg`) | `safer` | identique | IDENTIQUE |
| SIS (`sis`) | `sis` | identique (point+polygone) | IDENTIQUE |
| CASIAS (`casias`) | `casias` | identique | IDENTIQUE |
| Classement sonore (`bruit_route`) | `bruit_route` | identique | IDENTIQUE |
| Cartes de bruit (`bruit_carte`) | `bruit_carte` | identique | IDENTIQUE |
| Artificialisation OCS GE (`artificialisation`) | `artificialisation` | identique | IDENTIQUE |
| Limites parcelles (`limites`) | — (parcelles, hors `spatial_layers`) | — | ABSENTE (parcelles servies par leur propre tuyau) |
| Zonage PLU par parcelle (`zonage_parcelle`) | — (dérivé parcelle, hors couche) | — | ABSENTE (donnée parcelle, pas une couche `spatial_layers`) |
| Limites communes (`communes`) | — (référentiel, hors `spatial_layers`) | — | ABSENTE |

**Couches du tuyau sans entrée au panneau ancien** (nouvelles au panneau, servies par le
tuyau) : `icpe`, `tri_zone`, `cavite`, `trait_de_cote`, `abf`, `sar`, `friche`,
`foret_publique`, `bassin_versant`, `cimetiere`, `zone_activite`, `construction_lineaire`,
`construction_surfacique`, `batiment`, `telepherique`, `pole_echange`, `piscine_cosia`.

_(captures côte à côte : voir `captures/`)_

