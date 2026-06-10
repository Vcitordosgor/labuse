"""Ingestion des COUCHES STRUCTURANTES réelles → spatial_layers  [✓ live].

Remplace les couches synthétiques de la démo par les vrais flux confirmés au
SPIKE. Chaque fonction range son résultat dans le `kind`/`subtype` exact que la
cascade phase 1 consomme (cf. cascade/layers/phase1.py + config/cascade_rules.yaml).

Discipline : géométries stockées en 4326 (ST_GeomFromGeoJSON + ST_MakeValid) ;
toute mesure se fait en 2975 côté cascade. Résultats partiels (brief §4) : une
source en échec n'empêche pas les autres — chaque couche est isolée.
"""
from __future__ import annotations

import io
import json
import math
import os
import tempfile
import time
import zipfile

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from ..connectors.wfs import WfsConnector

APICARTO = "https://apicarto.ign.fr/api"
ODS_BASE = "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets"
ALTI_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"
# Indicateur national d'érosion côtière (Cerema/GéoLittoral), emprise Réunion, EPSG:2975.
EROSION_URL = ("https://geolittoral.din.developpement-durable.gouv.fr/telechargement/"
               "couches_sig/N_evolution_trait_cote_S_reunion_epsg2975_062018_shape.zip")

# kind LA BUSE -> nom canonique de data_sources (pour data_source_id).
KIND_SOURCE = {
    "water": "BD TOPO IGN",
    "voirie": "BD TOPO IGN",
    "plu_gpu_zone": "Urbanisme PLU/GPU (API Carto)",
    "parc_national": "Parc National de La Réunion (INPN)",
    "abf": "ABF / Monuments historiques",
    "potentiel_foncier": "data.regionreunion.com — Potentiel foncier",
    "ocs_ge": "OCS GE (IGN)",
    "pente": "RGE ALTI (altimétrie)",
    "trait_de_cote": "DEAL Réunion — trait de côte",
    "osm_faux_positif": "OpenStreetMap / Overpass",
}

# Faux positifs géométriques OSM : tags → subtype consommé par la cascade
# (config/cascade_rules.yaml : hard cemetery/school ; flag pitch/parking).
OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_OSM_FP_QUERY = """[out:json][timeout:90];
(
  way["landuse"="cemetery"]({s},{w},{n},{e});
  relation["landuse"="cemetery"]({s},{w},{n},{e});
  way["amenity"="grave_yard"]({s},{w},{n},{e});
  way["amenity"="school"]({s},{w},{n},{e});
  relation["amenity"="school"]({s},{w},{n},{e});
  way["leisure"="pitch"]({s},{w},{n},{e});
  way["amenity"="parking"]({s},{w},{n},{e});
  relation["amenity"="parking"]({s},{w},{n},{e});
);
out geom;"""


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=max(get_settings().http_timeout_s, 60.0),
        headers={"User-Agent": constants.USER_AGENT},
        follow_redirects=True,
    )


def _bbox_polygon(bbox: tuple[float, float, float, float]) -> dict:
    minlon, minlat, maxlon, maxlat = bbox
    return {"type": "Polygon", "coordinates": [[
        [minlon, minlat], [maxlon, minlat], [maxlon, maxlat], [minlon, maxlat], [minlon, minlat],
    ]]}


def _source_ids(session: Session) -> dict[str, int]:
    return {n: i for (n, i) in session.execute(text("SELECT name, id FROM data_sources")).all()}


def _insert_layer(session: Session, kind: str, subtype: str | None, name: str | None,
                  geometry: dict, source_id: int | None, commune: str | None,
                  run_id: int | None, attrs: dict | None = None) -> None:
    """Insère une entité dans spatial_layers (4326, géométrie validée)."""
    session.execute(
        text(
            """
            INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune, ingestion_run_id)
            VALUES (:k, :s, :n,
                    ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                    CAST(:a AS jsonb), :sid, :c, :run)
            """
        ),
        {"k": kind, "s": subtype, "n": name, "g": json.dumps(geometry),
         "a": json.dumps(attrs or {}), "sid": source_id, "c": commune, "run": run_id},
    )


