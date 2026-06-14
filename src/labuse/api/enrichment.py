"""Enrichissement « fiche promoteur » (TEMPS 1) — données publiques, tracées.

Tout est **INDICATIF** et **SOURCÉ**. Aucune valeur réglementaire n'est fabriquée :
quand une donnée n'existe pas en open data, on le DIT (et on renvoie vers la source
officielle), on n'invente pas d'indicateur.

Mesures métriques en **EPSG:2975** (RGR92 UTM 40S — La Réunion) ; jamais en degrés.

Lecture seule : ce module n'écrit rien et NE TOUCHE NI la cascade NI le scoring.
Il est appelé par `_build_fiche` et chaque section est isolée (un échec réseau d'une
section ne casse pas la fiche → pas de 500).
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings


def _live_enabled() -> bool:
    """Appels externes (RGE ALTI / GPU) actifs ? OFF en test (déterminisme/vitesse)."""
    return os.environ.get("LABUSE_ENRICH_LIVE", "1") != "0"

# RGE ALTI (altimétrie) — service de calcul d'altitude IGN (déjà utilisé pour la pente).
ALTI_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"

# Tolérance latérale (m) entre l'axe d'une voie (BD TOPO = filaire) et la limite
# parcellaire : une voie de desserte fait ~quelques mètres de demi-largeur, donc la
# limite « sur rue » tombe dans ce tampon. INDICATIF.
FACADE_TOL_M = 6.0
FACADE_MIN_SEG_M = 1.0      # en deçà : artefact d'intersection, ignoré
FACADE_ANGLE_MAX = 25.0    # écart angulaire (°) limite limite/voie pour compter un « longe »

# Seuils de RÉGULARITÉ pour autoriser une profondeur (sinon : non significative).
RECT_MIN = 0.70   # aire / aire(rectangle d'aire minimale orienté)
CONVEX_MIN = 0.85  # aire / aire(enveloppe convexe) → drapeaux / formes en L exclus


# ───────────────────────────── 1. Cote altimétrique ─────────────────────────────

def _alti_sample_points(db: Session, parcel_id: int) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Points (lon,lat, en 4326) pour échantillonner l'altitude.

    `interior` : tirage UNIFORME en surface (ST_GeneratePoints) → base de la moyenne.
    `boundary` : sommets de la limite (simplifiée) → étend min/max aux angles réels.
    """
    area = db.execute(text("SELECT ST_Area(geom_2975) FROM parcels WHERE id=:p"), {"p": parcel_id}).scalar() or 0.0
    n_int = max(12, min(80, round(area / 300.0)))
    interior = [
        (float(lon), float(lat))
        for lon, lat in db.execute(
            text(
                "SELECT ST_X(g) lon, ST_Y(g) lat FROM ("
                "  SELECT (ST_Dump(ST_GeneratePoints(geom, :n))).geom g FROM parcels WHERE id=:p"
                "  UNION ALL SELECT ST_Centroid(geom) FROM parcels WHERE id=:p"
                ") q"
            ),
            {"p": parcel_id, "n": n_int},
        ).all()
    ]
    boundary = [
        (float(lon), float(lat))
        for lon, lat in db.execute(
            text(
                "SELECT ST_X(g) lon, ST_Y(g) lat FROM ("
                "  SELECT (ST_DumpPoints(ST_Boundary(ST_SimplifyPreserveTopology(geom, 0.00003)))).geom g "
                "  FROM parcels WHERE id=:p"
                ") q LIMIT 80"
            ),
            {"p": parcel_id},
        ).all()
    ]
    return interior, boundary


def _alti_query(points: list[tuple[float, float]], timeout: float) -> list[float | None]:
    """Interroge RGE ALTI par lots de 100 (quota 5 req/s). NODATA → None."""
    out: list[float | None] = []
    with httpx.Client(timeout=timeout, headers={"User-Agent": "LA-BUSE/0.1 (+fiche promoteur)"}) as c:
        for k in range(0, len(points), 100):
            part = points[k:k + 100]
            r = c.get(ALTI_URL, params={
                "lon": "|".join(f"{lon:.6f}" for lon, _ in part),
                "lat": "|".join(f"{lat:.6f}" for _, lat in part),
                "resource": "ign_rge_alti_wld", "zonly": "true"})
            r.raise_for_status()
            for h in r.json().get("elevations", []):
                out.append(None if h is None or h <= -1000 else float(h))
            if len(points) > 100:
                time.sleep(0.21)
    return out


