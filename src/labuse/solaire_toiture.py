"""RETOURS-13 R31 — NATURE DE LA TOITURE (simple / double pente) depuis le LiDAR HD IGN.

Disponibilité VÉRIFIÉE le 05/09/2026 : la Géoplateforme diffuse les modèles dérivés du LiDAR HD
SUR LE 974 — couche WMS GeoTIFF `IGNF_LIDAR-HD_MNH_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S`
(MNH = hauteur au-dessus du sol, MNS−MNT déjà calculé par l'IGN, 50 cm, EPSG:2975, Licence
Ouverte). Valeurs réelles mesurées sur Saint-Denis/Saint-Paul (4-70 m).

Méthode « plans de toiture » (prototype qa/solaire/toiture_probe.py) : pente + orientation par
pixel sur l'emprise bâtie (BD TOPO), histogramme circulaire d'orientation lissé, pics = pans.
  · < 15 % de pixels pentus → toit PLAT / terrasse ;
  · 1 pic → MONOPENTE ; 2 pics opposés → DOUBLE PENTE ;
  · 2 pics perpendiculaires ou 3+ → CROUPE / COMPLEXE (toit en L, 4 pans…).

SEUIL DE CONFIANCE (RETOURS-14 S11) : la confiance = masse de l'histogramme expliquée par les
pics retenus (±1 secteur). Calibrée À L'ŒIL contre l'ortho : 0 faux au seuil sur les 20 premiers
bâtiments, CONFIRMÉ sur 50 (les 2 faux restants — croupe et bâtiment en L lus « double pente » —
tombent à 0,672 et 0,698, sous le seuil 0,70). Au seuil : 18/50 classés (36 %), 0 faux.
Sous le seuil, le verdict n'est JAMAIS servi : « non déterminée (LiDAR) » (le verdict brut reste
en cache pour mesure). STATUT : **Dérivé** — jamais servi comme un fait certain.

Calcul À LA DEMANDE (l'outil Solaire affiche une parcelle → une requête WMS ~1 s), mis en
CACHE (table toiture_lidar) — aucune ingestion de masse, aucun recalcul du run solaire gelé.
"""
from __future__ import annotations

import json
import logging

import httpx
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse")

WMS = "https://data.geopf.fr/wms-r/wms"
MNH_LAYER = "IGNF_LIDAR-HD_MNH_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S"
RES = 0.5   # m/pixel (natif LiDAR HD MNx)

# S11 — seuil de confiance : 0 faux à l'œil sur 20 bâtiments, confirmé sur 50 (voir docstring).
SEUIL_CONFIANCE = 0.70

# RETOURS-15 U5 — TROIS ÉTATS DISTINCTS à l'écran, jamais confondus :
#   servi (« simple pente ») · sous le seuil (« non déterminée — pans non nets ») ·
#   erreur technique (« non calculée — LiDAR indisponible », cause au journal serveur).
# Un échec technique ne se déguise JAMAIS en absence de donnée.
VERDICT_LABELS = {
    "plat": "toit plat / terrasse",
    "monopente": "simple pente (monopente)",
    "double_pente": "double pente",
    "croupe_complexe": "croupe ou toit complexe (3 pans et plus)",
    "indetermine": "non déterminée — emprise trop petite ou signal brouillé",
    "non_determine": "non déterminée — pans non nets (sous le seuil de confiance)",
    "indisponible": "non calculée — LiDAR indisponible",
}
VERDICT_COURTS = {
    "plat": "plat / terrasse",
    "monopente": "simple pente",
    "double_pente": "double pente",
    "croupe_complexe": "croupe / complexe",
    "indetermine": "non déterminée — signal brouillé",
    "non_determine": "non déterminée — pans non nets",
    "indisponible": "non calculée (LiDAR indisponible)",
}


def payload_indisponible(cause: str) -> dict:
    """État 3 (U5) — échec TECHNIQUE (WMS muet, dépendance absente…) : l'écran le dit, la cause
    va au journal serveur. Rien n'est mis en cache (le prochain appel retente)."""
    log.error("toiture_lidar : non calculée — LiDAR indisponible (%s)", cause)
    return {
        "verdict": "indisponible",
        "libelle": VERDICT_LABELS["indisponible"],
        "libelle_court": VERDICT_COURTS["indisponible"],
        "pente_mediane_deg": None, "pans_orientation_deg": [], "part_pentue": None,
        "confiance": None, "seuil": SEUIL_CONFIANCE, "statut": "Dérivé",
        "methode": ("Le calcul n'a pas pu être fait (LiDAR HD IGN injoignable ou erreur "
                    "technique) — ce n'est PAS une absence de donnée. Détail au journal serveur ; "
                    "réessayez en rouvrant la fiche."),
    }


