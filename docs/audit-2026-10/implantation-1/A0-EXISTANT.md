# IMPLANTATION-1 · LOT A0 — Inventaire de l'existant (lecture seule)

Branche `feat/implantation-1`, worktree `~/Desktop/labuse-implant1`, base `main @ a57c640d`
(merge de PLU-CALIBRAGE-9 présent). Aucun code écrit avant ce document (mandat).

Terrain étudié : **L'Étang-Salé, AW 99 + 451 + 624 + 625**, assiette fusionnée, zone **UA**,
collectif logements seuls, stationnement aérien, terrain libéré, un seul scénario.

---

## 0. Verdict A0 : **PAS DE STOP** — l'implantation est faisable

| Question du mandat | Réponse |
|---|---|
| Zone d'implantation du Gabarit sur assiette multi-parcelles : possible tel quel ? | **Oui.** Assiette = `ST_Union(geom_2975)` des 4 parcelles → **un seul polygone** 1 744,2 m². Zone d'implantation (reculs appliqués) = **1 170,2 m²**, enveloppe orientée ≈ **71,6 m × 17,9 m**. |
| Façade sur voie ? | **Oui**, 27,7 m sur l'Avenue Raymond Barre (BD TOPO « Route à 1 chaussée »). Accès véhicule possible sur limite classée voie. |
| Contraintes cartographiées (PPR/ER/EBC/SUP) ? | **Aucune** n'intersecte l'assiette → contrôles correspondants = *Non applicable*. |
| Règles UA validée+citation ? | **7 sur 8** (voir §3). Seul le **barème stationnement** est `propose` → objet du LOT A. |

Une réserve, non bloquante : une arête de **19,5 m** ressort `nonclass` (ni route ni voisin
cadastré ≤ 0,5 m — bord de l'union côté arrière). Le classifieur Gabarit (conçu pour la parcelle
unique) la marque *blocking* ; **le moteur IMPLANTATION-1 n'adopte PAS cette sémantique bloquante** :
il traite toute arête non-voie (side/rear/nonclass) avec le **recul séparatif 3 m** (interprétation
prudente — jamais moins que le minimum séparatif). La réserve est signalée au rapport.

---

## 1. Données réelles & CRS

- **Base** : PostgreSQL + PostGIS, socket `/tmp:5432`, base `labuse` (dev). URL
  `postgresql+psycopg://openclaw@localhost:5432/labuse`. Helper : `labuse.db.session_scope()`.
- **CRS** : stockage **EPSG:4326** (`geom`), métrique **EPSG:2975** (`geom_2975`, RGR92 / UTM 40 S,
  La Réunion) — *toute* mesure se fait en 2975 (`labuse/geo.py:5-10`). Le moteur travaille
  directement en 2975.
- **Table `parcels`** (`models.py:65-92`) : `idu` (14 car. = INSEE5 + `000` + section + n° 4 car.),
  `geom`, `geom_2975`, `surface_m2 = ST_Area(geom_2975)`, `contenance_m2` (cadastre, préférée).

| Parcelle | IDU | id | Contenance | Aire dessin 2975 |
|---|---|---|---|---|
| AW 99  | `97404000AW0099` | 89510 | 501 m² | 504,3 m² |
| AW 451 | `97404000AW0451` | 89509 | 586 m² | 582,7 m² |
| AW 624 | `97404000AW0624` | 89563 | 274 m² | 273,0 m² |
| AW 625 | `97404000AW0625` | 89717 | 385 m² | 384,2 m² |
| **Assiette fusionnée** | `ST_Union` | — | **1 746 m²** | **1 744,2 m²** |

La contenance cadastrale (1 746 m²) fait foi pour les surfaces servies (cf. CONTENANCE-1) ;
la géométrie du dessin (1 744,2 m²) sert aux formes. Écart 0,1 %.

## 2. Classification des limites (`gabarit/limites.py`)

