# Domaine 1 — Géométrie et surfaces servies

## Verdict (3 lignes)
434 582 parcelles passées au crible (géométrie) + 433 229 lignes `parcel_residuel` + 292 056 `parcel_residuel_bati`. 9 invariants vérifiés sur l'île entière.
Violations : **1 FAUX-CLIENT** (taux d'emprise / pct_potentiel servis jusqu'à 19 569 %, sans clamp), **3 INCOHERENT** (centroïde hors parcelle, emprise bâtie > dessin dans une table amont, `surface_terrain_m2` du run entièrement NULL), **1 muet** (parcelle-dans-commune : aucune couche limite communale ingérée → vérifié par INSEE seulement).
Tout le reste est PROPRE : 0 géométrie invalide, 0 SRID faux, 0 surface nulle/négative servie, 0 disparue dans `parcel_residuel`/`score_labuse`, borne « surface incertaine » (facteur 2) couvre bien les 1 593 divergences contenance↔dessin.

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
|---|---|---|---|---|
| 1 | Toute géométrie servie est valide, non nulle, au bon SRID (geom=4326, geom_2975=2975). | `SELECT count(*), count(*) FILTER (WHERE NOT ST_IsValid(geom)), count(*) FILTER (WHERE NOT ST_IsValid(geom_2975)), count(*) FILTER (WHERE ST_SRID(geom)<>4326), count(*) FILTER (WHERE ST_SRID(geom_2975)<>2975), count(*) FILTER (WHERE geom IS NULL OR geom_2975 IS NULL) FROM parcels;` | 434 582 | **0** |
| 2 | Le centroïde stocké de la parcelle tombe DANS sa géométrie. | `SELECT count(*) FILTER (WHERE centroid IS NOT NULL AND NOT ST_Intersects(geom, centroid)) FROM parcels;` | 434 582 | **9 845** (9 792 vivantes) |
| 3 | L'emprise bâtie (`parcel_residuel_bati.emprise_batie_m2`) ne dépasse pas le dessin de la parcelle. | `SELECT count(*) FILTER (WHERE b.emprise_batie_m2 > ST_Area(p.geom_2975)+1) FROM parcel_residuel_bati b JOIN parcels p ON p.idu=b.idu;` | 292 056 | **20 243** |
| 4 | Une parcelle disparue du cadastre n'alimente aucun calcul servi (résiduel / score). | `SELECT count(*) FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id WHERE p.cadastre_disparue_le IS NOT NULL;` (+ idem score_labuse servi, + parcel_zone_plu) | 1 353 disparues | **0** en résiduel/score ; 1 346 restent dans `parcel_zone_plu` (jamais servies, cf §Violations note) |
| 5 | La surface du terrain utilisée par le run (`surface_terrain_m2`) est présente et > 0 pour chaque ligne servie. | `SELECT count(*), count(*) FILTER (WHERE surface_terrain_m2 IS NULL) FROM parcel_residuel;` (+ `parcel_residuel_runs WHERE run_seq=15`) | 433 229 | **433 229 NULL** (colonne entièrement vide, run comme snapshot) |
| 6 | Quand la contenance s'écarte d'un facteur > 2 du dessin, la parcelle bascule « surface incertaine » (tracée). | `WITH x AS (SELECT idu,surface_m2 d,contenance_m2 c FROM parcels WHERE contenance_m2 IS NOT NULL AND surface_m2>0 AND cadastre_disparue_le IS NULL) SELECT count(*) FILTER (WHERE c<d/2 OR c>2*d) FROM x;` | 433 201 | 1 593 détectées (TOUTES couvertes par `surface_incertaine`, surface.py:48) → 0 non-tracée |
| 7 | Chaque parcelle est dans sa commune : préfixe INSEE de l'IDU ↔ 1 seul nom de commune. | `SELECT count(*) FROM (SELECT left(idu,5) FROM parcels GROUP BY 1 HAVING count(DISTINCT commune)>1) x;` (24 communes = 24 préfixes) | 434 582 | **0** |
| 8 | Aucune surface servie (dessin ou contenance) n'est nulle ou négative. | `SELECT count(*) FILTER (WHERE surface_m2<=0), count(*) FILTER (WHERE contenance_m2 IS NOT NULL AND contenance_m2<=0) FROM parcels WHERE cadastre_disparue_le IS NULL;` | 433 229 vivantes | **0** |
| 9 | Les ratios servis du résiduel sont bornés : taux_emprise ∈ [0,100], pct_potentiel ∈ [0,100], sdp ≥ 0. | `SELECT count(*) FILTER (WHERE taux_emprise_pct>100), count(*) FILTER (WHERE pct_potentiel>100), count(*) FILTER (WHERE sdp_residuelle_m2<0) FROM parcel_residuel;` | 433 229 (258 389 non-NULL) | **taux>100 : 61 599 · pct>100 : 64 293 · sdp<0 : 0** |

