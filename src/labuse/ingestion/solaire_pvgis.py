"""Lot 1 Habitat Solaire — baseline PVGIS : le score solaire gratuit sur toute l'île.

Pipeline en 4 temps, chacun repris là où il s'était arrêté (checkpoint = la base) :
1. build_grid   : grille de points ~400 m sur l'emprise terrestre (près des parcelles),
                  insérés dans solar_grid avec prod NULL (= « à récupérer »).
2. fetch        : PVcalc v5_3 par point (SARAH3, horizon topographique DEM intégré :
                  usehorizon=1 fait entrer cirques et remparts dans la donnée).
                  aspect=180 : plein NORD — hémisphère sud, versant optimal (+15 % vs sud).
3. interpolate  : IDW (4 plus proches voisins) → parcel_solar.prod_spec_kwh_kwc,
                  puis score_solaire = rang percentile île (0-100).
4. flags        : flag_topo_ombrage si prod de la parcelle < seuil (80 %) de la
                  médiane de SA commune — capte fonds de cirque et pieds de rempart.

Le run one-shot est LONG (~17 000 appels) : politesse 10 req/s (backoff sur 429/5xx),
relançable sans perte (`labuse solaire-pvgis`).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings, habitat_solaire
from .habitat_solaire_schema import ensure_schema

PVGIS_SOURCE = "pvgis_v5_3"


def _params() -> dict[str, Any]:
    return habitat_solaire()["pvgis"]


# ── 1. Grille ────────────────────────────────────────────────────────────────

def build_grid(session: Session, *, rebuild: bool = False) -> int:
    """Grille carrée (pas settings.pvgis_grid_step_m) sur l'emprise terrestre.

    « Terrestre » = centres de maille à moins d'un demi-pas d'au moins une parcelle
    cadastrale (le cadastre couvre l'île entière) — évite d'interroger l'océan.
    """
    ensure_schema(session)
    if rebuild:
        session.execute(text("DELETE FROM solar_grid"))
    existing = session.execute(text("SELECT count(*) FROM solar_grid")).scalar_one()
    if existing:
        return existing
    step = get_settings().pvgis_grid_step_m
    n = session.execute(text("""
        WITH grille AS (
          SELECT (ST_SquareGrid(:step,
                    ST_SetSRID(ST_Extent(geom_2975)::geometry, 2975))).geom AS cell
          FROM parcels
        ), centres AS (
          SELECT ST_Centroid(cell) AS pt FROM grille
        )
        INSERT INTO solar_grid (geom, source)
        SELECT ST_Transform(ST_SetSRID(pt, 2975), 4326), :src
        FROM centres c
        WHERE EXISTS (SELECT 1 FROM parcels p
                      WHERE ST_DWithin(p.geom_2975, c.pt, :halo))
        RETURNING 1
    """), {"step": step, "src": PVGIS_SOURCE, "halo": step * 0.75}).rowcount
    return n


# ── 2. Fetch PVGIS ───────────────────────────────────────────────────────────

async def _fetch_one(client: httpx.AsyncClient, url: str, lat: float, lon: float,
                     p: dict[str, Any]) -> tuple[float, float] | None:
    """(E_y kWh/kWc/an, H(i)_y kWh/m²/an) — None si le point reste inexploitable."""
    params = {
        "lat": round(lat, 5), "lon": round(lon, 5), "outputformat": "json",
        "peakpower": p["peakpower_kwc"], "loss": p["loss_pct"],
        "angle": p["angle_deg"], "aspect": p["aspect_deg"], "usehorizon": 1,
    }
    for attempt in range(5):
        try:
            r = await client.get(url, params=params, timeout=30)
        except httpx.HTTPError:
            await asyncio.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            tot = r.json()["outputs"]["totals"]["fixed"]
            return float(tot["E_y"]), float(tot.get("H(i)_y") or 0.0)
        if r.status_code in (429, 500, 502, 503, 504):
            await asyncio.sleep(2 ** attempt)
            continue
        return None  # 4xx franc (point hors couverture) : on n'insiste pas
    return None


async def _fetch_all(rows: list[tuple[int, float, float]], rps: float,
                     on_result) -> None:
    p = _params()
    url = f"https://re.jrc.ec.europa.eu/api/{get_settings().pvgis_version}/PVcalc"
    sem = asyncio.Semaphore(max(2, int(rps)))
    interval = 1.0 / rps
    next_slot = time.monotonic()

    async def one(gid: int, lon: float, lat: float) -> None:
        nonlocal next_slot
        async with sem:
            # cadence : un départ toutes les 1/rps s, quel que soit le temps de réponse
            now = time.monotonic()
            wait = next_slot - now
            next_slot = max(next_slot, now) + interval
            if wait > 0:
                await asyncio.sleep(wait)
            res = await _fetch_one(client, url, lat, lon, p)
            on_result(gid, res)

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(one(g, lo, la) for g, lo, la in rows))


def fetch_pending(session: Session, *, rps: float | None = None,
                  limit: int | None = None, log=print) -> dict[str, int]:
    """Récupère E_y pour tous les points encore NULL (reprise sur erreur incluse)."""
    rps = rps or get_settings().pvgis_rps
    rows = session.execute(text(
        "SELECT id, ST_X(geom), ST_Y(geom) FROM solar_grid"
        " WHERE prod_spec_kwh_kwc IS NULL ORDER BY id"
        + (" LIMIT :lim" if limit else "")), {"lim": limit} if limit else {}).all()
    done = failed = 0
    t0 = time.monotonic()

    def on_result(gid: int, res: tuple[float, float] | None) -> None:
        nonlocal done, failed
        if res is None:
            failed += 1
            return
        session.execute(text(
            "UPDATE solar_grid SET prod_spec_kwh_kwc = :e, ghi_kwh_m2_an = :h,"
            " fetched_at = now() WHERE id = :gid"),
            {"e": res[0], "h": res[1], "gid": gid})
        done += 1
        if done % 200 == 0:
            session.commit()  # checkpoint : une interruption ne perd que < 200 points
            log(f"  PVGIS {done}/{len(rows)} points ({done / (time.monotonic() - t0):.1f}/s)")

    asyncio.run(_fetch_all([(g, lo, la) for g, lo, la in rows], rps, on_result))
    session.commit()
    return {"points": len(rows), "ok": done, "echecs": failed}


# ── 3. Interpolation parcelles + score percentile ────────────────────────────

def interpolate(session: Session, log=print) -> dict[str, int]:
    """IDW 4-NN grille → parcelles, puis score_solaire = percentile île (0-100)."""
    n = session.execute(text("""
        INSERT INTO parcel_solar (idu, prod_spec_kwh_kwc, updated_at)
        SELECT p.idu, nn.prod, now()
        FROM parcels p
        CROSS JOIN LATERAL (
          SELECT sum(g.prod_spec_kwh_kwc / GREATEST(ST_Distance(g.geom::geography,
                       p.centroid::geography), 1.0))
                 / sum(1.0 / GREATEST(ST_Distance(g.geom::geography,
                       p.centroid::geography), 1.0)) AS prod
          FROM (
            SELECT prod_spec_kwh_kwc, geom FROM solar_grid
            WHERE prod_spec_kwh_kwc IS NOT NULL
            ORDER BY geom <-> p.centroid LIMIT 4
          ) g
        ) nn
        WHERE nn.prod IS NOT NULL
        ON CONFLICT (idu) DO UPDATE
          SET prod_spec_kwh_kwc = EXCLUDED.prod_spec_kwh_kwc, updated_at = now()
    """)).rowcount
    log(f"  interpolation : {n} parcelles")
    session.execute(text("""
        WITH ranked AS (
          SELECT idu, round(100 * percent_rank() OVER (ORDER BY prod_spec_kwh_kwc))::int AS s
          FROM parcel_solar WHERE prod_spec_kwh_kwc IS NOT NULL
        )
        UPDATE parcel_solar ps SET score_solaire = r.s
        FROM ranked r WHERE r.idu = ps.idu
    """))
    seuil = float(_params()["ombrage_seuil_mediane"])
    n_flag = session.execute(text("""
        WITH med AS (
          SELECT p.commune, percentile_cont(0.5) WITHIN GROUP (ORDER BY ps.prod_spec_kwh_kwc) AS m
          FROM parcel_solar ps JOIN parcels p ON p.idu = ps.idu
          WHERE ps.prod_spec_kwh_kwc IS NOT NULL GROUP BY p.commune
        )
        UPDATE parcel_solar ps SET flag_topo_ombrage = (ps.prod_spec_kwh_kwc < :seuil * med.m)
        FROM parcels p, med
        WHERE p.idu = ps.idu AND med.commune = p.commune
          AND ps.prod_spec_kwh_kwc IS NOT NULL
    """), {"seuil": seuil}).rowcount
    session.commit()
    return {"parcelles": n, "flags_ombrage_evalues": n_flag}


# ── 4. Sanity check physique (mandat : obligatoire) ──────────────────────────

def sanity_check(session: Session) -> dict[str, Any]:
    """Médiane côte Ouest (Saint-Paul, Saint-Leu) vs Est (Sainte-Rose, Salazie).

    Ouest ≤ Est = ingestion fausse (le mandat exige d'investiguer avant de continuer).
    """
    med = dict(session.execute(text("""
        SELECT p.commune, percentile_cont(0.5) WITHIN GROUP (ORDER BY ps.prod_spec_kwh_kwc)
        FROM parcel_solar ps JOIN parcels p ON p.idu = ps.idu
        WHERE p.commune IN ('Saint-Paul', 'Saint-Leu', 'Sainte-Rose', 'Salazie')
          AND ps.prod_spec_kwh_kwc IS NOT NULL
        GROUP BY p.commune
    """)).all())
    ouest = [med[c] for c in ("Saint-Paul", "Saint-Leu") if c in med]
    est = [med[c] for c in ("Sainte-Rose", "Salazie") if c in med]
    ok = bool(ouest and est) and min(ouest) > max(est)
    return {"medianes": {k: round(v, 1) for k, v in med.items()}, "ouest_sup_est": ok}


def run(session: Session, *, rebuild: bool = False, rps: float | None = None,
        limit: int | None = None, log=print) -> dict[str, Any]:
    """Pipeline complet, relançable (chaque étape reprend l'existant)."""
    n_grid = build_grid(session, rebuild=rebuild)
    session.commit()
    log(f"solar_grid : {n_grid} points")
    stats = fetch_pending(session, rps=rps, limit=limit, log=log)
    log(f"PVGIS : {stats}")
    manquants = session.execute(text(
        "SELECT count(*) FROM solar_grid WHERE prod_spec_kwh_kwc IS NULL")).scalar_one()
    out: dict[str, Any] = {"grid": n_grid, **stats, "restants": manquants}
    if manquants and not limit:
        log(f"⚠ {manquants} points sans donnée — relancer `labuse solaire-pvgis`")
    # Interpolation quand la grille est (quasi) complète — quelques points côtiers
    # peuvent rester hors couverture SARAH3 sans invalider l'île.
    if limit is None and manquants <= max(10, int(0.01 * n_grid)):
        out.update(interpolate(session, log=log))
        out["sanity"] = sanity_check(session)
        log(f"sanity Ouest>Est : {out['sanity']}")
    return out