`classify_parcel_limits(session, parcel_id, *, sub_geom_wkt=...)` — accepte une géométrie WKT
quelconque (ici l'assiette fusionnée) et classe chaque arête du contour (2975), route d'abord :

- **voie** si un axe BD TOPO carrossable passe à ≤ largeur/2 + 4 m (constantes `ROAD_EXTRA_M=4`,
  `DEFAULT_WIDTH_M=4`) ; **side/rear** si voisin cadastré ≤ 0,5 m ; **nonclass** sinon.

Résultat sur l'assiette (périmètre 196,4 m) : **voie 27,7 m** (source `bdtopo`, sud), rear 146,3 m,
side 2,9 m, nonclass 19,5 m. `has_voie=True`. Azimut de la façade voie ≈ 52° (grand axe NE-SW).

Le moteur **réutilise ce classifieur** pour connaître les arêtes voie, puis construit lui-même la
zone d'implantation en shapely/2975 (buffer + difference), de façon déterministe et testable.

## 3. Règles de zone UA — `config/plu_destinations/97404_l_etang_sale.yaml`

Lues par `faisabilite/zonage.py` (`ZoneRules`, gate `_val` : une valeur n'entre dans le calcul que
si `statut == "valide"`). Document : `97404_reglement_20250917.pdf`, millésime 2025-09-17, md5
`e6f47a869dbe752eea7113e3bfb76b7a`.

| Règle | Valeur | Article · page | Statut | Validée+citation ? |
|---|---|---|---|---|
| Hauteur égout | 12,0 m | UA 2.5.2 · p. 19 | `valide` | ✅ |
| Hauteur faîtage | 15,0 m | UA 2.5.2 · p. 19 | `valide` | ✅ |
| Emprise au sol (CES) | 70 % | UA 2.4 · p. 18 | `valide` | ✅ |
| Recul voie | 4,0 m | UA 2.1 · p. 17 | `valide` | ✅ |
| Recul séparatives | 3,0 m | UA 2.2 · p. 17 | `valide` | ✅ |
| Perméabilité (pleine terre) | 30 % | UA 2.6 · p. 21 | `valide` | ✅ |
| Mixité sociale | seuil 1 000 m² SDP · quota 20 % | UA 1.3 (1) · p. 17 | `valide` | ✅ |
| **Stationnement** | barème par typologie (non chiffré en scalaire) | UA 2.7.3 · p. 22 | **`propose`** | ❌ → **LOT A** |

Citation stationnement (verbatim, p. 22) : *« Logement individuel Par logement 2 / Logement
collectif 1 et 2 pièces 1 / 3 et 4 pièces 1,5 / 5 pièces et plus 2 »*.
Le schéma actuel ne porte qu'un scalaire `par_logement.places` → le barème par typologie ne rentre
pas dans cette feuille : **le LOT A ajoute une feuille structurée dédiée** (cf. RAPPORT, LOT A).

Il n'y a **pas** de contrôle d'espaces verts distinct de la pleine terre dans le règlement UA
(la maquette montre « espaces verts 20 % » comme exemple de rendu, non validé) → ce contrôle
restera *Non effectué* faute de règle validée. Seule la perméabilité 30 % est validée.

## 4. Composants géométriques réutilisables

| Besoin | Réutilisé | Référence |
|---|---|---|
| Fusion multi-parcelles | `ST_Union(geom_2975)` (patron `assemblage.py:129`) | SQL |
| Classification voie/séparative | `gabarit/limites.py:classify_parcel_limits` (via `sub_geom_wkt`) | code |
| Reculs / zone = buffer + difference | patron `gabarit/engine.py:80-96` (shapely) | code |
| OBB (longueur×largeur) | `shapely.minimum_rotated_rectangle` ; `limites.obb_dims` | code |
| CRS 4326↔2975 | `gabarit/_geom.py` (`to_metric`/`to_wgs`), `geo.py` | code |
| Profil LiDAR / pente | `faisabilite/profil_altimetrique.profil_parcelle` (RGE ALTI 5 m, WMS IGN) ; hauteur bâti `faisabilite/hauteur_lidar` | code (dépendant réseau) |
| Rendu | `gabarit/plan_svg.gabarit_svg` (SVG) ; **plan.png rendu en matplotlib 3.11.1** (cairosvg absent) | code |

**Terrain traité à plat** dans le moteur (le relief n'entre pas dans le volume bâti), cohérent avec
la note E-C1 du Gabarit (`contract.py:165`). Le LiDAR n'est pas requis pour la géométrie d'implantation ;
pente/dénivelé seront reportés comme *fait contextuel* si le WMS répond.

## 5. Environnement d'exécution (hors prod)

- Python : `/Users/openclaw/Desktop/labuse/.venv/bin/python` (sqlalchemy 2.0.50, shapely, matplotlib
  3.11.1) ; `PYTHONPATH=<worktree>/src` fait pointer `labuse` sur **ce** worktree.
- `PROJ_DATA=~/miniforge3/envs/labusedb/share/proj`. Ports réservés 8811 / 6011 (aucune API lancée).