def _ods_records(client: httpx.Client, dataset: str, *, where: str | None = None,
                 select: str | None = None, page: int = 100, cap: int = 10000) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while offset < cap:
        params: dict = {"limit": page, "offset": offset}
        if where:
            params["where"] = where
        if select:
            params["select"] = select
        r = client.get(f"{ODS_BASE}/{dataset}/records", params=params)
        r.raise_for_status()
        res = r.json().get("results", []) or []
        out.extend(res)
        if len(res) < page:
            break
        offset += page
    return out


# ───────────────────────── couches ─────────────────────────

def ingest_gpu_zones(session, bbox, commune, run_id, sids) -> int:
    """PLU/GPU zone-urba (API Carto) → kind='plu_gpu_zone', subtype=typezone."""
    with _client() as c:
        r = c.get(f"{APICARTO}/gpu/zone-urba", params={"geom": json.dumps(_bbox_polygon(bbox))})
        r.raise_for_status()
        feats = r.json().get("features", []) or []
    n = 0
    for f in feats:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        _insert_layer(session, "plu_gpu_zone", (p.get("typezone") or "").strip() or None,
                      p.get("libelong") or p.get("libelle"), f["geometry"],
                      sids.get(KIND_SOURCE["plu_gpu_zone"]), commune, run_id,
                      {"libelle": p.get("libelle"), "partition": p.get("partition"), "idurba": p.get("idurba")})
        n += 1
    return n


def ingest_parc_national(session, commune, run_id, sids) -> int:
    """Parc National (Région ODS pnrun_2021) → subtype 'coeur' | 'adhesion'."""
    with _client() as c:
        recs = _ods_records(c, "pnrun_2021", select="type,code_type,geo_shape", page=50)
    n = 0
    for rec in recs:
        shape = rec.get("geo_shape") or {}
        geom = shape.get("geometry") if shape.get("type") == "Feature" else shape
        if not geom:
            continue
        libelle = (rec.get("type") or "")
        subtype = "coeur" if "coeur" in libelle.lower() or "cœur" in libelle.lower() else "adhesion"
        _insert_layer(session, "parc_national", subtype, libelle, geom,
                      sids.get(KIND_SOURCE["parc_national"]), commune, run_id,
                      {"type": libelle, "code_type": rec.get("code_type")})
        n += 1
    return n


def ingest_potentiel_foncier(session, insee, commune, run_id, sids) -> int:
    """Potentiel foncier Région (grain parcelle) → kind='potentiel_foncier' (bonus §1)."""
    with _client() as c:
        recs = _ods_records(c, "potentiel-foncier", where=f'insee="{insee}"',
                            select="section,parcelle,espacesar,zpu,geo_shape", page=100)
    n = 0
    for rec in recs:
        shape = rec.get("geo_shape") or {}
        geom = shape.get("geometry") if shape.get("type") == "Feature" else shape
        if not geom:
            continue
        _insert_layer(session, "potentiel_foncier", "ilot", "Îlot potentiel foncier Région", geom,
                      sids.get(KIND_SOURCE["potentiel_foncier"]), commune, run_id,
                      {"espacesar": rec.get("espacesar"), "zpu": rec.get("zpu"),
                       "section": rec.get("section"), "parcelle": rec.get("parcelle")})
        n += 1
    return n


def ingest_abf(session, bbox, commune, run_id, sids) -> int:
    """ABF — SUP « abords MH » (API Carto GPU assiette-sup-s, filtre suptype AC1)."""
    with _client() as c:
        r = c.get(f"{APICARTO}/gpu/assiette-sup-s", params={"geom": json.dumps(_bbox_polygon(bbox))})
        r.raise_for_status()
        feats = r.json().get("features", []) or []
    n = 0
    for f in feats:
        p = f.get("properties") or {}
        suptype = (p.get("suptype") or "").upper()
        if suptype != "AC1" or not f.get("geometry"):   # AC1 = abords de monuments historiques (ABF)
            continue
        _insert_layer(session, "abf", suptype, p.get("nomass") or "Servitude AC1", f["geometry"],
                      sids.get(KIND_SOURCE["abf"]), commune, run_id,
                      {"suptype": suptype, "nomass": p.get("nomass")})
        n += 1
    return n