def altimetry(db: Session, parcel_id: int) -> dict[str, Any]:
    """Altitude min/max/moyenne (RGE ALTI, échantillonnée et live). INDICATIF.

    moyenne : sur le tirage uniforme intérieur ; min/max : intérieur + angles.
    """
    source = "RGE ALTI 1m (IGN) — échantillonnage live"
    if not _live_enabled():
        return {"available": False, "note": "Échantillonnage live désactivé (mode hors-ligne).", "source": source}
    try:
        interior, boundary = _alti_sample_points(db, parcel_id)
        if not interior:
            return {"available": False, "note": "Géométrie sans surface échantillonnable.", "source": source}
        timeout = max(get_settings().http_timeout_s, 30.0)
        h_int = [h for h in _alti_query(interior, timeout) if h is not None]
        h_bnd = [h for h in _alti_query(boundary, timeout) if h is not None] if boundary else []
        if not h_int:
            return {"available": False, "note": "RGE ALTI sans valeur exploitable ici.", "source": source}
        allh = h_int + h_bnd
        return {
            "available": True,
            "min_m": round(min(allh), 1),
            "max_m": round(max(allh), 1),
            "mean_m": round(sum(h_int) / len(h_int), 1),
            "amplitude_m": round(max(allh) - min(allh), 1),
            "n_points": len(allh),
            "source": source,
            "indicatif": True,
        }
    except Exception as exc:  # noqa: BLE001 — réseau/timeout : on dégrade, pas de 500
        return {"available": False, "note": f"RGE ALTI injoignable ({type(exc).__name__}).", "source": source}


_CARDINAUX = ["Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ouest", "Ouest", "Nord-Ouest"]


def exposition(db: Session, parcel_id: int) -> dict[str, Any]:
    """Exposition (orientation dominante de la pente) — 2.A. Calculée par gradient d'altitude
    (RGE ALTI) sur 4 points cardinaux autour du centroïde. À La Réunion, l'exposition (vue,
    ensoleillement) est un driver de valeur. INDICATIF ; plat → pas d'exposition dominante."""
    source = "RGE ALTI (IGN) — gradient d'altitude"
    if not _live_enabled():
        return {"available": False, "note": "Calcul live désactivé (mode hors-ligne).", "source": source}
    row = db.execute(text(
        "SELECT ST_X(centroid) lon, ST_Y(centroid) lat, sqrt(ST_Area(geom_2975)) cote "
        "FROM parcels WHERE id = :p"), {"p": parcel_id}).first()
    if not row or row.lon is None:
        return {"available": False, "note": "Centroïde indisponible.", "source": source}
    import math
    lon, lat = float(row.lon), float(row.lat)
    d_m = max(25.0, min(120.0, float(row.cote or 50.0)))     # demi-pas adapté à la taille
    dlat = d_m / 111320.0
    dlon = d_m / (111320.0 * max(0.1, math.cos(math.radians(lat))))
    pts = [(lon, lat + dlat), (lon, lat - dlat), (lon + dlon, lat), (lon - dlon, lat)]  # N,S,E,W
    try:
        h = _alti_query(pts, max(get_settings().http_timeout_s, 20.0))
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "note": f"RGE ALTI injoignable ({type(exc).__name__}).", "source": source}
    if any(x is None for x in h):
        return {"available": False, "note": "RGE ALTI sans valeur exploitable ici.", "source": source}
    hN, hS, hE, hW = h
    dz_ns, dz_ew = hN - hS, hE - hW                          # uphill components (N, E)
    pente_locale = math.hypot(dz_ew, dz_ns) / (2 * d_m) * 100.0
    if pente_locale < 3.0:                                   # quasi plat → pas d'exposition nette
        return {"available": True, "exposition": None, "label": "terrain plat (pas d'exposition dominante)",
                "pente_locale_pct": round(pente_locale, 1), "source": source, "indicatif": True}
    azimut = (math.degrees(math.atan2(-dz_ew, -dz_ns)) + 360.0) % 360.0   # downhill, depuis le Nord
    card = _CARDINAUX[round(azimut / 45.0) % 8]
    return {"available": True, "exposition": card, "azimut_deg": round(azimut),
            "label": f"exposition {card}", "pente_locale_pct": round(pente_locale, 1),
            "source": source, "indicatif": True}


