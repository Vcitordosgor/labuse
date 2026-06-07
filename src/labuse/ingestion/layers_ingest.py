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
}


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


def ingest_dvf(session, insee, commune, run_id, sids) -> int:
    """DVF (Région ODS) géolocalisé via jointure l_idpar→parcelle (requête par RAYON, §7bis)."""
    with _client() as c:
        recs = _ods_records(c, "demande-de-valeurs-foncierespublic", where=f'l_codinsee like "{insee}"',
                            select="l_idpar,valeurfonc,datemut,libnatmut,libtypbien,sterr", page=100, cap=10000)
    by_idpar: dict[str, dict] = {}
    for r in recs:
        for idpar in (r.get("l_idpar") or []):
            by_idpar.setdefault(idpar, r)
    n = 0
    for pid, idu in session.execute(text("SELECT id, idu FROM parcels")).all():
        m = by_idpar.get(idu)
        if not m:
            continue
        session.execute(
            text(
                """INSERT INTO dvf_mutations
                   (mutation_id, date_mutation, valeur_fonciere, type_local, surface_terrain, nature_mutation, commune, geom, raw)
                   SELECT :mid, :dt, :val, :tl, :st, :nat, commune, centroid, CAST(:raw AS jsonb)
                   FROM parcels WHERE id = :pid"""
            ),
            {"mid": idu, "dt": m.get("datemut"), "val": m.get("valeurfonc"), "tl": m.get("libtypbien"),
             "st": m.get("sterr"), "nat": m.get("libnatmut"), "pid": pid,
             "raw": json.dumps({"source": "DVF Région ODS", "idpar": idu})},
        )
        n += 1
    return n


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