def ingest_bdtopo(session, bbox, commune, run_id, sids, kind: str, typename: str, max_features: int = 8000) -> int:
    """BD TOPO via WFS Géoplateforme (bbox lon,lat) → kind (water | voirie)."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=bbox, max_features=max_features)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        _insert_layer(session, kind, p.get("nature"), p.get("nature") or typename.split(":")[-1],
                      f["geometry"], sids.get(KIND_SOURCE[kind]), commune, run_id, None)
        n += 1
    return n


def ingest_ocsge(session, bbox, commune, run_id, sids) -> int:
    """Occupation du sol (proxy BD CARTO `occupation_du_sol`, OCS GE 974 non exposé en WFS)."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "BDCARTO_V5:occupation_du_sol", bbox=bbox, max_features=3000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        nat = ((f.get("properties") or {}).get("nature") or "")
        low = nat.lower()
        if any(w in low for w in ("forêt", "foret", "bois", "végé", "vege", "lande", "verger", "haie")):
            sub = "naturel"
        elif any(w in low for w in ("cult", "agric", "vigne", "prairie", "canne")):
            sub = "agricole"
        else:
            sub = "artificialise"
        _insert_layer(session, "ocs_ge", sub, nat or "occupation du sol", f["geometry"],
                      sids.get(KIND_SOURCE["ocs_ge"]), commune, run_id, {"nature": nat, "src": "BDCARTO_V5"})
        n += 1
    return n


def ingest_pente(session, bbox, commune, run_id, sids, step_m: float = 180.0, chunk: int = 100) -> int:
    """Pente par échantillonnage RGE ALTI sur une GRILLE régulière (≈raster), batché.

    Indépendant du nombre de parcelles (grille fixe sur le bbox) → tient la commune
    entière sans des dizaines de milliers d'appels. Affichée, NON éliminatoire (§2)."""
    minlon, minlat, maxlon, maxlat = bbox
    dlat = step_m / 110574.0
    dlon = step_m / ((111320.0 * math.cos(math.radians((minlat + maxlat) / 2))) or 1.0)
    lats, y = [], minlat
    while y <= maxlat + dlat:
        lats.append(y)
        y += dlat
    lons, x = [], minlon
    while x <= maxlon + dlon:
        lons.append(x)
        x += dlon
    nodes = [(i, j, lons[j], lats[i]) for i in range(len(lats)) for j in range(len(lons))]
    elev: dict[tuple[int, int], float] = {}
    with _client() as c:
        for k in range(0, len(nodes), chunk):
            part = nodes[k:k + chunk]
            r = c.get(ALTI_URL, params={
                "lon": "|".join(f"{p[2]:.6f}" for p in part),
                "lat": "|".join(f"{p[3]:.6f}" for p in part),
                "resource": "ign_rge_alti_wld", "zonly": "true"})
            for idx, h in enumerate(r.json().get("elevations", [])):
                elev[(part[idx][0], part[idx][1])] = h
            time.sleep(0.21)  # quota 5 req/s
    n = 0
    for i in range(len(lats) - 1):
        for j in range(len(lons) - 1):
            hs = [elev.get((i, j)), elev.get((i, j + 1)), elev.get((i + 1, j)), elev.get((i + 1, j + 1))]
            hs = [h for h in hs if h is not None and h > -9999]
            if len(hs) < 2:
                continue
            slope = (max(hs) - min(hs)) / step_m * 100.0
            cell = {"type": "Polygon", "coordinates": [[
                [lons[j], lats[i]], [lons[j + 1], lats[i]], [lons[j + 1], lats[i + 1]],
                [lons[j], lats[i + 1]], [lons[j], lats[i]]]]}
            _insert_layer(session, "pente", None, "Pente RGE ALTI (grille)", cell,
                          sids.get(KIND_SOURCE["pente"]), commune, run_id, {"slope_pct": round(slope, 1)})
            n += 1
    return n


_GEO_DVF_CACHE: list[dict] | None = None  # dept 974 agrégé, téléchargé une fois par process