def vue_mer(db: Session, parcel_id: int) -> dict[str, Any]:
    """Vue mer — 2.B, v1 approximée (GRASS r.viewshed / raster PostGIS indisponibles ici).

    Ligne de vue 1D : profil d'altitude (RGE ALTI) du centroïde vers le point de côte le plus
    proche (trait de côte DEAL). La vue est dégagée si le terrain DESCEND vers la mer sans relief
    intermédiaire au-dessus de la ligne observateur→mer. Indicateur oui/partielle/non. LIMITE :
    profil sur un seul azimut (pas un viewshed 360°), sans bâti — INDICATIF."""
    import math
    source = "RGE ALTI (IGN) + trait de côte (DEAL) — ligne de vue 1D"
    if not _live_enabled():
        return {"available": False, "note": "Calcul live désactivé (mode hors-ligne).", "source": source}
    row = db.execute(text(
        """WITH p AS (SELECT centroid, geom_2975 FROM parcels WHERE id = :pid)
           SELECT ST_X(p.centroid) olon, ST_Y(p.centroid) olat,
                  ST_X(ST_Transform(t.cp,4326)) clon, ST_Y(ST_Transform(t.cp,4326)) clat,
                  round(t.dist) dist_m
           FROM p, LATERAL (
             SELECT ST_ClosestPoint(s.geom_2975, ST_Centroid(p.geom_2975)) cp,
                    ST_Distance(p.geom_2975, s.geom_2975) dist
             FROM spatial_layers s WHERE s.kind = 'trait_de_cote'
             ORDER BY p.geom_2975 <-> s.geom_2975 LIMIT 1) t"""),
        {"pid": parcel_id}).first()
    if not row or row.dist_m is None:
        return {"available": False, "note": "Trait de côte non ingéré.", "source": source}
    D = float(row.dist_m)
    if D > 6000:   # au-delà, une vue mer est très improbable depuis le sol
        return _memo_vue_mer(db, parcel_id, {"available": True, "vue": "non",
                "label": "pas de vue mer (côte à >6 km)", "distance_cote_m": round(D),
                "source": source, "indicatif": True})
    olon, olat, clon, clat = float(row.olon), float(row.olat), float(row.clon), float(row.clat)
    bearing = (math.degrees(math.atan2((clon - olon) * math.cos(math.radians(olat)), clat - olat)) + 360) % 360
    base = {"distance_cote_m": round(D), "azimut_mer_deg": round(bearing),
            "source": source, "indicatif": True, "available": True}
    if D < 120:    # front de mer : au contact de la côte → vue acquise (cas dégénéré du profil)
        return _memo_vue_mer(db, parcel_id, {**base, "vue": "oui", "label": "vue mer dégagée (front de mer)"})
    # échantillonnage du profil observateur → mer (jusqu'à 200 m AU-DELÀ de la côte, alt ~0).
    n, over = 40, 200.0
    f_end = (D + over) / D
    pts = [(olon + (clon - olon) * (k / n) * f_end, olat + (clat - olat) * (k / n) * f_end)
           for k in range(n + 1)]
    try:
        h = _alti_query(pts, max(get_settings().http_timeout_s, 25.0))
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "note": f"RGE ALTI injoignable ({type(exc).__name__}).", "source": source}
    hs = [x for x in h if x is not None]
    if len(hs) < n // 2:
        return {"available": False, "note": "RGE ALTI sans valeur exploitable ici.", "source": source}
    h0 = h[0] if h[0] is not None else max(hs)            # altitude observateur (parcelle)
    # obstruction = terrain AU-DESSUS de la ligne observateur→mer, sur la partie TERRESTRE (≤ D).
    obstructions, considered = 0, 0
    k_coast = round(n / f_end)
    for k in range(1, k_coast):
        if h[k] is None:
            continue
        considered += 1
        h_line = h0 * (1.0 - (k / n) / f_end * (D + over) / D)   # descend vers 0 à la côte
        if h[k] > h_line + 4.0:
            obstructions += 1
    frac = obstructions / considered if considered else 1.0
    vue = "oui" if frac < 0.10 else "partielle" if frac < 0.35 else "non"
    label = {"oui": "vue mer dégagée", "partielle": "vue mer partielle (relief intermédiaire)",
             "non": "pas de vue mer (relief masquant)"}[vue]
    return _memo_vue_mer(db, parcel_id, {**base, "vue": vue, "label": label,
            "altitude_obs_m": round(h0, 1), "obstruction_pct": round(100 * frac)})


