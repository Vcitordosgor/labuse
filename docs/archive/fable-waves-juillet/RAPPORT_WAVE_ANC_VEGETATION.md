# Rapport — Wave ANC & Végétation

Branche `feat/wave-anc-vegetation` (depuis main = 2d97a85, wave-ortho mergée). Exécuté le 11-12/07/2026.

## LOT A — Assainissement non collectif

### A1. Couche probabiliste — maille INSEE obtenue : l'IRIS

- **Variable** : `EGOUL` (« mode d'évacuation des eaux usées », DOM uniquement — 1=égout,
  2=fosse septique, 3=puisard, 4=à même le sol), fichier détail Logements **RP2022**
  (millésime le plus récent, publié 2026), pondération `IPONDL`, résidences principales.
- **Maille** : **IRIS** (la variable y est diffusée) — 326 IRIS 974 agrégés + repli
  commune (24/24). 148 307 résidences principales 974 dans le fichier.
- **Ingestion** : zip national (~400 Mo) streamé en stdlib (26,3 M lignes filtrées 974),
  cache hors dépôt `data/insee_rp/`. Table `anc_maille_taux`. Contours IRIS : 344
  polygones (WFS Géoplateforme `STATISTICALUNITS.IRIS:contours_iris`) →
  `spatial_layers kind='iris_insee'`.
