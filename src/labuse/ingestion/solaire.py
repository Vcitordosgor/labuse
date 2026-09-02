"""SOLAIRE M1 — reconstruction du builder `parcel_solar` depuis les sources.

Le builder d'origine est parti avec le spin-off « Plein Sud » ; on le réécrit au standard du dépôt,
à partir des mêmes méthodes (archive `origin/spinoff/vues-solaire`), avec les arbitrages Phase 1 (Vic) :

  · MENSUEL EN DB (décision « option B ») : PVGIS PVcalc renvoie 12 E_m + l'annuel E_y ; on stocke le
    mensuel dans solar_grid puis parcel_solar (prod_mensuel jsonb + mois_optimal). PAS de GeoTIFF sur
    disque (ni GDAL ni rasterio dans l'environnement) — même résultat mensuel, sans fichier raster.
  · ORIENTATION = azimut du BÂTI (Estimé, ST_OrientedEnvelope) — PAS l'aspect RGE ALTI (aucun MNT
    altimétrique en base, seulement le raster de pente). L'outil garde le libellé « Estimé ».
  · SCHÉMA 14 colonnes : les proxys morts sont abandonnés (pv_existant, conso/facture estimées,
    flag_amiante, repowering).

Sources : PVGIS PVcalc v5.3 (SARAH3 + usehorizon=1, gratuit sans clé, aspect 180° = plein nord) ·
bâti `spatial_layers kind='batiment'` (azimut) · cascade `abf` (flag_abf) · `parcel_vegetation`
(flag_ombrage_vegetal) · Filosofi 200 m + `commune_insee_logement` + `dvf_mutations_parcelle` (proba).

Idempotent et RÉSUMABLE : le checkpoint est la base (solar_grid.prod_spec NULL = point à récupérer).
CLI : `labuse solaire-build`.
"""
from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config
from .. import runs  # S3 : run servi relu à la requête

PVGIS_SOURCE = "pvgis_v5_3"
PVGIS_URL = "https://re.jrc.ec.europa.eu/api/{v}/PVcalc"


def _cfg() -> dict[str, Any]:
    return load_yaml_config("solaire")


def source_millesime() -> str:
    """Millésime porté sur chaque ligne — SARAH3 est le référentiel, le relevé date le run."""
    return f"PVGIS {_cfg()['pvgis']['version']} · SARAH3 · relevé {date.today().isoformat()}"


# ── Schéma (idempotent + migration de l'existant vers les 14 colonnes) ────────