def _memo_vue_mer(db: Session, parcel_id: int, res: dict) -> dict:
    """Mémoïse le résultat vue mer (cache lu par le bilan, sans appel live). Best-effort."""
    try:
        db.execute(text(
            """INSERT INTO parcel_vue_mer (parcel_id, vue, distance_cote_m, obstruction_pct, computed_at)
               VALUES (:p,:v,:d,:o, now())
               ON CONFLICT (parcel_id) DO UPDATE SET vue=EXCLUDED.vue,
                 distance_cote_m=EXCLUDED.distance_cote_m, obstruction_pct=EXCLUDED.obstruction_pct,
                 computed_at=now()"""),
            {"p": parcel_id, "v": res.get("vue"), "d": res.get("distance_cote_m"),
             "o": res.get("obstruction_pct")})
    except Exception:  # noqa: BLE001 - le cache ne casse jamais la fiche
        pass
    return res


# ──────────────────────────── 2. Façade sur rue + profondeur ────────────────────────────

def _shape_metrics(db: Session, parcel_id: int) -> dict[str, float]:
    a, hull, ombb_a, ombb_p = db.execute(
        text(
            "SELECT ST_Area(g), ST_Area(ST_ConvexHull(g)), "
            "ST_Area(ST_OrientedEnvelope(g)), ST_Perimeter(ST_OrientedEnvelope(g)) "
            "FROM (SELECT geom_2975 g FROM parcels WHERE id=:p) q"
        ), {"p": parcel_id},
    ).one()
    a = float(a or 0.0)
    s = float(ombb_p or 0.0) / 2.0
    disc = max(s * s - 4.0 * float(ombb_a or 0.0), 0.0)
    long_side = (s + math.sqrt(disc)) / 2.0
    short_side = (s - math.sqrt(disc)) / 2.0
    return {
        "area": a,
        "convexity": a / float(hull) if hull else 0.0,
        "rectangularity": a / float(ombb_a) if ombb_a else 0.0,
        "ombb_long": long_side,
        "ombb_short": short_side,
    }