## Violations

### V1 — taux d'emprise / pourcentage de potentiel servis jusqu'à 19 569 % (FAUX-CLIENT)
- **Gravité** : FAUX-CLIENT (le client lit un pourcentage absurde dans la fiche et le Comparatif).
- **idu(s)** : 61 599 parcelles pour `taux_emprise_pct>100` (max 19 569 %), 64 293 pour `pct_potentiel>100` (max 20 140 %). Pires : parcel_id 331544 (taux 19569, pct 20140), 331651, 176026. Ce sont des parcelles presque entièrement bâties (bâti existant > emprise constructible U/AU), dessin moyen 627 m².
- **Attendu** : un taux d'occupation et un % déjà-bâti bornés à 100 % (une parcelle ne peut être occupée à plus de 100 % de sa capacité).
- **Obtenu** : `100 * emprise_batie / emprise_max` et `100 * sdp_existante / sdp_max` servis BRUTS, sans `min(100, …)`. Quand `emprise_batie` (bâti mesuré sur toute la parcelle, source bati.py) dépasse `emprise_max` (capacité calculée sur la portion U/AU clippée, souvent minuscule), le rapport explose.
- **Où c'est servi** : fiche `/parcels/{idu}` tuile gabarit (`src/labuse/api/app.py:8069` `"taux_emprise_pct": res.get("taux_emprise_pct")`), Comparatif (`src/labuse/exports/blocs/comparatif.py:97` ligne « Taux d'occupation du gabarit » → `_pct` rend « 19569 % »). Corrompt aussi le **filtre emprise min/max** (`src/labuse/api/app.py:1880-1884`) et le partage « État du sol » (`:1683-1686`).
- **Cause probable / fichier:ligne** : `src/labuse/faisabilite/residuel.py:215-216` — `taux_emprise = (100.0 * emprise_batie / emprise_max)` et `pct_potentiel = (100.0 * sdp_existante / sdp_max)` sans clamp supérieur (le clamp inférieur n'existe pas non plus, mais aucune valeur < 0 observée). Le `sous_densite` dérivé (`:218`) hérite de la même valeur non bornée.

### V2 — centroïde stocké hors de la parcelle (INCOHERENT / ROBUSTESSE)
- **Gravité** : INCOHERENT (un point « centre de la parcelle » qui n'est pas dedans ; impact servi limité, voir plus bas).
- **idu(s)** : 9 845 parcelles (9 792 vivantes), centroïde jusqu'à 236,1 m hors géométrie (97414000CK0122), 701 à plus de 20 m. Grandes parcelles concaves/en croissant mono-partie où le barycentre tombe dans le creux.
- **Attendu** : un point garanti DANS la parcelle (ST_PointOnSurface).
- **Obtenu** : `ST_Centroid` (barycentre), qui sort des géométries concaves.
- **Cause probable / fichier:ligne** : `src/labuse/ingestion/cadastre_ingest.py:42` — `centroid = ST_Centroid(ST_MakeValid(...))`. Devrait être `ST_PointOnSurface`.
- **Impact servi (borné)** : la zone PLU SERVIE (`parcel_zone_plu`) est la **dominante par surface** (`ST_Intersection`, `src/labuse/faisabilite/zone_servie.py:66-73`), PAS le centroïde → le zonage servi n'est PAS faussé. Le centroïde ne feed que des proximités (couche « eau »/« ravine » dans la cascade, outil ÉTUDE-ZONE marché/aménités `src/labuse/zone.py:714,870,900`), où un barycentre à 236 m peut rattacher une parcelle à la mauvaise zone de proximité. À confirmer côté domaine cascade/zone.

### V3 — emprise bâtie > dessin dans `parcel_residuel_bati` (INCOHERENT)
- **Gravité** : INCOHERENT (deux lecteurs du bâti divergent ; le chiffre fautif n'atteint PAS la fiche).
- **idu(s)** : 20 243 (dont 19 364 où bâti > contenance aussi) ; surtout des parcelles minuscules (97406000AI0587 : bâti 18 m² / dessin 6 m²) ; ratio max 3,0.
- **Attendu** : emprise bâtie clippée à la parcelle ⇒ ≤ surface.
- **Obtenu** : `parcel_residuel_bati.emprise_batie_m2` n'est pas clippé comme la fiche l'est.
- **Cause / fichier** : table amont (ingestion, non réécrite par le code applicatif lu). Le lecteur SERVI de la fiche est `src/labuse/bati.py:119,147` (`ST_Area(ST_Union(ST_Intersection(b.geom_2975,p.geom_2975)))`, borné + garde RECETTE-5 ligne 234) et NON cette table ; `emprise_residuelle_m2` est clampée à 0 (0 négatif observé) et ces parcelles ressortent `cause=terrain_exigu`, verdict honnête. Donc pas de chiffre faux servi, mais incohérence de source à corriger à l'ingestion.

### V4 — `surface_terrain_m2` du run entièrement NULL (INCOHERENT / perte de fonctionnalité)
- **Gravité** : INCOHERENT (la fiche ne peut jamais afficher « Calcul du JJ/MM sur X m² » ; fonction E-B1 CHASSE-CALCULS morte sur le run servi).
- **idu(s)** : 433 229 / 433 229 lignes `parcel_residuel` ET 433 229 du snapshot `parcel_residuel_runs` (run_seq 15) ont `surface_terrain_m2 IS NULL`.
- **Attendu** : la surface utilisée par le run, écrite à chaque ligne (`src/labuse/faisabilite/residuel.py:243` `"surface_terrain_m2": round(surface)`).
- **Obtenu** : NULL partout → `src/labuse/api/app.py:6336` `_surf_run=None` → `surface_calcul_m2=None` et la note de péremption générique s'affiche (branche `:6346`, commentaire « run antérieur au lot (surface non écrite) »).
- **Cause probable** : le run q_v18/run_seq 15 servi a été calculé/figé AVANT que la colonne `surface_terrain_m2` soit peuplée (le code d'écriture existe mais n'a pas été rejoué). Donnée de run obsolète, pas un bug de code vif. Pas de chiffre faux servi (la SDP reste juste) — c'est la transparence « surface du calcul » qui est muette.

### Note INV4 — disparues résiduelles dans `parcel_zone_plu`
1 346 des 1 353 disparues restent dans `parcel_zone_plu` (table non purgée). Ce N'EST PAS une fuite : la liste/omnibox gatent sur `parcels.cadastre_disparue_le IS NULL` (`src/labuse/api/app.py:2104` `filtre_vivant_sql`, `:2703`), donc aucune disparue n'est servie. Dette de propreté, pas une violation d'invariant servi.

## Non vérifié
- **Parcelle géométriquement DANS sa commune** : AUCUNE couche de limites communales n'est ingérée (`spatial_layers` kind commune/admin = 0 ligne). Vérifié uniquement par cohérence du préfixe INSEE de l'IDU ↔ nom de commune (INV7, 0 écart) ; l'appartenance géométrique stricte (polygone parcelle ⊂ polygone commune) reste non testable localement.
- **Impact réel du centroïde faux sur la cascade eau/ravine et l'outil ÉTUDE-ZONE** : relève du domaine cascade/zone ; j'ai borné le risque (pas sur le zonage servi) mais pas quantifié les rattachements de proximité erronés.
- **Clamp inférieur des ratios** : aucune valeur négative observée, mais la formule `residuel.py:215-216` n'a pas de garde — non prouvé robuste sur un run futur.

## Gardes proposées
Prêtes pour `scripts/coherence/chasse_invariants.py` (chaque fonction rend `("[OK]"/"[ECART]", msg)` ; le runner fait `exit 1` si un `[ECART]`). Pseudo-SQL :

```python
def g_geom_valide(db):  # INV1 — DOIT rester 0
    n = db.execute(text("""SELECT count(*) FROM parcels
        WHERE NOT ST_IsValid(geom) OR NOT ST_IsValid(geom_2975)
           OR ST_SRID(geom)<>4326 OR ST_SRID(geom_2975)<>2975
           OR geom IS NULL OR geom_2975 IS NULL""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"geom invalides/SRID faux/nulles: {n}")

def g_ratios_bornes(db):  # INV9 / V1 — le FAUX-CLIENT. Attendu 0.
    r = db.execute(text("""SELECT
        count(*) FILTER (WHERE taux_emprise_pct>100) AS t,
        count(*) FILTER (WHERE pct_potentiel>100)   AS p,
        count(*) FILTER (WHERE sdp_residuelle_m2<0 OR taux_emprise_pct<0 OR pct_potentiel<0) AS neg
        FROM parcel_residuel""")).mappings().one()
    bad = r["t"]+r["p"]+r["neg"]
    return ("[OK]" if bad==0 else "[ECART]",
            f"ratios residuel hors bornes — taux>100:{r['t']} pct>100:{r['p']} <0:{r['neg']}")

def g_bati_sous_dessin(db):  # INV3 / V3 — Attendu 0 une fois la table clippée.
    n = db.execute(text("""SELECT count(*) FROM parcel_residuel_bati b
        JOIN parcels p ON p.idu=b.idu
        WHERE b.emprise_batie_m2 > ST_Area(p.geom_2975)+1""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"emprise batie > dessin: {n}")

def g_surface_run_presente(db):  # INV5 / V4 — Attendu 0.
    n = db.execute(text("""SELECT count(*) FROM parcel_residuel
        WHERE surface_terrain_m2 IS NULL OR surface_terrain_m2<=0""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"surface_terrain_m2 run nulle/<=0: {n}")

def g_disparue_hors_calcul(db):  # INV4 — Attendu 0.
    n = db.execute(text("""SELECT count(*) FROM parcel_residuel r
        JOIN parcels p ON p.id=r.parcel_id
        WHERE p.cadastre_disparue_le IS NOT NULL""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"disparue dans parcel_residuel: {n}")

def g_centroid_dans_parcelle(db):  # INV2 / V2 — basculer en [ECART] après passage à ST_PointOnSurface.
    n = db.execute(text("""SELECT count(*) FROM parcels
        WHERE cadastre_disparue_le IS NULL AND centroid IS NOT NULL
          AND NOT ST_Intersects(geom, centroid)""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"centroide hors parcelle (vivantes): {n}")

def g_surface_nonpos(db):  # INV8 — Attendu 0.
    n = db.execute(text("""SELECT count(*) FROM parcels
        WHERE cadastre_disparue_le IS NULL
          AND (surface_m2<=0 OR (contenance_m2 IS NOT NULL AND contenance_m2<=0))""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"surface servie nulle/negative: {n}")

def g_insee_une_commune(db):  # INV7 — Attendu 0.
    n = db.execute(text("""SELECT count(*) FROM
        (SELECT left(idu,5) FROM parcels GROUP BY 1 HAVING count(DISTINCT commune)>1) x""")).scalar()
    return ("[OK]" if n==0 else "[ECART]", f"prefixe INSEE a plusieurs communes: {n}")
```

NB : `g_ratios_bornes`, `g_surface_run_presente`, `g_bati_sous_dessin` échouent AUJOURD'HUI sur le run servi (ce sont V1/V4/V3). `g_centroid_dans_parcelle` échoue aussi (V2) ; les garder en [OK] tant que la règle de proximité n'est pas tranchée fausserait le banc — proposition : les activer en [ECART] et laisser Vic trancher les correctifs (clamp `min(100,…)` dans residuel.py, `ST_PointOnSurface` à l'ingestion, re-run pour peupler `surface_terrain_m2`, clip de la table bâti amont).