def ensure_table(session: Session) -> None:
    session.execute(text(
        """CREATE TABLE IF NOT EXISTS toiture_lidar (
             idu varchar(14) PRIMARY KEY,
             verdict varchar(24) NOT NULL,
             pente_mediane_deg real,
             pans_orientation_deg jsonb,
             part_pentue real,
             computed_at timestamptz NOT NULL DEFAULT now())"""))
    # S11 — la confiance est stockée pour appliquer le seuil ; les lignes d'avant-seuil (sans
    # confiance) sont purgées une fois : elles se recalculent à la demande.
    session.execute(text("ALTER TABLE toiture_lidar ADD COLUMN IF NOT EXISTS confiance real"))
    session.execute(text("DELETE FROM toiture_lidar WHERE confiance IS NULL"))


def _fetch_mnh(bbox: tuple[float, float, float, float]) -> "np.ndarray | str":
    """MNH LiDAR par WMS. En échec technique, retourne la CAUSE (str) — jamais un None muet (U5)."""
    w = max(8, int((bbox[2] - bbox[0]) / RES))
    h = max(8, int((bbox[3] - bbox[1]) / RES))
    try:
        r = httpx.get(WMS, params={
            "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": MNH_LAYER,
            "CRS": "EPSG:2975", "BBOX": ",".join(str(v) for v in bbox),
            "WIDTH": w, "HEIGHT": h, "FORMAT": "image/geotiff", "STYLES": ""}, timeout=60)
        r.raise_for_status()
        import rasterio
        from rasterio.io import MemoryFile
        with MemoryFile(r.content) as mf, mf.open() as ds:
            a = ds.read(1).astype("float64")
        a[a < -100] = np.nan
        return a
    except Exception as e:  # noqa: BLE001 — le WMS peut tomber : l'échec est DIT (U5), jamais un 500
        log.warning("toiture_lidar : WMS MNH indisponible (%s)", e)
        return f"{type(e).__name__}: {e}"