def ingest_dvf(session, insee, commune, run_id, sids) -> int:
    """DVF géolocalisé (Etalab, data.gouv) pour la commune.

    Remplace l'ancien flux ODS Région (2014-2021, surfaces lacunaires, mutation_id =
    parcelle). Apporte : millésime récent (5 ans glissants), id_mutation RÉEL (traçabilité),
    surface bâtie correcte agrégée PAR MUTATION (€/m² juste, plus de surcompte multi-lots),
    VEFA exploitable (= comparable « neuf »), et une vraie coordonnée de mutation."""
    global _GEO_DVF_CACHE
    if _GEO_DVF_CACHE is None:
        _GEO_DVF_CACHE = fetch_geo_dvf()  # dept 974 entier, une seule fois
    muts = [m for m in _GEO_DVF_CACHE if m["insee"] == insee]
    if not muts:
        return 0
    stmt = text(
        """INSERT INTO dvf_mutations
           (mutation_id, date_mutation, valeur_fonciere, type_local, surface_reelle_bati,
            surface_terrain, nature_mutation, commune, geom, raw)
           VALUES (:mid, :dt, :val, :tl, :sb, :st, :nat, :com,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:raw AS jsonb))""")
    params = [{**m, "com": commune,
               "raw": json.dumps({"source": "geo-dvf Etalab (data.gouv)",
                                  "id_mutation": m["mid"], "vefa": m["vefa"]})}
              for m in muts]
    session.execute(stmt, params)
    return len(params)


GEO_DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dep}.csv.gz"
GEO_DVF_YEARS = (2021, 2022, 2023, 2024, 2025)  # millésime « latest » Etalab (5 ans glissants)


def _geo_dvf_aggregate(rows: list[dict]) -> list[dict]:
    """Agrège les lignes geo-dvf (DVF géolocalisé Etalab) PAR MUTATION RÉELLE.

    DVF éclate une vente en plusieurs lignes (un local / lot / parcelle par ligne) qui
    portent TOUTES la valeur foncière TOTALE de la mutation. Un €/m² calculé ligne par
    ligne surévalue donc les ventes multi-lots. On regroupe par id_mutation, on somme la
    surface bâtie des locaux RÉSIDENTIELS (Maison/Appartement) et on divise la valeur par
    cette surface — €/m² correct, et dédoublonnage exact (le vrai défaut du flux ODS).

    On ne garde que les mutations mono-type, géolocalisées et avec surface : aucun prix
    fabriqué. La VEFA est conservée SI elle a une surface (geo-dvf la fournit, au contraire
    du flux ODS où elle vaut 0) — c'est le comparable « neuf » que vend un promoteur.
    """
    from collections import defaultdict
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["id_mutation"]].append(r)
    out: list[dict] = []
    for mid, rs in by.items():
        locs = [r for r in rs if r["type_local"] in ("Maison", "Appartement")
                and r["surface_reelle_bati"] and float(r["surface_reelle_bati"]) > 0]
        if not locs:
            continue
        types = {r["type_local"] for r in locs}
        if len(types) > 1:            # mutation appart+maison : €/m² ambigu → écartée
            continue
        vals = [float(r["valeur_fonciere"]) for r in rs if r["valeur_fonciere"]]
        coords = next(((r["longitude"], r["latitude"]) for r in locs
                       if r["longitude"] and r["latitude"]), None)
        if not vals or not coords:    # sans prix ou sans géolocalisation : inexploitable
            continue
        terr = next((float(r["surface_terrain"]) for r in rs if r.get("surface_terrain")), None)
        out.append({
            "mid": mid, "dt": rs[0]["date_mutation"], "val": max(vals),
            "tl": next(iter(types)),
            "sb": round(sum(float(r["surface_reelle_bati"]) for r in locs), 2),
            "st": terr, "nat": rs[0]["nature_mutation"], "insee": rs[0]["code_commune"],
            "lon": float(coords[0]), "lat": float(coords[1]),
            "vefa": any("futur" in r["nature_mutation"].lower() for r in rs),
        })
    return out


def fetch_geo_dvf(years: tuple[int, ...] = GEO_DVF_YEARS, dep: str = "974") -> list[dict]:
    """Télécharge geo-dvf (data.gouv, Etalab) pour un département et agrège par mutation."""
    import csv
    import gzip
    rows: list[dict] = []
    with _client() as c:
        for y in years:
            r = c.get(GEO_DVF_URL.format(year=y, dep=dep), timeout=120.0)
            r.raise_for_status()
            txt = gzip.decompress(r.content).decode("utf-8", "replace")
            rows += list(csv.DictReader(txt.splitlines()))
    return _geo_dvf_aggregate(rows)