def facade_depth(db: Session, parcel_id: int) -> dict[str, Any]:
    """Façade(s) sur voie (BD TOPO) et profondeur indicative. PRUDENCE :

    - façade = longueur de limite parcellaire longeant une voie (tampon ``FACADE_TOL_M``) ;
    - façade TOTALE dé-doublonnée (union des tampons) → pas de double comptage en angle ;
    - profondeur calculée UNIQUEMENT si la parcelle est régulière (≈ rectangulaire et
      convexe) ; sinon « forme irrégulière — profondeur non significative ».
    Tout en mètres (EPSG:2975), INDICATIF.
    """
    out: dict[str, Any] = {"source": "BD TOPO IGN (tronçons de route) · mesures EPSG:2975",
                           "tolerance_laterale_m": FACADE_TOL_M, "indicatif": True}
    shape = _shape_metrics(db, parcel_id)
    out["perimetre_m"] = round(db.execute(
        text("SELECT ST_Perimeter(geom_2975) FROM parcels WHERE id=:p"), {"p": parcel_id}).scalar() or 0.0, 1)

    # Façade par voie (orientation-aware) : on ne garde que les segments de LIMITE qui
    # LONGENT vraiment une voie (écart angulaire faible). Les retours perpendiculaires
    # d'angle (qui gonfleraient un simple tampon) sont écartés ; chaque segment est
    # rattaché à sa voie la PLUS PROCHE → pas de fusion abusive entre voies distinctes.
    per_road = {int(rid): float(flen) for rid, flen in db.execute(
        text(
            "WITH p AS (SELECT geom_2975 g FROM parcels WHERE id=:p), "
            "segs AS (SELECT (ST_DumpSegments(ST_Boundary((SELECT g FROM p)))).geom s), "
            "cand AS (SELECT segs.s seg, r.id rid, r.geom_2975 rg, ST_Distance(segs.s, r.geom_2975) d "
            "         FROM segs JOIN spatial_layers r ON r.kind='voirie' "
            "         AND ST_DWithin(segs.s, r.geom_2975, :tol)), "
            "nearest AS (SELECT DISTINCT ON (seg) seg, rid, rg FROM cand ORDER BY seg, d), "
            "d AS (SELECT rid, ST_Length(seg) len, "
            "        degrees(ST_Azimuth(ST_StartPoint(seg), ST_EndPoint(seg))) sa, "
            "        degrees(ST_Azimuth(ST_ClosestPoint(rg, ST_StartPoint(seg)), "
            "                           ST_ClosestPoint(rg, ST_EndPoint(seg)))) ra FROM nearest), "
            "ang AS (SELECT rid, len, CASE WHEN ra IS NULL THEN NULL ELSE "
            "          LEAST(abs((sa-ra+360)::numeric % 180), 180-abs((sa-ra+360)::numeric % 180)) "
            "        END ad FROM d) "
            "SELECT rid, sum(len) flen FROM ang WHERE ad < :amax GROUP BY rid ORDER BY flen DESC"
        ), {"p": parcel_id, "tol": FACADE_TOL_M, "amax": FACADE_ANGLE_MAX},
    ).all() if float(flen) >= FACADE_MIN_SEG_M}

    facade_principale = max(per_road.values(), default=0.0)
    total = sum(per_road.values())
    out["facade_totale_m"] = round(total, 1)
    out["facade_principale_m"] = round(facade_principale, 1)
    out["nb_voies"] = len(per_road)  # voies BD TOPO distinctes longées
    out["sur_rue"] = total >= FACADE_MIN_SEG_M

    if not out["sur_rue"]:
        out["profondeur_m"] = None
        out["profondeur_note"] = "Aucune façade sur voie identifiée (parcelle en cœur d'îlot ?)."
        return out

    regular = shape["rectangularity"] >= RECT_MIN and shape["convexity"] >= CONVEX_MIN
    if regular and facade_principale >= FACADE_MIN_SEG_M:
        depth = shape["area"] / facade_principale
        # garde-fou : la profondeur ne peut dépasser la plus grande dimension du terrain
        if depth <= shape["ombb_long"] * 1.15:
            out["profondeur_m"] = round(depth, 1)
            out["profondeur_note"] = "Approximation surface/façade (terrain régulier)."
        else:
            out["profondeur_m"] = None
            out["profondeur_note"] = "Forme atypique — profondeur non significative."
    else:
        out["profondeur_m"] = None
        out["profondeur_note"] = "Forme irrégulière — profondeur non significative."
    out["forme"] = {
        "rectangularite": round(shape["rectangularity"], 2),
        "convexite": round(shape["convexity"], 2),
        "emprise_orientee_m": [round(shape["ombb_long"], 1), round(shape["ombb_short"], 1)],
    }
    return out


# ──────────────────────────────── 4. PLU détaillé ────────────────────────────────

def _gpu_geom(db: Session, parcel_id: int) -> dict | None:
    gj = db.execute(text("SELECT ST_AsGeoJSON(geom) FROM parcels WHERE id=:p"), {"p": parcel_id}).scalar()
    import json
    return json.loads(gj) if gj else None


