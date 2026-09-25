"""RECETTE-8 W23 — HAUTEURS MESURÉES au LiDAR HD (MNS − MNT), faîtage ET égout distingués.

Le bâti BD TOPO ne porte qu'UNE hauteur (souvent au faîtage, parfois à l'égout, incertaine) : c'est
la cause de fond de E1 (on comparait un faîtage à une règle d'égout). Le LiDAR HD MNS de l'IGN donne
la hauteur MESURÉE : sur l'emprise du bâtiment, hauteur au-dessus du sol = MNS − MNT ; le FAÎTAGE est
le haut de la distribution (p99, robuste au bruit), l'ÉGOUT le bord de toit (p25).

Validé sur 20 bâtiments de Saint-Denis (script `scripts/_recette8_w23_lidar_mns.py`) : écart médian
faîtage − BD TOPO +0,57 m, écart absolu médian 1,11 m — les chiffres TIENNENT l'estimation, et le
MNS distingue bien faîtage/égout (ce que BD TOPO ne fait pas). Coût mesuré : ~1 s de fetch WMS +
33 ms de calcul par bâtiment.

Servi PAR PARCELLE à la demande (comme l'exposition, W22) : une fenêtre MNS+MNT autour du bâtiment
principal, jamais une ingestion massive bloquante. L'ingestion précalculée de toute l'île (pour
remplacer BD TOPO partout : extrusion 3D, surélévation, Apporteur) reste un batch borné à lancer sous
le go de Vic (coût extrapolé : ~1 s/bâtiment).
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger("labuse.hauteur_lidar")

WMS = "https://data.geopf.fr/wms-r/wms"
MNS = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS"   # surface (bâti compris) — LiDAR HD
MNT = "ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"       # sol
SRID = 2975
RES = 0.5
MARGE_M = 6.0
P_FAITAGE = 99
P_EGOUT = 25


def _fetch(layer: str, xmin, ymin, xmax, ymax) -> bytes:
    import httpx
    w = int(round((xmax - xmin) / RES))
    h = int(round((ymax - ymin) / RES))
    p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
         "CRS": f"EPSG:{SRID}", "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
         "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/geotiff", "STYLES": ""}
    r = httpx.get(WMS, params=p, timeout=90.0)
    r.raise_for_status()
    return r.content


def _hauteurs(geojson: str, bbox: tuple[float, float, float, float]) -> dict | None:
    """Faîtage/égout mesurés (m au-dessus du sol) sur l'emprise, depuis MNS−MNT. None si trop peu
    de cellules valides sous le contour."""
    import numpy as np
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.io import MemoryFile
    xmin, ymin, xmax, ymax = bbox
    tif_s = _fetch(MNS, xmin - MARGE_M, ymin - MARGE_M, xmax + MARGE_M, ymax + MARGE_M)
    tif_t = _fetch(MNT, xmin - MARGE_M, ymin - MARGE_M, xmax + MARGE_M, ymax + MARGE_M)
    with MemoryFile(tif_s) as ms, ms.open() as ds, MemoryFile(tif_t) as mt, mt.open() as dt:
        mns = ds.read(1).astype("float64"); tr = ds.transform; nod_s = ds.nodata
        mnt = dt.read(1).astype("float64"); nod_t = dt.nodata
    mask = geometry_mask([json.loads(geojson)], out_shape=mns.shape, transform=tr, invert=True)
    haut = mns - mnt
    ok = mask.copy()
    if nod_s is not None:
        ok &= mns != nod_s
    if nod_t is not None:
        ok &= mnt != nod_t
    ok &= np.isfinite(haut)
    vals = haut[ok]
    if vals.size < 5:
        return None
    return {"faitage_m": round(float(np.percentile(vals, P_FAITAGE)), 1),
            "egout_m": round(float(np.percentile(vals, P_EGOUT)), 1),
            "n_cellules": int(vals.size)}


def hauteur_parcelle_lidar(db, parcel_id: int) -> dict | None:
    """Hauteurs LiDAR mesurées du bâtiment PRINCIPAL (le plus grand) de la parcelle : faîtage, égout,
    et l'écart au faîtage BD TOPO (fait déclaré). None si la parcelle n'a pas de bâti BD TOPO. En cas
    d'échec fetch/calcul : `{faitage_m: None, erreur}` — dit, jamais une fausse mesure."""
    from sqlalchemy import text
    row = db.execute(text(
        """SELECT b.id, ST_AsGeoJSON(b.geom_2975) gj,
                  NULLIF(b.attrs->>'hauteur','')::float AS h_bdtopo,
                  ST_XMin(b.geom_2975) x0, ST_YMin(b.geom_2975) y0,
                  ST_XMax(b.geom_2975) x1, ST_YMax(b.geom_2975) y1
           FROM spatial_layers b JOIN parcels p ON p.id = :p
           WHERE b.kind='batiment' AND b.geom_2975 IS NOT NULL
             AND ST_Intersects(b.geom_2975, p.geom_2975)
           ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1"""), {"p": parcel_id}).mappings().first()
    if not row:
        return None
    try:
        h = _hauteurs(row["gj"], (row["x0"], row["y0"], row["x1"], row["y1"]))
    except Exception as exc:  # noqa: BLE001 — échec DIT
        log.warning("hauteur_lidar parcelle %s : %s", parcel_id, exc)
        return {"parcel_id": parcel_id, "faitage_m": None, "erreur": str(exc)[:200]}
    if h is None:
        return {"parcel_id": parcel_id, "faitage_m": None, "erreur": "MNS/MNT indisponible sur l'emprise"}
    hb = row["h_bdtopo"]
    return {"parcel_id": parcel_id, "source": "LiDAR HD MNS (IGN) − MNT, mesuré",
            "hauteur_bdtopo_m": (round(float(hb), 1) if hb is not None else None),
            "ecart_faitage_bdtopo_m": (round(h["faitage_m"] - float(hb), 1) if hb is not None else None),
            **h}


