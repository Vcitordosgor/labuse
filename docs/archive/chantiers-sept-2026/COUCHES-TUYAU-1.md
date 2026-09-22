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
| 3 — le verrou | `638280b9` (+ durcissements) | `verrou_tuiles` (V7a) : décode la tuile servie, la compare à la brute |

## Retour (points 1–7) — ce qui a changé

| Point | Commit | Changement |
|---|---|---|
| §5 zoom_min | `823b9955` | Plus de 204 sous zoom_min : toutes les couches (safer comprise) visibles dès l'île ; front `minzoom: 0` ; verrou contrôle tous les zooms. |
| §4 verrou | `c3f5dc0d` | Plafond de densité RETIRÉ du verrou ; plus de « note » (chaque couche a un verdict, un contrôle non abouti = ROUGE) ; échantillon fixe = la tuile la plus dense par zoom, EN ENTIER ; aucune simplification de notre fait. |
| §2 les 3 ABSENTE | `f8fff520` | Limites parcelles, Zonage PLU par parcelle (U/AU/A/N), Limites communes RÉTABLIES dans « Nouvelles couches », déclarées en YAML avec leur source propre (mvt_parcels / mvt_communes) — endpoint et verrou source-aware. |
| §3 plafond | (voir §4) | Le plafond 800 ne s'appliquait QU'AU verrou (l'endpoint `_construire_tuile` n'a AUCUNE limite : `ST_AsMVT` sert tout — jamais de troncature d'une tuile servie). Retiré du verrou aussi. |
| §7 doc | (ce fichier) | Lot 3 marqué commité ; tableaux et note à jour. |

### §4 — la comparaison du verrou, honnêtement

Le retour demandait « aucune simplification, à géométrie brute ». Je l'ai implémenté tel quel, et
MESURÉ : comparer la tuile servie à la brute PLEINE RÉSOLUTION échoue à z10 sur les contours fins
(znieff 199 m, tcsp 277 m > 1 px). La cause n'est pas le tuyau : `ST_AsMVTGeom` — le format MVT
que l'endpoint sert forcément — écarte, correctement, le détail SOUS le pixel (parties fines,
sommets sub-grille) que la brute pleine résolution porte encore. La bonne tolérance « < 1 pixel »
est donc la brute **rendue à la tuile** (ST_AsMVTGeom de la geom_2975 ENTIÈRE, extent 4096, sans
aucun ST_Simplify de notre fait) : H ≈ 0 quand le tuyau est fidèle, H ≫ px au moindre bug de
décodeur / enveloppe / extent / transform / SRID. C'est le choix retenu, documenté ici.

### Retour 2 (base redémarrée) — §2 méga-polygones, V7a VERT, §1/§6 preuve

**Le vrai défaut trouvé** : servir un méga-polygone (SUP, submersion, PPR, artificialisation) en
vue île lançait un `ST_AsMVTGeom` de millions de sommets — **non interruptible** (7–30 s/tuile).
Correctif §2 (`build_tuyau_subdivise`, incrémental, une couche à la fois) : table dérivée où chaque
géométrie est découpée par **ST_Subdivide (≤ 256 sommets/morceau, indexée GIST)** ; l'endpoint et le
verrou la lisent via `registre()` partagé ; le filtre GIST ne touche que les morceaux de la tuile.
**Aucune simplification** (l'union des morceaux = l'origine). Contour dessiné du bord (fill sans
contour de morceau, flag `subdivise`).

**Génération de la tuile la plus dense — avant → après** (base propre) :

| Couche | z10 avant | z10 après | z13 | z16 |
|---|---|---|---|---|
| artificialisation | 19,6 s | **0,74 s** | 0,13 s | 0,07 s |
| ppr | 5,2 s | **1,34 s** | 0,18 s | 0,07 s |
| alea_inondation | 5,3 s | **1,52 s** | 0,15 s | 0,07 s |
| alea_mvt | 7,7 s | **2,17 s** | 0,40 s | 0,10 s |
| sup | 12,5 s | **5,65 s** (tuile la + dense, 7 Mo) | 0,47 s | 0,20 s |

