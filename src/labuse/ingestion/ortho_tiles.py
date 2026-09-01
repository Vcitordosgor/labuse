"""Wave Détection Ortho, Lot 2 — infrastructure tuiles + acquisition ortho CIBLÉE.

On ne traite pas l'île : uniquement les tuiles 512×512 m intersectant au moins une
emprise bâtie BD TOPO OU un polygone parkings_aper (océan/forêts/remparts ignorés).
Source : BD ORTHO® 20 cm via WMS Géoplateforme (data.geopf.fr, gratuit sans clé,
Licence Ouverte — attribution IGN). **Millésime 974 = 2025** (fiche IGN des dates de
prise de vue) — l'âge de l'image est l'âge de la vérité terrain. Choix WMS (vs dalles
JP2 départementales) : 5 041 tuiles × ~1,2 Mo ≈ 6 Go, streaming ciblé plus léger que
~50-80 Go de dalles temporaires.

Acquisition : EPSG:2975 natif (tuiles carrées exactes), 2560×2560 px (20 cm),
cache disque data/ortho_tiles/{tile_id}.jpg, reprise par tile_id (fichier présent +
taille > 0 = acquis). Journal : ortho_tiles + ingestion_runs.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import _repo_root, load_yaml_config

#: CONNEXIONS-2 Lot 6.4 — repli SEUL. Le millésime servi n'est plus figé ici : il est LU dans
#: `data_sources.source_millesime` (table de millésimes CENTRALE, comme toutes les autres sources —
#: fini le « millésime ortho en dur » du rapport). Cette constante ne sert plus que d'amorce quand la
#: table n'a pas encore de ligne BD ORTHO (base neuve / test), jamais comme vérité concurrente.
MILLESIME = "2025"  # repli — BD ORTHO 974 (fiche IGN dates de prises de vues, juil. 2026)


def millesime_servi(db: Session) -> str:
    """Millésime ortho SERVI = `data_sources.source_millesime` de la source BD ORTHO (centralisé,
    même point que /sources, fiche et couches). Repli sur MILLESIME si la ligne n'existe pas encore."""
    try:
        v = db.execute(text(
            "SELECT source_millesime FROM data_sources "
            "WHERE (name ILIKE '%ortho%' OR name ILIKE '%BD ORTHO%') "
            "  AND source_millesime IS NOT NULL "
            "ORDER BY (name ILIKE '%BD ORTHO%') DESC LIMIT 1")).scalar()
    except Exception:  # noqa: BLE001 — un souci de lecture ne casse pas les badges ortho
        v = None
    return str(v) if v else MILLESIME

DDL = """
CREATE TABLE IF NOT EXISTS ortho_tiles (
  tile_id       varchar(24) PRIMARY KEY,        -- '<xmin>_<ymin>' en EPSG:2975
  geom          geometry(Polygon, 2975) NOT NULL,
  millesime     varchar(8),
  acquise_at    timestamptz,                    -- image en cache
  traite_at     timestamptz,                    -- passée par la détection (Lot 3/4)
  nb_detections integer
);
CREATE INDEX IF NOT EXISTS ortho_tiles_geom_gix ON ortho_tiles USING gist (geom);
"""


def _cfg() -> dict[str, Any]:
    return load_yaml_config("detection_ortho")["tuiles"]


def ortho_png_parcelle(session: Session, idu: str, *, taille_px: int = 384, marge_m: int = 25) -> bytes | None:
    """RATTACHEMENT-V2 (Lot 2) — vignette PNG ortho (BD ORTHO 20 cm IGN, EPSG:2975) cadrée sur la
    parcelle `idu`, pour l'écran « Instruire » du Radar. Le paquet pige/ reste sans réseau (doctrine) :
    la requête WMS vit ICI, dans l'ingestion imagerie qui utilise déjà la Géoplateforme. Ne lève jamais."""
    r = session.execute(text(
        "SELECT ST_XMin(g) x0, ST_YMin(g) y0, ST_XMax(g) x1, ST_YMax(g) y1 "
        "FROM (SELECT ST_Envelope(ST_Buffer(geom_2975, :m)) g FROM parcels WHERE idu = :i) q"),
        {"i": idu, "m": marge_m}).mappings().first()
    if not r or r["x0"] is None:
        return None
    cfg = _cfg()
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": cfg["wms_layer"],
        "STYLES": "", "CRS": "EPSG:2975", "BBOX": f"{r['x0']},{r['y0']},{r['x1']},{r['y1']}",
        "WIDTH": str(taille_px), "HEIGHT": str(taille_px), "FORMAT": "image/png",
    }
    try:
        with httpx.Client(headers={"User-Agent": "labuse/radar-ortho"}) as cl:
            resp = cl.get(cfg["wms_url"] + "/wms", params=params, timeout=30)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            return resp.content
    except httpx.HTTPError:
        return None
    return None