# ── RECETTE-9 T9 — ingestion BORNÉE + point unique de branchement des 4 consommateurs ────────────
#: table de MESURES LiDAR précalculées (ingestion bornée, sous go, jamais l'île en aveugle). Le point
#: de branchement lit ICI : une parcelle présente ⇒ sa hauteur passe d'`estimé` (BD TOPO déclaré) à
#: `sourcé` (LiDAR HD mesuré, faîtage ET égout distincts).
_DDL = """
CREATE TABLE IF NOT EXISTS batiment_hauteur_lidar (
  idu varchar(20) PRIMARY KEY,
  faitage_m real, egout_m real, hauteur_bdtopo_m real,
  ecart_faitage_bdtopo_m real, n_cellules int,
  mesure_le timestamptz NOT NULL DEFAULT now()
);
"""


def ensure_table(db) -> None:
    from sqlalchemy import text
    for stmt in _DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))


def ingest_hauteur_lidar(db, idu: str) -> dict | None:
    """Mesure le LiDAR d'UNE parcelle et l'écrit dans `batiment_hauteur_lidar` (ingestion bornée T9,
    idempotente par idu). Rend la mesure (ou None si pas de bâti / échec)."""
    from sqlalchemy import text
    ensure_table(db)
    pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if pid is None:
        return None
    m = hauteur_parcelle_lidar(db, int(pid))
    if not m or m.get("faitage_m") is None:
        return m
    db.execute(text(
        "INSERT INTO batiment_hauteur_lidar (idu, faitage_m, egout_m, hauteur_bdtopo_m, "
        "ecart_faitage_bdtopo_m, n_cellules, mesure_le) VALUES (:i, :f, :e, :b, :ec, :n, now()) "
        "ON CONFLICT (idu) DO UPDATE SET faitage_m=EXCLUDED.faitage_m, egout_m=EXCLUDED.egout_m, "
        "hauteur_bdtopo_m=EXCLUDED.hauteur_bdtopo_m, ecart_faitage_bdtopo_m=EXCLUDED.ecart_faitage_bdtopo_m, "
        "n_cellules=EXCLUDED.n_cellules, mesure_le=now()"),
        {"i": idu, "f": m.get("faitage_m"), "e": m.get("egout_m"), "b": m.get("hauteur_bdtopo_m"),
         "ec": m.get("ecart_faitage_bdtopo_m"), "n": m.get("n_cellules")})
    return m


