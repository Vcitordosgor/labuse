"""RETOURS-13 P6 — PROFIL ALTIMÉTRIQUE (coupe le long d'une ligne). Calcul LIVE, rien en base.

Source : RGE ALTI (le MÊME référentiel que la pente de la fiche). On lit d'abord le raster RGE ALTI
5 m EN BASE (``rgealti_mnt_5m``, SRID 2975) — chemin rapide en production. Là où la base n'a pas la
tuile (emprise non ingérée), on complète au service de calcul d'altitude IGN
(``connectors.rge_alti``) : même RGE ALTI, lecture pure, aucune écriture.

Vocabulaire aligné sur cartes.gouv (Vic s'y réfère) : distance, dénivelé positif, dénivelé négatif,
pente moyenne (= grade absolu moyen), plus forte pente.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE = "RGE ALTI 5 m (IGN)"
#: le service RGE ALTI renvoie des sentinelles négatives ; la fiche écarte <= -1000 (rge_alti.py).
_NODATA = -1000.0
_PAS_M = 5.0          # résolution RGE ALTI 5 m
_N_MAX = 250          # borne : une coupe reste légère


def _n_points(longueur_m: float) -> int:
    return max(2, min(_N_MAX, int(round(longueur_m / _PAS_M)) + 1))


def _echantillons(db: Session, wkt_2975: str, n: int) -> list[dict]:
    """n points réguliers le long de la ligne (WKT 2975) → [{dist_m, lon, lat, alt_m|None}].
    L'altitude vient du raster EN BASE ; None là où aucune tuile n'intersecte (ou no-data)."""
    rows = db.execute(text("""
        WITH l AS (SELECT ST_GeomFromText(:wkt, 2975) g),
             ll AS (SELECT g, GREATEST(ST_Length(g), 0.01) len FROM l),
             s AS (SELECT gs AS i, ST_LineInterpolatePoint(ll.g, gs::float / (:n - 1)) AS pt, ll.len
                   FROM ll, generate_series(0, :n - 1) gs)
        SELECT s.len * s.i / (:n - 1)          AS dist,
               ST_X(ST_Transform(s.pt, 4326))  AS lon,
               ST_Y(ST_Transform(s.pt, 4326))  AS lat,
               (SELECT ST_Value(r.rast, s.pt) FROM rgealti_mnt_5m r
                 WHERE ST_Intersects(r.rast, s.pt) LIMIT 1) AS z
        FROM s ORDER BY s.i
    """), {"wkt": wkt_2975, "n": n}).all()
    pts: list[dict] = []
    for dist, lon, lat, z in rows:
        alt = float(z) if (z is not None and float(z) > _NODATA) else None
        pts.append({"dist_m": float(dist), "lon": float(lon), "lat": float(lat), "alt_m": alt})
    return pts


def _completer_ign(pts: list[dict]) -> None:
    """Complète EN PLACE les points sans altitude base via le service IGN (même RGE ALTI). Silencieux
    en cas d'échec réseau : les points restent None → « relief non disponible »."""
    manquants = [p for p in pts if p["alt_m"] is None]
    if not manquants:
        return
    try:
        import httpx

        from ..connectors.rge_alti import fetch_elevations
        with httpx.Client(timeout=20, headers={"User-Agent": "labuse/1.0"}) as c:
            elevs = fetch_elevations([(p["lon"], p["lat"]) for p in manquants], client=c)
        for p, e in zip(manquants, elevs):
            if e is not None and float(e) > _NODATA:
                p["alt_m"] = float(e)
    except Exception:  # noqa: BLE001 — réseau IGN muet : on dégrade proprement
        pass


def stats_profil(points: list[dict]) -> dict | None:
    """PUR — statistiques de coupe à partir de ``[{dist_m, alt_m|None}]``.

    Pente moyenne = grade absolu moyen = (dénivelé positif + négatif) / distance échantillonnée
    valide (concorde avec la « pente moyenne » de cartes.gouv). Plus forte pente = max |Δalt/Δdist|
    entre deux points valides consécutifs. Renvoie ``None`` si moins de 2 points valides."""
    valides = [p for p in points if p.get("alt_m") is not None]
    if len(valides) < 2:
        return None
    dpos = dneg = dist_valide = 0.0
    pente_max = 0.0
    for a, b in zip(valides, valides[1:]):
        dd = b["dist_m"] - a["dist_m"]
        if dd <= 0:
            continue
        dh = b["alt_m"] - a["alt_m"]
        if dh >= 0:
            dpos += dh
        else:
            dneg += -dh
        dist_valide += dd
        s = abs(dh) / dd
        if s > pente_max:
            pente_max = s
    pente_moy = (dpos + dneg) / dist_valide if dist_valide > 0 else 0.0
    alts = [p["alt_m"] for p in valides]
    distance = points[-1]["dist_m"] - points[0]["dist_m"] if points else 0.0
    return {
        "distance_m": round(distance, 1),
        "denivele_positif_m": round(dpos, 1),
        "denivele_negatif_m": round(dneg, 1),
        "pente_moyenne_pct": round(pente_moy * 100, 1),
        "pente_max_pct": round(pente_max * 100, 1),
        "altitude_min_m": round(min(alts), 1),
        "altitude_max_m": round(max(alts), 1),
    }


def _profil(db: Session, wkt_2975: str, longueur: float, axe: str) -> dict:
    n = _n_points(longueur)
    pts = _echantillons(db, wkt_2975, n)
    if sum(1 for p in pts if p["alt_m"] is not None) < 2:
        _completer_ign(pts)   # emprise non ingérée en base → même RGE ALTI, service IGN
    st = stats_profil(pts)
    dispo = st is not None
    return {
        "disponible": dispo,
        "axe": axe,
        "source": SOURCE,
        "points": [{"dist_m": round(p["dist_m"], 1),
                    "alt_m": (round(p["alt_m"], 2) if p["alt_m"] is not None else None)} for p in pts],
        "motif": None if dispo else "Relief non disponible sur cette emprise (RGE ALTI absent en base et service IGN muet).",
        **(st or {}),
    }


def profil_parcelle(db: Session, idu: str) -> dict | None:
    """Coupe le long du PLUS GRAND AXE de la parcelle (ST_LongestLine). None = parcelle inconnue."""
    row = db.execute(text("""
        SELECT ST_AsText(ST_LongestLine(geom_2975, geom_2975)) AS wkt,
               ST_Length(ST_LongestLine(geom_2975, geom_2975)) AS len
        FROM parcels WHERE idu = :i
    """), {"i": idu}).first()
    if not row or not row.wkt:
        return None
    return _profil(db, row.wkt, float(row.len or 0.0), axe="parcelle")


def profil_ligne(db: Session, coords: list) -> dict:
    """Coupe le long d'une ligne DESSINÉE : ``coords = [[lon, lat], …]`` en 4326."""
    sommets = ", ".join(f"{float(lon)} {float(lat)}" for lon, lat in coords)
    row = db.execute(text("""
        WITH g AS (SELECT ST_Transform(ST_GeomFromText(:w, 4326), 2975) geom)
        SELECT ST_AsText(geom) AS wkt, ST_Length(geom) AS len FROM g
    """), {"w": f"LINESTRING({sommets})"}).first()
    return _profil(db, row.wkt, float(row.len or 0.0), axe="trace")