def plu_detail(db: Session, parcel_id: int, lon: float, lat: float) -> dict[str, Any]:
    """PLU : zonage (déjà ingéré) + prescriptions/servitudes RÉELLES de l'API GPU.

    Les règles CHIFFRÉES (hauteur, emprise, reculs) ne sont PAS exposées par l'API
    (elles vivent dans le règlement écrit) : on le dit explicitement et on renvoie au
    règlement. On NE FABRIQUE AUCUNE valeur réglementaire.
    """
    out: dict[str, Any] = {"source": "API Carto GPU (IGN) + zonage ingéré"}

    # Zonage : depuis la couche déjà ingérée (intersection précise en 2975)
    zones = db.execute(
        text(
            "SELECT DISTINCT attrs->>'libelle' lib, attrs->>'idurba' idurba "
            "FROM spatial_layers sl, parcels p "
            "WHERE p.id=:p AND sl.kind='plu_gpu_zone' AND ST_Intersects(sl.geom_2975, p.geom_2975) "
            "AND attrs->>'libelle' IS NOT NULL"
        ), {"p": parcel_id},
    ).mappings().all()
    out["zonage"] = [z["lib"] for z in zones]
    out["idurba"] = next((z["idurba"] for z in zones if z["idurba"]), None)

    # Prescriptions / servitudes live (surf/lin/pct) — réelles, jamais inventées
    prescriptions: list[dict] = []
    note: str | None = None
    if not _live_enabled():
        note = "Prescriptions live désactivées (mode hors-ligne)."
    else:
        try:
            from ..connectors.gpu import GpuConnector
            geom = _gpu_geom(db, parcel_id)
            if not geom:
                note = "Géométrie indisponible pour interroger les prescriptions."
            else:
                import concurrent.futures as _cf
                gpu = GpuConnector()

                def _fetch(kind):  # les 3 familles en PARALLÈLE (≈6 s → ≈2 s)
                    try:
                        return kind, gpu.prescriptions(geom, kind=kind)
                    except Exception:  # noqa: BLE001 — une famille en échec n'arrête pas les autres
                        return kind, None

                with _cf.ThreadPoolExecutor(max_workers=3) as _ex:
                    for kind, fc in _ex.map(_fetch, ("surf", "lin", "pct")):
                        if not fc:
                            continue
                        for feat in fc.get("features", []):
                            pr = feat.get("properties", {}) or {}
                            prescriptions.append({
                                "type": kind,
                                "libelle": pr.get("libelle") or pr.get("lib_idpsc"),
                                "nature": pr.get("nature"),
                            })
        except Exception as exc:  # noqa: BLE001
            note = f"Prescriptions GPU injoignables ({type(exc).__name__})."
    out["prescriptions"] = prescriptions
    if note:
        out["prescriptions_note"] = note

    out["regles_chiffrees"] = None
    out["regles_chiffrees_note"] = (
        "Hauteur max, emprise au sol et reculs ne sont pas exposés par l'API GPU : "
        "ils figurent dans le RÈGLEMENT ÉCRIT du PLU. Voir le règlement."
    )
    out["reglement_url"] = f"https://www.geoportail-urbanisme.gouv.fr/map/?lon={lon:.5f}&lat={lat:.5f}&zoom=18"
    return out


# ────────────────────────── 5. Propriétaire public/privé ──────────────────────────

def owner(db: Session, parcel_id: int) -> dict[str, Any]:
    """Catégorie de propriétaire si une source publique la donne, sinon honnêteté.

    On LIT les Fichiers fonciers s'ils ont été ingérés pour la parcelle (sous convention
    CEREMA, donc rarement présents ici) et on AFFICHE la catégorie morale/publique le cas
    échéant ; sinon « non vérifié ». Jamais de personne physique nominative, rien de fabriqué.
    """
    # 1.A — Fichier DGFiP des personnes morales (PUBLIC) en priorité : si la parcelle y figure,
    # on connaît le type ET le nom du propriétaire morale. Absente → particulier (→ SPF).
    pm = db.execute(text(
        """SELECT pm.groupe, pm.forme_juridique, pm.denomination, pm.millesime
           FROM parcels p JOIN parcelle_personne_morale pm ON pm.idu = p.idu
           WHERE p.id = :pid"""), {"pid": parcel_id}).mappings().first()
    if pm:
        from ..proprietaire_type import classify_dgfip
        ot = classify_dgfip(pm["groupe"], pm["forme_juridique"], pm["denomination"])
        return {
            "categorie": ot["famille"], "personne_morale": True, "indivision": ot["indivision"],
            "note": f"Propriétaire : {ot['label']}" + (f" — {ot['owner_name']}" if ot.get("owner_name") else ""),
            "source": "DGFiP — personnes morales (millésime " + str(pm["millesime"] or "—") + ")",
            "owner_type": ot["owner_type"], "owner_label": ot["label"], "owner_name": ot.get("owner_name"),
            "owner_famille": ot["famille"], "owner_acquerabilite": ot["acquerabilite"],
            "owner_identifiable": ot["identifiable"], "needs_spf": False,
        }

    note_absent = (
        "Propriétaire personne physique probable (absent du fichier DGFiP des personnes morales) "
        "— aucune donnée nominative dans LA BUSE. Identité à obtenir via le SPF (bouton ci-dessous)."
    )
    src = "Fichiers fonciers (Cerema)"
    row = db.execute(
        text(
            "SELECT psr.raw_payload FROM parcel_source_results psr "
            "JOIN data_sources ds ON ds.id = psr.data_source_id "
            "WHERE psr.parcel_id = :p AND ds.name = :s ORDER BY psr.fetched_at DESC LIMIT 1"
        ), {"p": parcel_id, "s": src},
    ).first()
    payload = row[0] if row and row[0] else None
    if not payload:
        from ..proprietaire_type import classify_owner_type
        ot = classify_owner_type(None)   # → inconnu
        return {"categorie": None, "note": note_absent, "source": "—",
                "owner_type": ot["owner_type"], "owner_label": ot["label"],
                "owner_famille": ot["famille"], "owner_acquerabilite": ot["acquerabilite"],
                "owner_identifiable": False, "needs_spf": True}

    morale = bool(payload.get("personne_morale"))
    cat = payload.get("categorie")
    nb = payload.get("nb_droits_propriete")
    indivision = bool(payload.get("indivision") or (nb is not None and nb >= 2))
    publique = morale and bool(cat) and any(
        h in cat.lower() for h in
        ("commune", "état", "etat", "région", "region", "départe", "departe", "public",
         "epci", "epf", "domaine", "collectivité", "collectivite", "conservatoire", "office", "hlm"))
    categorie = "publique" if publique else "morale_privee" if morale else "personne_physique"
    libelle = ("Propriété publique" if publique else
               "Personne morale privée" if morale else "Personne physique (non nominatif)")
    from ..proprietaire_type import classify_owner_type, needs_spf
    otype = classify_owner_type(payload)
    return {
        "categorie": categorie,
        "personne_morale": morale,
        "indivision": indivision,
        "note": f"Propriétaire : {libelle}" + (f" — {cat}" if cat else "")
                + (" · indivision probable (bloqueur fréquent)" if indivision else ""),
        "source": src,
        # Type fin (Lot C3) : SCI / commune / EPF / bailleur / État… + besoin d'une demande SPF.
        "owner_type": otype["owner_type"], "owner_label": otype["label"],
        "owner_famille": otype["famille"], "owner_acquerabilite": otype["acquerabilite"],
        "owner_identifiable": otype["identifiable"], "needs_spf": needs_spf(otype),
    }