def load_dvf_geo(session: Session, target: str = "dvf_mutations",
                 years: tuple[int, ...] = GEO_DVF_YEARS) -> int:
    """Charge geo-dvf dans `target` : mutation_id = id_mutation RÉEL (traçabilité corrigée),
    géométrie = vraie coordonnée lon/lat de la mutation (plus le centroïde de parcelle).
    N'insère que les communes ayant des parcelles chargées (jointure commune du moteur).
    Idempotent à l'appelant : vider `target` avant si rechargement. Renvoie le nombre inséré."""
    muts = fetch_geo_dvf(years)
    insee2com = {idu[:5]: com for (com, idu) in session.execute(
        text("SELECT commune, min(idu) FROM parcels GROUP BY commune")).all()}
    stmt = text(f"""
        INSERT INTO {target}
          (mutation_id, date_mutation, valeur_fonciere, type_local,
           surface_reelle_bati, surface_terrain, nature_mutation, commune, geom, raw)
        VALUES
          (:mid, :dt, :val, :tl, :sb, :st, :nat, :com,
           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:raw AS jsonb))""")
    params = []
    for m in muts:
        com = insee2com.get(m["insee"])
        if com is None:
            continue
        params.append({**m, "com": com,
                       "raw": json.dumps({"source": "geo-dvf Etalab (data.gouv)",
                                          "id_mutation": m["mid"], "vefa": m["vefa"]})})
    if params:
        session.execute(stmt, params)
    return len(params)


def ingest_foret_publique(session, bbox, commune, run_id, sids) -> int:
    """Forêts publiques / régime forestier — BD TOPO (IGN/ONF) via WFS Géoplateforme."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "BDTOPO_V3:foret_publique", bbox=bbox, max_features=5000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        topo = p.get("toponyme") or ""
        subtype = "domaniale" if "domanial" in topo.lower() else "publique"
        _insert_layer(session, "foret_publique", subtype, topo or "Forêt publique", f["geometry"],
                      sids.get("Forêts publiques (ONF)"), commune, run_id,
                      {"toponyme": topo, "src": "BDTOPO_V3:foret_publique"})
        n += 1
    return n


def ingest_rpg_agricole(session, bbox, commune, run_id, sids) -> int:
    """Parcelles agricoles déclarées (RPG, IGN/ASP via WFS) → proxy zonage agricole/SAFER."""
    wfs = WfsConnector("geoplateforme_wfs")
    fc = wfs.fetch_layer("geoplateforme_wfs", "RPG.LATEST:parcelles_graphiques", bbox=bbox, max_features=12000)
    n = 0
    for f in fc.get("features", []) or []:
        if not f.get("geometry"):
            continue
        p = f.get("properties") or {}
        _insert_layer(session, "safer", "rpg", f"Parcelle agricole RPG ({p.get('code_cultu') or '?'})",
                      f["geometry"], sids.get("Zonage SAFER (DAAF)"), commune, run_id,
                      {"code_cultu": p.get("code_cultu"), "code_group": p.get("code_group"), "src": "RPG.LATEST"})
        n += 1
    return n


_PROTECTED = [
    ("patrinat_apb:apb", "APB"),
    ("patrinat_aphn:aire_protection_habitats_naturels", "APHN"),
    ("patrinat_rnn:rnn", "Réserve naturelle nationale"),
    ("patrinat_rnr:rnr", "Réserve naturelle régionale"),
    ("patrinat_rb:reserve_biologique", "Réserve biologique"),
    ("patrinat_cen:cen", "Conservatoire d'espaces naturels"),
    ("patrinat_cdl:conservatoire_littoral", "Conservatoire du littoral"),
]


def ingest_espaces_proteges(session, bbox, commune, run_id, sids) -> int:
    """Espaces protégés réglementaires (INPN/MNHN via WFS Géoplateforme) → couche `ens`.

    ENS départemental proprement dit non public ; on intègre les protections
    réglementaires (APB/APHN/réserves/conservatoires) qui jouent le même rôle de
    contrainte. Étiquetées par leur vrai type."""
    wfs = WfsConnector("geoplateforme_wfs")
    n = 0
    for typename, label in _PROTECTED:
        try:
            fc = wfs.fetch_layer("geoplateforme_wfs", typename, bbox=bbox, max_features=2000)
        except Exception:
            continue
        for f in fc.get("features", []) or []:
            if not f.get("geometry"):
                continue
            p = f.get("properties") or {}
            # M1 : ne JAMAIS flaguer du foncier terrestre avec une protection MARINE
            # (ex. Réserve naturelle marine de La Réunion). On garde les protections terrestres.
            if str(p.get("marin", "")).strip().upper() in ("T", "OUI", "TRUE", "1"):
                continue
            nom = p.get("nom_site") or p.get("nom") or p.get("toponyme") or p.get("libelle") or label
            _insert_layer(session, "ens", label.lower().replace(" ", "_")[:48], f"{label} — {nom}"[:255],
                          f["geometry"], sids.get("ENS (Département)"), commune, run_id,
                          {"type": label, "src": typename, "marin": p.get("marin")})
            n += 1
    return n


def _taux_subtype(taux) -> str:
    """Mappe le taux d'évolution (m/an) du trait de côte vers le vocabulaire cascade."""
    if taux is None or taux <= -9000:
        return "indetermine"           # -9999 = donnée absente
    if taux <= -1.0:
        return "bande_courte"          # recul fort → HARD_EXCLUDE
    if taux < -0.1:
        return "bande_longue"          # recul modéré → SOFT_FLAG
    return "stable"                    # stable / accrétion → PASS