def cache_dir() -> Path:
    p = Path(_cfg()["cache_dir"])
    p = p if p.is_absolute() else _repo_root() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_grid(session: Session) -> int:
    """Tuiles à traiter = bâti OU parking. Idempotent (INSERT des manquantes)."""
    session.execute(text(DDL))
    taille = int(_cfg()["taille_m"])
    return session.execute(text("""
        WITH g AS (
          SELECT (ST_SquareGrid(:taille,
                    ST_SetSRID(ST_Extent(geom_2975)::geometry, 2975))).geom AS cell
          FROM parcels
        ),
        utiles AS (
          SELECT cell FROM g
          WHERE EXISTS (SELECT 1 FROM spatial_layers sl WHERE sl.kind = 'batiment'
                          AND sl.geom_2975 && g.cell AND ST_Intersects(sl.geom_2975, g.cell))
             OR EXISTS (SELECT 1 FROM parkings_aper pk
                        WHERE pk.geom_2975 && g.cell AND ST_Intersects(pk.geom_2975, g.cell))
        )
        INSERT INTO ortho_tiles (tile_id, geom, millesime)
        SELECT round(ST_XMin(cell))::bigint || '_' || round(ST_YMin(cell))::bigint,
               ST_SetSRID(cell, 2975), :mil
        FROM utiles
        ON CONFLICT (tile_id) DO NOTHING
    """), {"taille": taille, "mil": millesime_servi(session)}).rowcount


def tile_path(tile_id: str) -> Path:
    return cache_dir() / f"{tile_id}.jpg"


async def _fetch_tile(client: httpx.AsyncClient, cfg: dict, tile_id: str,
                      dest: Path | None = None) -> bool:
    """`dest` : chemin cible optionnel (mandat ANC & Végétation : cache IRC séparé) —
    par défaut le cache RVB historique, comportement inchangé."""
    xmin, ymin = (int(v) for v in tile_id.split("_"))
    taille, px = int(cfg["taille_m"]), int(cfg["pixels"])
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": cfg["wms_layer"], "STYLES": "", "CRS": "EPSG:2975",
        "BBOX": f"{xmin},{ymin},{xmin + taille},{ymin + taille}",
        "WIDTH": px, "HEIGHT": px, "FORMAT": "image/jpeg",
    }
    for attempt in range(4):
        try:
            r = await client.get(cfg["wms_url"] + "/wms", params=params, timeout=60)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                (dest or tile_path(tile_id)).write_bytes(r.content)
                return True
        except httpx.HTTPError:
            pass
        await asyncio.sleep(2 ** attempt)
    return False


def acquire(session: Session, *, limit: int | None = None, log=print) -> dict[str, int]:
    """Télécharge les tuiles manquantes (cache + colonne acquise_at = checkpoint)."""
    cfg = _cfg()
    rows = [t for (t,) in session.execute(text(
        "SELECT tile_id FROM ortho_tiles WHERE acquise_at IS NULL ORDER BY tile_id"
        + (" LIMIT :lim" if limit else "")), {"lim": limit} if limit else {}).all()]
    # reprise : fichiers déjà en cache (run interrompu avant l'UPDATE)
    deja = [t for t in rows if tile_path(t).exists() and tile_path(t).stat().st_size > 0]
    a_faire = [t for t in rows if t not in set(deja)]
    ok_ids: list[str] = list(deja)
    echecs = 0
    t0 = time.monotonic()

    async def main() -> None:
        nonlocal echecs
        sem = asyncio.Semaphore(int(cfg["concurrence"]))

        async def one(tid: str) -> None:
            nonlocal echecs
            async with sem:
                if await _fetch_tile(client, cfg, tid):
                    ok_ids.append(tid)
                    n = len(ok_ids)
                    if n % 200 == 0:
                        log(f"  ortho {n}/{len(rows)} tuiles"
                            f" ({(n - len(deja)) / max(1e-9, time.monotonic() - t0):.1f}/s)")
                else:
                    echecs += 1

        async with httpx.AsyncClient(headers={"User-Agent": "labuse/ortho-974"}) as client:
            await asyncio.gather(*(one(t) for t in a_faire))

    asyncio.run(main())
    for i in range(0, len(ok_ids), 500):
        session.execute(text(
            "UPDATE ortho_tiles SET acquise_at = now() WHERE tile_id = ANY(:ids)"),
            {"ids": ok_ids[i:i + 500]})
        session.commit()
    return {"demandees": len(rows), "acquises": len(ok_ids), "echecs": echecs}


def purge_cache(keep_tables: bool = True) -> int:
    """Fin de run (contrainte disque) : on garde les TABLES, pas les images."""
    n = 0
    for f in cache_dir().glob("*.jpg"):
        f.unlink()
        n += 1
    return n