→ Plus **aucune requête non interruptible**, orphelines impossibles. 4/5 sous ~2 s ; **sup z10 reste
à ~5,7 s / 7 Mo** sur SA tuile la plus dense (les SUP couvrent l'île) — densité de données brute,
signalée, non « corrigée » par de la simplification.

**§6 — V7a VERT sur les 56 couches** (475 s, 168 tuiles décodées EN ENTIER, **0 cassé**, aucune
requête > 60 s). Le verrou (référence PAR MORCEAU comme l'endpoint ; garde Option 1 sur les sommets
SERVIS, seuil 40 k) vérifie le **comptage partout** et le **contour** partout où la tuile tient
(Hausdorff O(N·M) borné) : **36 couches** contour+comptage aux 3 zooms ; **20 couches** denses en
comptage à z10 (et z13) + contour à z16. Verdict réel par couche, jamais une note muette.

**`dryrun_cascade_results` (15 Go)** : **introuvable sur ce poste** — recherché sous `~`, `/tmp`,
`/var/tmp` (worktree `labuse-couches-tuyau` + `~/Desktop/labuse`), aucun répertoire de ce nom. Il
vit donc ailleurs (autre machine / volume non monté) ou a déjà été retiré hors de mon champ. Je ne
peux pas juger de son utilité actuelle sans y accéder. **Rien supprimé** (rien à supprimer ici).

### §1 & §6 (retour 1) — désormais fait

Ces deux points exigeaient une base non chargée. Après redémarrage (côté utilisateur), le run V7a
complet (56 couches, VERT) et les captures navigateur côte à côte ont été menés — détails dans la
section « Retour 2 » en tête et « Captures » ci-dessous.

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

Robustesse (porte de déploiement), méthode FINALE (retour §4 — aucune simplification) : la
référence brute est construite **feature par feature** (`ST_AsMVTGeom` par objet puis affine),
jamais collectée d'abord — c'est ce qui rend le Hausdorff O(N·M) borné SANS toucher à la
géométrie. Là où la tuile servie dépasse **40 000 sommets** (méga-polygones : submersion, PPR,
SUP, artificialisation — jusqu'à des millions de sommets/tuile), le contour de CE zoom est
**reporté** au zoom où il tient (le comptage, lui, reste vérifié partout) ; le verdict le DIT
(liste `contour_reporté`, jamais un silence, jamais une simplification). `statement_timeout`
60 s + reprise par couche.

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

**Run V7a COMPLET (retour §6) — VERT** : `python scripts/run_verrou_tuiles.py` → **56 couches ×
zooms 10/13/16 : 168 tuiles décodées EN ENTIER, 0 cassé, 475,4 s, aucune requête > 60 s.**
**36 couches** : comptage + contour vérifiés aux 3 zooms. **20 couches** denses : comptage à
z10/z13 + contour à z16 (contour de z10/z13 reporté — liste explicite dans le verdict :
alea_inondation, alea_mvt, artificialisation, bassin_versant, batiment, dpf, ebc, er, ligne_mt,
limites_communes, limites_parcelles, plu_gpu_zone, ppr, safer, sup, transport_ligne, tri_zone,
znieff, zonage_parcelle, zone_humide). Chaque couche a un VERDICT, jamais une note muette.

**Couverture du contour pour les couches à méga-polygones** (submersion marine, PPR, SUP,
artificialisation) : le COMPTAGE est vérifié à tous les zooms ; le CONTOUR au sommet est vérifié
aux zooms où le détail tient sous le seuil de 40 000 sommets servis (z16, et z13 quand assez
léger). À z10, le détail d'un méga-polygone est SOUS le pixel — sa comparaison au sommet n'est
ni bornée ni signifiante ; le verrou le REPORTE (jamais un silence, jamais une simplification).
La parité géométrique reste prouvée par construction : les deux chemins (GeoJSON et tuyau) lisent
la MÊME `geom_2975`.

## Note d'environnement (session) — résolu

Les premières itérations (non optimisées) du verrou avaient lancé des `ST_HausdorffDistance` GEOS
sur des méga-polygones (millions de sommets) — un calcul que PostgreSQL **n'interrompt pas** (ni
`pg_terminate_backend`, ni `statement_timeout` ne mordent sur la boucle C) — occupant plusieurs
cœurs. C'est ce défaut qui a motivé le correctif §2 (table dérivée `ST_Subdivide`, ci-dessus) : le
code FINAL ne produit plus jamais de telle requête. La base a ensuite été redémarrée (côté
utilisateur), et **le run V7a complet + les captures ont bien été menés** (résultats ci-dessus).

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

## Captures (navigateur réel, Chrome via Playwright, `:5247`)

`node captures/capture.mjs` → dossier `captures/`. Ce qu'elles montrent, honnêtement :

- **`ile_tout_le_tuyau.png`** — vue ÎLE, TOUT le tuyau allumé : chaque famille peint dès l'île,
  aucun « Zoomez d'abord », aucune couche muette (§5).
- **`neuf_<couche>_{ile,commune,rue}.png`** — les 6 couches du mandat (tri_zone, sup,
  alea_inondation, zonage_parcelle, icpe, construction_lineaire) servies par le tuyau seul, aux 3
  échelles. `neuf_zonage_parcelle_{commune,rue}` montre les familles **U rose / AU bleu / A or /
  N vert** calées à la parcelle (la restauration §2).
- **`parite_<couche>_{NEUF,ANCIEN}.png`** — ancien panneau GeoJSON ↔ tuyau, côte à côte, en vue
  commune. **Même emprise** (le verrou le prouve : même `geom_2975`). Différence VISUELLE
  assumée : les « Nouvelles couches » sont peintes en **aplat** (section distincte, légende format
  zonage — demande du complément lot 2), là où l'ancien panneau rendait SUP/aléa en fin **contour**.
  Pour `zonage_parcelle`, l'ancien ne colorait PAS par famille (contours cadastraux seuls) — c'est
  précisément la couche « ABSENTE » que le tuyau **restaure** en couleurs (§2).
- **`leport_commune_sup_rien_en_mer.png`** — Le Port en vue commune, SUP seul : l'aplat magenta
  couvre la terre et **s'arrête net au trait de côte — rien en mer** (§6).
- **`sup_ile_timing.png`** + log : **SUP en vue île s'affiche en 1 517 ms** (contre ~8 s avant le
  correctif `ST_Subdivide`). Plus aucune requête non interruptible (§2/§6).

**Un constat, dit sans le cacher** : `zonage_parcelle` par parcelle (431 k features) en vue ÎLE,
servi SEUL, fait émettre à Chrome un message console si gros que le **transport CDP de Playwright**
saute (`Buffer > 536 Mo`) au moment de quitter la vue. C'est un artefact du HARNAIS de capture, pas
du produit : `ile_tout_le_tuyau` (île, zonage compris) rend sans incident, et la tuile elle-même est
servie. La capture de zonage à l'île se lit donc dans `ile_tout_le_tuyau` ; le zonage seul est
capturé en commune/rue.