def ensure_schema(session: Session) -> None:
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS solar_grid (
          id serial PRIMARY KEY,
          geom geometry(Point, 4326) NOT NULL,
          prod_spec_kwh_kwc double precision,
          ghi_kwh_m2_an double precision,
          prod_mensuel jsonb,                       -- 12 E_m (kWh/kWc/mois)
          source varchar(32) NOT NULL,
          fetched_at timestamptz DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS solar_grid_geom_gix ON solar_grid USING gist (geom);
        CREATE TABLE IF NOT EXISTS parcel_solar (
          idu varchar(14) PRIMARY KEY REFERENCES parcels (idu),
          prod_spec_kwh_kwc double precision,
          ghi_kwh_m2_an double precision,
          prod_mensuel jsonb,
          mois_optimal smallint,
          score_solaire integer,
          azimut_bati_deg double precision,
          azimut_confiance varchar(8),
          flag_abf boolean,
          flag_topo_ombrage boolean,
          flag_ombrage_vegetal boolean,
          proba_proprio_occupant integer,
          source_millesime text,
          updated_at timestamptz DEFAULT now()
        );
    """))
    # migration d'un parcel_solar/solar_grid pré-existant (données gelées 11/07/2026) vers le schéma cible :
    for col, typ in (("ghi_kwh_m2_an", "double precision"), ("prod_mensuel", "jsonb"),
                     ("mois_optimal", "smallint"), ("flag_ombrage_vegetal", "boolean"),
                     ("source_millesime", "text")):
        session.execute(text(f"ALTER TABLE parcel_solar ADD COLUMN IF NOT EXISTS {col} {typ}"))
    session.execute(text("ALTER TABLE solar_grid ADD COLUMN IF NOT EXISTS prod_mensuel jsonb"))
    for dead in ("flag_amiante", "conso_est_kwh_an", "facture_est_eur_mois", "pv_existant", "repowering"):
        session.execute(text(f"ALTER TABLE parcel_solar DROP COLUMN IF EXISTS {dead}"))
    session.commit()


# ── 1. Grille PVGIS (ST_SquareGrid sur l'emprise cadastrale terrestre) ────────

def build_grid(session: Session, *, rebuild: bool = False) -> int:
    if rebuild:
        session.execute(text("DELETE FROM solar_grid"))
        session.commit()
    existing = session.execute(text("SELECT count(*) FROM solar_grid")).scalar_one()
    if existing:
        return existing
    step = float(_cfg()["pvgis"]["grid_step_m"])
    n = session.execute(text("""
        WITH grille AS (
          SELECT (ST_SquareGrid(:step,
                    ST_SetSRID(ST_Extent(geom_2975)::geometry, 2975))).geom AS cell
          FROM parcels
        ), centres AS (SELECT ST_Centroid(cell) AS pt FROM grille)
        INSERT INTO solar_grid (geom, source)
        SELECT ST_Transform(ST_SetSRID(pt, 2975), 4326), :src
        FROM centres c
        WHERE EXISTS (SELECT 1 FROM parcels p WHERE ST_DWithin(p.geom_2975, c.pt, :halo))
    """), {"step": step, "src": PVGIS_SOURCE, "halo": step * 0.75}).rowcount
    session.commit()
    return n


# ── 2. Fetch PVGIS (annuel E_y + GHI + 12 E_m), résumable, rate-limité ────────

async def _fetch_one(client: httpx.AsyncClient, url: str, lat: float, lon: float,
                     p: dict) -> tuple[float, float, list[float]] | None:
    params = {"lat": round(lat, 5), "lon": round(lon, 5), "outputformat": "json",
              "peakpower": p["peakpower_kwc"], "loss": p["loss_pct"],
              "angle": p["angle_deg"], "aspect": p["aspect_deg"], "usehorizon": 1}
    for attempt in range(5):
        try:
            r = await client.get(url, params=params, timeout=30)
        except httpx.HTTPError:
            await asyncio.sleep(2 ** attempt)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(2 ** attempt)
            continue
        if r.status_code != 200:
            return None
        out = r.json()["outputs"]
        tot = out["totals"]["fixed"]
        months = [float(m["E_m"]) for m in sorted(out.get("monthly", {}).get("fixed", []),
                                                  key=lambda m: m["month"])]
        return float(tot["E_y"]), float(tot.get("H(i)_y") or 0.0), months
    return None


async def _fetch_all(rows: list[tuple[int, float, float]], rps: float, url: str, p: dict,
                     on_result) -> None:
    sem = asyncio.Semaphore(max(2, int(rps)))
    interval = 1.0 / rps
    next_slot = time.monotonic()

    async def one(gid: int, lon: float, lat: float) -> None:
        nonlocal next_slot
        async with sem:
            now = time.monotonic()
            wait = next_slot - now
            next_slot = max(next_slot, now) + interval
            if wait > 0:
                await asyncio.sleep(wait)
            on_result(gid, await _fetch_one(client, url, lat, lon, p))

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(one(g, lo, la) for g, lo, la in rows))


def fetch_pending(session: Session, *, rps: float | None = None,
                  limit: int | None = None, log=print) -> dict[str, int]:
    p = _cfg()["pvgis"]
    rps = rps or float(p["rps"])
    url = PVGIS_URL.format(v=p["version"])
    rows = session.execute(text(
        "SELECT id, ST_X(geom), ST_Y(geom) FROM solar_grid WHERE prod_spec_kwh_kwc IS NULL ORDER BY id"
        + (" LIMIT :lim" if limit else "")), {"lim": limit} if limit else {}).all()
    done = failed = 0
    t0 = time.monotonic()

    def on_result(gid: int, res: tuple[float, float, list[float]] | None) -> None:
        nonlocal done, failed
        if res is None:
            failed += 1
            return
        import json as _j
        session.execute(text(
            "UPDATE solar_grid SET prod_spec_kwh_kwc = :e, ghi_kwh_m2_an = :h,"
            " prod_mensuel = CAST(:m AS jsonb), fetched_at = now() WHERE id = :gid"),
            {"e": res[0], "h": res[1], "m": _j.dumps(res[2]), "gid": gid})
        done += 1
        if done % 200 == 0:
            session.commit()   # checkpoint : une interruption ne perd que < 200 points
            log(f"  PVGIS {done}/{len(rows)} points ({done / (time.monotonic() - t0):.1f}/s)")

    asyncio.run(_fetch_all([(g, lo, la) for g, lo, la in rows], rps, url, p, on_result))
    session.commit()
    return {"points": len(rows), "ok": done, "echecs": failed}


# ── 3. Interpolation parcelles (IDW annuel + GHI · mensuel/mois_optimal · score · ombrage topo) ──

def interpolate(session: Session, log=print) -> dict[str, int]:
    n = session.execute(text("""
        INSERT INTO parcel_solar (idu, prod_spec_kwh_kwc, ghi_kwh_m2_an, updated_at)
        SELECT p.idu, nn.prod, nn.ghi, now()
        FROM parcels p
        CROSS JOIN LATERAL (
          SELECT sum(g.prod_spec_kwh_kwc / d) / sum(1.0 / d) AS prod,
                 sum(g.ghi_kwh_m2_an   / d) / sum(1.0 / d) AS ghi
          FROM (
            SELECT prod_spec_kwh_kwc, ghi_kwh_m2_an,
                   GREATEST(ST_Distance(geom::geography, p.centroid::geography), 1.0) AS d
            FROM solar_grid WHERE prod_spec_kwh_kwc IS NOT NULL
            ORDER BY geom <-> p.centroid LIMIT 4
          ) g
        ) nn
        WHERE nn.prod IS NOT NULL
        ON CONFLICT (idu) DO UPDATE
          SET prod_spec_kwh_kwc = EXCLUDED.prod_spec_kwh_kwc,
              ghi_kwh_m2_an = EXCLUDED.ghi_kwh_m2_an, updated_at = now()
    """)).rowcount
    log(f"  interpolation IDW : {n} parcelles")
    # mensuel + mois_optimal : profil du point de grille LE PLUS PROCHE (le profil varie peu ; seule
    # l'amplitude annuelle mérite l'IDW). mois_optimal = index (1-12) du E_m max.
    session.execute(text("""
        UPDATE parcel_solar ps SET prod_mensuel = nn.pm, mois_optimal = nn.mois
        FROM parcels p, LATERAL (
          SELECT g.prod_mensuel AS pm,
                 (SELECT ord FROM jsonb_array_elements(g.prod_mensuel) WITH ORDINALITY AS a(val, ord)
                  ORDER BY val::float DESC LIMIT 1) AS mois
          FROM solar_grid g
          WHERE g.prod_mensuel IS NOT NULL
          ORDER BY g.geom <-> p.centroid LIMIT 1
        ) nn
        WHERE p.idu = ps.idu AND ps.prod_spec_kwh_kwc IS NOT NULL
    """))
    session.execute(text("""
        WITH ranked AS MATERIALIZED (
          SELECT idu, round(100 * percent_rank() OVER (ORDER BY prod_spec_kwh_kwc))::int AS s
          FROM parcel_solar WHERE prod_spec_kwh_kwc IS NOT NULL
        )
        UPDATE parcel_solar ps SET score_solaire = r.s FROM ranked r WHERE r.idu = ps.idu
    """))
    seuil = float(_cfg()["pvgis"]["ombrage_seuil_mediane"])
    n_flag = session.execute(text("""
        WITH med AS MATERIALIZED (
          SELECT p.commune, percentile_cont(0.5) WITHIN GROUP (ORDER BY ps.prod_spec_kwh_kwc) AS m
          FROM parcel_solar ps JOIN parcels p ON p.idu = ps.idu
          WHERE ps.prod_spec_kwh_kwc IS NOT NULL GROUP BY p.commune
        )
        UPDATE parcel_solar ps SET flag_topo_ombrage = (ps.prod_spec_kwh_kwc < :seuil * med.m)
        FROM parcels p, med
        WHERE p.idu = ps.idu AND med.commune = p.commune AND ps.prod_spec_kwh_kwc IS NOT NULL
    """), {"seuil": seuil}).rowcount
    session.commit()
    return {"parcelles": n, "flags_ombrage_topo": n_flag}


# ── 4. Azimut du bâti (Estimé — ST_OrientedEnvelope du bâti principal) ────────

def compute_azimut(session: Session) -> int:
    emin = float(_cfg()["flags"]["azimut_elongation_min"])
    n = session.execute(text("""
        WITH pairs AS (
          SELECT p.idu, sl.geom_2975 AS g,
                 ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975)) AS inter
          FROM parcels p
          JOIN spatial_layers sl ON sl.kind = 'batiment' AND ST_Intersects(sl.geom_2975, p.geom_2975)
        ),
        bati AS (SELECT idu, g, inter, row_number() OVER (PARTITION BY idu ORDER BY inter DESC) AS rn FROM pairs),
        env AS (SELECT idu, ST_OrientedEnvelope(g) AS e FROM bati WHERE rn = 1 AND inter >= 20),
        pts AS (
          SELECT idu, ST_PointN(ST_ExteriorRing(e), 1) AS a, ST_PointN(ST_ExteriorRing(e), 2) AS b,
                 ST_PointN(ST_ExteriorRing(e), 3) AS c
          FROM env WHERE ST_GeometryType(e) = 'ST_Polygon'
        ),
        az AS (
          SELECT idu,
                 CASE WHEN ST_Distance(a, b) >= ST_Distance(b, c)
                      THEN degrees(ST_Azimuth(a, b)) ELSE degrees(ST_Azimuth(b, c)) END AS azimut,
                 GREATEST(ST_Distance(a, b), ST_Distance(b, c))
                   / NULLIF(LEAST(ST_Distance(a, b), ST_Distance(b, c)), 0) AS elong
          FROM pts
        )
        UPDATE parcel_solar ps
          SET azimut_bati_deg = round((az.azimut::numeric % 180.0), 1),
              azimut_confiance = CASE WHEN az.elong > :emin THEN 'haute' ELSE 'basse' END,
              updated_at = now()
        FROM az WHERE az.idu = ps.idu AND az.azimut IS NOT NULL
    """), {"emin": emin}).rowcount
    session.commit()
    return n


# ── 5. flag_abf (cascade, périmètre ABF = result UNKNOWN au run servi) ────────

def compute_flag_abf(session: Session) -> int:
    n = session.execute(text("""
        WITH abf AS (
          SELECT p.idu, bool_or(cr.result = 'UNKNOWN') AS in_abf
          FROM parcels p
          JOIN dryrun_cascade_results cr
            ON cr.parcel_id = p.id AND cr.run_label = :run AND cr.layer_name = 'abf'
          GROUP BY p.idu
        )
        UPDATE parcel_solar ps SET flag_abf = abf.in_abf, updated_at = now()
        FROM abf WHERE abf.idu = ps.idu
    """), {"run": runs.current()}).rowcount
    session.commit()
    return n


# ── 6. flag_ombrage_vegetal (canopée sur le bâti, parcel_vegetation) ──────────

def compute_flag_ombrage_vegetal(session: Session) -> int:
    seuil = float(_cfg()["flags"]["ombrage_vegetal_canopee_pct_min"])
    n = session.execute(text("""
        UPDATE parcel_solar ps SET flag_ombrage_vegetal = (v.canopee_bati_pct >= :seuil), updated_at = now()
        FROM parcel_vegetation v
        WHERE v.idu = ps.idu AND v.canopee_bati_pct IS NOT NULL
    """), {"seuil": seuil}).rowcount
    session.commit()
    return n


# ── 7. proba propriétaire-occupant (Estimé statistique, jamais nominatif) ─────

def compute_proba(session: Session, *, aujourd_hui: date | None = None) -> int:
    f = _cfg()["flags"]
    ref = aujourd_hui or date.today()   # heure LOCALE (leçon QA : pas CURRENT_DATE)
    depuis = ref - timedelta(days=int(f["proprio_bonus_fenetre_mois"]) * 30)
    n = session.execute(text("""
        WITH base AS (
          SELECT p.idu,
                 COALESCE(
                   (SELECT 100.0 * fc.men_prop / NULLIF(fc.men, 0)
                    FROM filosofi_carreaux_200m fc
                    WHERE ST_Contains(fc.geom, ST_Transform(p.centroid, 2975)) AND fc.men > 0 LIMIT 1),
                   (SELECT cil.proprietaires_pct FROM commune_insee_logement cil WHERE cil.insee = left(p.idu, 5))
                 ) AS pct,
                 EXISTS (SELECT 1 FROM dvf_mutations_parcelle d
                         WHERE d.id_parcelle = p.idu AND d.type_local = 'Maison'
                           AND d.date_mutation >= :depuis) AS mut_recente
          FROM parcels p
        )
        UPDATE parcel_solar ps
          SET proba_proprio_occupant =
                LEAST(:pmax, GREATEST(:pmin,
                  round(COALESCE(base.pct, :pmin) + CASE WHEN base.mut_recente THEN :bonus ELSE 0 END)))::int,
              updated_at = now()
        FROM base WHERE base.idu = ps.idu AND base.pct IS NOT NULL
    """), {"depuis": depuis, "pmin": int(f["proprio_min"]), "pmax": int(f["proprio_max"]),
           "bonus": int(f["proprio_bonus_mutation_pts"])}).rowcount
    session.commit()
    return n


def stamp_millesime(session: Session) -> None:
    session.execute(text("UPDATE parcel_solar SET source_millesime = :m WHERE prod_spec_kwh_kwc IS NOT NULL"),
                    {"m": source_millesime()})
    session.commit()


# ── Orchestrateur ─────────────────────────────────────────────────────────────

def run(session: Session, *, rps: float | None = None, rebuild_grid: bool = False,
        skip_fetch: bool = False, fetch_limit: int | None = None, log=print) -> dict[str, Any]:
    ensure_schema(session)
    g = build_grid(session, rebuild=rebuild_grid)
    log(f"grille : {g} points")
    if not skip_fetch:
        log(f"PVGIS fetch (rps={rps or _cfg()['pvgis']['rps']})…")
        log(f"  {fetch_pending(session, rps=rps, limit=fetch_limit, log=log)}")
    out: dict[str, Any] = {"grille": g}
    out["interpolation"] = interpolate(session, log=log)
    out["azimut"] = compute_azimut(session)
    out["flag_abf"] = compute_flag_abf(session)
    out["flag_ombrage_vegetal"] = compute_flag_ombrage_vegetal(session)
    out["proba"] = compute_proba(session)
    stamp_millesime(session)
    out["millesime"] = source_millesime()
    log(f"terminé : {out}")
    return out