def ingest_trait_de_cote(session, commune, run_id, sids) -> int:
    """Indicateur national d'érosion côtière (Cerema/GéoLittoral) — SHP Réunion EPSG:2975.

    Téléchargé puis reprojeté 2975→4326 (pyproj). `taux` (m/an) → recul fort = exclude,
    recul modéré = flag (cf. config/cascade_rules.yaml : trait_de_cote)."""
    import shapefile  # pyshp
    from pyproj import Transformer

    with _client() as c:
        r = c.get(EROSION_URL)
        r.raise_for_status()
    tmp = tempfile.mkdtemp(prefix="labuse_tdc_")
    zipfile.ZipFile(io.BytesIO(r.content)).extractall(tmp)
    shp = next((os.path.join(tmp, f) for f in os.listdir(tmp) if f.lower().endswith(".shp")), None)
    if not shp:
        return 0
    rd = shapefile.Reader(shp)
    flds = [f[0] for f in rd.fields[1:]]
    ti = flds.index("taux") if "taux" in flds else None
    tr = Transformer.from_crs(2975, 4326, always_xy=True)
    n = 0
    for srec in rd.shapeRecords():
        sh = srec.shape
        if not sh.points or sh.shapeType not in (5, 15, 25):
            continue
        taux = float(srec.record[ti]) if ti is not None else None
        parts = list(sh.parts) + [len(sh.points)]
        polys = []
        for k in range(len(parts) - 1):
            ring = sh.points[parts[k]:parts[k + 1]]
            coords = [list(tr.transform(x, y)) for (x, y) in ring]
            if len(coords) >= 4:
                polys.append([coords])
        if not polys:
            continue
        _insert_layer(session, "trait_de_cote", _taux_subtype(taux),
                      f"Évolution trait de côte (taux {taux} m/an)",
                      {"type": "MultiPolygon", "coordinates": polys},
                      sids.get(KIND_SOURCE["trait_de_cote"]), commune, run_id,
                      {"taux": taux, "src": "GéoLittoral/Cerema — indicateur érosion (SHP, EPSG:2975)"})
        n += 1
    return n


def _overpass(query: str, tries: int = 3) -> dict:
    """POST Overpass, résilient : retries + bascule de mirror (Overpass est souvent saturé)."""
    last: Exception | None = None
    with _client() as c:
        for mirror in OVERPASS_MIRRORS:
            for attempt in range(tries):
                try:
                    r = c.post(mirror, data={"data": query})
                    r.raise_for_status()
                    return r.json()
                except Exception as exc:  # noqa: BLE001 - on retente / on bascule
                    last = exc
                    time.sleep(2 ** attempt)
    raise last  # type: ignore[misc]