# ──────────────────────────── Réseaux (eau / EDF / assainissement) ────────────────────────────

def networks(db: Session, parcel_id: int) -> dict[str, Any]:
    """Réseaux / viabilité — VERSION HONNÊTE (PARTIE 2).

    Les tracés réseau fins (eau / EDF / assainissement) ne sont PAS en open data 974 :
    on ne fabrique AUCUN indicateur « raccordé/non raccordé ». On fournit seulement :
    - un PROXY DE PRÉSOMPTION (proximité voirie : les réseaux courent généralement le
      long des voies) et la distance à la voie la plus proche ;
    - un champ clair « à vérifier auprès des concessionnaires (DT-DICT) ».
    """
    dtdict = ("Viabilité (eau, électricité, assainissement) à vérifier auprès des "
              "concessionnaires via DT-DICT (téléservice reseaux-et-canalisations.gouv.fr).")

    # Proxy de présomption : distance à la voirie la plus proche (BD TOPO, déjà ingérée).
    dist = db.execute(text(
        "SELECT round(ST_Distance(p.geom_2975, v.geom_2975)) "
        "FROM parcels p CROSS JOIN LATERAL ("
        "  SELECT geom_2975 FROM spatial_layers WHERE commune = p.commune AND kind = 'voirie' "
        "  ORDER BY p.geom_2975 <-> geom_2975 LIMIT 1) v WHERE p.id = :pid"),
        {"pid": parcel_id}).scalar()
    dist = float(dist) if dist is not None else None
    contact = dist is not None and dist <= 1.0
    if dist is None:
        presomption = "Voirie non disponible en base ici — proximité non évaluable."
    elif contact:
        presomption = ("Voirie AU CONTACT de la parcelle → réseaux probablement à proximité "
                       "immédiate (ils suivent généralement les voies). À CONFIRMER.")
    else:
        presomption = (f"Voie la plus proche à ~{dist:.0f} m → viabilisation à étudier "
                       "(extension de réseau possible, surcoût). À confirmer.")

    return {
        # JAMAIS « raccordé/non raccordé » : statut volontairement « à vérifier ».
        "viabilite": {
            "statut": "à_vérifier",
            "voirie_contact": contact,
            "distance_voirie_m": dist,
            "presomption": presomption,
            "a_verifier": dtdict,
        },
        "eau_potable": {"disponible_open_data": False,
                        "note": "Open data 974 limité à la qualité/captages/stations, pas au tracé. " + dtdict},
        "assainissement": {"disponible_open_data": False,
                           "note": "Open data limité aux stations de traitement (STEP), pas au réseau. " + dtdict},
        "electricite": {"disponible_open_data": False,
                        "note": "La Réunion = EDF SEI (hors Enedis) : open data agrégé (km de lignes), "
                                "sans tracé géolocalisé. " + dtdict},
        "source": "Recon open data 974 (eaureunion.fr, ODS Réunion, opendata-reunion.edf.fr) — "
                  "aucun tracé réseau exploitable par parcelle (cf. RESEAUX_RECON.md). "
                  "Présomption = proximité voirie (BD TOPO).",
    }