- **Calage Office de l'eau** (Chronique de l'eau n°149, déc. 2025, données 2023 —
  ~189 000 installations ANC ≈ 46 % des foyers ; seed versionné
  `data/anc/office_eau_chronique_149_2023.csv`, chiffres du texte p. 13) :

  | Commune | Office de l'eau (% foyers ANC) | INSEE EGOUL (% non racc.) |
  |---|---|---|
  | Salazie | 100 | 97,8 |
  | Petite-Île | 100 | 96,7 |
  | La Plaine-des-Palmistes | 100 | 94,7 |
  | Saint-Philippe | 95 | 94,6 |
  | Le Port | 8 | 6,8 |
  | Saint-Denis | 15 | 23,1 |

  Concordance forte (l'écart Saint-Denis s'explique par la méthode OLE « abonnés AEP −
  abonnés AC », approximative et assumée par l'OLE). SISPEA/Hub'Eau écarté : les données
  974 s'arrêtent à 2017 (transfert de compétence aux EPCI), API en décommissionnement.

- **`proba_anc` par parcelle bâtie** (emprise > 20 m²) : taux de la maille (IRIS, repli
  commune) **+15 pts** si la parcelle est à > 100 m de toute zone U (uniquement dans les
  communes au PLU ingéré — pas de sur-estimation ailleurs), plafonné 5-95.
  **278 685 parcelles** renseignées.

### A2. Zonages officiels — tableau de couverture (constat du 11/07/2026)

Mécanisme : couches d'information surfaciques du GPU (`typeinf='19'` CNIG), API Carto
`gpu/info-surf` par commune. Classification des libellés en config
(`anc_vegetation.yaml`) — les zones d'EXTENSION du réseau de Saint-Denis
(court/moyen/long terme) sont classées ANC (non raccordées aujourd'hui), les captages
mal typés 19 (L'Étang-Salé) sont écartés.

| Commune | Source | Détail |
|---|---|---|
| **L'Étang-Salé** | zonage officiel (GPU) | 20 polygones (8 AC + 12 ANC) |
| **Le Port** | zonage officiel (GPU) | 92 polygones (91 collectif + 1 autonome) |
| **Saint-Denis** | zonage officiel (GPU) | 119 polygones (48 « actuel » = AC ; 71 court/moyen/long terme = ANC aujourd'hui) |
| **Saint-Paul** | zonage officiel (GPU) | 27 polygones (18 collectif + 9 semi-collectif) |
| 20 autres communes | proba INSEE seule | Aucun SIG au GPU ni chez les intercos (vérifié : CINOR/CIREST/TCO/CIVIS/CASUD, AGORAH/PEIGEO, data.gouv, donnees.eaureunion.fr). PDF d'enquête publique au mieux : Petite-Île 2022 (CIVIS), Entre-Deux 2015 (CASUD) — notés, passés (pas de digitalisation, mandat). |

`zone_anc`/`source='zonage_officiel'` posés au centroïde ; `proba_anc` conservé partout.
Parcelles couvertes par un zonage officiel : 57 712 (9 909 « anc », 47 803 « collectif »).

### A3. Signal & vue

- **Signal `anc_mutation`** : parcelle bâtie × (zone officielle ANC OU proba ≥ 70) ×
  mutation DVF < 12 mois (fenêtre ancrée sur le dernier millésime DVF — 31/12/2025) :
  **1 905 signaux** (attendu mandat : centaines à ~2 k/an glissant ✓).
- **Vue « Prospection ANC »** : preset `anc-prospection` du moteur de segments —
  filtres (zone_anc OU proba_anc ≥ 70) + mutation < 12 mois + emprise bâtie +
  pente non bâtie ≤ 15° (optionnel décochable) ; commune, source du zonage et tri
  disponibles dans le query builder. **1 508 parcelles** matchées au 11/07.
  Export CSV « à l'occupant » (RGPD : zéro nominatif), publipostage BAN.
- **Mention informative UI** (vérifiée Légifrance 11/07/2026) : le diagnostic ANC joint
  au DDT relève de l'art. L.1331-11-1 CSP ; **le délai d'un an de mise en conformité
  par l'acquéreur relève de l'art. L.271-4 II CCH** (la formulation du mandat attribuait
  le délai au seul CSP — corrigé, les deux articles sont cités et liés). Applicable à
  La Réunion (identité législative, art. 73 C.). Affichée dans la vue (bloc mention +
  liens Légifrance + sourçage INSEE/IGN), jamais de conseil juridique.

### Critères d'acceptation A

```
Médiane proba_anc :            65 au niveau PARCELLE bâtie — cohérent avec les ~46 %
                               des FOYERS de l'Office de l'eau : le parc raccordé se
                               concentre dans le collectif dense (une parcelle
                               dionysienne porte des dizaines de logements), le parc
                               ANC dans les maisons individuelles = une parcelle chacune
Gradient communes (moyenne) :  Petite-Île/Salazie/Plaine-des-Palmistes/Saint-Philippe = 95
                               … Saint-Denis 36, La Possession 37, Le Port 10 ✓
Signal anc_mutation :          1 905 ✓
```

## LOT B — Végétation

### B1. Acquisition IRC + NDVI

- Grille `ortho_tiles` du mandat Ortho réutilisée telle quelle (5 041 tuiles 512 m,
  bâti ∪ parkings). Cache RVB purgé → l'IRC se télécharge dans SON cache
  (`data/ortho_irc`, checkpoint `irc_acquise_at`), couche WMS
  `ORTHOIMAGERY.ORTHOPHOTOS.IRC` à 0,4 m/px (≈ 2 Go — le NDVI n'a pas besoin des 20 cm).
- Pseudo-NDVI = (PIR − R)/(PIR + R), PIR = canal rouge de l'IRC, R = canal vert.
- **Seuil canopée CALIBRÉ : NDVI ≥ 0,3** (config ; défaut mandat 0,5). Le 0,5 suppose un
  NDVI de réflectance vraie — l'IRC servi en JPEG par le WMS compresse la dynamique :
  NDVI médian MESURÉ des pixels hauts (MNH > 3 m) = 0,32 (5 tuiles, 465 k px). À 0,5 on
  ne gardait que 8 % de la canopée réelle ; à 0,3 on en garde 56 % (le reste = toits,
  exclus voulus), l'herbe/canne étant neutralisée par la condition MNH > 3 m.

### B2. Méthode hauteur retenue : **LiDAR HD** (`methode_hauteur='lidar'`, `confiance='haute'`)

**Justification (constat, pas supposition)** : le programme LiDAR HD IGN couvre la
TOTALITÉ du 974 depuis le 25/06/2025 (2 665 dalles MNT/MNS/MNH 50 cm publiées — 1er
DROM couvert, vérifié par requêtes directes sur les API Géoplateforme le 11/07/2026).
Le MNH est streamé par tuile en GeoTIFF float32 via WMS-R à 1 m/px et jamais stocké.
Végétation haute = MNH > 3 m ∧ NDVI ≥ 0,3 calibré (le MNH inclut le sursol bâti : le
NDVI l'écarte). Les fallbacks du mandat (MNS corrélé, texture) ne sont pas nécessaires —
le MNS Corrélé D974 (2017/2023/2025) reste noté pour la dynamique en v1.1.

### B3. Agrégats & branchements

- `parcel_vegetation` : 426 107 parcelles (ndvi_moyen, canopee_pct,
  canopee_limite_pct — bande 3 m, canopee_bati_pct — buffer 8 m
  **V0 omnidirectionnelle ; TODO v1.1 : pondération directionnelle nord/est/ouest,
  hémisphère sud**, bati_voisin_10m).
- Sanity Est/Ouest ✓ : NDVI PONDÉRÉ PAR PIXEL Est (au vent) = 0,213 > Ouest (sous le
  vent) = 0,157. (La moyenne par parcelle, dominée par les micro-parcelles urbaines
  identiques des deux côtés, noyait le gradient — la sanity pondère par surface.)
- Couverture méthode hauteur : lidar = 426 107 (100 %).
- **Branchement solaire** : `parcel_solar.flag_topo_ombrage` inchangé ;
  `flag_ombrage_vegetal = canopee_bati_pct > 30 %` (config) : 17 670 leads PV
  re-flagués. Le preset `pv-residentiel` reçoit le filtre d'exclusion par défaut
  décochable (seed YAML + migration idempotente du preset vivant).
- **Signal `vegetation_haute_limite`** (canopee_limite_pct > 40 %) :
  57 687 (dont 38 976 avec bâti voisin < 10 m) parcelles candidates élagage.

### B4. Vue « Prospection élagage » + validation

- Preset `elagage-limite` : canopée limite ≥ 40 %, bâti voisin < 10 m, confiance
  (haute/moyenne), commune ; tri canopée décroissante ; export « à l'occupant ».
  Mention art. 673 C. civ. (texte vérifié Légifrance — 673 = branches qui avancent,
  671/672 = distances de plantation, on cite bien 673). Positionnement : service au
  propriétaire ou au voisin exposé, aucune fonctionnalité de délation.
- **Validation Vic : 20 vignettes** « végétation haute en limite » dans l'outil de
  validation ortho DERNIÈRE version (quota CÔTÉ SERVEUR, anti-rafale 300 ms,
  e.repeat ignoré, 409 au double-tir) — type `vegetation`, la parcelle est entourée.
  Les seules tuiles RVB nécessaires aux vignettes sont re-téléchargées.
  URL : `labuse api` → http://127.0.0.1:8000/ortho/validation?type=vegetation&profil=vegetation&quota=20

## Décision produit — catalogue Segments packagé (11/07/2026)

L'offre packagée passe à **5 presets ACTIFS** ; tous les autres presets du seed
passent `actif=false`. **Aucune suppression** : les rows presets, les données
(`parcel_anc`, `parcel_vegetation`, signaux), et TOUS les filtres du query builder
restent en base — réactiver = repasser le flag `actif` (admin, `PUT /segments/presets/{slug}`).
Le module Solaire (parkings APER M23, toitures tertiaires M24) n'est **pas** un preset
Segments : il reste actif tel quel, inchangé.

**Correspondance libellés → slugs réels** (les 5 existaient déjà, aucun à créer) :

| Libellé décision | Slug | Statut |
|---|---|---|
| Pergolas & terrasses | `pergolas-terrasses` | actif |
| Paysagistes | `paysagistes` | actif |
| Piscinistes (prospection installation) | `piscinistes-construction` | actif |
| Parc piscine (entretien/rénovation, piscines détectées) | `parc-piscines-entretien` | actif |
| Photovoltaïque résidentiel | `pv-residentiel` | actif |

**Désactivés (15, conservés en base)** : `clotures-portails`, `elagage`,
`elagage-limite`, `artisans-renovation`, `cuisinistes`, `salles-de-bain`,
`couvreurs-etancheite`, `menuiseries-cyclonique`, `termites-charpente`, `anc-travaux`,
`anc-prospection`, `chauffe-eau-solaire`, `clim-pac`, `alarmes-telesurveillance`,
`extensions-surelevations`.

Mécanique : le seed YAML porte désormais `actif: false` sur les 15 (le seed honore le
flag — fresh install correct) ; la base existante est passée par un `UPDATE` idempotent
(flag seulement). La galerie `GET /segments` ne liste que les actifs ; `?inclure_inactifs=true`
donne la vue admin. On réduit l'OFFRE packagée, **pas l'outil** : builder complet + 37
filtres du registry toujours servis, query/export par slug fonctionnent même sur un
preset inactif (les recherches sauvegardées ne cassent pas). E2E : `1a.galerie-5-actifs`
+ `1b.anc-elagage-hors-galerie` + `1e.inactifs-recuperables` verts.

## Attribution & conformité

- UI : © IGN (BD ORTHO IRC, LiDAR HD, contours IRIS), INSEE (RP2022), Géoportail de
  l'urbanisme, Office de l'eau Réunion — dans les mentions des presets et le catalogue
  `data_sources` (5 nouvelles sources).
- RGPD : niveau parcelle, exports « à l'occupant », aucune donnée nominative.
- Réseau utilisé : INSEE, GPU/API Carto, Géoplateforme IGN, eaureunion.fr (via seed
  manuel), rien d'autre.
- Le module ANC qualifie des travaux probables — il ne détecte pas d'installations
  non conformes.

## Dette / TODO v1.1

- `canopee_bati_pct` directionnel (nord/est/ouest, hémisphère sud) — hors mandat, noté.
- MNS Corrélé 2017→2025 pour la dynamique de canopée (croissance/défrichement).
- Zonages officiels des 20 communes : demande directe intercos (CADA) si Vic veut
  l'exhaustif — rien de téléchargeable aujourd'hui.
- NDVI depuis JPEG WMS : approximation assumée (masque, pas mesure radiométrique).