def _osm_fp_subtype(tags: dict) -> str | None:
    if tags.get("landuse") == "cemetery" or tags.get("amenity") == "grave_yard":
        return "cemetery"
    if tags.get("amenity") == "school":
        return "school"
    if tags.get("leisure") == "pitch":
        return "pitch"
    if tags.get("amenity") == "parking":
        return "parking"
    return None


def _osm_ring(geometry: list) -> list | None:
    coords = [[g["lon"], g["lat"]] for g in (geometry or []) if g.get("lon") is not None]
    if len(coords) < 3:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords if len(coords) >= 4 else None


def ingest_osm_faux_positifs(session, bbox, commune, run_id, sids) -> int:
    """Faux positifs géométriques OSM (cimetière / école / terrain de sport / parking) via
    Overpass → kind='osm_faux_positif'. Étiquettes mappées vers les subtypes que la cascade
    consomme (hard: cemetery/school ; flag: pitch/parking). Empêche qu'un équipement public
    ressorte en « opportunité »."""
    minlon, minlat, maxlon, maxlat = bbox
    data = _overpass(_OSM_FP_QUERY.format(s=minlat, w=minlon, n=maxlat, e=maxlon))
    src = sids.get(KIND_SOURCE["osm_faux_positif"])
    n = 0
    for el in data.get("elements", []) or []:
        sub = _osm_fp_subtype(el.get("tags", {}) or {})
        if not sub:
            continue
        geom = None
        if el.get("type") == "way":
            ring = _osm_ring(el.get("geometry"))
            if ring:
                geom = {"type": "Polygon", "coordinates": [ring]}
        elif el.get("type") == "relation":
            polys = [[r] for m in (el.get("members") or [])
                     if m.get("role") == "outer" and (r := _osm_ring(m.get("geometry")))]
            if polys:
                geom = {"type": "MultiPolygon", "coordinates": polys}
        if not geom:
            continue
        name = (el.get("tags", {}) or {}).get("name") or f"{sub} (OSM)"
        _insert_layer(session, "osm_faux_positif", sub, name[:255], geom, src, commune, run_id,
                      {"osm_id": el.get("id"), "osm_type": el.get("type"), "subtype": sub})
        n += 1
    return n


def ingest_layers(session: Session, insee: str, commune: str,
                  bbox: tuple[float, float, float, float], run_id: int | None) -> dict[str, object]:
    """Ingère toutes les couches géométriques réelles disponibles. Isolé par couche."""
    sids = _source_ids(session)
    counts: dict[str, object] = {}
    jobs = [
        ("plu_gpu_zone", lambda: ingest_gpu_zones(session, bbox, commune, run_id, sids)),
        ("parc_national", lambda: ingest_parc_national(session, commune, run_id, sids)),
        ("potentiel_foncier", lambda: ingest_potentiel_foncier(session, insee, commune, run_id, sids)),
        ("abf", lambda: ingest_abf(session, bbox, commune, run_id, sids)),
        ("water", lambda: ingest_bdtopo(session, bbox, commune, run_id, sids, "water", "BDTOPO_V3:surface_hydrographique")),
        ("voirie", lambda: ingest_bdtopo(session, bbox, commune, run_id, sids, "voirie", "BDTOPO_V3:troncon_de_route")),
        ("ocs_ge", lambda: ingest_ocsge(session, bbox, commune, run_id, sids)),
        ("foret_publique", lambda: ingest_foret_publique(session, bbox, commune, run_id, sids)),
        ("safer", lambda: ingest_rpg_agricole(session, bbox, commune, run_id, sids)),
        ("ens", lambda: ingest_espaces_proteges(session, bbox, commune, run_id, sids)),
        ("trait_de_cote", lambda: ingest_trait_de_cote(session, commune, run_id, sids)),
        ("pente", lambda: ingest_pente(session, bbox, commune, run_id, sids)),
        ("osm_faux_positif", lambda: ingest_osm_faux_positifs(session, bbox, commune, run_id, sids)),
        ("dvf", lambda: ingest_dvf(session, insee, commune, run_id, sids)),
    ]
    for kind, fn in jobs:
        try:
            # SAVEPOINT par couche : un échec n'annule QUE cette couche (§4), pas les parcelles.
            with session.begin_nested():
                counts[kind] = fn()
        except Exception as exc:
            counts[kind] = f"ERREUR {type(exc).__name__}: {exc}"
    return counts