# ─────────────────────────────────── Orchestrateur ───────────────────────────────────

def build_enrichment(db: Session, parcel, lon: float, lat: float) -> dict[str, Any]:
    """Assemble le bloc « promoteur » de la fiche. Chaque section est isolée."""
    def _safe(fn, *a):
        try:
            return fn(*a)
        except Exception as exc:  # noqa: BLE001 — jamais de 500 sur la fiche
            return {"available": False, "note": f"Indisponible ({type(exc).__name__})."}

    return {
        "altimetrie": _safe(altimetry, db, parcel.id),
        "exposition": _safe(exposition, db, parcel.id),
        "vue_mer": _safe(vue_mer, db, parcel.id),
        "facade": _safe(facade_depth, db, parcel.id),
        "plu_detail": _safe(plu_detail, db, parcel.id, lon, lat),
        "proprietaire": _safe(owner, db, parcel.id),
        "reseaux": _safe(networks, db, parcel.id),
        "disclaimer": "Données promoteur indicatives, sourcées ; aucune valeur réglementaire fabriquée. "
                      "Mesures en EPSG:2975. À confirmer auprès des sources officielles.",
    }


# ───────────────────── Cache d'enrichissement (perf fiche) ─────────────────────
# L'enrichissement « promoteur » fait des appels externes LENTS (prescriptions GPU ~6 s,
# RGE ALTI ~1,5 s) mais STATIQUES par parcelle. On le calcule UNE FOIS et on le stocke ;
# la fiche lit le cache → ouverture quasi instantanée. Pré-chauffable par commune/statut.

def _ensure_cache_table(db: Session) -> None:
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS parcel_enrichment ("
        " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
        " payload jsonb NOT NULL, computed_at timestamptz NOT NULL DEFAULT now())"))


def enrichment_cached(db: Session, parcel, lon: float, lat: float, *, refresh: bool = False) -> dict[str, Any]:
    """Enrichissement servi depuis le cache ; calculé puis stocké au premier accès."""
    _ensure_cache_table(db)
    if not refresh:
        cached = db.execute(text("SELECT payload FROM parcel_enrichment WHERE parcel_id = :p"),
                            {"p": parcel.id}).scalar()
        if cached is not None:
            return cached
    payload = build_enrichment(db, parcel, lon, lat)
    db.execute(text(
        "INSERT INTO parcel_enrichment (parcel_id, payload, computed_at) "
        "VALUES (:p, CAST(:j AS jsonb), now()) "
        "ON CONFLICT (parcel_id) DO UPDATE SET payload = EXCLUDED.payload, computed_at = now()"),
        {"p": parcel.id, "j": json.dumps(payload)})
    return payload


def warm_commune(db: Session, commune: str,
                 statuses: tuple[str, ...] = ("opportunite", "a_creuser"),
                 limit: int | None = None) -> int:
    """Pré-chauffe le cache pour les parcelles cliquables d'une commune (au moment de
    l'évaluation / en batch, pas au clic)."""
    from ..models import Parcel
    _ensure_cache_table(db)
    sql = ("SELECT p.id, ST_X(p.centroid), ST_Y(p.centroid) FROM parcels p "
           "JOIN LATERAL (SELECT status FROM parcel_evaluations e WHERE e.parcel_id=p.id "
           "ORDER BY evaluated_at DESC LIMIT 1) ev ON true "
           "WHERE p.commune = :c AND ev.status = ANY(:st) "
           "AND NOT EXISTS (SELECT 1 FROM parcel_enrichment pe WHERE pe.parcel_id = p.id)")
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = db.execute(text(sql), {"c": commune, "st": list(statuses)}).all()
    n = 0
    for pid, lon, lat in rows:
        enrichment_cached(db, db.get(Parcel, pid), float(lon), float(lat), refresh=True)
        db.commit()
        n += 1
    return n