def _classify(mnh: np.ndarray, mask: np.ndarray) -> tuple[str, dict]:
    """Même classification que le prototype contrôlé (qa/solaire/toiture_probe.py)."""
    from scipy.ndimage import binary_erosion
    gy, gx = np.gradient(mnh, RES)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    aspect = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360
    core = binary_erosion(mask, iterations=2)
    tot = int(core.sum())
    if tot < 40:
        return "indetermine", {}
    pentu = core & (slope >= 8) & (slope <= 50)
    part = float(pentu.sum()) / tot
    if part < 0.15:
        # plat = signal direct (85 %+ de pixels non pentus) : la confiance porte cette part.
        return "plat", {"part_pentue": round(part, 2), "confiance": round(1.0 - part, 3)}
    sect = ((aspect[pentu] + 11.25) // 22.5).astype(int) % 16
    hist = np.bincount(sect, minlength=16).astype(float)
    hist /= hist.sum()
    liss = np.array([hist[(i - 1) % 16] * 0.25 + hist[i] * 0.5 + hist[(i + 1) % 16] * 0.25
                     for i in range(16)])
    pics = [i for i in range(16)
            if liss[i] >= 0.10 and liss[i] >= liss[(i - 1) % 16] and liss[i] > liss[(i + 1) % 16]]
    pics = sorted(pics, key=lambda i: -liss[i])[:4]
    # S11 — confiance = « masse expliquée » : part de l'histogramme couverte par les pics ±1
    # secteur. Des pans nets concentrent la masse ; végétation/toit complexe la dispersent.
    expl = {j % 16 for i in pics for j in (i - 1, i, i + 1)}
    meta = {"part_pentue": round(part, 2), "pics_deg": [int(i * 22.5) for i in pics],
            "pente_mediane": round(float(np.median(slope[pentu])), 1),
            "confiance": round(float(sum(liss[i] for i in expl)), 3)}
    if len(pics) <= 1:
        return "monopente", meta
    if len(pics) == 2:
        ecart = min((pics[0] - pics[1]) % 16, (pics[1] - pics[0]) % 16)
        if ecart >= 6:
            return "double_pente", meta
        if ecart <= 2:
            return "monopente", meta
        return "croupe_complexe", meta
    return "croupe_complexe", meta


def analyse_toiture(session: Session, idu: str) -> dict | None:
    """Nature de toiture du PLUS GRAND bâtiment de la parcelle — cache d'abord, sinon calcul
    (une requête WMS) puis cache. None = pas de bâtiment / MNH indisponible (absence dite)."""
    ensure_table(session)
    row = session.execute(text(
        "SELECT verdict, pente_mediane_deg, pans_orientation_deg, part_pentue, confiance "
        "FROM toiture_lidar WHERE idu = :i"), {"i": idu}).mappings().first()
    if row:
        return _payload(row["verdict"], row["pente_mediane_deg"],
                        row["pans_orientation_deg"], row["part_pentue"], row["confiance"])
    bat = session.execute(text(
        """SELECT ST_AsGeoJSON(ST_Transform(b.geom, 2975)) AS gj,
                  ST_XMin(t.g) x1, ST_YMin(t.g) y1, ST_XMax(t.g) x2, ST_YMax(t.g) y2
           FROM spatial_layers b
           JOIN parcels p ON p.idu = :i AND ST_Intersects(b.geom_2975, p.geom_2975),
                LATERAL (SELECT b.geom_2975 AS g) t
           WHERE b.kind = 'batiment'
           ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1"""), {"i": idu}).mappings().first()
    if not bat:
        return None
    pad = 6.0
    bbox = (float(bat["x1"]) - pad, float(bat["y1"]) - pad,
            float(bat["x2"]) + pad, float(bat["y2"]) + pad)
    mnh = _fetch_mnh(bbox)
    if isinstance(mnh, str):
        # U5 — échec TECHNIQUE ≠ absence de donnée : l'écran le dira, rien n'entre au cache.
        return payload_indisponible(mnh)
    from rasterio.features import rasterize
    from rasterio.transform import from_bounds
    from shapely.geometry import shape
    h, w = mnh.shape
    mask = rasterize([(shape(json.loads(bat["gj"])), 1)], out_shape=(h, w),
                     transform=from_bounds(*bbox, w, h), fill=0).astype(bool)
    verdict, meta = _classify(np.nan_to_num(mnh, nan=0.0), mask)
    session.execute(text(
        "INSERT INTO toiture_lidar (idu, verdict, pente_mediane_deg, pans_orientation_deg, part_pentue, confiance) "
        "VALUES (:i, :v, :p, CAST(:o AS jsonb), :pp, :c) ON CONFLICT (idu) DO UPDATE SET "
        "verdict = EXCLUDED.verdict, pente_mediane_deg = EXCLUDED.pente_mediane_deg, "
        "pans_orientation_deg = EXCLUDED.pans_orientation_deg, part_pentue = EXCLUDED.part_pentue, "
        "confiance = EXCLUDED.confiance, computed_at = now()"),
        {"i": idu, "v": verdict, "p": meta.get("pente_mediane"),
         "o": json.dumps(meta.get("pics_deg") or []), "pp": meta.get("part_pentue"),
         "c": meta.get("confiance", 0.0)})
    return _payload(verdict, meta.get("pente_mediane"), meta.get("pics_deg") or [],
                    meta.get("part_pentue"), meta.get("confiance"))


def _payload(verdict: str, pente, pans, part, confiance) -> dict:
    conf = float(confiance) if confiance is not None else 0.0
    # S11 — sous le seuil, le verdict de forme n'est JAMAIS servi (0 faux au seuil sur
    # l'échantillon contrôlé) ; la pente médiane, mesure directe, reste servie.
    servi = verdict
    if verdict in ("monopente", "double_pente", "croupe_complexe") and conf < SEUIL_CONFIANCE:
        servi = "non_determine"
    return {
        "verdict": servi,
        "libelle": VERDICT_LABELS.get(servi, servi),
        "libelle_court": VERDICT_COURTS.get(servi, servi),
        "pente_mediane_deg": float(pente) if pente is not None else None,
        "pans_orientation_deg": (pans if isinstance(pans, list) else (pans or [])) if servi != "non_determine" else [],
        "part_pentue": float(part) if part is not None else None,
        "confiance": conf,
        "seuil": SEUIL_CONFIANCE,
        "statut": "Dérivé",
        "methode": ("Nature du toit lue sur le LiDAR HD IGN (MNH 50 cm) quand les pans sont "
                    "nets — confiance ≥ 0,70, calibrée à l'œil sur 50 bâtiments contre l'ortho "
                    "(0 faux au seuil, 36 % des toits classés) ; « non déterminée » sinon. "
                    "À vérifier sur la photo aérienne."),
    }