_MOIS_FR = ("", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre")


def survol_libelle(date_fin) -> str | None:
    """RECETTE-11 A2/A3 — la date de survol LUE dans les métadonnées IGN, formatée « mois année »
    (jamais supposée). None si la source ne l'a pas publiée."""
    if date_fin is None:
        return None
    try:
        return f"{_MOIS_FR[date_fin.month]} {date_fin.year}"
    except (AttributeError, IndexError):
        return None


def hauteur_lidar_servie(db, idu: str) -> dict | None:
    """La mesure LiDAR PRÉCALCULÉE de la parcelle (table `batiment_hauteur_lidar`), ou None. Lecture
    seule et SANS réseau — c'est ce que lisent les consommateurs (fiche, Apporteur, Dossier, 3D).
    Porte la DATE DE SURVOL de la dalle (RECETTE-11 A3) : aucune mesure ne s'affiche sans sa date."""
    from sqlalchemy import text
    try:
        row = db.execute(text(
            "SELECT faitage_m, egout_m, hauteur_bdtopo_m, ecart_faitage_bdtopo_m, n_cellules, "
            "date_fin_survol, code_mission "
            "FROM batiment_hauteur_lidar WHERE idu = :i"), {"i": idu}).mappings().first()
    except Exception:  # noqa: BLE001 — table/colonnes absentes (pas encore d'ingestion) → repli BD TOPO
        try:
            db.rollback()
        except Exception:  # noqa: BLE001 — session mock / déjà close : le repli reste None
            pass
        return None
    if not row or row["faitage_m"] is None:
        return None
    survol = survol_libelle(row.get("date_fin_survol"))
    return {"faitage_m": round(float(row["faitage_m"]), 1),
            "egout_m": round(float(row["egout_m"]), 1) if row["egout_m"] is not None else None,
            "hauteur_bdtopo_m": (round(float(row["hauteur_bdtopo_m"]), 1)
                                 if row["hauteur_bdtopo_m"] is not None else None),
            "ecart_faitage_bdtopo_m": row["ecart_faitage_bdtopo_m"],
            "n_cellules": row["n_cellules"],
            "survol": survol, "date_fin_survol": row.get("date_fin_survol"),
            "code_mission": row.get("code_mission"),
            "source": ("LiDAR HD MNS (IGN), mesuré, survol de " + survol) if survol
                      else "LiDAR HD MNS (IGN), mesuré"}


# ── DONNEES-FIX-1 lot A — le badge « Sources discordantes » compare la BONNE grandeur ────────────
# FICHE-FIX-2 comparait le FAÎTAGE LiDAR (p99) à la hauteur BD TOPO. Or BD TOPO ≈ l'ÉGOUT : sur un
# toit en pente ou un R+n, le faîtage dépasse toujours l'égout ≈ BD TOPO — l'écart n'est PAS une
# erreur, c'est la définition. Résultat : le badge s'allumait sur 43 404 bâtis (15,9 %) alors que
# l'audit DONNEES-LIDAR-PROPRIO ne trouve que des cas normaux + une poignée de vraies aberrations.
#
# On compare donc désormais la MÊME grandeur (égout LiDAR ↔ hauteur BD TOPO) et on garde à part le
# seul autre motif réel : un faîtage physiquement impossible (bug de coordonnée/unité).
#
# Distribution mesurée de |égout − BD TOPO| sur 273 552 comparables (voir DONNEES-FIX-1.md) :
#   médiane 1,70 m · p90 4,50 m · p99 8,40 m · max ~30 m.
# Le bruit normal (arrondi BD TOPO, débords de toiture, pente du terrain sous l'emprise) reste ≤ ~8 m.
# À 15 m (≈ 1,8 × p99, ~5 niveaux d'écart sur la MÊME grandeur), une des deux sources est
# nécessairement fausse — jamais du bruit de mesure : 132 parcelles (0,05 %).
SEUIL_ECART_EGOUT_BDTOPO_M = 15.0
# Faîtage aberrant = hauteur impossible sur l'île (plus haut immeuble ~15 étages ≈ 45 m). Capte les
# 2 aberrations de coordonnée de l'audit (53 401 m) + les mesures cassées (faîtage ≤ 0, MNS < MNT) :
# 58 parcelles au total.
PLAFOND_FAITAGE_ABERRANT_M = 60.0


def discordance_hauteur(lid: dict | None) -> dict:
    """DONNEES-FIX-1 lot A — RÈGLE UNIQUE du badge « Sources discordantes », lue par la fiche §Bâti
    ET la marge en hauteur (Potentiel) : une seule règle pour les deux écrans.

    Compare l'ÉGOUT LiDAR à la hauteur BD TOPO (MÊME grandeur, cf. audit) ; l'ancienne comparaison
    faîtage↔BD TOPO s'allumait à tort sur ~16 % des bâtis. Deux motifs, tous deux réels :
      - « faîtage aberrant » : faîtage impossible (≤ 0 ou > plafond) → bug de mesure/coordonnée ;
      - « égout ↔ BD TOPO »  : les deux sources désignent des hauteurs incompatibles (> seuil).

    Renvoie {discordante, motif, ecart_egout_bdtopo_m, ecart_faitage_bdtopo_m} — toujours défini,
    même sans mesure LiDAR (discordante=False)."""
    if not lid:
        return {"discordante": False, "motif": None,
                "ecart_egout_bdtopo_m": None, "ecart_faitage_bdtopo_m": None}
    fait = lid.get("faitage_m")
    egout = lid.get("egout_m")
    bdtopo = lid.get("hauteur_bdtopo_m")
    ecart_eg = (round(float(egout) - float(bdtopo), 1)
                if egout is not None and bdtopo is not None else None)
    aberrant = fait is not None and (float(fait) <= 0 or float(fait) > PLAFOND_FAITAGE_ABERRANT_M)
    discord_eg = ecart_eg is not None and abs(ecart_eg) > SEUIL_ECART_EGOUT_BDTOPO_M
    motif = "faîtage aberrant" if aberrant else ("égout ↔ BD TOPO" if discord_eg else None)
    return {"discordante": bool(aberrant or discord_eg), "motif": motif,
            "ecart_egout_bdtopo_m": ecart_eg,
            "ecart_faitage_bdtopo_m": lid.get("ecart_faitage_bdtopo_m")}


def hauteur_batie(db, idu: str) -> dict | None:
    """POINT UNIQUE (T9) de la hauteur du bâti servie aux 4 consommateurs. Préfère la mesure LiDAR
    (faîtage + égout distincts, nature « sourcé ») ; à défaut la hauteur BD TOPO déclarée (« estimé »).
    None si aucune. L'ÉGOUT — que BD TOPO ne donne jamais — est la hauteur qui décide de la
    surélévation (règle à l'égout, cause de fond de E1)."""
    from sqlalchemy import text
    lid = hauteur_lidar_servie(db, idu)
    if lid:
        return {"hauteur_m": lid["faitage_m"], "faitage_m": lid["faitage_m"], "egout_m": lid["egout_m"],
                "nature": "sourcé", "survol": lid.get("survol"), "source": lid["source"]}
    hb = db.execute(text(
        """SELECT NULLIF(b.attrs->>'hauteur','')::float h
           FROM spatial_layers b JOIN parcels p ON p.idu = :i
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)
           ORDER BY ST_Area(b.geom_2975) DESC LIMIT 1"""), {"i": idu}).scalar()
    if hb is None:
        return None
    return {"hauteur_m": round(float(hb), 1), "faitage_m": None, "egout_m": None,
            "nature": "estimé", "source": "BD TOPO® (hauteur déclarée)"}
